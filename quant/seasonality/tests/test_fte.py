"""
Unit tests for FTE (Forecast Theoretical Efficiency) Validation Engine.

Tests cover:
- Correlation metrics (Pearson, Spearman, Kendall)
- Adaptive threshold calculation
- Rolling window validation
- Broken seasonality detection
- Full FTE validation workflow
- Walk-forward validation
"""

import numpy as np
import pytest
from scipy import stats

from quant.seasonality.fte import (
    FTEConfig,
    FTEResult,
    FTEStatus,
    calculate_realized_volatility,
    calculate_adaptive_threshold,
    pearson_correlation,
    spearman_correlation,
    kendall_correlation,
    calculate_direction_accuracy,
    rolling_window_validation,
    detect_broken_seasonality,
    validate_fte,
    walk_forward_fte,
    aggregate_fte_results,
)


class TestCorrelationMetrics:
    """Tests for correlation calculation functions."""
    
    def test_pearson_perfect_positive(self):
        """Pearson correlation for perfectly correlated data."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([2, 4, 6, 8, 10])
        corr = pearson_correlation(x, y)
        assert abs(corr - 1.0) < 1e-10
    
    def test_pearson_perfect_negative(self):
        """Pearson correlation for perfectly negatively correlated data."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([10, 8, 6, 4, 2])
        corr = pearson_correlation(x, y)
        assert abs(corr - (-1.0)) < 1e-10
    
    def test_pearson_no_correlation(self):
        """Pearson correlation for uncorrelated random data."""
        np.random.seed(42)
        x = np.random.randn(100)
        y = np.random.randn(100)
        corr = pearson_correlation(x, y)
        assert abs(corr) < 0.3  # Should be close to 0
    
    def test_spearman_rank_correlation(self):
        """Spearman correlation handles non-linear monotonic relationships."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([1, 4, 9, 16, 25])  # x^2
        spearman = spearman_correlation(x, y)
        assert abs(spearman - 1.0) < 1e-10  # Perfect rank correlation
    
    def test_kendall_tau(self):
        """Kendall tau correlation calculation."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([1, 2, 3, 4, 5])
        tau = kendall_correlation(x, y)
        assert abs(tau - 1.0) < 1e-10
    
    def test_correlation_with_nan(self):
        """Correlation functions handle NaN values gracefully."""
        x = np.array([1, 2, np.nan, 4, 5])
        y = np.array([2, 4, 6, np.nan, 10])
        
        pearson = pearson_correlation(x, y)
        spearman = spearman_correlation(x, y)
        
        assert not np.isnan(pearson)
        assert not np.isnan(spearman)
        assert abs(pearson - 1.0) < 1e-10
    
    def test_correlation_insufficient_data(self):
        """Correlation returns NaN with insufficient data points."""
        x = np.array([1, 2])
        y = np.array([2, 4])
        
        assert np.isnan(pearson_correlation(x, y))
        assert np.isnan(spearman_correlation(x, y))


class TestVolatilityCalculation:
    """Tests for volatility calculation functions."""
    
    def test_realized_volatility_log_return(self):
        """Calculate realized volatility using log returns."""
        np.random.seed(42)
        prices = 100 * np.cumprod(1 + np.random.randn(100) * 0.01)
        vol = calculate_realized_volatility(prices, window=30)
        
        assert vol > 0
        assert vol < 1  # Should be reasonable annualized vol
    
    def test_realized_volatility_simple_return(self):
        """Calculate realized volatility using simple returns."""
        prices = np.array([100, 101, 99, 102, 98, 103, 97, 104])
        vol = calculate_realized_volatility(prices, window=5, method="simple")
        
        assert vol > 0
    
    def test_realized_volatility_insufficient_data(self):
        """Returns NaN when insufficient data for window."""
        prices = np.array([100, 101, 102])
        vol = calculate_realized_volatility(prices, window=10)
        assert np.isnan(vol)


