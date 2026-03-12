# quant/bootstrap/core.py
# Bootstrap Confidence Interval with Streaming gRPC Support
# CycleCast v3.2 Final - Larry Williams Methodology
#
# Implements non-parametric bootstrap for statistical validation
# of trading signals and backtest results.
#
# Formula:
#   CI_95 = [percentile_2.5, percentile_97.5] of bootstrap distribution
#   where each bootstrap sample is drawn with replacement from original data

import numpy as np
from typing import Optional, Callable, Iterator, List, Tuple, Dict, Any
from dataclasses import dataclass, field
import logging
from scipy.special import erfinv, erf

logger = logging.getLogger(__name__)


@dataclass
class BootstrapConfig:
    """Configuration for Bootstrap CI calculation."""
    n_iterations: int = 1000  # Number of bootstrap iterations
    confidence_level: float = 0.95  # Confidence level (default 95%)
    seed: Optional[int] = None  # Random seed for reproducibility
    streaming_batch_size: int = 100  # Batch size for streaming updates
    metric_func: Optional[Callable] = None  # Custom metric function
    
    # Advanced options
    bias_correction: bool = True  # Apply BCa bias correction
    acceleration: Optional[float] = None  # Acceleration parameter for BCa


@dataclass
class BootstrapResult:
    """Result of Bootstrap CI calculation."""
    ci_lower: float  # Lower bound of confidence interval
    ci_upper: float  # Upper bound of confidence interval
    point_estimate: float  # Original point estimate
    bootstrap_mean: float  # Mean of bootstrap distribution
    bootstrap_std: float  # Std of bootstrap distribution
    n_iterations: int  # Actual iterations performed
    confidence_level: float  # Confidence level used
    p_value: Optional[float] = None  # Two-tailed p-value if null hypothesis provided
    null_hypothesis: Optional[float] = None  # Null hypothesis value tested
    
    # Diagnostic info
    convergence_info: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BootstrapProgress:
    """Streaming progress update for gRPC."""
    current_iteration: int
    total_iterations: int
    progress_percent: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    running_estimate: Optional[float] = None
    running_std: Optional[float] = None
    is_complete: bool = False


