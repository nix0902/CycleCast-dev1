// Package impl_test contains tests for service implementations
package impl_test

import (
	"context"
	"testing"
	"time"

	"github.com/cyclecast/backend/internal/domain"
	"github.com/cyclecast/backend/internal/service/impl"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// MockMarketDataRepository implements repository.MarketDataRepository for testing
type MockMarketDataRepository struct {
	mock.Mock
}

func (m *MockMarketDataRepository) GetRange(ctx context.Context, instrumentID string, timeframe string, start, end time.Time) ([]*domain.MarketData, error) {
	args := m.Called(ctx, instrumentID, timeframe, start, end)
	return args.Get(0).([]*domain.MarketData), args.Error(1)
}

func (m *MockMarketDataRepository) GetLatest(ctx context.Context, instrumentID string, timeframe string, limit int) ([]*domain.MarketData, error) {
	args := m.Called(ctx, instrumentID, timeframe, limit)
	return args.Get(0).([]*domain.MarketData), args.Error(1)
}

func (m *MockMarketDataRepository) GetAligned(ctx context.Context, instrumentID string, targetTime string) ([]*domain.MarketData, error) {
	args := m.Called(ctx, instrumentID, targetTime)
	return args.Get(0).([]*domain.MarketData), args.Error(1)
}

func (m *MockMarketDataRepository) BulkInsert(ctx context.Context, data []*domain.MarketData) error {
	args := m.Called(ctx, data)
	return args.Error(0)
}

func (m *MockMarketDataRepository) UpdateNormalized(ctx context.Context, instrumentID string, timeframe string, data map[time.Time]float64) error {
	args := m.Called(ctx, instrumentID, timeframe, data)
	return args.Error(0)
}

func (m *MockMarketDataRepository) GetDailyAverage(ctx context.Context, instrumentID string, dayOfYear int, years int) (float64, error) {
	args := m.Called(ctx, instrumentID, dayOfYear, years)
	return args.Get(0).(float64), args.Error(1)
}

func (m *MockMarketDataRepository) GetYearDigitPattern(ctx context.Context, instrumentID string, yearDigit int, timeframe string) ([]*domain.MarketData, error) {
	args := m.Called(ctx, instrumentID, yearDigit, timeframe)
	return args.Get(0).([]*domain.MarketData), args.Error(1)
}

// MockCacheRepository implements repository.CacheRepository for testing
type MockCacheRepository struct {
	mock.Mock
}

func (m *MockCacheRepository) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	args := m.Called(ctx, key, value, ttl)
	return args.Error(0)
}

func (m *MockCacheRepository) Get(ctx context.Context, key string, dest interface{}) error {
	args := m.Called(ctx, key, dest)
	return args.Error(0)
}

func (m *MockCacheRepository) Delete(ctx context.Context, key string) error {
	args := m.Called(ctx, key)
	return args.Error(0)
}

func (m *MockCacheRepository) Exists(ctx context.Context, key string) (bool, error) {
	args := m.Called(ctx, key)
	return args.Bool(0), args.Error(1)
}

// TestGetHistoricalData_CacheHit tests that cached data is returned
func TestGetHistoricalData_CacheHit(t *testing.T) {
	mockRepo := new(MockMarketDataRepository)
	mockCache := new(MockCacheRepository)
	svc := impl.NewMarketDataService(mockRepo, mockCache)

	ctx := context.Background()
	instrumentID := "test-instrument"
	timeframe := "1d"
	start := "2024-01-01T00:00:00Z"
	end := "2024-12-31T23:59:59Z"

	expectedData := []*domain.MarketData{
		{InstrumentID: instrumentID, Timestamp: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC), Close: 100},
	}

	cacheKey := "market_data:test-instrument:1d:2024-01-01T00:00:00Z:2024-12-31T23:59:59Z"
	mockCache.On("Get", ctx, cacheKey, mock.Anything).Return(nil).Run(func(args mock.Arguments) {
		// Simulate cache hit by populating dest
		dest := args.Get(2).(*[]*domain.MarketData)
		*dest = expectedData
	})

	data, err := svc.GetHistoricalData(ctx, instrumentID, timeframe, start, end)

	assert.NoError(t, err)
	assert.Equal(t, expectedData, data)
	mockCache.AssertExpectations(t)
	mockRepo.AssertNotCalled(t, "GetRange")
}

