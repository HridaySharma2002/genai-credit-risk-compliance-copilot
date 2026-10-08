"""
scripts/client_test_upload.py
-----------------------------
Client script to upload a CSV file to the running FastAPI server endpoint
POST /analyze or verify GET /data/anomalies.

Usage:
    python scripts/client_test_upload.py [--url http://localhost:8000] [--csv transactions.csv]
"""

import argparse
import json
import os
import sys
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import DEFAULT_CSV_PATH


def main():
    parser = argparse.ArgumentParser(description="Upload transaction CSV to FastAPI /analyze endpoint.")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of FastAPI server")
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="Path to CSV file to upload")
    args = parser.parse_args()

    analyze_url = f"{args.url.rstrip('/')}/analyze"
    anomalies_url = f"{args.url.rstrip('/')}/data/anomalies"

    if not os.path.exists(args.csv):
        print(f"[ERROR] File not found: {args.csv}")
        sys.exit(1)

    print("=" * 70)
    print(f" SENDING CSV TO LIVE COPILOT ENDPOINT: {analyze_url}")
    print("=" * 70)

    try:
        with open(args.csv, "rb") as f:
            files = {"file": (os.path.basename(args.csv), f, "text/csv")}
            response = requests.post(analyze_url, files=files, timeout=60)
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Could not connect to {args.url}.")
        print("Make sure the FastAPI server is running with: uvicorn app:app --reload")
        sys.exit(1)

    if response.status_code != 200:
        print(f"[ERROR] Server returned status code {response.status_code}:")
        print(response.text)
        sys.exit(1)

    data = response.json()
    print("\n[SUCCESS] Response received from Copilot:")
    print(f"  - Status:              {data['status']}")
    print(f"  - Records Ingested:    {data['etl_summary']['records_ingested']}")
    print(f"  - Total Flagged Vol:   ${data['risk_engine_metrics']['total_flagged_volume_usd']:,.2f}")
    print(f"  - Total Anomalies:     {data['risk_engine_metrics']['total_anomalies']}")

    print("\n  Rule Breakdown:")
    for rule, info in data['risk_engine_metrics']['rule_breakdown'].items():
        print(f"    * {rule:32}: {info['count']:2d} flags (${info['volume_usd']:>12,.2f})")

    print("\n" + "=" * 70)
    print(" AI COMPLIANCE REPORT PREVIEW:")
    print("=" * 70)
    print(data.get("ai_compliance_summary", "")[:1200] + "\n...[truncated for display]...")

    # Now verify GET /data/anomalies
    print("\n" + "=" * 70)
    print(f" VERIFYING LIVE POWER BI ENDPOINT: {anomalies_url}")
    print("=" * 70)
    anom_res = requests.get(anomalies_url)
    if anom_res.status_code == 200:
        anom_list = anom_res.json()
        print(f"  [PASSED] GET /data/anomalies returned {len(anom_list)} formatted rows for Power BI.")
        if anom_list:
            print("  Sample row columns:", list(anom_list[0].keys()))
    else:
        print(f"  [FAILED] GET /data/anomalies returned {anom_res.status_code}")


if __name__ == "__main__":
    main()
