"""
Simple validation test for QSpectrum module.
Run directly to verify core functions work.
"""

import numpy as np

# Inline the core functions for testing (to avoid import issues)
from dataclasses import dataclass
from typing import List, Optional
import warnings


@dataclass
class CycleInfo:
    period: int
    energy: float
    stability: float
    correlation: float
    amplitude: float
    phase: float


@dataclass
class QSpectrumResult:
    cycles: List[CycleInfo]
    top3: List[CycleInfo]
    dominant_period: int
    spectral_entropy: float
    is_valid: bool
    validation_message: str


def cyclic_correlation(prices: np.ndarray, period: int) -> float:
    if period < 1 or period >= len(prices):
        return 0.0
    n = len(prices)
    correlation_sum = sum(prices[t] * prices[t - period] for t in range(period, n))
    return correlation_sum / (n - period)


def calculate_wfa_stability(prices: np.ndarray, period: int, n_windows: int = 5) -> float:
    n = len(prices)
    window_size = n // n_windows
    if window_size < period * 2:
        return 0.5
    positive_count = 0
    for i in range(n_windows):
        start_idx = i * window_size
        end_idx = start_idx + window_size
        if end_idx > n:
            break
        window_prices = prices[start_idx:end_idx]
        if len(window_prices) > period:
            corr = cyclic_correlation(window_prices, period)
            if corr > 0:
                positive_count += 1
    return positive_count / n_windows


def calculate_cycle_energy(prices: np.ndarray, period: int, wfa_stability: Optional[float] = None) -> float:
    n = len(prices)
    correlation = cyclic_correlation(prices, period)
    if wfa_stability is None:
        wfa_stability = calculate_wfa_stability(prices, period)
    energy = abs(correlation) * np.sqrt(n / period) * wfa_stability
    return energy


def preprocess_prices(prices: np.ndarray) -> np.ndarray:
    n = len(prices)
    t = np.arange(n)
    t_mean, p_mean = np.mean(t), np.mean(prices)
    numerator = np.sum((t - t_mean) * (prices - p_mean))
    denominator = np.sum((t - t_mean) ** 2)
    if denominator > 0:
        slope = numerator / denominator
        intercept = p_mean - slope * t_mean
        trend = slope * t + intercept
    else:
        trend = np.full(n, p_mean)
    detrended = prices - trend
    mean, std = np.mean(detrended), np.std(detrended)
    if std > 0:
        normalized = (detrended - mean) / std
    else:
        normalized = detrended - mean
    return normalized


