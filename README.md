# superset-codec

Um codec declarativo e idempotente para [Apache Superset](https://superset.apache.org/).  
Descreva bancos de dados, datasets, charts e dashboards em **YAML** e use `superset-codec` para aplicá-los em qualquer ambiente — ou exporte o estado atual do Superset de volta para YAML.

## Fluxo de trabalho UI-first

```
Superset UI (dev)
      │
      ▼  superset-codec export ./resources
   Git repo  ←──────────────────────────────
      │
      ▼  superset-codec apply ./resources
Superset (staging / produção)
```

Crie ou ajuste seus dashboards na interface web, exporte o estado para arquivos versionáveis e aplique em outros ambientes com um único comando.

## Funcionalidades

- **Declarativo** — recursos descritos em YAML legível; o codec decide criar ou atualizar.
- **Idempotente** — `apply` pode ser executado múltiplas vezes sem efeitos colaterais.
- **`export`** — converte o estado atual do Superset (incluindo `position_json`, `query_context` e `native_filter_configuration`) para o formato YAML declarativo.
- **Variáveis com `.env`** — `${VAR}` nos arquivos YAML; o arquivo `.env` da pasta de recursos é carregado automaticamente por ambos os comandos.
- **Inverse interpolation** — no export, valores concretos presentes no `.env` são substituídos por `${VAR}` automaticamente, mantendo dados sensíveis fora do Git.
- **Comentários automáticos** — arquivos exportados incluem uma linha de documentação por campo em inglês.
- **Ordem em cascata** — `apply` segue a ordem de dependências: `databases → datasets → charts → dashboards`.
- **Tabs em dashboards** — suporte a dashboards com abas; cada chart pode especificar um campo `tab`.
- **Filtros nativos** — suporte a filtros do tipo `select` e `date` com configuração declarativa.
- **Embedding automático** — dashboards recebem embedding habilitado após `apply`.

## Requisitos

| Requisito | Versão |
|-----------|--------|
| Python | ≥ 3.12 |
| [uv](https://docs.astral.sh/uv/) | recomendado |
| Apache Superset | 4.x – 6.x (REST API v1) |

## Instalação

```bash
# Instalar uv (se ainda não tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Criar o ambiente e instalar dependências
git clone <repo-url>
cd superset-provision
uv sync
```

## Uso

### `apply` — Git → Superset

Cria ou atualiza recursos declarados nos arquivos YAML:

```bash
uv run superset-codec apply ./resources \
  --url http://localhost:8088 \
  --user admin \
  --password admin
```

Se a pasta de recursos contiver um arquivo `.env`, ele é carregado automaticamente para resolver os `${VAR}` nos arquivos YAML. Para usar um arquivo explícito:

```bash
uv run superset-codec apply ./resources --vars .env.production
```

Apenas passos específicos:

```bash
uv run superset-codec apply ./resources --url ... --only databases datasets
```

### `export` — Superset → Git

Exporta o estado atual do Superset para arquivos YAML declarativos:

```bash
uv run superset-codec export ./resources \
  --url http://localhost:8088 \
  --user admin \
  --password admin
```

Se `resources/.env` existir, os valores nele contidos são substituídos por `${VAR}` nos arquivos exportados — dados sensíveis ficam fora do Git:

```bash
# resources/.env já existe com GOLD_URI=clickhousedb+connect://...
uv run superset-codec export ./resources --url ...
# → databases/gold.yaml terá: sqlalchemy_uri: ${GOLD_URI}
```

Apenas passos específicos:

```bash
uv run superset-codec export ./resources --url ... --only dashboards charts
```

Passos válidos: `databases`, `datasets`, `charts`, `dashboards`.

## Estrutura de recursos

```
resources/
├── .env                  # variáveis de ambiente (não versionado)
├── databases/
│   └── gold.yaml
├── datasets/
│   └── minha_tabela.yaml
├── charts/
│   ├── kpi_total.yaml
│   └── evolucao_mensal.yaml
└── dashboards/
    └── painel_geral.yaml
```

Subpastas são suportadas em `charts/` para organização por tema.

## Exemplos de arquivos

### `databases/gold.yaml`

```yaml
# Connection name displayed in Superset
database_name: gold
# SQLAlchemy connection URI. Use ${VAR} for sensitive values
sqlalchemy_uri: ${GOLD_URI}
# Make this connection available in SQL Lab
expose_in_sqllab: true
allow_run_async: true
allow_cvas: true
allow_dml: false
```

### `datasets/processos_novos_wide.yaml`

```yaml
# Table or view name
table_name: processos_novos_wide
# Superset connection name (must exist in databases/)
database: gold
# Schema or database within the connection
schema: gold
```

### `charts/kpi_total.yaml`

```yaml
# Chart name displayed on the dashboard
slice_name: Total de Processos
# Visualization type (e.g. big_number_total, echarts_timeseries_bar)
viz_type: big_number_total
# Source table/dataset (must exist in datasets/)
datasource_table: processos_novos_wide
# Visualization-specific configuration
params:
  metric: count
  time_range: No filter
```

Tipos de visualização mapeados com `query_context` gerado automaticamente:

| `viz_type` | Descrição |
|---|---|
| `big_number_total` | KPI — número único |
| `echarts_timeseries_line` | Linha temporal |
| `echarts_timeseries_bar` | Barras (por categoria ou temporal) |
| `pie` | Pizza |
| `country_map` | Mapa coroplético por país |
| outros | Fallback genérico — aceito pelo Superset para a maioria dos tipos |

### `dashboards/painel_geral.yaml`

```yaml
# Title displayed in Superset
dashboard_title: Painel Geral
# Unique identifier used in the URL and embedding
slug: painel-geral
# Visible to all users (false = admins only)
published: true
# Chart list with grid positions (row/col/width/height)
charts:
  - slice_name: Total de Processos
    row: 0
    col: 0
    width: 6
    height: 20
  - slice_name: Evolução Mensal
    row: 1
    col: 0
    width: 12
    height: 45
  # Charts com campo "tab" formam um layout com abas
  - slice_name: Ranking por Área
    row: 2
    col: 0
    width: 12
    height: 45
    tab: Por Área
  - slice_name: Ranking por Procurador
    row: 2
    col: 0
    width: 12
    height: 45
    tab: Por Procurador
```

### Filtros nativos

```yaml
# Native filters applied to the dashboard
native_filters:
  - name: Período
    column: dt_registro
    dataset: processos_novos_wide
    filter_type: date            # "date" ou "select" (padrão)
    default_value: No filter

  - name: Área
    column: area_nome_area
    dataset: processos_novos_wide
    filter_type: select
    multi_select: true           # padrão: true
    default_value: current_year  # ou valor fixo, ou lista
```

## Variáveis de ambiente

### Interpolação nos arquivos YAML

Crie um arquivo `.env` dentro da pasta de recursos:

```bash
# resources/.env  (não versionar)
GOLD_URI=clickhousedb+connect://default:senha@host:8123/gold
```

O `apply` resolve `${GOLD_URI}` antes de enviar à API. O `export` substitui o valor concreto por `${GOLD_URI}` nos arquivos gerados.

### Configuração da CLI

| Variável | Flag equivalente | Padrão |
|----------|-----------------|--------|
| `SUPERSET_URL` | `--url` | `http://localhost:8090` |
| `SUPERSET_ADMIN_USERNAME` | `--user` | `admin` |
| `SUPERSET_ADMIN_PASSWORD` | `--password` | `admin` |

## Testes

Os testes E2E sobem um stack Docker isolado (ClickHouse + PostgreSQL + Superset), semeiam dados e exercitam `apply` e `export` contra a API real.

```bash
uv sync --group dev

uv run pytest tests/e2e -m e2e        # E2E completo (~3 min na 1ª execução)
uv run pytest -m "not e2e"            # apenas testes sem Docker
```

### Rodar contra uma instância já em execução

Se o Superset e o ClickHouse já estiverem rodando localmente, pule o docker-compose:

```bash
SUPERSET_URL=http://localhost:8090 \
CLICKHOUSE_HOST_PORT=8123 \
GOLD_URI="clickhousedb+connect://default:@host.docker.internal:8123/default" \
uv run pytest tests/e2e -m e2e -v
```

### Cobertura de viz types

Os testes são parametrizados por tipo de visualização para garantir que `_build_query_context` gera um payload aceito pelo Superset:

| Teste | Garante |
|---|---|
| `test_apply_chart_viz_type[big_number_total]` | KPI criado sem erro |
| `test_apply_chart_viz_type[echarts_timeseries_line]` | Linha temporal criada |
| `test_apply_chart_viz_type[echarts_timeseries_bar]` | Barras criadas |
| `test_apply_chart_viz_type[table]` | Tabela criada (fallback genérico) |
| `test_apply_dashboard_with_tabs` | Layout com abas aplicado |
| `test_apply_is_idempotent` | Nenhum recurso duplicado em dois applies |
| `test_export_apply_roundtrip` | Export gera YAML; re-apply não duplica |

Use `KEEP_STACK=1` para manter os containers após os testes.

## Build

```bash
uv build
```

O wheel gerado fica em `dist/`.

## Licença

Veja [LICENSE](LICENSE) para detalhes.
