# Seasonality Module - Detrending & Normalization

## Overview

This module provides tools for extracting seasonal components from financial time series
by removing trend and normalizing values for comparative analysis.

### Key Components

#### Detrending (`detrend.py`)

1. **STLDecomposition**: Seasonal-Trend decomposition using LOESS
   - Robust to outliers (optional robust fitting)
   - Extracts: trend, seasonal, residual components
   - Configurable seasonal/trend smoothing windows
   
2. **HodrickPrescottFilter**: HP filter for smooth trend extraction
   - Minimizes: Σ(y-τ)² + λΣ(Δ²τ)²
   - Frequency-aware lambda defaults (daily=160000, monthly=14400, etc.)
   - Efficient sparse matrix solver with iterative fallback

3. **DetrendPipeline**: Unified interface for multiple methods
   - Methods: 'stl', 'hp', 'linear', 'difference'
   - Consistent fit/transform API
   - Component extraction helpers

#### Normalization (`normalizer.py`)

1. **PercentileRankNormalizer**: Rank-based normalization [0,1] or [0,100]
   - Robust to outliers and non-normal distributions
   - Supports global or rolling window ranking
   - Approximate inverse transform via quantile interpolation

2. **ZScoreNormalizer**: Standard score normalization (mean=0, std=1)
   - Global or rolling window statistics
   - Optional clipping for extreme values
   - Exact inverse transform

3. **MinMaxNormalizer**: Range-based scaling to [min, max]
   - Customizable target range
   - Optional clipping to training bounds
   - Exact inverse transform

4. **NormalizationPipeline**: Chain multiple normalizers
   - Sequential application of methods
   - Consistent fit/transform API

### Usage Examples

```python
import pandas as pd
from quant.seasonality import (
    STLDecomposition, 
    PercentileRankNormalizer,
    DetrendPipeline
)

# Load your time series
data = pd.read_csv('sp500.csv', index_col='date', parse_dates=True)['close']

# Method 1: Direct STL + Percentile Rank
stl = STLDecomposition(period=252)  # Annual cycle for daily data
result = stl.fit_transform(data)

# Extract seasonal component
seasonal = result['seasonal']

# Normalize for cross-asset comparison
prank = PercentileRankNormalizer(output_range=(0, 100))
normalized_seasonal = prank.fit_transform(seasonal)

# Method 2: Using Pipeline
pipeline = DetrendPipeline(method='stl', period=252)
detrended = pipeline.fit_transform(data)

# Get the detrended series (seasonal + residual)
detrended_series = pipeline.get_seasonal_component() + pipeline.get_residual_component()
```

```python
# Method 3: HP Filter for smoother trend
from quant.seasonality import HodrickPrescottFilter

hp = HodrickPrescottFilter(lamb=160000, freq='daily')
result = hp.fit_transform(data)

# Cyclical component (deseasonalized, detrended)
cycle = result['cycle']
```

```python
# Method 4: Normalization Pipeline for preprocessing
from quant.seasonality import NormalizationPipeline

# Chain: detrend -> percentile rank
prep_pipeline = NormalizationPipeline(
    methods=['prank'],
    prank_range=(0, 100),
    prank_window=63  # Quarterly rolling window
)
normalized = prep_pipeline.fit_transform(data)
```

### Validation Utilities

```python
from quant.seasonality.detrend import validate_detrended_data
from quant.seasonality.normalizer import validate_normalization

# Validate detrending
is_valid, diagnostics = validate_detrended_data(
    original=data.values,
    detrended=detrended_series,
    method='stl'
)

# Validate normalization
is_valid, diag = validate_normalization(
    original=detrended_series,
    normalized=normalized.values,
    method='prank',
    expected_range=(0, 100)
)
```

### Testing

Run integration tests:

```bash
# From project root
pytest quant/seasonality/tests/test_integration.py -v

# With coverage
pytest quant/seasonality/tests/ --cov=quant.seasonality
```

### Parameters Guide

#### STLDecomposition
| Parameter | Default | Description |
|-----------|---------|-------------|
| `period` | *required* | Length of seasonal cycle (e.g., 252 for annual daily) |
| `seasonal` | 7 | LOESS window for seasonal smoothing (odd int ≥ period) |
| `trend` | period+1 | LOESS window for trend smoothing |
| `robust` | True | Use outlier-resistant fitting |
| `inner_iter` | 2 | Inner loop iterations for convergence |
| `outer_iter` | 15 | Outer loop iterations for robust fitting |

#### HodrickPrescottFilter
| Parameter | Default | Description |
|-----------|---------|-------------|
| `lamb` | freq-based | Smoothing parameter (higher = smoother trend) |
| `freq` | 'daily' | Data frequency for default lambda selection |

#### PercentileRankNormalizer
| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_range` | (0, 1) | Target range for normalized values |
| `window` | None | Rolling window size (None = global) |
| `method` | 'average' | Ranking method ('average', 'min', 'max', etc.) |

### References

1. Cleveland, R.B., et al. (1990). "STL: A Seasonal-Trend Decomposition Procedure Based on Loess." *Journal of Official Statistics*.

2. Hodrick, R.J., & Prescott, E.C. (1997). "Postwar U.S. Business Cycles: An Empirical Investigation." *Journal of Money, Credit and Banking*.

3. Williams, L. (2023). *The New Commodity Trading Systems and Methods*. CycleCast Technical Documentation.

### See Also

- `docs/TZ.md#3.4-seasonality` - Technical specification
- `docs/TECHNICAL_SOLUTION.md#4.2-seasonality` - Implementation details
- `quant/qspectrum/` - Spectral analysis for cycle detection
- `quant/phenom/` - Phenomenological pattern matching
