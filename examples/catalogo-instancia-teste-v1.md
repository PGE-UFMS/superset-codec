# Catálogo da Instância de Teste

Este documento descreve um conjunto completo de recursos criado para testar e validar a ferramenta **superset-codec**. A instância funciona como catálogo exemplar do Superset 6.1, com 48 charts pré-configurados, 9 dashboards temáticos e 29 filtros nativos exercitando todos os recursos de configuração disponíveis. Serve como base de testes para exportação, importação e transformação de artefatos do Superset.

> Fonte primária: API REST do Superset (`/api/v1/chart`, `/api/v1/dashboard`) interrogada na instância local. Fontes secundárias: arquivos do projeto (`Dockerfile`, `docker-compose.yml`, `tutorial_flights.csv`). Diagnósticos de bugs específicos referenciam issues públicas e documentação oficial linkadas ao longo do texto.

## 1. Resumo dos Gráficos Existentes

A instância foi concebida como **catálogo exemplar**: um slice por tipo de chart suportado pelo Superset, configurado sobre o dataset `main.tutorial_flights`. Contém **48 charts**, com sufixo `[Default]` predominante nos nomes e uma única variação nomeada (`[Custom Cell-Thresholds]`, em `deck_contour`, refletindo ajuste manual de Cell Size/Thresholds). Repetição de domínio analítico entre charts não é incidente: faz parte do propósito documental.

> A coluna "Configurações principais" descreve as configurações **típicas exigidas pelo tipo de chart**.

### 1.1 Quadro consolidado dos 48 charts

