#!/usr/bin/env python3
"""
CLI for Decennial Pattern Analysis.

Reads JSON input from stdin, outputs JSON result to stdout.

Input format:
{
    "prices": [float, ...],
    "years": [int, ...],
    "current_year": int,
    "instrument_type": "tradfi" | "crypto"
}
"""

import sys
import json
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quant.seasonality.decennial import analyze_decennial, DecennialConfig


def main():
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        prices = np.array(input_data.get('prices', []))
        years = np.array(input_data.get('years', []))
        current_year = input_data.get('current_year')
        instrument_type = input_data.get('instrument_type', 'tradfi')
        
        if len(prices) == 0:
            result = {
                'status': 'insufficient_data',
                'digit_stats': {},
                'current_digit': (current_year or 2024) % 10,
                'current_year': current_year or 2024,
                'most_similar_digit': None,
                'similarity_score': 0.0,
                'projected_trend': None,
                'message': 'No price data provided',
                'years_analyzed': 0,
                'data_completeness': 0.0
            }
            print(json.dumps(result))
            return
        
        # Run analysis
        analysis = analyze_decennial(
            prices=prices,
            years=years,
            config=DecennialConfig(),
            current_year=current_year,
            instrument_type=instrument_type
        )
        
        # Convert to dict for JSON serialization
        result = {
            'status': analysis.status.value,
            'digit_stats': {
                str(digit): {
                    'digit': stats.digit,
                    'years': stats.years,
                    'avg_return': stats.avg_return,
                    'std_return': stats.std_return,
                    'win_rate': stats.win_rate,
                    'normalized_score': stats.normalized_score,
                    'sample_count': stats.sample_count,
                    'confidence': stats.confidence
                }
                for digit, stats in analysis.digit_stats.items()
            },
            'current_digit': analysis.current_digit,
            'current_year': analysis.current_year,
            'most_similar_digit': analysis.most_similar_digit,
            'similarity_score': analysis.similarity_score,
            'projected_trend': analysis.projected_trend,
            'message': analysis.message,
            'years_analyzed': analysis.years_analyzed,
            'data_completeness': analysis.data_completeness
        }
        
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            'status': 'error',
            'message': str(e),
            'digit_stats': {},
            'current_digit': 0,
            'current_year': 2024,
            'most_similar_digit': None,
            'similarity_score': 0.0,
            'projected_trend': None,
            'years_analyzed': 0,
            'data_completeness': 0.0
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()
