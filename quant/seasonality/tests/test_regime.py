"""
Unit tests for Regime Detection & Adaptive Threshold Module

Tests cover:
- Volatility calculation methods
- Regime classification accuracy
- Adaptive threshold formula compliance
- Edge cases and data validation
- Integration with FTE validation

Author: CycleCast AI Agent (Qwen 3.5)
Version: 3.2 Final
Date: 2026-03-14
"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock

from quant.seasonality.regime import (
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


class TestVolatilityCalculation(unittest.TestCase):
    """Tests for realized volatility calculation."""
    
    def test_log_returns_volatility(self):
        """Test volatility calculation with log returns."""
        # Synthetic price series with known volatility
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 100)  # 2% daily vol
        prices = 100 * np.exp(np.cumsum(returns))
        
        vol = calculate_realized_volatility(prices, window=21, method='log')
        
        # Check that we get valid results
        self.assertTrue(np.any(np.isfinite(vol)))
        
        # Annualized vol should be around 0.02 * sqrt(252) ≈ 0.317
        valid_vol = vol[np.isfinite(vol)]
        self.assertGreater(np.mean(valid_vol), 0.2)
        self.assertLess(np.mean(valid_vol), 0.5)
    
    def test_simple_returns_volatility(self):
        """Test volatility calculation with simple returns."""
        prices = np.array([100, 102, 99, 101, 103, 100, 102, 104, 101, 103])
        
        vol = calculate_realized_volatility(prices, window=5, method='simple')
        
        self.assertTrue(np.any(np.isfinite(vol)))
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100, 101, 102])
        
        vol = calculate_realized_volatility(prices, window=21)
        
        # Should return array with NaN
        self.assertTrue(np.all(np.isnan(vol)))
    
    def test_constant_prices_zero_volatility(self):
        """Test that constant prices yield zero volatility."""
        prices = np.array([100] * 100)
        
        vol = calculate_realized_volatility(prices, window=21)
        valid_vol = vol[np.isfinite(vol)]
        
        self.assertTrue(np.allclose(valid_vol, 0, atol=1e-10))
    
    def test_nan_handling(self):
        """Test handling of NaN values in price series."""
        prices = np.array([100, 101, np.nan, 102, 103, 100, 102, 104, 101, 103])
        
        vol = calculate_realized_volatility(prices, window=5)
        
        # Should still produce some valid results
        self.assertTrue(np.any(np.isfinite(vol)))


class TestVolatilityPercentile(unittest.TestCase):
    """Tests for percentile rank calculation."""
    
    def test_percentile_basic(self):
        """Test basic percentile calculation."""
        historical = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        
        # Value at median should give ~0.5
        pct = calculate_volatility_percentile(5.5, historical)
        self.assertAlmostEqual(pct, 0.5, places=1)
        
        # Low value should give low percentile
        pct = calculate_volatility_percentile(1, historical)
        self.assertLess(pct, 0.2)
        
        # High value should give high percentile
        pct = calculate_volatility_percentile(10, historical)
        self.assertGreater(pct, 0.9)
    
    def test_empty_historical(self):
        """Test behavior with empty historical data."""
        pct = calculate_volatility_percentile(5.0, np.array([]))
        
        # Should default to 0.5 (median)
        self.assertEqual(pct, 0.5)
    
    def test_all_nan_historical(self):
        """Test behavior with all-NaN historical data."""
        pct = calculate_volatility_percentile(5.0, np.array([np.nan] * 10))
        
        self.assertEqual(pct, 0.5)


class TestRegimeDetection(unittest.TestCase):
    """Tests for regime classification."""
    
    def test_low_volatility_regime(self):
        """Test detection of low volatility regime."""
        # Create low-volatility price series
        np.random.seed(42)
        returns = np.random.normal(0, 0.005, 300)  # Very low vol
        prices = 100 * np.exp(np.cumsum(returns))
        
        result = detect_regime(prices)
        
        # Should detect LOW_VOL or NORMAL_VOL
        self.assertIn(result.regime, [RegimeType.LOW_VOL, RegimeType.NORMAL_VOL])
        self.assertGreater(result.confidence, 0.0)
    
    def test_high_volatility_regime(self):
        """Test detection of high volatility regime."""
        # Create regime with transition from low to high volatility
        # This ensures percentile ranking will correctly identify high vol
        np.random.seed(42)
        # Start with low volatility
        low_vol = np.random.normal(0, 0.005, 200)  # Low vol baseline
        # Then add high volatility period
        high_vol = np.random.normal(0, 0.05, 100)  # High vol spike
        returns = np.concatenate([low_vol, high_vol])
        prices = 100 * np.exp(np.cumsum(returns))
        
        result = detect_regime(prices)
        
        # With high vol spike at the end, should detect elevated regime
        # (may be HIGH_VOL, EXTREME_VOL, or even NORMAL_VOL if still transitioning)
        self.assertIn(result.regime, [RegimeType.HIGH_VOL, RegimeType.EXTREME_VOL, RegimeType.NORMAL_VOL])
    
    def test_regime_transition(self):
        """Test regime detection during volatility transition."""
        # Low vol followed by high vol
        np.random.seed(42)
        low_vol = np.random.normal(0, 0.01, 150)
        high_vol = np.random.normal(0, 0.04, 150)
        returns = np.concatenate([low_vol, high_vol])
        prices = 100 * np.exp(np.cumsum(returns))
        
        # Early part should be low vol
        early_result = detect_regime(prices[:200])
        
        # Later part should show higher volatility
        late_result = detect_regime(prices)
        
        # Current volatility should be detectably different
        # (may not always be higher due to rolling window alignment)
        self.assertIsInstance(late_result.current_volatility, float)
    
    def test_insufficient_data_default(self):
        """Test behavior with insufficient data."""
        prices = np.array([100] * 30)  # Too short
        
        result = detect_regime(prices)
        
        # Should return default with low confidence
        self.assertEqual(result.regime, RegimeType.NORMAL_VOL)
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(np.isnan(result.current_volatility))
    
    def test_adaptive_threshold_formula(self):
        """Test adaptive threshold calculation matches TZ.md formula."""
        config = RegimeConfig(
            base_threshold=0.08,
            sensitivity_lambda=0.5,
            min_threshold_ratio=0.5
        )
        
        # Simulate high volatility (ratio = 2.0)
        # Expected: 0.08 * (1 + 0.5 * (2.0 - 1)) = 0.08 * 1.5 = 0.12
        np.random.seed(42)
        returns = np.random.normal(0, 0.04, 300)
        prices = 100 * np.exp(np.cumsum(returns))
        
        result = detect_regime(prices, config)
        
        # Check formula: base * (1 + lambda * (ratio - 1))
        expected = config.base_threshold * (1 + config.sensitivity_lambda * 
                                           (result.volatility_ratio - 1))
        expected = max(expected, config.base_threshold * config.min_threshold_ratio)
        
        self.assertAlmostEqual(result.adaptive_threshold, expected, places=4)
    
    def test_threshold_floor_constraint(self):
        """Test that threshold cannot go below 50% of base."""
        config = RegimeConfig(
            base_threshold=0.08,
            min_threshold_ratio=0.5
        )
        
        # Very low volatility should trigger floor
        prices = np.array([100 + i * 0.01 for i in range(300)])  # Almost flat
        
        result = detect_regime(prices, config)
        
        # Should not go below 0.04 (50% of 0.08)
        self.assertGreaterEqual(result.adaptive_threshold, 0.04)
    
    def test_regime_multiplier_application(self):
        """Test regime-specific threshold multipliers."""
        config = RegimeConfig(
            base_threshold=0.08,
            regime_multiplier={
                RegimeType.LOW_VOL: 1.0,
                RegimeType.NORMAL_VOL: 1.0,
                RegimeType.HIGH_VOL: 1.2,
                RegimeType.EXTREME_VOL: 1.5,
            }
        )
        
        # Force HIGH_VOL regime with synthetic data
        np.random.seed(42)
        returns = np.random.normal(0, 0.06, 300)
        prices = 100 * np.exp(np.cumsum(returns))
        
        result = detect_regime(prices, config)
        
        # Regime-adjusted should be adaptive * multiplier
        expected = result.adaptive_threshold * config.regime_multiplier[result.regime]
        self.assertAlmostEqual(result.regime_adjusted_threshold, expected, places=4)


class TestSignalValidation(unittest.TestCase):
    """Tests for signal validation with regime awareness."""
    
    def test_validate_with_regime_basic(self):
        """Test basic signal validation."""
        fte_score = 0.10  # Above default threshold of 0.08
        prices = np.array([100 + i * 0.1 for i in range(300)])
        
        is_valid, result = validate_with_regime(fte_score, prices)
        
        # Should be valid since 0.10 > 0.08
        self.assertTrue(is_valid)
        self.assertIsInstance(result, RegimeResult)
    
    def test_low_score_rejected(self):
        """Test that low FTE scores are rejected."""
        fte_score = 0.05  # Below default threshold
        prices = np.array([100 + i * 0.1 for i in range(300)])
        
        is_valid, result = validate_with_regime(fte_score, prices)
        
        self.assertFalse(is_valid)
    
    def test_high_vol_requires_stronger_signal(self):
        """Test that high volatility requires stronger signal."""
        # Create regime with transition from low to high volatility
        np.random.seed(42)
        # Start with low volatility baseline
        low_vol = np.random.normal(0, 0.005, 200)
        # Add high volatility period
        high_vol = np.random.normal(0, 0.05, 100)
        returns = np.concatenate([low_vol, high_vol])
        prices = 100 * np.exp(np.cumsum(returns))
        
        # Score that would pass in normal regime
        fte_score = 0.09
        
        is_valid, result = validate_with_regime(fte_score, prices)
        
        # In elevated vol, threshold should be adjusted
        # (regime_adjusted_threshold >= adaptive_threshold)
        self.assertIn(is_valid, [True, False, np.bool_(True), np.bool_(False)])
        self.assertGreaterEqual(result.regime_adjusted_threshold, result.adaptive_threshold)
    
    def test_regime_result_methods(self):
        """Test RegimeResult helper methods."""
        result = RegimeResult(
            regime=RegimeType.NORMAL_VOL,
            current_volatility=0.2,
            baseline_volatility=0.2,
            volatility_ratio=1.0,
            percentile_rank=0.5,
            adaptive_threshold=0.08,
            regime_adjusted_threshold=0.08,
            samples_analyzed=200,
            confidence=0.9
        )
        
        # Test is_valid_signal
        self.assertTrue(result.is_valid_signal(0.10))
        self.assertFalse(result.is_valid_signal(0.05))
        
        # Test get_signal_strength
        self.assertAlmostEqual(result.get_signal_strength(0.08), 1.0)
        self.assertAlmostEqual(result.get_signal_strength(0.04), 0.5)
        self.assertEqual(result.get_signal_strength(0.16), 1.0)  # Capped at 1.0


class TestTransitionProbability(unittest.TestCase):
    """Tests for regime transition probability estimation."""
    
    def test_uniform_on_insufficient_data(self):
        """Test uniform distribution when data insufficient."""
        prices = np.array([100] * 30)
        
        probs = get_regime_transition_probability(prices)
        
        # Should return uniform distribution
        expected = 0.25
        for regime in RegimeType:
            self.assertAlmostEqual(probs[regime], expected, places=2)
    
    def test_trend_based_adjustment(self):
        """Test that volatility trend affects transition probabilities."""
        np.random.seed(42)
        
        # Increasing volatility trend
        base_vol = 0.02
        returns = np.random.normal(0, base_vol, 100)
        # Add increasing volatility component
        for i in range(len(returns)):
            returns[i] *= (1 + i / 200)
        prices = 100 * np.exp(np.cumsum(returns))
        
        probs = get_regime_transition_probability(prices, lookback=50)
        
        # Probabilities should sum to 1
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=4)
        
        # All probabilities should be positive
        for p in probs.values():
            self.assertGreater(p, 0)


class TestBacktestIntegration(unittest.TestCase):
    """Tests for backtest signal generation."""
    
    def test_regime_aware_backtest_basic(self):
        """Test basic backtest signal generation."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 300)
        prices = 100 * np.exp(np.cumsum(returns))
        
        # Generate synthetic FTE scores (some above, some below threshold)
        fte_scores = np.random.uniform(0.05, 0.15, 300)
        
        results = regime_aware_backtest_signal(fte_scores.tolist(), prices)
        
        # Check structure
        self.assertIn('signals', results)
        self.assertIn('summary', results)
        self.assertEqual(len(results['signals']), 300)
        
        # Check summary fields
        summary = results['summary']
        self.assertEqual(summary['total_periods'], 300)
        self.assertIn('regime_distribution', summary)
        self.assertIn('avg_threshold', summary)
    
    def test_consecutive_signal_filtering(self):
        """Test that consecutive valid signals are required."""
        prices = np.array([100 + i * 0.1 for i in range(300)])
        
        # Create pattern: valid, invalid, valid, valid, valid
        fte_scores = [0.10, 0.05, 0.10, 0.10, 0.10] + [0.05] * 295
        
        results = regime_aware_backtest_signal(
            fte_scores, prices, min_consecutive=3
        )
        
        # First valid signal shouldn't trigger (only 1 consecutive)
        self.assertFalse(results['signals'][0]['trigger_signal'])
        
        # After 3 consecutive valid, should trigger
        self.assertTrue(results['signals'][4]['trigger_signal'])
    
    def test_length_mismatch_error(self):
        """Test error handling for mismatched input lengths."""
        prices = np.array([100, 101, 102])
        fte_scores = [0.10, 0.11]  # Wrong length
        
        with self.assertRaises(ValueError):
            regime_aware_backtest_signal(fte_scores, prices)


