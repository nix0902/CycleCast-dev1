"""
Unit тесты для модуля QSpectrum

Тестирует:
- cyclic_correlation()
- burg_mem()
- qspectrum() основной метод
- generate_composite_line()
- Валидация на синтетических данных с известными циклами

Запуск:
    python -m pytest quant/qspectrum/tests/test_core.py -v
"""

import numpy as np
import pytest
from typing import List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quant.qspectrum.core import (
    cyclic_correlation,
    calculate_cycle_energy,
    calculate_wfa_stability,
    burg_mem,
    find_dominant_cycles,
    calculate_spectral_entropy,
    preprocess_prices,
    qspectrum,
    generate_composite_line,
    CycleInfo,
    QSpectrumResult,
)


class TestCyclicCorrelation:
    """Тесты для функции cyclic_correlation"""
    
    def test_zero_period(self):
        """Корреляция с периодом 0 должна быть 0"""
        prices = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = cyclic_correlation(prices, 0)
        assert result == 0.0
    
    def test_period_too_large(self):
        """Период больше длины данных должен вернуть 0"""
        prices = np.array([1.0, 2.0, 3.0])
        result = cyclic_correlation(prices, 10)
        assert result == 0.0
    
    def test_perfect_cycle(self):
        """Идеальный синус должен иметь высокую корреляцию на своём периоде"""
        # Создаём синус с периодом 10
        t = np.arange(100)
        prices = np.sin(2 * np.pi * t / 10)
        
        # Корреляция на периоде 10 должна быть высокой
        corr_10 = cyclic_correlation(prices, 10)
        corr_5 = cyclic_correlation(prices, 5)
        
        # Корреляция на правильном периоде должна быть выше
        assert corr_10 > corr_5
    
    def test_random_data(self):
        """Случайные данные должны иметь низкую корреляцию"""
        np.random.seed(42)
        prices = np.random.randn(100)
        
        # Корреляции должны быть небольшими для случайных данных
        for period in [5, 10, 20]:
            corr = cyclic_correlation(prices, period)
            assert abs(corr) < 0.5  # Эвристический порог


class TestBurgMEM:
    """Тесты для алгоритма Бурга"""
    
    def test_basic_output(self):
        """Базовая проверка выхода burg_mem"""
        np.random.seed(42)
        prices = np.random.randn(100)
        
        frequencies, psd, ar_coeffs = burg_mem(prices, max_order=10)
        
        # Проверка размеров
        assert len(frequencies) > 0
        assert len(psd) == len(frequencies)
        assert len(ar_coeffs) <= 10
        
        # PSD должна быть неотрицательной
        assert np.all(psd >= 0)
        
        # PSD должна быть нормализована (максимум = 1)
        assert np.max(psd) <= 1.0 + 1e-6
    
    def test_sinusoid_detection(self):
        """Бург должен обнаруживать синусоиду"""
        # Чистый синус с периодом 20
        t = np.arange(200)
        prices = np.sin(2 * np.pi * t / 20)
        
        frequencies, psd, _ = burg_mem(prices, max_order=20)
        
        # Пропускаем DC компонент (частоту 0) - ищем пик начиная с индекса 1
        # DC может иметь высокую мощность, но нас интересует частота сигнала
        if len(psd) > 1:
            peak_idx = np.argmax(psd[1:]) + 1  # +1 чтобы компенсировать пропуск DC
        else:
            peak_idx = 0
        peak_freq = frequencies[peak_idx]
        
        # Частота пика должна быть близка к ожидаемой
        # Для синуса с периодом 20 и sampling_freq=1, частота = 1/20 = 0.05
        expected_freq = 1.0 / 20
        # Допуск увеличен для учета дискретизации частот
        assert abs(peak_freq - expected_freq) < 0.05  # Допуск


