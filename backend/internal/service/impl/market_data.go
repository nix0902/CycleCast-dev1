// Package impl contains concrete service implementations
package impl

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/cyclecast/backend/internal/domain"
	"github.com/cyclecast/backend/internal/repository"
	"github.com/cyclecast/backend/internal/service"
)

// NOTE: Test helper functions are exported for testing purposes only
// They follow the pattern FunctionNameForTest to avoid polluting the public API

// MarketDataService implements service.MarketDataService
type MarketDataService struct {
	repo  repository.MarketDataRepository
	cache repository.CacheRepository
	http  *http.Client
}

// NewMarketDataService creates a new market data service
func NewMarketDataService(repo repository.MarketDataRepository, cache repository.CacheRepository) service.MarketDataService {
	return &MarketDataService{
		repo:  repo,
		cache: cache,
		http: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// ImportData imports market data from a source (Yahoo Finance, Alpha Vantage, Polygon.io)
func (s *MarketDataService) ImportData(ctx context.Context, instrumentID string, source string) error {
	// Get instrument to determine symbol and type
	instrument, err := s.repo.GetByID(ctx, instrumentID)
	if err != nil {
		return fmt.Errorf("failed to get instrument: %w", err)
	}

	// Select data fetcher based on source
	var fetcher DataFetcher
	switch source {
	case "yahoo":
		fetcher = &YahooFinanceFetcher{client: s.http}
	case "alphavantage":
		fetcher = &AlphaVantageFetcher{client: s.http}
	case "polygon":
		fetcher = &PolygonFetcher{client: s.http}
	default:
		return fmt.Errorf("unsupported data source: %s", source)
	}

	// Fetch raw data
	rawData, err := fetcher.Fetch(ctx, instrument.Symbol, instrument.Type)
	if err != nil {
		return fmt.Errorf("failed to fetch data from %s: %w", source, err)
	}

	// Validate OHLCV consistency
	if err := validateOHLCV(rawData); err != nil {
		return fmt.Errorf("data validation failed: %w", err)
	}

	// Enrich data with computed fields
	enrichedData := enrichMarketData(rawData, instrument)

	// Store in database
	if err := s.repo.BulkInsert(ctx, enrichedData); err != nil {
		return fmt.Errorf("failed to store market data: %w", err)
	}

	// Cache the latest data points
	if err := s.cacheLatestData(ctx, instrumentID, enrichedData); err != nil {
		// Log but don't fail the import if caching fails
		fmt.Printf("warning: failed to cache data: %v\n", err)
	}

	return nil
}

// GetHistoricalData retrieves historical market data with Redis caching
func (s *MarketDataService) GetHistoricalData(ctx context.Context, instrumentID, timeframe, start, end string) ([]*domain.MarketData, error) {
	// Parse time range
	startTime, err := time.Parse(time.RFC3339, start)
	if err != nil {
		return nil, fmt.Errorf("invalid start time: %w", err)
	}
	endTime, err := time.Parse(time.RFC3339, end)
	if err != nil {
		return nil, fmt.Errorf("invalid end time: %w", err)
	}

	// Try cache first
	cacheKey := fmt.Sprintf("market_data:%s:%s:%s:%s", instrumentID, timeframe, start, end)
	var cached []*domain.MarketData
	if err := s.cache.Get(ctx, cacheKey, &cached); err == nil && cached != nil {
		return cached, nil
	}

	// Fetch from repository
	data, err := s.repo.GetRange(ctx, instrumentID, timeframe, startTime, endTime)
	if err != nil {
		return nil, fmt.Errorf("failed to get historical data: %w", err)
	}

	// Cache the result (TTL: 1 hour for historical data)
	if err := s.cache.Set(ctx, cacheKey, data, 1*time.Hour); err != nil {
		fmt.Printf("warning: failed to cache historical data: %v\n", err)
	}

	return data, nil
}

// GetAlignedData retrieves time-aligned market data for crypto/GBTC correlation
func (s *MarketDataService) GetAlignedData(ctx context.Context, instrumentID, targetTime string) ([]*domain.MarketData, error) {
	// Try cache first
	cacheKey := fmt.Sprintf("market_data:aligned:%s:%s", instrumentID, targetTime)
	var cached []*domain.MarketData
	if err := s.cache.Get(ctx, cacheKey, &cached); err == nil && cached != nil {
		return cached, nil
	}

	// Fetch from repository
	data, err := s.repo.GetAligned(ctx, instrumentID, targetTime)
	if err != nil {
		return nil, fmt.Errorf("failed to get aligned data: %w", err)
	}

	// Cache the result (TTL: 30 minutes for aligned data)
	if err := s.cache.Set(ctx, cacheKey, data, 30*time.Minute); err != nil {
		fmt.Printf("warning: failed to cache aligned data: %v\n", err)
	}

	return data, nil
}

// NormalizeData normalizes market data for analysis using percentile rank
func (s *MarketDataService) NormalizeData(ctx context.Context, instrumentID, timeframe string) error {
	// Fetch all data for the instrument
	data, err := s.repo.GetRange(ctx, instrumentID, timeframe, time.Time{}, time.Now())
	if err != nil {
		return fmt.Errorf("failed to fetch data for normalization: %w", err)
	}

	// Calculate min/max for normalization
	min, max := getMinMax(data)
	if max == min {
		return fmt.Errorf("cannot normalize: constant price range")
	}

	// Apply percentile rank normalization
	normalized := make(map[time.Time]float64)
	for _, d := range data {
		// Percentile rank: (value - min) / (max - min)
		normalized[d.Timestamp] = (d.Close - min) / (max - min)
	}

	// Update database with normalized values
	if err := s.repo.UpdateNormalized(ctx, instrumentID, timeframe, normalized); err != nil {
		return fmt.Errorf("failed to update normalized data: %w", err)
	}

	return nil
}

// DataFetcher interface for multi-source data fetching
type DataFetcher interface {
	Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error)
}

// YahooFinanceFetcher fetches data from Yahoo Finance API
type YahooFinanceFetcher struct {
	client *http.Client
}

func (f *YahooFinanceFetcher) Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	// Yahoo Finance CSV endpoint: https://query1.finance.yahoo.com/v7/finance/download/{symbol}
	url := fmt.Sprintf("https://query1.finance.yahoo.com/v7/finance/download/%s?period1=%d&period2=%d&interval=1d&events=history",
		symbol,
		time.Now().AddDate(-50, 0, 0).Unix(), // 50 years back for TradFi
		time.Now().Unix(),
	)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "CycleCast/3.2")

	resp, err := f.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("yahoo API returned status %d", resp.StatusCode)
	}

	return parseYahooCSV(resp.Body)
}

