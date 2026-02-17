"""Tests for the metrics catalog."""

import os
from src.catalog.metrics_catalog import metadata_search

CATALOG = os.path.join(os.path.dirname(__file__), "..", "data", "metrics_catalog.yaml")


def test_search_complaints():
    results = metadata_search("complaint", catalog_path=CATALOG)
    names = [r.get("name") or r.get("id") for r in results]
    assert "dp_complaints" in names


def test_search_net_income():
    results = metadata_search("net income", catalog_path=CATALOG)
    names = [r.get("name") or r.get("id") for r in results]
    assert any("call_reports" in n or "net_income" in n for n in names)


def test_search_no_match():
    results = metadata_search("xyzzy_nonexistent", catalog_path=CATALOG)
    assert len(results) == 0
