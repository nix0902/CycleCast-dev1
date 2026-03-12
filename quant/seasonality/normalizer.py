"""
Normalization Module - Percentile Rank and Standard Normalizers

Provides normalization techniques for preparing detrended time series
for seasonality analysis and cross-asset comparison.

Methods:
- Percentile Rank: Rank-based normalization robust to outliers
- Z-Score: Standard deviation normalization
- Min-Max: Range-based normalization to [0, 1]

Author: CycleCast AI Agent (Qwen 3.5)
Version: 3.2 Final
Date: 2026-03-13
"""

import numpy as np
import pandas as pd
from typing import Union, Optional, Tuple, List
from scipy import stats
import warnings


class PercentileRankNormalizer:
    """
    Percentile Rank Normalizer for time series data.
    
    Transforms values to their percentile rank within a rolling or 
    fixed window, producing values in [0, 100] or [0, 1] range.
    
    Advantages:
    - Robust to outliers and non-normal distributions
    - Preserves ordinal relationships
    - Enables cross-asset comparison on uniform scale
    
    Reference: Williams, L. (2023). The New Commodity Trading Systems.
    """
    
    def __init__(
        self,
        output_range: Tuple[float, float] = (0, 1),
        window: Optional[int] = None,
        method: str = 'mean',
        normalize_output: bool = True
    ):
        """
        Initialize percentile rank normalizer.
        
        Args:
            output_range: Target range for normalized values (default: [0, 1])
            window: Rolling window size (None for global ranking)
            method: Ranking method ('mean', 'rank', 'strict', 'weak') for scipy
            normalize_output: Scale output to output_range (else use raw percentiles 0-100)
        """
        # Map common aliases
        method_map = {
            'average': 'mean',
            'min': 'strict',
            'max': 'weak',
        }
        self.method = method_map.get(method, method)
        self.output_range = output_range
        self.window = window
        self.normalize_output = normalize_output
        self._fitted = False
        self._global_stats: Optional[dict] = None
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'PercentileRankNormalizer':
        """
        Fit the normalizer by computing global statistics.
        
        Only needed for non-rolling (global) normalization.
        
        Args:
            data: Training data for computing reference distribution
            
        Returns:
            Self
        """
        if self.window is None:
            values = data.values if isinstance(data, pd.Series) else np.asarray(data)
            values = values[~np.isnan(values)]
            
            self._global_stats = {
                'min': np.min(values),
                'max': np.max(values),
                'median': np.median(values),
                'q25': np.percentile(values, 25),
                'q75': np.percentile(values, 75),
            }
            self._fitted = True
        
        return self
    
    def _compute_percentile_rank(
        self,
        values: np.ndarray,
        reference: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute percentile ranks for values.
        
        Args:
            values: Values to rank
            reference: Reference distribution (None = use values themselves)
            
        Returns:
            Percentile ranks (0-100 scale)
        """
        if reference is None:
            reference = values
        
        # Use scipy for efficient percentile ranking
        ranks = stats.percentileofscore(reference, values, kind=self.method)
        
        # Handle vectorized case
        if np.isscalar(ranks):
            # Single value case
            return np.array([ranks])
        else:
            return np.asarray(ranks)
    
    def _scale_to_range(self, values: np.ndarray) -> np.ndarray:
        """Scale values from [0, 100] to target output_range."""
        if not self.normalize_output:
            return values
        
        min_out, max_out = self.output_range
        # Input is [0, 100], scale to [min_out, max_out]
        scaled = min_out + (values / 100.0) * (max_out - min_out)
        return scaled
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """
        Transform data to percentile ranks.
        
        Args:
            data: Time series data to normalize
            
        Returns:
            Normalized data with same type/index as input
        """
        if isinstance(data, pd.Series):
            values = data.values
            index = data.index
            return_type = 'series'
        else:
            values = np.asarray(data, dtype=float)
            index = None
            return_type = 'array'
        
        # Handle missing values
        mask = ~np.isnan(values)
        result = np.full(len(values), np.nan)
        
        if self.window is None:
            # Global ranking
            if not self._fitted and self._global_stats is None:
                # Auto-fit on first transform if not fitted
                self.fit(data)
            
            valid_values = values[mask]
            if len(valid_values) > 0:
                reference = valid_values if self._global_stats is None else None
                ranks = self._compute_percentile_rank(valid_values, reference)
                result[mask] = self._scale_to_range(ranks)
        else:
            # Rolling window ranking
            for i in range(len(values)):
                if np.isnan(values[i]):
                    continue
                    
                # Define window bounds
                start = max(0, i - self.window + 1)
                end = i + 1
                
                window_values = values[start:end]
                valid_window = window_values[~np.isnan(window_values)]
                
                if len(valid_window) > 0:
                    rank = self._compute_percentile_rank(
                        np.array([values[i]]), 
                        valid_window
                    )[0]
                    result[i] = self._scale_to_range(np.array([rank]))[0]
        
        # Return in original format
        if return_type == 'series':
            return pd.Series(result, index=index, name=f"{data.name}_prank" if data.name else "prank")
        return result
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)
    
    def inverse_transform(self, normalized: Union[np.ndarray, pd.Series]) -> Optional[np.ndarray]:
        """
        Approximate inverse transform (not exact due to ranking).
        
        Uses stored quantiles to map back to approximate original scale.
        Only available for global (non-rolling) normalization.
        
        Args:
            normalized: Normalized values in output_range
            
        Returns:
            Approximate original values or None if not possible
        """
        if self.window is not None:
            warnings.warn("Inverse transform not available for rolling window normalization")
            return None
        
        if self._global_stats is None:
            warnings.warn("Normalizer not fitted; cannot perform inverse transform")
            return None
        
        if isinstance(normalized, pd.Series):
            values = normalized.values
        else:
            values = np.asarray(normalized, dtype=float)
        
        # Map from output_range back to [0, 100]
        min_out, max_out = self.output_range
        percentiles = ((values - min_out) / (max_out - min_out)) * 100 if max_out != min_out else values
        
        # Use linear interpolation between known quantiles
        quantiles = np.array([0, 25, 50, 75, 100])
        ref_values = np.array([
            self._global_stats['min'],
            self._global_stats['q25'],
            self._global_stats['median'],
            self._global_stats['q75'],
            self._global_stats['max']
        ])
        
        # Interpolate
        result = np.interp(percentiles, quantiles, ref_values)
        return result


class ZScoreNormalizer:
    """
    Z-Score (Standard Score) Normalizer.
    
    Transforms data to have mean=0 and std=1:
        z = (x - mean) / std
    
    Supports both global and rolling window normalization.
    """
    
    def __init__(
        self,
        window: Optional[int] = None,
        ddof: int = 1,
        clip: Optional[Tuple[float, float]] = None
    ):
        """
        Initialize Z-score normalizer.
        
        Args:
            window: Rolling window size (None for global normalization)
            ddof: Delta degrees of freedom for std calculation
            clip: Optional (min, max) to clip extreme z-scores
        """
        self.window = window
        self.ddof = ddof
        self.clip = clip
        self._global_mean: Optional[float] = None
        self._global_std: Optional[float] = None
        self._fitted = False
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'ZScoreNormalizer':
        """Compute global mean and std for normalization."""
        if self.window is None:
            values = data.values if isinstance(data, pd.Series) else np.asarray(data)
            values = values[~np.isnan(values)]
            
            self._global_mean = np.mean(values)
            self._global_std = np.std(values, ddof=self.ddof)
            self._fitted = True
        
        return self
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Transform data to z-scores."""
        if isinstance(data, pd.Series):
            values = data.values
            index = data.index
            return_type = 'series'
        else:
            values = np.asarray(data, dtype=float)
            index = None
            return_type = 'array'
        
        result = np.full(len(values), np.nan)
        
        if self.window is None:
            # Global normalization
            if not self._fitted:
                self.fit(data)
            
            if self._global_std and self._global_std > 0:
                result = (values - self._global_mean) / self._global_std
            else:
                result = np.zeros_like(values)  # Constant data
        else:
            # Rolling window normalization
            for i in range(len(values)):
                if np.isnan(values[i]):
                    continue
                    
                start = max(0, i - self.window + 1)
                end = i + 1
                
                window = values[start:end]
                valid = window[~np.isnan(window)]
                
                if len(valid) >= 2:
                    mean = np.mean(valid)
                    std = np.std(valid, ddof=self.ddof)
                    if std > 0:
                        result[i] = (values[i] - mean) / std
                    else:
                        result[i] = 0.0
        
        # Clip extreme values if requested
        if self.clip is not None:
            result = np.clip(result, self.clip[0], self.clip[1])
        
        if return_type == 'series':
            return pd.Series(result, index=index, name=f"{data.name}_zscore" if data.name else "zscore")
        return result
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)
    
    def inverse_transform(self, normalized: Union[np.ndarray, pd.Series]) -> Optional[np.ndarray]:
        """Convert z-scores back to original scale."""
        if self.window is not None:
            warnings.warn("Inverse transform not available for rolling window normalization")
            return None
        
        if not self._fitted:
            warnings.warn("Normalizer not fitted; cannot perform inverse transform")
            return None
        
        if isinstance(normalized, pd.Series):
            values = normalized.values
        else:
            values = np.asarray(normalized, dtype=float)
        
        result = values * self._global_std + self._global_mean
        return result


