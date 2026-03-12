"""
Decennial Pattern Analysis - Larry Williams Methodology

Analyzes market behavior by year digit (year % 10), identifying
patterns that repeat every 10 years based on Larry Williams'
observation that certain years show similar market behavior.

Reference: Williams, L. (2023). The New Commodity Trading Systems.

Key Concepts:
- Year Digit: year % 10 (0-9)
- Groups years by digit to find repeating patterns
- Requires 30+ years of data for statistical significance
- Not applicable for crypto (< 30 years of history)

Version: 3.2 Final
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
import warnings


class DecennialStatus(Enum):
    """Status of decennial analysis."""
    VALID = "valid"
    INSUFFICIENT_DATA = "insufficient_data"
    CRYPTO_UNSUPPORTED = "crypto_unsupported"


@dataclass
class DecennialConfig:
    """Configuration for Decennial Pattern analysis."""
    min_years: int = 30  # Minimum years of data required
    min_years_per_digit: int = 2  # Minimum years per digit for stats
    normalization_range: Tuple[float, float] = (0, 1)  # Output scale
    similarity_method: str = 'correlation'  # 'correlation', 'euclidean', 'dtw'
    

@dataclass
class DigitStats:
    """Statistics for a single year digit."""
    digit: int
    years: List[int]
    avg_return: float
    std_return: float
    win_rate: float
    normalized_score: float
    sample_count: int
    confidence: float


@dataclass
class DecennialResult:
    """Result of Decennial Pattern analysis."""
    status: DecennialStatus
    digit_stats: Dict[int, DigitStats]
    current_digit: int
    current_year: int
    most_similar_digit: Optional[int]
    similarity_score: float
    projected_trend: Optional[str]  # 'bullish', 'bearish', 'neutral'
    message: str
    years_analyzed: int
    data_completeness: float


def get_year_digit(year: int) -> int:
    """
    Calculate year digit (year % 10).
    
    Args:
        year: Full year (e.g., 2024)
        
    Returns:
        Digit 0-9
    """
    return year % 10


def extract_years_from_data(
    data: Union[pd.DataFrame, pd.Series, np.ndarray],
    date_column: Optional[str] = None
) -> np.ndarray:
    """
    Extract years from time series data.
    
    Args:
        data: Time series data with date index or date column
        date_column: Name of date column if data is DataFrame
        
    Returns:
        Array of years
    """
    if isinstance(data, pd.DataFrame):
        if date_column and date_column in data.columns:
            dates = pd.to_datetime(data[date_column])
        elif isinstance(data.index, pd.DatetimeIndex):
            dates = data.index
        else:
            # Try to find a date-like column
            for col in data.columns:
                if 'date' in col.lower() or 'time' in col.lower():
                    dates = pd.to_datetime(data[col])
                    break
            else:
                raise ValueError("Cannot find date column in DataFrame")
        return dates.year.values
    
    elif isinstance(data, pd.Series):
        if isinstance(data.index, pd.DatetimeIndex):
            return data.index.year.values
        else:
            raise ValueError("Series must have DatetimeIndex")
    
    elif isinstance(data, np.ndarray):
        # Assume data doesn't have date info
        warnings.warn("No date information in numpy array; cannot extract years")
        return np.array([])
    
    else:
        raise ValueError(f"Unsupported data type: {type(data)}")


def calculate_annual_returns(
    prices: np.ndarray,
    years: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate annual returns for each year.
    
    Args:
        prices: Array of prices (year-end or close prices)
        years: Array of corresponding years
        
    Returns:
        Tuple of (unique_years, annual_returns)
    """
    # Get unique years and their indices
    unique_years = np.unique(years)
    
    if len(unique_years) < 2:
        return unique_years, np.array([])
    
    annual_returns = []
    result_years = []
    
    for year in sorted(unique_years):
        year_mask = years == year
        year_prices = prices[year_mask]
        
        if len(year_prices) < 2:
            continue
        
        # Calculate return from first to last price of year
        first_price = year_prices[0]
        last_price = year_prices[-1]
        
        if first_price > 0:
            annual_return = (last_price - first_price) / first_price
            annual_returns.append(annual_return)
            result_years.append(year)
    
    return np.array(result_years), np.array(annual_returns)


def group_by_digit(
    years: np.ndarray,
    returns: np.ndarray
) -> Dict[int, List[Tuple[int, float]]]:
    """
    Group annual returns by year digit.
    
    Args:
        years: Array of years
        returns: Array of corresponding annual returns
        
    Returns:
        Dict mapping digit to list of (year, return) tuples
    """
    digit_groups = {i: [] for i in range(10)}
    
    for year, ret in zip(years, returns):
        digit = get_year_digit(int(year))
        digit_groups[digit].append((int(year), float(ret)))
    
    return digit_groups


