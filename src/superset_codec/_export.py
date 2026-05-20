"""Export mixin — _export_* methods that write Superset resources to YAML files."""
import json
import logging
import uuid as _uuid_mod
from typing import Any

from ._filters import simplify_native_filter
from ._interpolate import inverse_interpolate
from ._positions import decompose_position_json

log = logging.getLogger(__name__)


class ExportMixin:
    """Mixin that adds ``export`` and ``_export_*`` methods to a SupersetClient subclass."""

    def _build_inverse_maps(self) -> None:
        """Populate ``_id_to_*`` dicts used to resolve IDs back to names during export."""
        self._id_to_database:  dict[int, str] = {r.id: r.database_name for r in self.list_databases()}
        self._id_to_dataset:   dict[int, str] = {r.id: r.table_name    for r in self.list_datasets()}
        self._id_to_chart:     dict[int, str] = {r.id: r.slice_name    for r in self.list_charts()}
        self._id_to_dashboard: dict[int, str] = {r.id: r.slug          for r in self.list_dashboards()}

    def _validate_chart(self, slice_name: str, raw: dict) -> bool:
        """Create a temp copy of the chart, verify its query executes, then delete it.

        Returns True if the chart can be applied and renders data without error.
        The temp chart is always deleted in the finally block.
        """
        temp_name = f"_tmp_{_uuid_mod.uuid4().hex[:6]}_{slice_name}"[:200]
        chart_id = None
        try:
            payload = {
                "slice_name":      temp_name,
                "viz_type":        raw.get("viz_type", ""),
                "datasource_id":   raw.get("datasource_id"),
                "datasource_type": raw.get("datasource_type", "table"),
                "params":          raw.get("params", "{}"),
                "query_context":   raw.get("query_context", ""),
            }
            resp = self._create("/api/v1/chart/", payload)
            chart_id = resp["id"]

            # Verify the query actually reaches the data source without error.
            qc_str = raw.get("query_context") or "{}"
            qc = json.loads(qc_str) if isinstance(qc_str, str) else qc_str
            if qc:
                data_resp = self.session.post(
                    f"{self.url}/api/v1/chart/data",
                    json=qc,
                    timeout=30,
                )
                if data_resp.status_code >= 400:
                    log.warning(
                        "  Validate FAIL '%s': data endpoint %s — %s",
                        slice_name, data_resp.status_code, data_resp.text[:300],
                    )
                    return False

            log.info("  Validated OK: %s", slice_name)
            return True

        except Exception as exc:
            log.warning("  Validate ERROR '%s': %s", slice_name, exc)
            return False
        finally:
            if chart_id is not None:
                try:
                    self._delete("/api/v1/chart", chart_id)
                    log.debug("  Temp chart deleted (id=%s)", chart_id)
                except Exception as exc:
                    log.warning("  Could not delete temp chart id=%s: %s — delete manually", chart_id, exc)

    def _export_databases(self) -> None:
        from .writer import write
        KEEP = {
            "database_name", "sqlalchemy_uri", "expose_in_sqllab", "allow_run_async",
            "allow_cvas", "allow_dml", "allow_file_upload", "cache_timeout",
            "configuration_method", "driver", "engine",
        }
        for ref in self._database_map.values():
            try:
                raw = self._get_resource("/api/v1/database", ref.id)
                data = {k: v for k, v in raw.items() if k in KEEP and v is not None}
                # sqlalchemy_uri is not returned by the main endpoint for security reasons;
                # fetch it via /connection which returns the URI with a masked password.
                if "sqlalchemy_uri" not in data:
                    try:
                        conn = self._get_resource("/api/v1/database", ref.id, suffix="/connection")
                        uri = conn.get("sqlalchemy_uri") or conn.get("parameters", {}).get("sqlalchemy_uri")
                        if uri:
                            data["sqlalchemy_uri"] = uri
                            log.debug("  URI fetched via /connection: %s", uri)
                    except Exception as exc:
                        log.warning("  Could not fetch sqlalchemy_uri for %s: %s", ref.database_name, exc)
                if self.variables:
                    data = inverse_interpolate(data, self.variables)
                path = write(self._resources_dir, "databases", ref.database_name, data)
                log.info("  Exported: %s → %s", ref.database_name, path)
                self._record("databases", ref.database_name, ok=True)
            except Exception as exc:
                self._record("databases", ref.database_name, ok=False)
                log.warning("  Failed to export database '%s': %s", ref.database_name, exc)
                if not self.safe_mode:
                    raise

    def _export_datasets(self) -> None:
        from .writer import write
        KEEP = {
            "table_name", "schema", "catalog", "sql", "description",
            "main_dttm_col", "offset", "default_endpoint", "cache_timeout",
            "is_sqllab_view", "template_params", "filter_select_enabled",
        }
        for table_name, ref in self._dataset_map.items():
            try:
                raw = self._get_resource("/api/v1/dataset", ref.id)
                data = {k: v for k, v in raw.items() if k in KEEP and v is not None}
                db_raw = raw.get("database")
                db_id = db_raw.get("id") if isinstance(db_raw, dict) else db_raw
                data["database"] = self._id_to_database.get(db_id, str(db_id))
                if self.variables:
                    data = inverse_interpolate(data, self.variables)
                path = write(self._resources_dir, "datasets", table_name, data)
                log.info("  Exported: %s → %s", table_name, path)
                self._record("datasets", table_name, ok=True)
            except Exception as exc:
                self._record("datasets", table_name, ok=False)
                log.warning("  Failed to export dataset '%s': %s", table_name, exc)
                if not self.safe_mode:
                    raise

    def _export_charts(self) -> None:
        from .writer import write
        for slice_name, ref in self._chart_map.items():
            try:
                raw = self._get_resource("/api/v1/chart", ref.id)
                params_raw = raw.get("params") or "{}"
                try:
                    params = json.loads(params_raw) if isinstance(params_raw, str) else params_raw
                except json.JSONDecodeError:
                    params = {}
                for key in ("datasource", "url_params"):
                    params.pop(key, None)
                ds_id = raw.get("datasource_id")
                data: dict[str, Any] = {
                    "slice_name":       slice_name,
                    "viz_type":         raw.get("viz_type", ""),
                    "datasource_table": self._id_to_dataset.get(ds_id, str(ds_id)),
                    "params":           params,
                }
                if self.safe_mode:
                    # Store the verbatim query_context from Superset so apply can
                    # restore it directly, guaranteeing roundtrip for any viz_type.
                    qc = raw.get("query_context")
                    if qc:
                        data["query_context_raw"] = qc

                if self.validate:
                    self._validate_chart(slice_name, raw)

                path = write(self._resources_dir, "charts", slice_name, data)
                log.info("  Exported: %s → %s", slice_name, path)
                self._record("charts", slice_name, ok=True)
            except Exception as exc:
                self._record("charts", slice_name, ok=False)
                log.warning("  Failed to export chart '%s': %s", slice_name, exc)
                if not self.safe_mode:
                    raise

    def _export_dashboards(self) -> None:
        from .writer import write
        for slug, ref in self._dashboard_map.items():
            try:
                raw = self._get_resource("/api/v1/dashboard", ref.id)

                positions_raw = raw.get("position_json") or "{}"
                try:
                    positions = json.loads(positions_raw) if isinstance(positions_raw, str) else positions_raw
                except json.JSONDecodeError:
                    positions = {}
                charts = decompose_position_json(positions, self._id_to_chart)

                metadata_raw = raw.get("json_metadata") or "{}"
                try:
                    metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                except json.JSONDecodeError:
                    metadata = {}

                native_filters = [
                    simplify_native_filter(f, self._id_to_dataset, safe_mode=self.safe_mode)
                    for f in metadata.get("native_filter_configuration", [])
                ]

                data: dict[str, Any] = {
                    "dashboard_title": raw.get("dashboard_title", ""),
                    "slug":            slug,
                    "published":       raw.get("published", False),
                    "charts":          charts,
                }
                if native_filters:
                    data["native_filters"] = native_filters
                fbo = metadata.get("filter_bar_orientation")
                if fbo:
                    data["filter_bar_orientation"] = fbo
                if self.safe_mode:
                    # Store the verbatim position_json from Superset so apply can
                    # restore non-chart elements (MARKDOWN, DIVIDER, COLUMN) exactly.
                    data["position_json_raw"] = positions_raw

                path = write(self._resources_dir, "dashboards", slug, data)
                log.info("  Exported: %s → %s", slug, path)
                self._record("dashboards", slug, ok=True)
            except Exception as exc:
                self._record("dashboards", slug, ok=False)
                log.warning("  Failed to export dashboard '%s': %s", slug, exc)
                if not self.safe_mode:
                    raise

    def export(self, steps: list[str] | None = None) -> None:
        """Export Superset resources to declarative YAML files.

        Args:
            steps: steps to run; ``None`` runs all.
                   Valid values: ``databases``, ``datasets``, ``charts``, ``dashboards``.
        """
        self._build_inverse_maps()
        pipeline = [
            ("databases",  self._export_databases),
            ("datasets",   self._export_datasets),
            ("charts",     self._export_charts),
            ("dashboards", self._export_dashboards),
        ]
        active = steps or [name for name, _ in pipeline]
        for name, fn in pipeline:
            if name in active:
                log.info("=== EXPORT %s ===", name.upper())
                fn()
        log.info("Export complete: %s", self._resources_dir)
