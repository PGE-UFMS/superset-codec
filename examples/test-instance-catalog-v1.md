# Test Instance Catalog

A complete resource set built to test and validate **superset-codec**: an exemplar Superset 6.1 instance with 48 pre-configured charts, 9 themed dashboards, and 29 native filters exercising every available configuration option.

> Primary source: Superset REST API (`/api/v1/chart`, `/api/v1/dashboard`) on the local instance. Secondary: project files (`Dockerfile`, `docker-compose.yml`, `tutorial_flights.csv`). Bug diagnoses link to public issues inline.

## 1. Chart Inventory

One slice per chart type supported by Superset, all over `main.tutorial_flights`. The only non-default variant is `[Custom Cell-Thresholds]` on `deck_contour` (manual Cell Size/Threshold tuning). Analytic-domain repetition between charts is intentional. "Main settings" = what the type typically requires.

### 1.1 Consolidated table — 48 charts

| viz_type | Slice name | Main settings (per type) | Analytic purpose | Note |
|---|---|---|---|---|
| `big_number` | Big Number with Trendline [Default] | Single metric + temporal dim | KPI with trend | — |
| `big_number_total` | Big Number [Default] | Single metric | Static KPI | — |
| `box_plot` | Box Plot [Default] | Dim + numeric metric | Distribution/outliers | — |
| `bubble` | Bubble Chart (legacy) [Default] | X/Y + size + group | Trivariate correlation | Marked legacy |
| `bubble_v2` | Bubble Chart [Default] | Same as `bubble`, updated | Trivariate correlation | — |
| `bullet` | Bullet [Default] | Value + target + ranges | Comparison vs. goal | — |
| `cal_heatmap` | Calendar Heatmap [Default] | Date + metric | Daily seasonal pattern | — |
| `cartodiagram` | Cartodiagram [Default] | GeoJSON Point column + embedded chart | Mini-charts at geo coords | Requires calculated column `origin_geojson`; chart embedded at each point |
| `chord` | Chord Diagram [Default] | Source-target-magnitude | Bilateral flow | — |
| `compare` | Time-series Percent Change [Default] | Temporal metric | Percentage variation | — |
| `country_map` | Country Map [Default] | Country + ISO 3166-2 + metric | Subnational choropleth | UK; uses county/local-authority codes |
| `deck_arc` | deck.gl Arc [Default] | Origin/dest lat/lng + metric | Georeferenced flows | — |
| `deck_contour` | deck.gl Contour [Custom Cell-Thresholds] | lat/lng + aggregation; Cell Size + thresholds | Density isolines | Cell Size/Thresholds manually tuned |
| `deck_geojson` | deck.gl GeoJson [Default] | Column with `Feature`/`FeatureCollection` | Custom vector rendering | Raw `Polygon`/`Point` rejected — issue [#33618](https://github.com/apache/superset/issues/33618) |
| `deck_heatmap` | deck.gl Heatmap [Default] | lat/lng + intensity metric | Continuous density | — |
| `deck_multi` | deck.gl Multiple Layers [Default] | Sub-layer composition | Multiple geo layers | — |
| `deck_scatter` | deck.gl Scatterplot [Default] | lat/lng + size metric | Georeferenced points | — |
| `deck_screengrid` | deck.gl Screengrid [Default] | lat/lng + pixel-grid aggregation | Zoom-independent density | — |
| `echarts_area` | Area Chart [Default] | Temporal X + metric + group | Cumulative temporal evolution | — |
| `echarts_timeseries` | Generic Chart [Default] | Timeseries; type-agnostic | Generic temporal evolution | — |
| `echarts_timeseries_bar` | Bar Chart [Default] | Timeseries with bars | Categorized temporal evolution | — |
| `echarts_timeseries_line` | Line Chart [Default] | Timeseries with lines | Continuous temporal evolution | — |
| `echarts_timeseries_scatter` | Scatter Plot [Default] | X/Y + group | Correlation/dispersion | — |
| `echarts_timeseries_smooth` | Smooth Line [Default] | Smoothed line | Noise-free trend | — |
| `echarts_timeseries_step` | Stepped Line [Default] | Step line | Discrete states over time | — |
| `funnel` | Funnel Chart [Default] | Ordered stages + metric | Sequential conversion | — |
| `gauge_chart` | Gauge Chart [Default] | Value + ranges | Point-in-time status | — |
| `graph_chart` | Graph Chart [Default] | Source-target-weight | Network topology | — |
| `heatmap_v2` | Heatmap [Default] | 2 dims × metric | Matrix density | — |
| `histogram_v2` | Histogram [Default] | Numeric metric + bins | Univariate distribution | — |
| `horizon` | Horizon Chart [Default] | Compressed time series | Dense series comparison | — |
| `mapbox` | MapBox [Default] | lat/lng + aggregation | Point map | — |
| `mixed_timeseries` | Mixed Chart [Default] | Dual Y-axis | Different-scale metrics | — |
| `para` | Parallel Coordinates [Default] | N dimensions | Multivariate | — |
| `partition` | Partition Chart [Default] | Hierarchy + metric | Hierarchical composition | — |
| `pie` | Pie Chart [Default] | Dim + metric | Part-of-whole | — |
| `pivot_table_v2` | Pivot Table [Default] | Rows × cols × metrics | Cross-tabulation | — |
| `radar` | Radar Chart [Default] | N dims on polar scale | Multidimensional comparison | — |
| `rose` | Nightingale Rose Chart [Default] | Angular sectors × magnitude | Cyclic composition | — |
| `sankey_v2` | Sankey Chart [Default] | Source → target → flow | Unidirectional flow | — |
| `sunburst_v2` | Sunburst Chart [Default] | Hierarchy in rings | Radial hierarchical composition | — |
| `table` | Table [Default] | Raw or aggregated cols | Tabular view | — |
| `time_pivot` | Time-series Period Pivot [Default] | 2 time axes × metric | Seasonality comparison | — |
| `time_table` | Time-series Table [Default] | Metrics × time (sparkline per row) | Temporal KPI panel | — |
| `treemap_v2` | Treemap [Default] | Hierarchy + metric (area) | Hierarchical composition | — |
| `waterfall` | Waterfall Chart [Default] | Variations between stages | Variance decomposition | — |
| `word_cloud` | Word Cloud [Default] | Text column + frequency | Lexical frequency | — |
| `world_map` | World Map [Default] | ISO 3166-1 alpha-2 + metric | Global choropleth | — |

### 1.2 Native filters applied

The 48 charts are spread across 9 dashboards (`Map`, `Part of a Whole`, `Flow`, `KPI`, `Distribution`, `Evolution`, `Ranking`, `Table`, `Correlation`), all sharing `main.tutorial_flights`. Each dashboard has **29 entries in `native_filter_configuration`** (see §4).

| Filter group | `filterType` | Count | Target columns |
| --- | --- | --- | --- |
| Value | `filter_select` | 10 | `destination_country`, `origin_country`, `origin_municipality`, `origin_name`, `airline`, `travel_class`, `ticket_single_or_return` |
| Numerical range | `filter_range` | 8 | `cost` |
| Time column | `filter_timecolumn` | 4 | — |
| Time grain | `filter_timegrain` | 4 | — |
| Time range | `filter_time` | 3 | — |

### 1.3 Layout elements not covered

The catalog tests dashboard **content**, not **visual structure**. All 9 dashboards use a flat layout — one chart per `row/col` cell, no `TABS`/`ROW`/`COLUMN`/`HEADER`/`MARKDOWN`/`DIVIDER`. Layout fidelity through the export/apply cycle **is not validated** here.

---

## 2. Missing Charts — Analysis

The catalog's rule is "one exemplar per type", so each absence reflects a concrete blocker — incompatibility between what the type requires and what `tutorial_flights` offers, or a Superset/deck.gl bug preventing rendering.

### 2.1 Paired t-test Table
- **Requires:** two paired samples — same observational unit in two conditions/times.
- **Absent because:** `tutorial_flights` records each flight independently; no field establishes pairing.

### 2.2 Gantt Chart
- **Requires:** task ID + start timestamp + end timestamp (or duration).
- **Absent because:** CSV has only `travel_date` — one date per flight, no interval concept.

### 2.3 Tree Chart
- **Requires:** explicit hierarchical relation (self-reference `parent_id` → `id`, or predefined levels).
- **Absent because:** no self-referencing column. Derived categorical hierarchies (`country → region → municipality → ICAO`) are nested dimensions, not a tree with internal nodes.

### 2.4 deck.gl Path
- **Requires:** one column per row holding the full trajectory as `[[lng,lat],...]` or encoded polyline.
- **Absent because:** origin/destination are separate columns. Synthesizing geometry via `printf('[[%f,%f],[%f,%f]]', ...)` produces valid SQL Lab output, but rendering fails with `@math.gl/web-mercator: assertion failed — Could not fit viewport`. Auto-fit requires `latitude`/`longitude` columns in the resultset, absent when only line geometry is projected (see [PathLayer docs](https://deck.gl/docs/api-reference/layers/path-layer)).

### 2.5 deck.gl 3D Hexagon
- **Requires:** lat/lng + volumetric aggregation in hexagonal cells; inherently extruded.
- **Absent because:** `column-layer-fragment-shader` (shared by [`HexagonLayer`](https://deck.gl/docs/api-reference/aggregation-layers/hexagon-layer) in extruded mode) references `lighting_getLightColor` inside `#ifdef FLAT_SHADING`. The function is undefined in deck.gl 9.x's injected lighting module (issue [#9700](https://github.com/visgl/deck.gl/issues/9700), no fix in 9.1.x/9.2.x). `FLAT_SHADING` is set at compile time when material/lighting is on (default), so compilation fails at mount before any runtime check.

### 2.6 deck.gl Grid
- **Requires:** lat/lng + square-grid aggregation; rendered via `GridCellLayer`, inheriting `ColumnLayer`'s lighting pipeline.
- **Absent because:** same shader bug as §2.5. [`GridCellLayer`](https://deck.gl/docs/api-reference/layers/grid-cell-layer) compiles with `FLAT_SHADING` whenever material/lighting is active (default). UI "Extruded" toggle doesn't help — block is selected at compile time. Superset 6.1 exposes no control to disable the layer's lighting module.

### 2.7 deck.gl Polygon
- **Requires:** one column with polygon geometry (closed coord array or GeoJSON `Polygon`/`MultiPolygon`) per row.
- **Absent because:** structural — `tutorial_flights` has only point coordinates, no plausible polygon synthesis from existing columns. Aggravating: stroke-color regression in Superset 6.0 (issue [#36326](https://github.com/apache/superset/issues/36326)); with extrusion, same shader bug as §2.5.

### 2.8 Feature-flag-gated plugins — `pop_kpi` and `ag-grid-table`
- **Affected:** `pop_kpi` (Big Number Period over Period), `ag-grid-table` (ag-Grid Table).
- **UI behavior:** absent from chart picker despite being in enums and JS bundles.
- **Reason:** conditional registration in [`MainPreset.ts`](https://github.com/apache/superset/blob/6.1.0/superset-frontend/src/visualizations/presets/MainPreset.ts) gated by `CHART_PLUGINS_EXPERIMENTAL` (`pop_kpi`) and `AG_GRID_TABLE_ENABLED` (`ag-grid-table`). Both `False` (Superset 6.1 default). [`superset/superset_config.py`](superset/superset_config.py) sets only `ENABLE_TEMPLATE_PROCESSING=True` and `PRESTO_EXPAND_DATA=False`.
- **Mitigation:** enable the flags and restart. Not applied here to preserve vanilla 6.1 fidelity.

### 2.9 Handlebars — CSP block
- **Requires:** Handlebars template compiled at runtime via `new Function(...)` / `eval`.
- **Absent because:** plugin registered and visible, but rendering fails with `'unsafe-eval' is not an allowed source of script`. Superset 6.1's default `TALISMAN_CONFIG` ([superset/config.py:2152](https://github.com/apache/superset/blob/6.1.0/superset/config.py#L2152)) sets `"script-src": ["'self'", "'strict-dynamic'"]` — no `'unsafe-eval'`. Tracked in [apache/superset#30607](https://github.com/apache/superset/issues/30607).
- **Mitigation:** override `TALISMAN_CONFIG`. Not applied: relaxing CSP weakens XSS protection globally.

---

## 3. Implemented vs. Superset Catalog

Sources: 58 plugins in this instance's frontend bundle (47 non-deck + 11 deck.gl). 2 are gated by off feature flags ([`MainPreset.ts`](https://github.com/apache/superset/blob/6.1.0/superset-frontend/src/visualizations/presets/MainPreset.ts)), leaving **56 in the UI**; 48 distinct `viz_type`s are returned by `/api/v1/chart/?q=(page_size:200)`. Coverage: **48/56 = 85.7% over UI**, **48/58 = 82.8% over source**. The 8 missing types are documented in §2.

### 3.1 Coverage by category

> "Available (UI)" excludes flag-gated plugins; "Available (code)" keeps the source total.

| Category | Implemented | Available (UI) | Available (code) | Coverage | Missing |
| --- | --- | --- | --- | --- | --- |
| KPI | 2 | 2 | 3 | 100% | — (`pop_kpi` gated) |
| Time series ECharts | 8 | 8 | 8 | 100% | — |
| Time series (other) | 5 | 5 | 5 | 100% | — |
| Tabular | 2 | 2 | 3 | 100% | — (`ag-grid-table` gated) |
| Distribution | 3 | 3 | 3 | 100% | — |
| Part-of-whole | 6 | 7 | 7 | 85.7% | `tree_chart` |
| Multivariate | 4 | 4 | 4 | 100% | — |
| Flow/Network | 3 | 3 | 3 | 100% | — |
| Geospatial base | 4 | 4 | 4 | 100% | — |
| Geospatial deck.gl | 7 | 11 | 11 | 63.6% | `deck_grid`, `deck_hex`, `deck_path`, `deck_polygon` |
| Inferential statistics | 0 | 1 | 1 | 0% | `paired_ttest` |
| Schedule | 0 | 1 | 1 | 0% | `gantt_chart` |
| Other (gauge, bullet, word cloud, waterfall, handlebars) | 4 | 5 | 5 | 80.0% | `handlebars` |
| **Total** | **48** | **56** | **58** | **85.7%** | 8 in UI |

### 3.2 Missing types — state and data dependency

| `viz_type` | In UI? | State | Required column(s) | Available? |
| --- | --- | --- | --- | --- |
| `paired_ttest` | Yes | Structural — §2.1 | pair ID + 2 obs of same unit | Absent |
| `gantt_chart` | Yes | Structural — §2.2 | id + start + end | Only `travel_date` |
| `tree_chart` | Yes | Structural — §2.3 | `parent_id` → `id` | Absent |
| `deck_path` | Yes | Viewport auto-fit — §2.4 | trajectory in single column | Constructible; rendering blocked |
| `deck_hex` | Yes | deck.gl 9.x shader — §2.5 | lat/lng + metric | Data ok; shader fails at mount |
| `deck_grid` | Yes | deck.gl 9.x shader — §2.6 | lat/lng + metric | Data ok; shader fails even in 2D with default lighting |
| `deck_polygon` | Yes | Structural + shader — §2.7 | polygon geometry | Absent; no plausible synthesis |
| `handlebars` | Yes | CSP — §2.9 | — | n/a |
| `pop_kpi` | **No** | `CHART_PLUGINS_EXPERIMENTAL=False` — §2.8 | — | n/a |
| `ag-grid-table` | **No** | `AG_GRID_TABLE_ENABLED=False` — §2.8 | — | n/a |

---

## 4. Native Filters Catalog

29 active filters, covering all 5 `filterType`s in Superset 6.1, all targeting `main.tutorial_flights` (id=44).

### 4.1 "Value" group — `filter_select` (10 filters)

| # | Filter name | Target column | Feature demonstrated | Default |
| --- | --- | --- | --- | --- |
| 01 | `Value [Default]` | `destination_country` | Baseline (multi-select, creatable, no custom sort); parent of cascade filters 02 and 13 | — |
| 02 | `[Value] Values are dependent on other filters` | `airline` | **Cascade**: `cascadeParentIds` → filter 01; options filtered by `destination_country` | — |
| 03 | `Value [Pre-filter available values]` | `origin_municipality` | **Pre-filter**: `adhocFilters` restricts dropdown to `origin_country = 'United Kingdom'` | — |
| 04 | `Value [Sort filter values]` | `origin_name` | **Sort ascending** (`controlValues.sortAscending = true`) | — |
| 05 | `Value [Filter has default value]` | `origin_country` | **Default value** without `required` | `['United Kingdom']` |
| 06 | `Value [Filter value is required]` | `origin_country` | **Required** (`enableEmptyFilter = true`) + default | `['United Kingdom']` |
| 07 | `Value [Select first filter value by default]` | `ticket_single_or_return` | **`defaultToFirstItem = true`** | dynamic |
| 08 | `Value [Can't select multiple values]` | `travel_class` | **Single-select** (`multiSelect = false`) | — |
| 09 | `Value [Dynamically search all filter values]` | `airline` | **Search-all** (`searchAllOptions = true`) | — |
| 10 | `Value [Inverse selection]` | `destination_country` | **Inverse** (`inverseSelection = true`) — "NOT IN" semantics | — |

### 4.2 "Numerical range" group — `filter_range` (8 filters), all on `cost`

| # | Filter name | Feature demonstrated | Default |
| --- | --- | --- | --- |
| 12 | `Numerical range [Default]` | Baseline — dual-slider UI | — |
| 13 | `Numerical range [Values are dependent on other filters]` | **Cascade** of filter 01; min/max adjusted to filtered subset | — |
| 14 | `Numerical range [Pre-filter available values]` | **Pre-filter** with `adhocFilters` restricting extrema to `origin_country = 'United Kingdom'` | — |
| 15 | `Numerical range [Single Value]` | **Single-value mode** (`enableSingleValue = 1`) — UI becomes single slider | — |
| 16 | `Numerical range [Range Inputs]` | Numeric inputs instead of slider | — |
| 17 | `Numerical range [Slider]` | Slider explicitly | — |
| 18 | `Numerical range [Filter has default value]` | **Default value** | `[1, 7969.2]` (dataset min/max) |
| 19 | `Numerical range [Filter value is required]` | **Required** + default | `[1, 7969.2]` |

### 4.3 Time groups — `filter_timecolumn` (4), `filter_timegrain` (4), `filter_time` (3)

| # | Filter name | Feature | Default |
| --- | --- | --- | --- |
| 21 | `Time column [Default]` | Baseline; `targets[0].column` empty (applies to dataset) | — |
| 22 | `Time column [Sort filter values]` | **Sort ascending** | — |
| 23 | `Time column [Filter has default value]` | **Default value** | `['travel_date']` |
| 24 | `Time column [Filter value is required]` | **Required** + default | `['travel_date']` |
| 26 | `Time grain [Default]` | Baseline — `P1D`, `P1W`, `P1M`, `P1Y`… | — |
| 27 | `Time grain [Sort filter values]` | **Sort ascending** | — |
| 28 | `Time grain [Filter has default value]` | **Default value** | `['P1Y']` (annual) |
| 29 | `Time grain [Filter value is required]` | **Required** + default | `['P1Y']` |
| 31 | `Time range [Default]` | Baseline — temporal interval picker | — |
| 32 | `Time range [Filter has default value]` | **Default** with arbitrary start | `2011-01-01T03:30:09 : 2011-12-31T00:00:00` |
| 33 | `Time range [Filter value is required]` | **Required** + normalized default | `2011-01-01T00:00:00 : 2011-12-31T00:00:00` |

### 4.4 Feature → internal field mapping

Every filter feature Superset 6.1 exposes in the native-filter UI is exercised across the 29 filters above.

| UI feature | Internal field | Filter(s) |
| --- | --- | --- |
| Filter type | `filterType` | All 5 types covered |
| Target column | `targets[0].column.name` | 7 categorical + `cost` |
| Default value | `defaultDataMask.filterState.value` | 05, 06, 18, 19, 23, 24, 28, 29, 32, 33 |
| Required | `controlValues.enableEmptyFilter` | 06, 19, 24, 29, 33 |
| Single-select | `controlValues.multiSelect = false` | 08 |
| Inverse selection | `controlValues.inverseSelection` | 10 |
| Select first item | `controlValues.defaultToFirstItem` | 07 |
| Dynamic search-all | `controlValues.searchAllOptions` | 09 |
| Sort ascending | `controlValues.sortAscending` | 04, 22, 27 |
| Pre-filter | `controlValues.adhocFilters` | 03, 14 |
| Cascade | `cascadeParentIds` | 02, 13 (both depend on 01) |
| Single-value range | `controlValues.enableSingleValue` | 15 |
| Range input / slider widget | widget type | 16 / 17 |
| Scope | `scope` | All 29 use `rootPath: ["ROOT_ID"]` (global) |

---

## 5. Structural Limitations & Possible Mitigations

| Limitation | Origin | Possible mitigation |
|---|---|---|
| deck.gl extrusion shader bug (§2.5–2.7) | deck.gl 9.x — issue [#9700](https://github.com/visgl/deck.gl/issues/9700) | Wait for upstream fix; or local patch in `@deck.gl/layers` |
| Viewport auto-fit on `deck.gl Path` (§2.4) | `@math.gl/web-mercator` requires `latitude`/`longitude` in resultset | Add auxiliary columns to virtual dataset, or disable Autozoom and fix viewport |
| Country Map (UK) granularity | Embedded TopoJSON only has county/local-authority codes | Replace plugin's GeoJSON with nation-consolidated version |
| GeoJSON in deck.gl | Requires `Feature`/`FeatureCollection` wrapping ([#33618](https://github.com/apache/superset/issues/33618)) | Already worked around here via `printf` building `Feature` |
| Per-dashboard native filters | Superset 6.1 native filters don't cross dashboards | No native cross-dashboard filter exists |
| Paired analyses | Dataset doesn't model pairs | Virtual dataset synthesizing pairs by route+period |

> **Filter impact on charts:** `filter_select` on categorical columns applies via `WHERE` to all 47 charts (semantics preserved, cardinality reduced). `filter_range` on `cost` acts before aggregation, mainly affecting `box_plot`/`histogram_v2` and SUM/AVG-of-`cost` metrics. `filter_timecolumn` + `filter_time` on `travel_date` are relevant for the 8 timeseries + `cal_heatmap` + `horizon` + `time_pivot` + `time_table`. `filter_timegrain` applies only to charts aggregating over a native temporal interval.