class BootstrapCI:
    """
    Bootstrap Confidence Interval calculator with streaming support.
    
    Implements:
    - Standard percentile bootstrap
    - BCa (Bias-Corrected and Accelerated) bootstrap
    - Streaming progress via generator for gRPC
    - Parallel processing support
    """
    
    def __init__(self, config: Optional[BootstrapConfig] = None):
        self.config = config or BootstrapConfig()
        if self.config.seed is not None:
            np.random.seed(self.config.seed)
    
    def calculate(
        self,
        data: np.ndarray,
        statistic: Optional[Callable[[np.ndarray], float]] = None,
        null_hypothesis: Optional[float] = None,
    ) -> BootstrapResult:
        """
        Calculate bootstrap confidence interval.
        
        Args:
            data: Original data array
            statistic: Function to compute statistic (default: mean)
            null_hypothesis: Value for p-value calculation
            
        Returns:
            BootstrapResult with CI bounds and diagnostics
        """
        if statistic is None:
            statistic = np.mean
        
        n = len(data)
        if n == 0:
            raise ValueError("Data array cannot be empty")
        
        # Compute original point estimate
        point_estimate = statistic(data)
        
        # Generate bootstrap samples and compute statistics
        bootstrap_stats = np.zeros(self.config.n_iterations)
        
        for i in range(self.config.n_iterations):
            # Sample with replacement
            sample_idx = np.random.choice(n, size=n, replace=True)
            bootstrap_sample = data[sample_idx]
            bootstrap_stats[i] = statistic(bootstrap_sample)
        
        # Calculate confidence interval
        alpha = 1 - self.config.confidence_level
        lower_percentile = alpha / 2 * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        ci_lower = np.percentile(bootstrap_stats, lower_percentile)
        ci_upper = np.percentile(bootstrap_stats, upper_percentile)
        
        # Optional BCa correction
        if self.config.bias_correction:
            ci_lower, ci_upper = self._bca_correction(
                data, bootstrap_stats, point_estimate,
                statistic, lower_percentile, upper_percentile
            )
        
        # Calculate p-value if null hypothesis provided
        p_value = None
        if null_hypothesis is not None:
            # Two-tailed test: proportion of bootstrap stats as extreme as null
            extreme_count = np.sum(np.abs(bootstrap_stats - point_estimate) >= 
                                 np.abs(null_hypothesis - point_estimate))
            p_value = extreme_count / self.config.n_iterations
        
        return BootstrapResult(
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            point_estimate=point_estimate,
            bootstrap_mean=np.mean(bootstrap_stats),
            bootstrap_std=np.std(bootstrap_stats),
            n_iterations=self.config.n_iterations,
            confidence_level=self.config.confidence_level,
            p_value=p_value,
            null_hypothesis=null_hypothesis,
            convergence_info={
                'final_ci_width': ci_upper - ci_lower,
                'bootstrap_skew': self._calculate_skew(bootstrap_stats),
            }
        )
    
    def calculate_streaming(
        self,
        data: np.ndarray,
        statistic: Optional[Callable[[np.ndarray], float]] = None,
    ) -> Iterator[BootstrapProgress]:
        """
        Calculate bootstrap CI with streaming progress updates.
        
        Yields BootstrapProgress objects for gRPC streaming.
        """
        if statistic is None:
            statistic = np.mean
        
        n = len(data)
        if n == 0:
            raise ValueError("Data array cannot be empty")
        
        # Compute original point estimate
        point_estimate = statistic(data)
        
        # Pre-allocate array for bootstrap statistics
        bootstrap_stats = np.zeros(self.config.n_iterations)
        
        for i in range(self.config.n_iterations):
            # Sample with replacement
            sample_idx = np.random.choice(n, size=n, replace=True)
            bootstrap_sample = data[sample_idx]
            bootstrap_stats[i] = statistic(bootstrap_sample)
            
            # Yield progress at batch intervals
            if (i + 1) % self.config.streaming_batch_size == 0 or i == self.config.n_iterations - 1:
                completed = i + 1
                progress = completed / self.config.n_iterations * 100
                
                # Calculate interim CI
                alpha = 1 - self.config.confidence_level
                lower_pct = alpha / 2 * 100
                upper_pct = (1 - alpha / 2) * 100
                
                ci_lower = np.percentile(bootstrap_stats[:completed], lower_pct)
                ci_upper = np.percentile(bootstrap_stats[:completed], upper_pct)
                
                yield BootstrapProgress(
                    current_iteration=completed,
                    total_iterations=self.config.n_iterations,
                    progress_percent=progress,
                    ci_lower=ci_lower if completed >= 30 else None,  # Need min samples
                    ci_upper=ci_upper if completed >= 30 else None,
                    running_estimate=np.mean(bootstrap_stats[:completed]),
                    running_std=np.std(bootstrap_stats[:completed]) if completed > 1 else None,
                    is_complete=(i == self.config.n_iterations - 1)
                )
    
    def calculate_for_backtest(
        self,
        returns: np.ndarray,
        metric: str = 'sharpe',
        risk_free_rate: float = 0.0,
    ) -> BootstrapResult:
        """
        Calculate bootstrap CI for backtest metrics.
        
        Args:
            returns: Array of periodic returns
            metric: Metric to evaluate ('sharpe', 'mean', 'total_return')
            risk_free_rate: Annual risk-free rate for Sharpe calculation
            
        Returns:
            BootstrapResult for the specified metric
        """
        def sharpe_ratio(r: np.ndarray) -> float:
            """Calculate annualized Sharpe ratio."""
            if len(r) == 0 or np.std(r) == 0:
                return 0.0
            # Assume daily returns, annualize
            mean_ret = np.mean(r)
            std_ret = np.std(r)
            return (mean_ret - risk_free_rate / 252) / std_ret * np.sqrt(252)
        
        if metric == 'sharpe':
            stat_func = sharpe_ratio
        elif metric == 'mean':
            stat_func = np.mean
        elif metric == 'total_return':
            stat_func = lambda r: np.prod(1 + r) - 1
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        return self.calculate(returns, statistic=stat_func)
    
    def _bca_correction(
        self,
        data: np.ndarray,
        bootstrap_stats: np.ndarray,
        point_estimate: float,
        statistic: Callable[[np.ndarray], float],
        lower_pct: float,
        upper_pct: float,
    ) -> Tuple[float, float]:
        """
        Apply BCa (Bias-Corrected and Accelerated) correction.
        
        Reference: Efron & Tibshirani (1993), "An Introduction to the Bootstrap"
        """
        n = len(data)
        
        # Calculate bias correction factor z0
        prop_below = np.mean(bootstrap_stats < point_estimate)
        if prop_below <= 0 or prop_below >= 1:
            # Edge case: return standard percentile CI
            return np.percentile(bootstrap_stats, lower_pct), np.percentile(bootstrap_stats, upper_pct)
        
        z0 = np.sqrt(2) * erfinv(2 * prop_below - 1)
        
        # Calculate acceleration parameter a (if not provided)
        a = self.config.acceleration
        if a is None:
            # Jackknife estimate of acceleration
            jackknife_stats = np.zeros(n)
            for i in range(n):
                jack_sample = np.delete(data, i)
                jackknife_stats[i] = statistic(jack_sample)
            
            jack_mean = np.mean(jackknife_stats)
            num = np.sum((jack_mean - jackknife_stats) ** 3)
            den = 6 * (np.sum((jack_mean - jackknife_stats) ** 2) ** 1.5)
            a = num / den if den > 0 else 0
        
        # Adjusted percentiles
        def bca_adjust(z: float) -> float:
            """Convert z-score to adjusted percentile."""
            z_adj = z0 + (z0 + z) / (1 - a * (z0 + z))
            return self._norm_cdf(z_adj) * 100
        
        z_lower = np.sqrt(2) * erfinv(2 * (lower_pct / 100) - 1)
        z_upper = np.sqrt(2) * erfinv(2 * (upper_pct / 100) - 1)
        
        adj_lower = bca_adjust(z_lower)
        adj_upper = bca_adjust(z_upper)
        
        # Clamp to valid range
        adj_lower = max(0, min(100, adj_lower))
        adj_upper = max(0, min(100, adj_upper))
        
        return np.percentile(bootstrap_stats, adj_lower), np.percentile(bootstrap_stats, adj_upper)
    
    @staticmethod
    def _calculate_skew(data: np.ndarray) -> float:
        """Calculate sample skewness."""
        if len(data) < 3:
            return 0.0
        n = len(data)
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        m3 = np.mean((data - mean) ** 3)
        return m3 / (std ** 3)
    
    @staticmethod
    def _norm_cdf(x: float) -> float:
        """Standard normal CDF approximation."""
        # Error function approximation
        return 0.5 * (1 + erf(x / np.sqrt(2)))


