# quant/bootstrap/__init__.py
# Bootstrap Confidence Interval Module
# CycleCast v3.2 Final

"""
Bootstrap CI module for statistical validation of trading signals.

Provides non-parametric bootstrap confidence intervals with:
- Standard percentile method
- BCa (Bias-Corrected and Accelerated) correction
- Streaming support for gRPC progress updates
- Integration with backtest metrics and QSpectrum results

Example:
    >>> from quant.bootstrap import bootstrap_ci
    >>> import numpy as np
    >>> data = np.random.randn(100)
    >>> result = bootstrap_ci(data, n_iterations=1000)
    >>> print(f"95% CI: [{result.ci_lower:.3f}, {result.ci_upper:.3f}]")
"""

from .core import (
    BootstrapConfig,
    BootstrapResult,
    BootstrapProgress,
    BootstrapCI,
    bootstrap_ci,
    bootstrap_ci_streaming,
    validate_cycle_significance,
)

__all__ = [
    'BootstrapConfig',
    'BootstrapResult', 
    'BootstrapProgress',
    'BootstrapCI',
    'bootstrap_ci',
    'bootstrap_ci_streaming',
    'validate_cycle_significance',
]

__version__ = '1.0.0'
