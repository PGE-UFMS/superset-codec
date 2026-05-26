"""Apply mixin — sync_* methods that create or update Superset resources."""
import json
import logging
from typing import Any

from .models import ChartRef, DashboardRef, DatabaseRef, DatasetRef
from ._filters import build_native_filters
from ._positions import build_position_json

log = logging.getLogger(__name__)


def _enable_embedding(session, url: str, dashboard_id: int) -> str:
    resp = session.post(
        f"{url}/api/v1/dashboard/{dashboard_id}/embedded",
        json={"allowed_domains": []},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["result"]["uuid"]


def _build_query_context(viz_type: str, dataset_id: int, params: dict) -> str:
    """Build the ``query_context`` required by Superset 4.x to execute chart queries.

    Without this field, charts render with "Empty query?".
    """
    if "metric" in params:
        metrics = [params["metric"]]
    elif "metrics" in params:
        metrics = params["metrics"]
    else:
        metrics = []

    groupby = params.get("groupby", [])
    x_axis  = params.get("x_axis")
    entity  = params.get("entity")

    def _col_str(c: Any) -> str:
        return c.get("column_name", str(c)) if isinstance(c, dict) else c

    if viz_type == "big_number_total":
        columns, row_limit = [], 1
    elif viz_type == "country_map":
        columns   = [_col_str(entity)] if entity else []
        row_limit = params.get("row_limit", 50)
    elif viz_type in ("echarts_timeseries_bar", "echarts_timeseries_line") and x_axis:
        columns   = [_col_str(x_axis)] + [_col_str(g) for g in groupby if g != x_axis]
        row_limit = params.get("row_limit", 10000)
    elif viz_type == "pie":
        columns   = [_col_str(g) for g in groupby]
        row_limit = params.get("row_limit", 10000)
    elif x_axis:
        columns   = [_col_str(x_axis)] + [_col_str(g) for g in groupby if g != x_axis]
        row_limit = params.get("row_limit", 10000)
    else:
        columns   = [_col_str(g) for g in groupby]
        row_limit = params.get("row_limit", 10000)

    granularity = (
        params.get("granularity")
        or params.get("granularity_sqla")
        or params.get("time_column")
    )
    query: dict[str, Any] = {
        "time_range":          params.get("time_range", "No filter"),
        "filters":             [],
        "extras":              {"having": "", "where": ""},
        "applied_time_extras": {},
        "columns":             columns,
        "metrics":             metrics,
        "annotation_layers":   [],
        "row_limit":           row_limit,
        "series_limit":        0,
        "order_desc":          True,
        "url_params":          {},
        "custom_params":       {},
        "custom_form_data":    {},
    }
    if granularity:
        query["granularity"] = granularity

    return json.dumps({
        "datasource":    {"id": dataset_id, "type": "table"},
        "force":         False,
        "result_format": "json",
        "result_type":   "full",
        "queries":       [query],
    })


class ApplyMixin:
    """Mixin that adds ``sync_*`` methods to a SupersetClient subclass."""

    # ----- databases -----

    def sync_database(self, database_name: str, properties: dict) -> None:
        if database_name in self._database_map:
            ref = self._database_map[database_name]
            self._update("/api/v1/database", ref.id, properties)
            log.info("  Updated: %s", database_name)
        else:
            response = self._create("/api/v1/database/", properties)
            result = response["result"]
            ref = DatabaseRef(
                id=response["id"],
                uuid=result.get("uuid"),
                database_name=database_name,
            )
            self._database_map[database_name] = ref
            log.info("  Created: %s (id=%s)", database_name, ref.id)

    def sync_databases(self) -> None:
        """Create or update database connections from ``databases/`` files."""
        self.list_databases()
        counter = 0
        for defn in self._iter_resources("databases"):
            name = defn.get("database_name", "?")
            try:
                self.sync_database(name, defn)
                counter += 1
                self._record("databases", name, ok=True)
            except Exception as exc:
                self._record("databases", name, ok=False)
                if self.safe_mode:
                    log.warning("  Skipped database '%s': %s", name, exc)
                else:
                    raise
        log.info("Databases synced: %d", counter)

    # ----- datasets -----

    def sync_dataset(
        self,
        table_name: str,
        schema: str | None,
        catalog: str | None,
        properties: dict,
    ) -> None:
        props = properties.copy()
        db_name = props.pop("database", None)
        db_id = None
        if db_name:
            db_ref = self._database_map.get(db_name)
            if db_ref is None:
                log.warning("Database '%s' not found — skipping dataset '%s'.", db_name, table_name)
                return
            db_id = db_ref.id

        if table_name not in self._dataset_map:
            creation_props = {k: props[k] for k in DatasetRef.CREATION_PARAMS if k in props}
            if db_id is not None:
                creation_props["database"] = db_id
            response = self._create("/api/v1/dataset/", creation_props)
            result = response["result"]
            ref = DatasetRef(
                id=response["id"],
                uuid=result.get("uuid"),
                catalog=catalog,
                schema=schema,
                table_name=table_name,
                database=db_id,
            )
            self._dataset_map[table_name] = ref
            log.info("  Created: %s (id=%s)", table_name, ref.id)

        # PUT does not accept 'database'; applies remaining fields
        self._update("/api/v1/dataset", self._dataset_map[table_name].id, props)
        log.info("  Updated: %s", table_name)

    def sync_datasets(self) -> None:
        """Create or update datasets from ``datasets/`` files."""
        self.list_databases()
        self.list_datasets()
        counter = 0
        for defn in self._iter_resources("datasets"):
            name = defn.get("table_name", "?")
            try:
                self.sync_dataset(name, defn.get("schema"), defn.get("catalog"), defn)
                counter += 1
                self._record("datasets", name, ok=True)
            except Exception as exc:
                self._record("datasets", name, ok=False)
                if self.safe_mode:
                    log.warning("  Skipped dataset '%s': %s", name, exc)
                else:
                    raise
        log.info("Datasets synced: %d", counter)

    # ----- charts -----

    def sync_chart(self, slice_name: str, properties: dict) -> None:
        props = properties.copy()
        viz_type = props["viz_type"]
        params = props.get("params", {})

        ds_table = props.pop("datasource_table", None)
        if ds_table:
            ds_ref = self._dataset_map.get(ds_table)
            if ds_ref is None:
                log.warning("Dataset '%s' not found — skipping chart '%s'.", ds_table, slice_name)
                return
            ds_id = ds_ref.id
            props["datasource_id"] = ds_id
            props.setdefault("datasource_type", "table")
        else:
            ds_id = props["datasource_id"]

        props["params"] = json.dumps({
            "datasource": f"{ds_id}__table",
            "viz_type": viz_type,
            "adhoc_filters": [],
            **params,
        })

        # Use the verbatim query_context stored by safe-mode export when available,
        # updating only the datasource ID for the current environment.
        qc_raw = props.pop("query_context_raw", None)
        if qc_raw:
            try:
                qc_obj = json.loads(qc_raw) if isinstance(qc_raw, str) else qc_raw
                qc_obj["datasource"]["id"] = ds_id
                props["query_context"] = json.dumps(qc_obj)
                log.debug("  Using query_context_raw for '%s'.", slice_name)
            except Exception as exc:
                log.warning("  Could not apply query_context_raw for '%s': %s — rebuilding.", slice_name, exc)
                props["query_context"] = _build_query_context(viz_type, ds_id, params)
        else:
            props["query_context"] = _build_query_context(viz_type, ds_id, params)

        if slice_name in self._chart_map:
            self._update("/api/v1/chart", self._chart_map[slice_name].id, props)
            log.info("  Updated: %s", slice_name)
        else:
            try:
                response = self._create("/api/v1/chart/", props)
            except RuntimeError as exc:
                if "500" in str(exc):
                    log.warning("  500 on create '%s', retrying without query_context...", slice_name)
                    response = self._create("/api/v1/chart/", {**props, "query_context": ""})
                else:
                    raise
            result = response.get("result") or {}
            ref = ChartRef(
                id=response["id"],
                uuid=result.get("uuid"),
                slice_name=slice_name,
                datasource_id=ds_id,
                datasource_type=props.get("datasource_type", "table"),
            )
            self._chart_map[slice_name] = ref
            log.info("  Created: %s (id=%s)", slice_name, ref.id)

    def sync_charts(self) -> None:
        """Create or update charts from ``charts/`` files."""
        self.list_datasets()
        self.list_charts()
        counter = 0
        for defn in self._iter_resources("charts"):
            name = defn.get("slice_name", "?")
            try:
                self.sync_chart(name, defn)
                counter += 1
                self._record("charts", name, ok=True)
            except Exception as exc:
                self._record("charts", name, ok=False)
                if self.safe_mode:
                    log.warning("  Skipped chart '%s': %s", name, exc)
                else:
                    raise
        log.info("Charts synced: %d", counter)

    # ----- dashboards -----

    def sync_dashboard(self, slug: str, properties: dict) -> None:
        defn = dict(properties)
        title = defn["dashboard_title"]
        raw_charts = defn.pop("charts", [])
        native_filters_def = defn.pop("native_filters", [])
        position_json_raw = defn.pop("position_json_raw", None)

        chart_entries: list[dict] = [
            ({"slice_name": c, "row": i, "col": 0, "width": 4, "height": 50}
             if isinstance(c, str) else c)
            for i, c in enumerate(raw_charts)
        ]

        charts_with_ids: list[dict] = []
        missing: list[str] = []
        for entry in chart_entries:
            ref = self._chart_map.get(entry["slice_name"])
            if ref is None:
                missing.append(entry["slice_name"])
                continue
            charts_with_ids.append({
                **entry,
                "chart_id": ref.id,
                "uuid": str(ref.uuid) if ref.uuid else "",
            })
        if missing:
            log.warning("  Charts not found (skipped): %s", missing)

        # Use verbatim position_json from safe-mode export when available,
        # remapping chartId values to the current environment's IDs.
        if position_json_raw:
            try:
                raw_pos = json.loads(position_json_raw) if isinstance(position_json_raw, str) else position_json_raw
                for node in raw_pos.values():
                    if isinstance(node, dict) and node.get("type") == "CHART":
                        chart_name = node.get("meta", {}).get("sliceName", "")
                        ref = self._chart_map.get(chart_name)
                        if ref:
                            node["meta"]["chartId"] = ref.id
                position_json = raw_pos
                log.debug("  Using position_json_raw for '%s'.", title)
            except Exception as exc:
                log.warning("  Could not apply position_json_raw for '%s': %s — rebuilding.", title, exc)
                position_json = build_position_json(charts_with_ids, title=title)
        else:
            position_json = build_position_json(charts_with_ids, title=title)

        native_filter_config = (
            build_native_filters(
                native_filters_def,
                {k: v.id for k, v in self._dataset_map.items()},
                charts_in_scope=[item["chart_id"] for item in charts_with_ids],
            )
            if native_filters_def else []
        )

        json_metadata: dict[str, Any] = {
            "native_filter_configuration": native_filter_config,
            "timed_refresh_immune_slices": [],
            "expanded_slices": {},
            "refresh_frequency": 0,
            "color_scheme": "",
            "label_colors": {},
            "shared_label_colors": {},
            "color_scheme_domain": [],
            "cross_filters_enabled": True,
            "chart_configuration": {},
            "global_chart_configuration": {
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "chartsInScope": [],
            },
            "filter_bar_orientation": defn.get("filter_bar_orientation", "HORIZONTAL"),
            "default_filters": "{}",
            "positions": position_json,
        }
        full_payload: dict[str, Any] = {
            "dashboard_title": title,
            "slug":            defn.get("slug"),
            "published":       defn.get("published", False),
            "position_json":   json.dumps(position_json),
            "json_metadata":   json.dumps(json_metadata),
        }

        if slug in self._dashboard_map:
            ref = self._dashboard_map[slug]
            log.info("  Updating: %s (id=%s)", title, ref.id)
        else:
            response = self._create("/api/v1/dashboard/", {
                "dashboard_title": title,
                "slug":      defn.get("slug"),
                "published": defn.get("published", False),
            })
            result = response.get("result") or {}
            ref = DashboardRef(
                id=response["id"],
                uuid=result.get("uuid"),
                slug=slug,
                dashboard_title=title,
            )
            self._dashboard_map[slug] = ref
            log.info("  Created: %s (id=%s)", title, ref.id)

        self._update("/api/v1/dashboard", ref.id, full_payload)
        log.info("  Layout and charts applied: %s", title)

        try:
            embed_uuid = _enable_embedding(self.session, self.url, ref.id)
            log.info("  Embedding enabled: uuid=%s", embed_uuid)
            log.info(
                "  Set in .env: VITE_DASHBOARD_%s_UUID=%s",
                defn.get("slug", title).upper().replace("-", "_"),
                embed_uuid,
            )
        except Exception as exc:
            log.warning("  Could not enable embedding: %s", exc)

    def sync_dashboards(self) -> None:
        """Create or update dashboards from ``dashboards/`` files."""
        self.list_datasets()
        self.list_charts()
        self.list_dashboards()
        counter = 0
        for defn in self._iter_resources("dashboards"):
            slug = defn.get("slug") or defn["dashboard_title"]
            try:
                self.sync_dashboard(slug, defn)
                counter += 1
                self._record("dashboards", slug, ok=True)
            except Exception as exc:
                self._record("dashboards", slug, ok=False)
                if self.safe_mode:
                    log.warning("  Skipped dashboard '%s': %s", slug, exc)
                else:
                    raise
        log.info("Dashboards synced: %d", counter)