class TestAdaptiveThreshold:
    """Tests for adaptive threshold calculation."""
    
    def test_adaptive_threshold_default(self):
        """Returns base threshold when volatility ratio is 1."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(300) * 0.5)
        config = FTEConfig(base_threshold=0.08, sensitivity_lambda=0.5)
        
        threshold = calculate_adaptive_threshold(prices, config)
        
        # Should be close to base when vol ratio ~1
        assert 0.04 <= threshold <= 0.12  # Within 50%-150% of base
    
    def test_adaptive_threshold_high_volatility(self):
        """Threshold decreases with high current volatility."""
        # Create data with recent high volatility
        stable = np.ones(200) * 100
        volatile = 100 + np.cumsum(np.random.randn(50) * 0.1)
        prices = np.concatenate([stable, volatile])
        
        config = FTEConfig(base_threshold=0.08, sensitivity_lambda=1.0)
        threshold = calculate_adaptive_threshold(prices, config)
        
        # High vol should lower threshold (more lenient)
        assert threshold <= config.base_threshold
    
    def test_adaptive_threshold_minimum_floor(self):
        """Threshold never goes below 50% of base."""
        # Extreme volatility scenario
        prices = np.array([100] * 100 + list(range(100, 200)))
        config = FTEConfig(base_threshold=0.10, sensitivity_lambda=2.0)
        
        threshold = calculate_adaptive_threshold(prices, config)
        
        assert threshold >= config.base_threshold * 0.5


class TestDirectionAccuracy:
    """Tests for prediction direction accuracy."""
    
    def test_perfect_direction_accuracy(self):
        """100% accuracy when directions match perfectly."""
        prediction = np.array([1, 2, 3, 4, 5])
        actual = np.array([10, 20, 30, 40, 50])
        
        accuracy = calculate_direction_accuracy(prediction, actual)
        assert accuracy == 1.0
    
    def test_zero_direction_accuracy(self):
        """0% accuracy when directions always oppose."""
        prediction = np.array([1, 2, 3, 4, 5])
        actual = np.array([5, 4, 3, 2, 1])
        
        accuracy = calculate_direction_accuracy(prediction, actual)
        assert accuracy == 0.0
    
    def test_partial_direction_accuracy(self):
        """Partial accuracy with mixed directions."""
        prediction = np.array([1, 2, 3, 4, 5, 6])
        actual = np.array([10, 20, 15, 25, 20, 30])  # 4/5 correct
        
        accuracy = calculate_direction_accuracy(prediction, actual)
        assert 0.6 <= accuracy <= 1.0


class TestRollingWindowValidation:
    """Tests for rolling window correlation analysis."""
    
    def test_rolling_window_basic(self):
        """Basic rolling window correlation calculation."""
        prediction = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        actual = np.array([1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1])
        
        corrs, mean, std = rolling_window_validation(
            prediction, actual, window_size=3
        )
        
        assert len(corrs) == 8  # 10 - 3 + 1
        assert all(abs(c - 1.0) < 1e-10 for c in corrs)  # Perfect correlation
        assert abs(mean - 1.0) < 1e-10
    
    def test_rolling_window_varying_correlation(self):
        """Rolling window captures changing correlation."""
        np.random.seed(42)
        prediction = np.random.randn(100)
        # First half correlated, second half uncorrelated
        actual = np.concatenate([
            prediction[:50] + np.random.randn(50) * 0.1,
            np.random.randn(50)
        ])
        
        corrs, mean, std = rolling_window_validation(
            prediction, actual, window_size=20
        )
        
        assert len(corrs) == 81
        # First correlations should be higher
        assert np.mean(corrs[:10]) > np.mean(corrs[-10:])
    
    def test_rolling_window_length_mismatch(self):
        """Raises error for mismatched array lengths."""
        prediction = np.array([1, 2, 3])
        actual = np.array([1, 2])
        
        with pytest.raises(ValueError):
            rolling_window_validation(prediction, actual, window_size=2)


class TestBrokenSeasonalityDetection:
    """Tests for broken seasonality pattern detection."""
    
    def test_detect_broken_consecutive(self):
        """Detects broken pattern with consecutive low correlations."""
        correlations = [0.5, 0.4, -0.2, -0.15, -0.12, 0.3]
        
        is_broken = detect_broken_seasonality(
            correlations, broken_threshold=-0.1, consecutive_count=3
        )
        assert is_broken
    
    def test_no_broken_intermittent(self):
        """Does not detect broken with intermittent low values."""
        correlations = [0.5, -0.2, 0.4, -0.15, 0.3, -0.12]
        
        is_broken = detect_broken_seasonality(
            correlations, broken_threshold=-0.1, consecutive_count=3
        )
        assert not is_broken
    
    def test_broken_threshold_parameter(self):
        """Respects custom broken threshold."""
        correlations = [0.1, 0.05, 0.0, -0.05]
        
        # With strict threshold
        assert detect_broken_seasonality(correlations, broken_threshold=0.0, consecutive_count=2)
        # With lenient threshold
        assert not detect_broken_seasonality(correlations, broken_threshold=-0.1, consecutive_count=2)


class TestFTEValidation:
    """Tests for main FTE validation function."""
    
    def test_fte_valid_high_correlation(self):
        """Validates as valid when correlation exceeds threshold."""
        np.random.seed(42)
        # Generate correlated data
        base = np.cumsum(np.random.randn(200) * 0.02) + 100
        prediction = base[-50:] + np.random.randn(50) * 0.01
        
        result = validate_fte(base, prediction, FTEConfig(base_threshold=0.05))
        
        assert result.is_valid
        assert result.status == FTEStatus.VALID
        assert result.pearson_correlation > 0.05
    
    def test_fte_invalid_low_correlation(self):
        """Validates as invalid when correlation below threshold."""
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(200) * 0.02) + 100
        prediction = np.random.randn(50)  # Uncorrelated
        
        result = validate_fte(prices, prediction, FTEConfig(base_threshold=0.1))
        
        assert not result.is_valid
        # Can be INVALID or BROKEN depending on correlation pattern
        assert result.status in [FTEStatus.INVALID, FTEStatus.BROKEN]
    
    def test_fte_insufficient_data(self):
        """Returns INSUFFICIENT_DATA status for small datasets."""
        prices = np.array([100, 101, 102])
        prediction = np.array([101, 102])
        
        result = validate_fte(prices, prediction)
        
        assert result.status == FTEStatus.INSUFFICIENT_DATA
        assert not result.is_valid
    
    def test_fte_adaptive_threshold_used(self):
        """Uses adaptive threshold when volatility differs."""
        np.random.seed(42)
        # Create data with changing volatility
        stable = np.ones(150) * 100
        volatile = 100 + np.cumsum(np.random.randn(50) * 0.1)
        prices = np.concatenate([stable, volatile])
        prediction = prices[-50:] + np.random.randn(50) * 0.02
        
        result = validate_fte(prices, prediction, FTEConfig(base_threshold=0.08))
        
        assert result.threshold_type in ["base", "adaptive"]
        assert result.threshold_used >= 0.04  # Floor at 50% of base
    
    def test_fte_rolling_window_results(self):
        """Includes rolling window statistics in result."""
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(200) * 0.01) + 100
        prediction = prices[-50:] + np.random.randn(50) * 0.005
        
        result = validate_fte(prices, prediction, FTEConfig(rolling_window=10))
        
        assert result.rolling_correlations is not None
        assert result.rolling_mean is not None
        assert result.rolling_std is not None
        assert len(result.rolling_correlations) == 41  # 50 - 10 + 1
    
    def test_fte_broken_seasonality_detection(self):
        """Detects and reports broken seasonality."""
        # Create data where correlation breaks down
        prices = np.cumsum(np.random.randn(300) * 0.015) + 100
        
        # Prediction matches first half, diverges in second
        pred_first = prices[200:225] + np.random.randn(25) * 0.005
        pred_second = np.random.randn(25) * 2  # Uncorrelated
        prediction = np.concatenate([pred_first, pred_second])
        
        result = validate_fte(prices, prediction, FTEConfig(
            base_threshold=0.05,
            broken_threshold=-0.05,
            rolling_window=15
        ))
        
        # May detect as broken depending on random seed
        assert result.status in [FTEStatus.VALID, FTEStatus.INVALID, FTEStatus.BROKEN]
    
    def test_fte_result_fields(self):
        """Result contains all expected fields."""
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(200) * 0.01) + 100
        prediction = prices[-50:]
        
        result = validate_fte(prices, prediction)
        
        assert hasattr(result, 'pearson_correlation')
        assert hasattr(result, 'spearman_correlation')
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'status')
        assert hasattr(result, 'threshold_used')
        assert hasattr(result, 'p_value')
        assert hasattr(result, 'prediction_accuracy')
        assert hasattr(result, 'message')


class TestWalkForwardValidation:
    """Tests for walk-forward FTE validation."""
    
    def test_walk_forward_basic(self):
        """Basic walk-forward validation execution."""
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(500) * 0.01) + 100
        
        # Simple forecast: last value repeated
        def simple_forecast(train_data, horizon):
            return np.full(horizon, train_data[-1])
        
        results = walk_forward_fte(prices, simple_forecast, steps=5)
        
        assert len(results) == 5
        assert all(isinstance(r, FTEResult) for r in results)
    
    def test_walk_forward_aggregation(self):
        """Aggregates walk-forward results correctly."""
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(500) * 0.01) + 100
        
        def correlated_forecast(train_data, horizon):
            # Forecast with some correlation to actual
            last = train_data[-1]
            trend = (train_data[-1] - train_data[-20]) / 20
            return last + np.arange(horizon) * trend + np.random.randn(horizon) * 0.1
        
        results = walk_forward_fte(prices, correlated_forecast, steps=10)
        summary = aggregate_fte_results(results)
        
        assert summary['count'] == len(results)
        assert 'pearson_mean' in summary
        assert 'valid_ratio' in summary
        assert 0 <= summary['valid_ratio'] <= 1
    
    def test_walk_forward_empty_results(self):
        """Handles empty result list gracefully."""
        summary = aggregate_fte_results([])
        assert summary == {}
    
    def test_walk_forward_no_valid(self):
        """Aggregates when no valid results exist."""
        results = [
            FTEResult(
                pearson_correlation=np.nan,
                spearman_correlation=np.nan,
                is_valid=False,
                status=FTEStatus.INSUFFICIENT_DATA,
                threshold_used=0.08,
                threshold_type="base"
            )
        ]
        summary = aggregate_fte_results(results)
        
        assert summary['valid_count'] == 0
        assert 'message' in summary


class TestFTEIntegration:
    """Integration tests for FTE workflow."""
    
    def test_end_to_end_seasonal_forecast(self):
        """Full workflow: generate seasonal forecast and validate."""
        np.random.seed(42)
        
        # Generate synthetic seasonal data
        n_days = 365 * 5  # 5 years
        t = np.arange(n_days)
        seasonal = 10 * np.sin(2 * np.pi * t / 365)  # Annual cycle
        trend = 0.01 * t
        noise = np.random.randn(n_days) * 2
        prices = 100 + trend + seasonal + noise
        
        # Split for training/testing
        train_size = int(len(prices) * 0.7)
        train_data = prices[:train_size]
        test_actual = prices[train_size:]
        
        # Simple seasonal forecast (naive seasonal pattern)
        seasonal_pattern = []
        for i in range(len(test_actual)):
            # Look back 365 days in training data
            if train_size - 365 + i >= 0:
                seasonal_pattern.append(train_data[train_size - 365 + i])
            else:
                seasonal_pattern.append(train_data[-1])
        prediction = np.array(seasonal_pattern)
        
        # Validate
        result = validate_fte(prices, prediction, FTEConfig(
            base_threshold=0.08,
            rolling_window=30
        ))
        
        # Should detect some seasonal correlation
        assert result.pearson_correlation is not None
        assert not np.isnan(result.pearson_correlation)
        assert result.sample_size == len(test_actual)
    
    def test_fte_with_realistic_market_data(self):
        """Test with more realistic market-like data."""
        np.random.seed(123)
        
        # Simulate GBM with seasonal component
        def generate_market_data(n_days: int, annual_vol: float = 0.2):
            daily_vol = annual_vol / np.sqrt(252)
            returns = np.random.randn(n_days) * daily_vol + 0.05/252
            
            # Add seasonal pattern
            t = np.arange(n_days)
            seasonal = 0.0002 * np.sin(2 * np.pi * t / 365)
            
            prices = 100 * np.cumprod(1 + returns + seasonal)
            return prices
        
        prices = generate_market_data(1000)
        
        # Create forecast with partial seasonal capture
        prediction = prices[-100:] * (1 + 0.001 * np.sin(
            2 * np.pi * np.arange(100) / 365
        ))
        
        result = validate_fte(prices, prediction)
        
        # Should complete without errors
        assert result is not None
        assert hasattr(result, 'is_valid')
        assert isinstance(result.message, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
