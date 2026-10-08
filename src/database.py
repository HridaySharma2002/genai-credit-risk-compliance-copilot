"""
src/database.py
---------------
Database management and SQLite schema definitions with composite indexing.
"""

import sqlite3
from config.settings import DATABASE_PATH


def get_db_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    """Creates a sqlite3 connection with dictionary row access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DATABASE_PATH) -> None:
    """Initializes schema and performance indexes in SQLite."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Normalized Transactions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        client_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        amount_usd REAL NOT NULL,
        sender_account TEXT,
        receiver_account TEXT,
        location TEXT,
        destination_country TEXT,
        transaction_type TEXT,
        channel TEXT,
        unstructured_narrative TEXT
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_client_time ON transactions(client_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_amount ON transactions(amount_usd);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_location ON transactions(location, destination_country);")

    # Flagged Anomalies Table (Target for Power BI and Analytics)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anomalies (
        anomaly_id TEXT PRIMARY KEY,
        transaction_id TEXT NOT NULL,
        client_id TEXT NOT NULL,
        client_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        amount_usd REAL NOT NULL,
        location TEXT,
        destination_country TEXT,
        rule_flagged TEXT NOT NULL,
        severity_level TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        anomaly_description TEXT NOT NULL,
        detected_at TEXT NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anom_client ON anomalies(client_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anom_rule ON anomalies(rule_flagged);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anom_severity ON anomalies(severity_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anom_amount ON anomalies(amount_usd);")

    # Compliance Reports Archive Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        generated_at TEXT NOT NULL,
        total_anomalies INTEGER NOT NULL,
        total_volume_flagged REAL NOT NULL,
        report_markdown TEXT NOT NULL,
        model_used TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
