"""
Forecast Theoretical Efficiency (FTE) Validation Engine

Implements validation of seasonal forecasts against out-of-sample data
using correlation metrics, rolling window analysis, and adaptive thresholds.

Based on Larry Williams methodology and CycleCast v3.2 specifications.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence

import numpy as np
from scipy import stats


class FTEStatus(Enum):
    """FTE validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    BROKEN = "broken"  # Seasonality pattern has broken
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class FTEConfig:
    """Configuration for FTE validation."""
    # Train/test split ratio (0.0-1.0)
    train_ratio: float = 0.7
    
    # Base threshold for correlation (default: 0.08 per TZ.md)
    base_threshold: float = 0.08
    
    # Sensitivity for adaptive threshold adjustment
    sensitivity_lambda: float = 0.5
    
    # Rolling window size for validation (in days)
    rolling_window: int = 21
    
    # Minimum data points required
    min_data_points: int = 100
    
    # Volatility lookback periods for adaptive threshold
    short_vol_window: int = 30
    long_vol_window: int = 252
    
    # Minimum correlation for "broken" seasonality detection
    broken_threshold: float = -0.1


@dataclass
class FTEResult:
    """Result of FTE validation."""
    # Correlation metrics (required fields first)
    pearson_correlation: float
    spearman_correlation: float
    is_valid: bool
    status: FTEStatus
    threshold_used: float
    threshold_type: str  # "base" or "adaptive"
    
    # Optional fields with defaults
    kendall_tau: Optional[float] = None
    p_value: Optional[float] = None
    sample_size: int = 0
    prediction_accuracy: float = 0.0  # Direction accuracy
    
    # Rolling window results (if applicable)
    rolling_correlations: Optional[Sequence[float]] = None
    rolling_mean: Optional[float] = None
    rolling_std: Optional[float] = None
    
    # Metadata
    train_size: int = 0
    test_size: int = 0
    message: str = ""
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.pearson_correlation is not None:
            self.pearson_correlation = float(self.pearson_correlation)
        if self.spearman_correlation is not None:
            self.spearman_correlation = float(self.spearman_correlation)
        if self.kendall_tau is not None:
            self.kendall_tau = float(self.kendall_tau)


def calculate_realized_volatility(
    prices: np.ndarray, 
    window: int,
    method: str = "log_return"
) -> float:
    """
    Calculate realized volatility over a rolling window.
    
    Args:
        prices: Array of price data
        window: Lookback window size
        method: Volatility calculation method ("log_return" or "simple")
    
    Returns:
        Annualized volatility estimate
    """
    if len(prices) < window + 1:
        return np.nan
    
    # Calculate returns
    if method == "log_return":
        returns = np.diff(np.log(prices[-window:]))
    else:
        returns = np.diff(prices[-window:]) / prices[-window:-1]
    
    # Annualize (assuming daily data)
    return np.std(returns, ddof=1) * np.sqrt(252)


def calculate_adaptive_threshold(
    prices: np.ndarray,
    config: FTEConfig
) -> float:
    """
    Calculate adaptive threshold based on realized volatility.
    
    Higher volatility -> lower threshold (more lenient validation)
    Lower volatility -> higher threshold (stricter validation)
    
    Formula:
        threshold = base_threshold * (1 + lambda * (current_vol / long_term_vol - 1))
    """
    if len(prices) < config.long_vol_window + 1:
        return config.base_threshold
    
    # Calculate volatilities
    current_vol = calculate_realized_volatility(
        prices, config.short_vol_window
    )
    long_term_vol = calculate_realized_volatility(
        prices, config.long_vol_window
    )
    
    if np.isnan(current_vol) or np.isnan(long_term_vol) or long_term_vol == 0:
        return config.base_threshold
    
    # Calculate adaptive adjustment
    vol_ratio = current_vol / long_term_vol
    threshold = config.base_threshold * (
        1 + config.sensitivity_lambda * (vol_ratio - 1)
    )
    
    # Enforce minimum threshold (50% of base)
    return max(threshold, config.base_threshold * 0.5)


def pearson_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Calculate Pearson correlation coefficient with NaN handling."""
    # Remove NaN values
    mask = ~np.isnan(x) & ~np.isnan(y)
    if np.sum(mask) < 3:
        return np.nan
    
    corr, _ = stats.pearsonr(x[mask], y[mask])
    return float(corr)


def spearman_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Calculate Spearman rank correlation coefficient with NaN handling."""
    mask = ~np.isnan(x) & ~np.isnan(y)
    if np.sum(mask) < 3:
        return np.nan
    
    corr, _ = stats.spearmanr(x[mask], y[mask])
    return float(corr)


