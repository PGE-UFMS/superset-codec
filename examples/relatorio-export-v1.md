# Relatório de Export — Instância de Teste v1

**Data de execução:** 22 de maio de 2026
**Comando:** `superset-codec export ./examples/export --url http://localhost:8090 --user admin --password admin --safe`
**Resultado:** 59 YAMLs gerados em [examples/export/](export/) | 48/48 charts validados por roundtrip de query | 0 falhas reportadas pela ferramenta

---

## 1. Resumo Executivo

A ferramenta `superset-codec` exportou todos os artefatos da instância de teste do Superset 6.1: 1 database, 1 dataset, 48 charts e 9 dashboards (com 29 entradas de filtros nativos por dashboard). A execução foi feita em modo `--safe`; a justificativa está em §2.

Os 48 charts passaram na validação automática por roundtrip de query — para cada chart, a ferramenta cria uma cópia temporária, executa `/api/v1/chart/data` e a deleta. Essa validação confirma que o chart é capaz de retornar dados na instância de origem, mas **não** atesta que o YAML reconstrói o estado completo em um Superset limpo.

A combinação do modo `--safe` com auditoria dos YAMLs em [examples/export/](export/) elimina três das limitações documentadas na auditoria preliminar (filtros de range/tempo, layout dos dashboards e query context dos charts), mas mantém quatro riscos residuais relevantes para re-aplicação — listados em §9.

---

## 2. Justificativa do uso de `--safe`

Os critérios automáticos que disparariam `--safe` (definidos em [src/superset_codec/_export.py](../src/superset_codec/_export.py) e [src/superset_codec/_filters.py](../src/superset_codec/_filters.py)) não foram acionados nesta instância — todos os `viz_type` são conhecidos, todos os `filterType` estão no conjunto reconhecido pelo schema simplificado e nenhum chart falhou em roundtrip. Mesmo assim, uma auditoria prévia dos YAMLs do export padrão revelou perdas silenciosas de schema:

- O dashboard YAML lista os charts em uma grade `row/col/width/height` flat, descartando containers `TABS`/`ROW`/`COLUMN`/`HEADER`/`MARKDOWN`/`DIVIDER` do `position_json`.
- Filtros `filter_range`, `filter_timecolumn` e `filter_timegrain` (16 dos 29) eram serializados como `filter_type: select`, perdendo o `filterType` original e atributos como `enableSingleValue`, `cascadeParentIds` e `controlValues`.
- O campo `query_context` dos charts não aparecia no YAML.

Rodar com `--safe` ativa três comportamentos no exporter:

| Comportamento | Onde no código |
| --- | --- |
| Grava `query_context_raw` em cada chart | [_export.py:151–156](../src/superset_codec/_export.py#L151-L156) |
| Grava `position_json_raw` em cada dashboard | [_export.py:205–208](../src/superset_codec/_export.py#L205-L208) |
| Grava `_raw` (objeto Superset completo) em filtros cujo `filterType` ∉ `{filter_select, filter_time}` | [_filters.py:141–144](../src/superset_codec/_filters.py#L141-L144) |
| Logs de warning em erros por recurso ao invés de abortar | [_export.py:104, 129, 167, 216](../src/superset_codec/_export.py#L104) |

A decisão foi acionar `--safe` deliberadamente, mesmo sem disparo automático, porque os campos `_raw` cobrem perdas reais identificadas na auditoria e o custo é apenas o aumento de tamanho do output (de 145 KB para 370 KB total).

---

## 3. Resultados Consolidados

| Artefato | Esperado | Exportado | Geração | Validação por roundtrip |
|----------|----------|-----------|---------|-------------------------|
| Databases | 1 | 1 | OK | n/a |
| Datasets | 1 | 1 | OK | n/a |
| Charts | 48 | 48 | OK | 48/48 query OK |
| Dashboards | 9 | 9 | OK | n/a |
| Filtros nativos | 29 | 29 | OK | n/a |
| Arquivos YAML | — | 59 | OK | — |

Tempo de execução não foi cronometrado.

---

## 4. Distribuição de Charts por Categoria

Categorização alinhada com §3 do [catalogo-instancia-teste-v1.md](catalogo-instancia-teste-v1.md). `time_table` aparece em "Séries Temporais (outros)"; `bullet` aparece em "Outros" (comparação contra meta); `generic_chart` corresponde a `echarts_timeseries` e entra em "Séries Temporais (ECharts)".

| Categoria | Qtd. | viz_types |
|---|---|---|
| Séries Temporais (ECharts) | 8 | `echarts_area`, `echarts_timeseries_bar`, `echarts_timeseries_line`, `echarts_timeseries_scatter`, `echarts_timeseries_smooth`, `echarts_timeseries_step`, `echarts_timeseries` (Generic), `mixed_timeseries` |
| Séries Temporais (outros) | 5 | `compare`, `time_pivot`, `time_table`, `horizon`, `cal_heatmap` |
| Distribuição | 3 | `box_plot`, `histogram_v2`, `heatmap_v2` |
| Composição parte/todo | 6 | `pie`, `treemap_v2`, `sunburst_v2`, `partition`, `funnel`, `rose` |
| Geoespacial (base) | 3 | `country_map`, `world_map`, `mapbox` |
| Geoespacial (deck.gl) | 7 | `deck_arc`, `deck_contour`, `deck_geojson`, `deck_heatmap`, `deck_multi`, `deck_scatter`, `deck_screengrid` |
| Multivariado | 4 | `radar`, `bubble_v2`, `bubble`, `para` |
| Fluxo/Rede | 3 | `sankey_v2`, `chord`, `graph_chart` |
| Tabulares | 2 | `table`, `pivot_table_v2` |
| KPI | 2 | `big_number_total`, `big_number` |
| Outros | 5 | `gauge_chart`, `bullet`, `word_cloud`, `cartodiagram`, `waterfall` |
| **Total** | **48** | — |

Cobertura sobre o catálogo do Superset 6.1: 48 dos 56 `viz_type` efetivamente disponíveis na UI (85,7 %). Os 8 ausentes estão documentados em §2 do catálogo.

---

## 5. Distribuição de Dashboards

Contagens verificadas por inspeção direta dos YAMLs em [examples/export/dashboards/](export/dashboards/).

| Dashboard | Charts | Filtros nativos |
| --- | --- | --- |
| `correlation` | 4 | 29 |
| `distribution` | 3 | 29 |
| `evolution` | 11 | 29 |
| `flow` | 3 | 29 |
| `kpi` | 5 | 29 |
| `map` | 11 | 29 |
| `part-of-a-whole` | 4 | 29 |
| `ranking` | 4 | 29 |
| `table` | 3 | 29 |
| **Total** | **48** | **29 configurações replicadas em cada dashboard** |

Cada dashboard armazena o mesmo conjunto de 29 entradas de filtros nativos (não são 261 configurações independentes).

---

## 6. Filtros Nativos

### 6.1 Composição por `filterType` da origem

| `filterType` | Quantidade | Coluna-alvo |
| --- | --- | --- |
| `filter_select` | 10 | `destination_country`, `airline`, `origin_municipality`, `origin_name`, `origin_country`, `ticket_single_or_return`, `travel_class` |
| `filter_range` | 8 | `cost` |
| `filter_timecolumn` | 4 | — (coluna temporal do dataset) |
| `filter_timegrain` | 4 | — (granularidade temporal) |
| `filter_time` | 3 | — (intervalo temporal global) |
| **Total** | **29** | — |

### 6.2 Atributos da UI — preservação no YAML

| Recurso da UI | Configurado na origem | Preservação no YAML em modo `--safe` |
| --- | --- | --- |
| Default value | 10 filtros | Sim — campo `default_value` |
| Multi-select | filter_select (padrão) | Sim — campo `multi_select` |
| Single-select | 1 filtro (08) | Sim — `multi_select: false` |
| Cascata (`cascadeParentIds`) | 2 filtros (02, 13) | Filtro 13 é `filter_range` → preservado via `_raw`; filtro 02 é `filter_select` → **perdido** |
| Pre-filter (`adhocFilters`) | 2 filtros (03, 14) | Filtro 14 é `filter_range` → preservado via `_raw`; filtro 03 é `filter_select` → **perdido** |
| Required (`enableEmptyFilter`) | 5 filtros (06, 19, 24, 29, 33) | 4 deles em range/time-column/time-grain → preservados via `_raw`; filtro 06 é `filter_select` → **perdido** |
| Sort ascending (`sortAscending`) | 3 filtros (04, 22, 27) | 2 em time-column/time-grain → preservados via `_raw`; filtro 04 é `filter_select` → **perdido** |
| Select first item (`defaultToFirstItem`) | 1 filtro (07) | `filter_select` → **perdido** |
| Dynamic search (`searchAllOptions`) | 1 filtro (09) | `filter_select` → **perdido** |
| Inverse selection (`inverseSelection`) | 1 filtro (10) | `filter_select` → **perdido** |
| Single-value mode (`enableSingleValue`) | 1 filtro (15) | `filter_range` → preservado via `_raw` |

Em modo `--safe`, os 16 filtros de `filter_range`/`filter_timecolumn`/`filter_timegrain` recebem um bloco `_raw` com o objeto Superset completo (verificado em [examples/export/dashboards/kpi.yaml:95–119](export/dashboards/kpi.yaml#L95)). Os 10 `filter_select` e os 3 `filter_time` não recebem `_raw` porque seus tipos estão em `_KNOWN_FILTER_TYPES` ([_filters.py:12](../src/superset_codec/_filters.py#L12)), e o schema simplificado descarta seus atributos da UI. Esta é a única perda relevante de atributos de filtro que sobreviveu ao `--safe` — registrada como risco em §9.

---

## 7. Estrutura de Saída Gerada

```
examples/export/
├── databases/
│   └── examples.yaml                                       [1 arquivo]
├── datasets/
│   └── tutorial_flights.yaml                               [1 arquivo]
├── charts/                                                 [48 arquivos]
│   ├── area_chart__default_.yaml
│   ├── bar_chart__default_.yaml
│   ├── big_number__default_.yaml
│   ├── big_number_with_trendline___default_.yaml
│   ├── ... (48 arquivos no total — um por slice)
│   └── world_map__default_.yaml
└── dashboards/                                             [9 arquivos]
    ├── correlation.yaml
    ├── distribution.yaml
    ├── evolution.yaml
    ├── flow.yaml
    ├── kpi.yaml
    ├── map.yaml
    ├── part-of-a-whole.yaml
    ├── ranking.yaml
    └── table.yaml
```

| Métrica | Valor | Verificação |
| --- | --- | --- |
| Total de arquivos YAML | 59 | Contagem direta |
| Tamanho total | ~370 KB (377.521 bytes) | `wc -c` somado em todos os YAMLs |

O aumento de ~225 KB vem dos blocos `query_context_raw` (48 charts), `position_json_raw` (9 dashboards) e `_raw` em 144 entradas de filtro (16 por dashboard × 9).

---

## 8. Elementos preservados no YAML

Quadro verificado por inspeção dos YAMLs em [examples/export/](export/). "Preservado" = campo aparece no YAML; "Simplificado" = subset/transformação; "Ausente" = campo da instância não aparece.

### 8.1 Chart

| Elemento | Status | Observação |
|----------|--------|------------|
| `viz_type`, `slice_name`, `datasource_table`, `params` | Preservado | Em todos os 48 charts |
| `query_context` | Preservado via `query_context_raw` | Adicionado pelo `--safe` |
| Referências cruzadas (`params.dashboards`, `params.selected_chart.id`) | Preservado como IDs numéricos | Não resolve em re-apply — ver risco 2 em §9 |
| `description`, `tags`, `owner`, `created_on`, `changed_on` | Ausente | Não exportados pelo schema atual |

### 8.2 Dashboard

| Elemento | Status | Observação |
|----------|--------|------------|
| `dashboard_title`, `slug`, `published` | Preservado | — |
| Lista de charts (referência por `slice_name`) | Preservado | Com `row/col/width/height` reduzidos |
| `position_json` completo (TABS/ROW/COLUMN/HEADER/MARKDOWN/DIVIDER) | Preservado via `position_json_raw` | Adicionado pelo `--safe` |
| `json_metadata`, `description`, `embedding_config`, `refresh_interval`, `cache_timeout` | Ausente | Não exportados pelo schema atual |

### 8.3 Filter

| Elemento | Status | Observação |
|----------|--------|------------|
| `name`, `column`, `dataset` | Preservado | Em todos os 29 filtros |
| `filterType` original | Preservado para 19 filtros | `filter_select` (10) → `select` no YAML; `filter_time` (3) → `date`; `filter_range`/`filter_timecolumn`/`filter_timegrain` (16) → via `_raw` |
| `multi_select`, `default_value` | Preservado | Quando configurados |
| `controlValues`, `cascadeParentIds`, `adhocFilters`, `enableEmptyFilter` | Preservado para 16 filtros via `_raw`; ausente nos 10 `filter_select` | Ver risco 3 em §9 |

### 8.4 Dataset

| Elemento | Status | Observação |
|----------|--------|------------|
| `table_name`, `schema`, `database`, `main_dttm_col`, `filter_select_enabled`, `is_sqllab_view`, `offset`, `sql` | Preservado | 16 linhas no YAML |
| `columns`, `metrics`, calculated columns | Ausente | `--safe` não afeta — ver risco 1 em §9 |

---

## 9. Riscos remanescentes para re-apply

Verificações feitas contra [examples/export/](export/) após execução em `--safe`. Os riscos abaixo **não são detectados** pela validação por roundtrip atual (que testa query na instância de origem).

| # | Risco | Severidade | O que causa | Mitigação no schema |
| --- | --- | --- | --- | --- |
| 1 | Dataset YAML omite colunas físicas e calculated columns | Alta | `--safe` não altera o exporter de dataset; YAML tem só 16 linhas, sem `columns`/`metrics`. Charts que dependem de calculated columns falham em re-apply: `country_map` (`gb_code`), `cartodiagram` (`origin_cartodiagram`), `deck_geojson` (`destination_geojson`) | Estender `_export_datasets` para incluir `columns:` e `metrics:` |
| 2 | `cartodiagram.selected_chart.id` hardcoded | Alta | O JSON serializado em `selected_chart` traz `"id":325` apontando para o Funnel embutido. Em outro Superset, esse ID não existirá. Verificado em [cartodiagram__default_.yaml:34](export/charts/cartodiagram__default_.yaml#L34) | Resolver referência por `slice_name` no apply, reescrevendo o ID numérico |
| 3 | 10 `filter_select` perdem atributos da UI | Média | `filter_select` está em `_KNOWN_FILTER_TYPES` e não recebe `_raw`. Os 10 filtros desta instância demonstram cascade (02), inverse (10), sort (04), search-all (09), required (06), pre-filter (03), default-to-first (07) — todos ausentes do YAML. Mesma situação para os 3 `filter_time` (sem `_raw`) | Incluir `controlValues` na simplificação de [_filters.py:127–139](../src/superset_codec/_filters.py#L127-L139), ou remover `filter_select` de `_KNOWN_FILTER_TYPES` |
| 4 | Country Map (UK) — granularidade do TopoJSON | Baixa | O plugin embute TopoJSON a nível de county/local authority; o YAML expõe `entity: gb_code` corretamente, mas o mapa só renderiza regiões cujo código bata com o nível embutido. Bloqueio é do plugin, não do codec | Substituir o TopoJSON embutido no plugin |
| 5 | Roundtrip valida query, não rendering | Baixa | Bugs de plugin/shader que falham em mount não são detectados pela validação atual (ver §2/§5.3 do catálogo) | Validação em ambiente separado (ver §10) |

Riscos cobertos pelo `--safe` desta execução:

- **`filter_range`/`filter_timecolumn`/`filter_timegrain` colapsados em `select`** → resolvido via `_raw` para 16 dos 29 filtros (verificado em [kpi.yaml:95–119](export/dashboards/kpi.yaml#L95)).
- **`position_json` reduzido** → resolvido via `position_json_raw` (verificado em [kpi.yaml:600](export/dashboards/kpi.yaml#L600)).
- **`query_context` ausente** → resolvido via `query_context_raw` em todos os 48 charts.

---

## 10. Próximas Etapas

### 10.1 Validação em ambiente separado

```bash
# Em um Superset limpo (dev/staging)
superset-codec apply ./examples/export \
  --url http://localhost:9090 \
  --user admin \
  --password admin
```

Resultado nominal esperado: 1 database, 1 dataset, 48 charts, 9 dashboards e 29 entradas de filtro por dashboard. Falhas previstas pelos riscos remanescentes (§9): `country_map`, `cartodiagram` e `deck_geojson` por dependência de calculated columns ausentes do dataset YAML; os 10 `filter_select` reconstruídos sem `cascadeParentIds`/`inverseSelection`/`sortAscending`/`searchAllOptions`/`defaultToFirstItem`/`enableEmptyFilter`/`adhocFilters`.

### 10.2 Testes de conformidade pós-apply

| Teste | Comando | Critério de sucesso |
|-------|---------|---------------------|
| Contar charts | `curl .../api/v1/chart?page_size=1000` | 48 charts |
| Contar dashboards | `curl .../api/v1/dashboard?page_size=100` | 9 dashboards |
| Validar filtros | `curl .../api/v1/dashboard/{id}` | `native_filter_configuration` com 29 entradas |
| Renderização | Abrir cada chart na UI | Detectar falhas previstas em §9 (riscos 1, 2, 4) |

---

## 11. Conclusões

**Execução:** export concluído em modo `--safe`, gerando 59 YAMLs (~370 KB) com 48/48 charts validados por roundtrip de query.

**O que o `--safe` resolveu nesta execução:** `query_context_raw` em todos os charts, `position_json_raw` em todos os dashboards, e `_raw` em 16 dos 29 filtros (range, time-column, time-grain). Estes três pontos eram perdas silenciosas do export padrão.

**O que continua sendo risco para re-apply:** o dataset YAML omite colunas e calculated columns (afeta `country_map`, `cartodiagram`, `deck_geojson`); o `cartodiagram` carrega `slice_id: 325` hardcoded; e 10 `filter_select` perdem `controlValues`/`cascadeParentIds`/`adhocFilters` por estarem em `_KNOWN_FILTER_TYPES`. Estes três riscos pedem evolução do schema — não são resolvíveis por flags da CLI atual.

**Recomendação:** validar o ciclo `apply` em um Superset limpo separado antes de usar o export como mecanismo de sincronização entre ambientes. Os riscos 1, 2 e 3 da §9 devem ser tratados em iterações futuras do schema.

---

**Relatório preparado em:** 22 de maio de 2026
**Ferramenta:** superset-codec v0.1.0
**Superset alvo:** 6.1.0
