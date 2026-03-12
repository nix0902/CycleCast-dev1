"""
QSpectrum - Циклический спектральный анализ

Модуль для выявления доминантных циклов в финансовых временных рядах
используя методологию Ларри Вильямса.

Основные функции:
- cyclic_correlation(): Циклическая корреляция (не FFT!)
- burg_mem(): Burg's Maximum Entropy Method
- qspectrum(): Основной метод анализа
- generate_composite_line(): Генерация Composite Line

Пример использования:
    from quant.qspectrum import qspectrum, generate_composite_line
    
    # Загрузка цен
    prices = np.array([...])
    
    # QSpectrum анализ
    result = qspectrum(prices, min_period=5, max_period=100)
    
    # Получение топ-3 циклов
    for cycle in result.top3:
        print(f"Период: {cycle.period}, Энергия: {cycle.energy:.3f}")
    
    # Генерация Composite Line
    composite = generate_composite_line(result.top3, n_points=100)

Версия: 3.2 Final
"""

from .core import (
    CycleInfo,
    QSpectrumResult,
    cyclic_correlation,
    calculate_cycle_energy,
    calculate_wfa_stability,
    burg_mem,
    find_dominant_cycles,
    calculate_spectral_entropy,
    preprocess_prices,
    qspectrum,
    generate_composite_line,
)

__version__ = "3.2.0"
__author__ = "CycleCast Team"

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
    'generate_composite_line',
]