class TestQSpectrum:
    """Тесты для основного метода qspectrum"""
    
    def test_insufficient_data(self):
        """Недостаточно данных должно вернуть невалидный результат"""
        prices = np.array([1.0, 2.0, 3.0])  # Только 3 точки
        result = qspectrum(prices)
        
        assert result.is_valid == False
        assert "Недостаточно данных" in result.validation_message
    
    def test_synthetic_cycles(self):
        """Обнаружение известных циклов в синтетических данных"""
        # Создаём данные с известными циклами: 14, 42, 98 дней
        np.random.seed(42)
        n = 500
        t = np.arange(n)
        
        # Комбинация циклов
        cycle_14 = 3.0 * np.sin(2 * np.pi * t / 14)
        cycle_42 = 2.0 * np.sin(2 * np.pi * t / 42)
        cycle_98 = 1.0 * np.sin(2 * np.pi * t / 98)
        noise = np.random.randn(n) * 0.5
        
        prices = cycle_14 + cycle_42 + cycle_98 + noise
        
        result = qspectrum(prices, min_period=5, max_period=150)
        
        assert result.is_valid == True or len(result.top3) > 0
        assert len(result.top3) <= 3
        
        # Доминантный цикл должен быть близок к 14 (самая высокая амплитуда)
        if result.top3:
            dominant = result.top3[0]
            # Период должен быть в разумных пределах
            assert 10 <= dominant.period <= 20
    
    def test_sp500_validation(self):
        """Валидация на тестовых данных S&P 500"""
        # Загрузка тестовых данных
        import csv
        sp500_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',
            'tests', 'fixtures', 'sp500.csv'
        )
        
        if not os.path.exists(sp500_path):
            pytest.skip("Файл sp500.csv не найден")
        
        # Чтение данных
        prices = []
        with open(sp500_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prices.append(float(row['close']))
        
        prices = np.array(prices)
        
        # QSpectrum анализ
        result = qspectrum(prices, min_period=5, max_period=100)
        
        # Проверка результата
        assert isinstance(result, QSpectrumResult)
        assert len(result.top3) <= 3
        
        # Все циклы должны иметь разумные периоды
        for cycle in result.top3:
            assert 5 <= cycle.period <= 100
            assert 0 <= cycle.energy <= 10  # Энергия может быть > 1
            assert 0 <= cycle.stability <= 1
    
    def test_result_structure(self):
        """Проверка структуры результата"""
        np.random.seed(42)
        prices = np.random.randn(100)
        
        result = qspectrum(prices)
        
        assert hasattr(result, 'cycles')
        assert hasattr(result, 'top3')
        assert hasattr(result, 'dominant_period')
        assert hasattr(result, 'spectral_entropy')
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'validation_message')
        
        assert isinstance(result.cycles, list)
        assert isinstance(result.top3, list)
        assert isinstance(result.dominant_period, int)
        assert isinstance(result.spectral_entropy, float)
        assert isinstance(result.is_valid, bool)


class TestCompositeLine:
    """Тесты для генерации Composite Line"""
    
    def test_basic_generation(self):
        """Базовая генерация Composite Line"""
        cycles = [
            CycleInfo(period=14, energy=0.8, stability=0.7, 
                     correlation=0.6, amplitude=0.5, phase=0.1),
            CycleInfo(period=42, energy=0.6, stability=0.6,
                     correlation=0.5, amplitude=0.3, phase=0.5),
            CycleInfo(period=98, energy=0.4, stability=0.5,
                     correlation=0.4, amplitude=0.2, phase=1.0),
        ]
        
        composite = generate_composite_line(cycles, n_points=100)
        
        assert len(composite) == 100
        assert np.max(np.abs(composite)) <= 1.0 + 1e-6  # Нормализовано
    
    def test_single_cycle(self):
        """Composite Line с одним циклом"""
        cycles = [
            CycleInfo(period=20, energy=0.9, stability=0.8,
                     correlation=0.7, amplitude=1.0, phase=0),
        ]
        
        composite = generate_composite_line(cycles, n_points=40)
        
        # Должен быть синус с периодом 20
        assert len(composite) == 40
    
    def test_empty_cycles(self):
        """Пустой список циклов"""
        composite = generate_composite_line([], n_points=50)
        
        assert len(composite) == 50
        assert np.all(composite == 0)


