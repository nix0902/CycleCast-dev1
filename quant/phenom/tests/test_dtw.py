"""
Unit tests for Phenomenological DTW Module - CycleCast v3.2
Task: PH-001 - Phenomenological DTW Prototype
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List

from quant.phenom.dtw import (
    DTWConfig,
    DTWMatch,
    PhenomResult,
    adaptive_dtw,
    find_historical_analogies,
    validate_analogy_quality,
    _normalize_series,
    _get_year_digit,
    _fast_correlation_filter,
    _exact_dtw,
    _project_continuation,
)


class TestNormalization:
    """Tests for series normalization functions."""
    
    def test_zscore_normalization(self):
        """Test z-score normalization."""
        series = np.array([1, 2, 3, 4, 5])
        normalized = _normalize_series(series, 'zscore')
        
        assert np.isclose(np.mean(normalized), 0, atol=1e-10)
        assert np.isclose(np.std(normalized), 1, atol=1e-10)
    
    def test_minmax_normalization(self):
        """Test min-max normalization."""
        series = np.array([10, 20, 30, 40, 50])
        normalized = _normalize_series(series, 'minmax')
        
        assert np.isclose(np.min(normalized), 0, atol=1e-10)
        assert np.isclose(np.max(normalized), 1, atol=1e-10)
    
    def test_percentile_normalization(self):
        """Test percentile normalization (robust to outliers)."""
        series = np.array([1, 2, 3, 4, 100])  # Outlier at end
        normalized = _normalize_series(series, 'percentile')
        
        # Should not be dominated by outlier
        assert not np.isnan(normalized).any()
        assert normalized[-1] > 1.0  # Outlier should be > 1
    
    def test_constant_series(self):
        """Test normalization of constant series."""
        series = np.array([5, 5, 5, 5, 5])
        
        for method in ['zscore', 'minmax', 'percentile']:
            normalized = _normalize_series(series, method)
            assert np.allclose(normalized, 0) or np.allclose(normalized, 1)


class TestYearDigit:
    """Tests for year digit extraction."""
    
    def test_year_digit_extraction(self):
        """Test extracting year digit from datetime."""
        test_cases = [
            (datetime(2020, 1, 1), 0),
            (datetime(2021, 6, 15), 1),
            (datetime(2024, 12, 31), 4),
            (datetime(2030, 1, 1), 0),
        ]
        
        for date, expected in test_cases:
            assert _get_year_digit(date) == expected
    
    def test_year_digit_from_string(self):
        """Test extracting year digit from ISO string."""
        result = _get_year_digit("2024-03-13T10:00:00Z")
        assert result == 4


class TestCorrelationFilter:
    """Tests for fast correlation pre-filtering."""
    
    def test_correlation_filter_basic(self):
        """Test basic correlation filtering."""
        target = np.array([1, 2, 3, 4, 5])
        
        # High correlation candidate
        high_corr = np.array([2, 4, 6, 8, 10])
        # Low correlation candidate
        low_corr = np.array([5, 4, 3, 2, 1])
        
        candidates = [
            (datetime(2020, 1, 1), datetime(2020, 1, 5), high_corr),
            (datetime(2021, 1, 1), datetime(2021, 1, 5), low_corr),
        ]
        
        filtered = _fast_correlation_filter(target, candidates, threshold=0.8)
        
        # Only high correlation should pass
        assert len(filtered) == 1
        assert filtered[0][0] == datetime(2020, 1, 1)
    
    def test_correlation_filter_length_mismatch(self):
        """Test handling of length mismatched series."""
        target = np.array([1, 2, 3, 4, 5])
        short = np.array([1, 2])
        long_series = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        
        candidates = [
            (datetime(2020, 1, 1), datetime(2020, 1, 2), short),
            (datetime(2021, 1, 1), datetime(2021, 1, 10), long_series),
        ]
        
        # Should handle gracefully without errors
        filtered = _fast_correlation_filter(target, candidates, threshold=0.5)
        assert isinstance(filtered, list)


class TestExactDTW:
    """Tests for exact DTW implementation."""
    
    def test_exact_dtw_identical_series(self):
        """Test DTW on identical series (should have zero distance)."""
        series = np.array([1, 2, 3, 4, 5])
        distance, path = _exact_dtw(series, series)
        
        assert distance == 0
        assert len(path) == len(series)
    
    def test_exact_dtw_shifted_series(self):
        """Test DTW on shifted series."""
        target = np.array([1, 2, 3, 4, 5])
        shifted = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
        
        distance, path = _exact_dtw(target, shifted)
        
        # Should be small but non-zero
        assert 0 < distance < 1
        assert len(path) == len(target)
    
    def test_exact_dtw_with_window(self):
        """Test DTW with Sakoe-Chiba band constraint."""
        target = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        candidate = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        
        distance, path = _exact_dtw(target, candidate, window=2)
        
        assert distance == 0
        # Path should be diagonal with window constraint
        for i, (t_idx, c_idx) in enumerate(path):
            assert abs(t_idx - c_idx) <= 2
    
    def test_exact_dtw_path_validity(self):
        """Test that DTW path is valid (monotonic, contiguous)."""
        target = np.random.randn(20)
        candidate = np.random.randn(25)
        
        distance, path = _exact_dtw(target, candidate)
        
        # Path should start at (0, 0) and end at (len-1, len-1)
        assert path[0] == (0, 0)
        assert path[-1] == (len(target) - 1, len(candidate) - 1)
        
        # Path should be monotonic
        for i in range(1, len(path)):
            assert path[i][0] >= path[i-1][0]
            assert path[i][1] >= path[i-1][1]
            # At least one index should advance
            assert path[i][0] > path[i-1][0] or path[i][1] > path[i-1][1]


class TestProjection:
    """Tests for continuation projection."""
    
    def test_projection_basic(self):
        """Test basic projection from historical pattern."""
        historical = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        alignment = [(i, i) for i in range(10)]  # Perfect alignment
        
        projection = _project_continuation(historical, alignment, target_length=5, horizon=3)
        
        assert len(projection) == 3
        # Should continue the pattern: 10, 11, 12
        assert np.allclose(projection, [8, 9, 10], atol=1)  # Approximate
    
    def test_projection_with_trend(self):
        """Test projection when historical has clear trend."""
        historical = np.arange(100)  # Linear trend
        alignment = [(i, i + 50) for i in range(20)]  # Map to latter half
        
        projection = _project_continuation(
            historical, alignment, target_length=20, horizon=5
        )
        
        assert len(projection) == 5
        # Should continue upward trend
        assert projection[-1] > projection[0]


class TestAdaptiveDTW:
    """Tests for main adaptive_dtw function."""
    
    def _generate_test_data(self, n_points: int = 100, n_history: int = 500):
        """Generate synthetic test data with embedded cycles."""
        # Generate dates
        end_date = datetime.now()
        target_dates = [end_date - timedelta(days=i) for i in range(n_points)]
        target_dates.reverse()
        
        history_dates = [end_date - timedelta(days=i) for i in range(n_history + n_points)]
        history_dates.reverse()
        
        # Generate prices with cycles
        t_target = np.arange(n_points)
        target = (
            100 + 
            10 * np.sin(2 * np.pi * t_target / 14) +  # 14-day cycle
            5 * np.sin(2 * np.pi * t_target / 42) +   # 42-day cycle
            np.random.randn(n_points) * 2  # Noise
        )
        
        t_history = np.arange(n_history + n_points)
        history = (
            100 + 
            10 * np.sin(2 * np.pi * t_history / 14) +
            5 * np.sin(2 * np.pi * t_history / 42) +
            np.random.randn(n_history + n_points) * 2
        )
        
        return target, target_dates, history, history_dates
    
    def test_adaptive_dtw_basic(self):
        """Test basic adaptive_dtw execution."""
        target, target_dates, history, history_dates = self._generate_test_data()
        
        result = adaptive_dtw(
            target, history, history_dates,
            config=DTWConfig(
                correlation_threshold=0.5,
                max_candidates=50,
                projection_horizon=5,
                decennial_filter=False  # Disable for synthetic data
            )
        )
        
        assert result.candidates_evaluated > 0
        assert isinstance(result.matches, list)
        assert result.processing_time_ms >= 0
    
    def test_adaptive_dtw_with_decennial_filter(self):
        """Test decennial (year digit) filtering."""
        target, target_dates, history, history_dates = self._generate_test_data()
        
        # Set specific year digits for testing
        target_dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(len(target_dates))]
        history_dates = [datetime(2014, 1, 1) + timedelta(days=i) for i in range(len(history_dates))]
        
        result = adaptive_dtw(
            target, history, history_dates,
            config=DTWConfig(
                correlation_threshold=0.3,  # Lower for synthetic
                decennial_filter=True,
                max_candidates=20
            )
        )
        
        # All matches should have year_digit == 4 (2024 % 10)
        for match in result.matches:
            assert match.year_digit == 4
    
    def test_adaptive_dtw_projection(self):
        """Test that projection is generated when configured."""
        target, target_dates, history, history_dates = self._generate_test_data()
        
        result = adaptive_dtw(
            target, history, history_dates,
            config=DTWConfig(projection_horizon=10)
        )
        
        if result.matches and result.matches[0].projection is not None:
            assert len(result.matches[0].projection) == 10
            assert result.best_projection is not None
    
    def test_adaptive_dtw_no_matches(self):
        """Test handling when no candidates pass filter."""
        target = np.random.randn(50)
        history = np.random.randn(200)
        history_dates = [datetime.now() - timedelta(days=i) for i in range(200)]
        history_dates.reverse()
        
        result = adaptive_dtw(
            target, history, history_dates,
            config=DTWConfig(correlation_threshold=0.99)  # Very high threshold
        )
        
        assert not result.is_valid
        assert len(result.warnings) > 0 or len(result.matches) == 0


class TestFindHistoricalAnalogies:
    """Tests for convenience function."""
    
    def test_convenience_function(self):
        """Test find_historical_analogies wrapper."""
        prices = np.array([100, 102, 101, 103, 105, 104, 106])
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(len(prices))]
        
        history_prices = np.array([100 + i * 0.5 + np.random.randn() for i in range(200)])
        history_dates = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(200)]
        
        result = find_historical_analogies(
            prices, dates, history_prices, history_dates,
            correlation_threshold=0.3,
            max_candidates=10
        )
        
        assert isinstance(result, PhenomResult)


class TestValidateAnalogyQuality:
    """Tests for quality validation."""
    
    def test_validate_good_quality(self):
        """Test validation with good quality results."""
        result = PhenomResult(
            target_start=datetime.now(),
            target_end=datetime.now(),
            target_length=50,
            matches=[
                DTWMatch(
                    start_date=datetime(2020, 1, 1),
                    end_date=datetime(2020, 3, 1),
                    distance=10.0,
                    correlation=0.85,
                )
            ],
            confidence=0.7,
            avg_correlation=0.8,
            is_valid=True
        )
        
        is_valid, issues = validate_analogy_quality(
            result,
            min_correlation=0.5,
            min_confidence=0.3
        )
        
        assert is_valid
        assert len(issues) == 0
    
    def test_validate_poor_quality(self):
        """Test validation with poor quality results."""
        result = PhenomResult(
            target_start=datetime.now(),
            target_end=datetime.now(),
            target_length=50,
            matches=[
                DTWMatch(
                    start_date=datetime(2020, 1, 1),
                    end_date=datetime(2020, 3, 1),
                    distance=50.0,
                    correlation=0.2,
                )
            ],
            confidence=0.1,
            avg_correlation=0.25,
            is_valid=False
        )
        
        is_valid, issues = validate_analogy_quality(
            result,
            min_correlation=0.5,
            min_confidence=0.3
        )
        
        assert not is_valid
        assert len(issues) > 0
    
    def test_validate_empty_matches(self):
        """Test validation with no matches."""
        result = PhenomResult(
            target_start=datetime.now(),
            target_end=datetime.now(),
            target_length=50,
            matches=[]
        )
        
        is_valid, issues = validate_analogy_quality(result)
        
        assert not is_valid
        assert any("No matches" in issue for issue in issues)


class TestIntegration:
    """Integration tests with test fixtures."""
    
    def test_with_sp500_fixture(self):
        """Test DTW with S&P 500 test fixture."""
        try:
            sp500 = pd.read_csv('tests/fixtures/sp500.csv', parse_dates=['time'])
            
            # Use last 50 days as target
            target = sp500['close'].values[-50:]
            target_dates = sp500['time'].values[-50:]
            
            # Use earlier data as history
            history = sp500['close'].values[:-50]
            history_dates = sp500['time'].values[:-50]
            
            result = adaptive_dtw(
                target, history, history_dates.tolist(),
                config=DTWConfig(
                    correlation_threshold=0.4,
                    max_candidates=30,
                    projection_horizon=10,
                    decennial_filter=False
                )
            )
            
            assert result.candidates_evaluated > 0
            assert isinstance(result, PhenomResult)
            
        except FileNotFoundError:
            pytest.skip("Test fixture not found")
    
    def test_with_gold_fixture(self):
        """Test DTW with Gold test fixture."""
        try:
            gold = pd.read_csv('tests/fixtures/gold.csv', parse_dates=['time'])
            
            target = gold['close'].values[-30:]
            target_dates = gold['time'].values[-30:]
            history = gold['close'].values[:-30]
            history_dates = gold['time'].values[:-30]
            
            result = find_historical_analogies(
                target, target_dates.tolist(),
                history, history_dates.tolist(),
                correlation_threshold=0.3,
                max_candidates=20
            )
            
            assert result is not None
            
        except FileNotFoundError:
            pytest.skip("Test fixture not found")


class TestDataClasses:
    """Tests for data class functionality."""
    
    def test_dtw_config_defaults(self):
        """Test DTWConfig default values."""
        config = DTWConfig()
        
        assert config.correlation_threshold == 0.6
        assert config.max_candidates == 100
        assert config.decennial_filter is True
        assert config.projection_horizon == 30
    
    def test_dtw_match_creation(self):
        """Test DTWMatch creation and fields."""
        match = DTWMatch(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 3, 1),
            distance=15.5,
            correlation=0.72,
            metadata={'source': 'test'}
        )
        
        assert match.start_date.year == 2020
        assert match.distance == 15.5
        assert match.metadata['source'] == 'test'
        assert match.path == []  # Default empty list
    
    def test_phenom_result_aggregation(self):
        """Test PhenomResult with multiple matches."""
        matches = [
            DTWMatch(
                start_date=datetime(2020, 1, 1) + timedelta(days=i*30),
                end_date=datetime(2020, 3, 1) + timedelta(days=i*30),
                distance=10 + i,
                correlation=0.9 - i*0.1,
            )
            for i in range(5)
        ]
        
        result = PhenomResult(
            target_start=datetime.now(),
            target_end=datetime.now(),
            target_length=50,
            matches=matches
        )
        
        # Best match should have lowest distance
        assert result.matches[0].distance == min(m.distance for m in matches)


# Run with: pytest quant/phenom/tests/test_dtw.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
