"""
scripts/run_etl_and_risk.py
---------------------------
Direct CLI tool to run the ETL Pipeline and SQL Risk Engine on a CSV file
without having to run the web server.

Usage:
    python scripts/run_etl_and_risk.py [--csv transactions.csv]
"""

import argparse
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import DEFAULT_CSV_PATH, DATABASE_PATH
from src.database import init_db
from src.etl import run_etl_pipeline
from src.risk_engine import run_sql_risk_engine
from src.gemini_copilot import generate_aml_compliance_summary
from src.database import get_db_connection


def main():
    parser = argparse.ArgumentParser(description="Run ETL and SQL Risk Engine directly on transaction CSV.")
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help=f"Path to input CSV (default: {DEFAULT_CSV_PATH})")
    parser.add_argument("--with-ai", action="store_true", help="Also generate Gemini AML compliance narrative")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[ERROR] CSV file not found at: {args.csv}")
        print("Run 'python generate_mock_data.py' first to create it.")
        sys.exit(1)

    print("=" * 70)
    print(" GENAI CREDIT RISK & COMPLIANCE COPILOT - DIRECT PIPELINE EXECUTION")
    print("=" * 70)

    # 1. Initialize SQLite Database
    print(f"\n[1/3] Initializing SQLite database at: {DATABASE_PATH}")
    init_db(DATABASE_PATH)

    # 2. Ingest CSV via Pandas ETL
    print(f"\n[2/3] Ingesting and strictly typing: {args.csv}")
    with open(args.csv, "rb") as f:
        content = f.read()
    etl_stats = run_etl_pipeline(content, DATABASE_PATH)
    print(f"  - Ingested Records: {etl_stats['records_ingested']}")
    print(f"  - Unique Clients:   {etl_stats['unique_clients']}")
    print(f"  - Total Volume USD: ${etl_stats['total_volume_usd']:,.2f}")
    print(f"  - Date Range:       {etl_stats['min_timestamp']} to {etl_stats['max_timestamp']}")

    # 3. Execute SQL Risk Engine
    print("\n[3/3] Executing Analytical SQL Risk Engine...")
    risk_stats = run_sql_risk_engine(DATABASE_PATH)
    print(f"  - Total Anomalies Flagged: {risk_stats['total_anomalies']}")
    print(f"  - High-Risk Entities:      {risk_stats['unique_flagged_clients']}")
    print(f"  - Flagged Exposure Volume: ${risk_stats['total_flagged_volume_usd']:,.2f}")
    print("\n  Breaches by Regulatory Typology:")
    for rule, data in risk_stats['rule_breakdown'].items():
        print(f"    * {rule:32}: {data['count']:2d} flags (${data['volume_usd']:>12,.2f})")

    print("\n  Top High-Risk Corporate Profiles:")
    for client in risk_stats['top_risky_clients']:
        print(f"    * {client['client_name']} ({client['client_id']}): {client['anomaly_count']} flags | ${client['total_volume_usd']:,.2f}")

    if args.with_ai:
        print("\n[BONUS] Generating Executive AML Compliance Briefing with Copilot...")
        conn = get_db_connection(DATABASE_PATH)
        anomalies = [dict(r) for r in conn.execute("SELECT * FROM anomalies ORDER BY risk_score DESC;").fetchall()]
        conn.close()
        report = generate_aml_compliance_summary(anomalies, risk_stats, DATABASE_PATH)
        print("\n" + report)

    print("\n" + "=" * 70)
    print(" PIPELINE COMPLETED SUCCESSFULLY! Data is stored in SQLite.")
    print("=" * 70)


if __name__ == "__main__":
    main()