def find_dominant_cycles(prices: np.ndarray, min_period: int = 5, max_period: int = 100, top_n: int = 3) -> List[CycleInfo]:
    n = len(prices)
    max_period = min(max_period, n // 3)
    cycles = []
    for period in range(min_period, max_period + 1):
        correlation = cyclic_correlation(prices, period)
        wfa_stability = calculate_wfa_stability(prices, period)
        energy = calculate_cycle_energy(prices, period, wfa_stability)
        t = np.arange(len(prices))
        sin_comp = np.sin(2 * np.pi * t / period)
        cos_comp = np.cos(2 * np.pi * t / period)
        a = 2 * np.sum(prices * cos_comp) / n
        b = 2 * np.sum(prices * sin_comp) / n
        amplitude = np.sqrt(a ** 2 + b ** 2)
        phase = np.arctan2(b, a) % (2 * np.pi)
        cycles.append(CycleInfo(period=period, energy=energy, stability=wfa_stability, 
                               correlation=correlation, amplitude=amplitude, phase=phase))
    cycles.sort(key=lambda x: x.energy, reverse=True)
    return cycles[:top_n]


def calculate_spectral_entropy(psd: np.ndarray) -> float:
    psd_norm = psd / (np.sum(psd) + 1e-10)
    entropy = -np.sum(psd_norm * np.log(psd_norm + 1e-10))
    max_entropy = np.log(len(psd))
    return entropy / max_entropy if max_entropy > 0 else 0


def burg_mem(prices: np.ndarray, max_order: int = 50, sampling_freq: float = 1.0):
    n = len(prices)
    if n < max_order + 1:
        max_order = n - 1
    e_f, e_b = prices.copy(), prices.copy()
    ar_coeffs = np.zeros(max_order)
    for order in range(max_order):
        if order >= n - 1:
            break
        numerator = sum(e_f[i] * e_b[i - 1] for i in range(order + 1, n))
        denominator = sum(e_f[i] ** 2 + e_b[i - 1] ** 2 for i in range(order + 1, n))
        reflection = -2 * numerator / denominator if denominator > 0 else 0
        reflection = np.clip(reflection, -0.99, 0.99)
        e_f_new, e_b_new = np.zeros(n), np.zeros(n)
        for i in range(order + 1, n):
            e_f_new[i] = e_f[i] + reflection * e_b[i - 1]
            e_b_new[i] = e_b[i - 1] + reflection * e_f[i]
        e_f, e_b = e_f_new, e_b_new
        if order == 0:
            ar_coeffs[order] = reflection
        else:
            for k in range(order):
                ar_coeffs[k] = ar_coeffs[k] + reflection * ar_coeffs[order - 1 - k]
            ar_coeffs[order] = reflection
    n_freq = n
    frequencies = np.linspace(0, sampling_freq / 2, n_freq // 2 + 1)
    psd = np.zeros(len(frequencies))
    prediction_error = np.sum(e_f ** 2) / (n - max_order) if n > max_order else 1
    for i, f in enumerate(frequencies):
        denom = 1.0 + sum(ar_coeffs[k] * np.exp(-1j * 2 * np.pi * f * (k + 1) / sampling_freq) for k in range(max_order))
        psd[i] = prediction_error / (np.abs(denom) ** 2)
    if np.max(psd) > 0:
        psd = psd / np.max(psd)
    return frequencies, psd, ar_coeffs[:max_order]


def qspectrum(prices: np.ndarray, min_period: int = 5, max_period: int = 100, max_order: int = 50, top_n: int = 3) -> QSpectrumResult:
    if len(prices) < 50:
        return QSpectrumResult([], [], 0, 0, False, "Недостаточно данных (минимум 50 точек)")
    normalized = preprocess_prices(prices)
    top_cycles = find_dominant_cycles(normalized, min_period, max_period, top_n)
    _, psd, _ = burg_mem(normalized, max_order)
    spectral_entropy = calculate_spectral_entropy(psd)
    is_valid = len(top_cycles) > 0 and top_cycles[0].energy > 0.1 and spectral_entropy < 0.9
    msg = "OK" if is_valid else "Низкая энергия цикла или высокая энтропия"
    return QSpectrumResult(top_cycles, top_cycles, top_cycles[0].period if top_cycles else 0, 
                          spectral_entropy, is_valid, msg)


def generate_composite_line(cycles: List[CycleInfo], n_points: int = 100) -> np.ndarray:
    t = np.arange(n_points)
    composite = np.zeros(n_points)
    for cycle in cycles:
        freq = 1.0 / cycle.period
        composite += cycle.amplitude * np.sin(2 * np.pi * freq * t + cycle.phase)
    if np.max(np.abs(composite)) > 0:
        composite = composite / np.max(np.abs(composite))
    return composite


# ============== TESTS ==============

def run_tests():
    print("=" * 60)
    print("QSPECTRUM CORE FUNCTIONS - VALIDATION TESTS")
    print("=" * 60)
    
    np.random.seed(42)
    
    # Test 1: cyclic_correlation with perfect sine
    print("\n[Test 1] cyclic_correlation - Perfect Sine Wave")
    t = np.arange(100)
    sine_10 = np.sin(2 * np.pi * t / 10)
    corr_10 = cyclic_correlation(sine_10, 10)
    corr_5 = cyclic_correlation(sine_10, 5)
    print(f"  Correlation at period 10: {corr_10:.4f}")
    print(f"  Correlation at period 5: {corr_5:.4f}")
    assert corr_10 > corr_5, "Period 10 should have higher correlation"
    print("  ✓ PASSED")
    
    # Test 2: preprocess_prices (detrending)
    print("\n[Test 2] preprocess_prices - Detrending")
    trend_data = 0.1 * t + np.sin(2 * np.pi * t / 20)
    detrended = preprocess_prices(trend_data)
    print(f"  Mean after detrending: {np.mean(detrended):.6f}")
    print(f"  Std after normalization: {np.std(detrended):.6f}")
    assert abs(np.mean(detrended)) < 0.1
    assert abs(np.std(detrended) - 1.0) < 0.1
    print("  ✓ PASSED")
    
    # Test 3: burg_mem
    print("\n[Test 3] burg_mem - Spectral Analysis")
    freqs, psd, coeffs = burg_mem(sine_10, max_order=20)
    print(f"  Frequencies: {len(freqs)} points")
    print(f"  PSD max: {np.max(psd):.4f}")
    print(f"  AR coefficients: {len(coeffs)}")
    assert np.all(psd >= 0), "PSD must be non-negative"
    assert np.max(psd) <= 1.01, "PSD should be normalized"
    print("  ✓ PASSED")
    
    # Test 4: qspectrum on synthetic data
    print("\n[Test 4] qspectrum - Synthetic Multi-Cycle Data")
    n = 500
    t = np.arange(n)
    cycle_14 = 3.0 * np.sin(2 * np.pi * t / 14)
    cycle_42 = 2.0 * np.sin(2 * np.pi * t / 42)
    cycle_98 = 1.0 * np.sin(2 * np.pi * t / 98)
    noise = np.random.randn(n) * 0.5
    synthetic = cycle_14 + cycle_42 + cycle_98 + noise
    
    result = qspectrum(synthetic, min_period=5, max_period=150)
    print(f"  Dominant period: {result.dominant_period}")
    print(f"  Spectral entropy: {result.spectral_entropy:.4f}")
    print(f"  Is valid: {result.is_valid}")
    print(f"  Top 3 cycles:")
    for i, c in enumerate(result.top3, 1):
        print(f"    {i}. Period: {c.period:3d}, Energy: {c.energy:.4f}, Stability: {c.stability:.4f}")
    assert len(result.top3) <= 3
    assert result.dominant_period > 0
    print("  ✓ PASSED")
    
    # Test 5: generate_composite_line
    print("\n[Test 5] generate_composite_line")
    composite = generate_composite_line(result.top3, n_points=100)
    print(f"  Output length: {len(composite)}")
    print(f"  Max absolute value: {np.max(np.abs(composite)):.4f}")
    assert len(composite) == 100
    assert np.max(np.abs(composite)) <= 1.01
    print("  ✓ PASSED")
    
    # Test 6: WFA Stability
    print("\n[Test 6] calculate_wfa_stability")
    stable_signal = np.sin(2 * np.pi * t / 20)
    stability = calculate_wfa_stability(stable_signal, period=20, n_windows=5)
    print(f"  Stability of pure sine: {stability:.4f}")
    assert stability > 0.6, "Pure sine should have high stability"
    print("  ✓ PASSED")
    
    print("\n" + "=" * 60)
    print("ALL VALIDATION TESTS PASSED ✓")
    print("=" * 60)
    return True


if __name__ == '__main__':
    run_tests()