def calculate_digit_statistics(
    digit_groups: Dict[int, List[Tuple[int, float]]],
    config: DecennialConfig
) -> Dict[int, DigitStats]:
    """
    Calculate statistics for each digit group.
    
    Args:
        digit_groups: Dict mapping digit to list of (year, return) tuples
        config: DecennialConfig with parameters
        
    Returns:
        Dict mapping digit to DigitStats
    """
    stats_dict = {}
    
    # Collect all returns for normalization
    all_returns = []
    for digit_data in digit_groups.values():
        all_returns.extend([r for _, r in digit_data])
    
    if len(all_returns) == 0:
        return stats_dict
    
    all_returns = np.array(all_returns)
    min_ret, max_ret = np.min(all_returns), np.max(all_returns)
    ret_range = max_ret - min_ret if max_ret > min_ret else 1.0
    
    for digit, year_returns in digit_groups.items():
        if len(year_returns) < config.min_years_per_digit:
            # Insufficient data for this digit
            stats_dict[digit] = DigitStats(
                digit=digit,
                years=[y for y, _ in year_returns],
                avg_return=0.0,
                std_return=0.0,
                win_rate=0.0,
                normalized_score=0.5,
                sample_count=len(year_returns),
                confidence=0.0
            )
            continue
        
        returns = np.array([r for _, r in year_returns])
        years_list = [y for y, _ in year_returns]
        
        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 0.0
        win_rate = np.mean(returns > 0)
        
        # Normalize to 0-1 scale
        if ret_range > 0:
            normalized = (avg_return - min_ret) / ret_range
        else:
            normalized = 0.5
        
        # Confidence based on sample size
        sample_confidence = min(1.0, len(year_returns) / 5)
        
        stats_dict[digit] = DigitStats(
            digit=digit,
            years=years_list,
            avg_return=avg_return,
            std_return=std_return,
            win_rate=win_rate,
            normalized_score=normalized,
            sample_count=len(year_returns),
            confidence=sample_confidence
        )
    
    return stats_dict


def calculate_similarity(
    digit_stats: Dict[int, DigitStats],
    current_digit: int,
    method: str = 'correlation'
) -> Tuple[int, float]:
    """
    Find most similar digit to current based on pattern.
    
    Args:
        digit_stats: Dict of digit statistics
        current_digit: Current year digit
        method: Similarity method ('correlation', 'euclidean')
        
    Returns:
        Tuple of (most_similar_digit, similarity_score)
    """
    if current_digit not in digit_stats:
        return current_digit, 0.0
    
    current_stats = digit_stats[current_digit]
    
    best_digit = current_digit
    best_score = 0.0
    
    for digit, stats in digit_stats.items():
        if digit == current_digit:
            continue
        
        if stats.sample_count < 2:
            continue
        
        # Simple similarity: compare normalized scores
        score_diff = abs(current_stats.normalized_score - stats.normalized_score)
        similarity = 1.0 - score_diff  # Higher is more similar
        
        if similarity > best_score:
            best_score = similarity
            best_digit = digit
    
    return best_digit, best_score