def kendall_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Calculate Kendall tau correlation coefficient with NaN handling."""
    mask = ~np.isnan(x) & ~np.isnan(y)
    if np.sum(mask) < 3:
        return np.nan
    
    tau, _ = stats.kendalltau(x[mask], y[mask])
    return float(tau)


def calculate_direction_accuracy(
    prediction: np.ndarray,
    actual: np.ndarray
) -> float:
    """
    Calculate prediction direction accuracy.
    
    Returns the fraction of time steps where prediction
    and actual move in the same direction.
    """
    if len(prediction) != len(actual):
        return 0.0
    
    # Calculate direction changes
    pred_direction = np.sign(np.diff(prediction))
    actual_direction = np.sign(np.diff(actual))
    
    # Count matches (excluding zeros)
    mask = (pred_direction != 0) & (actual_direction != 0)
    if np.sum(mask) == 0:
        return 0.0
    
    matches = np.sum(pred_direction[mask] == actual_direction[mask])
    return matches / np.sum(mask)


def rolling_window_validation(
    prediction: np.ndarray,
    actual: np.ndarray,
    window_size: int,
    correlation_func: callable = pearson_correlation
) -> tuple[np.ndarray, float, float]:
    """
    Perform rolling window correlation validation.
    
    Args:
        prediction: Predicted values
        actual: Actual observed values
        window_size: Size of rolling window
        correlation_func: Correlation function to use
    
    Returns:
        Tuple of (rolling_correlations, mean, std)
    """
    if len(prediction) != len(actual):
        raise ValueError("Prediction and actual must have same length")
    
    if len(prediction) < window_size:
        return np.array([]), np.nan, np.nan
    
    rolling_corrs = []
    
    for i in range(len(prediction) - window_size + 1):
        start, end = i, i + window_size
        corr = correlation_func(
            prediction[start:end],
            actual[start:end]
        )
        rolling_corrs.append(corr)
    
    rolling_arr = np.array(rolling_corrs)
    
    # Calculate statistics (excluding NaN)
    valid_corrs = rolling_arr[~np.isnan(rolling_arr)]
    if len(valid_corrs) == 0:
        return rolling_arr, np.nan, np.nan
    
    return rolling_arr, np.mean(valid_corrs), np.std(valid_corrs)


def detect_broken_seasonality(
    correlations: Sequence[float],
    broken_threshold: float = -0.1,
    consecutive_count: int = 3
) -> bool:
    """
    Detect if seasonality pattern has "broken".
    
    A broken pattern is detected when correlation drops
    below threshold for consecutive periods.
    
    Args:
        correlations: Sequence of correlation values
        broken_threshold: Threshold for "broken" detection
        consecutive_count: Number of consecutive low values required
    
    Returns:
        True if broken pattern detected
    """
    consecutive = 0
    for corr in correlations:
        if corr <= broken_threshold:
            consecutive += 1
            if consecutive >= consecutive_count:
                return True
        else:
            consecutive = 0
    return False


def validate_fte(
    prices: np.ndarray,
    prediction: np.ndarray,
    config: Optional[FTEConfig] = None
) -> FTEResult:
    """
    Main FTE validation function.
    
    Validates seasonal forecast against out-of-sample data using:
    - Pearson and Spearman correlation metrics
    - Rolling window analysis
    - Adaptive threshold based on volatility
    - Broken seasonality detection
    
    Args:
        prices: Historical price data (for volatility calculation)
        prediction: Predicted values for test period
        config: FTE configuration (uses defaults if None)
    
    Returns:
        FTEResult with validation metrics and status
    """
    if config is None:
        config = FTEConfig()
    
    # Input validation
    if len(prices) < config.min_data_points:
        return FTEResult(
            pearson_correlation=np.nan,
            spearman_correlation=np.nan,
            is_valid=False,
            status=FTEStatus.INSUFFICIENT_DATA,
            threshold_used=config.base_threshold,
            threshold_type="base",
            sample_size=len(prices),
            message=f"Insufficient data: {len(prices)} < {config.min_data_points}"
        )
    
    if len(prediction) < config.rolling_window:
        return FTEResult(
            pearson_correlation=np.nan,
            spearman_correlation=np.nan,
            is_valid=False,
            status=FTEStatus.INSUFFICIENT_DATA,
            threshold_used=config.base_threshold,
            threshold_type="base",
            sample_size=len(prediction),
            message=f"Prediction too short for validation: {len(prediction)}"
        )
    
    # Determine actual values (use prices for test period)
    # If prediction is shorter than prices, assume it's for the end period
    if len(prediction) <= len(prices):
        actual = prices[-len(prediction):]
    else:
        # If prediction extends beyond prices, truncate
        actual = prices
        prediction = prediction[:len(prices)]
    
    # Calculate correlation metrics
    pearson = pearson_correlation(prediction, actual)
    spearman = spearman_correlation(prediction, actual)
    kendall = kendall_correlation(prediction, actual)
    
    # Calculate p-value for Pearson correlation
    p_value = None
    if not np.isnan(pearson) and len(prediction) >= 3:
        try:
            _, p_value = stats.pearsonr(prediction, actual)
        except Exception:
            p_value = None
    
    # Calculate adaptive threshold
    threshold = calculate_adaptive_threshold(prices, config)
    threshold_type = "adaptive" if threshold != config.base_threshold else "base"
    
    # Determine validity
    correlation_metric = pearson if not np.isnan(pearson) else spearman
    is_valid = not np.isnan(correlation_metric) and correlation_metric > threshold
    
    # Rolling window validation
    rolling_corrs, rolling_mean, rolling_std = rolling_window_validation(
        prediction, actual, config.rolling_window
    )
    
    # Detect broken seasonality
    is_broken = False
    if len(rolling_corrs) > 0:
        is_broken = detect_broken_seasonality(
            rolling_corrs, 
            config.broken_threshold
        )
    
    # Determine final status
    if is_broken:
        status = FTEStatus.BROKEN
        is_valid = False
    elif is_valid:
        status = FTEStatus.VALID
    else:
        status = FTEStatus.INVALID
    
    # Calculate direction accuracy
    direction_acc = calculate_direction_accuracy(prediction, actual)
    
    # Generate message
    if status == FTEStatus.VALID:
        message = f"FTE valid: r={pearson:.3f} > threshold={threshold:.3f}"
    elif status == FTEStatus.BROKEN:
        message = f"Seasonality broken: rolling mean={rolling_mean:.3f} < {config.broken_threshold}"
    elif status == FTEStatus.INVALID:
        message = f"FTE invalid: r={pearson:.3f} <= threshold={threshold:.3f}"
    else:
        message = f"Insufficient data for validation"
    
    return FTEResult(
        pearson_correlation=pearson,
        spearman_correlation=spearman,
        kendall_tau=kendall,
        is_valid=is_valid,
        status=status,
        threshold_used=threshold,
        threshold_type=threshold_type,
        p_value=p_value,
        sample_size=len(prediction),
        prediction_accuracy=direction_acc,
        rolling_correlations=rolling_corrs if len(rolling_corrs) > 0 else None,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        train_size=int(len(prices) * config.train_ratio),
        test_size=len(prediction),
        message=message
    )


def walk_forward_fte(
    prices: np.ndarray,
    forecast_func: callable,
    config: Optional[FTEConfig] = None,
    steps: int = 12
) -> list[FTEResult]:
    """
    Perform walk-forward FTE validation.
    
    Repeatedly trains on expanding window and validates on 
    subsequent out-of-sample period.
    
    Args:
        prices: Full historical price series
        forecast_func: Function that takes training data and returns prediction
        config: FTE configuration
        steps: Number of walk-forward iterations
    
    Returns:
        List of FTEResult for each iteration
    """
    if config is None:
        config = FTEConfig()
    
    results = []
    min_train = max(config.min_data_points, int(len(prices) * 0.3))
    
    for step in range(steps):
        # Calculate train/test split for this iteration
        train_end = min_train + int((len(prices) - min_train) * (step + 1) / steps)
        test_start = train_end
        test_end = min(train_end + config.rolling_window * 2, len(prices))
        
        if test_end >= len(prices):
            break
        
        # Split data
        train_data = prices[:train_end]
        test_actual = prices[test_start:test_end]
        
        # Generate prediction
        try:
            prediction = forecast_func(train_data, len(test_actual))
        except Exception as e:
            results.append(FTEResult(
                pearson_correlation=np.nan,
                spearman_correlation=np.nan,
                is_valid=False,
                status=FTEStatus.INSUFFICIENT_DATA,
                threshold_used=config.base_threshold,
                threshold_type="base",
                message=f"Forecast error at step {step}: {str(e)}"
            ))
            continue
        
        # Validate
        result = validate_fte(prices[:test_end], prediction, config)
        result.message = f"Step {step + 1}/{steps}: {result.message}"
        results.append(result)
    
    return results


def aggregate_fte_results(results: list[FTEResult]) -> dict:
    """
    Aggregate multiple FTE results into summary statistics.
    
    Args:
        results: List of FTEResult objects
    
    Returns:
        Dictionary with aggregated metrics
    """
    if not results:
        return {}
    
    valid_results = [r for r in results if not np.isnan(r.pearson_correlation)]
    
    if not valid_results:
        return {
            "count": len(results),
            "valid_count": 0,
            "message": "No valid results to aggregate"
        }
    
    pearson_values = [r.pearson_correlation for r in valid_results]
    spearman_values = [r.spearman_correlation for r in valid_results]
    
    return {
        "count": len(results),
        "valid_count": len(valid_results),
        "pearson_mean": np.mean(pearson_values),
        "pearson_std": np.std(pearson_values),
        "pearson_min": np.min(pearson_values),
        "pearson_max": np.max(pearson_values),
        "spearman_mean": np.mean(spearman_values),
        "valid_ratio": sum(1 for r in valid_results if r.is_valid) / len(valid_results),
        "broken_count": sum(1 for r in valid_results if r.status == FTEStatus.BROKEN),
        "avg_direction_accuracy": np.mean([r.prediction_accuracy for r in valid_results])
    }