class MinMaxNormalizer:
    """
    Min-Max Normalizer for scaling to [0, 1] or custom range.
    
    Formula: scaled = (x - min) / (max - min) * (new_max - new_min) + new_min
    """
    
    def __init__(
        self,
        feature_range: Tuple[float, float] = (0, 1),
        window: Optional[int] = None,
        clip: bool = True
    ):
        """
        Initialize min-max normalizer.
        
        Args:
            feature_range: Target (min, max) for normalized values
            window: Rolling window (None for global)
            clip: Clip input values to training range before normalization
        """
        self.feature_range = feature_range
        self.window = window
        self.clip = clip
        self._global_min: Optional[float] = None
        self._global_max: Optional[float] = None
        self._fitted = False
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'MinMaxNormalizer':
        """Compute global min/max for normalization."""
        if self.window is None:
            values = data.values if isinstance(data, pd.Series) else np.asarray(data)
            values = values[~np.isnan(values)]
            
            self._global_min = np.min(values)
            self._global_max = np.max(values)
            self._fitted = True
        
        return self
    
    def _scale_value(self, value: float, min_val: float, max_val: float) -> float:
        """Scale a single value to feature_range."""
        if max_val == min_val:
            return (self.feature_range[0] + self.feature_range[1]) / 2
        
        new_min, new_max = self.feature_range
        scaled = (value - min_val) / (max_val - min_val) * (new_max - new_min) + new_min
        return scaled
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Transform data to normalized range."""
        if isinstance(data, pd.Series):
            values = data.values
            index = data.index
            return_type = 'series'
        else:
            values = np.asarray(data, dtype=float)
            index = None
            return_type = 'array'
        
        result = np.full(len(values), np.nan)
        
        if self.window is None:
            # Global normalization
            if not self._fitted:
                self.fit(data)
            
            min_val = self._global_min
            max_val = self._global_max
            
            if self.clip:
                values = np.clip(values, min_val, max_val)
            
            for i, v in enumerate(values):
                if not np.isnan(v):
                    result[i] = self._scale_value(v, min_val, max_val)
        else:
            # Rolling window
            for i in range(len(values)):
                if np.isnan(values[i]):
                    continue
                    
                start = max(0, i - self.window + 1)
                end = i + 1
                
                window = values[start:end]
                valid = window[~np.isnan(window)]
                
                if len(valid) >= 2:
                    min_val = np.min(valid)
                    max_val = np.max(valid)
                    
                    val = values[i]
                    if self.clip:
                        val = np.clip(val, min_val, max_val)
                    
                    result[i] = self._scale_value(val, min_val, max_val)
        
        if return_type == 'series':
            return pd.Series(result, index=index, name=f"{data.name}_minmax" if data.name else "minmax")
        return result
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)
    
    def inverse_transform(self, normalized: Union[np.ndarray, pd.Series]) -> Optional[np.ndarray]:
        """Convert normalized values back to original scale."""
        if self.window is not None:
            warnings.warn("Inverse transform not available for rolling window normalization")
            return None
        
        if not self._fitted:
            warnings.warn("Normalizer not fitted; cannot perform inverse transform")
            return None
        
        if isinstance(normalized, pd.Series):
            values = normalized.values
        else:
            values = np.asarray(normalized, dtype=float)
        
        new_min, new_max = self.feature_range
        original_min = self._global_min
        original_max = self._global_max
        
        if original_max == original_min or new_max == new_min:
            return np.full_like(values, original_min)
        
        # Inverse: x = (scaled - new_min) / (new_max - new_min) * (orig_max - orig_min) + orig_min
        result = ((values - new_min) / (new_max - new_min)) * (original_max - original_min) + original_min
        return result


def create_normalization_pipeline(
    methods: List[str],
    **kwargs
) -> 'NormalizationPipeline':
    """
    Factory function to create a chained normalization pipeline.
    
    Args:
        methods: List of normalization method names to apply in order
        **kwargs: Parameters for each normalizer
        
    Returns:
        Configured NormalizationPipeline instance
    """
    return NormalizationPipeline(methods=methods, **kwargs)


class NormalizationPipeline:
    """
    Pipeline for chaining multiple normalization methods.
    
    Example:
        pipeline = NormalizationPipeline(['detrend', 'prank'])
        result = pipeline.fit_transform(data)
    """
    
    def __init__(
        self,
        methods: List[str],
        **kwargs
    ):
        """
        Initialize normalization pipeline.
        
        Args:
            methods: List of method names: ['prank', 'zscore', 'minmax']
            **kwargs: Method-specific parameters (e.g., prank_window=20)
        """
        self.methods = methods
        self.kwargs = kwargs
        self._normalizers = []
        self._fitted = False
        
        # Initialize normalizers
        for method in methods:
            if method == 'prank':
                self._normalizers.append(PercentileRankNormalizer(
                    window=kwargs.get('prank_window'),
                    output_range=kwargs.get('prank_range', (0, 1)),
                    method=kwargs.get('prank_method', 'average')
                ))
            elif method == 'zscore':
                self._normalizers.append(ZScoreNormalizer(
                    window=kwargs.get('zscore_window'),
                    ddof=kwargs.get('zscore_ddof', 1),
                    clip=kwargs.get('zscore_clip', (-3, 3))
                ))
            elif method == 'minmax':
                self._normalizers.append(MinMaxNormalizer(
                    feature_range=kwargs.get('minmax_range', (0, 1)),
                    window=kwargs.get('minmax_window'),
                    clip=kwargs.get('minmax_clip', True)
                ))
            else:
                raise ValueError(f"Unknown normalization method: {method}")
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'NormalizationPipeline':
        """Fit all normalizers in the pipeline."""
        current_data = data
        for normalizer in self._normalizers:
            normalizer.fit(current_data)
            current_data = normalizer.transform(current_data)
        
        self._fitted = True
        return self
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Apply all normalizers sequentially."""
        if not self._fitted:
            raise RuntimeError("Must call fit() before transform()")
        
        result = data
        for normalizer in self._normalizers:
            result = normalizer.transform(result)
        
        return result
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> Union[np.ndarray, pd.Series]:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)


