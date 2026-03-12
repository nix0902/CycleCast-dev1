// Package service defines business logic interfaces
package service

import (
	"context"

	"github.com/cyclecast/backend/internal/domain"
)

// MarketDataService handles market data operations
type MarketDataService interface {
	ImportData(ctx context.Context, instrumentID string, source string) error
	GetHistoricalData(ctx context.Context, instrumentID, timeframe string, start, end string) ([]*domain.MarketData, error)
	GetAlignedData(ctx context.Context, instrumentID, targetTime string) ([]*domain.MarketData, error)
	NormalizeData(ctx context.Context, instrumentID string, timeframe string) error
}

// AnnualCycleService handles seasonality analysis
type AnnualCycleService interface {
	Calculate(ctx context.Context, instrumentID string, minYears int) (*domain.AnnualCycleResult, error)
	ValidateFTE(ctx context.Context, instrumentID string, result *domain.AnnualCycleResult) (*domain.AnnualCycleResult, error)
	GetCurrentSignal(ctx context.Context, instrumentID string) (*domain.Signal, error)
}

// CycleAnalysisService handles spectral analysis via Python service
type CycleAnalysisService interface {
	AnalyzeSpectrum(ctx context.Context, instrumentID string, data []*domain.MarketData) ([]*domain.Cycle, error)
	GetDominantCycles(ctx context.Context, instrumentID string) ([]*domain.Cycle, error)
}

// CompositeLineService handles composite line generation
type CompositeLineService interface {
	Generate(ctx context.Context, instrumentID string, cycles []*domain.Cycle) (*domain.CompositeLineResult, error)
	GetSignal(ctx context.Context, instrumentID string) (*domain.Signal, error)
}

// PhenomenologicalService handles historical analogy search via Python DTW
type PhenomenologicalService interface {
	FindAnalogies(ctx context.Context, instrumentID string, lookbackDays int) ([]*domain.Signal, error)
	ProjectContinuation(ctx context.Context, instrumentID string, analogies []*domain.Signal) (*domain.Signal, error)
}

// COTService handles Commitment of Traders analysis
type COTService interface {
	GetLatest(ctx context.Context, instrumentID string) (*domain.COTData, error)
	AnalyzeExtremes(ctx context.Context, instrumentID string) (*domain.Signal, error)
	GetProxySignal(ctx context.Context, instrumentID string) (*domain.Signal, error) // For crypto via GBTC/ETF
}

// SignalAggregationService combines signals from multiple sources
type SignalAggregationService interface {
	Aggregate(ctx context.Context, instrumentID string) (*domain.Signal, error)
	CalculateWeightedSignal(ctx context.Context, signals map[string]*domain.Signal) *domain.Signal
}

// RiskManagementService handles position sizing and risk calculations
type RiskManagementService interface {
	CalculatePositionSize(ctx context.Context, instrumentID string, signal *domain.Signal, accountValue float64) (float64, error)
	CalculateStopLoss(ctx context.Context, instrumentID string, entryPrice float64) (float64, error)
	ValidateRisk(ctx context.Context, instrumentID string, positionSize float64) error
}

// BacktestService handles strategy backtesting
type BacktestService interface {
	Run(ctx context.Context, strategyName, instrumentID string, config map[string]interface{}) (*domain.BacktestResult, error)
	ValidateWithBootstrap(ctx context.Context, result *domain.BacktestResult) (*domain.BacktestResult, error)
}
