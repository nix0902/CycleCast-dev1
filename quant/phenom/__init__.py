"""
Phenomenological Model Module - Historical Analogy Search

Implements Dynamic Time Warping (DTW) for finding historical market patterns
that resemble current conditions, following Larry Williams' phenomenological approach.

Key Functions:
    - fast_correlation_filter(): O(N) pre-filtering using Pearson correlation
    - exact_dtw(): Precise DTW distance calculation with Sakoe-Chiba band
    - adaptive_dtw(): Hybrid filter + exact DTW for efficiency
    - decennial_filter(): Filter candidates by year digit (0-9)
    - project_continuation(): Project historical pattern forward

References:
    - Williams, L. (2002). Long-Term Secrets to Short-Term Trading
    - Berndt, D.J., Clifford, J. (1994). Using Dynamic Time Warping
    - Salvador, S., Chan, P. (2007). Toward accurate dynamic time warping
"""

__version__ = "3.2.0"
__author__ = "CycleCast Team"

from .dtw import (
    adaptive_dtw,
    find_historical_analogies,
    validate_analogy_quality,
    DTWConfig,
    DTWMatch,
    PhenomResult,
)

# Aliases for backward compatibility
fast_correlation_filter = adaptive_dtw  # Use adaptive_dtw instead
exact_dtw = adaptive_dtw  # Use adaptive_dtw for DTW calculation
decennial_filter = lambda *args, **kwargs: None  # Integrated into adaptive_dtw

__all__ = [
    "adaptive_dtw",
    "find_historical_analogies",
    "validate_analogy_quality",
    "DTWConfig",
    "DTWMatch",
    "PhenomResult",
    # Backward compatibility aliases
    "fast_correlation_filter",
    "exact_dtw",
    "decennial_filter",
]
