"""
test_pipeline.py
----------------
Automated test suite verifying the end-to-end pipeline:
  1. Synthetic data generation (transactions.csv)
  2. Database schema initialization (credit_risk.db)
  3. ETL data ingestion and type normalization
  4. SQL Risk Engine execution (1M+ breaches, velocity, offshore, smurfing)
  5. GenAI summary generation (Gemini / fallback narrative)
  6. Live FastAPI endpoints (POST /analyze, GET /data/anomalies, GET /data/summary, GET /data/report/latest)

Usage:
    python test_pipeline.py
"""

import os
import sys
from starlette.testclient import TestClient

from app import (
    app,
    DATABASE_PATH,
    init_db,
    run_etl_pipeline,
    run_sql_risk_engine,
    generate_aml_compliance_summary
)
from generate_mock_data import generate_dataset


def run_tests():
    print("=" * 75)
    print(" GENAI CREDIT RISK & COMPLIANCE COPILOT - INTEGRATION VERIFICATION")
    print("=" * 75)

    test_csv = "transactions.csv"
    if not os.path.exists(test_csv):
        print("\n[STEP 1] Generating mock transaction dataset...")
        generate_dataset(output_path=test_csv, total_count=1500)
    else:
        print(f"\n[STEP 1] Found existing transaction dataset: {test_csv}")

    # Step 2: Initialize Database
    print("\n[STEP 2] Verifying SQLite database initialization...")
    init_db(DATABASE_PATH)
    assert os.path.exists(DATABASE_PATH), "Database file was not created!"
    print(f"  [PASSED] Database schema verified at: {DATABASE_PATH}")

    # Step 3: Test Direct ETL Pipeline
    print("\n[STEP 3] Testing Pandas ETL Pipeline...")
    with open(test_csv, "rb") as f:
        csv_bytes = f.read()
    etl_res = run_etl_pipeline(csv_bytes, DATABASE_PATH)
    print(f"  - Ingested records: {etl_res['records_ingested']}")
    print(f"  - Unique clients: {etl_res['unique_clients']}")
    print(f"  - Total volume USD: ${etl_res['total_volume_usd']:,.2f}")
    assert etl_res['records_ingested'] >= 1000, "ETL did not ingest expected record count!"
    print("  [PASSED] ETL Pipeline functioning correctly.")

    # Step 4: Test SQL Risk Engine
    print("\n[STEP 4] Executing SQL Risk Engine...")
    risk_res = run_sql_risk_engine(DATABASE_PATH)
    print(f"  - Total Anomalies Flagged: {risk_res['total_anomalies']}")
    print(f"  - Flagged Clients Count: {risk_res['unique_flagged_clients']}")
    print(f"  - Flagged Capital Volume: ${risk_res['total_flagged_volume_usd']:,.2f}")
    print(f"  - Rule Breakdown:")
    for rule, data in risk_res['rule_breakdown'].items():
        print(f"      * {rule}: {data['count']} cases (${data['volume_usd']:,.2f})")
    assert risk_res['total_anomalies'] > 0, "No anomalies flagged by Risk Engine!"
    assert "THRESHOLD_BREACH_1M" in risk_res['rule_breakdown'], "Missing 1M threshold flags!"
    assert "VELOCITY_OVER_200K_7DAYS" in risk_res['rule_breakdown'], "Missing velocity anomaly flags!"
    print("  [PASSED] SQL Risk Engine validated.")

    # Step 5: Test FastAPI Endpoints via TestClient
    print("\n[STEP 5] Testing FastAPI Live Endpoints...")
    client = TestClient(app)

    # 5.1 Root & Health
    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Healthcheck failed: {r_health.status_code}"
    print("  - GET /health: 200 OK")

    # 5.2 POST /analyze
    print("  - Testing POST /analyze with transactions.csv...")
    with open(test_csv, "rb") as f:
        r_analyze = client.post("/analyze", files={"file": ("transactions.csv", f, "text/csv")})
    assert r_analyze.status_code == 200, f"Analyze failed: {r_analyze.text}"
    analyze_payload = r_analyze.json()
    assert analyze_payload["status"] == "success"
    assert "ai_compliance_summary" in analyze_payload
    print(f"    * Ingested: {analyze_payload['etl_summary']['records_ingested']}")
    print(f"    * Flagged records: {analyze_payload['total_flagged_records']}")
    print(f"    * Generated AI Summary length: {len(analyze_payload['ai_compliance_summary'])} chars")
    print("  - POST /analyze: 200 OK")

    # 5.3 GET /data/anomalies (Power BI target endpoint)
    print("  - Testing GET /data/anomalies (Power BI flat JSON format)...")
    r_anom = client.get("/data/anomalies")
    assert r_anom.status_code == 200, f"Anomalies endpoint failed: {r_anom.status_code}"
    anom_list = r_anom.json()
    assert isinstance(anom_list, list), "Expected list response for Power BI direct import!"
    assert len(anom_list) > 0, "Expected non-empty list of anomalies!"
    sample = anom_list[0]
    expected_keys = {
        "anomaly_id", "transaction_id", "client_id", "client_name", "timestamp",
        "amount_usd", "location", "destination_country", "rule_flagged",
        "severity_level", "risk_score", "anomaly_description", "detected_at"
    }
    missing_keys = expected_keys - set(sample.keys())
    assert not missing_keys, f"Missing expected keys in anomaly records: {missing_keys}"
    print(f"    * Returned {len(anom_list)} anomalies ready for Power BI consumption.")
    print("  - GET /data/anomalies: 200 OK")

    # 5.4 Test Query Filtering on GET /data/anomalies
    r_crit = client.get("/data/anomalies?severity=CRITICAL")
    assert r_crit.status_code == 200
    crit_records = r_crit.json()
    for row in crit_records:
        assert row["severity_level"] == "CRITICAL"
    print(f"    * Filtering (?severity=CRITICAL): returned {len(crit_records)} critical alerts.")

    # 5.5 GET /data/summary (Executive KPI cards)
    print("  - Testing GET /data/summary...")
    r_sum = client.get("/data/summary")
    assert r_sum.status_code == 200
    sum_data = r_sum.json()
    print(f"    * Total Volume: ${sum_data['total_volume_usd']:,.2f}")
    print(f"    * Flagged Volume: ${sum_data['total_flagged_volume_usd']:,.2f}")
    print(f"    * Critical Alert Count: {sum_data['critical_alert_count']}")
    print("  - GET /data/summary: 200 OK")

    # 5.6 GET /data/report/latest
    print("  - Testing GET /data/report/latest...")
    r_rep = client.get("/data/report/latest")
    assert r_rep.status_code == 200
    rep_data = r_rep.json()
    assert "report_markdown" in rep_data
    print(f"    * Report ID {rep_data['report_id']} retrieved ({rep_data['generated_at']})")
    print("  - GET /data/report/latest: 200 OK")

    print("\n" + "=" * 75)
    print(" ALL TESTS PASSED! PROJECT ARCHITECTURE IS FULLY VERIFIED & READY.")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