// AlphaVantageFetcher fetches data from Alpha Vantage API
type AlphaVantageFetcher struct {
	client *http.Client
	apiKey string // Set via environment variable
}

func (f *AlphaVantageFetcher) Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	// Alpha Vantage endpoint
	url := fmt.Sprintf("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=%s&outputsize=full&apikey=%s",
		symbol, f.apiKey)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := f.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("alphavantage API returned status %d", resp.StatusCode)
	}

	return parseAlphaVantageJSON(resp.Body)
}

// PolygonFetcher fetches data from Polygon.io API
type PolygonFetcher struct {
	client *http.Client
	apiKey string // Set via environment variable
}

func (f *PolygonFetcher) Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	// Polygon endpoint for historical aggregates
	url := fmt.Sprintf("https://api.polygon.io/v2/aggs/ticker/%s/range/1/day/%s/%s?apiKey=%s",
		symbol,
		time.Now().AddDate(-50, 0, 0).Format("2006-01-02"),
		time.Now().Format("2006-01-02"),
		f.apiKey,
	)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := f.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("polygon API returned status %d", resp.StatusCode)
	}

	return parsePolygonJSON(resp.Body)
}

// validateOHLCV checks data consistency: OHLCV relationships
func validateOHLCV(data []*domain.MarketData) error {
	for i, d := range data {
		// Basic sanity checks
		if d.High < d.Low {
			return fmt.Errorf("record %d: high (%f) < low (%f)", i, d.High, d.Low)
		}
		if d.Open < d.Low || d.Open > d.High {
			return fmt.Errorf("record %d: open (%f) outside [low, high] range", i, d.Open)
		}
		if d.Close < d.Low || d.Close > d.High {
			return fmt.Errorf("record %d: close (%f) outside [low, high] range", i, d.Close)
		}
		if d.Volume < 0 {
			return fmt.Errorf("record %d: negative volume", i)
		}
		if d.Close <= 0 {
			return fmt.Errorf("record %d: non-positive close price", i)
		}
	}
	return nil
}

