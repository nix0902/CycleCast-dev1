# Regime Detection & Adaptive Threshold Module

## Overview

This module implements market regime detection using volatility-based statistical approaches and adaptive threshold calculation for seasonality signal validation. It enhances the FTE (Forecast Theoretical Efficiency) validation by adjusting signal thresholds based on detected market conditions.

## Key Features

### Regime Classification
- **LOW_VOL**: Calm markets with below-average volatility (< 25th percentile)
- **NORMAL_VOL**: Typical market conditions (25th-75th percentile)
- **HIGH_VOL**: Elevated volatility, uncertain conditions (75th-95th percentile)
- **EXTREME_VOL**: Crisis mode, very high volatility (> 95th percentile)

### Adaptive Threshold Formula
```
adaptive_threshold = base_threshold × (1 + λ × (vol_ratio - 1))
```
Where:
- `base_threshold`: Default FTE threshold (default: 0.08)
- `λ (lambda)`: Sensitivity parameter (default: 0.5)
- `vol_ratio`: current_volatility / baseline_volatility
- **Floor**: Threshold cannot drop below 50% of base_threshold

### Regime-Specific Adjustments
| Regime | Multiplier | Effect |
|--------|-----------|--------|
| LOW_VOL | 1.0× | Standard threshold |
| NORMAL_VOL | 1.0× | Standard threshold |
| HIGH_VOL | 1.2× | Require 20% stronger signal |
| EXTREME_VOL | 1.5× | Require 50% stronger signal |

## Quick Start

```python
from quant.seasonality import (
    detect_regime,
    validate_with_regime,
    RegimeConfig,
    RegimeType
)

# Basic usage with default config
prices = [...]  # Your price series
fte_score = 0.10  # Your FTE correlation score

is_valid, result = validate_with_regime(fte_score, prices)

if is_valid:
    print(f"✓ Signal valid in {result.regime.name} regime")
    print(f"  Threshold: {result.regime_adjusted_threshold:.3f}")
    print(f"  Signal strength: {result.get_signal_strength(fte_score):.1%}")
else:
    print(f"✗ Signal rejected (FTE: {fte_score:.3f} < threshold: {result.regime_adjusted_threshold:.3f})")
```

## Configuration

```python
from quant.seasonality import RegimeConfig

config = RegimeConfig(
    # Volatility calculation
    short_window=21,          # Days for current volatility
    long_window=252,          # Days for baseline volatility
    
    # Regime classification percentiles
    low_vol_percentile=0.25,      # Below 25% = LOW
    high_vol_percentile=0.75,     # Above 75% = HIGH
    extreme_vol_percentile=0.95,  # Above 95% = EXTREME
    
    # Adaptive threshold parameters
    base_threshold=0.08,          # Base FTE threshold
    sensitivity_lambda=0.5,       # Volatility sensitivity
    min_threshold_ratio=0.5,      # Floor: 50% of base
    
    # Regime-specific multipliers
    regime_multiplier={
        RegimeType.LOW_VOL: 1.0,
        RegimeType.NORMAL_VOL: 1.0,
        RegimeType.HIGH_VOL: 1.2,
        RegimeType.EXTREME_VOL: 1.5,
    },
    
    # Minimum data requirements
    min_samples=60,             # Min data points for detection
)
```

## API Reference

### Core Functions

#### `detect_regime(prices, config=None) -> RegimeResult`
Detect market regime based on volatility analysis.

**Parameters:**
- `prices`: Price series (list or numpy array)
- `config`: Optional RegimeConfig with parameters

**Returns:** `RegimeResult` dataclass with:
- `regime`: Detected RegimeType
- `current_volatility`, `baseline_volatility`, `volatility_ratio`
- `percentile_rank`: Where current vol falls historically
- `adaptive_threshold`, `regime_adjusted_threshold`
- `confidence`: Confidence in classification (0-1)

#### `validate_with_regime(fte_score, prices, config=None) -> Tuple[bool, RegimeResult]`
Validate FTE score against regime-adjusted threshold.

**Parameters:**
- `fte_score`: Forecast Theoretical Efficiency score
- `prices`: Price series for regime detection
- `config`: Optional configuration

**Returns:** `(is_valid: bool, regime_result: RegimeResult)`

#### `integrate_with_fte(fte_result, prices, config=None) -> dict`
Integrate regime detection with existing FTE validation results.

**Parameters:**
- `fte_result`: Dict from FTE validation (with 'correlation' key)
- `prices`: Price series for regime analysis
- `config`: Optional RegimeConfig

**Returns:** Enhanced result dict with regime information added

### Utility Functions

#### `calculate_realized_volatility(prices, window=21, method='log') -> np.ndarray`
Calculate rolling realized volatility.

#### `calculate_volatility_percentile(current_vol, historical_vols) -> float`
Calculate percentile rank of current volatility.

#### `get_regime_transition_probability(prices, config=None, lookback=50) -> dict`
Estimate probability of regime transitions based on volatility trend.

#### `regime_aware_backtest_signal(fte_scores, prices, config=None, min_consecutive=3) -> dict`
Generate backtest-ready signals with regime-aware validation and consecutive signal filtering.

## Integration with FTE Module

```python
from quant.seasonality import validate_fte, integrate_with_fte

# Run standard FTE validation
fte_result = validate_fte(prices, model, fte_config)

# Enhance with regime awareness
enhanced = integrate_with_fte(fte_result, prices)

# Check regime-validated result
if enhanced['regime_validated']:
    print(f"Signal approved: {enhanced['signal_strength']:.1%} strength")
else:
    print(f"Signal rejected by regime filter")
```

## Backtest Integration Example

```python
from quant.seasonality import regime_aware_backtest_signal

# Run regime-aware backtest analysis
results = regime_aware_backtest_signal(
    fte_scores=my_fte_scores,
    prices=my_prices,
    min_consecutive=3  # Require 3 consecutive valid signals
)

# Analyze results
summary = results['summary']
print(f"Triggered {summary['triggered_signals']} signals")
print(f"Regime distribution: {summary['regime_distribution']}")

# Access individual signal details
for signal in results['signals'][-10:]:  # Last 10 periods
    if signal['trigger_signal']:
        print(f"✓ Signal at {signal['index']}: regime={signal['regime']}, "
              f"fte={signal['fte_score']:.3f}, threshold={signal['threshold']:.3f}")
```

## Performance Notes

- **Volatility calculation**: O(n) with rolling window
- **Regime detection**: O(n) for percentile calculation
- **Memory**: O(n) for storing rolling volatility array
- **Recommendation**: Pre-calculate volatility for repeated regime checks

## Testing

Run tests with:
```bash
python -m pytest quant/seasonality/tests/test_regime.py -v
```

Test coverage includes:
- Volatility calculation methods (log/simple returns)
- Regime classification accuracy across volatility regimes
- Adaptive threshold formula compliance with TZ.md
- Edge cases: insufficient data, NaN handling, extreme ratios
- Integration with FTE validation workflow
- Backtest signal generation with consecutive filtering

## References

- TZ.md §2.3.2: FTE Validation with Adaptive Threshold
- TECHNICAL_SOLUTION.md §4.2-regime: Regime Detection Architecture
- Williams, L. (2018). *The Secrets of Seasonal Trading*

---

**Version**: 1.0.0  
**Author**: CycleCast AI Agent (Qwen 3.5)  
**Last Updated**: 2026-03-14
