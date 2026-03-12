"""
Seasonality Module - Detrending, Normalization, FTE Validation, and Regime Detection Pipeline

This module provides tools for extracting seasonal components from time series data
by removing trend and normalizing values for comparative analysis, plus FTE validation
and regime-aware adaptive thresholding.

Algorithms:
- STL (Seasonal-Trend decomposition using LOESS)
- Hodrick-Prescott Filter
- Percentile Rank Normalization
- FTE (Forecast Theoretical Efficiency) Validation
- Regime Detection (volatility-based classification)
- Adaptive Threshold Calculation

Author: CycleCast AI Agent (Qwen 3.5)
Version: 3.2 Final
Date: 2026-03-14
"""

from .detrend import STLDecomposition, HodrickPrescottFilter, DetrendPipeline
from .normalizer import PercentileRankNormalizer, ZScoreNormalizer, MinMaxNormalizer
from .fte import (
    FTEConfig,
    FTEResult,
    FTEStatus,
    validate_fte,
    walk_forward_fte,
    aggregate_fte_results,
    calculate_adaptive_threshold,
    pearson_correlation,
    spearman_correlation,
    rolling_window_validation,
)
from .regime import (
    RegimeType,
    RegimeConfig,
    RegimeResult,
    calculate_realized_volatility,
    calculate_volatility_percentile,
    detect_regime,
    validate_with_regime,
    get_regime_transition_probability,
    regime_aware_backtest_signal,
    integrate_with_fte,
)

__all__ = [
    # Detrending
    "STLDecomposition",
    "HodrickPrescottFilter", 
    "DetrendPipeline",
    # Normalization
    "PercentileRankNormalizer",
    "ZScoreNormalizer",
    "MinMaxNormalizer",
    # FTE Validation
    "FTEConfig",
    "FTEResult",
    "FTEStatus",
    "validate_fte",
    "walk_forward_fte",
    "aggregate_fte_results",
    "calculate_adaptive_threshold",
    "pearson_correlation",
    "spearman_correlation",
    "rolling_window_validation",
    # Regime Detection
    "RegimeType",
    "RegimeConfig",
    "RegimeResult",
    "calculate_realized_volatility",
    "calculate_volatility_percentile",
    "detect_regime",
    "validate_with_regime",
    "get_regime_transition_probability",
    "regime_aware_backtest_signal",
    "integrate_with_fte",
]

__version__ = "1.0.0"
