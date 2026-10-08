"""
src/etl.py
----------
Pandas-powered ETL pipeline for ingesting, validating, strictly typing,
and persisting corporate transaction data into SQLite.
"""

import io
from typing import Dict, Any, Union
import pandas as pd

from config.settings import DATABASE_PATH
from src.database import get_db_connection


def run_etl_pipeline(csv_input: Union[bytes, str], db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """
    Ingests CSV data, enforces strict types, standardizes timestamps to ISO,
    cleans numeric currencies, and executes batch upsert into SQLite.
    """
    try:
        if isinstance(csv_input, bytes):
            df = pd.read_csv(io.BytesIO(csv_input))
        elif isinstance(csv_input, str):
            # If path exists, read file; otherwise treat as string buffer
            import os
            if os.path.exists(csv_input):
                df = pd.read_csv(csv_input)
            else:
                df = pd.read_csv(io.StringIO(csv_input))
        else:
            raise ValueError("Unsupported input format for CSV.")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")

    required_columns = {"transaction_id", "client_id", "client_name", "timestamp", "amount_usd"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    # Strict string hygiene
    df["transaction_id"] = df["transaction_id"].astype(str).str.strip()
    df["client_id"] = df["client_id"].astype(str).str.strip()
    df["client_name"] = df["client_name"].astype(str).str.strip()

    # Normalize timestamps to YYYY-MM-DD HH:MM:SS
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        df["timestamp"] = df["timestamp"].fillna(pd.Timestamp.now())
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Strict numeric cleaning
    if df["amount_usd"].dtype == object:
        df["amount_usd"] = df["amount_usd"].astype(str).str.replace(r"[$,]", "", regex=True)
    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce").fillna(0.0).round(2)

    # Optional metadata fields with fallback defaults
    metadata_fields = [
        "sender_account", "receiver_account", "location",
        "destination_country", "transaction_type", "channel",
        "unstructured_narrative"
    ]
    for col in metadata_fields:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        else:
            df[col] = "UNKNOWN"

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    records = df[[
        "transaction_id", "client_id", "client_name", "timestamp", "amount_usd",
        "sender_account", "receiver_account", "location", "destination_country",
        "transaction_type", "channel", "unstructured_narrative"
    ]].to_dict(orient="records")

    cursor.executemany("""
    INSERT OR REPLACE INTO transactions (
        transaction_id, client_id, client_name, timestamp, amount_usd,
        sender_account, receiver_account, location, destination_country,
        transaction_type, channel, unstructured_narrative
    ) VALUES (
        :transaction_id, :client_id, :client_name, :timestamp, :amount_usd,
        :sender_account, :receiver_account, :location, :destination_country,
        :transaction_type, :channel, :unstructured_narrative
    )
    """, records)

    conn.commit()
    conn.close()

    return {
        "records_ingested": len(df),
        "unique_clients": int(df["client_id"].nunique()),
        "total_volume_usd": float(df["amount_usd"].sum()),
        "min_timestamp": str(df["timestamp"].min()),
        "max_timestamp": str(df["timestamp"].max())
    }
