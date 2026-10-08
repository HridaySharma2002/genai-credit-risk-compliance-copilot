"""
app.py
------
FastAPI Application for GenAI Credit Risk & Compliance Copilot (Data Analyst Focus).

Architecture Components:
  1. ETL Pipeline (src.etl): Ingests uploaded corporate transaction CSVs, strictly types
     and sanitizes all fields, and commits normalized records to SQLite.
  2. SQL Risk Engine (src.risk_engine): Executes analytical SQL queries to detect regulatory threshold
     breaches (>= $1M), velocity anomalies (5+ transactions >= $200k in 7 days),
     high-risk offshore jurisdiction exposure, and CTR structuring/smurfing.
  3. GenAI Integration (src.gemini_copilot): Translates flagged anomalies into an executive-grade
     AML compliance and Suspicious Activity Report (SAR) narrative using Google Gemini.
  4. Live Endpoints:
     - POST /analyze: Complete end-to-end processing of uploaded CSV data.
     - GET /data/anomalies: Live endpoint formatted specifically for Power BI consumption.
     - GET /data/summary: High-level KPI aggregations for Power BI executive cards.
     - GET /data/report/latest: Retrieves the latest generated GenAI compliance narrative.
     - GET /health: Healthcheck and diagnostic metadata.

Run with:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# Centralized Configuration & Modular Source Components
from config.settings import DATABASE_PATH, GEMINI_API_KEY, GEMINI_MODEL, HOST, PORT, DEBUG
from src.database import get_db_connection, init_db
from src.etl import run_etl_pipeline
from src.risk_engine import run_sql_risk_engine
from src.gemini_copilot import generate_aml_compliance_summary


# =============================================================================
# APPLICATION LIFECYCLE & INITIALIZATION
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema and indexes are initialized on startup."""
    init_db(DATABASE_PATH)
    yield


app = FastAPI(
    title="GenAI Credit Risk & Compliance Copilot",
    description="Automated real-time interpretation of corporate credit risk profiles, velocity spikes, and AML anomalies.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin dashboarding tools (e.g. web dashboards, local frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database is initialized immediately upon import
init_db(DATABASE_PATH)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
def root():
    """Interactive Landing Page with API Overview & Quick Navigation."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GenAI Credit Risk & Compliance Copilot</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }
            .container { max-width: 900px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; margin-top: 0; }
            h2 { color: #94a3b8; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 24px; }
            code { background: #334155; padding: 2px 6px; border-radius: 4px; color: #f472b6; font-size: 0.9em; }
            .badge { display: inline-block; padding: 4px 10px; border-radius: 16px; font-size: 12px; font-weight: 600; background: #0284c7; color: white; margin-right: 8px; }
            a { color: #38bdf8; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .endpoint-card { background: #0f172a; padding: 16px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #38bdf8; }
        </style>
    </head>
    <body>
        <div class="container">
            <span class="badge">PRODUCTION READY</span>
            <span class="badge" style="background:#10b981;">DATA ANALYST COPILOT</span>
            <h1>GenAI Credit Risk & Compliance Copilot</h1>
            <p>Automated real-time interpretation of high-risk credit profiles, velocity spikes, and regulatory AML anomalies bridging transactional data with executive dashboards.</p>
            
            <h2>Interactive Endpoints</h2>
            <div class="endpoint-card">
                <strong>POST <code>/analyze</code></strong>
                <p>Accepts a CSV transaction file, executes the Pandas ETL pipeline, runs the SQL Risk Engine, synthesizes Gemini AML narratives, and returns full JSON analysis.</p>
            </div>
            <div class="endpoint-card">
                <strong>GET <code>/data/anomalies</code></strong>
                <p>Live REST endpoint formatted specifically for <strong>Power BI Web Connector</strong> to build interactive executive dashboards.</p>
            </div>
            <div class="endpoint-card">
                <strong>GET <code>/data/summary</code></strong>
                <p>Key risk performance indicators (KPIs) for executive cards (Total Flagged Volume, Critical Alerts, Riskiest Entities).</p>
            </div>
            <div class="endpoint-card">
                <strong>GET <code>/data/report/latest</code></strong>
                <p>Returns the latest synthesized GenAI AML Compliance Briefing.</p>
            </div>

            <h2>Documentation & Testing</h2>
            <p>Explore interactive Swagger UI: <a href="/docs" target="_blank"><strong>/docs</strong></a> or ReDoc: <a href="/redoc" target="_blank"><strong>/redoc</strong></a></p>
        </div>
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    """System health check and database statistics."""
    try:
        conn = get_db_connection()
        txn_count = conn.execute("SELECT COUNT(*) FROM transactions;").fetchone()[0]
        anom_count = conn.execute("SELECT COUNT(*) FROM anomalies;").fetchone()[0]
        conn.close()
        db_status = "connected"
    except Exception as e:
        txn_count, anom_count = 0, 0
        db_status = f"error: {str(e)}"

    has_gemini_key = bool(GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY")

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": db_status,
            "total_transactions": txn_count,
            "total_flagged_anomalies": anom_count
        },
        "gemini_api_configured": has_gemini_key,
        "gemini_model": GEMINI_MODEL
    }


@app.post("/analyze")
async def analyze_transactions(file: UploadFile = File(...)):
    """
    Core Pipeline Endpoint:
      1. Ingests uploaded CSV transaction log via Pandas ETL.
      2. Writes normalized records into SQLite.
      3. Executes SQL Risk Engine (1M+ breach, 5+ txns >200k/7d velocity, offshore, smurfing).
      4. Pipes flagged anomalies into Google Gemini API to generate executive AML compliance narrative.
      5. Returns full JSON response with metrics and AI summary.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a standard CSV file."
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file content: {str(e)}")

    # 1. Run ETL Pipeline
    try:
        etl_metrics = run_etl_pipeline(content, DATABASE_PATH)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ETL Pipeline Error: {str(e)}")

    # 2. Run SQL Risk Engine
    try:
        risk_metrics = run_sql_risk_engine(DATABASE_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk Engine Error: {str(e)}")

    # 3. Retrieve Flagged Anomalies
    conn = get_db_connection(DATABASE_PATH)
    anomalies_rows = conn.execute("SELECT * FROM anomalies ORDER BY risk_score DESC, amount_usd DESC;").fetchall()
    anomalies = [dict(row) for row in anomalies_rows]
    conn.close()

    # 4. Generate GenAI Executive Compliance Narrative
    ai_summary = generate_aml_compliance_summary(anomalies, risk_metrics, DATABASE_PATH)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "filename": file.filename,
            "processed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "etl_summary": etl_metrics,
            "risk_engine_metrics": risk_metrics,
            "ai_compliance_summary": ai_summary,
            "total_flagged_records": len(anomalies),
            "flagged_records_sample": anomalies[:25]
        }
    )


