"""Streamlit UI – interactive demo for the Verifiable Banking Analytics Agent."""

from __future__ import annotations

import io
import json
import csv
import os
import sys

# Ensure project root is on sys.path so `src.*` imports work when
# Streamlit is launched from the repo root via `streamlit run src/ui/app.py`.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import altair as alt
import pandas as pd
import streamlit as st

from src.agent.pipeline import run_agent
from src.data.seed import seed_database

# ── page config ──────────────────────────────────────────────────
st.set_page_config(page_title="Verifiable Banking Analytics Agent", layout="wide")
st.title("🏦 Verifiable Banking Analytics Agent")
st.caption("Ask analytics questions in natural language. All answers come with an evidence pack for audit.")

# ── sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    user_role = st.selectbox("User role", ["analyst", "compliance_officer", "admin"], index=0)
    st.markdown("---")
    st.markdown(
        "**Example queries**\n"
        '- "Show quarterly net income trend for US banks since 2020 and highlight outliers."\n'
        '- "Break down complaint volumes by product and state for the last 12 months."\n'
        '- "Can I see complaint narratives?"\n'
        '- "Export the table and give me an evidence pack for audit."\n'
    )

# ── database ─────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    return seed_database()

con = get_db()

# ── main input ───────────────────────────────────────────────────
query = st.text_input("Ask a question:", placeholder="e.g., Show quarterly net income trend for US banks since 2020")

if query:
    with st.spinner("Running verifiable analytics pipeline…"):
        result = run_agent(query, con, user_role=user_role)

    if result["status"] == "denied":
        st.error(f"🚫 **Policy denied:** {result['explanation']}")
        st.info(f"💡 **Alternative:** {result.get('alternative', 'N/A')}")
        with st.expander("DSL plan"):
            st.json(result["dsl"])
    elif result["status"] == "error":
        st.error(f"Query error: {result['error']}")
        with st.expander("Generated SQL"):
            st.code(result["sql"], language="sql")
    else:
        # ── explanation ──────────────────────────────────────────
        st.markdown(f"### 📝 Explanation\n{result['explanation']}")

        # ── chart / table ────────────────────────────────────────
        df = pd.DataFrame(result["data"])
        if not df.empty:
            # Mark outliers
            df["_outlier"] = False
            for idx in result.get("outlier_indices", []):
                if idx < len(df):
                    df.loc[idx, "_outlier"] = True

            intent = result["dsl"].get("intent", "table")
            dims = result["dsl"].get("dimensions", [])
            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            if intent == "chart" and dims and numeric_cols:
                metric_col = numeric_cols[-1]
                dim_col = dims[0]

                base = alt.Chart(df).encode(
                    x=alt.X(f"{dim_col}:N", sort=None),
                    y=alt.Y(f"{metric_col}:Q"),
                )
                line = base.mark_line(point=True)
                outlier_df = df[df["_outlier"]]
                outlier_pts = (
                    alt.Chart(outlier_df)
                    .mark_point(size=120, color="red", filled=True)
                    .encode(
                        x=alt.X(f"{dim_col}:N", sort=None),
                        y=alt.Y(f"{metric_col}:Q"),
                        tooltip=list(df.columns),
                    )
                ) if not outlier_df.empty else alt.Chart(pd.DataFrame()).mark_point()

                st.altair_chart(line + outlier_pts, use_container_width=True)
            else:
                st.dataframe(df.drop(columns=["_outlier"]), use_container_width=True)

            # ── export ───────────────────────────────────────────
            if result["dsl"].get("export", {}).get("format") == "csv":
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow([c for c in df.columns if c != "_outlier"])
                for _, row in df.iterrows():
                    writer.writerow([row[c] for c in df.columns if c != "_outlier"])
                st.download_button(
                    "⬇️ Download CSV",
                    data=buf.getvalue(),
                    file_name="analytics_export.csv",
                    mime="text/csv",
                )

        # ── SQL ──────────────────────────────────────────────────
        with st.expander("🔍 Generated SQL"):
            st.code(result["sql"], language="sql")

        # ── evidence pack ────────────────────────────────────────
        with st.expander("📦 Evidence Pack (audit)"):
            st.json(result["evidence_pack"])
