# FTE Validation Engine

Forecast Theoretical Efficiency (FTE) validation module for the CycleCast seasonality pipeline.

## Overview

The FTE Validation Engine validates seasonal forecasts against out-of-sample data using:

- **Correlation Metrics**: Pearson, Spearman, and Kendall tau coefficients
- **Adaptive Thresholds**: Volatility-adjusted validation thresholds
- **Rolling Window Analysis**: Time-varying correlation assessment
- **Broken Seasonality Detection**: Identifies when seasonal patterns break down
- **Walk-Forward Validation**: Robust out-of-sample testing methodology

## Installation

No additional dependencies beyond the base seasonality module requirements:

```bash
pip install numpy scipy
```

## Quick Start

```python
import numpy as np
from quant.seasonality import validate_fte, FTEConfig

# Generate sample data
np.random.seed(42)
prices = np.cumsum(np.random.randn(500) * 0.01) + 100
prediction = prices[-100:] + np.random.randn(100) * 0.05

# Validate with default configuration
result = validate_fte(prices, prediction)

print(f"Valid: {result.is_valid}")
print(f"Status: {result.status}")
print(f"Pearson r: {result.pearson_correlation:.3f}")
print(f"Threshold: {result.threshold_used:.3f} ({result.threshold_type})")
print(f"Message: {result.message}")
```

## Configuration

```python
from quant.seasonality import FTEConfig

config = FTEConfig(
    # Train/test split ratio
    train_ratio=0.7,
    
    # Base correlation threshold (default: 0.08 per TZ.md)
    base_threshold=0.08,
    
    # Sensitivity for adaptive threshold adjustment
    sensitivity_lambda=0.5,
    
    # Rolling window size for validation (days)
    rolling_window=21,
    
    # Minimum data points required
    min_data_points=100,
    
    # Volatility lookback periods
    short_vol_window=30,
    long_vol_window=252,
    
    # Threshold for "broken" seasonality detection
    broken_threshold=-0.1
)
```

## Adaptive Threshold Formula

The adaptive threshold adjusts based on realized volatility:

```
threshold = base_threshold × (1 + λ × (current_vol / long_term_vol - 1))
```

Where:
- `λ` = sensitivity_lambda (default: 0.5)
- `current_vol` = 30-day realized volatility
- `long_term_vol` = 252-day realized volatility

The threshold is floored at 50% of the base threshold to prevent over-lenient validation.

## API Reference

### `validate_fte(prices, prediction, config=None) -> FTEResult`

Main validation function.

**Parameters:**
- `prices`: Historical price array (for volatility calculation)
- `prediction`: Forecasted values for validation period
- `config`: Optional FTEConfig instance

**Returns:** `FTEResult` dataclass with:
- `pearson_correlation`, `spearman_correlation`, `kendall_tau`
- `is_valid`: Boolean validation result
- `status`: FTEStatus enum (VALID/INVALID/BROKEN/INSUFFICIENT_DATA)
- `threshold_used`, `threshold_type`
- `p_value`: Statistical significance of Pearson correlation
- `prediction_accuracy`: Direction prediction accuracy
- `rolling_correlations`, `rolling_mean`, `rolling_std`
- `message`: Human-readable summary

### `walk_forward_fte(prices, forecast_func, config=None, steps=12) -> list[FTEResult]`

Performs walk-forward validation with expanding training window.

**Parameters:**
- `prices`: Full historical price series
- `forecast_func`: Function(train_data, horizon) -> prediction array
- `config`: FTE configuration
- `steps`: Number of walk-forward iterations

### `aggregate_fte_results(results) -> dict`

Aggregates multiple FTE results into summary statistics.

**Returns:** Dictionary with:
- `count`, `valid_count`, `valid_ratio`
- `pearson_mean`, `pearson_std`, `pearson_min`, `pearson_max`
- `broken_count`: Number of broken seasonality detections
- `avg_direction_accuracy`: Mean prediction direction accuracy

## Status Enum Values

```python
from quant.seasonality import FTEStatus

FTEStatus.VALID           # Correlation > threshold
FTEStatus.INVALID         # Correlation <= threshold
FTEStatus.BROKEN          # Rolling correlations indicate pattern breakdown
FTEStatus.INSUFFICIENT_DATA  # Not enough data for validation
```

## Integration with Seasonality Pipeline

```python
from quant.seasonality import (
    DetrendPipeline,
    PercentileRankNormalizer,
    validate_fte,
    FTEConfig
)

# 1. Prepare data
detrender = DetrendPipeline(method='stl')
detrended = detrender.fit_transform(prices)

normalizer = PercentileRankNormalizer(mode='global')
normalized = normalizer.fit_transform(detrended)

# 2. Generate seasonal forecast (example: repeat last year's pattern)
forecast = generate_seasonal_forecast(normalized)

# 3. Validate with FTE
result = validate_fte(
    prices=normalized,
    prediction=forecast,
    config=FTEConfig(base_threshold=0.08)
)

# 4. Use result for signal generation
if result.is_valid and result.status == FTEStatus.VALID:
    signal_strength = result.pearson_correlation
    # ... generate trading signal
```

## Testing

Run the test suite:

```bash
# From project root
pytest quant/seasonality/tests/test_fte.py -v

# With coverage
pytest quant/seasonality/tests/test_fte.py --cov=quant.seasonality.fte
```

## Performance Notes

- Correlation calculations: O(n) where n = sample size
- Rolling window: O(n × w) where w = window size
- Adaptive threshold: O(1) with pre-computed volatility
- Walk-forward: O(steps × n) - use sparingly for production

## References

- TZ.md §2.3: Forward Testing Efficiency (FTE) requirements
- Williams, L. (2018). *The Secrets of Seasonal Trading*
- Hyndman, R.J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*

## Changelog

### v1.0.0 (2026-03-14)
- Initial implementation per SEA-003 Definition of Done
- Pearson, Spearman, Kendall correlation metrics
- Adaptive threshold with volatility adjustment
- Rolling window validation with broken pattern detection
- Walk-forward validation framework
- Comprehensive test coverage (20+ test cases)
