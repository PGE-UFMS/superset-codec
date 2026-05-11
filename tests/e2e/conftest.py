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
STACK_DIR = E2E_DIR / "stack"
COMPOSE_FILE = STACK_DIR / "docker-compose.yml"
ENV_FILE = STACK_DIR / "test.env"

CLICKHOUSE_HOST_PORT = int(os.environ.get("CLICKHOUSE_HOST_PORT", "18123"))
SUPERSET_HOST_PORT = int(os.environ.get("SUPERSET_HOST_PORT", "18088"))


def _compose(*args: str, check: bool = True):
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), "--env-file", str(ENV_FILE), *args]
    return subprocess.run(cmd, check=check)


@pytest.fixture(scope="session")
def superset_url():
    """Sobe o stack e devolve a URL do Superset.

    ``docker compose up --wait`` bloqueia até todos os healthchecks ficarem
    healthy, então não precisa de retry/wait em Python.
    Set ``KEEP_STACK=1`` para manter os containers depois dos testes.
    """
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
def seeded_warehouse(superset_url):
    """Cria a tabela ``warehouse`` e popula com dados fake determinísticos."""
    client = clickhouse_connect.get_client(
        host="localhost",
        port=CLICKHOUSE_HOST_PORT,
        username="default",
        password="",
    )
    client.command("DROP TABLE IF EXISTS warehouse")
    client.command("""
        CREATE TABLE warehouse (
            event_date Date,
            event_ts   DateTime,
            region     LowCardinality(String),
            category   LowCardinality(String),
            product_id UInt32,
            units      UInt32,
            revenue    Float64
        ) ENGINE = MergeTree()
        ORDER BY (event_date, region, category)
    """)

    rng = random.Random(42)
    regions = ["north", "south", "east", "west"]
    categories = ["alpha", "beta", "gamma", "delta"]
    base = date(2025, 1, 1)

    rows = []
    for _ in range(500):
        d = base + timedelta(days=rng.randint(0, 180))
        ts = datetime.combine(d, datetime.min.time()) + timedelta(seconds=rng.randint(0, 86399))
        rows.append([
            d, ts,
            rng.choice(regions),
            rng.choice(categories),
            rng.randint(1, 50),
            rng.randint(1, 20),
            round(rng.uniform(10.0, 500.0), 2),
        ])
    client.insert(
        "warehouse",
        rows,
        column_names=["event_date", "event_ts", "region", "category", "product_id", "units", "revenue"],
    )
    return client
