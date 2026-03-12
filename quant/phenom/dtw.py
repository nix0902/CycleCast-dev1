"""
Phenomenological DTW Module - CycleCast v3.2
Методология Ларри Вильямса: Поиск исторических аналогий через динамическое выравнивание времени

Module: quant/phenom/dtw.py
Task: PH-001 - Phenomenological DTW Prototype
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable, Union
from datetime import datetime, timedelta
import warnings

# Optional imports - fastdtw may not be installed
try:
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    FASTDTW_AVAILABLE = True
except ImportError:
    FASTDTW_AVAILABLE = False
    warnings.warn(
        "fastdtw not installed. Install with: pip install fastdtw\n"
        "Falling back to basic correlation filter."
    )

from scipy.spatial.distance import cdist
from scipy.stats import pearsonr


@dataclass
class DTWConfig:
    """Configuration for DTW algorithm."""
    # Correlation threshold for fast filtering
    correlation_threshold: float = 0.6
    
    # Maximum candidates for exact DTW
    max_candidates: int = 100
    
    # DTW window constraint (Sakoe-Chiba band)
    window_size: Optional[int] = None
    
    # Training interval for historical search
    training_years: int = 10
    
    # Decennial filter: only match same yearDigit (0-9)
    decennial_filter: bool = True
    
    # Minimum length for comparison
    min_length: int = 20
    
    # Distance metric: 'euclidean', 'manhattan', 'cosine'
    distance_metric: str = 'euclidean'
    
    # Normalization: z-score, min-max, or None
    normalization: str = 'zscore'
    
    # Projection horizon (days to project forward)
    projection_horizon: int = 30
    
    # Parallel processing
    n_jobs: int = -1


@dataclass
class DTWMatch:
    """Result of a DTW match."""
    # Historical period start/end dates
    start_date: datetime
    end_date: datetime
    
    # DTW distance (lower = better match)
    distance: float
    
    # Correlation coefficient
    correlation: float
    
    # Alignment path (indices mapping)
    path: List[Tuple[int, int]] = field(default_factory=list)
    
    # Projected continuation (if projection_horizon > 0)
    projection: Optional[np.ndarray] = None
    
    # Year digit of historical match
    year_digit: int = -1
    
    # Additional metadata
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.path and not isinstance(self.path[0], tuple):
            # Convert list of lists to list of tuples if needed
            self.path = [tuple(p) for p in self.path]


@dataclass
class PhenomResult:
    """Complete result of phenomenological analysis."""
    # Target period info
    target_start: datetime
    target_end: datetime
    target_length: int
    
    # Top matches ranked by distance
    matches: List[DTWMatch] = field(default_factory=list)
    
    # Best match projection
    best_projection: Optional[np.ndarray] = None
    
    # Confidence score (0-1)
    confidence: float = 0.0
    
    # Validation metrics
    avg_correlation: float = 0.0
    std_distance: float = 0.0
    
    # Processing info
    candidates_evaluated: int = 0
    processing_time_ms: float = 0.0
    
    # Status
    is_valid: bool = False
    warnings: List[str] = field(default_factory=list)


def _normalize_series(series: np.ndarray, method: str = 'zscore') -> np.ndarray:
    """Normalize time series for comparison."""
    if len(series) == 0:
        return series
    
    if method == 'zscore':
        mean = np.mean(series)
        std = np.std(series)
        if std < 1e-10:
            return np.zeros_like(series)
        return (series - mean) / std
    
    elif method == 'minmax':
        min_val = np.min(series)
        max_val = np.max(series)
        if max_val - min_val < 1e-10:
            return np.zeros_like(series)
        return (series - min_val) / (max_val - min_val)
    
    elif method == 'percentile':
        # Robust normalization using percentiles
        p25 = np.percentile(series, 25)
        p75 = np.percentile(series, 75)
        if p75 - p25 < 1e-10:
            return np.zeros_like(series)
        return (series - p25) / (p75 - p25)
    
    return series


def _get_year_digit(timestamp: Union[datetime, str]) -> int:
    """Extract year digit (0-9) from timestamp."""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return timestamp.year % 10


def _fast_correlation_filter(
    target: np.ndarray,
    candidates: List[Tuple[datetime, datetime, np.ndarray]],
    threshold: float
) -> List[Tuple[datetime, datetime, np.ndarray]]:
    """
    Fast pre-filtering using Pearson correlation.
    O(N) complexity vs O(N²) for DTW.
    """
    filtered = []
    
    for start_date, end_date, series in candidates:
        # Skip if lengths don't match reasonably
        if len(series) < len(target) * 0.5 or len(series) > len(target) * 2:
            continue
        
        # Truncate/pad to same length for correlation
        min_len = min(len(target), len(series))
        t_trunc = target[:min_len]
        s_trunc = series[:min_len]
        
        # Normalize both
        t_norm = _normalize_series(t_trunc)
        s_norm = _normalize_series(s_trunc)
        
        # Calculate correlation
        try:
            corr, _ = pearsonr(t_norm, s_norm)
            if corr >= threshold:
                filtered.append((start_date, end_date, series))
        except (ValueError, RuntimeWarning):
            continue
    
    return filtered


def _euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate Euclidean distance between two series."""
    return np.sqrt(np.sum((a - b) ** 2))


