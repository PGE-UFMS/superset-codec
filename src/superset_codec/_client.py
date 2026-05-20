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
    ):
        self.url = url.rstrip("/")
        self._user = user
        self._password = password
        self._resources_dir = Path(resources_dir)
        self._session: requests.Session | None = None
        self.variables = variables

        self._database_map:  dict[str, DatabaseRef] = {}
        self._dataset_map:   dict[str, DatasetRef]  = {}
        self._chart_map:     dict[str, ChartRef]    = {}
        self._dashboard_map: dict[str, DashboardRef] = {}

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
        self._dataset_map = {}
        for k, v in self._map_by_field(ids, items, "table_name").items():
            database_id = v.pop("database")["id"]
            self._dataset_map[k] = DatasetRef(database=database_id, **v)
        return self._dataset_map.values()

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
