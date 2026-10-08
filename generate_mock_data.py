"""
generate_mock_data.py
---------------------
Root entry point to generate synthetic corporate transaction logs with
injected AML regulatory and credit risk anomalies.

Delegates execution to the modular generator engine at `src/generator.py`.

Usage:
    python generate_mock_data.py [--output transactions.csv] [--count 1500]
"""

import argparse
from config.settings import DEFAULT_CSV_PATH
from src.generator import generate_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic corporate transaction logs with AML risk anomalies.")
    parser.add_argument("--output", default=DEFAULT_CSV_PATH, help=f"Target CSV file path (default: {DEFAULT_CSV_PATH})")
    parser.add_argument("--count", type=int, default=1500, help="Number of records to generate (default: 1500)")
    args = parser.parse_args()

    generate_dataset(output_path=args.output, total_count=args.count)
