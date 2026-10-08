"""
src/risk_engine.py
------------------
SQL-based forensic risk engine executing analytical queries in SQLite
to detect threshold breaches, rolling velocity anomalies, offshore
jurisdiction exposures, and CTR structuring/smurfing patterns.
"""

from datetime import datetime
from typing import Dict, Any

from config.settings import DATABASE_PATH
from src.database import get_db_connection


def run_sql_risk_engine(db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """
    Executes analytical SQL queries to detect regulatory anomalies:
      - Rule 1: Threshold breaches (>= $1,000,000 USD)
      - Rule 2: Velocity anomalies (5+ transfers >= $200k in 7 days for same client)
      - Rule 3: High-risk offshore jurisdictions (>= $100k to tax havens)
      - Rule 4: CTR structuring / smurfing ($9k-$10k transfers in 72 hours)
    Populates 'anomalies' table and returns risk aggregates.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    detected_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Clear previous anomaly records before fresh evaluation
    cursor.execute("DELETE FROM anomalies;")

    # -------------------------------------------------------------------------
    # RULE 1: Threshold Breaches (>= $1,000,000 USD)
    # -------------------------------------------------------------------------
    cursor.execute("""
    INSERT OR REPLACE INTO anomalies (
        anomaly_id, transaction_id, client_id, client_name, timestamp,
        amount_usd, location, destination_country, rule_flagged,
        severity_level, risk_score, anomaly_description, detected_at
    )
    SELECT 
        'ANOM_' || transaction_id || '_THRESHOLD' AS anomaly_id,
        transaction_id,
        client_id,
        client_name,
        timestamp,
        amount_usd,
        location,
        destination_country,
        'THRESHOLD_BREACH_1M' AS rule_flagged,
        'CRITICAL' AS severity_level,
        CASE 
            WHEN amount_usd >= 5000000 THEN 99
            WHEN amount_usd >= 2000000 THEN 95
            ELSE 90 
        END AS risk_score,
        printf('Critical Single Threshold Breach: Transaction of $%.2f exceeds the $1,000,000 corporate monitoring threshold.', amount_usd) AS anomaly_description,
        ? AS detected_at
    FROM transactions
    WHERE amount_usd >= 1000000.0;
    """, (detected_at,))

    # -------------------------------------------------------------------------
    # RULE 2: Velocity Anomaly (5+ txns >= $200k in 7-day rolling window)
    # -------------------------------------------------------------------------
    cursor.execute("""
    WITH high_value AS (
        SELECT 
            transaction_id, client_id, client_name, timestamp, amount_usd,
            location, destination_country, julianday(timestamp) AS jd
        FROM transactions
        WHERE amount_usd >= 200000.0
    ),
    velocity_clusters AS (
        SELECT 
            t1.transaction_id,
            t1.client_id,
            t1.client_name,
            t1.timestamp,
            t1.amount_usd,
            t1.location,
            t1.destination_country,
            COUNT(t2.transaction_id) AS window_tx_count,
            SUM(t2.amount_usd) AS window_total_usd
        FROM high_value t1
        JOIN high_value t2 
          ON t1.client_id = t2.client_id 
         AND ABS(t1.jd - t2.jd) <= 7.0
        GROUP BY t1.transaction_id
        HAVING COUNT(t2.transaction_id) >= 5
    )
    INSERT OR REPLACE INTO anomalies (
        anomaly_id, transaction_id, client_id, client_name, timestamp,
        amount_usd, location, destination_country, rule_flagged,
        severity_level, risk_score, anomaly_description, detected_at
    )
    SELECT 
        'ANOM_' || transaction_id || '_VELOCITY' AS anomaly_id,
        transaction_id,
        client_id,
        client_name,
        timestamp,
        amount_usd,
        location,
        destination_country,
        'VELOCITY_OVER_200K_7DAYS' AS rule_flagged,
        'CRITICAL' AS severity_level,
        96 AS risk_score,
        printf('Velocity Anomaly: Client triggered %d high-value transfers (>= $200k) within a 7-day rolling window totaling $%.2f.', window_tx_count, window_total_usd) AS anomaly_description,
        ? AS detected_at
    FROM velocity_clusters;
    """, (detected_at,))

    # -------------------------------------------------------------------------
    # RULE 3: High-Risk Offshore Jurisdictions Exposure (>= $100k)
    # -------------------------------------------------------------------------
    cursor.execute("""
    INSERT OR REPLACE INTO anomalies (
        anomaly_id, transaction_id, client_id, client_name, timestamp,
        amount_usd, location, destination_country, rule_flagged,
        severity_level, risk_score, anomaly_description, detected_at
    )
    SELECT 
        'ANOM_' || transaction_id || '_OFFSHORE' AS anomaly_id,
        transaction_id,
        client_id,
        client_name,
        timestamp,
        amount_usd,
        location,
        destination_country,
        'OFFSHORE_JURISDICTION_EXPOSURE' AS rule_flagged,
        'HIGH' AS severity_level,
        CASE 
            WHEN amount_usd >= 500000 THEN 88
            WHEN amount_usd >= 250000 THEN 82
            ELSE 75 
        END AS risk_score,
        printf('Offshore Exposure: Transfer of $%.2f routed via unverified high-risk jurisdiction: %s -> %s.', amount_usd, location, destination_country) AS anomaly_description,
        ? AS detected_at
    FROM transactions
    WHERE (location IN ('Cayman Islands', 'Panama', 'Cyprus', 'Seychelles', 'British Virgin Islands', 'Vanuatu', 'Belize')
       OR destination_country IN ('Cayman Islands', 'Panama', 'Cyprus', 'Seychelles', 'British Virgin Islands', 'Vanuatu', 'Belize'))
      AND amount_usd >= 100000.0;
    """, (detected_at,))

    # -------------------------------------------------------------------------
    # RULE 4: CTR Structuring / Smurfing ($9,000 - $9,999.99 in 72 hrs)
    # -------------------------------------------------------------------------
    cursor.execute("""
    WITH struct_candidates AS (
        SELECT 
            transaction_id, client_id, client_name, timestamp, amount_usd,
            location, destination_country, julianday(timestamp) AS jd
        FROM transactions
        WHERE amount_usd >= 9000.0 AND amount_usd < 10000.0
    ),
    struct_clusters AS (
        SELECT 
            s1.transaction_id,
            s1.client_id,
            s1.client_name,
            s1.timestamp,
            s1.amount_usd,
            s1.location,
            s1.destination_country,
            COUNT(s2.transaction_id) AS cluster_count,
            SUM(s2.amount_usd) AS cluster_total_usd
        FROM struct_candidates s1
        JOIN struct_candidates s2 
          ON s1.client_id = s2.client_id 
         AND ABS(s1.jd - s2.jd) <= 3.0
        GROUP BY s1.transaction_id
        HAVING COUNT(s2.transaction_id) >= 3
    )
    INSERT OR REPLACE INTO anomalies (
        anomaly_id, transaction_id, client_id, client_name, timestamp,
        amount_usd, location, destination_country, rule_flagged,
        severity_level, risk_score, anomaly_description, detected_at
    )
    SELECT 
        'ANOM_' || transaction_id || '_STRUCTURING' AS anomaly_id,
        transaction_id,
        client_id,
        client_name,
        timestamp,
        amount_usd,
        location,
        destination_country,
        'STRUCTURING_SMURFING' AS rule_flagged,
        'HIGH' AS severity_level,
        86 AS risk_score,
        printf('Structuring Typology: %d repetitive transfers between $9,000-$10,000 within 72 hours totaling $%.2f evading CTR reporting.', cluster_count, cluster_total_usd) AS anomaly_description,
        ? AS detected_at
    FROM struct_clusters;
    """, (detected_at,))

    conn.commit()

    # Aggregate Risk Engine Metrics
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT client_id), COALESCE(SUM(amount_usd), 0.0) FROM anomalies;")
    total_anomalies, unique_clients, total_flagged_volume = cursor.fetchone()

    cursor.execute("SELECT rule_flagged, COUNT(*), SUM(amount_usd) FROM anomalies GROUP BY rule_flagged;")
    rule_breakdown = {row[0]: {"count": row[1], "volume_usd": round(row[2], 2)} for row in cursor.fetchall()}

    cursor.execute("SELECT severity_level, COUNT(*) FROM anomalies GROUP BY severity_level;")
    severity_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("""
    SELECT client_id, client_name, COUNT(*) as anomaly_count, SUM(amount_usd) as total_volume
    FROM anomalies
    GROUP BY client_id, client_name
    ORDER BY total_volume DESC
    LIMIT 5;
    """)
    top_risky_clients = [
        {"client_id": r[0], "client_name": r[1], "anomaly_count": r[2], "total_volume_usd": round(r[3], 2)}
        for r in cursor.fetchall()
    ]

    conn.close()

    return {
        "total_anomalies": total_anomalies,
        "unique_flagged_clients": unique_clients,
        "total_flagged_volume_usd": round(total_flagged_volume, 2),
        "rule_breakdown": rule_breakdown,
        "severity_breakdown": severity_breakdown,
        "top_risky_clients": top_risky_clients
    }
