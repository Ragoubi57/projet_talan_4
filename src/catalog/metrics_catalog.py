"""Metrics catalog – YAML-based registry of KPIs, data products, and sensitivity tags."""

import os
import yaml
from typing import Any

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "metrics_catalog.yaml")


def _load_catalog(path: str | None = None) -> dict[str, Any]:
    path = path or _CATALOG_PATH
    with open(path, "r") as f:
        return yaml.safe_load(f)


def metadata_search(query: str, catalog_path: str | None = None) -> list[dict[str, Any]]:
    """METADATA_SEARCH – return metrics/datasets relevant to *query*.

    Simple keyword match against metric names, descriptions, and dataset fields.
    """
    catalog = _load_catalog(catalog_path)
    tokens = query.lower().split()
    results: list[dict[str, Any]] = []
    for dp in catalog.get("data_products", []):
        text = " ".join(
            [
                dp.get("name", ""),
                dp.get("description", ""),
                " ".join(dp.get("dimensions", [])),
                " ".join(dp.get("metrics", [])),
            ]
        ).lower()
        if any(t in text for t in tokens):
            results.append(dp)
    for metric in catalog.get("metrics", []):
        text = " ".join(
            [metric.get("id", ""), metric.get("description", ""), metric.get("data_product", "")]
        ).lower()
        if any(t in text for t in tokens):
            results.append(metric)
    return results
