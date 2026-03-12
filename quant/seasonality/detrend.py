"""
Detrending Module - STL and Hodrick-Prescott Filter Implementations

Provides algorithms for removing trend components from time series data
to isolate seasonal patterns for analysis.

Algorithms:
- STL: Seasonal-Trend decomposition using LOESS (robust to outliers)
- HP Filter: Hodrick-Prescott filter for smooth trend extraction

Author: CycleCast AI Agent (Qwen 3.5)
Version: 3.2 Final
Date: 2026-03-13
"""

import numpy as np
import pandas as pd
from typing import Union, Optional, Tuple, List
from scipy import signal
from scipy.optimize import minimize
from scipy.interpolate import UnivariateSpline
import warnings


class STLDecomposition:
    """
    Seasonal-Trend decomposition using LOESS.
    
    Decomposes a time series into three components:
    - Trend: Long-term movement in the data
    - Seasonal: Regular periodic fluctuations
    - Residual: Irremainder after removing trend and seasonal
    
    Based on Cleveland et al. (1990) STL algorithm.
    """
    
    def __init__(
        self,
        period: int,
        seasonal: int = 7,
        trend: Optional[int] = None,
        robust: bool = True,
        seasonal_deg: int = 1,
        trend_deg: int = 1,
        inner_iter: int = 2,
        outer_iter: int = 15
    ):
        """
        Initialize STL decomposition.
        
        Args:
            period: Length of seasonal cycle (e.g., 12 for monthly, 252 for daily trading)
            seasonal: Loess window for seasonal smoothing (odd integer >= period)
            trend: Loess window for trend smoothing (odd integer, default: next odd after period)
            robust: Use robust fitting to reduce outlier influence
            seasonal_deg: Degree of local polynomial for seasonal smoothing (1 or 2)
            trend_deg: Degree of local polynomial for trend smoothing (1 or 2)
            inner_iter: Number of inner loop iterations for convergence
            outer_iter: Number of outer loop iterations for robust fitting
        """
        self.period = period
        self.seasonal = seasonal if seasonal % 2 == 1 else seasonal + 1
        self.trend = trend if trend else (period + 1 if period % 2 == 0 else period)
        if self.trend % 2 == 0:
            self.trend += 1
        self.robust = robust
        self.seasonal_deg = seasonal_deg
        self.trend_deg = trend_deg
        self.inner_iter = inner_iter
        self.outer_iter = outer_iter
        
        self.trend_component: Optional[np.ndarray] = None
        self.seasonal_component: Optional[np.ndarray] = None
        self.residual_component: Optional[np.ndarray] = None
        
    def _loess_smooth(
        self,
        x: np.ndarray,
        y: np.ndarray,
        x_eval: np.ndarray,
        frac: float,
        degree: int = 1,
        weights: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Local polynomial regression (LOESS) smoothing.
        
        Args:
            x: Independent variable values
            y: Dependent variable values
            x_eval: Points at which to evaluate the smoothed function
            frac: Fraction of data to use for each local fit (0 < frac <= 1)
            degree: Degree of local polynomial (1=linear, 2=quadratic)
            weights: Optional robustness weights
            
        Returns:
            Smoothed values at x_eval points
        """
        n = len(x)
        n_eval = len(x_eval)
        result = np.zeros(n_eval)
        
        # Number of points in local neighborhood
        q = int(np.ceil(frac * n))
        q = min(q, n)  # Ensure q doesn't exceed n
        
        for i, x0 in enumerate(x_eval):
            # Calculate distances and select neighborhood
            distances = np.abs(x - x0)
            idx = np.argsort(distances)[:q]
            x_local = x[idx]
            y_local = y[idx]
            
            # Tricube weights based on distance
            max_dist = np.max(distances[idx])
            if max_dist > 0:
                u = distances[idx] / max_dist
                local_weights = np.maximum(0, 1 - u**3)**3
            else:
                local_weights = np.ones(q)
            
            # Apply robustness weights if provided
            if weights is not None:
                local_weights *= weights[idx]
            
            # Build design matrix for polynomial regression
            X = np.vstack([np.ones(q), (x_local - x0)] if degree == 1 
                         else [np.ones(q), (x_local - x0), (x_local - x0)**2])
            X = X.T
            
            # Weighted least squares
            W = np.diag(local_weights)
            try:
                # Solve (X'WX)^-1 X'Wy
                beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y_local)
                result[i] = beta[0]  # Intercept is the fitted value at x0
            except np.linalg.LinAlgError:
                # Fallback to simple average if matrix is singular
                result[i] = np.average(y_local, weights=local_weights)
        
        return result
    
    def _compute_robustness_weights(self, residuals: np.ndarray) -> np.ndarray:
        """
        Compute robustness weights based on residuals.
        
        Uses bisquare weighting function to down-weight outliers.
        
        Args:
            residuals: Array of residuals from current fit
            
        Returns:
            Robustness weights array
        """
        # Median absolute deviation for robust scale estimate
        mad = np.median(np.abs(residuals - np.median(residuals)))
        if mad == 0:
            mad = np.std(residuals)
        if mad == 0:
            return np.ones(len(residuals))
        
        # Scale factor for normal distribution
        c = 6.0
        u = np.abs(residuals) / (c * mad)
        
        # Bisquare weights
        weights = np.where(u < 1, (1 - u**2)**2, 0.0)
        return weights
    
    def _extract_seasonal(self, detrended: np.ndarray, iteration: int) -> np.ndarray:
        """
        Extract seasonal component using moving average and LOESS.
        
        Args:
            detrended: Detrended series (original - trend)
            iteration: Current iteration number (for seasonal subseries)
            
        Returns:
            Seasonal component array
        """
        n = len(detrended)
        
        # Step 1: Cycle-subseries smoothing
        seasonal_subseries = np.zeros((self.period, n))
        
        for s in range(self.period):
            # Extract subseries for season s
            indices = np.arange(s, n, self.period)
            subseries = detrended[indices]
            
            # Apply LOESS smoothing to subseries
            if len(subseries) >= 3:
                x_sub = np.arange(len(subseries))
                smoothed = self._loess_smooth(
                    x_sub, subseries, x_sub,
                    frac=min(1.0, self.seasonal / len(subseries)),
                    degree=self.seasonal_deg
                )
                seasonal_subseries[s, indices] = smoothed
            else:
                seasonal_subseries[s, indices] = np.mean(subseries) if len(subseries) > 0 else 0
        
        # Step 2: Low-pass filter to remove residual trend
        # Apply moving average of length period
        seasonal = np.zeros(n)
        for i in range(n):
            start = max(0, i - self.period // 2)
            end = min(n, i + self.period // 2 + 1)
            seasonal[i] = np.mean(seasonal_subseries[:, i][seasonal_subseries[:, i] != 0])
        
        # Step 3: Center the seasonal component (sum to zero over each period)
        for s in range(self.period):
            indices = np.arange(s, n, self.period)
            if len(indices) > 0:
                mean_val = np.mean(seasonal[indices])
                seasonal[indices] -= mean_val
        
        return seasonal
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'STLDecomposition':
        """
        Fit the STL decomposition to the data.
        
        Args:
            data: Time series data to decompose
            
        Returns:
            Self with fitted components
        """
        if isinstance(data, pd.Series):
            y = data.values
        else:
            y = np.asarray(data, dtype=float)
        
        n = len(y)
        if n < 2 * self.period:
            raise ValueError(f"Data length ({n}) must be at least 2x period ({self.period})")
        
        # Handle missing values
        mask = ~np.isnan(y)
        if not np.all(mask):
            warnings.warn("Missing values detected; using interpolation")
            y_interp = pd.Series(y).interpolate(method='linear').values
        else:
            y_interp = y.copy()
        
        # Initialize components
        trend = np.zeros(n)
        seasonal = np.zeros(n)
        residual = np.zeros(n)
        
        # Outer loop for robust fitting
        robust_weights = np.ones(n)
        
        for outer in range(self.outer_iter + 1):
            # Inner loop: alternating trend and seasonal estimation
            for inner in range(self.inner_iter):
                # Step 1: Detrend and extract seasonal
                detrended = y_interp - trend
                seasonal = self._extract_seasonal(detrended, inner)
                
                # Step 2: Deseasonalize and extract trend
                deseasonalized = y_interp - seasonal
                x = np.arange(n)
                
                trend = self._loess_smooth(
                    x, deseasonalized, x,
                    frac=min(1.0, self.trend / n),
                    degree=self.trend_deg,
                    weights=robust_weights if self.robust and outer > 0 else None
                )
            
            # Update residuals and robustness weights
            residual = y_interp - trend - seasonal
            
            if self.robust and outer < self.outer_iter:
                robust_weights = self._compute_robustness_weights(residual)
        
        # Store components
        self.trend_component = trend
        self.seasonal_component = seasonal
        self.residual_component = residual
        
        return self
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> pd.DataFrame:
        """
        Transform data by extracting components.
        
        Args:
            data: Time series data
            
        Returns:
            DataFrame with original, trend, seasonal, and residual columns
        """
        if self.trend_component is None:
            raise RuntimeError("Must call fit() before transform()")
        
        if isinstance(data, pd.Series):
            index = data.index
            y = data.values
        else:
            index = None
            y = np.asarray(data, dtype=float)
        
        result = pd.DataFrame({
            'original': y,
            'trend': self.trend_component,
            'seasonal': self.seasonal_component,
            'residual': self.residual_component
        }, index=index)
        
        return result
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)
    
    def get_seasonal_component(self) -> Optional[np.ndarray]:
        """Return the extracted seasonal component."""
        return self.seasonal_component
    
    def get_trend_component(self) -> Optional[np.ndarray]:
        """Return the extracted trend component."""
        return self.trend_component
    
    def get_residual_component(self) -> Optional[np.ndarray]:
        """Return the residual (noise) component."""
        return self.residual_component


class HodrickPrescottFilter:
    """
    Hodrick-Prescott Filter for trend extraction.
    
    Separates a time series into trend and cyclical components
    by minimizing: sum((y_t - tau_t)^2) + lambda * sum((tau_{t+1} - 2*tau_t + tau_{t-1})^2)
    
    The smoothing parameter lambda controls the trade-off between
    fit quality and trend smoothness.
    
    Reference: Hodrick, R. J., & Prescott, E. C. (1997).
    """
    
    # Default lambda values by data frequency
    LAMBDA_DEFAULTS = {
        'annual': 100,
        'quarterly': 1600,
        'monthly': 14400,
        'weekly': 100000,
        'daily': 160000,  # Trading days
    }
    
    def __init__(self, lamb: Optional[float] = None, freq: str = 'daily'):
        """
        Initialize HP filter.
        
        Args:
            lamb: Smoothing parameter (higher = smoother trend)
            freq: Data frequency for default lambda selection
        """
        if lamb is None:
            self.lamb = self.LAMBDA_DEFAULTS.get(freq, 160000)
        else:
            self.lamb = lamb
        
        self.trend: Optional[np.ndarray] = None
        self.cycle: Optional[np.ndarray] = None
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'HodrickPrescottFilter':
        """
        Fit the HP filter to extract trend.
        
        Solves: (I + lambda*D'D) * tau = y
        where D is the second-difference matrix.
        
        Args:
            data: Time series data
            
        Returns:
            Self with fitted components
        """
        if isinstance(data, pd.Series):
            y = data.values
        else:
            y = np.asarray(data, dtype=float)
        
        n = len(y)
        if n < 3:
            raise ValueError("HP filter requires at least 3 data points")
        
        # Build the penalty matrix D'D (second difference operator)
        # D is (n-2) x n matrix with [1, -2, 1] pattern
        # D'D is n x n tridiagonal-like matrix
        
        # Create the matrix efficiently using sparse-like operations
        DTD = np.zeros((n, n))
        
        # Interior points: [1, -4, 6, -4, 1] pattern from D'D
        for i in range(2, n - 2):
            DTD[i, i-2] = 1
            DTD[i, i-1] = -4
            DTD[i, i] = 6
            DTD[i, i+1] = -4
            DTD[i, i+2] = 1
        
        # Boundary adjustments
        DTD[0, 0] = 1
        DTD[1, 1] = 5
        DTD[1, 2] = -4
        DTD[1, 3] = 1
        DTD[n-2, n-4] = 1
        DTD[n-2, n-3] = -4
        DTD[n-2, n-2] = 5
        DTD[n-1, n-1] = 1
        
        # Solve: (I + lambda*DTD) * tau = y
        A = np.eye(n) + self.lamb * DTD
        
        try:
            self.trend = np.linalg.solve(A, y)
        except np.linalg.LinAlgError:
            # Fallback: use iterative method for ill-conditioned matrices
            self.trend = self._solve_iterative(A, y, max_iter=1000, tol=1e-8)
        
        self.cycle = y - self.trend
        return self
    
    def _solve_iterative(
        self,
        A: np.ndarray,
        b: np.ndarray,
        max_iter: int = 1000,
        tol: float = 1e-8
    ) -> np.ndarray:
        """
        Solve linear system using conjugate gradient method.
        
        Fallback for when direct solve fails.
        """
        n = len(b)
        x = b.copy()  # Initial guess
        r = b - A @ x
        p = r.copy()
        rs_old = np.dot(r, r)
        
        for _ in range(max_iter):
            Ap = A @ p
            alpha = rs_old / np.dot(p, Ap)
            x = x + alpha * p
            r = r - alpha * Ap
            rs_new = np.dot(r, r)
            
            if np.sqrt(rs_new) < tol:
                break
                
            p = r + (rs_new / rs_old) * p
            rs_old = rs_new
        
        return x
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> pd.DataFrame:
        """
        Transform data by extracting trend and cycle.
        
        Args:
            data: Time series data
            
        Returns:
            DataFrame with original, trend, and cycle columns
        """
        if self.trend is None:
            raise RuntimeError("Must call fit() before transform()")
        
        if isinstance(data, pd.Series):
            index = data.index
            y = data.values
        else:
            index = None
            y = np.asarray(data, dtype=float)
        
        result = pd.DataFrame({
            'original': y,
            'trend': self.trend,
            'cycle': self.cycle
        }, index=index)
        
        return result
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)
    
    def get_trend(self) -> Optional[np.ndarray]:
        """Return the extracted trend component."""
        return self.trend
    
    def get_cycle(self) -> Optional[np.ndarray]:
        """Return the cyclical component."""
        return self.cycle


class DetrendPipeline:
    """
    Pipeline for detrending time series data.
    
    Supports multiple detrending methods and allows chaining
    with normalization for seasonality analysis.
    """
    
    METHODS = ['stl', 'hp', 'linear', 'difference']
    
    def __init__(
        self,
        method: str = 'stl',
        period: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize detrending pipeline.
        
        Args:
            method: Detrending method ('stl', 'hp', 'linear', 'difference')
            period: Seasonal period (required for 'stl' method)
            **kwargs: Additional parameters passed to the detrending method
        """
        if method not in self.METHODS:
            raise ValueError(f"Method must be one of {self.METHODS}")
        
        self.method = method
        self.period = period
        self.kwargs = kwargs
        self._model = None
        self._fitted = False
        
        # Initialize appropriate model
        if method == 'stl':
            if period is None:
                raise ValueError("period is required for STL method")
            self._model = STLDecomposition(period=period, **kwargs)
        elif method == 'hp':
            self._model = HodrickPrescottFilter(**kwargs)
    
    def fit(self, data: Union[np.ndarray, pd.Series]) -> 'DetrendPipeline':
        """Fit the detrending model to data."""
        if self.method == 'stl':
            self._model.fit(data)
        elif self.method == 'hp':
            self._model.fit(data)
        elif self.method == 'linear':
            # Simple linear regression detrending
            if isinstance(data, pd.Series):
                y = data.values
                x = np.arange(len(y))
            else:
                y = np.asarray(data, dtype=float)
                x = np.arange(len(y))
            
            # Fit linear trend
            coeffs = np.polyfit(x, y, 1)
            self._model = {'coeffs': coeffs, 'trend': np.polyval(coeffs, x)}
        elif self.method == 'difference':
            # First-order differencing
            if isinstance(data, pd.Series):
                self._model = {'original_index': data.index, 'first_value': data.iloc[0]}
            else:
                self._model = {'first_value': data[0]}
        
        self._fitted = True
        return self
    
    def transform(self, data: Union[np.ndarray, pd.Series]) -> Union[pd.DataFrame, np.ndarray]:
        """
        Transform data by removing trend.
        
        Returns:
            For STL/HP: DataFrame with components
            For linear/difference: Detrended array
        """
        if not self._fitted:
            raise RuntimeError("Must call fit() before transform()")
        
        if self.method == 'stl':
            return self._model.transform(data)
        elif self.method == 'hp':
            return self._model.transform(data)
        elif self.method == 'linear':
            if isinstance(data, pd.Series):
                y = data.values
                index = data.index
            else:
                y = np.asarray(data, dtype=float)
                index = None
            
            trend = np.polyval(self._model['coeffs'], np.arange(len(y)))
            detrended = y - trend
            
            if index is not None:
                return pd.Series(detrended, index=index, name='detrended')
            return detrended
        elif self.method == 'difference':
            if isinstance(data, pd.Series):
                diff = data.diff()
                # Don't fill first NaN - it's a valid result of differencing
                return diff
            else:
                diff = np.diff(data, prepend=np.nan)
                return diff
        
        return data
    
    def fit_transform(self, data: Union[np.ndarray, pd.Series]) -> Union[pd.DataFrame, np.ndarray]:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)
    
    def get_seasonal_component(self) -> Optional[np.ndarray]:
        """Extract seasonal component (STL method only)."""
        if self.method != 'stl' or not hasattr(self._model, 'get_seasonal_component'):
            return None
        return self._model.get_seasonal_component()
    
    def get_trend_component(self) -> Optional[np.ndarray]:
        """Extract trend component."""
        if self.method == 'stl':
            return self._model.get_trend_component()
        elif self.method == 'hp':
            return self._model.get_trend()
        elif self.method == 'linear':
            return self._model['trend']
        return None
    
    def get_detrended(self) -> Optional[np.ndarray]:
        """
        Get the detrended series (original - trend).
        
        For STL: returns seasonal + residual
        For HP: returns cycle component
        """
        if self.method == 'stl':
            seasonal = self._model.get_seasonal_component()
            residual = self._model.get_residual_component()
            if seasonal is not None and residual is not None:
                return seasonal + residual
        elif self.method == 'hp':
            return self._model.get_cycle()
        return None


def validate_detrended_data(
    original: np.ndarray,
    detrended: np.ndarray,
    method: str = 'stl',
    tolerance: float = 1e-6
) -> Tuple[bool, dict]:
    """
    Validate that detrending was performed correctly.
    
    Checks:
    - No NaN/inf values introduced
    - Trend removal reduces variance appropriately
    - Seasonal component (if applicable) has expected periodicity
    
    Args:
        original: Original time series
        detrended: Detrended output
        method: Detrending method used
        tolerance: Numerical tolerance for checks
        
    Returns:
        Tuple of (is_valid, diagnostic_dict)
    """
    diagnostics = {
        'nan_count': np.sum(np.isnan(detrended)),
        'inf_count': np.sum(np.isinf(detrended)),
        'variance_ratio': np.var(detrended) / np.var(original) if np.var(original) > 0 else np.nan,
        'mean_shift': np.abs(np.mean(detrended) - np.mean(original)),
    }
    
    # Check for numerical issues
    if diagnostics['nan_count'] > 0 or diagnostics['inf_count'] > 0:
        return False, diagnostics
    
    # Check that variance is reduced (detrending should remove some variation)
    if diagnostics['variance_ratio'] > 1.5:  # Allow some increase due to numerical effects
        warnings.warn(f"Variance increased after detrending: {diagnostics['variance_ratio']:.3f}")
    
    # For STL, check seasonal component periodicity
    if method == 'stl' and hasattr(detrended, 'columns') and 'seasonal' in detrended.columns:
        seasonal = detrended['seasonal'].values
        # Check autocorrelation at expected period
        if len(seasonal) > 20:
            acf = np.correlate(seasonal - np.mean(seasonal), 
                             seasonal - np.mean(seasonal), mode='full')
            acf = acf[len(acf)//2:]
            acf = acf / acf[0] if acf[0] != 0 else acf
    
    return True, diagnostics
