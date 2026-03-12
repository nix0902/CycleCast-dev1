// Package repository defines data access interfaces
package repository

import (
	"context"
	"time"

	"github.com/cyclecast/backend/internal/domain"
)

// InstrumentRepository handles instrument data persistence
type InstrumentRepository interface {
	GetByID(ctx context.Context, id string) (*domain.Instrument, error)
	GetBySymbol(ctx context.Context, symbol string) (*domain.Instrument, error)
	List(ctx context.Context, activeOnly bool) ([]*domain.Instrument, error)
	Create(ctx context.Context, instrument *domain.Instrument) error
	Update(ctx context.Context, instrument *domain.Instrument) error
	Delete(ctx context.Context, id string) error
}

// MarketDataRepository handles market data persistence with time-series support
type MarketDataRepository interface {
	// Query historical data
	GetRange(ctx context.Context, instrumentID string, timeframe string, start, end time.Time) ([]*domain.MarketData, error)
	GetLatest(ctx context.Context, instrumentID string, timeframe string, limit int) ([]*domain.MarketData, error)
	GetAligned(ctx context.Context, instrumentID string, targetTime string) ([]*domain.MarketData, error)

	// Write operations
	BulkInsert(ctx context.Context, data []*domain.MarketData) error
	UpdateNormalized(ctx context.Context, instrumentID string, timeframe string, data map[time.Time]float64) error

	// Aggregations
	GetDailyAverage(ctx context.Context, instrumentID string, dayOfYear int, years int) (float64, error)
	GetYearDigitPattern(ctx context.Context, instrumentID string, yearDigit int, timeframe string) ([]*domain.MarketData, error)
}

// COTRepository handles Commitment of Traders data
type COTRepository interface {
	GetByDate(ctx context.Context, instrumentID string, date time.Time) (*domain.COTData, error)
	GetRange(ctx context.Context, instrumentID string, start, end time.Time) ([]*domain.COTData, error)
	GetLatest(ctx context.Context, instrumentID string) (*domain.COTData, error)
	Create(ctx context.Context, data *domain.COTData) error
	BulkInsert(ctx context.Context, data []*domain.COTData) error
}

// SignalRepository handles trading signals
type SignalRepository interface {
	Create(ctx context.Context, signal *domain.Signal) error
	GetActive(ctx context.Context, instrumentID string) ([]*domain.Signal, error)
	GetByType(ctx context.Context, instrumentID, signalType string) ([]*domain.Signal, error)
	Update(ctx context.Context, signal *domain.Signal) error
	ExpireOld(ctx context.Context, before time.Time) (int, error)
}

// BacktestRepository handles backtest results
type BacktestRepository interface {
	Create(ctx context.Context, result *domain.BacktestResult) error
	GetByStrategy(ctx context.Context, strategyName, instrumentID string) ([]*domain.BacktestResult, error)
	GetLatest(ctx context.Context, instrumentID string) (*domain.BacktestResult, error)
	List(ctx context.Context, limit int) ([]*domain.BacktestResult, error)
}

// CacheRepository handles Redis caching operations
type CacheRepository interface {
	Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error
	Get(ctx context.Context, key string, dest interface{}) error
	Delete(ctx context.Context, key string) error
	Exists(ctx context.Context, key string) (bool, error)
}