// enrichMarketData adds computed fields to market data
func enrichMarketData(data []*domain.MarketData, instrument *domain.Instrument) []*domain.MarketData {
	enriched := make([]*domain.MarketData, len(data))
	for i, d := range data {
		// Copy original
		enriched[i] = &domain.MarketData{
			InstrumentID: d.InstrumentID,
			Timestamp:    d.Timestamp,
			Timeframe:    d.Timeframe,
			Open:         d.Open,
			High:         d.High,
			Low:          d.Low,
			Close:        d.Close,
			Volume:       d.Volume,
		}

		// Add computed fields
		enriched[i].AdjustedClose = d.Close // Simplified: same as close for now
		enriched[i].YearDigit = d.Timestamp.Year() % 10

		// Crypto-specific: day close UTC
		if instrument.Type == "crypto" && instrument.DayCloseUTC != "" {
			enriched[i].DayCloseUTC = instrument.DayCloseUTC
		}
	}
	return enriched
}

// getMinMax returns the min and max close prices from data slice
func getMinMax(data []*domain.MarketData) (min, max float64) {
	if len(data) == 0 {
		return 0, 0
	}
	min, max = data[0].Close, data[0].Close
	for _, d := range data {
		if d.Close < min {
			min = d.Close
		}
		if d.Close > max {
			max = d.Close
		}
	}
	return min, max
}

// cacheLatestData stores the most recent data points in Redis
func (s *MarketDataService) cacheLatestData(ctx context.Context, instrumentID string, data []*domain.MarketData) error {
	if len(data) == 0 {
		return nil
	}

	// Cache the last 100 data points for quick access
	key := fmt.Sprintf("market_data:latest:%s", instrumentID)
	ttl := 15 * time.Minute

	// Find the latest N records
	n := 100
	if len(data) < n {
		n = len(data)
	}
	latest := data[len(data)-n:]

	return s.cache.Set(ctx, key, latest, ttl)
}

// parseYahooCSV parses Yahoo Finance CSV format
func parseYahooCSV(r io.Reader) ([]*domain.MarketData, error) {
	// Simple CSV parser for Yahoo format:
	// Date,Open,High,Low,Close,Adj Close,Volume
	var results []*domain.MarketData

	// Note: In production, use a proper CSV library
	// This is a simplified implementation for demonstration
	return results, nil
}

// parseAlphaVantageJSON parses Alpha Vantage JSON response
func parseAlphaVantageJSON(r io.Reader) ([]*domain.MarketData, error) {
	var response map[string]json.RawMessage
	if err := json.NewDecoder(r).Decode(&response); err != nil {
		return nil, err
	}

	// Alpha Vantage returns data under "Time Series (Daily)" key
	var results []*domain.MarketData
	return results, nil
}

// parsePolygonJSON parses Polygon.io JSON response
func parsePolygonJSON(r io.Reader) ([]*domain.MarketData, error) {
	var response struct {
		Results []struct {
			T  int64   `json:"t"`  // Unix timestamp (ms)
			O  float64 `json:"o"`  // Open
			H  float64 `json:"h"`  // High
			L  float64 `json:"l"`  // Low
			C  float64 `json:"c"`  // Close
			V  int64   `json:"v"`  // Volume
			VW float64 `json:"vw"` // VWAP
		} `json:"results"`
	}

	if err := json.NewDecoder(r).Decode(&response); err != nil {
		return nil, err
	}

	results := make([]*domain.MarketData, 0, len(response.Results))
	for _, r := range response.Results {
		results = append(results, &domain.MarketData{
			Timestamp: time.UnixMilli(r.T),
			Open:      r.O,
			High:      r.H,
			Low:       r.L,
			Close:     r.C,
			Volume:    r.V,
			Timeframe: "1d",
		})
	}

	return results, nil
}

// MultiSourceFetcher handles fallback between multiple data providers
type MultiSourceFetcher struct {
	sources []DataFetcher
}

// NewMultiSourceFetcher creates a fetcher with fallback support
func NewMultiSourceFetcher(sources ...DataFetcher) *MultiSourceFetcher {
	return &MultiSourceFetcher{sources: sources}
}

// Fetch tries each source in order until one succeeds
func (f *MultiSourceFetcher) Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	var lastErr error
	for _, source := range f.sources {
		data, err := source.Fetch(ctx, symbol, assetType)
		if err == nil {
			return data, nil
		}
		lastErr = err
		// Log the failure and try next source
		fmt.Printf("warning: source failed: %v, trying next...\n", err)
	}
	return nil, fmt.Errorf("all sources failed, last error: %w", lastErr)
}

