"""SupersetCodec — public entry point combining client, apply, and export."""
import logging
from typing import Any

from ._apply import ApplyMixin
from ._client import SupersetClient
from ._export import ExportMixin

log = logging.getLogger(__name__)


class SupersetCodec(SupersetClient, ApplyMixin, ExportMixin):
    """Idempotent codec for Apache Superset resources.

    Dependency order (apply):
        databases → datasets → charts → dashboards

    UI-first workflow:
        Superset UI (dev) → export → Git → apply → Superset (staging/prod)

    Safe mode (``safe_mode=True`` or ``--safe`` CLI flag):
        - export: stores verbatim Superset fields (``query_context_raw``,
          ``position_json_raw``, ``_raw`` for unknown filter types) alongside
          the simplified representation, guaranteeing roundtrip for any
          viz_type, layout element, or filter type.
        - apply: uses raw fields when present; on per-resource errors, logs a
          warning and continues instead of aborting the entire pipeline.
    """

    def apply(self, steps: list[str] | None = None, *, safe: bool = False) -> None:
        """Apply declarative resources to Superset (idempotent).

        Args:
            steps: steps to run; ``None`` runs all.
                   Valid values: ``databases``, ``datasets``, ``charts``, ``dashboards``.
            safe:  if True, per-resource errors are logged as warnings and
                   skipped instead of aborting the pipeline.
        """
        if safe:
            self.safe_mode = True
        pipeline: list[tuple[str, Any]] = [
            ("databases",  self.sync_databases),
            ("datasets",   self.sync_datasets),
            ("charts",     self.sync_charts),
            ("dashboards", self.sync_dashboards),
        ]
        for name, fn in pipeline:
            if steps is None or name in steps:
                log.info("=== %s ===", name.upper())
                try:
                    fn()
                except Exception as exc:
                    if self.safe_mode:
                        log.warning("Error in step %s (continuing in safe mode): %s", name, exc)
                    else:
                        log.error("Error applying %s: %s", name, exc)
                        raise
        self.print_summary()

    def export(
        self,
        steps: list[str] | None = None,
        *,
        safe: bool = False,
        no_validate: bool = False,
    ) -> None:
        """Export Superset resources to declarative YAML files.

        Args:
            steps:       steps to run; ``None`` runs all.
                         Valid values: ``databases``, ``datasets``, ``charts``, ``dashboards``.
            safe:        if True, stores verbatim raw fields (``query_context_raw``,
                         ``position_json_raw``, ``_raw`` filters) alongside the simplified
                         representation to guarantee roundtrip for any viz_type.
            no_validate: if True, skips the per-chart roundtrip validation (create temp
                         chart, test data endpoint, delete). Default is to validate.
        """
        if safe:
            self.safe_mode = True
        if no_validate:
            self.validate = False
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
        self.print_summary()
