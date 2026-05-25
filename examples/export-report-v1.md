# Export Report — Test Instance v1

**Run date:** May 25, 2026
**Command:** `superset-codec export ./examples/export --url http://localhost:8090 --user admin --password admin`
**Result:** 59 YAMLs generated in [examples/export/](export/) | 48/48 charts validated by query roundtrip | 0 failures reported | total size **145 KB** (145,009 bytes)

> Default mode — no `--safe`. For comparison, the repo also ships the same export produced with `--safe` (in [examples/export-safe/](export-safe/), 377 KB) and Superset's native UI export (in [examples/export-native/](export-native/), 469 KB across 60 files). See §2.

---

## 1. Summary

`superset-codec` exported every artifact in the Superset 6.1 test instance: 1 database, 1 dataset, 48 charts, 9 dashboards (29 native filter entries per dashboard). All 48 charts passed automated query-roundtrip validation — for each chart, the tool creates a temporary copy, calls `/api/v1/chart/data`, then deletes it. This confirms the chart returns data on the source instance, but **does not** prove the YAML rebuilds the full state on a clean Superset. The default output is compact and human-friendly but drops several Superset-internal fields the simplified schema doesn't model. The trade-off, and the alternative provided by `--safe`, are detailed in §3 and §8.

---

## 2. Reference baselines — three export modes

The repo ships three exports of the same instance for direct comparison:

| Folder | Mode | Files | Size | Produced by |
| --- | --- | --- | --- | --- |
| [examples/export/](export/) | **codec default** | 59 | 145 KB | `superset-codec export …` (this run) |
| [examples/export-safe/](export-safe/) | codec `--safe` | 59 | 377 KB | `superset-codec export … --safe` |
| [examples/export-native/](export-native/) | Superset native UI | 60 | 469 KB | "Export Dashboards / Export Charts" in the UI |

The native export is downloaded as a zip from `/api/v1/dashboard/export` and `/api/v1/chart/export` (what you get by clicking **Export** in the Superset UI). Unpacked, it looks like:

```text
examples/export-native/
├── metadata.yaml                                     # version, type, timestamp
├── databases/examples.yaml                           # full DB config + uuid
├── datasets/examples/tutorial_flights_44.yaml       # incl. columns, metrics, calculated columns
├── charts/<Name>_<id>.yaml                          # 48 files — slice_id in filename
└── dashboards/<Name>_<id>.yaml                      # 9 files — full position_json with ROW/CHART
```