@app.get("/data/anomalies")
def get_anomalies_for_power_bi(
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM)"),
    rule: Optional[str] = Query(None, description="Filter by rule flagged"),
    min_amount: Optional[float] = Query(None, description="Filter minimum transaction amount"),
    limit: int = Query(1000, description="Maximum number of rows to return")
):
    """
    Live Data Endpoint designed specifically for Power BI Web Connector.
    Returns a direct flat JSON array of typed anomaly records so Power BI
    can immediately expand and visualize columns without complex transformation.
    """
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()

    query = "SELECT * FROM anomalies WHERE 1=1"
    params = []

    if severity:
        query += " AND severity_level = ?"
        params.append(severity.upper())
    if rule:
        query += " AND rule_flagged = ?"
        params.append(rule)
    if min_amount is not None:
        query += " AND amount_usd >= ?"
        params.append(min_amount)

    query += " ORDER BY risk_score DESC, amount_usd DESC LIMIT ?"
    params.append(limit)

    rows = cursor.execute(query, params).fetchall()
    results = [dict(row) for row in rows]
    conn.close()

    return results


@app.get("/data/summary")
def get_dashboard_summary():
    """High-level aggregated metrics for Power BI KPI Cards and Executive Widgets."""
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transactions;")
    total_txns = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount_usd), 0.0) FROM transactions;")
    total_txn_volume = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM anomalies;")
    total_anomalies = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount_usd), 0.0) FROM anomalies;")
    total_flagged_volume = cursor.fetchone()[0]

    cursor.execute("SELECT severity_level, COUNT(*) FROM anomalies GROUP BY severity_level;")
    severity_counts = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT rule_flagged, COUNT(*), SUM(amount_usd) FROM anomalies GROUP BY rule_flagged;")
    rule_counts = {r[0]: {"count": r[1], "volume_usd": round(r[2], 2)} for r in cursor.fetchall()}

    cursor.execute("""
    SELECT client_id, client_name, COUNT(*) as flags, SUM(amount_usd) as volume
    FROM anomalies
    GROUP BY client_id, client_name
    ORDER BY volume DESC
    LIMIT 10;
    """)
    top_clients = [
        {"client_id": r[0], "client_name": r[1], "flags": r[2], "flagged_volume_usd": round(r[3], 2)}
        for r in cursor.fetchall()
    ]

    conn.close()

    return {
        "total_transactions_scanned": total_txns,
        "total_volume_usd": round(total_txn_volume, 2),
        "total_anomalies_flagged": total_anomalies,
        "total_flagged_volume_usd": round(total_flagged_volume, 2),
        "critical_alert_count": severity_counts.get("CRITICAL", 0),
        "high_alert_count": severity_counts.get("HIGH", 0),
        "severity_distribution": severity_counts,
        "rule_distribution": rule_counts,
        "top_high_risk_clients": top_clients
    }


@app.get("/data/report/latest")
def get_latest_compliance_report():
    """Fetches the latest GenAI compliance narrative report."""
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    row = cursor.execute("""
    SELECT report_id, generated_at, total_anomalies, total_volume_flagged, report_markdown, model_used
    FROM compliance_reports
    ORDER BY report_id DESC
    LIMIT 1;
    """).fetchone()
    conn.close()

    if not row:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "No compliance reports found. Please execute POST /analyze first."}
        )

    return dict(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=DEBUG)
