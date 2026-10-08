"""
src/generator.py
----------------
Synthetic corporate transaction log generator with injected regulatory
and credit risk anomalies.
"""

import argparse
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from config.settings import DEFAULT_CSV_PATH


LEGITIMATE_CORPORATIONS: List[Tuple[str, str]] = [
    ("CLT_2001", "Apex Global Trading Corp"),
    ("CLT_2002", "BlueWave Logistics Inc"),
    ("CLT_2003", "Summit Industrial Supplies"),
    ("CLT_2004", "Nordic Freight & Cargo Ltd"),
    ("CLT_2005", "Pacific Rim Tech Solutions"),
    ("CLT_2006", "Atlas Health Sciences LLC"),
    ("CLT_2007", "Solaria Energy Systems"),
    ("CLT_2008", "Vanguard BioPharma Group"),
    ("CLT_2009", "Keystone Construction Materials"),
    ("CLT_2010", "Aura Consumer Electronics"),
    ("CLT_2011", "Beacon Agribusiness Holdings"),
    ("CLT_2012", "Pinnacle Paper & Packaging"),
    ("CLT_2013", "Horizon Auto Parts Int"),
    ("CLT_2014", "Starlight Media Distribution"),
    ("CLT_2015", "Oasis Hospitality Services"),
    ("CLT_2016", "Sterling Chemical Works"),
    ("CLT_2017", "Crestview Aviation Maintenance"),
    ("CLT_2018", "Triton Marine Equipments"),
    ("CLT_2019", "Quantum Telecom Infrastructure"),
    ("CLT_2020", "Elysian Retail Enterprises"),
]

ANOMALY_ENTITIES: Dict[str, Tuple[str, str]] = {
    "VELOCITY_1": ("CLT_9001", "Zephyr Offshore Holdings Ltd"),
    "VELOCITY_2": ("CLT_9002", "Meridian Frontier Ventures"),
    "THRESHOLD_1": ("CLT_9003", "Nexus Crypto Liquidations LLC"),
    "THRESHOLD_2": ("CLT_9004", "Aegis Commodity Syndicate"),
    "THRESHOLD_3": ("CLT_9005", "Vanguard Strategic Assets Inc"),
    "OFFSHORE_1": ("CLT_9006", "Blackthorn Shell Trading"),
    "OFFSHORE_2": ("CLT_9007", "Isle Harbor Management"),
    "STRUCTURING_1": ("CLT_9008", "Titan Cash Wholesale Inc"),
    "STRUCTURING_2": ("CLT_9009", "QuickTrade Currency Exchange"),
}

LOW_RISK_JURISDICTIONS = [
    "United States", "United Kingdom", "Germany", "Japan",
    "Canada", "Singapore", "Australia", "France", "Netherlands"
]

HIGH_RISK_OFFSHORE_JURISDICTIONS = [
    "Cayman Islands", "Panama", "Cyprus", "Seychelles",
    "British Virgin Islands", "Vanuatu", "Belize", "Bahamas"
]

TRANSACTION_TYPES = ["WIRE", "SWIFT", "ACH", "SEPA", "DIRECT_DEBIT"]
CHANNELS = ["API_DIRECT", "ONLINE_PORTAL", "SWIFT_NETWORK", "COMMERCIAL_BRANCH"]

STANDARD_MEMOS = [
    "Invoice settlement - Q3 industrial parts",
    "Quarterly logistics & freight fees",
    "Software enterprise licensing renewal",
    "Raw materials purchase order #PO-8812",
    "Employee payroll disbursement",
    "Vendor equipment service contract",
    "Commercial warehouse lease payment",
    "Supply chain fulfillment retainer",
    "Bulk inventory replenishment",
    "Professional auditing services fee",
]

SUSPICIOUS_MEMOS = [
    "Urgent management consulting fee - priority release",
    "Confidential retainer transfer to special vehicle",
    "Expedited escrow disbursement per director memo",
    "Advisory commission for international facilitation",
    "Unspecified intercompany loan repayment",
    "Offshore account capitalization tranche",
    "Urgent settlement - waiver of documentation",
    "Third-party invoice liquidation without bill of lading",
]


