"""
scripts/export_power_bi_data.py
-------------------------------
Utility script that queries the SQLite database and exports the latest
flagged anomalies to CSV and JSON formats for offline Power BI or Excel exploration.

Usage:
    python scripts/export_power_bi_data.py [--format csv|json|both]
"""

import argparse
import json
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import DATABASE_PATH, BASE_DIR
from src.database import get_db_connection


def main():
    parser = argparse.ArgumentParser(description="Export flagged anomalies for offline Power BI/Excel consumption.")
    parser.add_argument("--format", default="both", choices=["csv", "json", "both"], help="Export format")
    parser.add_argument("--outdir", default=str(BASE_DIR), help="Output directory")
    args = parser.parse_args()

    if not os.path.exists(DATABASE_PATH):
        print(f"[ERROR] Database file not found at: {DATABASE_PATH}")
        print("Please run ETL or POST /analyze first.")
        sys.exit(1)

    conn = get_db_connection(DATABASE_PATH)
    df = pd.read_sql_query("SELECT * FROM anomalies ORDER BY risk_score DESC, amount_usd DESC;", conn)
    conn.close()

    if df.empty:
        print("[WARNING] Anomalies table is empty. Please run ETL and Risk Engine first.")
        sys.exit(0)

    csv_path = os.path.join(args.outdir, "powerbi_anomalies_export.csv")
    json_path = os.path.join(args.outdir, "powerbi_anomalies_export.json")

    if args.format in ("csv", "both"):
        df.to_csv(csv_path, index=False)
        print(f"[SUCCESS] Exported {len(df)} anomalies to CSV: {csv_path}")

    if args.format in ("json", "both"):
        df.to_json(json_path, orient="records", indent=2)
        print(f"[SUCCESS] Exported {len(df)} anomalies to JSON: {json_path}")

    print("\nSummary of Exported Risk Exposure:")
    print(f"  - Total Flagged Records: {len(df)}")
    print(f"  - Total Flagged Capital: ${df['amount_usd'].sum():,.2f}")
    print(f"  - Critical Alerts:       {len(df[df['severity_level'] == 'CRITICAL'])}")
    print(f"  - High Alerts:           {len(df[df['severity_level'] == 'HIGH'])}")


if __name__ == "__main__":
    main()