// TestGetHistoricalData_CacheMiss tests fallback to repository when cache misses
func TestGetHistoricalData_CacheMiss(t *testing.T) {
	mockRepo := new(MockMarketDataRepository)
	mockCache := new(MockCacheRepository)
	svc := impl.NewMarketDataService(mockRepo, mockCache)

	ctx := context.Background()
	instrumentID := "test-instrument"
	timeframe := "1d"
	start := "2024-01-01T00:00:00Z"
	end := "2024-12-31T23:59:59Z"
	startTime, _ := time.Parse(time.RFC3339, start)
	endTime, _ := time.Parse(time.RFC3339, end)

	expectedData := []*domain.MarketData{
		{InstrumentID: instrumentID, Timestamp: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC), Close: 100},
	}

	cacheKey := "market_data:test-instrument:1d:2024-01-01T00:00:00Z:2024-12-31T23:59:59Z"
	mockCache.On("Get", ctx, cacheKey, mock.Anything).Return(assert.AnError)
	mockRepo.On("GetRange", ctx, instrumentID, timeframe, startTime, endTime).Return(expectedData, nil)
	mockCache.On("Set", ctx, cacheKey, expectedData, 1*time.Hour).Return(nil)

	data, err := svc.GetHistoricalData(ctx, instrumentID, timeframe, start, end)

	assert.NoError(t, err)
	assert.Equal(t, expectedData, data)
	mockCache.AssertExpectations(t)
	mockRepo.AssertExpectations(t)
}

// TestValidateOHLCV_ValidData tests that valid OHLCV data passes validation
func TestValidateOHLCV_ValidData(t *testing.T) {
	data := []*domain.MarketData{
		{Open: 100, High: 110, Low: 95, Close: 105, Volume: 1000},
		{Open: 105, High: 115, Low: 100, Close: 110, Volume: 2000},
	}

	err := impl.ValidateOHLCVForTest(data)
	assert.NoError(t, err)
}

// TestValidateOHLCV_InvalidHighLow tests rejection when high < low
func TestValidateOHLCV_InvalidHighLow(t *testing.T) {
	data := []*domain.MarketData{
		{Open: 100, High: 90, Low: 95, Close: 105, Volume: 1000}, // high < low
	}

	err := impl.ValidateOHLCVForTest(data)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "high")
}

// TestValidateOHLCV_InvalidOpen tests rejection when open outside [low, high]
func TestValidateOHLCV_InvalidOpen(t *testing.T) {
	data := []*domain.MarketData{
		{Open: 80, High: 110, Low: 95, Close: 105, Volume: 1000}, // open < low
	}

	err := impl.ValidateOHLCVForTest(data)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "open")
}

// TestValidateOHLCV_NegativeVolume tests rejection of negative volume
func TestValidateOHLCV_NegativeVolume(t *testing.T) {
	data := []*domain.MarketData{
		{Open: 100, High: 110, Low: 95, Close: 105, Volume: -100},
	}

	err := impl.ValidateOHLCVForTest(data)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "volume")
}

// TestValidateOHLCV_NonPositiveClose tests rejection of non-positive close
func TestValidateOHLCV_NonPositiveClose(t *testing.T) {
	data := []*domain.MarketData{
		{Open: 100, High: 110, Low: 95, Close: 0, Volume: 1000},
	}

	err := impl.ValidateOHLCVForTest(data)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "close")
}

// TestEnrichMarketData_AddsComputedFields tests that enrichMarketData adds computed fields
func TestEnrichMarketData_AddsComputedFields(t *testing.T) {
	instrument := &domain.Instrument{
		Type:       "crypto",
		DayCloseUTC: "20:00:00",
	}
	data := []*domain.MarketData{
		{InstrumentID: "test", Timestamp: time.Date(2024, 3, 15, 0, 0, 0, 0, time.UTC), Close: 100},
	}

	enriched := impl.EnrichMarketDataForTest(data, instrument)

	assert.Len(t, enriched, 1)
	assert.Equal(t, 100.0, enriched[0].AdjustedClose)
	assert.Equal(t, 4, enriched[0].YearDigit) // 2024 % 10 = 4
	assert.Equal(t, "20:00:00", enriched[0].DayCloseUTC)
}

// TestEnrichMarketData_StockNoDayCloseUTC tests that stock instruments don't get DayCloseUTC
func TestEnrichMarketData_StockNoDayCloseUTC(t *testing.T) {
	instrument := &domain.Instrument{Type: "stock"}
	data := []*domain.MarketData{
		{InstrumentID: "test", Timestamp: time.Date(2024, 3, 15, 0, 0, 0, 0, time.UTC), Close: 100},
	}

	enriched := impl.EnrichMarketDataForTest(data, instrument)

	assert.Equal(t, "", enriched[0].DayCloseUTC)
}

// TestGetMinMax_CalculatesCorrectRange tests min/max calculation
func TestGetMinMax_CalculatesCorrectRange(t *testing.T) {
	data := []*domain.MarketData{
		{Close: 100}, {Close: 150}, {Close: 75}, {Close: 200},
	}

	min, max := impl.GetMinMaxForTest(data)

	assert.Equal(t, 75.0, min)
	assert.Equal(t, 200.0, max)
}