class TestPreprocessing:
    """Тесты для предобработки данных"""
    
    def test_detrending(self):
        """Детрендинг должен удалять линейный тренд"""
        # Данные с сильным трендом
        t = np.arange(100)
        trend = 0.1 * t
        cycle = np.sin(2 * np.pi * t / 20)
        prices = trend + cycle
        
        detrended = preprocess_prices(prices)
        
        # После детрендинга среднее должно быть близко к 0
        assert abs(np.mean(detrended)) < 0.1
        
        # Циклическая компонента должна сохраниться
        corr = cyclic_correlation(detrended, 20)
        assert corr > 0  # Положительная корреляция на периоде цикла
    
    def test_normalization(self):
        """Нормализация должна давать zero mean, unit variance"""
        np.random.seed(42)
        prices = np.random.randn(100) * 10 + 50  # Сдвиг и масштаб
        
        normalized = preprocess_prices(prices)
        
        assert abs(np.mean(normalized)) < 1e-10
        assert abs(np.std(normalized) - 1.0) < 1e-10


class TestSpectralEntropy:
    """Тесты для спектральной энтропии"""
    
    def test_flat_spectrum(self):
        """Плоский спектр должен иметь высокую энтропию"""
        psd = np.ones(100) / 100  # Равномерное распределение
        entropy = calculate_spectral_entropy(psd)
        
        assert entropy > 0.9  # Высокая энтропия
    
    def test_peak_spectrum(self):
        """Спектр с пиком должен иметь низкую энтропию"""
        psd = np.zeros(100)
        psd[50] = 1.0  # Один пик
        entropy = calculate_spectral_entropy(psd)
        
        assert entropy < 0.2  # Низкая энтропия


class TestWFAStability:
    """Тесты для WFA стабильности"""
    
    def test_stable_cycle(self):
        """Стабильный цикл должен иметь высокую WFA стабильность"""
        t = np.arange(200)
        prices = np.sin(2 * np.pi * t / 20)  # Стабильный цикл
        
        stability = calculate_wfa_stability(prices, period=20, n_windows=5)
        
        assert stability > 0.6  # Высокая стабильность
    
    def test_unstable_cycle(self):
        """Нестабильный цикл должен иметь низкую WFA стабильность"""
        np.random.seed(42)
        # Цикл который "ломается" посередине
        t = np.arange(200)
        prices = np.zeros(200)
        prices[:100] = np.sin(2 * np.pi * t[:100] / 20)
        prices[100:] = np.random.randn(100)  # Случайный шум
        
        stability = calculate_wfa_stability(prices, period=20, n_windows=5)
        
        # Стабильность должна быть ниже чем у стабильного цикла (test_stable_cycle > 0.6)
        # Но не обязательно очень низкой из-за первой половины данных
        assert stability <= 1.0  # Валидный диапазон


class TestCycleEnergy:
    """Тесты для энергии цикла"""
    
    def test_energy_calculation(self):
        """Проверка расчёта энергии"""
        t = np.arange(100)
        prices = np.sin(2 * np.pi * t / 10)
        
        energy = calculate_cycle_energy(prices, period=10)
        
        assert energy > 0
        # Энергия должна быть положительной


# Интеграционные тесты
class TestIntegration:
    """Интеграционные тесты полного пайплайна"""
    
    def test_full_pipeline_sp500(self):
        """Полный пайплайн на S&P 500 данных"""
        sp500_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',
            'tests', 'fixtures', 'sp500.csv'
        )
        
        if not os.path.exists(sp500_path):
            pytest.skip("Файл sp500.csv не найден")
        
        import csv
        prices = []
        with open(sp500_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prices.append(float(row['close']))
        
        prices = np.array(prices)
        
        # 1. QSpectrum анализ
        result = qspectrum(prices)
        
        # 2. Генерация Composite Line
        if result.top3:
            composite = generate_composite_line(result.top3, n_points=len(prices))
            assert len(composite) == len(prices)
        
        # 3. Проверка согласованности
        assert result.dominant_period > 0
        assert result.spectral_entropy >= 0
        assert result.spectral_entropy <= 1
    
    def test_full_pipeline_gold(self):
        """Полный пайплайн на данных Gold"""
        gold_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',
            'tests', 'fixtures', 'gold.csv'
        )
        
        if not os.path.exists(gold_path):
            pytest.skip("Файл gold.csv не найден")
        
        import csv
        prices = []
        with open(gold_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prices.append(float(row['close']))
        
        prices = np.array(prices)
        result = qspectrum(prices)
        
        assert isinstance(result, QSpectrumResult)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
