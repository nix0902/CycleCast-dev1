// Package domain contains core business entities and interfaces
package domain

import (
	"time"
)

// Instrument represents a financial instrument
type Instrument struct {
	ID              string          `json:"id"`
	Symbol          string          `json:"symbol"`
	Name            string          `json:"name"`
	Exchange        string          `json:"exchange"`
	Type            string          `json:"type"` // stock, futures, forex, crypto
	Currency        string          `json:"currency"`
	TickSize        float64         `json:"tick_size"`
	IsActive        bool            `json:"is_active"`
	CreatedAt       time.Time       `json:"created_at"`
	UpdatedAt       time.Time       `json:"updated_at"`

	// Crypto/GBTC adaptation fields
	ProxyType        string         `json:"proxy_type,omitempty"`
	RegimeChangeDate *time.Time     `json:"regime_change_date,omitempty"`
	DayCloseUTC      string         `json:"day_close_utc,omitempty"`
	SignalDirection  int8           `json:"signal_direction,omitempty"` // 1 or -1
	ProxyList        []string       `json:"proxy_list,omitempty"`
	ProxyWeights     map[string]float64 `json:"proxy_weights,omitempty"`
	FTEThreshold     float64        `json:"fte_threshold,omitempty"`
	MinSignalDistance int           `json:"min_signal_distance,omitempty"`
}

// MarketData represents OHLCV market data point
type MarketData struct {
	InstrumentID string    `json:"instrument_id"`
	Timestamp    time.Time `json:"timestamp"`
	Timeframe    string    `json:"timeframe"` // 1m, 5m, 1h, 1d, 1w, 1M
	Open         float64   `json:"open"`
	High         float64   `json:"high"`
	Low          float64   `json:"low"`
	Close        float64   `json:"close"`
	Volume       int64     `json:"volume"`

	// Computed fields
	AdjustedClose   float64 `json:"adjusted_close,omitempty"`
	NormalizedClose float64 `json:"normalized_close,omitempty"`
	YearDigit       int     `json:"year_digit,omitempty"`
	DetrendedClose  float64 `json:"detrended_close,omitempty"`
	DayCloseUTC     string  `json:"day_close_utc,omitempty"`
}

// COTData represents Commitment of Traders report data
type COTData struct {
	ID             string    `json:"id"`
	InstrumentID   string    `json:"instrument_id"`
	ReportDate     time.Time `json:"report_date"`

	// Futures positions
	CommercialsLong  int64 `json:"commercials_long"`
	CommercialsShort int64 `json:"commercials_short"`
	CommercialsNet   int64 `json:"commercials_net"`
	LargeSpecsLong   int64 `json:"large_specs_long"`
	LargeSpecsShort  int64 `json:"large_specs_short"`
	SmallSpecsLong   int64 `json:"small_specs_long"`
	SmallSpecsShort  int64 `json:"small_specs_short"`

	// Trusts/ETF (GBTC)
	Premium     *float64 `json:"premium,omitempty"`
	NAV         *float64 `json:"nav,omitempty"`

	// Indices
	CommercialIndex *float64 `json:"commercial_index,omitempty"`
	IsExtreme       bool     `json:"is_extreme"`
	SignalType      string   `json:"signal_type,omitempty"`
}

// Signal represents a trading signal
type Signal struct {
	ID              string    `json:"id"`
	InstrumentID    string    `json:"instrument_id"`
	SignalType      string    `json:"signal_type"` // BUY, SELL, HOLD
	Strength        float64   `json:"strength"`    // 0.0 to 1.0
	InitialStrength float64   `json:"initial_strength"`
	Timestamp       time.Time `json:"timestamp"`
	ExpiryDate      *time.Time `json:"expiry_date,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// BacktestResult represents backtesting metrics
type BacktestResult struct {
	ID             string    `json:"id"`
	StrategyName   string    `json:"strategy_name"`
	InstrumentID   string    `json:"instrument_id"`
	StartDate      time.Time `json:"start_date"`
	EndDate        time.Time `json:"end_date"`
	IsInSample     bool      `json:"is_in_sample"`

	// Metrics
	TotalReturn   float64 `json:"total_return"`
	CAGR          float64 `json:"cagr"`
	SharpeRatio   float64 `json:"sharpe_ratio"`
	MaxDrawdown   float64 `json:"max_drawdown"`
	WinRate       float64 `json:"win_rate"`
	ProfitFactor  float64 `json:"profit_factor"`
	TotalTrades   int     `json:"total_trades"`

	// Statistics
	PValue           float64  `json:"p_value"`
	BootstrapCILower *float64 `json:"bootstrap_ci_lower,omitempty"`
	BootstrapCIUpper *float64 `json:"bootstrap_ci_upper,omitempty"`

	// Equity curve (serialized)
	EquityCurve   []float64 `json:"equity_curve,omitempty"`
	CalculatedAt  time.Time `json:"calculated_at"`
}

// AnnualCycleResult represents annual seasonality analysis
type AnnualCycleResult struct {
	Cycle      map[int]float64 `json:"cycle"`       // day of year -> normalized value
	Confidence map[int]float64 `json:"confidence"`  // day of year -> confidence level
	YearsUsed  int             `json:"years_used"`
	IsValid    bool            `json:"is_valid"`
}

// Cycle represents a detected market cycle
type Cycle struct {
	Period     int     `json:"period"`      // in days
	Amplitude  float64 `json:"amplitude"`
	Phase      float64 `json:"phase"`
	Energy     float64 `json:"energy"`
	Significance float64 `json:"significance"`
}

// CompositeLineResult represents the composite line signal
type CompositeLineResult struct {
	Value       float64   `json:"value"`
	Derivative  float64   `json:"derivative"`
	Signal      string    `json:"signal"` // BUY, SELL, NEUTRAL
	Confidence  float64   `json:"confidence"`
	Cycles      []Cycle   `json:"cycles"`
	Timestamp   time.Time `json:"timestamp"`
}