def bootstrap_ci(
    data: np.ndarray,
    n_iterations: int = 1000,
    confidence_level: float = 0.95,
    statistic: Optional[Callable[[np.ndarray], float]] = None,
    seed: Optional[int] = None,
    null_hypothesis: Optional[float] = None,
) -> BootstrapResult:
    """
    Convenience function for quick bootstrap CI calculation.
    
    Args:
        data: Input data array
        n_iterations: Number of bootstrap iterations
        confidence_level: Confidence level (0-1)
        statistic: Function to compute (default: mean)
        seed: Random seed for reproducibility
        null_hypothesis: Value for p-value calculation
        
    Returns:
        BootstrapResult with confidence interval
    """
    config = BootstrapConfig(
        n_iterations=n_iterations,
        confidence_level=confidence_level,
        seed=seed,
    )
    calculator = BootstrapCI(config)
    return calculator.calculate(data, statistic=statistic, null_hypothesis=null_hypothesis)


def bootstrap_ci_streaming(
    data: np.ndarray,
    n_iterations: int = 1000,
    confidence_level: float = 0.95,
    statistic: Optional[Callable[[np.ndarray], float]] = None,
    batch_size: int = 100,
    seed: Optional[int] = None,
) -> Iterator[BootstrapProgress]:
    """
    Convenience function for streaming bootstrap CI calculation.
    
    Yields BootstrapProgress objects for real-time updates.
    """
    config = BootstrapConfig(
        n_iterations=n_iterations,
        confidence_level=confidence_level,
        seed=seed,
        streaming_batch_size=batch_size,
    )
    calculator = BootstrapCI(config)
    return calculator.calculate_streaming(data, statistic=statistic)