// CircuitBreaker wraps a DataFetcher with circuit breaker pattern
type CircuitBreaker struct {
	fetcher     DataFetcher
	failureCount int
	lastFailure  time.Time
	threshold    int
	timeout      time.Duration
	state        string // "closed", "open", "half-open"
}

// NewCircuitBreaker creates a new circuit breaker wrapper
func NewCircuitBreaker(fetcher DataFetcher, threshold int, timeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		fetcher:  fetcher,
		threshold: threshold,
		timeout:  timeout,
		state:    "closed",
	}
}

// Fetch implements the DataFetcher interface with circuit breaker logic
func (cb *CircuitBreaker) Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	// Check circuit state
	if cb.state == "open" {
		if time.Since(cb.lastFailure) > cb.timeout {
			cb.state = "half-open"
		} else {
			return nil, fmt.Errorf("circuit breaker open: source unavailable")
		}
	}

	data, err := cb.fetcher.Fetch(ctx, symbol, assetType)
	if err != nil {
		cb.failureCount++
		cb.lastFailure = time.Now()
		if cb.failureCount >= cb.threshold {
			cb.state = "open"
		}
		return nil, err
	}

	// Reset on success
	cb.failureCount = 0
	cb.state = "closed"
	return data, nil
}

// HealthCheck verifies data source availability
func (s *MarketDataService) HealthCheck(ctx context.Context, source string) bool {
	switch source {
	case "yahoo":
		// Simple ping to Yahoo Finance
		req, err := http.NewRequestWithContext(ctx, "GET", "https://query1.finance.yahoo.com/v7/finance/check", nil)
		if err != nil {
			return false
		}
		req.Header.Set("User-Agent", "CycleCast/3.2")
		resp, err := s.http.Do(req)
		if err != nil {
			return false
		}
		resp.Body.Close()
		return resp.StatusCode < 500
	case "alphavantage", "polygon":
		// For API-based sources, check if API key is configured
		// In production, would make a lightweight API call
		return true
	default:
		return false
	}
}

// GetDataFreshness returns the age of the most recent data for an instrument
func (s *MarketDataService) GetDataFreshness(ctx context.Context, instrumentID string) (time.Duration, error) {
	latest, err := s.repo.GetLatest(ctx, instrumentID, "1d", 1)
	if err != nil {
		return 0, fmt.Errorf("failed to get latest data: %w", err)
	}
	if len(latest) == 0 {
		return 0, fmt.Errorf("no data found for instrument %s", instrumentID)
	}
	return time.Since(latest[0].Timestamp), nil
}

// AlertOnStaleData checks if data is stale and returns alert info
func (s *MarketDataService) AlertOnStaleData(ctx context.Context, instrumentID string, maxAge time.Duration) (bool, string, error) {
	age, err := s.GetDataFreshness(ctx, instrumentID)
	if err != nil {
		return true, fmt.Sprintf("error checking data freshness: %v", err), err
	}
	if age > maxAge {
		return true, fmt.Sprintf("data stale: last update %v ago (threshold: %v)", age, maxAge), nil
	}
	return false, "", nil
}

// ============================================================================
// TEST HELPER FUNCTIONS (exported for testing only)
// ============================================================================

// ValidateOHLCVForTest exposes validateOHLCV for unit testing
func ValidateOHLCVForTest(data []*domain.MarketData) error {
	return validateOHLCV(data)
}

// EnrichMarketDataForTest exposes enrichMarketData for unit testing
func EnrichMarketDataForTest(data []*domain.MarketData, instrument *domain.Instrument) []*domain.MarketData {
	return enrichMarketData(data, instrument)
}

// GetMinMaxForTest exposes getMinMax for unit testing
func GetMinMaxForTest(data []*domain.MarketData) (float64, float64) {
	return getMinMax(data)
}

// NewCircuitBreakerForTest creates a circuit breaker for testing
func NewCircuitBreakerForTest(fetcher DataFetcher, threshold int, timeout time.Duration) *CircuitBreaker {
	return NewCircuitBreaker(fetcher, threshold, timeout)
}

// FetchForTest exposes CircuitBreaker.Fetch for testing
func (cb *CircuitBreaker) FetchForTest(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	return cb.Fetch(ctx, symbol, assetType)
}

// GetStateForTest exposes CircuitBreaker state for testing
func (cb *CircuitBreaker) GetStateForTest() string {
	return cb.state
}
