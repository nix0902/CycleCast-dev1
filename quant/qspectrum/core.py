"""
QSpectrum - Циклический спектральный анализ (Larry Williams methodology)

Модуль для выявления доминантных циклов в финансовых временных рядах
с использованием:
- Циклической корреляции (не FFT!)
- МЭМ (Burg's Maximum Entropy Method)
- Walk-Forward Analysis стабильности

Версия: 3.2 Final
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import warnings


@dataclass
class CycleInfo:
    """Информация о выявленном цикле"""
    period: int           # Период цикла в барах
    energy: float         # Энергия цикла (0-1 нормализовано)
    stability: float      # WFA стабильность (0-1)
    correlation: float    # Циклическая корреляция
    amplitude: float      # Амплитуда
    phase: float          # Фаза (0-2π)


@dataclass
class QSpectrumResult:
    """Результат анализа QSpectrum"""
    cycles: List[CycleInfo]           # Все выявленные циклы
    top3: List[CycleInfo]             # Топ-3 доминантных цикла
    dominant_period: int              # Доминантный период
    spectral_entropy: float           # Энтропия спектра
    is_valid: bool                    # Валидность результата
    validation_message: str           # Сообщение о валидации


def cyclic_correlation(prices: np.ndarray, period: int) -> float:
    """
    Вычисляет циклическую корреляцию для заданного периода.
    
    Формула (из TZ.md):
    CyclicCorrelation(period) = Σ(t=period to N) [P(t) × P(t-period)] / (N - period)
    
    Args:
        prices: Массив цен (детренденный и нормализованный)
        period: Период для проверки
        
    Returns:
        Значение циклической корреляции
    """
    if period < 1 or period >= len(prices):
        return 0.0
    
    n = len(prices)
    # Циклическая корреляция: сумма произведений P(t) * P(t-period)
    correlation_sum = 0.0
    for t in range(period, n):
        correlation_sum += prices[t] * prices[t - period]
    
    # Нормализация на количество точек
    correlation = correlation_sum / (n - period)
    
    return correlation


def calculate_cycle_energy(
    prices: np.ndarray,
    period: int,
    wfa_stability: Optional[float] = None
) -> float:
    """
    Вычисляет энергию цикла.
    
    Формула (из TZ.md):
    Energy(period) = |CyclicCorrelation| × √(N/period) × WFA_Stability
    
    Args:
        prices: Массив цен
        period: Период цикла
        wfa_stability: Стабильность WFA (если None, вычисляется)
        
    Returns:
        Энергия цикла (нормализованная 0-1)
    """
    n = len(prices)
    correlation = cyclic_correlation(prices, period)
    
    # Если WFA стабильность не предоставлена, вычисляем её
    if wfa_stability is None:
        wfa_stability = calculate_wfa_stability(prices, period)
    
    # Энергия цикла
    energy = abs(correlation) * np.sqrt(n / period) * wfa_stability
    
    return energy


def calculate_wfa_stability(
    prices: np.ndarray,
    period: int,
    n_windows: int = 5
) -> float:
    """
    Вычисляет стабильность цикла через Walk-Forward Analysis.
    
    Формула (из TZ.md):
    WFA_Stability = Count(Correlation > 0) / Total_Periods
    
    Args:
        prices: Массив цен
        period: Период цикла
        n_windows: Количество окон для WFA
        
    Returns:
        Стабильность (0-1)
    """
    n = len(prices)
    window_size = n // n_windows
    
    if window_size < period * 2:
        # Недостаточно данных для WFA
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
    
    stability = positive_count / n_windows
    return stability


def burg_mem(
    prices: np.ndarray,
    max_order: int = 50,
    sampling_freq: float = 1.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Алгоритм Бурга для спектральной оценки (Maximum Entropy Method).
    
    Формула (из TZ.md):
    P(f) = σ² / |1 + Σ(k=1 to p) aₖ × e^(-i2πfk)|²
    
    Args:
        prices: Входной временной ряд (детренденный)
        max_order: Максимальный порядок модели AR
        sampling_freq: Частота дискретизации
        
    Returns:
        frequencies: Массив частот
        psd: Спектральная плотность мощности
        ar_coefficients: Коэффициенты AR модели
    """
    n = len(prices)
    
    if n < max_order + 1:
        max_order = n - 1
        warnings.warn(f"Уменьшен порядок модели до {max_order} из-за недостатка данных")
    
    # Инициализация
    e_f = prices.copy()  # Прямая ошибка предсказания
    e_b = prices.copy()  # Обратная ошибка предсказания
    
    ar_coeffs = np.zeros(max_order)
    reflection_coeffs = np.zeros(max_order)
    
    # Начальная энергия
    e_total = np.sum(e_f ** 2) + np.sum(e_b[:-1] ** 2)
    
    for order in range(max_order):
        if order >= n - 1:
            break
            
        # Вычисление коэффициента отражения (reflection coefficient)
        numerator = 0.0
        denominator = 0.0
        
        for i in range(order + 1, n):
            numerator += e_f[i] * e_b[i - 1]
            denominator += e_f[i] ** 2 + e_b[i - 1] ** 2
        
        if denominator == 0:
            reflection_coeffs[order] = 0
        else:
            reflection_coeffs[order] = -2 * numerator / denominator
        
        # Ограничение коэффициента отражения (стабильность)
        reflection_coeffs[order] = np.clip(reflection_coeffs[order], -0.99, 0.99)
        
        # Обновление ошибок предсказания
        e_f_new = np.zeros(n)
        e_b_new = np.zeros(n)
        
        for i in range(order + 1, n):
            e_f_new[i] = e_f[i] + reflection_coeffs[order] * e_b[i - 1]
            e_b_new[i] = e_b[i - 1] + reflection_coeffs[order] * e_f[i]
        
        e_f = e_f_new
        e_b = e_b_new
        
        # Обновление AR коэффициентов (рекурсия Левинсона-Дурбина)
        if order == 0:
            ar_coeffs[order] = reflection_coeffs[order]
        else:
            for k in range(order):
                ar_coeffs[k] = ar_coeffs[k] + reflection_coeffs[order] * ar_coeffs[order - 1 - k]
            ar_coeffs[order] = reflection_coeffs[order]
    
    # Вычисление спектральной плотности мощности (PSD)
    n_freq = n  # Количество частотных точек
    
    # Частоты от 0 до Nyquist
    frequencies = np.linspace(0, sampling_freq / 2, n_freq // 2 + 1)
    
    # Вычисление PSD через AR модель
    psd = np.zeros(len(frequencies))
    
    # Оценка дисперсии белого шума
    prediction_error = np.sum(e_f ** 2) / (n - max_order)
    
    for i, f in enumerate(frequencies):
        # P(f) = σ² / |1 + Σ(k=1 to p) aₖ × e^(-i2πfk)|²
        denominator_sum = 1.0
        for k in range(max_order):
            denominator_sum += ar_coeffs[k] * np.exp(-1j * 2 * np.pi * f * (k + 1) / sampling_freq)
        
        psd[i] = prediction_error / (np.abs(denominator_sum) ** 2)
    
    # Нормализация PSD
    if np.max(psd) > 0:
        psd = psd / np.max(psd)
    
    return frequencies, psd, ar_coeffs[:max_order]


def find_dominant_cycles(
    prices: np.ndarray,
    min_period: int = 5,
    max_period: int = 100,
    top_n: int = 3
) -> List[CycleInfo]:
    """
    Находит доминантные циклы в ценовом ряде.
    
    Args:
        prices: Массив цен (детренденный и нормализованный)
        min_period: Минимальный период для поиска
        max_period: Максимальный период для поиска
        top_n: Количество топ циклов для возврата
        
    Returns:
        Список CycleInfo отсортированный по энергии (убывание)
    """
    n = len(prices)
    max_period = min(max_period, n // 3)  # Ограничение по длине данных
    
    cycles = []
    
    # Поиск циклов через циклическую корреляцию
    for period in range(min_period, max_period + 1):
        correlation = cyclic_correlation(prices, period)
        wfa_stability = calculate_wfa_stability(prices, period)
        energy = calculate_cycle_energy(prices, period, wfa_stability)
        
        # Вычисление амплитуды и фазы через корреляцию с синусом/косинусом
        t = np.arange(len(prices))
        sin_component = np.sin(2 * np.pi * t / period)
        cos_component = np.cos(2 * np.pi * t / period)
        
        # Проекция на синус и косинус
        a = 2 * np.sum(prices * cos_component) / n
        b = 2 * np.sum(prices * sin_component) / n
        
        amplitude = np.sqrt(a ** 2 + b ** 2)
        phase = np.arctan2(b, a) % (2 * np.pi)
        
        cycles.append(CycleInfo(
            period=period,
            energy=energy,
            stability=wfa_stability,
            correlation=correlation,
            amplitude=amplitude,
            phase=phase
        ))
    
    # Сортировка по энергии (убывание)
    cycles.sort(key=lambda x: x.energy, reverse=True)
    
    return cycles[:top_n]


def calculate_spectral_entropy(psd: np.ndarray) -> float:
    """
    Вычисляет спектральную энтропию.
    
    Мера "разбросанности" спектра. Низкая энтропия = чёткие доминантные циклы.
    
    Args:
        psd: Спектральная плотность мощности (нормализованная)
        
    Returns:
        Спектральная энтропия (0-1)
    """
    # Нормализация PSD как вероятностного распределения
    psd_norm = psd / (np.sum(psd) + 1e-10)
    
    # Энтропия Шеннона
    entropy = -np.sum(psd_norm * np.log(psd_norm + 1e-10))
    
    # Нормализация на максимальную энтропию
    max_entropy = np.log(len(psd))
    
    if max_entropy > 0:
        entropy = entropy / max_entropy
    
    return entropy


def preprocess_prices(prices: np.ndarray) -> np.ndarray:
    """
    Предобработка цен: детрендинг и нормализация.
    
    Args:
        prices: Исходные цены
        
    Returns:
        Детренденный и нормализованный ряд
    """
    # Детрендинг через линейную регрессию
    n = len(prices)
    t = np.arange(n)
    
    # Линейный тренд
    t_mean = np.mean(t)
    p_mean = np.mean(prices)
    
    numerator = np.sum((t - t_mean) * (prices - p_mean))
    denominator = np.sum((t - t_mean) ** 2)
    
    if denominator > 0:
        slope = numerator / denominator
        intercept = p_mean - slope * t_mean
        trend = slope * t + intercept
    else:
        trend = np.full(n, p_mean)
    
    # Удаление тренда
    detrended = prices - trend
    
    # Нормализация (zero mean, unit variance)
    mean = np.mean(detrended)
    std = np.std(detrended)
    
    if std > 0:
        normalized = (detrended - mean) / std
    else:
        normalized = detrended - mean
    
    return normalized


def qspectrum(
    prices: np.ndarray,
    min_period: int = 5,
    max_period: int = 100,
    max_order: int = 50,
    top_n: int = 3
) -> QSpectrumResult:
    """
    Основной метод QSpectrum анализа.
    
    Комбинирует:
    1. Циклическую корреляцию для поиска периодов
    2. Burg's MEM для спектральной оценки
    3. WFA для оценки стабильности
    
    Args:
        prices: Массив цен (OHLCV close prices)
        min_period: Минимальный период цикла
        max_period: Максимальный период цикла
        max_order: Максимальный порядок модели Бурга
        top_n: Количество топ циклов для возврата
        
    Returns:
        QSpectrumResult с полным анализом
    """
    # Предобработка
    if len(prices) < 50:
        return QSpectrumResult(
            cycles=[],
            top3=[],
            dominant_period=0,
            spectral_entropy=0,
            is_valid=False,
            validation_message="Недостаточно данных (минимум 50 точек)"
        )
    
    normalized_prices = preprocess_prices(prices)
    
    # Поиск доминантных циклов
    top_cycles = find_dominant_cycles(
        normalized_prices,
        min_period=min_period,
        max_period=max_period,
        top_n=top_n
    )
    
    # Burg's MEM спектральный анализ
    frequencies, psd, ar_coeffs = burg_mem(normalized_prices, max_order=max_order)
    
    # Спектральная энтропия
    spectral_entropy = calculate_spectral_entropy(psd)
    
    # Валидация результата
    is_valid = True
    validation_messages = []
    
    if len(top_cycles) == 0:
        is_valid = False
        validation_messages.append("Циклы не найдены")
    
    if top_cycles and top_cycles[0].energy < 0.1:
        validation_messages.append("Низкая энергия доминантного цикла")
    
    if spectral_entropy > 0.9:
        validation_messages.append("Высокая спектральная энтропия (нет чётких циклов)")
    
    # Определение доминантного периода
    dominant_period = top_cycles[0].period if top_cycles else 0
    
    return QSpectrumResult(
        cycles=top_cycles,
        top3=top_cycles,
        dominant_period=dominant_period,
        spectral_entropy=spectral_entropy,
        is_valid=is_valid and len(validation_messages) == 0,
        validation_message="; ".join(validation_messages) if validation_messages else "OK"
    )


def generate_composite_line(
    cycles: List[CycleInfo],
    n_points: int = 100
) -> np.ndarray:
    """
    Генерирует Composite Line на основе топ циклов.
    
    Формула (из TZ.md):
    CL(t) = A₁sin(2πf₁t + φ₁) + A₂sin(2πf₂t + φ₂) + A₃sin(2πf₃t + φ₃)
    
    Args:
        cycles: Список циклов (обычно top3)
        n_points: Количество точек для генерации
        
    Returns:
        Массив значений Composite Line
    """
    t = np.arange(n_points)
    composite = np.zeros(n_points)
    
    for cycle in cycles:
        frequency = 1.0 / cycle.period
        composite += cycle.amplitude * np.sin(2 * np.pi * frequency * t + cycle.phase)
    
    # Нормализация
    if np.max(np.abs(composite)) > 0:
        composite = composite / np.max(np.abs(composite))
    
    return composite


# Экспорт публичного API
__all__ = [
    'CycleInfo',
    'QSpectrumResult',
    'cyclic_correlation',
    'calculate_cycle_energy',
    'calculate_wfa_stability',
    'burg_mem',
    'find_dominant_cycles',
    'calculate_spectral_entropy',
    'preprocess_prices',
    'qspectrum',
    'generate_composite_line'
]
