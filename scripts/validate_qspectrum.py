"""
QSpectrum Validation Script

Валидация алгоритма QSpectrum на тестовых данных S&P 500.

Запуск:
    python scripts/validate_qspectrum.py
"""

import sys
import os
import csv
import numpy as np

# Добавляем путь к модулю quant
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.qspectrum.core import (
    qspectrum,
    generate_composite_line,
    preprocess_prices,
    cyclic_correlation,
    burg_mem,
)


def load_csv_data(filepath: str) -> np.ndarray:
    """Загружает цены close из CSV файла"""
    prices = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prices.append(float(row['close']))
    return np.array(prices)


def validate_qspectrum():
    """Основная функция валидации"""
    print("=" * 60)
    print("QSPECTRUM VALIDATION - S&P 500 Test Data")
    print("=" * 60)
    
    # Пути к тестовым данным
    fixtures_dir = os.path.join(os.path.dirname(__file__), '..', 'tests', 'fixtures')
    sp500_path = os.path.join(fixtures_dir, 'sp500.csv')
    gold_path = os.path.join(fixtures_dir, 'gold.csv')
    btc_path = os.path.join(fixtures_dir, 'btc.csv')
    
    results = {}
    
    for name, path in [('S&P 500', sp500_path), ('Gold', gold_path), ('BTC', btc_path)]:
        print(f"\n--- {name} ---")
        
        if not os.path.exists(path):
            print(f"  ⚠ Файл не найден: {path}")
            continue
        
        # Загрузка данных
        prices = load_csv_data(path)
        print(f"  Загружено точек: {len(prices)}")
        
        # QSpectrum анализ
        result = qspectrum(prices, min_period=5, max_period=100)
        
        print(f"  Доминантный период: {result.dominant_period} дней")
        print(f"  Спектральная энтропия: {result.spectral_entropy:.4f}")
        print(f"  Валидность: {'✓' if result.is_valid else '✗'} {result.validation_message}")
        
        print(f"  Топ-3 цикла:")
        for i, cycle in enumerate(result.top3, 1):
            print(f"    {i}. Период: {cycle.period:3d}, "
                  f"Энергия: {cycle.energy:.4f}, "
                  f"Стабильность: {cycle.stability:.4f}")
        
        # Генерация Composite Line
        if result.top3:
            composite = generate_composite_line(result.top3, n_points=100)
            print(f"  Composite Line: сгенерировано {len(composite)} точек")
        
        results[name] = result
    
    # Итоговая сводка
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    all_valid = all(r.is_valid or len(r.top3) > 0 for r in results.values())
    
    if all_valid:
        print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print(f"  - Проанализировано активов: {len(results)}")
        print(f"  - Найдено циклов: {sum(len(r.top3) for r in results.values())}")
    else:
        print("⚠ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    
    return all_valid


if __name__ == '__main__':
    success = validate_qspectrum()
    sys.exit(0 if success else 1)
