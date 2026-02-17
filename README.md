# Verifiable Banking Analytics Agent

A **verifiable, policy-governed analytics agent** for regulated banking environments.  
Ask analytics questions in natural language and receive **charts, tables, plain-language explanations, and audit-ready evidence packs** — all governed by privacy and access policies.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Natural Language Query                                          │
│  "Show quarterly net income trend for US banks since 2020"       │
└──────────┬───────────────────────────────────────────────────────┘
           │
   ┌───────▼──────────┐
   │  DSL Parser       │  NL → structured Analytics DSL plan
   └───────┬──────────┘
           │
   ┌───────▼──────────┐
   │ Metrics Catalog   │  METADATA_SEARCH – YAML registry of KPIs,
   │ (Semantic Layer)  │  data products, sensitivity tags, versions
   └───────┬──────────┘
           │
   ┌───────▼──────────┐
   │  Policy Engine    │  POLICY_EVAL – ABAC/PBAC (role, sensitivity,
   │  (OPA-style)      │  min aggregation, PII guardrails)
   └───────┬──────────┘
           │  ALLOW / DENY / ALLOW_WITH_CONSTRAINTS
   ┌───────▼──────────┐
   │  SQL Compiler     │  DSL → validated SQL (sqlglot + DuckDB)
   └───────┬──────────┘
           │
   ┌───────▼──────────┐
   │  DuckDB Engine    │  RUN_QUERY on certified data products
   └───────┬──────────┘
           │
   ┌───────▼──────────┐
   │ Evidence Pack     │  Metric version, datasets, freshness,
   │ + Quality Status  │  policy decision, SQL hash, lineage
   └───────┬──────────┘
           │
   ┌───────▼──────────┐
   │  Streamlit UI     │  Charts (Altair) + Tables + Evidence Pack
   └──────────────────┘
```

## Data Products (Gold Layer)

| Data Product | Source | Grain | Key Metrics |
|---|---|---|---|
| `dp_complaints` | CFPB Consumer Complaint Database | daily | complaint_volume, timely_response_rate, disputed_rate |
| `dp_call_reports` | FDIC/FFIEC Call Reports | quarterly | net_income, total_assets, total_deposits, npa_ratio, tier1_ratio |
| `dp_macro_rates` | FRED | daily | fed_funds_rate, treasury_10y_rate |

## Demo Queries

| Query | Expected Result |
|---|---|
| *"Show quarterly net income trend for US banks since 2020 and highlight outliers."* | Chart with trend line + red outlier markers + evidence pack |
| *"Break down complaint volumes by product and state for the last 12 months."* | Table grouped by product × state + evidence pack |
| *"Can I see complaint narratives?"* | **Policy DENY** – narrative fields are HIGH sensitivity (analyst role) |
| *"Export the table and give me an evidence pack for audit."* | CSV export + full evidence pack with SQL hash |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run tests
python -m pytest tests/ -v

# 3. Launch Streamlit UI
streamlit run src/ui/app.py
```

## Project Structure

```
├── data/
│   └── metrics_catalog.yaml     # KPI registry (semantic layer)
├── src/
│   ├── agent/
│   │   └── pipeline.py          # Full analytics pipeline orchestration
│   ├── catalog/
│   │   └── metrics_catalog.py   # METADATA_SEARCH tool
│   ├── data/
│   │   └── seed.py              # DuckDB synthetic data seeding
│   ├── dsl/
│   │   ├── parser.py            # NL → DSL plan
│   │   └── compiler.py          # DSL → validated SQL
│   ├── policy/
│   │   └── engine.py            # POLICY_EVAL (ABAC/PBAC)
│   └── ui/
│       └── app.py               # Streamlit demo UI
├── tests/
│   ├── test_catalog.py
│   ├── test_compiler.py
│   ├── test_parser.py
│   ├── test_pipeline.py
│   └── test_policy.py
├── requirements.txt
└── README.md
```

## Policy Engine

The policy engine enforces:

- **Role-based access**: Narrative/PII fields require `compliance_officer` or `admin` role
- **Privacy guardrails**: Minimum group size (default 10) for individual-level data
- **Sensitivity tags**: Each field tagged LOW/HIGH; HIGH fields trigger policy evaluation
- **Safe defaults**: Ambiguous requests get the most aggregated, least sensitive interpretation

## Evidence Pack

Every successful query produces an evidence pack containing:

```json
{
  "evidence_pack_id": "uuid",
  "timestamp": "ISO-8601",
  "dsl_plan": { "..." },
  "policy_decision": { "decision": "ALLOW", "..." },
  "sql_hash": "sha256-prefix",
  "sql": "SELECT ...",
  "datasets_quality": [
    { "dataset": "dp_call_reports", "version": "2.0.1", "freshness": "quarterly", "tests_passed": true }
  ],
  "result_row_count": 132
}
```

## Tool Stack

| Layer | Tool |
|---|---|
| Analytics engine | DuckDB |
| SQL validation | sqlglot |
| Metrics catalog | YAML + Python |
| Policy engine | Python (OPA-style ABAC) |
| UI | Streamlit + Altair |
| Testing | pytest |
