"""
Regime Detection & Adaptive Threshold Module

This module implements market regime detection using volatility-based statistical
approaches and adaptive threshold calculation for seasonality signal validation.

Algorithms:
- Volatility-based regime classification (LOW/NORMAL/HIGH/EXTREME)
- Adaptive threshold: base × (1 + λ × (vol_ratio - 1)) with 50% floor
- Regime-aware FTE validation integration

Author: CycleCast AI Agent (Qwen 3.5)
Version: 3.2 Final
Date: 2026-03-14
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple, Union

import numpy as np
from scipy import stats


class RegimeType(Enum):
    """Market regime classification based on volatility."""
    LOW_VOL = auto()      # Calm market, low volatility
    NORMAL_VOL = auto()   # Typical market conditions
    HIGH_VOL = auto()     # Elevated volatility, uncertain
    EXTREME_VOL = auto()  # Crisis mode, very high volatility


@dataclass
class RegimeConfig:
    """Configuration for regime detection and adaptive thresholds."""
    
    # Volatility calculation
    short_window: int = 21          # Days for current volatility (1 month)
    long_window: int = 252          # Days for baseline volatility (1 year)
    
    # Regime classification thresholds (percentile-based)
    low_vol_percentile: float = 0.25    # Below 25th percentile = LOW
    high_vol_percentile: float = 0.75   # Above 75th percentile = HIGH
    extreme_vol_percentile: float = 0.95  # Above 95th percentile = EXTREME
    
    # Adaptive threshold parameters (from TZ.md §2.3.2)
    base_threshold: float = 0.08        # Base FTE threshold
    sensitivity_lambda: float = 0.5     # λ parameter for volatility adjustment
    min_threshold_ratio: float = 0.5    # Floor: threshold can't go below 50% of base
    
    # Regime-specific adjustments
    regime_multiplier: dict = field(default_factory=lambda: {
        RegimeType.LOW_VOL: 1.0,      # No adjustment in calm markets
        RegimeType.NORMAL_VOL: 1.0,    # Standard threshold
        RegimeType.HIGH_VOL: 1.2,      # Require stronger signal in high vol
        RegimeType.EXTREME_VOL: 1.5,   # Much stronger signal in crisis
    })
    
    # Minimum data requirements
    min_samples: int = 60             # Minimum data points for regime detection


@dataclass
class RegimeResult:
    """Result of regime detection analysis."""
    
    regime: RegimeType
    current_volatility: float
    baseline_volatility: float
    volatility_ratio: float
    percentile_rank: float  # Where current vol falls in historical distribution
    
    # Adaptive threshold
    adaptive_threshold: float
    regime_adjusted_threshold: float
    
    # Metadata
    samples_analyzed: int
    confidence: float  # Confidence in regime classification (0-1)
    
    def is_valid_signal(self, fte_score: float) -> bool:
        """Check if FTE score exceeds the regime-adjusted threshold."""
        return fte_score >= self.regime_adjusted_threshold
    
    def get_signal_strength(self, fte_score: float) -> float:
        """Calculate normalized signal strength relative to threshold."""
        if self.regime_adjusted_threshold <= 0:
            return 0.0
        return min(1.0, fte_score / self.regime_adjusted_threshold)


def calculate_realized_volatility(
    prices: Union[List[float], np.ndarray],
    window: int = 21,
    method: str = 'log'
) -> np.ndarray:
    """
    Calculate realized volatility using rolling window.
    
    Args:
        prices: Price series (close prices)
        window: Rolling window size in days
        method: 'log' for log returns, 'simple' for simple returns
    
    Returns:
        Array of rolling volatility values
    """
    prices = np.asarray(prices, dtype=float)
    
    if len(prices) < window + 1:
        return np.array([np.nan])
    
    # Calculate returns
    if method == 'log':
        returns = np.diff(np.log(prices))
    else:
        returns = np.diff(prices) / prices[:-1]
    
    # Remove NaN and infinite values
    returns = returns[np.isfinite(returns)]
    
    if len(returns) < window:
        return np.array([np.nan])
    
    # Calculate rolling standard deviation (annualized)
    rolling_std = np.zeros(len(prices))
    rolling_std[:] = np.nan
    
    for i in range(window, len(prices)):
        window_returns = returns[i-window:i]
        if len(window_returns) >= window // 2:  # Allow some missing data
            rolling_std[i] = np.std(window_returns) * np.sqrt(252)  # Annualize
    
    return rolling_std


def calculate_volatility_percentile(
    current_vol: float,
    historical_vols: np.ndarray
) -> float:
    """
    Calculate percentile rank of current volatility in historical distribution.
    
    Args:
        current_vol: Current volatility value
        historical_vols: Array of historical volatility values
    
    Returns:
        Percentile rank (0.0 to 1.0)
    """
    valid_vols = historical_vols[np.isfinite(historical_vols)]
    
    if len(valid_vols) == 0:
        return 0.5  # Default to median if no data
    
    # Use percentileofscore for accurate ranking
    percentile = stats.percentileofscore(valid_vols, current_vol, kind='weak')
    return percentile / 100.0


def detect_regime(
    prices: Union[List[float], np.ndarray],
    config: Optional[RegimeConfig] = None
) -> RegimeResult:
    """
    Detect market regime based on volatility analysis.
    
    Implements statistical approach using rolling volatility percentiles.
    
    Args:
        prices: Price series for analysis
        config: RegimeConfig with parameters (uses defaults if None)
    
    Returns:
        RegimeResult with classification and adaptive thresholds
    """
    if config is None:
        config = RegimeConfig()
    
    prices = np.asarray(prices, dtype=float)
    
    # Check minimum data requirements
    if len(prices) < config.min_samples:
        # Return default regime with low confidence
        return RegimeResult(
            regime=RegimeType.NORMAL_VOL,
            current_volatility=np.nan,
            baseline_volatility=np.nan,
            volatility_ratio=1.0,
            percentile_rank=0.5,
            adaptive_threshold=config.base_threshold,
            regime_adjusted_threshold=config.base_threshold,
            samples_analyzed=len(prices),
            confidence=0.0
        )
    
    # Calculate rolling volatility
    rolling_vol = calculate_realized_volatility(
        prices, 
        window=config.short_window
    )
    
    # Get current and baseline volatility
    valid_rolling = rolling_vol[np.isfinite(rolling_vol)]
    
    if len(valid_rolling) < config.short_window // 2:
        return RegimeResult(
            regime=RegimeType.NORMAL_VOL,
            current_volatility=np.nan,
            baseline_volatility=np.nan,
            volatility_ratio=1.0,
            percentile_rank=0.5,
            adaptive_threshold=config.base_threshold,
            regime_adjusted_threshold=config.base_threshold,
            samples_analyzed=len(prices),
            confidence=0.0
        )
    
    current_vol = valid_rolling[-1]  # Most recent volatility
    
    # Calculate baseline (long-term average volatility)
    baseline_vol = np.mean(valid_rolling[-config.long_window:])
    if baseline_vol <= 0:
        baseline_vol = np.median(valid_rolling)
    
    # Calculate volatility ratio
    vol_ratio = current_vol / baseline_vol if baseline_vol > 0 else 1.0
    
    # Calculate percentile rank
    percentile = calculate_volatility_percentile(current_vol, valid_rolling)
    
    # Classify regime based on percentiles
    if percentile < config.low_vol_percentile:
        regime = RegimeType.LOW_VOL
    elif percentile < config.high_vol_percentile:
        regime = RegimeType.NORMAL_VOL
    elif percentile < config.extreme_vol_percentile:
        regime = RegimeType.HIGH_VOL
    else:
        regime = RegimeType.EXTREME_VOL
    
    # Calculate adaptive threshold (TZ.md §2.3.2 formula)
    adaptive_threshold = config.base_threshold * (
        1 + config.sensitivity_lambda * (vol_ratio - 1)
    )
    
    # Apply floor constraint
    adaptive_threshold = max(
        adaptive_threshold, 
        config.base_threshold * config.min_threshold_ratio
    )
    
    # Apply regime-specific multiplier
    regime_multiplier = config.regime_multiplier.get(regime, 1.0)
    regime_adjusted_threshold = adaptive_threshold * regime_multiplier
    
    # Calculate confidence based on sample size and volatility stability
    vol_stability = 1 - (np.std(valid_rolling[-config.long_window:]) / 
                        (np.mean(valid_rolling[-config.long_window:]) + 1e-10))
    sample_confidence = min(1.0, len(valid_rolling) / (config.long_window * 2))
    confidence = (vol_stability + sample_confidence) / 2
    
    return RegimeResult(
        regime=regime,
        current_volatility=current_vol,
        baseline_volatility=baseline_vol,
        volatility_ratio=vol_ratio,
        percentile_rank=percentile,
        adaptive_threshold=adaptive_threshold,
        regime_adjusted_threshold=regime_adjusted_threshold,
        samples_analyzed=len(valid_rolling),
        confidence=confidence
    )


def validate_with_regime(
    fte_score: float,
    prices: Union[List[float], np.ndarray],
    config: Optional[RegimeConfig] = None
) -> Tuple[bool, RegimeResult]:
    """
    Validate FTE score against regime-adjusted threshold.
    
    Args:
        fte_score: Forecast Theoretical Efficiency score
        prices: Price series for regime detection
        config: Optional configuration
    
    Returns:
        Tuple of (is_valid, RegimeResult)
    """
    regime_result = detect_regime(prices, config)
    is_valid = regime_result.is_valid_signal(fte_score)
    return is_valid, regime_result


def get_regime_transition_probability(
    prices: Union[List[float], np.ndarray],
    config: Optional[RegimeConfig] = None,
    lookback: int = 50
) -> dict:
    """
    Estimate probability of regime transitions based on recent volatility trend.
    
    Uses simple linear regression on volatility series to detect momentum.
    
    Args:
        prices: Price series for analysis
        config: RegimeConfig parameters
        lookback: Number of periods to analyze for trend
    
    Returns:
        Dict with transition probabilities to each regime
    """
    if config is None:
        config = RegimeConfig()
    
    prices = np.asarray(prices, dtype=float)
    
    if len(prices) < lookback + config.short_window:
        return {r: 0.25 for r in RegimeType}  # Uniform if insufficient data
    
    # Calculate rolling volatility
    rolling_vol = calculate_realized_volatility(prices, window=config.short_window)
    valid_vol = rolling_vol[np.isfinite(rolling_vol)][-lookback:]
    
    if len(valid_vol) < lookback // 2:
        return {r: 0.25 for r in RegimeType}
    
    # Simple linear trend analysis
    x = np.arange(len(valid_vol))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, valid_vol)
    
    # Current regime
    current_result = detect_regime(prices, config)
    current_regime = current_result.regime
    
    # Base probabilities (stay in current regime is most likely)
    probs = {r: 0.1 for r in RegimeType}
    probs[current_regime] = 0.6  # Base probability to stay
    
    # Adjust based on volatility trend
    if slope > 0 and r_value > 0.3:  # Increasing volatility trend
        # Shift probability toward higher volatility regimes
        if current_regime == RegimeType.LOW_VOL:
            probs[RegimeType.NORMAL_VOL] += 0.2
            probs[RegimeType.LOW_VOL] -= 0.2
        elif current_regime == RegimeType.NORMAL_VOL:
            probs[RegimeType.HIGH_VOL] += 0.2
            probs[RegimeType.NORMAL_VOL] -= 0.2
        elif current_regime == RegimeType.HIGH_VOL:
            probs[RegimeType.EXTREME_VOL] += 0.2
            probs[RegimeType.HIGH_VOL] -= 0.2
    
    elif slope < 0 and r_value < -0.3:  # Decreasing volatility trend
        # Shift probability toward lower volatility regimes
        if current_regime == RegimeType.EXTREME_VOL:
            probs[RegimeType.HIGH_VOL] += 0.2
            probs[RegimeType.EXTREME_VOL] -= 0.2
        elif current_regime == RegimeType.HIGH_VOL:
            probs[RegimeType.NORMAL_VOL] += 0.2
            probs[RegimeType.HIGH_VOL] -= 0.2
        elif current_regime == RegimeType.NORMAL_VOL:
            probs[RegimeType.LOW_VOL] += 0.2
            probs[RegimeType.NORMAL_VOL] -= 0.2
    
    # Normalize probabilities
    total = sum(probs.values())
    return {r: p / total for r, p in probs.items()}


def regime_aware_backtest_signal(
    fte_scores: List[float],
    prices: Union[List[float], np.ndarray],
    config: Optional[RegimeConfig] = None,
    min_consecutive: int = 3
) -> dict:
    """
    Generate backtest-ready signals with regime-aware validation.
    
    Implements signal filtering based on regime stability and consecutive
    validation to reduce false positives during regime transitions.
    
    Args:
        fte_scores: List of FTE scores over time
        prices: Corresponding price series
        config: RegimeConfig parameters
        min_consecutive: Minimum consecutive valid signals to trigger
    
    Returns:
        Dict with signal analysis results
    """
    if config is None:
        config = RegimeConfig()
    
    prices = np.asarray(prices, dtype=float)
    fte_scores = np.asarray(fte_scores, dtype=float)
    
    if len(fte_scores) != len(prices):
        raise ValueError("fte_scores and prices must have same length")
    
    results = []
    regime_history = []
    valid_count = 0
    
    for i, fte in enumerate(fte_scores):
        # Detect regime at this point (using data up to i)
        regime_result = detect_regime(prices[:i+1], config)
        regime_history.append(regime_result.regime)
        
        # Check if signal is valid under current regime
        is_valid = regime_result.is_valid_signal(fte)
        
        if is_valid:
            valid_count += 1
        else:
            valid_count = 0
        
        results.append({
            'index': i,
            'fte_score': fte,
            'regime': regime_result.regime.name,
            'threshold': regime_result.regime_adjusted_threshold,
            'is_valid': is_valid,
            'consecutive_valid': valid_count,
            'trigger_signal': valid_count >= min_consecutive
        })
    
    # Summary statistics
    valid_signals = [r for r in results if r['trigger_signal']]
    
    return {
        'signals': results,
        'summary': {
            'total_periods': len(results),
            'valid_periods': sum(1 for r in results if r['is_valid']),
            'triggered_signals': len(valid_signals),
            'regime_distribution': {
                r.name: sum(1 for rh in regime_history if rh == r) 
                for r in RegimeType
            },
            'avg_threshold': np.mean([r['threshold'] for r in results]),
        }
    }


# Convenience function for integration with existing FTE module
def integrate_with_fte(
    fte_result: dict,
    prices: Union[List[float], np.ndarray],
    config: Optional[RegimeConfig] = None
) -> dict:
    """
    Integrate regime detection with existing FTE validation results.
    
    Args:
        fte_result: Dict from FTE validation (with 'correlation' key)
        prices: Price series for regime analysis
        config: Optional RegimeConfig
    
    Returns:
        Enhanced result dict with regime information
    """
    fte_score = fte_result.get('correlation', 0.0)
    
    is_valid, regime_result = validate_with_regime(fte_score, prices, config)
    
    return {
        **fte_result,
        'regime_validated': is_valid,
        'regime': regime_result.regime.name,
        'regime_confidence': regime_result.confidence,
        'adaptive_threshold': regime_result.adaptive_threshold,
        'regime_adjusted_threshold': regime_result.regime_adjusted_threshold,
        'volatility_ratio': regime_result.volatility_ratio,
        'signal_strength': regime_result.get_signal_strength(fte_score),
    }
