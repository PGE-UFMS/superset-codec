"""E2E: provisiona apenas databases + datasets contra um Superset/ClickHouse reais."""
from __future__ import annotations

import json
from pathlib import Path

from superset_provision import SupersetProvisioner

RESOURCES_DIR = Path(__file__).parent / "resources"

# CLICKHOUSE_HOST=clickhouse é o nome do serviço na rede `testnet` do compose —
# o container do Superset resolve via DNS interno.
PROVISIONER_VARS = {
    "CLICKHOUSE_HOST": "clickhouse",
    "CLICKHOUSE_PORT": "8123",
    "CLICKHOUSE_USER": "default",
    "CLICKHOUSE_PASSWORD": "",
    "CLICKHOUSE_DATABASE": "default",
}


def _query_count(session, url: str, api_path: str, col: str, value: str) -> int:
    q = {"filters": [{"col": col, "opr": "eq", "value": value}]}
    r = session.get(f"{url}{api_path}", params={"q": json.dumps(q)}, timeout=15)
    r.raise_for_status()
    return r.json()["count"]


def test_provision_databases_and_datasets(superset_url, seeded_warehouse):
    p = SupersetProvisioner(
        url=superset_url,
        user="admin",
        password="admin",
        resources_dir=RESOURCES_DIR,
        variables=PROVISIONER_VARS,
    )

    p.sync_all(steps=["databases", "datasets"])

    s = p.session
    assert _query_count(s, superset_url, "/api/v1/database/", "database_name", "Test Warehouse") == 1
    assert _query_count(s, superset_url, "/api/v1/dataset/", "table_name", "warehouse") == 1


def test_provision_is_idempotent(superset_url, seeded_warehouse):
    """Rodar duas vezes não deve duplicar recursos nem falhar."""
    p = SupersetProvisioner(
        url=superset_url,
        user="admin",
        password="admin",
        resources_dir=RESOURCES_DIR,
        variables=PROVISIONER_VARS,
    )
    p.sync_all(steps=["databases", "datasets"])
    p.sync_all(steps=["databases", "datasets"])

    s = p.session
    assert _query_count(s, superset_url, "/api/v1/database/", "database_name", "Test Warehouse") == 1
    assert _query_count(s, superset_url, "/api/v1/dataset/", "table_name", "warehouse") == 1