def _manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate Manhattan distance between two series."""
    return np.sum(np.abs(a - b))


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine distance between two series."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a * norm_b < 1e-10:
        return 1.0
    return 1 - dot / (norm_a * norm_b)


def _get_distance_func(metric: str) -> Callable[[np.ndarray, np.ndarray], float]:
    """Get distance function by name."""
    metrics = {
        'euclidean': _euclidean_distance,
        'manhattan': _manhattan_distance,
        'cosine': _cosine_distance,
    }
    return metrics.get(metric, _euclidean_distance)


def _exact_dtw(
    target: np.ndarray,
    candidate: np.ndarray,
    window: Optional[int] = None,
    distance_func: Callable = None
) -> Tuple[float, List[Tuple[int, int]]]:
    """
    Calculate exact DTW distance using dynamic programming.
    
    Args:
        target: Target time series
        candidate: Candidate historical series
        window: Sakoe-Chiba band width (None = no constraint)
        distance_func: Distance metric function
    
    Returns:
        (distance, alignment_path)
    """
    if distance_func is None:
        distance_func = _euclidean_distance
    
    n, m = len(target), len(candidate)
    
    # Initialize cost matrix
    cost = np.full((n + 1, m + 1), np.inf)
    cost[0, 0] = 0
    
    # Initialize path matrix
    path = np.zeros((n + 1, m + 1), dtype=object)
    
    # Dynamic programming
    for i in range(1, n + 1):
        # Window constraint
        j_start = max(1, i - window) if window else 1
        j_end = min(m, i + window) if window else m
        
        for j in range(j_start, j_end + 1):
            # Local distance
            local_dist = distance_func(
                np.array([target[i-1]]),
                np.array([candidate[j-1]])
            )
            
            # Accumulate cost from best predecessor
            cost[i, j] = local_dist + min(
                cost[i-1, j],      # Insertion
                cost[i, j-1],      # Deletion
                cost[i-1, j-1]     # Match
            )
            
            # Track path
            min_prev = np.argmin([
                cost[i-1, j],
                cost[i, j-1],
                cost[i-1, j-1]
            ])
            if min_prev == 0:
                path[i, j] = (i-1, j)
            elif min_prev == 1:
                path[i, j] = (i, j-1)
            else:
                path[i, j] = (i-1, j-1)
    
    # Backtrack to find alignment path
    alignment = []
    i, j = n, m
    while i > 0 or j > 0:
        alignment.append((i-1, j-1))
        if path[i, j] is None:
            break
        i, j = path[i, j]
    
    alignment.reverse()
    
    return cost[n, m], alignment


def _project_continuation(
    historical: np.ndarray,
    alignment: List[Tuple[int, int]],
    target_length: int,
    horizon: int
) -> np.ndarray:
    """
    Project continuation based on historical pattern.
    
    Uses the alignment to map target end to historical continuation.
    """
    if not alignment or horizon <= 0:
        return np.array([])
    
    # Find where target ends in historical series
    target_end_idx = target_length - 1
    hist_idx = None
    
    for t_idx, h_idx in reversed(alignment):
        if t_idx == target_end_idx:
            hist_idx = h_idx
            break
    
    if hist_idx is None or hist_idx + horizon > len(historical):
        # Fallback: use last values with trend
        last_values = historical[-min(10, len(historical)):]
        trend = np.mean(np.diff(last_values)) if len(last_values) > 1 else 0
        return historical[-1] + np.arange(1, horizon + 1) * trend
    
    # Extract continuation from historical
    continuation = historical[hist_idx:hist_idx + horizon]
    
    # Adjust to match target scale
    if len(continuation) < horizon:
        # Pad with extrapolation
        trend = np.mean(np.diff(continuation)) if len(continuation) > 1 else 0
        padding = continuation[-1] + np.arange(1, horizon - len(continuation) + 1) * trend
        continuation = np.concatenate([continuation, padding])
    
    return continuation[:horizon]


def adaptive_dtw(
    target: np.ndarray,
    history: np.ndarray,
    history_dates: List[datetime],
    config: Optional[DTWConfig] = None
) -> PhenomResult:
    """
    Hybrid DTW algorithm for finding historical analogies.
    
    Implements the algorithm from TZ.md section 2.7.2:
    1. Fast correlation filter (O(N))
    2. Limit to top-100 candidates
    3. Parallel exact DTW on candidates
    4. Return sorted results
    
    Args:
        target: Target time series to match
        history: Full historical time series
        history_dates: Corresponding dates for history
        config: DTW configuration
    
    Returns:
        PhenomResult with ranked matches and projection
    """
    import time
    start_time = time.time()
    
    if config is None:
        config = DTWConfig()
    
    result = PhenomResult(
        target_start=datetime.now(),  # Placeholder
        target_end=datetime.now(),
        target_length=len(target)
    )
    
    # Validate inputs
    if len(target) < config.min_length:
        result.warnings.append(f"Target too short: {len(target)} < {config.min_length}")
        return result
    
    if len(history) < config.min_length:
        result.warnings.append(f"History too short: {len(history)} < {config.min_length}")
        return result
    
    # Normalize target
    target_norm = _normalize_series(target, config.normalization)
    
    # Get target year digit for decennial filter
    target_year_digit = _get_year_digit(datetime.now())  # Approximate
    
    # Generate candidate windows from history
    candidates = []
    window_size = len(target)
    
    for i in range(0, len(history) - window_size + 1, window_size // 2):  # 50% overlap
        end_idx = i + window_size
        
        # Decennial filter
        if config.decennial_filter:
            candidate_date = history_dates[i]
            candidate_year_digit = _get_year_digit(candidate_date)
            if candidate_year_digit != target_year_digit:
                continue
        
        candidate_series = history[i:end_idx]
        start_date = history_dates[i]
        end_date = history_dates[end_idx - 1]
        
        candidates.append((start_date, end_date, candidate_series))
    
    # Step 1: Fast correlation filter
    filtered = _fast_correlation_filter(
        target_norm,
        candidates,
        config.correlation_threshold
    )
    
    # Step 2: Limit candidates
    if len(filtered) > config.max_candidates:
        # Sort by correlation and take top N
        filtered.sort(
            key=lambda x: pearsonr(
                _normalize_series(x[2][:len(target)], config.normalization),
                target_norm
            )[0],
            reverse=True
        )
        filtered = filtered[:config.max_candidates]
    
    result.candidates_evaluated = len(filtered)
    
    if not filtered:
        result.warnings.append("No candidates passed correlation filter")
        result.is_valid = False
        return result
    
    # Step 3: Exact DTW on candidates
    distance_func = _get_distance_func(config.distance_metric)
    matches = []
    
    for start_date, end_date, candidate in filtered:
        # Normalize candidate
        candidate_norm = _normalize_series(candidate, config.normalization)
        
        # Calculate DTW
        if FASTDTW_AVAILABLE and config.window_size:
            # Use fastdtw with window constraint
            distance, path = fastdtw(
                target_norm,
                candidate_norm,
                radius=config.window_size,
                dist=distance_func
            )
        else:
            # Use exact DTW (may be slower for long series)
            distance, path = _exact_dtw(
                target_norm,
                candidate_norm,
                window=config.window_size,
                distance_func=distance_func
            )
        
        # Calculate correlation for ranking
        min_len = min(len(target_norm), len(candidate_norm))
        try:
            corr, _ = pearsonr(target_norm[:min_len], candidate_norm[:min_len])
        except:
            corr = 0.0
        
        # Create match result
        match = DTWMatch(
            start_date=start_date,
            end_date=end_date,
            distance=float(distance),
            correlation=float(corr),
            path=path,
            year_digit=_get_year_digit(start_date)
        )
        
        # Project continuation if configured
        if config.projection_horizon > 0:
            match.projection = _project_continuation(
                candidate,
                path,
                len(target),
                config.projection_horizon
            )
        
        matches.append(match)
    
    # Step 4: Sort by distance (ascending)
    matches.sort(key=lambda m: m.distance)
    result.matches = matches
    
    # Calculate aggregate metrics
    if matches:
        result.best_projection = matches[0].projection if matches[0].projection is not None else None
        result.avg_correlation = np.mean([m.correlation for m in matches[:10]])
        result.std_distance = np.std([m.distance for m in matches])
        
        # Confidence: based on best match quality
        best_corr = matches[0].correlation
        best_dist = matches[0].distance
        result.confidence = max(0, min(1, (best_corr + 1) / 2 * (1 - best_dist / 100)))
        result.is_valid = result.confidence > 0.3
    
    # Processing time
    result.processing_time_ms = (time.time() - start_time) * 1000
    
    return result


def find_historical_analogies(
    prices: np.ndarray,
    dates: List[datetime],
    history_prices: np.ndarray,
    history_dates: List[datetime],
    **kwargs
) -> PhenomResult:
    """
    Convenience function to find historical analogies.
    
    Args:
        prices: Current price series (close prices)
        dates: Corresponding dates for current prices
        history_prices: Historical price series
        history_dates: Corresponding dates for historical prices
        **kwargs: Additional config parameters for DTWConfig
    
    Returns:
        PhenomResult with matches and projections
    """
    config = DTWConfig(**kwargs)
    return adaptive_dtw(prices, history_prices, history_dates, config)


def validate_analogy_quality(
    result: PhenomResult,
    min_correlation: float = 0.5,
    min_confidence: float = 0.3,
    max_distance: Optional[float] = None
) -> Tuple[bool, List[str]]:
    """
    Validate if analogy results meet quality thresholds.
    
    Args:
        result: PhenomResult from adaptive_dtw
        min_correlation: Minimum acceptable correlation
        min_confidence: Minimum confidence score
        max_distance: Maximum DTW distance (optional)
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    if not result.is_valid:
        issues.append("Result marked as invalid")
    
    if not result.matches:
        issues.append("No matches found")
        return False, issues
    
    best = result.matches[0]
    
    if best.correlation < min_correlation:
        issues.append(f"Best correlation {best.correlation:.3f} < {min_correlation}")
    
    if result.confidence < min_confidence:
        issues.append(f"Confidence {result.confidence:.3f} < {min_confidence}")
    
    if max_distance is not None and best.distance > max_distance:
        issues.append(f"DTW distance {best.distance:.3f} > {max_distance}")
    
    if result.avg_correlation < min_correlation * 0.8:
        issues.append(f"Average correlation of top-10 too low: {result.avg_correlation:.3f}")
    
    return len(issues) == 0, issues


# Public API
__all__ = [
    'DTWConfig',
    'DTWMatch', 
    'PhenomResult',
    'adaptive_dtw',
    'find_historical_analogies',
    'validate_analogy_quality',
    '_normalize_series',
    '_get_year_digit',
]