def analyze_decennial(
    prices: Union[pd.DataFrame, pd.Series, np.ndarray],
    years: Optional[np.ndarray] = None,
    config: Optional[DecennialConfig] = None,
    current_year: Optional[int] = None,
    instrument_type: str = 'tradfi'
) -> DecennialResult:
    """
    Perform full Decennial Pattern analysis.
    
    Args:
        prices: Price time series data
        years: Array of years (extracted from prices if not provided)
        config: DecennialConfig with parameters
        current_year: Current year (defaults to current year)
        instrument_type: 'tradfi' or 'crypto'
        
    Returns:
        DecennialResult with analysis
    """
    if config is None:
        config = DecennialConfig()
    
    if current_year is None:
        current_year = pd.Timestamp.now().year
    
    # Check if crypto (not enough history)
    if instrument_type == 'crypto':
        return DecennialResult(
            status=DecennialStatus.CRYPTO_UNSUPPORTED,
            digit_stats={},
            current_digit=get_year_digit(current_year),
            current_year=current_year,
            most_similar_digit=None,
            similarity_score=0.0,
            projected_trend=None,
            message="Decennial pattern not applicable for crypto (< 30 years of data)",
            years_analyzed=0,
            data_completeness=0.0
        )
    
    # Extract years if not provided
    if years is None:
        try:
            years = extract_years_from_data(prices)
        except ValueError as e:
            return DecennialResult(
                status=DecennialStatus.INSUFFICIENT_DATA,
                digit_stats={},
                current_digit=get_year_digit(current_year),
                current_year=current_year,
                most_similar_digit=None,
                similarity_score=0.0,
                projected_trend=None,
                message=str(e),
                years_analyzed=0,
                data_completeness=0.0
            )
    
    # Get price values
    if isinstance(prices, pd.DataFrame):
        # Assume close or first numeric column
        price_values = prices.select_dtypes(include=[np.number]).iloc[:, 0].values
    elif isinstance(prices, pd.Series):
        price_values = prices.values
    else:
        price_values = np.asarray(prices)
    
    # Check minimum data requirement
    unique_years = np.unique(years)
    if len(unique_years) < config.min_years:
        return DecennialResult(
            status=DecennialStatus.INSUFFICIENT_DATA,
            digit_stats={},
            current_digit=get_year_digit(current_year),
            current_year=current_year,
            most_similar_digit=None,
            similarity_score=0.0,
            projected_trend=None,
            message=f"Insufficient data: {len(unique_years)} years, need {config.min_years}",
            years_analyzed=len(unique_years),
            data_completeness=len(unique_years) / config.min_years
        )
    
    # Calculate annual returns
    analysis_years, annual_returns = calculate_annual_returns(price_values, years)
    
    if len(annual_returns) == 0:
        return DecennialResult(
            status=DecennialStatus.INSUFFICIENT_DATA,
            digit_stats={},
            current_digit=get_year_digit(current_year),
            current_year=current_year,
            most_similar_digit=None,
            similarity_score=0.0,
            projected_trend=None,
            message="Could not calculate annual returns",
            years_analyzed=0,
            data_completeness=0.0
        )
    
    # Group by digit
    digit_groups = group_by_digit(analysis_years, annual_returns)
    
    # Calculate statistics
    digit_stats = calculate_digit_statistics(digit_groups, config)
    
    # Get current digit
    current_digit = get_year_digit(current_year)
    
    # Find similar digits
    similar_digit, similarity = calculate_similarity(
        digit_stats, current_digit, config.similarity_method
    )
    
    # Determine projected trend
    current_stats = digit_stats.get(current_digit)
    if current_stats and current_stats.confidence > 0.3:
        if current_stats.avg_return > 0.05:
            projected_trend = 'bullish'
        elif current_stats.avg_return < -0.05:
            projected_trend = 'bearish'
        else:
            projected_trend = 'neutral'
    else:
        projected_trend = None
    
    # Calculate data completeness
    complete_digits = sum(1 for s in digit_stats.values() if s.sample_count >= config.min_years_per_digit)
    data_completeness = complete_digits / 10.0
    
    return DecennialResult(
        status=DecennialStatus.VALID,
        digit_stats=digit_stats,
        current_digit=current_digit,
        current_year=current_year,
        most_similar_digit=similar_digit,
        similarity_score=similarity,
        projected_trend=projected_trend,
        message="Decennial pattern analysis complete",
        years_analyzed=len(analysis_years),
        data_completeness=data_completeness
    )


def get_decennial_forecast(
    result: DecennialResult,
    lookback_digits: int = 3
) -> Dict[str, any]:
    """
    Generate forecast based on decennial pattern.
    
    Args:
        result: DecennialResult from analysis
        lookback_digits: Number of similar digits to consider
        
    Returns:
        Dict with forecast information
    """
    if result.status != DecennialStatus.VALID:
        return {
            'valid': False,
            'message': result.message
        }
    
    # Get current digit stats
    current = result.digit_stats.get(result.current_digit)
    if current is None:
        return {
            'valid': False,
            'message': 'No data for current digit'
        }
    
    # Find best historical years
    digit_data = []
    for digit, stats in result.digit_stats.items():
        if stats.confidence > 0.3:
            digit_data.append({
                'digit': digit,
                'avg_return': stats.avg_return,
                'win_rate': stats.win_rate,
                'confidence': stats.confidence
            })
    
    # Sort by similarity to current
    digit_data.sort(key=lambda x: abs(x['avg_return'] - current.avg_return))
    
    return {
        'valid': True,
        'current_digit': result.current_digit,
        'current_stats': {
            'avg_return': current.avg_return,
            'win_rate': current.win_rate,
            'sample_count': current.sample_count
        },
        'projected_trend': result.projected_trend,
        'similar_patterns': digit_data[:lookback_digits],
        'years_analyzed': result.years_analyzed
    }


# Convenience function for quick analysis
def decennial_pattern(
    prices: Union[pd.DataFrame, pd.Series, np.ndarray],
    years: Optional[np.ndarray] = None,
    **kwargs
) -> DecennialResult:
    """
    Convenience function for Decennial Pattern analysis.
    
    Args:
        prices: Price time series
        years: Optional years array
        **kwargs: Additional config options
        
    Returns:
        DecennialResult
    """
    config = DecennialConfig(**{k: v for k, v in kwargs.items() 
                                  if k in DecennialConfig.__dataclass_fields__})
    
    instrument_type = kwargs.get('instrument_type', 'tradfi')
    current_year = kwargs.get('current_year')
    
    return analyze_decennial(prices, years, config, current_year, instrument_type)


__all__ = [
    'DecennialStatus',
    'DecennialConfig',
    'DigitStats',
    'DecennialResult',
    'get_year_digit',
    'analyze_decennial',
    'get_decennial_forecast',
    'decennial_pattern',
]
