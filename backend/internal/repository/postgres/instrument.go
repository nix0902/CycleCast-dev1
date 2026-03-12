// Package postgres implements repository interfaces using PostgreSQL
package postgres

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/cyclecast/backend/internal/domain"
	"github.com/cyclecast/backend/internal/repository"
)

// InstrumentRepository implements repository.InstrumentRepository using PostgreSQL
type InstrumentRepository struct {
	pool *pgxpool.Pool
}

// NewInstrumentRepository creates a new instrument repository
func NewInstrumentRepository(pool *pgxpool.Pool) repository.InstrumentRepository {
	return &InstrumentRepository{pool: pool}
}

// GetByID retrieves an instrument by its ID
func (r *InstrumentRepository) GetByID(ctx context.Context, id string) (*domain.Instrument, error) {
	query := `
		SELECT id, symbol, name, exchange, type, currency, tick_size, is_active,
		       proxy_type, regime_change_date, day_close_utc, signal_direction,
		       proxy_list, proxy_weights, fte_threshold, min_signal_distance,
		       created_at, updated_at
		FROM instruments
		WHERE id = $1
	`

	var inst domain.Instrument
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&inst.ID, &inst.Symbol, &inst.Name, &inst.Exchange, &inst.Type,
		&inst.Currency, &inst.TickSize, &inst.IsActive,
		&inst.ProxyType, &inst.RegimeChangeDate, &inst.DayCloseUTC,
		&inst.SignalDirection, &inst.ProxyList, &inst.ProxyWeights,
		&inst.FTEThreshold, &inst.MinSignalDistance,
		&inst.CreatedAt, &inst.UpdatedAt,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("instrument not found: %s", id)
		}
		return nil, fmt.Errorf("failed to query instrument: %w", err)
	}

	return &inst, nil
}

// GetBySymbol retrieves an instrument by its symbol
func (r *InstrumentRepository) GetBySymbol(ctx context.Context, symbol string) (*domain.Instrument, error) {
	query := `
		SELECT id, symbol, name, exchange, type, currency, tick_size, is_active,
		       proxy_type, regime_change_date, day_close_utc, signal_direction,
		       proxy_list, proxy_weights, fte_threshold, min_signal_distance,
		       created_at, updated_at
		FROM instruments
		WHERE symbol = $1
	`

	var inst domain.Instrument
	err := r.pool.QueryRow(ctx, query, symbol).Scan(
		&inst.ID, &inst.Symbol, &inst.Name, &inst.Exchange, &inst.Type,
		&inst.Currency, &inst.TickSize, &inst.IsActive,
		&inst.ProxyType, &inst.RegimeChangeDate, &inst.DayCloseUTC,
		&inst.SignalDirection, &inst.ProxyList, &inst.ProxyWeights,
		&inst.FTEThreshold, &inst.MinSignalDistance,
		&inst.CreatedAt, &inst.UpdatedAt,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("instrument not found: %s", symbol)
		}
		return nil, fmt.Errorf("failed to query instrument: %w", err)
	}

	return &inst, nil
}

// List retrieves all instruments
func (r *InstrumentRepository) List(ctx context.Context, activeOnly bool) ([]*domain.Instrument, error) {
	query := `
		SELECT id, symbol, name, exchange, type, currency, tick_size, is_active,
		       proxy_type, regime_change_date, day_close_utc, signal_direction,
		       proxy_list, proxy_weights, fte_threshold, min_signal_distance,
		       created_at, updated_at
		FROM instruments
	`
	if activeOnly {
		query += " WHERE is_active = true"
	}
	query += " ORDER BY symbol"

	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to query instruments: %w", err)
	}
	defer rows.Close()

	var instruments []*domain.Instrument
	for rows.Next() {
		var inst domain.Instrument
		err := rows.Scan(
			&inst.ID, &inst.Symbol, &inst.Name, &inst.Exchange, &inst.Type,
			&inst.Currency, &inst.TickSize, &inst.IsActive,
			&inst.ProxyType, &inst.RegimeChangeDate, &inst.DayCloseUTC,
			&inst.SignalDirection, &inst.ProxyList, &inst.ProxyWeights,
			&inst.FTEThreshold, &inst.MinSignalDistance,
			&inst.CreatedAt, &inst.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan instrument: %w", err)
		}
		instruments = append(instruments, &inst)
	}

	return instruments, rows.Err()
}

// Create inserts a new instrument
func (r *InstrumentRepository) Create(ctx context.Context, instrument *domain.Instrument) error {
	query := `
		INSERT INTO instruments (
			id, symbol, name, exchange, type, currency, tick_size, is_active,
			proxy_type, regime_change_date, day_close_utc, signal_direction,
			proxy_list, proxy_weights, fte_threshold, min_signal_distance
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
	`

	_, err := r.pool.Exec(ctx, query,
		instrument.ID, instrument.Symbol, instrument.Name, instrument.Exchange,
		instrument.Type, instrument.Currency, instrument.TickSize, instrument.IsActive,
		instrument.ProxyType, instrument.RegimeChangeDate, instrument.DayCloseUTC,
		instrument.SignalDirection, instrument.ProxyList, instrument.ProxyWeights,
		instrument.FTEThreshold, instrument.MinSignalDistance,
	)
	if err != nil {
		return fmt.Errorf("failed to create instrument: %w", err)
	}

	return nil
}

// Update modifies an existing instrument
func (r *InstrumentRepository) Update(ctx context.Context, instrument *domain.Instrument) error {
	query := `
		UPDATE instruments SET
			symbol = $2, name = $3, exchange = $4, type = $5, currency = $6,
			tick_size = $7, is_active = $8, proxy_type = $9,
			regime_change_date = $10, day_close_utc = $11, signal_direction = $12,
			proxy_list = $13, proxy_weights = $14, fte_threshold = $15,
			min_signal_distance = $16, updated_at = NOW()
		WHERE id = $1
	`

	_, err := r.pool.Exec(ctx, query,
		instrument.ID, instrument.Symbol, instrument.Name, instrument.Exchange,
		instrument.Type, instrument.Currency, instrument.TickSize, instrument.IsActive,
		instrument.ProxyType, instrument.RegimeChangeDate, instrument.DayCloseUTC,
		instrument.SignalDirection, instrument.ProxyList, instrument.ProxyWeights,
		instrument.FTEThreshold, instrument.MinSignalDistance,
	)
	if err != nil {
		return fmt.Errorf("failed to update instrument: %w", err)
	}

	return nil
}

// Delete removes an instrument by ID
func (r *InstrumentRepository) Delete(ctx context.Context, id string) error {
	query := `DELETE FROM instruments WHERE id = $1`

	result, err := r.pool.Exec(ctx, query, id)
	if err != nil {
		return fmt.Errorf("failed to delete instrument: %w", err)
	}

	if result.RowsAffected() == 0 {
		return fmt.Errorf("instrument not found: %s", id)
	}

	return nil
}