def generate_baseline_transactions(n_records: int, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Generates standard B2B commercial transactions."""
    records = []
    total_seconds = int((end_date - start_date).total_seconds())

    for i in range(1, n_records + 1):
        txn_id = f"TXN_{100000 + i}"
        client_id, client_name = random.choice(LEGITIMATE_CORPORATIONS)
        
        amount = round(float(np.random.lognormal(mean=9.8, sigma=1.0)), 2)
        amount = max(1250.0, min(amount, 195000.0))

        random_second = random.randint(0, total_seconds)
        txn_timestamp = start_date + timedelta(seconds=random_second)

        origin = random.choice(LOW_RISK_JURISDICTIONS)
        dest = random.choice(LOW_RISK_JURISDICTIONS) if random.random() < 0.4 else origin

        sender_acc = f"US{random.randint(10, 99)}CHASE{random.randint(10000000, 99999999)}"
        receiver_acc = f"{dest[:2].upper()}{random.randint(10, 99)}CITI{random.randint(10000000, 99999999)}"

        records.append({
            "transaction_id": txn_id,
            "client_id": client_id,
            "client_name": client_name,
            "timestamp": txn_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_usd": amount,
            "sender_account": sender_acc,
            "receiver_account": receiver_acc,
            "location": origin,
            "destination_country": dest,
            "transaction_type": random.choice(TRANSACTION_TYPES),
            "channel": random.choice(CHANNELS),
            "unstructured_narrative": random.choice(STANDARD_MEMOS)
        })

    return records


def inject_anomalies(base_records: List[Dict[str, Any]], reference_date: datetime) -> List[Dict[str, Any]]:
    """Injects high-risk regulatory AML anomalies."""
    anomalous_records = []
    current_idx = len(base_records) + 100000 + 1

    # 1. VELOCITY ANOMALY 1: Zephyr Offshore Holdings (CLT_9001) - 6 txns in 5 days
    v1_id, v1_name = ANOMALY_ENTITIES["VELOCITY_1"]
    v1_start = reference_date - timedelta(days=12)
    for step in range(6):
        current_idx += 1
        txn_time = v1_start + timedelta(days=step * 0.8, hours=random.randint(1, 4))
        amount = round(random.uniform(220000.0, 480000.0), 2)
        anomalous_records.append({
            "transaction_id": f"TXN_{current_idx}",
            "client_id": v1_id,
            "client_name": v1_name,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_usd": amount,
            "sender_account": f"US99WF{random.randint(10000000, 99999999)}",
            "receiver_account": f"CY44BNP{random.randint(10000000, 99999999)}",
            "location": "United States",
            "destination_country": "Cyprus",
            "transaction_type": "SWIFT",
            "channel": "API_DIRECT",
            "unstructured_narrative": f"Rapid tranche liquidation {step+1}/6 per executive agreement"
        })

    # 2. VELOCITY ANOMALY 2: Meridian Frontier Ventures (CLT_9002) - 7 txns in 6 days
    v2_id, v2_name = ANOMALY_ENTITIES["VELOCITY_2"]
    v2_start = reference_date - timedelta(days=18)
    for step in range(7):
        current_idx += 1
        txn_time = v2_start + timedelta(days=step * 0.75, hours=random.randint(2, 6))
        amount = round(random.uniform(205000.0, 390000.0), 2)
        anomalous_records.append({
            "transaction_id": f"TXN_{current_idx}",
            "client_id": v2_id,
            "client_name": v2_name,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_usd": amount,
            "sender_account": f"GB88BARC{random.randint(10000000, 99999999)}",
            "receiver_account": f"PA22HSBC{random.randint(10000000, 99999999)}",
            "location": "United Kingdom",
            "destination_country": "Panama",
            "transaction_type": "WIRE",
            "channel": "COMMERCIAL_BRANCH",
            "unstructured_narrative": f"Intercompany emergency bridge advance tranche #{step+1}"
        })

    # 3. THRESHOLD BREACHES (> $1M USD)
    threshold_cases = [
        (ANOMALY_ENTITIES["THRESHOLD_1"], 4850000.0, "United States", "Panama", "WIRE", "Nexus Crypto Liquidations LLC - multi-million dollar unbacked redemption"),
        (ANOMALY_ENTITIES["THRESHOLD_2"], 2350000.0, "United Kingdom", "Cayman Islands", "SWIFT", "Aegis Commodity Syndicate - unverified mineral trading escrow deposit"),
        (ANOMALY_ENTITIES["THRESHOLD_3"], 7200000.0, "Canada", "Seychelles", "WIRE", "Vanguard Strategic Assets Inc - major offshore restructuring capitalization"),
        (ANOMALY_ENTITIES["THRESHOLD_1"], 1450000.0, "United States", "Switzerland", "WIRE", "Nexus Crypto Liquidations LLC - private liquidity provider transfer"),
        (ANOMALY_ENTITIES["THRESHOLD_2"], 3100000.0, "Singapore", "British Virgin Islands", "SWIFT", "Aegis Commodity Syndicate - synthetic commodities settlement")
    ]
    for (c_id, c_name), amt, origin, dest, t_type, memo in threshold_cases:
        current_idx += 1
        txn_time = reference_date - timedelta(days=random.randint(3, 25), hours=random.randint(1, 23))
        anomalous_records.append({
            "transaction_id": f"TXN_{current_idx}",
            "client_id": c_id,
            "client_name": c_name,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_usd": amt,
            "sender_account": f"{origin[:2].upper()}77INTL{random.randint(10000000, 99999999)}",
            "receiver_account": f"{dest[:2].upper()}33OFFS{random.randint(10000000, 99999999)}",
            "location": origin,
            "destination_country": dest,
            "transaction_type": t_type,
            "channel": "SWIFT_NETWORK",
            "unstructured_narrative": memo
        })

    # 4. HIGH-RISK OFFSHORE JURISDICTION DISBURSEMENTS (> $100k USD)
    offshore_cases = [
        (ANOMALY_ENTITIES["OFFSHORE_1"], 450000.0, "United States", "Cayman Islands", "SWIFT"),
        (ANOMALY_ENTITIES["OFFSHORE_1"], 620000.0, "Germany", "Panama", "WIRE"),
        (ANOMALY_ENTITIES["OFFSHORE_2"], 380000.0, "United Kingdom", "Seychelles", "SWIFT"),
        (ANOMALY_ENTITIES["OFFSHORE_2"], 750000.0, "Australia", "British Virgin Islands", "WIRE"),
        (ANOMALY_ENTITIES["OFFSHORE_1"], 290000.0, "United States", "Vanuatu", "WIRE"),
        (ANOMALY_ENTITIES["OFFSHORE_2"], 510000.0, "Singapore", "Belize", "SWIFT"),
    ]
    for (c_id, c_name), amt, origin, dest, t_type in offshore_cases:
        current_idx += 1
        txn_time = reference_date - timedelta(days=random.randint(2, 28), hours=random.randint(1, 23))
        anomalous_records.append({
            "transaction_id": f"TXN_{current_idx}",
            "client_id": c_id,
            "client_name": c_name,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_usd": amt,
            "sender_account": f"{origin[:2].upper()}88CORP{random.randint(10000000, 99999999)}",
            "receiver_account": f"{dest[:2].upper()}11HAVN{random.randint(10000000, 99999999)}",
            "location": origin,
            "destination_country": dest,
            "transaction_type": t_type,
            "channel": "ONLINE_PORTAL",
            "unstructured_narrative": random.choice(SUSPICIOUS_MEMOS)
        })

    # 5. STRUCTURING / SMURFING ANOMALY ($9,000 - $9,950 within 48-72 hours)
    struct_id, struct_name = ANOMALY_ENTITIES["STRUCTURING_1"]
    struct_start = reference_date - timedelta(days=5, hours=10)
    for step in range(8):
        current_idx += 1
        txn_time = struct_start + timedelta(hours=step * 5, minutes=random.randint(5, 45))
        smurf_amount = round(random.uniform(9200.0, 9950.0), 2)
        anomalous_records.append({
            "transaction_id": f"TXN_{current_idx}",
            "client_id": struct_id,
            "client_name": struct_name,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_usd": smurf_amount,
            "sender_account": f"US11COMM{random.randint(10000000, 99999999)}",
            "receiver_account": f"US55RECV{random.randint(10000000, 99999999)}",
            "location": "United States",
            "destination_country": "United States",
            "transaction_type": "WIRE",
            "channel": "COMMERCIAL_BRANCH",
            "unstructured_narrative": f"Installment settlement tranche {step+1} - cash equivalent delivery"
        })

    return base_records + anomalous_records


def generate_dataset(output_path: str = DEFAULT_CSV_PATH, total_count: int = 1500) -> pd.DataFrame:
    """Generates the full dataset and writes to CSV."""
    np.random.seed(42)
    random.seed(42)

    reference_date = datetime.now()
    start_date = reference_date - timedelta(days=60)

    baseline_count = max(50, total_count - 32)
    base = generate_baseline_transactions(baseline_count, start_date, reference_date)
    full_data = inject_anomalies(base, reference_date)

    df = pd.DataFrame(full_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Generated {len(df)} transactions and saved to '{output_path}'")
    print(f"  - Baseline records: {baseline_count}")
    print(f"  - Injected anomaly scenarios: {len(full_data) - baseline_count}")
    print(f"  - Total Volume USD: ${df['amount_usd'].sum():,.2f}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic corporate transaction logs.")
    parser.add_argument("--output", default=DEFAULT_CSV_PATH, help="Target CSV file path")
    parser.add_argument("--count", type=int, default=1500, help="Number of records to generate")
    args = parser.parse_args()

    generate_dataset(output_path=args.output, total_count=args.count)
