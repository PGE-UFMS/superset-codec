# superset-provision

An idempotent provisioning tool for [Apache Superset](https://superset.apache.org/).  
Define your databases, datasets, charts, and dashboards as **JSON files** and let `superset-provision` create or update them via the Superset REST API — no manual clicking required.

## Features

- **Declarative** — describe resources in JSON; the tool figures out whether to create or update.
- **Idempotent** — run it as many times as you want; existing resources are updated in place.
- **Variable interpolation** — use `${VAR}` placeholders in your JSON files, resolved at runtime.
- **Cascade ordering** — resources are synced in dependency order: databases → datasets → charts → dashboards.
- **Automatic embedding** — dashboards get embedding enabled automatically after provisioning.

## Requirements

| Requirement | Version |
|-------------|---------|
| Python      | ≥ 3.12  |
| [uv](https://docs.astral.sh/uv/) | latest recommended |
| Apache Superset instance | 6.x (REST API v1) |

## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd superset-provision
```

### 2. Install dependencies

This project uses [uv](https://docs.astral.sh/uv/) as its build backend and package manager.

```bash
# Install uv (if you don't have it yet)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create the virtual environment and install dependencies
uv sync
```

### 3. Configure your resources

Create a directory (default: `./resources`) with sub-folders for each resource type:

```
resources/
├── databases/
│   └── my_database.json
├── datasets/
│   └── my_table.json
├── charts/
│   └── my_chart.json
└── dashboards/
    └── my_dashboard.json
```

See [`docs/example/`](docs/example/) for sample resource files and [`docs/schemas/`](docs/schemas/) for JSON schemas.

### 4. Run the provisioner

```bash
uv run superset-provision \
  --url http://localhost:8088 \
  --user admin \
  --password admin
```

You can also target specific steps:

```bash
uv run superset-provision --url ... --user ... --password ... --steps databases datasets
```

Valid steps: `databases`, `datasets`, `charts`, `dashboards`.

## Environment Variables

Instead of passing flags, you can set:

| Variable | Description |
|----------|-------------|
| `SUPERSET_URL` | Base URL of the Superset instance |
| `SUPERSET_USER` | Login username |
| `SUPERSET_PASSWORD` | Login password |

## Building

```bash
uv build
```

The built wheel will be in `dist/`.

## License

See [LICENSE](LICENSE) for details.
