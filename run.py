"""
run.py
------
Master unified execution script for GenAI Credit Risk & Compliance Copilot.
Provides an interactive menu or command-line dispatch for all project workflows.

Usage:
    python run.py               (Interactive Menu)
    python run.py generate      (Generate mock transaction dataset)
    python run.py pipeline      (Run direct ETL and SQL Risk Engine)
    python run.py test          (Run automated integration test suite)
    python run.py server        (Start live FastAPI server with Uvicorn)
    python run.py export        (Export flagged anomalies for Power BI)
"""

import sys
import subprocess
import os

from config.settings import DEFAULT_CSV_PATH, HOST, PORT


def show_menu():
    print("\n" + "=" * 65)
    print(" GENAI CREDIT RISK & COMPLIANCE COPILOT - CONTROL CENTER")
    print("=" * 65)
    print(" 1. Generate Synthetic Transactions (1,500 records + anomalies)")
    print(" 2. Run Direct ETL Pipeline & Analytical SQL Risk Engine")
    print(" 3. Run Automated Integration Test Suite")
    print(" 4. Start Live FastAPI Web Server (Uvicorn)")
    print(" 5. Test Live CSV Upload via Client Script")
    print(" 6. Export Flagged Anomalies for Power BI (CSV & JSON)")
    print(" 7. Exit")
    print("=" * 65)
    choice = input("Enter choice [1-7]: ").strip()
    return choice


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None

    if arg == "generate" or (arg is None and False):
        subprocess.run([sys.executable, "generate_mock_data.py"])
    elif arg == "pipeline":
        subprocess.run([sys.executable, "scripts/run_etl_and_risk.py", "--with-ai"])
    elif arg == "test":
        subprocess.run([sys.executable, "test_pipeline.py"])
    elif arg == "server":
        print(f"Starting server on http://{HOST}:{PORT}...")
        subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", HOST, "--port", str(PORT), "--reload"])
    elif arg == "export":
        subprocess.run([sys.executable, "scripts/export_power_bi_data.py"])
    elif arg == "upload":
        subprocess.run([sys.executable, "scripts/client_test_upload.py"])
    else:
        while True:
            choice = show_menu()
            if choice == "1":
                subprocess.run([sys.executable, "generate_mock_data.py"])
            elif choice == "2":
                subprocess.run([sys.executable, "scripts/run_etl_and_risk.py", "--with-ai"])
            elif choice == "3":
                subprocess.run([sys.executable, "test_pipeline.py"])
            elif choice == "4":
                print(f"Starting server on http://{HOST}:{PORT} (Press Ctrl+C to stop)...")
                subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", HOST, "--port", str(PORT), "--reload"])
            elif choice == "5":
                subprocess.run([sys.executable, "scripts/client_test_upload.py"])
            elif choice == "6":
                subprocess.run([sys.executable, "scripts/export_power_bi_data.py"])
            elif choice == "7":
                print("Exiting Copilot Control Center. Goodbye!")
                break
            else:
                print("Invalid choice, please select between 1 and 7.")


if __name__ == "__main__":
    main()