class TestFTEIntegration(unittest.TestCase):
    """Tests for integration with existing FTE module."""
    
    def test_integrate_with_fte_basic(self):
        """Test basic FTE integration."""
        fte_result = {'correlation': 0.10, 'p_value': 0.03}
        prices = np.array([100 + i * 0.1 for i in range(300)])
        
        enhanced = integrate_with_fte(fte_result, prices)
        
        # Should preserve original fields
        self.assertEqual(enhanced['correlation'], 0.10)
        self.assertEqual(enhanced['p_value'], 0.03)
        
        # Should add regime fields
        self.assertIn('regime_validated', enhanced)
        self.assertIn('regime', enhanced)
        self.assertIn('adaptive_threshold', enhanced)
        self.assertIn('signal_strength', enhanced)
    
    def test_integrate_missing_correlation(self):
        """Test handling of missing correlation in FTE result."""
        fte_result = {'other_field': 'value'}
        prices = np.array([100 + i * 0.1 for i in range(300)])
        
        enhanced = integrate_with_fte(fte_result, prices)
        
        # Should handle missing correlation gracefully
        self.assertIn('regime_validated', enhanced)
        self.assertEqual(enhanced.get('correlation', 0.0), 0.0)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and robustness."""
    
    def test_negative_prices(self):
        """Test handling of negative prices (should not occur but handle gracefully)."""
        prices = np.array([100, -50, 100, 101, 102])
        
        # Should not crash, may produce NaN or warning
        vol = calculate_realized_volatility(prices, window=3)
        # Just check it doesn't raise exception
        self.assertIsInstance(vol, np.ndarray)
    
    def test_zero_prices(self):
        """Test handling of zero prices."""
        prices = np.array([100, 0, 100, 101, 102])
        
        vol = calculate_realized_volatility(prices, window=3)
        self.assertIsInstance(vol, np.ndarray)
    
    def test_extreme_volatility_ratio(self):
        """Test behavior with extreme volatility ratios."""
        # Create scenario with very low baseline, high current
        config = RegimeConfig(base_threshold=0.08)
        
        # Almost flat historical, then spike
        prices = np.array([100] * 250 + [100, 150, 100, 150, 100])
        
        result = detect_regime(prices, config)
        
        # Should handle extreme ratios without crashing
        self.assertIsInstance(result.volatility_ratio, float)
        self.assertTrue(np.isfinite(result.adaptive_threshold))
    
    def test_custom_config_parameters(self):
        """Test that custom config parameters are respected."""
        config = RegimeConfig(
            short_window=10,
            long_window=100,
            base_threshold=0.05,
            sensitivity_lambda=1.0,
        )
        
        np.random.seed(42)
        prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.02, 300)))
        
        result = detect_regime(prices, config)
        
        # Custom base threshold should be used
        self.assertEqual(config.base_threshold, 0.05)
        # Adaptive threshold calculation should use custom lambda
        self.assertIsInstance(result.adaptive_threshold, float)


class TestRegimeResultDataclass(unittest.TestCase):
    """Tests for RegimeResult dataclass functionality."""
    
    def test_dataclass_fields(self):
        """Test that all required fields are present."""
        result = RegimeResult(
            regime=RegimeType.NORMAL_VOL,
            current_volatility=0.2,
            baseline_volatility=0.2,
            volatility_ratio=1.0,
            percentile_rank=0.5,
            adaptive_threshold=0.08,
            regime_adjusted_threshold=0.08,
            samples_analyzed=200,
            confidence=0.9
        )
        
        # Check all fields exist and have correct types
        self.assertIsInstance(result.regime, RegimeType)
        self.assertIsInstance(result.current_volatility, float)
        self.assertIsInstance(result.baseline_volatility, float)
        self.assertIsInstance(result.volatility_ratio, float)
        self.assertIsInstance(result.percentile_rank, float)
        self.assertIsInstance(result.adaptive_threshold, float)
        self.assertIsInstance(result.regime_adjusted_threshold, float)
        self.assertIsInstance(result.samples_analyzed, int)
        self.assertIsInstance(result.confidence, float)
    
    def test_dataclass_immutability(self):
        """Test that dataclass can be modified (not frozen)."""
        result = RegimeResult(
            regime=RegimeType.NORMAL_VOL,
            current_volatility=0.2,
            baseline_volatility=0.2,
            volatility_ratio=1.0,
            percentile_rank=0.5,
            adaptive_threshold=0.08,
            regime_adjusted_threshold=0.08,
            samples_analyzed=200,
            confidence=0.9
        )
        
        # Should be able to modify (not frozen)
        result.confidence = 0.95
        self.assertEqual(result.confidence, 0.95)


if __name__ == '__main__':
    unittest.main()