def validate_normalization(
    original: np.ndarray,
    normalized: np.ndarray,
    method: str,
    expected_range: Optional[Tuple[float, float]] = None
) -> Tuple[bool, dict]:
    """
    Validate normalization output.
    
    Checks:
    - No NaN/inf values (except where input had NaN)
    - Output range matches expectations
    - Monotonicity preserved (for rank-based methods)
    
    Args:
        original: Original input data
        normalized: Normalized output
        method: Normalization method used
        expected_range: Expected (min, max) for output
        
    Returns:
        Tuple of (is_valid, diagnostic_dict)
    """
    diagnostics = {
        'nan_preserved': True,
        'range_valid': True,
        'monotonicity_preserved': True,
        'output_min': np.nanmin(normalized),
        'output_max': np.nanmax(normalized),
    }
    
    # Check NaN preservation
    orig_nan = np.isnan(original)
    norm_nan = np.isnan(normalized)
    if not np.array_equal(orig_nan, norm_nan):
        diagnostics['nan_preserved'] = False
        diagnostics['nan_mismatch'] = np.sum(orig_nan != norm_nan)
    
    # Check output range
    if expected_range is not None:
        valid_vals = normalized[~np.isnan(normalized)]
        if len(valid_vals) > 0:
            if np.min(valid_vals) < expected_range[0] - 1e-6 or np.max(valid_vals) > expected_range[1] + 1e-6:
                diagnostics['range_valid'] = False
    
    # Check monotonicity for rank-based methods
    if method == 'prank' and expected_range == (0, 1):
        # Percentile rank should preserve order
        valid_idx = ~np.isnan(original) & ~np.isnan(normalized)
        if np.sum(valid_idx) >= 2:
            orig_valid = original[valid_idx]
            norm_valid = normalized[valid_idx]
            
            # Check that order is preserved
            for i in range(len(orig_valid) - 1):
                if orig_valid[i] < orig_valid[i+1] and norm_valid[i] > norm_valid[i+1] + 1e-6:
                    diagnostics['monotonicity_preserved'] = False
                    break
                elif orig_valid[i] > orig_valid[i+1] and norm_valid[i] < norm_valid[i+1] - 1e-6:
                    diagnostics['monotonicity_preserved'] = False
                    break
    
    is_valid = all([
        diagnostics['nan_preserved'],
        diagnostics['range_valid'],
        diagnostics['monotonicity_preserved']
    ])
    
    return is_valid, diagnostics
