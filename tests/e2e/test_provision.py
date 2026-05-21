"""E2E: applies and exports resources against real Superset + ClickHouse instances."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from superset_codec import SupersetCodec

RESOURCES_DIR = Path(__file__).parent / "resources"

# URI as seen from inside Superset's container (Superset → ClickHouse).
# Override with GOLD_URI env var when using an existing stack.
# Default matches the docker-compose test network (service name "clickhouse").
# For an existing local Superset (Docker on Mac): host.docker.internal:8123
_DEFAULT_GOLD_URI = "clickhousedb+connect://default:@clickhouse:8123/default"
CODEC_VARS = {"GOLD_URI": os.environ.get("GOLD_URI", _DEFAULT_GOLD_URI)}

# Chart names that correspond to each mapped viz_type
VIZ_TYPE_CHARTS = {
    "big_number_total":      "Test KPI Revenue",
    "echarts_timeseries_line": "Test Revenue Timeline",
    "echarts_timeseries_bar":  "Test Revenue by Region",
    "table":                 "Test Detail Table",
}


def _count(session, url: str, api_path: str, col: str, value: str) -> int:
    q = {"filters": [{"col": col, "opr": "eq", "value": value}]}
    r = session.get(f"{url}{api_path}", params={"q": json.dumps(q)}, timeout=15)
    r.raise_for_status()
    return r.json()["count"]


def _codec(superset_url, resources_dir=RESOURCES_DIR) -> SupersetCodec:
    return SupersetCodec(
        url=superset_url,
        user="admin",
        password="admin",
        resources_dir=resources_dir,
        variables=CODEC_VARS,
    )


def test_apply_databases_and_datasets(superset_url, seeded_warehouse):
    codec = _codec(superset_url)
    codec.apply(steps=["databases", "datasets"])

    s = codec.session
    assert _count(s, superset_url, "/api/v1/database/", "database_name", "Test Warehouse") == 1
    assert _count(s, superset_url, "/api/v1/dataset/",  "table_name",    "warehouse")      == 1

@pytest.mark.parametrize("viz_type,slice_name", VIZ_TYPE_CHARTS.items())
def test_apply_chart_viz_type(superset_url, seeded_warehouse, viz_type, slice_name):
    """Each viz_type handled by _build_query_context creates a chart without error."""
    codec = _codec(superset_url)
    codec.apply(steps=["databases", "datasets", "charts"])

    count = _count(codec.session, superset_url, "/api/v1/chart/", "slice_name", slice_name)
    assert count == 1, f"viz_type '{viz_type}' chart '{slice_name}' not found after apply"


def test_apply_dashboard_with_tabs(superset_url, seeded_warehouse):
    """Dashboard with tabbed layout is created and charts are linked."""
    codec = _codec(superset_url)
    codec.apply()

    s = codec.session
    assert _count(s, superset_url, "/api/v1/dashboard/", "slug", "test-dashboard") == 1

def test_apply_is_idempotent(superset_url, seeded_warehouse):
    """Running apply twice must not duplicate any resource."""
    codec = _codec(superset_url)
    codec.apply()
    codec.apply()

    s = codec.session
    assert _count(s, superset_url, "/api/v1/database/",  "database_name", "Test Warehouse")     == 1
    assert _count(s, superset_url, "/api/v1/dataset/",   "table_name",    "warehouse")          == 1
    assert _count(s, superset_url, "/api/v1/chart/",     "slice_name",    "Test KPI Revenue")   == 1
    assert _count(s, superset_url, "/api/v1/dashboard/", "slug",          "test-dashboard")     == 1

def test_export_apply_roundtrip(superset_url, seeded_warehouse, tmp_path):
    """export() captures state; re-applying the exported files produces no duplicates."""
    # 1. initial apply
    codec = _codec(superset_url)
    codec.apply()

    # 2. export to tmp_path
    export_codec = _codec(superset_url, resources_dir=tmp_path)
    export_codec.export()

    # 3. exported files must exist for every resource type
    assert len(list((tmp_path / "databases").glob("*.yaml"))) >= 1
    assert len(list((tmp_path / "datasets").glob("*.yaml")))  >= 1
    assert len(list((tmp_path / "charts").glob("*.yaml")))    == len(VIZ_TYPE_CHARTS)
    assert len(list((tmp_path / "dashboards").glob("*.yaml"))) >= 1

    # 4. re-apply from exported files — no duplicates
    export_codec.apply()

    s = export_codec.session
    assert _count(s, superset_url, "/api/v1/chart/",     "slice_name", "Test KPI Revenue") == 1
    assert _count(s, superset_url, "/api/v1/dashboard/", "slug",       "test-dashboard")   == 1
