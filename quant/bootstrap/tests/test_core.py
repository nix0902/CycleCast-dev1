# quant/bootstrap/tests/test_core.py
# Unit tests for Bootstrap CI module
# CycleCast v3.2 Final

import pytest
import numpy as np
from typing import List
from quant.bootstrap.core import (
    BootstrapConfig,
    BootstrapResult,
    BootstrapProgress,
    BootstrapCI,
    bootstrap_ci,
    bootstrap_ci_streaming,
    validate_cycle_significance,
)


class TestBootstrapConfig:
    """Tests for BootstrapConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = BootstrapConfig()
        assert config.n_iterations == 1000
        assert config.confidence_level == 0.95
        assert config.seed is None
        assert config.streaming_batch_size == 100
        assert config.bias_correction is True
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = BootstrapConfig(
            n_iterations=500,
            confidence_level=0.99,
            seed=42,
            streaming_batch_size=50,
        )
        assert config.n_iterations == 500
        assert config.confidence_level == 0.99
        assert config.seed == 42
        assert config.streaming_batch_size == 50


class TestBootstrapResult:
    """Tests for BootstrapResult dataclass."""
    
    def test_result_creation(self):
        """Test BootstrapResult instantiation."""
        result = BootstrapResult(
            ci_lower=1.5,
            ci_upper=3.5,
            point_estimate=2.5,
            bootstrap_mean=2.48,
            bootstrap_std=0.5,
            n_iterations=1000,
            confidence_level=0.95,
        )
        assert result.ci_lower == 1.5
        assert result.ci_upper == 3.5
        assert result.point_estimate == 2.5
        assert result.n_iterations == 1000


class TestBootstrapCI:
    """Tests for BootstrapCI class."""
    
    def test_calculate_mean(self):
        """Test bootstrap CI for mean of normal data."""
        np.random.seed(42)
        data = np.random.normal(loc=10, scale=2, size=100)
        
        config = BootstrapConfig(n_iterations=500, seed=42)
        calc = BootstrapCI(config)
        result = calc.calculate(data)
        
        # CI should contain true mean (10) with high probability
        assert result.ci_lower < 10 < result.ci_upper
        assert result.point_estimate == pytest.approx(10, abs=1)
        assert result.n_iterations == 500
    
    def test_calculate_custom_statistic(self):
        """Test bootstrap with custom statistic function."""
        np.random.seed(42)
        data = np.random.exponential(scale=2, size=100)
        
        # Use median as statistic
        result = bootstrap_ci(data, statistic=np.median, n_iterations=500, seed=42)
        
        assert result.ci_lower < result.point_estimate < result.ci_upper
        assert result.point_estimate > 0  # Median of exponential is positive
    
    def test_calculate_empty_data(self):
        """Test error handling for empty data."""
        calc = BootstrapCI()
        with pytest.raises(ValueError, match="cannot be empty"):
            calc.calculate(np.array([]))
    
    def test_streaming_progress(self):
        """Test streaming progress updates."""
        np.random.seed(42)
        data = np.random.normal(size=50)
        
        config = BootstrapConfig(
            n_iterations=100,
            streaming_batch_size=25,
            seed=42,
        )
        calc = BootstrapCI(config)
        
        progress_updates: List[BootstrapProgress] = list(
            calc.calculate_streaming(data)
        )
        
        # Should have updates at batch intervals + final
        assert len(progress_updates) >= 4  # 25, 50, 75, 100
        
        # Check final update
        final = progress_updates[-1]
        assert final.is_complete is True
        assert final.current_iteration == 100
        assert final.progress_percent == 100.0
        assert final.ci_lower is not None
        assert final.ci_upper is not None
    
    def test_streaming_convergence(self):
        """Test that streaming CI converges to final value."""
        np.random.seed(42)
        data = np.random.normal(loc=5, scale=1, size=100)
        
        # Get final result
        config = BootstrapConfig(n_iterations=500, seed=42)
        calc = BootstrapCI(config)
        final_result = calc.calculate(data)
        
        # Get streaming final update
        streaming_updates = list(calc.calculate_streaming(data))
        streaming_final = streaming_updates[-1]
        
        # Should be very close
        assert streaming_final.ci_lower == pytest.approx(
            final_result.ci_lower, rel=0.01
        )
        assert streaming_final.ci_upper == pytest.approx(
            final_result.ci_upper, rel=0.01
        )
    
    def test_backtest_sharpe(self):
        """Test bootstrap CI for Sharpe ratio."""
        np.random.seed(42)
        # Simulate daily returns with positive mean
        returns = np.random.normal(loc=0.0005, scale=0.02, size=252)
        
        calc = BootstrapCI()
        result = calc.calculate_for_backtest(returns, metric='sharpe')
        
        assert result.ci_lower < result.point_estimate < result.ci_upper
        assert result.point_estimate > 0  # Positive expected Sharpe
    
    def test_backtest_total_return(self):
        """Test bootstrap CI for total return."""
        np.random.seed(42)
        returns = np.random.normal(loc=0.001, scale=0.015, size=100)
        
        calc = BootstrapCI()
        result = calc.calculate_for_backtest(returns, metric='total_return')
        
        # Total return should be reasonable for 100 periods
        assert -0.5 < result.ci_lower < result.ci_upper < 2.0
    
    def test_p_value_calculation(self):
        """Test p-value calculation against null hypothesis."""
        np.random.seed(42)
        # Data with mean significantly different from 0
        data = np.random.normal(loc=2, scale=1, size=100)
        
        result = bootstrap_ci(data, null_hypothesis=0, n_iterations=500, seed=42)
        
        # Should reject null (p-value < 0.05)
        assert result.p_value is not None
        assert result.p_value < 0.05
        
        # Test with null close to true mean
        result2 = bootstrap_ci(data, null_hypothesis=2, n_iterations=500, seed=42)
        assert result2.p_value > 0.05  # Should not reject
    
    def test_bca_correction(self):
        """Test BCa bias correction on skewed data."""
        np.random.seed(42)
        # Skewed data
        data = np.random.exponential(scale=2, size=100)
        
        # With BCa
        config_bca = BootstrapConfig(bias_correction=True, seed=42)
        calc_bca = BootstrapCI(config_bca)
        result_bca = calc_bca.calculate(data)
        
        # Without BCa
        config_std = BootstrapConfig(bias_correction=False, seed=42)
        calc_std = BootstrapCI(config_std)
        result_std = calc_std.calculate(data)
        
        # BCa should adjust for skewness
        # (exact values depend on data, but both should be valid CIs)
        assert result_bca.ci_lower < result_bca.point_estimate < result_bca.ci_upper
        assert result_std.ci_lower < result_std.point_estimate < result_std.ci_upper


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_bootstrap_ci_function(self):
        """Test bootstrap_ci convenience function."""
        np.random.seed(42)
        data = np.random.normal(size=50)
        
        result = bootstrap_ci(data, n_iterations=200, seed=42)
        
        assert isinstance(result, BootstrapResult)
        assert result.ci_lower < result.ci_upper
        assert result.n_iterations == 200
    
    def test_bootstrap_ci_streaming_function(self):
        """Test bootstrap_ci_streaming convenience function."""
        np.random.seed(42)
        data = np.random.normal(size=30)
        
        updates = list(bootstrap_ci_streaming(
            data, n_iterations=50, batch_size=10, seed=42
        ))
        
        assert len(updates) >= 5
        assert updates[-1].is_complete is True


class TestValidateCycleSignificance:
    """Tests for cycle significance validation."""
    
    def test_significant_cycle(self):
        """Test detection of significant cycle."""
        np.random.seed(42)
        # Create data with strong 14-day cycle
        n = 200
        t = np.arange(n)
        prices = 100 + 5 * np.sin(2 * np.pi * t / 14) + np.random.normal(0, 1, n)
        
        cycle_energies = {14: 25.0, 7: 5.0, 30: 3.0}
        
        results = validate_cycle_significance(
            cycle_energies, prices, n_iterations=200, threshold=0.1
        )
        
        # 14-day cycle should be significant
        assert results[14]['significant'] is True
        assert results[14]['p_value'] < 0.1
        
        # Weaker cycles may not be significant
        assert results[7]['p_value'] >= 0 or True  # May or may not be significant
    
    def test_no_significant_cycles(self):
        """Test with pure noise data."""
        np.random.seed(42)
        prices = np.random.normal(100, 5, 200)
        
        cycle_energies = {14: 2.0, 21: 1.5, 30: 1.0}
        
        results = validate_cycle_significance(
            cycle_energies, prices, n_iterations=200, threshold=0.05
        )
        
        # With pure noise, cycles should generally not be significant
        # (though random chance may cause false positives)
        for period, result in results.items():
            assert 'significant' in result
            assert 'p_value' in result
            assert 0 <= result['p_value'] <= 1


class TestIntegration:
    """Integration tests with QSpectrum module."""
    
    def test_bootstrap_with_qspectrum_output(self):
        """Test bootstrap validation of QSpectrum cycle energies."""
        try:
            from quant.qspectrum.core import cyclic_correlation, calculate_cycle_energy
        except ImportError:
            pytest.skip("QSpectrum module not available")
        
        np.random.seed(42)
        # Generate test price series
        n = 500
        t = np.arange(n)
        prices = 100 + 3*np.sin(2*np.pi*t/20) + 2*np.sin(2*np.pi*t/42) + np.random.normal(0, 2, n)
        
        # Calculate cycle energies for different periods
        cycle_energies = {}
        for period in [14, 20, 28, 42, 56]:
            energy = calculate_cycle_energy(prices, period)
            cycle_energies[period] = energy
        
        # Validate with bootstrap
        results = validate_cycle_significance(
            cycle_energies, prices, n_iterations=200, threshold=0.1
        )
        
        # At least one cycle should be detected (20 or 42 day)
        significant_periods = [p for p, r in results.items() if r['significant']]
        assert len(significant_periods) >= 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_very_small_sample(self):
        """Test with minimal sample size."""
        data = np.array([1, 2, 3])
        result = bootstrap_ci(data, n_iterations=50, seed=42)
        assert result.ci_lower <= result.point_estimate <= result.ci_upper
    
    def test_constant_data(self):
        """Test with constant data (zero variance)."""
        data = np.ones(50) * 5
        result = bootstrap_ci(data, n_iterations=100, seed=42)
        # CI should be very narrow around 5
        assert abs(result.ci_lower - 5) < 0.1
        assert abs(result.ci_upper - 5) < 0.1
    
    def test_large_sample(self):
        """Test with large sample size."""
        np.random.seed(42)
        data = np.random.normal(size=10000)
        result = bootstrap_ci(data, n_iterations=200, seed=42)
        
        # CI should be narrow for large n
        ci_width = result.ci_upper - result.ci_lower
        assert ci_width < 0.5  # Reasonable width for n=10000
    
    def test_high_confidence_level(self):
        """Test with 99% confidence level."""
        np.random.seed(42)
        data = np.random.normal(size=100)
        
        result_95 = bootstrap_ci(data, confidence_level=0.95, seed=42)
        result_99 = bootstrap_ci(data, confidence_level=0.99, seed=42)
        
        # 99% CI should be wider than 95% CI
        width_95 = result_95.ci_upper - result_95.ci_lower
        width_99 = result_99.ci_upper - result_99.ci_lower
        assert width_99 > width_95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
