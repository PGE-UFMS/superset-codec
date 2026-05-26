# superset-codec

A round-trip **Dashboard-as-Code** tool for [Apache Superset](https://superset.apache.org/).  
Databases, datasets, charts, and dashboards are described as version-controlled **YAML** files and provisioned to any environment with a single CLI command. The same files can be generated automatically from an existing Superset instance, making adoption possible without rewriting anything from scratch.

## Workflow

```
Superset UI (dev)
      │
      ▼  superset-codec export ./definitions
   Git repo  ←──────────────────────────────
      │
      ▼  superset-codec apply ./definitions
Superset (staging / production)
```

Build or tweak dashboards in the web UI, export the state to versioned files, and apply to other environments with a single command.

## Features

- **Declarative** — resources described in human-readable YAML; the codec decides whether to create or update.
- **Idempotent** — `apply` can run multiple times without side effects.
- **`export`** — converts the current Superset state (including `position_json`, `query_context`, and `native_filter_configuration`) to declarative YAML.
- **Variable interpolation** — use `${VAR}` placeholders in YAML files; the `.env` file in the definitions folder is loaded automatically by both commands.
- **Inverse interpolation** — during export, concrete values present in the `.env` are replaced by `${VAR}` automatically, keeping sensitive data out of Git.
- **URI variable matching** — any variable whose value parses as a URI matching scheme + host + port + path is used to substitute `sqlalchemy_uri`, regardless of naming convention.
- **Cascade order** — `apply` follows dependency order: `databases → datasets → charts → dashboards`.
- **Native filters** — declarative support for `select` and `date` filter types.
- **Automatic embedding** — dashboards get embedding enabled after `apply`.
- **Safe mode (`--safe`)** — on export, stores verbatim Superset fields (`query_context_raw`, `position_json_raw`, unknown filters as `_raw`) to guarantee roundtrip for any `viz_type` or filter type; on apply, per-resource errors are logged as warnings and skipped instead of aborting the pipeline.
- **Roundtrip validation (default)** — each exported chart is recreated under a temporary name, tested via the data endpoint, and deleted automatically. Use `--no-validate` to skip.

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.12 |
| [uv](https://docs.astral.sh/uv/) | recommended |
| Apache Superset | 4.x – 6.x (REST API v1) |

## Installation

```bash
git clone https://github.com/PGE-UFMS/superset-codec
cd superset-codec

# Create and activate the virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate   # Windows

# Install
pip install -e .

# Verify
superset-codec --help
```

## Flights Example

The `examples/flights/` directory contains a complete working example using a ClickHouse dataset of flight records.

**Structure:**

```
examples/flights/
├── data/
│   └── tutorial_flights.csv       # sample dataset
├── definitions/                   # superset-codec definitions
│   ├── .env.dev                   # dev environment variables
│   ├── .env.prod                  # prod environment variables
│   ├── databases/flightsdb.yaml
│   ├── datasets/flights.yaml
│   ├── charts/
│   └── dashboards/home.yaml
└── infra/
    ├── docker-compose.yml         # ClickHouse + PostgreSQL + Superset
    ├── .env.dev                   # infra config for dev
    ├── .env.prod                  # infra config for prod
    └── load_flights.sh            # loads CSV into ClickHouse
```

**Start the stack:**

```bash
cd examples/flights/infra

# Dev environment (port 8089)
docker compose --env-file .env.dev up -d

# Prod environment (port 8088)
docker compose --env-file .env.prod up -d
```

The `loader` service creates the `flightsdb` database in ClickHouse and imports the CSV automatically.

**Apply definitions to Superset:**

```bash
superset-codec apply ./examples/flights/definitions \
  --url http://localhost:8088 \
  --user admin \
  --password admin \
  --vars examples/flights/infra/.env.prod
```

**Export the current state back to YAML:**

```bash
superset-codec export ./examples/flights/definitions \
  --url http://localhost:8088 \
  --user admin \
  --password admin \
  --vars examples/flights/definitions/.env.prod
```

## Usage

### `apply` — Git → Superset

Creates or updates resources declared in YAML files:

```bash
superset-codec apply ./definitions \
  --url http://localhost:8088 \
  --user admin \
  --password admin
```

If the definitions folder contains a `.env` file, it is loaded automatically to resolve `${VAR}` placeholders. To use an explicit file:

```bash
superset-codec apply ./definitions --vars .env.prod
```

Run specific steps only:

```bash
superset-codec apply ./definitions --url ... --only databases datasets
```

Safe mode — per-resource errors are logged and skipped; `_raw` fields from export are used directly when present:

```bash
superset-codec apply ./definitions --url ... --safe
```

### `export` — Superset → Git

Exports the current Superset state to declarative YAML files:

```bash
superset-codec export ./definitions \
  --url http://localhost:8088 \
  --user admin \
  --password admin
```

If a `.env` file is provided, concrete values are replaced by `${VAR}` placeholders in the exported files:

```bash
# definitions/.env.prod contains FLIGHTSDB_URI=clickhousedb+connect://...
superset-codec export ./definitions --url ... --vars .env.prod
# → databases/flightsdb.yaml will have: sqlalchemy_uri: ${FLIGHTSDB_URI}
```

Run specific steps only:

```bash
superset-codec export ./definitions --url ... --only charts dashboards
```

Safe mode — stores `query_context_raw`, `position_json_raw`, and unknown filters as `_raw` for lossless roundtrip:

```bash
superset-codec export ./definitions --url ... --safe
```

Disable validation — by default each chart is recreated as `_tmp_*`, tested via `/api/v1/chart/data`, and deleted. Skip with:

```bash
superset-codec export ./definitions --url ... --no-validate
```

### Advanced flags

| Flag | Command | Behavior |
|------|---------|----------|
| `--safe` | `apply` | Per-resource errors become warnings; pipeline continues. Uses `_raw` fields when present. |
| `--safe` | `export` | Stores `query_context_raw`, `position_json_raw`, unknown filters as `_raw`. Guarantees roundtrip for any `viz_type`. |
| `--no-validate` | `export` | Skips roundtrip validation (create temp chart → test data → delete). Faster, less safe. |
| `--vars FILE` | both | Path to a `.env` file for variable interpolation / inverse interpolation. |
| `--only STEP...` | both | Run only the specified steps: `databases`, `datasets`, `charts`, `dashboards`. |

## Definitions Structure

```
definitions/
├── .env                  # environment variables (not committed)
├── databases/
│   └── flightsdb.yaml
├── datasets/
│   └── flights.yaml
├── charts/
│   ├── total_cost.yaml
│   └── total_cost_by_airline.yaml
└── dashboards/
    └── home.yaml
```

Subdirectories inside `charts/` are supported for organizing by theme.

## YAML File Reference

### `databases/flightsdb.yaml`

```yaml
# Connection name displayed in Superset
database_name: FlightsDb
# SQLAlchemy connection URI — use ${VAR} to keep credentials out of Git
sqlalchemy_uri: ${FLIGHTSDB_URI}
# Make this connection available in SQL Lab
expose_in_sqllab: true
allow_run_async: false
allow_cvas: false
allow_dml: false
allow_file_upload: false
configuration_method: sqlalchemy_form
driver: connect
```

### `datasets/flights.yaml`

```yaml
# Table or view name
table_name: flights
# Superset connection name (must exist in databases/)
database: FlightsDb
# Schema or database within the connection
schema: flightsdb
# Default datetime column for time filters
main_dttm_col: Travel Date
filter_select_enabled: true
is_sqllab_view: false
offset: 0
```

### `charts/total_cost.yaml`

```yaml
# Chart name displayed on the dashboard
slice_name: Total Cost
# Visualization type
viz_type: big_number_total
# Source dataset (must exist in datasets/)
datasource_table: flights
# Visualization-specific parameters
params:
  metric:
    expressionType: SIMPLE
    column:
      column_name: Cost
    aggregate: SUM
  y_axis_format: SMART_NUMBER
  time_range: No filter
```

Supported `viz_type` values with automatic `query_context` generation:

| `viz_type` | Description |
|---|---|
| `big_number_total` | Single KPI number |
| `echarts_timeseries_line` | Time series line chart |
| `echarts_timeseries_bar` | Bar chart (by category or time) |
| `pie` | Pie chart |
| `country_map` | Choropleth map by country |
| others | Generic fallback — accepted by Superset for most types |

### `dashboards/home.yaml`

```yaml
# Title displayed in Superset
dashboard_title: Home
# Unique identifier used in the URL and embedding
slug: home
# Visible to all users (false = admins only)
published: false
# Chart list with grid positions (row/col/width/height)
charts:
  - slice_name: Total Cost by Airline
    row: 0
    col: 0
    width: 4
    height: 50
  - slice_name: Total Trips
    row: 0
    col: 2
    width: 2
    height: 50
  - slice_name: Cost Data
    row: 1
    col: 0
    width: 12
    height: 50
# Native filters applied to the dashboard
native_filters:
  - name: Travel Class
    column: Travel Class
    dataset: flights
    filter_type: select   # "select" or "date"
    multi_select: false
```

Native filter options:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | required | Label shown in the filter bar |
| `column` | string | required | Column in the dataset |
| `dataset` | string | required | Dataset name (must exist in `datasets/`) |
| `filter_type` | string | `select` | `select` or `date` |
| `multi_select` | bool | `true` | Allow multiple selections (select only) |
| `default_value` | any | none | Pre-selected value; `current_year` is a special keyword |

## Environment Variables

### Variable interpolation in YAML files

Create a `.env` file inside the definitions folder:

```bash
# definitions/.env.prod  (do not commit)
FLIGHTSDB_URI=clickhousedb+connect://prod:prod@clickhouse:8123/flightsdb
```

`apply` resolves `${FLIGHTSDB_URI}` before sending to the API. `export` detects any variable whose value parses as a URI matching the connection (scheme + host + port + path) and substitutes the `sqlalchemy_uri` field automatically — even when Superset returns the password masked.

### CLI environment variables

| Variable | Equivalent flag | Default |
|----------|----------------|---------|
| `SUPERSET_URL` | `--url` | `http://localhost:8090` |
| `SUPERSET_ADMIN_USERNAME` | `--user` | `admin` |
| `SUPERSET_ADMIN_PASSWORD` | `--password` | `admin` |

## Tests

End-to-end tests spin up an isolated Docker stack (ClickHouse + PostgreSQL + Superset), seed data, and exercise `apply` and `export` against the real API.

```bash
uv sync --group dev

uv run pytest tests/e2e -m e2e        # full E2E (~3 min on first run)
uv run pytest -m "not e2e"            # unit tests only (no Docker)
```

Use `KEEP_STACK=1` to keep the containers alive after the test run.

### Running against an existing instance

```bash
SUPERSET_URL=http://localhost:8090 \
CLICKHOUSE_HOST_PORT=8123 \
FLIGHTSDB_URI="clickhousedb+connect://default:@host.docker.internal:8123/flightsdb" \
uv run pytest tests/e2e -m e2e -v
```

## Build

```bash
uv build
```

The generated wheel is placed in `dist/`.

## License

See [LICENSE](LICENSE) for details.