| viz_type | Nome do slice | Configurações principais (do tipo) | Finalidade analítica | Observação |
|---|---|---|---|---|
| `big_number` | Big Number with Trendline [Default] | Métrica única + dimensão temporal | KPI com tendência | — |
| `big_number_total` | Big Number [Default] | Métrica única | KPI estático | — |
| `box_plot` | Box Plot [Default] | Dimensão + métrica numérica | Distribuição/outliers | — |
| `bubble` | Bubble Chart (legacy) [Default] | Eixos X/Y + tamanho + grupo | Correlação trivariada | Tipo marcado como legacy |
| `bubble_v2` | Bubble Chart [Default] | Idem `bubble`, versão atualizada | Correlação trivariada | — |
| `bullet` | Bullet [Default] | Valor + alvo + faixas | Comparação contra meta | — |
| `cal_heatmap` | Calendar Heatmap [Default] | Data + métrica | Padrão sazonal diário | — |
| `cartodiagram` | Cartodiagram [Default] | Coluna com GeoJSON Point + chart embutido | Mini-charts em coordenadas geográficas | Exige calculated column `origin_geojson` no dataset (CSV não tem coluna de geometria); chart embutido renderizado em cada ponto |
| `chord` | Chord Diagram [Default] | Origem-destino-magnitude | Fluxo bilateral | — |
| `compare` | Time-series Percent Change [Default] | Métrica temporal | Variação percentual | — |
| `country_map` | Country Map [Default] | País + código ISO 3166-2 + métrica | Coropleto subnacional | UK; mapa do Superset usa códigos a nível de county/local authority, não nação |
| `deck_arc` | deck.gl Arc [Default] | Origem (lat/lng) + destino (lat/lng) + métrica | Fluxos georreferenciados | — |
| `deck_contour` | deck.gl Contour [Custom Cell-Thresholds] | lat/lng + agregação; Cell Size + thresholds | Isolinhas de densidade | Cell Size/Thresholds ajustados manualmente (não default) |
| `deck_geojson` | deck.gl GeoJson [Default] | Coluna com `Feature`/`FeatureCollection` | Renderização vetorial customizada | Exige wrapping em `Feature` (não aceita `Polygon`/`Point` cru — issue [#33618](https://github.com/apache/superset/issues/33618)) |
| `deck_heatmap` | deck.gl Heatmap [Default] | lat/lng + métrica de intensidade | Densidade contínua | — |
| `deck_multi` | deck.gl Multiple Layers [Default] | Composição de sub-layers | Múltiplas camadas geográficas | — |
| `deck_scatter` | deck.gl Scatterplot [Default] | lat/lng + métrica (tamanho) | Pontos georreferenciados | — |
| `deck_screengrid` | deck.gl Screengrid [Default] | lat/lng + agregação em grid de pixels | Densidade independente de zoom | — |
| `echarts_area` | Area Chart [Default] | Eixo X temporal + métrica + grupo | Evolução temporal acumulada | — |
| `echarts_timeseries` | Generic Chart [Default] | Idem timeseries; tipo agnóstico | Evolução temporal genérica | — |
| `echarts_timeseries_bar` | Bar Chart [Default] | Idem timeseries com barras | Evolução temporal categorizada | — |
| `echarts_timeseries_line` | Line Chart [Default] | Idem timeseries com linhas | Evolução temporal contínua | — |
| `echarts_timeseries_scatter` | Scatter Plot [Default] | Eixos X/Y + grupo | Correlação ou dispersão | — |
| `echarts_timeseries_smooth` | Smooth Line [Default] | Linha suavizada | Tendência sem ruído | — |
| `echarts_timeseries_step` | Stepped Line [Default] | Linha escalonada | Estados discretos no tempo | — |
| `funnel` | Funnel Chart [Default] | Estágios ordenados + métrica | Conversão sequencial | — |
| `gauge_chart` | Gauge Chart [Default] | Valor + faixas | Status pontual | — |
| `graph_chart` | Graph Chart [Default] | Nó origem-destino-peso | Topologia de rede | — |
| `heatmap_v2` | Heatmap [Default] | 2 dimensões × métrica | Densidade em matriz | — |
| `histogram_v2` | Histogram [Default] | Métrica numérica + bins | Distribuição univariada | — |
| `horizon` | Horizon Chart [Default] | Séries temporais compactadas | Comparação densa de séries | — |
| `mapbox` | MapBox [Default] | lat/lng + agregação | Mapa de pontos | — |
| `mixed_timeseries` | Mixed Chart [Default] | Eixo Y duplo | Métricas em escalas distintas | — |
| `para` | Parallel Coordinates [Default] | N dimensões | Multivariado | — |
| `partition` | Partition Chart [Default] | Hierarquia + métrica | Composição hierárquica | — |
| `pie` | Pie Chart [Default] | Dimensão + métrica | Composição parte/todo | — |
| `pivot_table_v2` | Pivot Table [Default] | Linhas × colunas × métricas | Tabulação cruzada | — |
| `radar` | Radar Chart [Default] | N dimensões em escala polar | Comparação multidimensional | — |
| `rose` | Nightingale Rose Chart [Default] | Setores angulares × magnitude | Composição cíclica | — |
| `sankey_v2` | Sankey Chart [Default] | Origem → destino → fluxo | Fluxo unidirecional | — |
| `sunburst_v2` | Sunburst Chart [Default] | Hierarquia em coroas | Composição hierárquica radial | — |
| `table` | Table [Default] | Colunas brutas ou agregadas | Visualização tabular | — |
| `time_pivot` | Time-series Period Pivot [Default] | 2 eixos de tempo × métrica | Sazonalidade comparada | — |
| `time_table` | Time-series Table [Default] | Métricas × tempo (sparkline por linha) | Painel de KPIs temporais | — |
| `treemap_v2` | Treemap [Default] | Hierarquia + métrica (área) | Composição hierárquica | — |
| `waterfall` | Waterfall Chart [Default] | Variações entre estágios | Decomposição de variação | — |
| `word_cloud` | Word Cloud [Default] | Coluna de texto + frequência | Frequência lexical | — |
| `world_map` | World Map [Default] | ISO 3166-1 alpha-2 + métrica | Coropleto global | — |

### 1.2 Filtros nativos aplicados

Os 48 charts listados acima estão distribuídos em 9 dashboards (`Map`, `Part of a Whole`, `Flow`, `KPI`, `Distribuição`, `Evolution`, `Ranking`, `Table`, `Correlation`). Todos os 9 compartilham `main.tutorial_flights` como dataset. Os dashboards foram configurados com **29 entradas no `native_filter_configuration`**. A configuração detalhada de cada filtro está em §4.

| Grupo de filtro | Tipo (`filterType`) | Filtros | Colunas-alvo |
| --- | --- | --- | --- |
| Value | `filter_select` | 10 | `destination_country`, `origin_country`, `origin_municipality`, `origin_name`, `airline`, `travel_class`, `ticket_single_or_return` |
| Numerical range | `filter_range` | 8 | `cost` |
| Time column | `filter_timecolumn` | 4 | — (aplica-se ao temporal column do dataset) |
| Time grain | `filter_timegrain` | 4 | — (granularidade temporal) |
| Time range | `filter_time` | 3 | — (intervalo temporal) |

### 1.3 Elementos de layout não cobertos pelo catálogo

O catálogo testa o **conteúdo** dos dashboards (charts e filtros nativos), não a **estrutura visual** da página. Os elementos de layout do Superset 6.1 e o estado nesta instância são:

| Elemento | Função no Superset | Estado nesta instância |
| --- | --- | --- |
| `HEADER` | Cabeçalhos de seção dentro do dashboard | Não configurado |
| `TABS` / `TAB` | Abas para segmentar conteúdo do dashboard | Não configurado |
| `ROW` / `COLUMN` | Containers de linha e coluna no `position_json` | Não configurado (charts em grade flat) |
| `MARKDOWN` | Caixas de texto Markdown como elementos do dashboard | Não configurado |
| `DIVIDER` (filtros nativos) | Separadores visuais para agrupar filtros na sidebar | Não configurados |

Os 9 dashboards usam disposição flat: cada chart ocupa uma célula `row/col` na grade, sem tabs, sem markdown, sem cabeçalhos e sem dividers entre filtros. Esses elementos não foram exercitados e portanto a fidelidade do ciclo export/apply em relação ao layout **não está validada** por este catálogo.

---

## 2. Análise de Ausência de Gráficos

> Os gráficos abaixo **não foram configurados** na montagem do catálogo. Como o critério desta instância é "um exemplar por tipo", a ausência reflete bloqueios concretos: incompatibilidade entre o que o tipo exige e o que o dataset `tutorial_flights` oferece, ou bugs do Superset/deck.gl que impediram a renderização. Para cada chart, registra-se: (i) o que o tipo exige; (ii) o motivo factual pelo qual não foi possível configurá-lo.

### 2.1 Paired t-test Table

| Aspecto | Conteúdo |
|---|---|
| Exigência | Duas amostras pareadas — mesma unidade observacional em duas condições/tempos |
| Uso típico | Validação estatística de variação intra-grupo |
| Motivo da ausência | `tutorial_flights` registra cada voo como observação independente (verificado nos cabeçalhos do CSV); não há campo que estabeleça pareamento entre observações. Sem definição operacional de "par", o teste não é aplicável ao dataset no seu estado atual |

### 2.2 Gantt Chart

| Aspecto | Conteúdo |
|---|---|
| Exigência | Identificador de tarefa + timestamp de início + timestamp de fim (ou duração) |
| Uso típico | Cronograma de atividades discretas com sobreposição temporal |
| Motivo da ausência | O CSV contém apenas `travel_date` como campo temporal — uma única data por voo. Inexiste no dataset o conceito de **intervalo** (início ≠ fim), que é estrutural para o chart |

### 2.3 Tree Chart

| Aspecto | Conteúdo |
|---|---|
| Exigência | Relação hierárquica explícita (auto-relacionamento `parent_id` → `id`, ou níveis predefinidos) |
| Uso típico | Organogramas, taxonomias, árvores de decisão |
| Motivo da ausência | O CSV não contém coluna de auto-relacionamento (`parent_id` apontando para `id`) nem qualquer outro campo que estabeleça relação hierárquica explícita entre linhas. As hierarquias categóricas derivadas (`country → region → municipality → ICAO`) caracterizam **dimensões aninhadas**, não estrutura de árvore com nós internos próprios, de modo que não satisfazem o formato de entrada que o tipo `tree_chart` exige |

### 2.4 deck.gl Path

| Aspecto | Conteúdo |
|---|---|
| Exigência | Uma coluna por linha contendo a trajetória completa como array `[[lng,lat],...]` ou polyline codificada |
| Uso típico | Rotas, segmentos lineares georreferenciados |
| Motivo da ausência | O dataset oferece origem e destino em colunas separadas, não como geometria de linha consolidada. A síntese da geometria via `printf('[[%f,%f],[%f,%f]]', ...)` (como calculated column ou em virtual dataset) produz strings válidas no SQL Lab, mas a renderização falha com `@math.gl/web-mercator: assertion failed — Could not fit viewport`. A lógica de auto-fit do chart na versão 6.1 do Superset depende da presença de colunas `latitude`/`longitude` no resultset, ausentes quando apenas a geometria de linha é projetada (ver [PathLayer docs](https://deck.gl/docs/api-reference/layers/path-layer)) |

### 2.5 deck.gl 3D Hexagon

| Aspecto | Conteúdo |
|---|---|
| Exigência | lat/lng + agregação volumétrica em células hexagonais; renderização inerentemente extrudada (3D é o valor distintivo do tipo) |
| Uso típico | Densidade espacial 3D em hotspots |
| Motivo da ausência | O shader `column-layer-fragment-shader`, compartilhado pela `HexagonLayer` em modo extrudado, referencia a função `lighting_getLightColor` dentro do bloco `#ifdef FLAT_SHADING`. Essa função não está definida no módulo de iluminação injetado pela versão 9.x do deck.gl (issue [#9700](https://github.com/visgl/deck.gl/issues/9700), aberta em 07/2025, sem fix nas séries 9.1.x e 9.2.x). Como `FLAT_SHADING` é definido em **tempo de compilação** quando o material/lighting do layer está habilitado — default na [`HexagonLayer`](https://deck.gl/docs/api-reference/aggregation-layers/hexagon-layer) — a compilação falha em tempo de mount; o teste `if (column.extruded ...)` no shader é runtime e nunca chega a ser avaliado |

### 2.6 deck.gl Grid

| Aspecto | Conteúdo |
|---|---|
| Exigência | lat/lng + agregação em grade quadrada; renderização via `GridCellLayer`, que herda o pipeline de iluminação da `ColumnLayer` |
| Uso típico | Discretização de densidade espacial em células regulares no plano geográfico |
| Motivo da ausência | Mesmo bug do shader registrado em §2.5: a [`GridCellLayer`](https://deck.gl/docs/api-reference/layers/grid-cell-layer) compila o `column-layer-fragment-shader` com `FLAT_SHADING` definido sempre que material/lighting está ativo (default). O toggle "Extruded" da UI **não evita** o erro, pois o bloco problemático é selecionado em tempo de compilação (diretiva `#ifdef`), antes de qualquer avaliação de uniforms em runtime. A UI do Superset 6.1 não expõe controle direto para desabilitar o módulo de iluminação do layer, inviabilizando o caminho de configuração dentro da interface |

### 2.7 deck.gl Polygon

| Aspecto | Conteúdo |
|---|---|
| Exigência | Coluna com geometria de polígono (array fechado de coordenadas ou GeoJSON `Polygon`/`MultiPolygon`) por linha |
| Uso típico | Coropleto sobre fronteiras customizadas, áreas de cobertura |
| Motivo da ausência | Razão primária — estrutural: `tutorial_flights` contém apenas pares de coordenadas pontuais (origem e destino), não geometrias de polígono. Diferente do caso do `deck_path` (em que a linha pôde ser sintetizada via `printf`), não há combinação plausível das colunas existentes que produza polígonos válidos para fins de visualização. Limitações secundárias agravantes, caso polígonos sintéticos fossem providos: (i) regressão de stroke color em Superset 6.0 (issue [#36326](https://github.com/apache/superset/issues/36326)); (ii) com extrusão habilitada, o mesmo bug de shader documentado em 2.5 |

### 2.8 Plugins gated por feature flag — `pop_kpi` e `ag-grid-table`

| Aspecto | Conteúdo |
|---|---|
| Tipos afetados | `pop_kpi` (Big Number Period over Period) e `ag-grid-table` (Table baseada em ag-Grid) |
| Comportamento observado na UI | Não aparecem no chart picker do Superset, apesar de presentes nos enums e bundles JS |
| Motivo da ausência | Registro condicional em [`MainPreset.ts`](https://github.com/apache/superset/blob/6.1.0/superset-frontend/src/visualizations/presets/MainPreset.ts) gated pelos feature flags `CHART_PLUGINS_EXPERIMENTAL` (para `pop_kpi`) e `AG_GRID_TABLE_ENABLED` (para `ag-grid-table`). Os blocos de instanciação retornam array vazio quando a flag está desligada: `isFeatureEnabled(FeatureFlag.ChartPluginsExperimental) ? [new BigNumberPeriodOverPeriodChartPlugin().configure({...})] : []` e equivalente para ag-Grid |
| Estado das flags nesta instância | Ambos `False` (default do Superset 6.1). [`superset/superset_config.py`](superset/superset_config.py) define apenas `ENABLE_TEMPLATE_PROCESSING=True` e `PRESTO_EXPAND_DATA=False` |
| Mitigação possível | Adicionar `'CHART_PLUGINS_EXPERIMENTAL': True` e/ou `'AG_GRID_TABLE_ENABLED': True` ao `FEATURE_FLAGS` em [`superset/superset_config.py`](superset/superset_config.py) e reiniciar o container. Não foi aplicado nesta instância para manter fidelidade ao estado vanilla de uma instalação oficial Superset 6.1 |

### 2.9 Handlebars — bloqueio por CSP

| Aspecto | Conteúdo |
|---|---|
| Exigência | Template Handlebars que é compilado em runtime via `new Function(...)` / `eval` |
| Uso típico | Renderização customizada de qualquer query como HTML arbitrário |
| Motivo da ausência | Plugin registrado e visível na UI, mas a renderização falha com erro de CSP: `Evaluating a string as JavaScript violates the following Content Security Policy directive because 'unsafe-eval' is not an allowed source of script`. O `TALISMAN_CONFIG` default do Superset 6.1 ([superset/config.py:2152](https://github.com/apache/superset/blob/6.1.0/superset/config.py#L2152)) define `"script-src": ["'self'", "'strict-dynamic'"]` — sem `'unsafe-eval'`. Issue rastreada em [apache/superset#30607](https://github.com/apache/superset/issues/30607) |
| Mitigação possível | Override em `superset_config.py` adicionando `'unsafe-eval'` ao `script-src` do `TALISMAN_CONFIG`. Não foi aplicado: a CSP strict é o estado vanilla do Superset 6.1 oficial; relaxá-la enfraqueceria a proteção contra XSS globalmente |

---

## 3. Comparação: Implementado vs Potencial do Superset

### 3.1 Cobertura por categoria

| Categoria | Charts no inventário | Tipos de chart relacionados disponíveis no Superset 6.1 |
|---|---|---|
| KPI | `big_number`, `big_number_total` | mesmos |
| Séries temporais (ECharts) | 8 variantes | mesmos + `compare`, `time_pivot`, `time_table` (também presentes) |
| Tabulares | `table`, `pivot_table_v2`, `time_table` | mesmos |
| Distribuição | `box_plot`, `histogram_v2`, `heatmap_v2` | mesmos |
| Composição parte/todo | `pie`, `treemap_v2`, `sunburst_v2`, `partition`, `funnel` (×2), `rose` | + `tree_chart` (ausente, ver §2.3) |
| Multivariado | `radar`, `para`, `bubble`, `bubble_v2` | mesmos |
| Fluxo/Rede | `sankey_v2`, `chord`, `graph_chart` | mesmos |
| Geoespacial base | `country_map`, `world_map`, `mapbox` | mesmos |
| Geoespacial deck.gl | 7 tipos (`arc`, `contour`, `geojson`, `heatmap`, `multi`, `scatter`, `screengrid`) | + `deck_path`, `deck_hex`, `deck_grid`, `deck_polygon` (ausentes) |
| Estatística inferencial | — | `paired_ttest` (ausente, ver §2.1) |
| Cronograma | — | `gantt_chart` (legacy, ausente, ver §2.2) |

### 3.2 Comparação por complexidade analítica

| Eixo analítico | Implementado | Lacuna identificada |
|---|---|---|
| Univariado | `histogram_v2`, `box_plot`, `big_number*` | — |
| Bivariado | `echarts_timeseries_scatter`, `heatmap_v2`, `bubble*` | — |
| Multivariado | `para`, `radar`, `bubble_v2` | — |
| Temporal | 8 timeseries + `compare`, `time_pivot`, `time_table`, `cal_heatmap`, `horizon` | — |
| Geoespacial 2D | `country_map`, `world_map`, `mapbox`, `deck_scatter`, `deck_heatmap`, `deck_screengrid`, `deck_contour`, `deck_arc`, `deck_geojson` | `deck_grid` ausente — bug de shader bloqueia compilação mesmo em modo 2D quando lighting/material está habilitado (ver §2.6) |
| Geoespacial 3D (extrudado) | nenhum | deck.gl 9.x bloqueia compilação do shader em Column/Hexagon/Grid/Polygon quando `FLAT_SHADING` é definido (ver §2.5–2.7) |
| Trajetórias georreferenciadas | nenhum | `deck_path` bloqueado por auto-fit (ver §2.4) |
| Hierárquico (auto-rel) | nenhum | `tree_chart` ausente — dataset não possui coluna de auto-relacionamento `parent_id` → `id` (ver §2.3) |
| Inferência estatística | nenhum | `paired_ttest` requer pareamento ausente no dataset |
| Cronograma | nenhum | `gantt` requer dois timestamps por registro |

### 3.3 Dependência de dados — viabilidade por chart ausente

| Chart ausente | Coluna(s) necessária(s) | Disponibilidade em `tutorial_flights` |
|---|---|---|
| paired t-test | par identificador + 2 observações da mesma unidade | Ausente |
| Gantt | id + início + fim | Apenas `travel_date` (um único timestamp) |
| Tree | `parent_id` referenciando `id` | Ausente |
| deck.gl Path | trajetória em coluna única | Construtível via calculated column (`origin_long/lat` + `destination_long/lat`); bloqueio é de renderização, não de dado |
| deck.gl 3D Hexagon | lat/lng + métrica | Dado disponível; bloqueio é de shader (compilação falha em mount) |
| deck.gl Grid | lat/lng + métrica | Dado disponível; bloqueio é de shader (compilação falha mesmo em 2D quando lighting/material está ativo, default no Superset 6.1) |
| deck.gl Polygon | geometria de polígono | Ausente — CSV não contém polígonos nem permite síntese plausível a partir de pontos |

### 3.4 Cobertura numérica — instância vs. catálogo Superset 6.1

> Fonte: enumeração dos plugins registrados no bundle frontend desta instância (47 plugins não-deck + 11 plugins deck.gl = **58 tipos no código fonte**), confrontada com o registro condicional em [`MainPreset.ts`](https://github.com/apache/superset/blob/6.1.0/superset-frontend/src/visualizations/presets/MainPreset.ts) (2 tipos gated por feature flag desligada → **56 tipos efetivamente disponíveis na UI**) e com os 48 `viz_type` distintos retornados por `/api/v1/chart/?q=(page_size:200)`.

#### 3.4.1 Totais

| Métrica | Valor |
|---|---|
| Tipos de chart registrados no código fonte do Superset 6.1 | 58 |
| Tipos gated por feature flag desligada (não aparecem na UI) | 2 (`pop_kpi`, `ag-grid-table` — ver §2.8) |
| Tipos efetivamente disponíveis na UI (sem alterar feature flags) | 56 |
| Tipos implementados nesta instância | 48 |
| Cobertura sobre catálogo efetivo (UI) | 48 / 56 = 85,7 % |
| Cobertura sobre catálogo total (código) | 48 / 58 = 82,8 % |
| Tipos ausentes na UI atual e documentados em §2 | 8 (§2.1–§2.7 + §2.9) |

#### 3.4.2 Cobertura por categoria

> Coluna "Disponíveis (UI)" exclui plugins gated por feature flag; coluna "Disponíveis (código)" mantém o total registrado no código fonte. As porcentagens usam o catálogo efetivo (UI).

| Categoria | Implementados | Disponíveis (UI) | Disponíveis (código) | Cobertura | Ausentes |
| --- | --- | --- | --- | --- | --- |
| KPI | 2 | 2 | 3 | 100 % | — (`pop_kpi` gated) |
| Séries temporais ECharts | 8 | 8 | 8 | 100 % | — |
| Séries temporais (outros) | 5 | 5 | 5 | 100 % | — |
| Tabular | 2 | 2 | 3 | 100 % | — (`ag-grid-table` gated) |
| Distribuição | 3 | 3 | 3 | 100 % | — |
| Composição parte/todo | 6 | 7 | 7 | 85,7 % | `tree_chart` |
| Multivariado | 4 | 4 | 4 | 100 % | — |
| Fluxo/Rede | 3 | 3 | 3 | 100 % | — |
| Geoespacial base | 4 | 4 | 4 | 100 % | — |
| Geoespacial deck.gl | 7 | 11 | 11 | 63,6 % | `deck_grid`, `deck_hex`, `deck_path`, `deck_polygon` |
| Estatística inferencial | 0 | 1 | 1 | 0 % | `paired_ttest` |
| Cronograma | 0 | 1 | 1 | 0 % | `gantt_chart` |
| Outros (gauge, bullet, word cloud, waterfall, handlebars) | 4 | 5 | 5 | 80,0 % | `handlebars` |
| **Total** | **48** | **56** | **58** | **85,7 %** | 8 tipos na UI |

#### 3.4.3 Lista completa dos tipos ausentes

| `viz_type` | Categoria | Visível na UI? | Estado |
| --- | --- | --- | --- |
| `paired_ttest` | Estatística | Sim | Bloqueio estrutural — §2.1 |
| `gantt_chart` | Cronograma | Sim | Bloqueio estrutural — §2.2 |
| `tree_chart` | Composição | Sim | Bloqueio estrutural — §2.3 |
| `deck_path` | Geoespacial deck.gl | Sim | Bloqueio de auto-fit do viewport — §2.4 |
| `deck_hex` | Geoespacial deck.gl | Sim | Bug de shader deck.gl 9.x — §2.5 |
| `deck_grid` | Geoespacial deck.gl | Sim | Bug de shader deck.gl 9.x — §2.6 |
| `deck_polygon` | Geoespacial deck.gl | Sim | Bloqueio estrutural + shader em extrusão — §2.7 |
| `handlebars` | Outros | Sim | Bloqueio por CSP — §2.9 |
| `pop_kpi` | KPI | **Não** | Gated por `CHART_PLUGINS_EXPERIMENTAL=False` — §2.8 |
| `ag-grid-table` | Tabular | **Não** | Gated por `AG_GRID_TABLE_ENABLED=False` — §2.8 |

---

## 4. Catálogo de Filtros Nativos Configurados

### 4.1 Estrutura e totais

| Métrica | Valor |
| --- | --- |
| Entradas em `native_filter_configuration` | 29 |
| Filtros ativos | 29 |
| Tipos de filtro (`filterType`) cobertos | 5 de 5 do Superset 6.1 (100 %) |
| Datasets-alvo | 1 (`main.tutorial_flights`, id=44) |

| `filterType` | Quantidade | Colunas-alvo |
| --- | --- | --- |
| `filter_select` | 10 | `destination_country`, `airline`, `origin_municipality`, `origin_name`, `origin_country`, `ticket_single_or_return`, `travel_class` |
| `filter_range` | 8 | `cost` |
| `filter_timecolumn` | 4 | — (escolhe a coluna temporal do dataset) |
| `filter_timegrain` | 4 | — (escolhe a granularidade) |
| `filter_time` | 3 | — (intervalo temporal global) |

### 4.2 Grupo "Value" — `filter_select` (10 filtros)

| # | Nome do filtro | Coluna-alvo | Recurso demonstrado | Default | Notas |
| --- | --- | --- | --- | --- | --- |
| 01 | `Value [Default]` | `destination_country` | Configuração baseline (multi-select, criável, sem ordenação custom) | — | É o "pai" dos filtros cascata (02 e 13) |
| 02 | `[Value] Values are dependent on other filters` | `airline` | **Cascata**: `cascadeParentIds` aponta para filtro 01; opções de airline filtradas pelo valor de `destination_country` | — | — |
| 03 | `Value [Pre-filter available values]` | `origin_municipality` | **Pre-filter**: `adhocFilters` restringe as opções exibidas no dropdown a `origin_country = 'United Kingdom'` | — | Pre-filter atua sobre as opções listadas, não sobre os dados do chart |
| 04 | `Value [Sort filter values]` | `origin_name` | **Sort ascending**: `controlValues.sortAscending = true` | — | — |
| 05 | `Value [Filter has default value]` | `origin_country` | **Default value** sem `required` | `['United Kingdom']` | — |
| 06 | `Value [Filter value is required]` | `origin_country` | **Required** (`enableEmptyFilter = true`) + default | `['United Kingdom']` | UI bloqueia limpar a seleção |
| 07 | `Value [Select first filter value by default]` | `ticket_single_or_return` | **`defaultToFirstItem = true`** — auto-seleciona o primeiro valor disponível | dinâmico | — |
| 08 | `Value [Can't select multiple values]` | `travel_class` | **Single-select** (`multiSelect = false`) | — | — |
| 09 | `Value [Dynamically search all filter values]` | `airline` | **Search-all** (`searchAllOptions = true`) — busca server-side em cardinalidades altas | — | — |
| 10 | `Value [Inverse selection]` | `destination_country` | **Inverse** (`inverseSelection = true`) — seleção semântica "NOT IN" | — | — |

### 4.3 Grupo "Numerical range" — `filter_range` (8 filtros)

| # | Nome do filtro | Coluna-alvo | Recurso demonstrado | Default | Notas |
| --- | --- | --- | --- | --- | --- |
| 12 | `Numerical range [Default]` | `cost` | Configuração baseline — UI dual-slider | — | — |
| 13 | `Numerical range [Values are dependent on other filters]` | `cost` | **Cascata**: depende de `Value [Default]` (filtro 01); min/max ajustados ao subset filtrado por `destination_country` | — | — |
| 14 | `Numerical range [Pre-filter available values]` | `cost` | **Pre-filter** com `adhocFilters` restringindo a `origin_country = 'United Kingdom'` para o cálculo dos extremos | — | — |
| 15 | `Numerical range [Single Value]` | `cost` | **Single-value mode** (`enableSingleValue = 1`) — UI vira slider único (≤ ou ≥) | — | — |
| 16 | `Numerical range [Range Inputs]` | `cost` | Configuração com inputs numéricos no lugar do slider | — | — |
| 17 | `Numerical range [Slider]` | `cost` | Configuração com slider explicitamente | — | — |
| 18 | `Numerical range [Filter has default value]` | `cost` | **Default value** | `[1, 7969.2]` (min/max do dataset) | — |
| 19 | `Numerical range [Filter value is required]` | `cost` | **Required** + default | `[1, 7969.2]` | — |

### 4.4 Grupo "Time column" — `filter_timecolumn` (4 filtros)

| # | Nome do filtro | Recurso demonstrado | Default | Notas |
| --- | --- | --- | --- | --- |
| 21 | `Time column [Default]` | Configuração baseline — lista todas as colunas temporais do dataset | — | `targets[0].column` é vazio: o filtro atua sobre o dataset, não sobre coluna específica |
| 22 | `Time column [Sort filter values]` | **Sort ascending** | — | — |
| 23 | `Time column [Filter has default value]` | **Default value** | `['travel_date']` | — |
| 24 | `Time column [Filter value is required]` | **Required** + default | `['travel_date']` | — |

### 4.5 Grupo "Time grain" — `filter_timegrain` (4 filtros)

| # | Nome do filtro | Recurso demonstrado | Default | Notas |
| --- | --- | --- | --- | --- |
| 26 | `Time grain [Default]` | Configuração baseline — lista granularidades padrão (`P1D`, `P1W`, `P1M`, `P1Y`…) | — | — |
| 27 | `Time grain [Sort filter values]` | **Sort ascending** | — | — |
| 28 | `Time grain [Filter has default value]` | **Default value** | `['P1Y']` (anual) | — |
| 29 | `Time grain [Filter value is required]` | **Required** + default | `['P1Y']` | — |

### 4.6 Grupo "Time range" — `filter_time` (3 filtros)

| # | Nome do filtro | Recurso demonstrado | Default | Notas |
| --- | --- | --- | --- | --- |
| 31 | `Time range [Default]` | Configuração baseline — seletor de intervalo temporal | — | — |
| 32 | `Time range [Filter has default value]` | **Default value** com timestamp arbitrário no início | `2011-01-01T03:30:09 : 2011-12-31T00:00:00` | — |
| 33 | `Time range [Filter value is required]` | **Required** + default normalizado | `2011-01-01T00:00:00 : 2011-12-31T00:00:00` | — |

### 4.7 Recursos de configuração de filtro cobertos

A instância exercita **todos os recursos de configuração** que o Superset 6.1 expõe na UI de filtros nativos, distribuídos pelos 29 filtros:

| Recurso (UI do Superset) | Campo interno | Demonstrado em |
| --- | --- | --- |
| Filter type | `filterType` | 5 tipos: `filter_select` (10×), `filter_range` (8×), `filter_timecolumn` (4×), `filter_timegrain` (4×), `filter_time` (3×) |
| Target column | `targets[0].column.name` | 7 colunas categóricas + `cost` |
| Default value | `defaultDataMask.filterState.value` | 9 filtros (05, 06, 18, 19, 23, 24, 28, 29, 32, 33 — 10 instâncias) |
| Filter value is required | `controlValues.enableEmptyFilter` | 5 filtros (06, 19, 24, 29, 33) |
| Can't select multiple values | `controlValues.multiSelect = false` | 1 filtro (08) |
| Inverse selection | `controlValues.inverseSelection` | 1 filtro (10) |
| Select first filter value by default | `controlValues.defaultToFirstItem` | 1 filtro (07) |
| Dynamically search all filter values | `controlValues.searchAllOptions` | 1 filtro (09) |
| Sort filter values | `controlValues.sortAscending` | 3 filtros (04, 22, 27) |
| Pre-filter available values | `controlValues.adhocFilters` | 2 filtros (03, 14) |
| Values are dependent on other filters | `cascadeParentIds` | 2 filtros (02, 13) — ambos dependem do filtro 01 |
| Single-value mode (range) | `controlValues.enableSingleValue` | 1 filtro (15) |
| Range input mode | tipo de widget | 1 filtro (16) |
| Slider mode | tipo de widget | 1 filtro (17) |
| Scope (escopo no dashboard) | `scope` | Todos os 29 filtros usam `rootPath: ["ROOT_ID"]` (escopo global) |

### 4.8 Cobertura sobre o catálogo de filtros do Superset 6.1

| Tipo de filtro nativo | Implementado? |
| --- | --- |
| `filter_select` | Sim (10 instâncias, todos os recursos UI) |
| `filter_range` | Sim (8 instâncias, todos os modos: dual-slider, single-value, range inputs) |
| `filter_timecolumn` | Sim (4 instâncias) |
| `filter_timegrain` | Sim (4 instâncias) |
| `filter_time` | Sim (3 instâncias) |
| **Total** | **5 de 5 (100 %)** |

---

## 5. Considerações sobre Filtros — impacto nos charts

### 5.1 Impacto nos charts existentes

| Tipo de filtro | Comportamento esperado nos charts do inventário |
|---|---|
| `filter_select` em colunas categóricas (`destination_country`, `airline`, etc.) | Aplica-se a todos os 47 charts via `WHERE` automático; charts que agregam acima dessa coluna mantêm sua semântica, apenas com cardinalidade reduzida |
| `filter_range` em `cost` | Atua antes da agregação; afeta especialmente charts de distribuição (`box_plot`, `histogram_v2`) e métricas baseadas em SUM/AVG de `cost` |
| `filter_timecolumn` + `filter_time` em `travel_date` | Relevante para 8 timeseries + `cal_heatmap` + `horizon` + `time_pivot` + `time_table`; em charts não-temporais, restringe a amostra mas não altera a estrutura visual |
| `filter_timegrain` | Aplicável apenas a charts que agregam sobre intervalo temporal nativo |

### 5.2 Viabilidade dos charts ausentes sob a configuração atual de filtros

| Chart ausente | Interação esperada com os filtros existentes |
|---|---|
| paired t-test | Filtros podem quebrar pares (uma observação do par é mantida e a outra removida), inviabilizando a inferência |
| Gantt | `filter_time` sobre `travel_date` truncaria intervalos não modelados |
| Tree | Filtros que removem nós internos produziriam folhas órfãs |
| deck.gl Path | `filter_select`/`filter_range` operariam sobre as colunas originais antes do `printf`, portanto compatíveis em princípio; a barreira permanece a do auto-fit (§2.4) |
| deck.gl 3D Hexagon / Polygon extrudado / Grid extrudado | Filtros operacionais, porém o bloqueio é de renderização — independente de filtros |

### 5.3 Limitações estruturais e possibilidades futuras

| Limitação | Origem | Caminho potencial de mitigação |
|---|---|---|
| Bug de shader em extrusão deck.gl | deck.gl 9.x — issue [#9700](https://github.com/visgl/deck.gl/issues/9700) | Aguardar fix upstream e upgrade do Superset; alternativamente, patch local no bundle `@deck.gl/layers` |
| Auto-fit viewport em `deck.gl Path` | Lógica `@math.gl/web-mercator` exige colunas `latitude`/`longitude` no resultset | Incluir colunas auxiliares no virtual dataset, ou desligar Autozoom e fixar viewport |
| Granularidade da Country Map (UK) | TopoJSON embutido contém apenas códigos a nível de county/local authority | Substituição do GeoJSON por versão consolidada por nação no plugin |
| GeoJSON em deck.gl | Exige envelopamento em `Feature`/`FeatureCollection` (issue [#33618](https://github.com/apache/superset/issues/33618)) | Já contornado nesta instância via `printf` que constrói `Feature` completo |
| Filtros nativos por-dashboard | Native filters do Superset 6.1 não atravessam dashboards | Sem implementação nativa de "cross-dashboard filter" nesta versão |
| Análises pareadas | Dataset não modela pares | Modelagem adicional (virtual dataset que sintetize pares por rota+período) seria necessária |

---

## 6. Síntese

A instância foi construída como catálogo exemplar (um slice por tipo de chart), com **48 slices** sobre o dataset `main.tutorial_flights`. As ausências documentadas refletem **impossibilidade de configuração** sob esse dataset ou estado de configuração default da instalação oficial, distribuindo-se em cinco classes mutuamente exclusivas:

1. **Incompatibilidade estrutural com o dataset**: `paired_ttest`, `gantt`, `tree_chart` e `deck_polygon` exigem estruturas (pares de observações, intervalos com início/fim, auto-relacionamento `parent_id`/`id`, geometria de polígonos) que `tutorial_flights` não comporta e que não podem ser sintetizadas a partir das colunas disponíveis.
2. **Bloqueio por bug de shader do deck.gl 9.x**: `deck_hex` e `deck_grid` dependem do `column-layer-fragment-shader`, que referencia `lighting_getLightColor` — função ausente do módulo de iluminação injetado (issue [#9700](https://github.com/visgl/deck.gl/issues/9700)). O bloco problemático é selecionado em tempo de compilação via `#ifdef FLAT_SHADING`, ativado pelo material/lighting que está habilitado por padrão; a falha ocorre em mount, independentemente do toggle "Extruded" da UI.
3. **Bloqueio por integração viewport**: `deck_path` falhou em renderização por causa do erro `@math.gl/web-mercator: assertion failed — Could not fit viewport`. A lógica de auto-fit espera colunas `latitude`/`longitude` no resultset, ausentes quando a geometria de linha é construída via `printf`.
4. **Gating por feature flag desligada (default oficial)**: `pop_kpi` (gated por `CHART_PLUGINS_EXPERIMENTAL`) e `ag-grid-table` (gated por `AG_GRID_TABLE_ENABLED`) não aparecem no chart picker porque seus blocos de registro em [`MainPreset.ts`](https://github.com/apache/superset/blob/6.1.0/superset-frontend/src/visualizations/presets/MainPreset.ts) retornam array vazio quando a flag está `False` (default do Superset 6.1).
5. **Bloqueio por CSP**: `handlebars` falha em runtime com `'unsafe-eval' is not an allowed source of script` porque o `TALISMAN_CONFIG` default do Superset 6.1 omite `'unsafe-eval'` do `script-src`.

A configuração de filtros nativos é completa: **29 filtros ativos** cobrindo os **5 tipos** disponíveis no Superset 6.1 (`filter_select`, `filter_range`, `filter_timecolumn`, `filter_timegrain`, `filter_time`) e exercitando todos os recursos de configuração que a UI expõe (default value, required, single/multi-select, inverse, default-first, search-all, sort, pre-filter, cascata, single-value ranges).