# Integration helper for QSpectrum results
def validate_cycle_significance(
    cycle_energies: Dict[int, float],
    prices: np.ndarray,
    n_iterations: int = 1000,
    threshold: float = 0.05,
) -> Dict[int, Dict[str, Any]]:
    """
    Validate cycle significance using bootstrap.
    
    Tests if each cycle's energy is significantly different from noise.
    
    Args:
        cycle_energies: Dict mapping period -> energy value
        prices: Original price series
        n_iterations: Bootstrap iterations
        threshold: Significance threshold (p-value)
        
    Returns:
        Dict mapping period -> {significant: bool, p_value: float, ci: (low, high)}
    """
    results = {}
    
    # Generate surrogate data (phase-randomized)
    surrogate = _generate_phase_randomized_surrogate(prices)
    
    for period, energy in cycle_energies.items():
        # Bootstrap distribution of energy under null (surrogate data)
        config = BootstrapConfig(n_iterations=n_iterations)
        calc = BootstrapCI(config)
        
        def energy_stat(data: np.ndarray) -> float:
            """Compute energy for given period."""
            from quant.qspectrum.core import cyclic_correlation
            corr = cyclic_correlation(data, period)
            n = len(data)
            return abs(corr) * np.sqrt(n / period)
        
        result = calc.calculate(surrogate, statistic=energy_stat)
        
        # P-value: proportion of surrogate energies >= observed
        p_value = np.mean([energy] >= [result.bootstrap_mean] * n_iterations)
        # More accurate: count how many bootstrap samples exceed observed
        bootstrap_samples = np.array([
            energy_stat(surrogate[np.random.choice(len(surrogate), len(surrogate), replace=True)])
            for _ in range(n_iterations)
        ])
        p_value = np.mean(bootstrap_samples >= energy)
        
        results[period] = {
            'significant': p_value < threshold,
            'p_value': p_value,
            'ci': (result.ci_lower, result.ci_upper),
            'observed_energy': energy,
        }
    
    return results


def _generate_phase_randomized_surrogate(
    data: np.ndarray,
    n_realizations: int = 1,
) -> np.ndarray:
    """
    Generate phase-randomized surrogate data for null hypothesis testing.
    
    Preserves power spectrum while randomizing phases.
    """
    from scipy import fft
    
    n = len(data)
    fft_orig = fft.rfft(data)
    
    # Randomize phases while preserving amplitudes
    amplitudes = np.abs(fft_orig)
    phases = np.random.uniform(0, 2 * np.pi, size=len(fft_orig))
    
    # Reconstruct with random phases
    fft_surr = amplitudes * np.exp(1j * phases)
    surrogate = fft.irfft(fft_surr, n=n)
    
    # Preserve mean and std
    surrogate = (surrogate - np.mean(surrogate)) / np.std(surrogate) * np.std(data) + np.mean(data)
    
    return surrogate
