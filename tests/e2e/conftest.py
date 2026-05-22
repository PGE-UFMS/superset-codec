"""E2E test fixtures: bring up docker compose, seed ClickHouse."""
from __future__ import annotations

import logging
import os
import random
import subprocess
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import clickhouse_connect
import pytest

log = logging.getLogger(__name__)


def pytest_collection_modifyitems(config, items):
    """Marca automaticamente todos os testes sob ``tests/e2e/`` com ``@pytest.mark.e2e``."""
    e2e_root = Path(__file__).parent
    for item in items:
        try:
            item.path.relative_to(e2e_root)
        except ValueError:
            continue
        item.add_marker(pytest.mark.e2e)


E2E_DIR = Path(__file__).parent
COMPOSE_FILE = E2E_DIR / "docker-compose.yml"

CLICKHOUSE_HOST_PORT = int(os.environ.get("CLICKHOUSE_HOST_PORT", "18123"))
SUPERSET_HOST_PORT = int(os.environ.get("SUPERSET_HOST_PORT", "18088"))

# Set SUPERSET_URL to skip docker-compose and use an existing instance.
# Example: SUPERSET_URL=http://localhost:8090 CLICKHOUSE_HOST_PORT=8123 uv run pytest tests/e2e
_SUPERSET_URL_OVERRIDE = os.environ.get("SUPERSET_URL")


def _compose(*args: str, check: bool = True):
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    return subprocess.run(cmd, check=check)


@pytest.fixture(scope="session")
def superset_url():
    """Returns the Superset URL.

    If ``SUPERSET_URL`` is set, uses that directly (no docker-compose).
    Otherwise, brings up the docker-compose stack and tears it down after.
    Set ``KEEP_STACK=1`` to keep containers running after the tests.
    """
    if _SUPERSET_URL_OVERRIDE:
        log.warning("Using existing Superset at %s (docker-compose skipped).", _SUPERSET_URL_OVERRIDE)
        yield _SUPERSET_URL_OVERRIDE
        return

    log.warning(
        "Subindo docker compose (build + healthchecks) — primeira execução "
        "pode levar 2-3 min. Use `docker compose -f %s logs -f` para acompanhar.",
        COMPOSE_FILE,
    )
    t0 = time.monotonic()
    _compose("up", "-d", "--build", "--wait")
    log.warning("Stack pronto em %.1fs", time.monotonic() - t0)
    try:
        yield f"http://localhost:{SUPERSET_HOST_PORT}"
    finally:
        if os.environ.get("KEEP_STACK") != "1":
            log.warning("Derrubando docker compose (KEEP_STACK=1 para manter)...")
            _compose("down", "-v", check=False)


@pytest.fixture(scope="session")
def seeded_shipments(superset_url):
    """Creates the ``shipments`` table with deterministic fake data.

    Connects to localhost:CLICKHOUSE_HOST_PORT.
    For an existing stack use CLICKHOUSE_HOST_PORT=8123.
    """
    client = clickhouse_connect.get_client(
        host="localhost",
        port=CLICKHOUSE_HOST_PORT,
        username="default",
        password="",
    )
    client.command("DROP TABLE IF EXISTS shipments")
    client.command("""
        CREATE TABLE shipments (
            shipment_date Date,
            shipment_ts   DateTime,
            uf            LowCardinality(String),
            category      LowCardinality(String),
            status        LowCardinality(String),
            weight_kg     Float64,
            revenue       Float64
        ) ENGINE = MergeTree()
        ORDER BY (shipment_date, uf, category)
    """)

    rng = random.Random(42)
    ufs = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    ]
    categories = ["electronics", "clothing", "food", "books", "sports"]
    statuses = ["delivered"] * 7 + ["in_transit"] * 2 + ["returned"] * 1
    base = date(2025, 1, 1)

    rows = []
    for _ in range(3000):
        d = base + timedelta(days=rng.randint(0, 180))
        ts = datetime.combine(d, datetime.min.time()) + timedelta(seconds=rng.randint(0, 86399))
        rows.append([
            d, ts,
            rng.choice(ufs),
            rng.choice(categories),
            rng.choice(statuses),
            round(rng.uniform(0.1, 30.0), 2),
            round(rng.uniform(15.0, 500.0), 2),
        ])
    client.insert(
        "shipments",
        rows,
        column_names=["shipment_date", "shipment_ts", "uf", "category", "status", "weight_kg", "revenue"],
    )
    return client
