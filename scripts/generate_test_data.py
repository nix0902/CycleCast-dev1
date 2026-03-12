#!/usr/bin/env python3
"""
CycleCast Test Data Generator Script
=====================================
Generates synthetic market data with embedded cycles for algorithm validation.

Usage:
    python scripts/generate_test_data.py [--years N] [--output-dir PATH]

Embedded Cycles:
    - 14-day cycle (short-term)
    - 42-day cycle (medium-term)
    - 98-day cycle (long-term)
    - Annual seasonality pattern

Output Files:
    - tests/fixtures/sp500.csv (15 years default)
    - tests/fixtures/gold.csv (15 years default)
    - tests/fixtures/btc.csv (10 years default)
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# Configuration
SEED = 42
np.random.seed(SEED)

# Default parameters per asset
ASSET_CONFIG = {
    "sp500": {
        "symbol": "SP500",
        "start_date": "2010-01-01",
        "base_price": 1100.0,
        "annual_growth": 0.12,
        "volatility": 0.015,
        "cycles": {14: 15, 42: 30, 98: 50},
        "base_volume": 1e8,
        "years": 15,
    },
    "gold": {
        "symbol": "GOLD",
        "start_date": "2010-01-01",
        "base_price": 1100.0,
        "annual_growth": 0.03,
        "volatility": 0.02,
        "cycles": {14: 8, 42: 15, 98: 25},
        "base_volume": 5e7,
        "years": 15,
    },
    "btc": {
        "symbol": "BTC-USD",
        "start_date": "2015-01-01",
        "base_price": 300.0,
        "annual_growth": 0.80,
        "volatility": 0.05,
        "cycles": {14: 500, 42: 1500, 98: 3000},
        "base_volume": 1e9,
        "years": 10,
    },
}


def generate_ohlcv_series(
    start_date: str,
    end_date: str,
    base_price: float,
    annual_growth: float,
    volatility: float,
    cycles: dict,
    base_volume: float,
) -> list[dict]:
    """
    Generate realistic OHLCV time series with embedded cycles.

    Args:
        start_date: Start date (ISO format YYYY-MM-DD)
        end_date: End date (ISO format YYYY-MM-DD)
        base_price: Starting price level
        annual_growth: Expected annual return (decimal)
        volatility: Daily volatility (decimal)
        cycles: Dict mapping period_days -> amplitude
        base_volume: Typical daily volume

    Returns:
        List of OHLCV records as dicts
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    days = (end - start).days

    t = np.arange(days)

    # Base exponential trend
    daily_growth = np.log(1 + annual_growth) / 252
    trend = base_price * np.exp(daily_growth * t)

    # Add cyclical components
    cycle_component = np.zeros(days)
    for period, amplitude in cycles.items():
        cycle_component += amplitude * np.sin(2 * np.pi * t / period)

    # Annual seasonality (stronger in Q4 for equities)
    seasonal = 0.02 * base_price * np.sin(2 * np.pi * t / 365 - np.pi / 4)

    # Random noise (Gaussian)
    noise = np.random.randn(days) * volatility * base_price

    # Combine components
    close = trend + cycle_component + seasonal + noise
    close = np.maximum(close, base_price * 0.1)  # Floor at 10% of base

    # Generate OHLCV records
    records = []
    for i in range(days):
        date = start + timedelta(days=i)
        c = close[i]

        # Generate realistic OHLC relationships
        daily_range = volatility * c * abs(np.random.randn()) * 2
        high = c + daily_range * np.random.rand()
        low = c - daily_range * np.random.rand()
        open_price = low + (high - low) * np.random.rand()

        # Ensure OHLC consistency
        high = max(high, open_price, c)
        low = min(low, open_price, c)

        # Volume (log-normal distribution)
        volume = int(base_volume * np.exp(np.random.randn() * 0.5))

        records.append(
            {
                "time": date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(c, 2),
                "volume": max(volume, int(base_volume * 0.1)),
            }
        )

    return records


def save_csv(records: list[dict], filepath: str) -> int:
    """Save records to CSV file. Returns number of records written."""
    if not records:
        return 0

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    return len(records)


def generate_asset_data(asset_key: str, output_dir: str) -> tuple[str, int]:
    """Generate data for a single asset. Returns (filepath, record_count)."""
    config = ASSET_CONFIG[asset_key]

    # Calculate end date
    start = datetime.strptime(config["start_date"], "%Y-%m-%d")
    end = start + timedelta(days=config["years"] * 365)

    print(f"  Generating {config['symbol']} ({config['years']} years)...")

    records = generate_ohlcv_series(
        start_date=config["start_date"],
        end_date=end.strftime("%Y-%m-%d"),
        base_price=config["base_price"],
        annual_growth=config["annual_growth"],
        volatility=config["volatility"],
        cycles=config["cycles"],
        base_volume=config["base_volume"],
    )

    filepath = os.path.join(output_dir, f"{asset_key}.csv")
    count = save_csv(records, filepath)

    return filepath, count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="CycleCast Test Data Generator")
    parser.add_argument(
        "--years", type=int, default=None, help="Override default years for all assets"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/fixtures",
        help="Output directory for CSV files",
    )
    parser.add_argument(
        "--assets",
        type=str,
        default="sp500,gold,btc",
        help="Comma-separated list of assets to generate",
    )

    args = parser.parse_args()
    output_dir = args.output_dir

    print("=" * 60)
    print("CycleCast Test Data Generator v3.2")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print()

    assets = [a.strip() for a in args.assets.split(",")]
    results = {}

    for asset_key in assets:
        if asset_key not in ASSET_CONFIG:
            print(f"⚠ Unknown asset: {asset_key}, skipping...")
            continue

        # Override years if specified
        if args.years:
            ASSET_CONFIG[asset_key]["years"] = args.years

        filepath, count = generate_asset_data(asset_key, output_dir)
        results[asset_key] = {"filepath": filepath, "count": count}
        print(f"  ✓ {filepath}: {count:,} records")

    print()
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    for asset_key, result in results.items():
        print(f"  {asset_key:8s}: {result['count']:>7,} records → {result['filepath']}")

    total = sum(r["count"] for r in results.values())
    print(f"\n  Total: {total:,} records generated")
    print("\nEmbedded cycles: 14-day, 42-day, 98-day, Annual")
    print("Ready for QSpectrum, DTW, and Annual Cycle validation.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
