import json
import logging
import re
from pathlib import Path
from typing import Iterable

import requests

from .models import ChartRef, DashboardRef, DatabaseRef, DatasetRef
from ._interpolate import get_by_path, interpolate

log = logging.getLogger(__name__)


class SupersetClient:
    """Low-level Superset REST API client.

    Handles authentication, HTTP primitives (create/update/list/get),
    and in-memory resource maps populated by ``list_*`` methods.
    """

    def __init__(
        self,
        url: str,
        user: str,
        password: str,
        resources_dir: Path | str = "./resources",
        variables: dict[str, str] = {},
        safe_mode: bool = False,
    ):
        self.url = url.rstrip("/")
        self._user = user
        self._password = password
        self._resources_dir = Path(resources_dir)
        self._session: requests.Session | None = None
        self.variables = variables
        self.safe_mode = safe_mode
        self.validate = True

        self._database_map:  dict[str, DatabaseRef] = {}
        self._dataset_map:   dict[tuple[str | None, str | None, str], DatasetRef] = {}
        self._chart_map:     dict[str, ChartRef]    = {}
        self._dashboard_map: dict[str, DashboardRef] = {}

        self._summary: dict[str, dict[str, list[str]]] = {
            step: {"ok": [], "fail": []}
            for step in ("databases", "datasets", "charts", "dashboards")
        }

    # ------------------------------------------------------------------
    # Session / auth
    # ------------------------------------------------------------------

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = self._authenticate()
        return self._session

    def _authenticate(self) -> requests.Session:
        log.debug("Authenticating at %s as '%s'...", self.url, self._user)
        session = requests.Session()

        resp = session.post(
            f"{self.url}/api/v1/security/login",
            json={"username": self._user, "password": self._password,
                  "provider": "db", "refresh": True},
            timeout=15,
        )
        resp.raise_for_status()
        session.headers.update({"Authorization": f"Bearer {resp.json()['access_token']}"})

        # Flask-Login session — required so current_user resolves correctly
        # inside the ORM (cascade of owners on charts/dashboards).
        login_page = session.get(f"{self.url}/login/", timeout=10)
        form_csrf = ""
        m = re.search(r'name="csrf_token"[^>]+value="([^"]+)"', login_page.text)
        if not m:
            m = re.search(r'value="([^"]+)"[^>]+name="csrf_token"', login_page.text)
        if m:
            form_csrf = m.group(1)
        session.post(
            f"{self.url}/login/",
            data={"username": self._user, "password": self._password, "csrf_token": form_csrf},
            allow_redirects=True,
            timeout=15,
        )
        log.debug("Flask-Login session established.")

        csrf_resp = session.get(f"{self.url}/api/v1/security/csrf_token/", timeout=10)
        csrf_resp.raise_for_status()
        session.headers.update({
            "X-CSRFToken": csrf_resp.json()["result"],
            "Referer": self.url,
        })
        log.debug("Authentication complete.")
        return session

    # ------------------------------------------------------------------
    # HTTP primitives
    # ------------------------------------------------------------------

    def _create(self, api_path: str, payload: dict) -> dict:
        log.debug("POST %s\n%s", api_path, json.dumps(payload, indent=2, ensure_ascii=False))
        resp = self.session.post(f"{self.url}{api_path}", json=payload, timeout=30)
        log.debug("  → %s %s", resp.status_code, resp.text[:500] if not resp.ok else "OK")
        if not resp.ok:
            raise RuntimeError(f"POST {api_path} → {resp.status_code}: {resp.text}")
        return resp.json()

    def _update(self, api_path: str, resource_id: int, payload: dict) -> dict:
        log.debug("PUT %s/%s\n%s", api_path, resource_id,
                  json.dumps(payload, indent=2, ensure_ascii=False))
        resp = self.session.put(f"{self.url}{api_path}/{resource_id}", json=payload, timeout=30)
        log.debug("  → %s %s", resp.status_code, resp.text[:500] if not resp.ok else "OK")
        if not resp.ok:
            raise RuntimeError(f"PUT {api_path}/{resource_id} → {resp.status_code}: {resp.text}")
        return resp.json()

    def _delete(self, api_path: str, resource_id: int) -> None:
        resp = self.session.delete(f"{self.url}{api_path}/{resource_id}", timeout=15)
        if not resp.ok:
            raise RuntimeError(f"DELETE {api_path}/{resource_id} → {resp.status_code}: {resp.text}")

    def _get_resource(self, api_path: str, resource_id: int, suffix: str = "") -> dict:
        resp = self.session.get(f"{self.url}{api_path}/{resource_id}{suffix}", timeout=15)
        resp.raise_for_status()
        return resp.json()["result"]

    def _list_resources(self, api_path: str, *columns: str) -> tuple[list[int], list[dict]]:
        query: dict = {"page_size": -1}
        if columns:
            query["columns"] = list(columns)
        resp = self.session.get(
            f"{self.url}{api_path}",
            params={"q": json.dumps(query)},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["ids"], data["result"]

    @staticmethod
    def _map_by_field(ids: list[int], items: list[dict], field: str) -> dict[str, dict]:
        d: dict[str, dict] = {}
        for resource_id, item in zip(ids, items, strict=True):
            key = get_by_path(item, field)
            if key in d:
                log.warning("Duplicate resource key '%s'", key)
            item["id"] = resource_id
            d[key] = item
        return d

    @staticmethod
    def _resolve_id(result: dict) -> int | None:
        return result.get("id") or (result.get("result") or {}).get("id")

    def _record(self, step: str, name: str, *, ok: bool) -> None:
        bucket = "ok" if ok else "fail"
        self._summary[step][bucket].append(name)

    def print_summary(self) -> None:
        """Print a summary table and, if there are failures, a friendly list."""
        STEPS = ("databases", "datasets", "charts", "dashboards")
        all_names = [n for s in STEPS for n in self._summary[s]["ok"] + self._summary[s]["fail"]]
        name_w = max((len(n) for n in all_names), default=0, )
        name_w = max(name_w, len("Resource"))
        step_w = len("dashboards")
        sep = "-" * (name_w + step_w + len("  Status  ") + 2)

        lines = [sep, f"{'Resource':<{name_w}}  {'Step':<{step_w}}  Status", sep]
        any_row = False
        for step in STEPS:
            for name in self._summary[step]["ok"]:
                lines.append(f"{name:<{name_w}}  {step:<{step_w}}  OK")
                any_row = True
            for name in self._summary[step]["fail"]:
                lines.append(f"{name:<{name_w}}  {step:<{step_w}}  FAIL")
                any_row = True
        if not any_row:
            lines.append("  (no resources processed)")

        ok_total   = sum(len(self._summary[s]["ok"])   for s in STEPS)
        fail_total = sum(len(self._summary[s]["fail"]) for s in STEPS)
        lines += [sep, f"  {ok_total} OK  |  {fail_total} FAIL", sep]
        log.info("\n" + "\n".join(lines))

        if fail_total:
            failed_lines = ["", "The following resources could not be processed:"]
            for step in STEPS:
                for name in self._summary[step]["fail"]:
                    failed_lines.append(f"  - [{step}] {name}")
            failed_lines.append("")
            log.warning("\n".join(failed_lines))

    # ------------------------------------------------------------------
    # Resource list methods (populate in-memory maps)
    # ------------------------------------------------------------------

    def list_databases(self) -> Iterable[DatabaseRef]:
        ids, items = self._list_resources("/api/v1/database/", "database_name", "uuid")
        self._database_map = {
            k: DatabaseRef(**v)
            for k, v in self._map_by_field(ids, items, "database_name").items()
        }
        return self._database_map.values()

    def list_datasets(self) -> Iterable[DatasetRef]:
        ids, items = self._list_resources(
            "/api/v1/dataset/", "catalog", "schema", "table_name", "database.id", "uuid"
        )
        self._dataset_map = self._build_dataset_map(ids, items)
        return self._dataset_map.values()

    @staticmethod
    def _build_dataset_map(
        ids: list[int], items: list[dict]
    ) -> dict[tuple[str | None, str | None, str], DatasetRef]:
        out: dict[tuple[str | None, str | None, str], DatasetRef] = {}
        for resource_id, item in zip(ids, items, strict=True):
            database_id = item.pop("database")["id"]
            ref = DatasetRef(id=resource_id, database=database_id, **item)
            key = ref.provision_key()
            if key in out:
                log.warning("Duplicate dataset key %s", key)
            out[key] = ref
        return out

    def find_dataset_by_table_name(self, table_name: str) -> DatasetRef | None:
        """Resolve a dataset by its ``table_name`` alone.

        Warns when multiple datasets share the table name and returns the first match.
        Prefer :meth:`resolve_dataset_ref` to disambiguate via ``catalog``/``schema``.
        """
        matches = [r for r in self._dataset_map.values() if r.table_name == table_name]
        if len(matches) > 1:
            keys = [r.provision_key() for r in matches]
            log.warning(
                "Ambiguous dataset table_name '%s' matches %s — using first.",
                table_name, keys,
            )
        return matches[0] if matches else None

    def resolve_dataset_ref(self, ref: str | dict) -> DatasetRef | None:
        """Resolve a YAML dataset reference (string or dict) to a ``DatasetRef``.

        - ``"orders"`` → fuzzy lookup by ``table_name`` (warns on ambiguity).
        - ``{"table_name": "orders", "schema": "public", "catalog": "prod"}`` →
          exact lookup by ``(catalog, schema, table_name)``; missing keys default to None.
        """
        if isinstance(ref, dict):
            key = (ref.get("catalog"), ref.get("schema"), ref["table_name"])
            return self._dataset_map.get(key)
        if isinstance(ref, str):
            return self.find_dataset_by_table_name(ref)
        return None

    def list_charts(self) -> Iterable[ChartRef]:
        ids, items = self._list_resources(
            "/api/v1/chart/", "slice_name", "datasource_id", "datasource_type", "uuid"
        )
        self._chart_map = {
            k: ChartRef(**v)
            for k, v in self._map_by_field(ids, items, "slice_name").items()
        }
        return self._chart_map.values()

    def list_dashboards(self) -> Iterable[DashboardRef]:
        ids, items = self._list_resources(
            "/api/v1/dashboard/", "slug", "dashboard_title", "uuid"
        )
        self._dashboard_map = {
            k: DashboardRef(**v)
            for k, v in self._map_by_field(ids, items, "slug").items()
        }
        return self._dashboard_map.values()

    # ------------------------------------------------------------------
    # Resource file reader
    # ------------------------------------------------------------------

    def _iter_resources(self, resource_type: str) -> Iterable[dict]:
        """Yield dicts from all *.yaml / *.json files under resources_dir/resource_type/.

        Supports sub-folders and ``${VAR}`` interpolation.
        """
        from ruamel.yaml import YAML as _YAML

        directory = self._resources_dir / resource_type
        if not directory.exists():
            log.debug("Directory '%s' not found — skipping.", directory)
            return

        files = sorted(
            list(directory.glob("**/*.yaml")) + list(directory.glob("**/*.json"))
        )
        for path in files:
            try:
                text = interpolate(path.read_text(encoding="utf-8"), self.variables)
                if path.suffix == ".yaml":
                    data = dict(_YAML().load(text))
                else:
                    data = json.loads(text)
                    data.pop("$schema", None)
                log.info("Reading %s", path.name)
                yield data
            except Exception as exc:
                log.warning("Skipping %s: %s", path.name, exc)
