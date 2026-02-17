"""Seed DuckDB with synthetic data products for demo purposes."""

from __future__ import annotations

import random
from datetime import date

import duckdb


def seed_database(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Create and populate dp_complaints, dp_call_reports, dp_macro_rates."""
    con = duckdb.connect(db_path)

    # ---- dp_complaints ----
    con.execute("""
        CREATE TABLE IF NOT EXISTS dp_complaints (
            complaint_id INTEGER,
            date_received DATE,
            product VARCHAR,
            issue VARCHAR,
            company VARCHAR,
            state VARCHAR,
            channel VARCHAR,
            timely BOOLEAN,
            disputed BOOLEAN,
            consumer_complaint_narrative VARCHAR
        )
    """)

    products = [
        "Mortgage", "Credit card", "Student loan",
        "Vehicle loan", "Checking account", "Savings account",
    ]
    issues = [
        "Billing disputes", "Incorrect information",
        "Communication tactics", "Closing/cancelling account",
        "Managing an account", "Struggling to pay",
    ]
    companies = [
        "JPMorgan Chase", "Bank of America", "Wells Fargo",
        "Citibank", "US Bank", "PNC Bank",
    ]
    states = ["CA", "TX", "NY", "FL", "IL", "OH", "PA", "GA", "NC", "MI"]
    channels = ["Web", "Phone", "Referral", "Mail", "Fax"]

    random.seed(42)
    rows = []
    cid = 1
    for year in range(2020, 2026):
        for month in range(1, 13):
            if year == 2025 and month > 6:
                break
            n = random.randint(30, 80)
            for _ in range(n):
                rows.append((
                    cid,
                    date(year, month, random.randint(1, 28)),
                    random.choice(products),
                    random.choice(issues),
                    random.choice(companies),
                    random.choice(states),
                    random.choice(channels),
                    random.random() > 0.1,
                    random.random() > 0.85,
                    None,  # narrative intentionally null
                ))
                cid += 1
    con.executemany(
        "INSERT INTO dp_complaints VALUES (?,?,?,?,?,?,?,?,?,?)", rows
    )

    # ---- dp_call_reports ----
    con.execute("""
        CREATE TABLE IF NOT EXISTS dp_call_reports (
            quarter VARCHAR,
            bank_name VARCHAR,
            bank_id INTEGER,
            assets DOUBLE,
            deposits DOUBLE,
            net_income DOUBLE,
            npa DOUBLE,
            tier1_ratio DOUBLE
        )
    """)

    random.seed(123)
    cr_rows = []
    bid = 1
    for bank in companies:
        base_assets = random.uniform(500_000, 3_000_000)
        for year in range(2020, 2026):
            for q in range(1, 5):
                if year == 2025 and q > 2:
                    break
                quarter_str = f"{year}-Q{q}"
                assets = base_assets * (1 + random.uniform(-0.02, 0.05))
                deposits = assets * random.uniform(0.6, 0.8)
                net_income = assets * random.uniform(0.005, 0.02)
                npa = random.uniform(0.5, 3.0)
                tier1 = random.uniform(10.0, 16.0)
                cr_rows.append((
                    quarter_str, bank, bid,
                    round(assets, 2), round(deposits, 2),
                    round(net_income, 2), round(npa, 2), round(tier1, 2),
                ))
                base_assets = assets
        bid += 1
    con.executemany(
        "INSERT INTO dp_call_reports VALUES (?,?,?,?,?,?,?,?)", cr_rows
    )

    # ---- dp_macro_rates ----
    con.execute("""
        CREATE TABLE IF NOT EXISTS dp_macro_rates (
            rate_date DATE,
            fed_funds DOUBLE,
            treasury_10y DOUBLE
        )
    """)

    random.seed(999)
    mr_rows = []
    ff = 1.5
    t10 = 2.0
    d = date(2020, 1, 1)
    while d <= date(2025, 6, 30):
        ff += random.uniform(-0.05, 0.05)
        t10 += random.uniform(-0.03, 0.04)
        ff = max(0.0, ff)
        t10 = max(0.5, t10)
        mr_rows.append((d, round(ff, 4), round(t10, 4)))
        d = date.fromordinal(d.toordinal() + 1)
    con.executemany(
        "INSERT INTO dp_macro_rates VALUES (?,?,?)", mr_rows
    )

    return con