It is **the source of truth for what Superset can round-trip end-to-end**: it preserves the entire Superset schema, including `uuid`s, internal slice IDs, full `position_json` with `ROW`/`CHART`/`TABS` containers, dataset `columns`, `metrics`, and calculated columns (e.g., `gb_code` at [tutorial_flights_44.yaml:31+](export-native/datasets/examples/tutorial_flights_44.yaml#L31)), and every `controlValues` attribute on filters. Drawback: filenames embed numeric IDs (`Bar_Chart_Default_279.yaml`), UUIDs are everywhere, and cross-references use Superset-internal identifiers — not human-friendly, not portable across instances without remapping.

The codec's simplified YAML in [examples/export/](export/) is a deliberate trade-off — files named by slice slug, references by `slice_name`, no UUIDs — at the cost of dropping fields the native export keeps (detailed in §3 and §7). `--safe` patches the most impactful drops by storing `_raw` fields alongside the simplified ones; [examples/export-safe/](export-safe/) shows the result.

---

## 3. Default mode — what gets dropped

Diffing this run against [examples/export-native/](export-native/) confirms three categories of silent loss (none reported as failures by the tool itself):

| Loss | Where | Verified by |
| --- | --- | --- |
| Chart `query_context` absent | All 48 charts (`grep -c "query_context_raw" examples/export/charts/*.yaml` → 0) | [bar_chart__default_.yaml](export/charts/bar_chart__default_.yaml) — no `query_context_raw` block |
| Dashboard `position_json` reduced to flat grid | All 9 dashboards (`grep -l "position_json_raw" examples/export/dashboards/*.yaml` → 0) | Charts listed with `row/col/width/height` only; `TABS`/`ROW`/`COLUMN`/`HEADER`/`MARKDOWN`/`DIVIDER` containers dropped (cf. [KPI_30.yaml](export-native/dashboards/KPI_30.yaml) which keeps the full container tree) |
| 16 of 29 filters collapsed to `filter_type: select` | All dashboards (`grep "filter_type:" examples/export/dashboards/kpi.yaml \| sort \| uniq -c` → 26 `select` + 3 `date`) | The 8 `filter_range` + 4 `filter_timecolumn` + 4 `filter_timegrain` are indistinguishable in the YAML from the 10 source `filter_select` |

Additional losses present in any mode (not affected by `--safe`):

- Dataset YAML omits `columns`, `metrics`, and calculated columns (12-line YAML for both default and safe runs vs. the native export's full block at [tutorial_flights_44.yaml:20+](export-native/datasets/examples/tutorial_flights_44.yaml#L20)).
- `cartodiagram.params.selected_chart` contains a hardcoded `"id":325` referring to the embedded Funnel chart ([cartodiagram__default_.yaml:34](export/charts/cartodiagram__default_.yaml#L34)).
- The 10 `filter_select` and 3 `filter_time` filters lose `controlValues`/`cascadeParentIds`/`adhocFilters` because their types are in `_KNOWN_FILTER_TYPES` ([_filters.py:12](../src/superset_codec/_filters.py#L12)) and the simplified schema drops these attributes.

### What `--safe` mitigates

For comparison, running with `--safe` (output preserved in [examples/export-safe/](export-safe/)) enables four exporter behaviors:

| Behavior | Source location | Effect on size |
| --- | --- | --- |
| `query_context_raw` on every chart | [_export.py:151–156](../src/superset_codec/_export.py#L151-L156) | charts +128 KB |
| `position_json_raw` on every dashboard | [_export.py:205–208](../src/superset_codec/_export.py#L205-L208) | dashboards +25 KB (subset of next row) |
| `_raw` (full Superset object) on filters whose `filterType` ∉ `{filter_select, filter_time}` | [_filters.py:141–144](../src/superset_codec/_filters.py#L141-L144) | 16 filters × 9 dashboards |
| Per-resource warnings instead of abort on error | [_export.py:104, 129, 167, 216](../src/superset_codec/_export.py#L104) | — |

Total cost: 145 KB → 377 KB. `--safe` covers the first three losses listed above; it does **not** fix the dataset omission, the cartodiagram hardcoded ID, or the `filter_select`/`filter_time` attribute drop (see §8).

---

## 4. Consolidated Results

| Artifact | Expected | Exported | Generation | Roundtrip |
|----------|----------|----------|------------|-----------|
| Databases | 1 | 1 | OK | n/a |
| Datasets | 1 | 1 | OK | n/a |
| Charts | 48 | 48 | OK | 48/48 query OK |
| Dashboards | 9 | 9 | OK | n/a |
| Native filters | 29 | 29 | OK | n/a |
| YAML files | — | 59 | OK | — |

Coverage over Superset 6.1 catalog: 48 of 56 effectively available `viz_type`s in the UI (85.7%). The 8 missing are documented in §2 of [test-instance-catalog-v1.md](test-instance-catalog-v1.md).

### 4.1 Dashboards

Counts verified via [examples/export/dashboards/](export/dashboards/). All 9 share the same 29 filter entries (not 261 independent configurations).

| Dashboard | Charts | | Dashboard | Charts |
| --- | --- | --- | --- | --- |
| `correlation` | 4 | | `map` | 11 |
| `distribution` | 3 | | `part-of-a-whole` | 4 |
| `evolution` | 11 | | `ranking` | 4 |
| `flow` | 3 | | `table` | 3 |
| `kpi` | 5 | | **Total** | **48** |

---

## 5. Native Filters — YAML Preservation

29 filters in source: `filter_select` (10, mostly on `destination_country`/`airline`/`origin_*`/`travel_class`/`ticket_single_or_return`), `filter_range` (8, on `cost`), `filter_timecolumn` (4), `filter_timegrain` (4), `filter_time` (3).

In default mode (no `_raw`), the YAML preserves only `name`, `column`, `dataset`, `filter_type`, `multi_select`, and `default_value`. The original `filterType` distinction is lost for everything outside `{filter_select, filter_time}`: 16 filters end up as `filter_type: select` in the YAML, indistinguishable from the 10 source `filter_select`. Verified by `grep "filter_type:" examples/export/dashboards/kpi.yaml | sort | uniq -c` → 26 × `select` + 3 × `date`.

| UI feature | Source filters | YAML status (default mode) |
| --- | --- | --- |
| Default value | 10 filters | Preserved (`default_value`) |
| Multi/Single-select | filter_select (08 single) | Preserved (`multi_select`) |
| Cascade (`cascadeParentIds`) | 02, 13 | **Both lost** |
| Pre-filter (`adhocFilters`) | 03, 14 | **Both lost** |
| Required (`enableEmptyFilter`) | 06, 19, 24, 29, 33 | **All lost** |
| Sort ascending | 04, 22, 27 | **All lost** |
| Select first item (`defaultToFirstItem`) | 07 | **Lost** |
| Dynamic search (`searchAllOptions`) | 09 | **Lost** |
| Inverse selection | 10 | **Lost** |
| Single-value mode (`enableSingleValue`) | 15 | **Lost** |
| Range input / slider widget | 16, 17 | **Lost** |
| Original `filterType` (range/time-column/time-grain) | 16 filters | **Lost** — all collapse to `filter_type: select` |

`--safe` would preserve the 16 `filter_range`/`filter_timecolumn`/`filter_timegrain` attributes via `_raw` (see [export-safe/dashboards/kpi.yaml:95+](export-safe/dashboards/kpi.yaml#L95)), still leaving the 10 `filter_select` and 3 `filter_time` UI features unrecoverable in either mode.

---

## 6. Output Structure

```text
examples/export/
├── databases/examples.yaml                                 [1 file]
├── datasets/tutorial_flights.yaml                          [1 file]
├── charts/                                                 [48 files — one per slice]
│   ├── area_chart__default_.yaml
│   ├── ... (e.g. big_number__default_.yaml, world_map__default_.yaml)
└── dashboards/                                             [9 files]
    └── correlation|distribution|evolution|flow|kpi|map|part-of-a-whole|ranking|table.yaml
```

Total: 59 YAMLs, **145 KB** (145,009 bytes). Per-section breakdown:

| Section | Default | Safe | Native | Delta default → safe |
| --- | --- | --- | --- | --- |
| `databases/` | 647 B | 647 B | 525 B | 0 |
| `datasets/` | 465 B | 465 B | 14 KB | 0 |
| `charts/` | 98 KB | 224 KB | ~270 KB | +126 KB (`query_context_raw`) |
| `dashboards/` | 42 KB | 144 KB | ~185 KB | +102 KB (`position_json_raw` + 144 filter `_raw`) |
| **Total** | **145 KB** | **377 KB** | **469 KB** | **+232 KB** |

The native export's overhead beyond `--safe` is mostly the dataset `columns:`/`metrics:` block (the codec drops them in both modes) and full Superset object serialization on every artifact.

---

## 7. Elements Preserved in YAML

Verified by inspecting YAMLs in [examples/export/](export/) and diffing against [examples/export-native/](export-native/).

| Artifact | Preserved | Missing (default mode) |
|---|---|---|
| **Chart** | `viz_type`, `slice_name`, `datasource_table`, `params` (all 48); cross-refs (`params.dashboards`, `params.selected_chart.id`) as numeric IDs — don't resolve on re-apply (risk 2) | `query_context` (risk 3); `description`, `tags`, `owner`, `created_on`, `changed_on` |
| **Dashboard** | `dashboard_title`, `slug`, `published`; chart list by `slice_name` with flat `row/col/width/height` | Full `position_json` with `TABS`/`ROW`/`COLUMN`/`HEADER`/`MARKDOWN`/`DIVIDER` containers (risk 4); `json_metadata`, `description`, `embedding_config`, `refresh_interval`, `cache_timeout` |
| **Filter** | `name`, `column`, `dataset` (all 29); `filter_type` ∈ `{select, date}` only — 16 source filters collapsed to `select` (risk 5); `multi_select`, `default_value` when set | `controlValues`/`cascadeParentIds`/`adhocFilters`/`enableEmptyFilter`/`sortAscending`/`enableSingleValue` on all 29 filters (risk 6) |
| **Dataset** | `table_name`, `schema`, `database`, `main_dttm_col`, `filter_select_enabled`, `is_sqllab_view`, `offset`, `sql` (12-line YAML) | `columns`, `metrics`, calculated columns (risk 1) |

---

## 8. Risks for Re-apply

Not detected by roundtrip validation (which only tests queries on the source). Severity is **for a clean-target re-apply**; on the source instance, all 48 charts respond OK.

| # | Risk | Severity | `--safe` covers? | Cause | Schema mitigation |
| --- | --- | --- | --- | --- | --- |
| 1 | Dataset YAML omits physical and calculated columns | High | **No** | Charts depending on calculated columns fail on re-apply: `country_map` (`gb_code`), `cartodiagram` (`origin_cartodiagram`), `deck_geojson` (`destination_geojson`). Compare against native [tutorial_flights_44.yaml:20+](export-native/datasets/examples/tutorial_flights_44.yaml#L20) which keeps `metrics:` and `columns:` | Extend `_export_datasets` to include `columns:` and `metrics:` |
| 2 | `cartodiagram.selected_chart.id` hardcoded | High | **No** | Serialized JSON carries `"id":325` for the embedded Funnel — won't exist on another Superset. See [cartodiagram__default_.yaml:34](export/charts/cartodiagram__default_.yaml#L34) | Resolve reference by `slice_name` on apply, rewriting the ID |
| 3 | Chart `query_context` missing | Medium | **Yes** (`query_context_raw`) | Default mode drops the pre-computed query payload Superset uses for the explore view; rebuild on apply depends on the codec's `_build_query_context` fallback covering every `viz_type` — guaranteed only for the 5 in the README table, generic fallback for the rest | Run with `--safe`, or extend `_build_query_context` |
| 4 | Dashboard `position_json` reduced | Medium | **Yes** (`position_json_raw`) | Default mode emits charts in a flat `row/col` grid; layout primitives (`TABS`, `ROW`, `COLUMN`, `HEADER`, `MARKDOWN`, `DIVIDER`) are dropped. The test instance uses a flat layout so the loss is invisible here, but any dashboard with tabs/markdown/dividers would degrade on re-apply | Run with `--safe`, or extend the dashboard schema |
| 5 | 16 filters collapsed to `filter_type: select` | High | **Yes** (`_raw` block on those 16) | `filter_range`/`filter_timecolumn`/`filter_timegrain` are indistinguishable from `filter_select` in the YAML; on re-apply they would be recreated as `select` filters, breaking range UI, time-column targeting, and grain selection | Run with `--safe`, or expand the simplified schema to retain `filterType` |
| 6 | All 29 filters lose UI attributes | Medium | **Partial** (`--safe` recovers 16 via `_raw`) | The 10 `filter_select` and 3 `filter_time` lose `cascadeParentIds`, `adhocFilters`, `enableEmptyFilter`, `sortAscending`, `searchAllOptions`, `defaultToFirstItem`, `inverseSelection`, `enableSingleValue` — see §5 | Include `controlValues` in [_filters.py:127–139](../src/superset_codec/_filters.py#L127-L139), or remove `filter_select` from `_KNOWN_FILTER_TYPES` |
| 7 | Country Map (UK) — TopoJSON granularity | Low | n/a | Plugin embeds TopoJSON at county/local-authority level; YAML exposes `entity: gb_code` correctly but the map only renders matching codes. Block is in the plugin, not the codec | Replace plugin's embedded TopoJSON |
| 8 | Roundtrip validates query, not rendering | Low | n/a | Plugin/shader bugs failing at mount aren't detected (see §2/§5.3 of the catalog) | Validation in a separate environment (§9) |

**Recommendation:** for a single source instance evolving in place, the default mode is acceptable. For re-applying to a clean target — especially without dataset hand-edits — run with `--safe` and address risks 1, 2, and 6 via schema evolution.

---

## 9. Next Steps

Validate `apply` on a separate clean Superset before using the export as a sync mechanism between environments:

```bash
superset-codec apply ./examples/export \
  --url http://localhost:9090 --user admin --password admin
```

Nominal: 1 database, 1 dataset, 48 charts, 9 dashboards, 29 filter entries per dashboard. Predicted failures in default mode (from §8): `country_map`, `cartodiagram`, `deck_geojson` (calculated columns missing — risk 1); 16 filters rebuilt as `filter_type: select` instead of range/time-column/time-grain (risk 5); all 29 filters rebuilt without `cascadeParentIds`/`inverseSelection`/`sortAscending`/`searchAllOptions`/`defaultToFirstItem`/`enableEmptyFilter`/`adhocFilters` (risk 6); charts losing `query_context` fall back to the codec's generic builder (risk 3). Conformance checks:

| Test | Command | Success criterion |
|------|---------|-------------------|
| Count charts | `curl .../api/v1/chart?page_size=1000` | 48 |
| Count dashboards | `curl .../api/v1/dashboard?page_size=100` | 9 |
| Validate filters | `curl .../api/v1/dashboard/{id}` | 29 entries in `native_filter_configuration` |
| Rendering | Open each chart in the UI | Detect §8 failures (risks 1, 2, 5, 7) |
| Filter type preservation | Inspect `native_filter_configuration` of a re-applied dashboard | 8 `filter_range`, 4 `filter_timecolumn`, 4 `filter_timegrain` rebuilt (currently fails in default mode — risk 5) |

Risks 1, 2, and 6 require schema evolution — not solvable via CLI flags. Risks 3, 4, and 5 can be mitigated immediately by re-running with `--safe`.

---

**Report prepared on:** May 25, 2026 · **Tool:** superset-codec v0.1.0 · **Target Superset:** 6.1.0