// TestGetMinMax_EmptyData tests edge case of empty data slice
func TestGetMinMax_EmptyData(t *testing.T) {
	data := []*domain.MarketData{}

	min, max := impl.GetMinMaxForTest(data)

	assert.Equal(t, 0.0, min)
	assert.Equal(t, 0.0, max)
}

// TestCircuitBreaker_ClosedState tests normal operation when circuit is closed
func TestCircuitBreaker_ClosedState(t *testing.T) {
	mockFetcher := new(MockDataFetcher)
	cb := impl.NewCircuitBreakerForTest(mockFetcher, 3, 1*time.Minute)

	ctx := context.Background()
	expectedData := []*domain.MarketData{{Close: 100}}

	mockFetcher.On("Fetch", ctx, "TEST", "stock").Return(expectedData, nil)

	data, err := cb.FetchForTest(ctx, "TEST", "stock")

	assert.NoError(t, err)
	assert.Equal(t, expectedData, data)
	assert.Equal(t, "closed", cb.GetStateForTest())
	mockFetcher.AssertExpectations(t)
}

// TestCircuitBreaker_OpenState tests that circuit opens after threshold failures
func TestCircuitBreaker_OpenState(t *testing.T) {
	mockFetcher := new(MockDataFetcher)
	cb := impl.NewCircuitBreakerForTest(mockFetcher, 3, 1*time.Minute)

	ctx := context.Background()

	// Simulate 3 failures to open circuit
	for i := 0; i < 3; i++ {
		mockFetcher.On("Fetch", ctx, "TEST", "stock").Return(nil, assert.AnError)
		_, err := cb.FetchForTest(ctx, "TEST", "stock")
		assert.Error(t, err)
	}

	assert.Equal(t, "open", cb.GetStateForTest())
	mockFetcher.AssertExpectations(t)
}

// TestCircuitBreaker_HalfOpenState tests recovery after timeout
func TestCircuitBreaker_HalfOpenState(t *testing.T) {
	mockFetcher := new(MockDataFetcher)
	cb := impl.NewCircuitBreakerForTest(mockFetcher, 1, 100*time.Millisecond)

	ctx := context.Background()

	// Open the circuit
	mockFetcher.On("Fetch", ctx, "TEST", "stock").Return(nil, assert.AnError)
	cb.FetchForTest(ctx, "TEST", "stock")
	assert.Equal(t, "open", cb.GetStateForTest())

	// Wait for timeout
	time.Sleep(150 * time.Millisecond)

	// Next call should transition to half-open
	mockFetcher.On("Fetch", ctx, "TEST", "stock").Return([]*domain.MarketData{{Close: 100}}, nil)
	data, err := cb.FetchForTest(ctx, "TEST", "stock")

	assert.NoError(t, err)
	assert.Equal(t, "closed", cb.GetStateForTest()) // Should reset to closed on success
	assert.Equal(t, 100.0, data[0].Close)
	mockFetcher.AssertExpectations(t)
}

// MockDataFetcher for circuit breaker tests
type MockDataFetcher struct {
	mock.Mock
}

func (m *MockDataFetcher) Fetch(ctx context.Context, symbol, assetType string) ([]*domain.MarketData, error) {
	args := m.Called(ctx, symbol, assetType)
	return args.Get(0).([]*domain.MarketData), args.Error(1)
}

// BenchmarkGetHistoricalData_CacheHit benchmarks cache hit performance
func BenchmarkGetHistoricalData_CacheHit(b *testing.B) {
	mockRepo := new(MockMarketDataRepository)
	mockCache := new(MockCacheRepository)
	svc := impl.NewMarketDataService(mockRepo, mockCache)

	ctx := context.Background()
	testData := make([]*domain.MarketData, 1000)
	for i := range testData {
		testData[i] = &domain.MarketData{Close: float64(100 + i)}
	}

	cacheKey := "market_data:test:1d:2024-01-01:2024-12-31"
	mockCache.On("Get", ctx, cacheKey, mock.Anything).Return(nil).Run(func(args mock.Arguments) {
		dest := args.Get(2).(*[]*domain.MarketData)
		*dest = testData
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = svc.GetHistoricalData(ctx, "test", "1d", "2024-01-01T00:00:00Z", "2024-12-31T23:59:59Z")
	}
}

// BenchmarkValidateOHLCV benchmarks data validation performance
func BenchmarkValidateOHLCV(b *testing.B) {
	data := make([]*domain.MarketData, 10000)
	for i := range data {
		data[i] = &domain.MarketData{
			Open:   100,
			High:   110,
			Low:    95,
			Close:  105,
			Volume: 1000,
		}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = impl.ValidateOHLCVForTest(data)
	}
}
