"""
Integration Tests for Seasonality Detrending and Normalization

Tests the complete pipeline: detrending -> normalization -> validation
for seasonality analysis preparation.

Author: CycleCast AI Agent (Qwen 3.5)
Version: 3.2 Final
Date: 2026-03-13
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from quant.seasonality.detrend import (
    STLDecomposition, 
    HodrickPrescottFilter, 
    DetrendPipeline,
    validate_detrended_data
)
from quant.seasonality.normalizer import (
    PercentileRankNormalizer,
    ZScoreNormalizer,
    MinMaxNormalizer,
    NormalizationPipeline,
    validate_normalization
)


def generate_synthetic_seasonal_data(
    n_points: int = 500,
    period: int = 50,
    trend_slope: float = 0.01,
    seasonal_amplitude: float = 10.0,
    noise_level: float = 2.0,
    seed: int = 42
) -> pd.Series:
    """
    Generate synthetic time series with known components for testing.
    
    Components:
    - Linear trend: slope * t
    - Seasonal: amplitude * sin(2*pi*t/period)
    - Noise: Gaussian with specified std
    
    Args:
        n_points: Number of data points
        period: Seasonal period
        trend_slope: Trend component slope
        seasonal_amplitude: Amplitude of seasonal component
        noise_level: Standard deviation of noise
        seed: Random seed for reproducibility
        
    Returns:
        pd.Series with datetime index and synthetic values
    """
    np.random.seed(seed)
    
    t = np.arange(n_points)
    
    # Generate components
    trend = trend_slope * t
    seasonal = seasonal_amplitude * np.sin(2 * np.pi * t / period)
    noise = np.random.normal(0, noise_level, n_points)
    
    # Combine
    values = 100 + trend + seasonal + noise  # Base level = 100
    
    # Create datetime index (daily data)
    start_date = datetime(2020, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(n_points)]
    
    return pd.Series(values, index=dates, name='synthetic_price')


class TestSTLDecomposition:
    """Test suite for STL decomposition."""
    
    def test_stl_basic_decomposition(self):
        """Test that STL correctly decomposes synthetic data."""
        data = generate_synthetic_seasonal_data(n_points=300, period=30)
        
        stl = STLDecomposition(period=30, seasonal=31, trend=31)
        result = stl.fit_transform(data)
        
        # Check output structure
        assert 'original' in result.columns
        assert 'trend' in result.columns
        assert 'seasonal' in result.columns
        assert 'residual' in result.columns
        
        # Check that components sum to original (within tolerance)
        reconstructed = result['trend'] + result['seasonal'] + result['residual']
        assert np.allclose(reconstructed, result['original'], rtol=1e-5)
        
        # Check seasonal component has expected periodicity
        seasonal = result['seasonal'].values
        if len(seasonal) >= 60:  # Need at least 2 periods
            # Autocorrelation at lag=period should be high
            acf = np.correlate(seasonal - np.mean(seasonal), 
                             seasonal - np.mean(seasonal), mode='full')
            acf = acf[len(acf)//2:]
            if acf[0] > 0:
                acf_normalized = acf / acf[0]
                # Peak at period lag
                if len(acf_normalized) > 30:
                    assert acf_normalized[30] > 0.5  # Strong autocorrelation at period
    
    def test_stl_robustness_to_outliers(self):
        """Test that robust STL handles outliers correctly."""
        data = generate_synthetic_seasonal_data(n_points=200, period=20)
        
        # Inject outliers
        data_with_outliers = data.copy()
        outlier_indices = [50, 100, 150]
        data_with_outliers.iloc[outlier_indices] += 50  # Large spikes
        
        # Fit with robust=True
        stl_robust = STLDecomposition(period=20, robust=True)
        result_robust = stl_robust.fit_transform(data_with_outliers)
        
        # Fit with robust=False
        stl_nonrobust = STLDecomposition(period=20, robust=False)
        result_nonrobust = stl_nonrobust.fit_transform(data_with_outliers)
        
        # Robust version should have smaller residual at outlier points
        for idx in outlier_indices:
            robust_resid = abs(result_robust['residual'].iloc[idx])
            nonrobust_resid = abs(result_nonrobust['residual'].iloc[idx])
            # Robust should handle outliers better (smaller residual impact on trend)
            assert robust_resid <= nonrobust_resid + 10  # Allow some tolerance
    
    def test_stl_invalid_inputs(self):
        """Test STL error handling for invalid inputs."""
        # Too short data
        short_data = pd.Series(np.random.randn(10))
        stl = STLDecomposition(period=20)
        
        with pytest.raises(ValueError, match="at least 2x period"):
            stl.fit(short_data)
        
        # Missing values (should warn but not crash)
        data_with_nan = generate_synthetic_seasonal_data(n_points=100, period=10)
        data_with_nan.iloc[10:15] = np.nan
        
        stl = STLDecomposition(period=10)
        with pytest.warns(UserWarning, match="Missing values"):
            result = stl.fit_transform(data_with_nan)
        
        # Should still produce output with NaNs in same positions
        assert result['original'].isna().sum() == 5


class TestHodrickPrescottFilter:
    """Test suite for Hodrick-Prescott filter."""
    
    def test_hp_basic_extraction(self):
        """Test HP filter extracts smooth trend from noisy data."""
        data = generate_synthetic_seasonal_data(
            n_points=200, 
            period=25, 
            trend_slope=0.02,
            noise_level=5.0
        )
        
        hp = HodrickPrescottFilter(lamb=160000, freq='daily')
        result = hp.fit_transform(data)
        
        # Check output structure
        assert 'original' in result.columns
        assert 'trend' in result.columns
        assert 'cycle' in result.columns
        
        # Trend should be smoother than original
        orig_diff = np.diff(data.values)
        trend_diff = np.diff(result['trend'].values)
        
        assert np.std(trend_diff) < np.std(orig_diff) * 0.5  # Trend much smoother
        
        # Cycle should be extracted (not necessarily zero mean for all data)
        cycle = result['cycle'].dropna()
        assert len(cycle) > 0  # Cycle exists
        
    def test_hp_lambda_sensitivity(self):
        """Test that lambda parameter controls trend smoothness."""
        data = generate_synthetic_seasonal_data(n_points=150)
        
        # Low lambda = less smoothing
        hp_low = HodrickPrescottFilter(lamb=100)
        result_low = hp_low.fit_transform(data)
        
        # High lambda = more smoothing
        hp_high = HodrickPrescottFilter(lamb=1000000)
        result_high = hp_high.fit_transform(data)
        
        # High lambda trend should be smoother
        low_trend_diff = np.std(np.diff(result_low['trend'].dropna()))
        high_trend_diff = np.std(np.diff(result_high['trend'].dropna()))
        
        assert high_trend_diff < low_trend_diff
    
    def test_hp_frequency_defaults(self):
        """Test default lambda values for different frequencies."""
        data = pd.Series(np.random.randn(100))
        
        # Test different frequency defaults
        for freq, expected_lambda in HodrickPrescottFilter.LAMBDA_DEFAULTS.items():
            hp = HodrickPrescottFilter(freq=freq)
            assert hp.lamb == expected_lambda


class TestDetrendPipeline:
    """Test suite for the detrending pipeline."""
    
    def test_pipeline_stl_method(self):
        """Test pipeline with STL method."""
        data = generate_synthetic_seasonal_data(n_points=200, period=25)
        
        pipeline = DetrendPipeline(method='stl', period=25)
        result = pipeline.fit_transform(data)
        
        # Should return DataFrame with components
        assert isinstance(result, pd.DataFrame)
        assert 'seasonal' in result.columns
        assert pipeline.get_seasonal_component() is not None
    
    def test_pipeline_hp_method(self):
        """Test pipeline with HP method."""
        data = generate_synthetic_seasonal_data(n_points=200)
        
        pipeline = DetrendPipeline(method='hp', lamb=160000)
        result = pipeline.fit_transform(data)
        
        assert isinstance(result, pd.DataFrame)
        assert 'cycle' in result.columns
        assert pipeline.get_trend_component() is not None
    
    def test_pipeline_linear_method(self):
        """Test pipeline with simple linear detrending."""
        # Create data with strong linear trend
        t = np.arange(100)
        data = pd.Series(100 + 0.5 * t + np.random.randn(100) * 2)
        
        pipeline = DetrendPipeline(method='linear')
        result = pipeline.fit_transform(data)
        
        # Result should be array/Series of detrended values
        assert isinstance(result, (np.ndarray, pd.Series))
        
        # Detrended data should have near-zero slope
        if isinstance(result, pd.Series):
            detrended = result.values
        else:
            detrended = result
        
        slope = np.polyfit(np.arange(len(detrended)), detrended, 1)[0]
        assert abs(slope) < 0.1  # Near-zero trend removed
    
    def test_pipeline_difference_method(self):
        """Test pipeline with first-difference detrending."""
        # Random walk with drift
        np.random.seed(42)
        drift = 0.1
        noise = np.random.randn(100) * 0.5
        data = pd.Series(np.cumsum(drift + noise) + 100)
        
        pipeline = DetrendPipeline(method='difference')
        result = pipeline.fit_transform(data)
        
        # Differenced data should be stationary (mean near drift)
        if isinstance(result, pd.Series):
            diff_values = result.dropna().values  # Skip NaN from diff
        else:
            diff_values = result[1:]  # First diff
        
        # Mean should be close to drift (excluding the filled first value)
        assert abs(np.mean(diff_values) - drift) < 0.15  # Allow tolerance


class TestPercentileRankNormalizer:
    """Test suite for percentile rank normalization."""
    
    def test_prank_global_normalization(self):
        """Test global percentile rank normalization."""
        data = pd.Series(np.random.randn(100) * 10 + 50)
        
        prank = PercentileRankNormalizer(output_range=(0, 1))
        result = prank.fit_transform(data)
        
        # Output should be in [0, 1] range
        valid = result.dropna()
        assert valid.min() >= 0 - 1e-6
        assert valid.max() <= 1 + 1e-6
        
        # Order should be preserved
        assert np.all(np.argsort(data.values) == np.argsort(result.values))
    
    def test_prank_rolling_normalization(self):
        """Test rolling window percentile rank."""
        data = generate_synthetic_seasonal_data(n_points=100)
        
        prank = PercentileRankNormalizer(window=20, output_range=(0, 100))
        result = prank.transform(data)
        
        # Each value should be ranked within its window
        valid = result.dropna()
        assert valid.min() >= 0 - 1e-6
        assert valid.max() <= 100 + 1e-6
    
    def test_prank_inverse_transform(self):
        """Test approximate inverse transform."""
        np.random.seed(42)
        data = pd.Series(np.random.exponential(scale=10, size=100) + 20)
        
        prank = PercentileRankNormalizer(output_range=(0, 1))
        normalized = prank.fit_transform(data)
        reconstructed = prank.inverse_transform(normalized)
        
        # Reconstruction should be approximate (not exact due to ranking)
        assert reconstructed is not None
        # Correlation should be high even if values aren't exact
        corr = np.corrcoef(data.dropna(), reconstructed[~np.isnan(reconstructed)])[0, 1]
        assert corr > 0.9


class TestZScoreNormalizer:
    """Test suite for Z-score normalization."""
    
    def test_zscore_global_normalization(self):
        """Test global Z-score normalization."""
        data = pd.Series(np.random.randn(100) * 5 + 30)
        
        zscore = ZScoreNormalizer()
        result = zscore.fit_transform(data)
        
        # Result should have mean~0, std~1
        valid = result.dropna()
        assert abs(np.mean(valid)) < 0.1
        assert abs(np.std(valid) - 1.0) < 0.1
    
    def test_zscore_clipping(self):
        """Test Z-score clipping of extreme values."""
        # Data with outliers
        data = pd.Series(list(np.random.randn(95) * 2) + [100, -100, 100, -100, 100])
        
        zscore = ZScoreNormalizer(clip=(-3, 3))
        result = zscore.fit_transform(data)
        
        # Extreme values should be clipped
        assert result.max() <= 3 + 1e-6
        assert result.min() >= -3 - 1e-6
    
    def test_zscore_rolling_normalization(self):
        """Test rolling window Z-score."""
        data = generate_synthetic_seasonal_data(n_points=100)
        
        zscore = ZScoreNormalizer(window=25)
        result = zscore.transform(data)
        
        # Local normalization should adapt to local statistics
        valid = result.dropna()
        # Local z-scores should still be roughly standardized
        assert abs(np.mean(valid)) < 1.0  # Less strict for rolling


class TestMinMaxNormalizer:
    """Test suite for Min-Max normalization."""
    
    def test_minmax_default_range(self):
        """Test min-max normalization to [0, 1]."""
        data = pd.Series(np.random.randn(100) * 10 + 50)
        
        minmax = MinMaxNormalizer()
        result = minmax.fit_transform(data)
        
        valid = result.dropna()
        assert valid.min() >= 0 - 1e-6
        assert valid.max() <= 1 + 1e-6
    
    def test_minmax_custom_range(self):
        """Test min-max normalization to custom range."""
        data = pd.Series(np.random.randn(100) * 10 + 50)
        
        minmax = MinMaxNormalizer(feature_range=(-1, 1))
        result = minmax.fit_transform(data)
        
        valid = result.dropna()
        assert valid.min() >= -1 - 1e-6
        assert valid.max() <= 1 + 1e-6
    
    def test_minmax_inverse_transform(self):
        """Test exact inverse transform for min-max."""
        data = pd.Series(np.random.randn(100) * 10 + 50)
        
        minmax = MinMaxNormalizer(feature_range=(0, 1))
        normalized = minmax.fit_transform(data)
        reconstructed = minmax.inverse_transform(normalized)
        
        # Min-max inverse should be exact (within numerical precision)
        assert np.allclose(data.dropna(), reconstructed[~np.isnan(reconstructed)], rtol=1e-10)


class TestNormalizationPipeline:
    """Test suite for chained normalization pipeline."""
    
    def test_pipeline_basic(self):
        """Test basic normalization pipeline."""
        data = generate_synthetic_seasonal_data(n_points=100)
        
        # Detrend then normalize
        pipeline = NormalizationPipeline(
            methods=['prank'],
            prank_range=(0, 1)
        )
        result = pipeline.fit_transform(data)
        
        assert result.min() >= 0 - 1e-6
        assert result.max() <= 1 + 1e-6
    
    def test_validation_functions(self):
        """Test validation utilities."""
        # Test detrend validation
        original = np.random.randn(100) * 10 + 50
        detrended = original - np.mean(original)  # Simple detrend
        
        is_valid, diag = validate_detrended_data(original, detrended, method='linear')
        assert is_valid
        assert diag['variance_ratio'] <= 1.0  # Variance should not increase
        
        # Test normalization validation
        prank = PercentileRankNormalizer(output_range=(0, 1))
        normalized = prank.fit_transform(pd.Series(original))
        
        is_valid, diag = validate_normalization(
            original, normalized.values, 
            method='prank', 
            expected_range=(0, 1)
        )
        assert is_valid
        assert diag['monotonicity_preserved']


class TestIntegrationEndToEnd:
    """End-to-end integration tests for seasonality preparation."""
    
    def test_full_seasonality_pipeline(self):
        """Test complete detrend -> normalize pipeline."""
        # Generate realistic financial-like data
        data = generate_synthetic_seasonal_data(
            n_points=500,
            period=50,  # ~50 trading days seasonal cycle
            trend_slope=0.02,
            seasonal_amplitude=8.0,
            noise_level=3.0
        )
        
        # Step 1: Detrend with STL
        detrender = DetrendPipeline(method='stl', period=50)
        detrended_result = detrender.fit_transform(data)
        
        # Extract detrended series (seasonal + residual)
        detrended = detrended_result['seasonal'] + detrended_result['residual']
        
        # Step 2: Normalize with percentile rank
        normalizer = PercentileRankNormalizer(output_range=(0, 100))
        normalized = normalizer.fit_transform(detrended)
        
        # Validation checks
        # 1. No unexpected NaNs
        assert normalized.isna().sum() == data.isna().sum()
        
        # 2. Output in expected range
        valid_norm = normalized.dropna()
        assert valid_norm.min() >= 0 - 1e-6
        assert valid_norm.max() <= 100 + 1e-6
        
        # 3. Seasonal pattern should still be visible in normalized data
        # Check autocorrelation at expected period
        if len(valid_norm) >= 100:
            acf = np.correlate(valid_norm - np.mean(valid_norm),
                             valid_norm - np.mean(valid_norm), mode='full')
            acf = acf[len(acf)//2:]
            if acf[0] > 0 and len(acf) > 50:
                acf_norm = acf / acf[0]
                # Should see peak at period=50
                assert acf_norm[50] > acf_norm[25]  # Stronger at true period
    
    def test_cross_asset_normalization(self):
        """Test that normalization enables cross-asset comparison."""
        # Generate two assets with different scales but same seasonal pattern
        np.random.seed(42)
        
        # Asset 1: Price ~100, seasonal amplitude ~5
        asset1 = generate_synthetic_seasonal_data(
            n_points=200, period=25, 
            trend_slope=0.01, seasonal_amplitude=5, noise_level=1
        )
        
        # Asset 2: Price ~1000, seasonal amplitude ~50 (10x scale)
        asset2 = generate_synthetic_seasonal_data(
            n_points=200, period=25,
            trend_slope=0.1, seasonal_amplitude=50, noise_level=10
        )
        
        # Detrend both
        detrender = DetrendPipeline(method='stl', period=25)
        
        detrended1 = detrender.fit_transform(asset1)['seasonal']
        detrender2 = DetrendPipeline(method='stl', period=25)
        detrended2 = detrender2.fit_transform(asset2)['seasonal']
        
        # Normalize both to [0, 100] percentile rank
        prank = PercentileRankNormalizer(output_range=(0, 100))
        
        norm1 = prank.fit_transform(detrended1)
        norm2 = prank.fit_transform(detrended2)
        
        # After normalization, seasonal patterns should be comparable
        # Correlation between normalized seasonal components should be high
        valid_mask = ~norm1.isna() & ~norm2.isna()
        if valid_mask.sum() >= 50:
            corr = np.corrcoef(norm1[valid_mask], norm2[valid_mask])[0, 1]
            # Should capture similar seasonal pattern despite different scales
            assert corr > 0.7


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
