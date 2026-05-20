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
    """

    def apply(self, steps: list[str] | None = None) -> None:
        """Apply declarative resources to Superset (idempotent).

        Args:
            steps: steps to run; ``None`` runs all.
                   Valid values: ``databases``, ``datasets``, ``charts``, ``dashboards``.
        """
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
                    log.error("Error applying %s: %s", name, exc)
                    raise
