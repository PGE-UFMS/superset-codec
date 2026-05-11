import logging
import json
import re
import requests
from pathlib import Path
from typing import Any, Iterable, Sequence
from .models import ChartRef, DashboardRef, DatabaseRef, DatasetRef

from uuid import UUID

log = logging.getLogger(__name__)

def _interpolate(text: str, variables: dict[str]) -> str:
    """Replace ``${VAR}`` with the corresponding variable value.

    Unknown variables are left as-is (i.e. ``${MISSING}`` stays ``${MISSING}``).
    """
    return re.sub(r"\$\{([^}]+)\}", lambda m: variables.get(m.group(1), m.group(0)), text)

def _get_by_path(d: dict, path: str, default=None, sep="."):
    """Acessa valores em dicionários aninhados usando uma notação de caminho.

    Args:
        d:       Dicionário raiz a ser percorrido.
        path:    Caminho até o valor desejado, com chaves separadas por ``sep``.
                 Exemplo: ``"foo.bar.baz"`` equivale a ``d["foo"]["bar"]["baz"]``.
        default: Valor retornado quando qualquer chave não é encontrada ou
                 quando um nível intermediário não é um dicionário.
                 Padrão: ``None``.
        sep:     Separador de chaves. Padrão: ``"."``.

    Returns:
        O valor encontrado no caminho especificado, ou ``default`` caso alguma
        chave não exista ou um nível intermediário não seja um ``dict``.

    Examples:
        ```
        >>> data = {"foo": {"bar": {"baz": 42}}}
        >>> _get_by_path(data, "foo.bar.baz")
        42
        >>> _get_by_path(data, "foo.bar.missing", default=0)
        0
        >>> _get_by_path(data, "foo.bar.baz.deep")  # nível intermediário não é dict
        None
        ```
    """
    value = d
    for key in path.split(sep):
        if not isinstance(value, dict):
            return default

        value = value.get(key, default)
        if value is default:
            return default

    return value

class SupersetProvisioner:
    """
    Provisionador idempotente de recursos do Superset.

    Ordem de execução obrigatória (dependências em cascata):
        databases → datasets → charts → dashboards
    
    Gerencia ids de recurso automaticamente.
    Para isso, utiliza referências de recursos por nome:
    - Database:         database_name
    - Dataset:          [[catalog.]schema.]table_name
    - Chart (slice):    slice_name
    - Dashboard:        slug

    Alguns recursos referenciam outros recursos por id inteiro:
    - Dataset:          database
    - Chart (slice):    datasource_id (Dataset), datasource_type
        - Optional:     datasource_name
    - Dashboard:        charts[].slice_name
    """

    def __init__(self,
            url: str,
            user: str,
            password: str,
            resources_dir: Path | str = "./resources",
            variables: dict[str] = {}
        ):
        self.url = url.rstrip("/")
        self._user = user
        self._password = password
        self._resources_dir = Path(resources_dir)
        self._session: requests.Session | None = None
        self.variables = variables
        self._database_map: dict[str,DatabaseRef] = {}
        self._dataset_map: dict[str,DatasetRef] = {}
        self._chart_map: dict[str,ChartRef] = {}
        self._dashboard_map: dict[str,DashboardRef] = {}

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = self._authenticate()
        return self._session

    def _authenticate(self) -> requests.Session:
        log.debug("Autenticando em %s como '%s'...", self.url, self._user)
        session = requests.Session()

        resp = session.post(
            f"{self.url}/api/v1/security/login",
            json={
                "username": self._user,
                "password": self._password,
                "provider": "db",
                "refresh": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})

        # 2. Sessão Flask-Login — necessária para que current_user seja resolvido
        #    corretamente dentro do ORM (cascade de owners em charts/dashboards).
        #    Sem este passo, current_user fica como AnonymousUserMixin.
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
        log.debug("Sessão Flask-Login estabelecida.")

        # 3. CSRF token para as APIs REST
        csrf_resp = session.get(f"{self.url}/api/v1/security/csrf_token/", timeout=10)
        csrf_resp.raise_for_status()
        session.headers.update({
            "X-CSRFToken": csrf_resp.json()["result"],
            "Referer": self.url,
        })
        log.debug("Autenticação concluída.")
        return session

    def _iter_resources(self, resource_type: str) -> Iterable[dict]:
        """
        Carrega todos os arquivos *.json de {resources_dir}/{resource_type}/ recursivamente.
        Suporta subpastas e interpolação ${ENV_VAR} nos valores.
        """
        directory = self._resources_dir / resource_type
        if not directory.exists():
            log.debug("Diretório '%s' não encontrado — pulando.", directory)
            return

        for path in sorted(directory.glob("*.json")):
            try:
                text = _interpolate(path.read_text(encoding="utf-8"), self.variables)
                data = json.loads(text)
                data.pop("$schema", None) # Allow schema reference in json files
                log.info("Lendo %s", path.name)
                yield data
            except Exception as e:
                log.warning("Ignorando %s: %s", path.name, e)

    def _list_resources(self, api_path: str, *columns: str) -> (list[int], list[dict]):
        query = {"page_size": -1}
        if len(columns) > 0:
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
    def _map_by_fields(ids: list[int], items: list[dict], *fields: str) -> dict[tuple[str,...],dict]:
        """Retorna {(field,...): item} para todos os recursos existentes na API."""
        d = {}
        for id, item in zip(ids, items, strict=True):
            key = tuple(_get_by_path(item, field) for field in fields)
            if key in d:
                log.warning(f"Recurso com chave {key} duplicada")
            item["id"] = id
            d[key] = id
        return d

    @staticmethod
    def _map_by_field(ids: list[int], items: list[dict], field: str) -> dict[str,dict]:
        """Retorna {field: item} para todos os recursos existentes na API."""
        d = {}
        for id, item in zip(ids, items, strict=True):
            key = _get_by_path(item, field)
            if key in d:
                log.warning(f"Recurso com chave '{key}' duplicada")
            item["id"] = id
            d[key] = item
        return d

    def _create(self, api_path: str, payload: dict) -> dict:
        log.debug("POST %s\n  payload: %s", api_path, json.dumps(payload, indent=2, ensure_ascii=False))
        resp = self.session.post(f"{self.url}{api_path}", json=payload, timeout=30)
        log.debug("  → %s %s", resp.status_code, resp.text[:500] if not resp.ok else "OK")
        if not resp.ok:
            raise RuntimeError(f"POST {api_path} → {resp.status_code}: {resp.text}")
        return resp.json()

    def _update(self, api_path: str, resource_id: int, payload: dict) -> dict:
        log.debug("PUT %s/%s\n  payload: %s", api_path, resource_id, json.dumps(payload, indent=2, ensure_ascii=False))
        resp = self.session.put(f"{self.url}{api_path}/{resource_id}", json=payload, timeout=30)
        log.debug("  → %s %s", resp.status_code, resp.text[:500] if not resp.ok else "OK")
        if not resp.ok:
            raise RuntimeError(f"PUT {api_path}/{resource_id} → {resp.status_code}: {resp.text}")
        return resp.json()

    def _resolve_id(self, result: dict) -> int | None:
        """Extrai o id da resposta de criação do Superset (formatos variam)."""
        return result.get("id") or (result.get("result") or {}).get("id")

    def list_databases(self) -> Iterable[DatabaseRef]:
        ids, items = self._list_resources("/api/v1/database/", "database_name", "uuid")
        d = {
            k: DatabaseRef(**v)
            for k, v in self._map_by_field(ids, items, "database_name").items()
        }
        self._database_map = d
        return d.values()

    def list_datasets(self) -> Iterable[DatasetRef]:
        ids, items = self._list_resources("/api/v1/dataset/", "catalog", "schema", "table_name", "database.id", "uuid")
        d = {}
        # TODO incluir catalog e schema
        for k, v in self._map_by_field(ids, items, "table_name").items():
            database_id = v.pop("database")["id"]
            d[k] = DatasetRef(database=database_id, **v)
        self._dataset_map = d
        return d.values()

    def list_charts(self) -> Iterable[ChartRef]:
        ids, items = self._list_resources("/api/v1/chart/", "slice_name", "datasource_id", "datasource_type", "uuid")
        d = {
            k: ChartRef(**v)
            for k, v in self._map_by_field(ids, items, "slice_name").items()
        }
        self._chart_map = d
        return d.values()
    
    def list_dashboards(self) -> Iterable[DashboardRef]:
        ids, items = self._list_resources("/api/v1/chart/", "slug", "dashboard_title", "uuid")
        d = {
            k: DashboardRef(**v)
            for k, v in self._map_by_field(ids, items, "slug").items()
        }
        self._dashboard_map = d
        return d.values()

    def sync_database(self, database_name: str, properties: dict):
        if database_name in self._database_map:
            ref = self._database_map[database_name]
            self._update("/api/v1/database", ref.id, properties)
            log.info("  Atualizado: %s", database_name)
        else:
            result = self._create("/api/v1/database/", properties)
            ref = DatabaseRef(
                id=result["id"],
                uuid=result["uuid"],
                database_name=database_name,
            )
            self._database_map[database_name] = ref
            log.info("  Criado: %s (id=%s)", database_name, ref.id)

    def sync_databases(self):
        """
        Cria ou atualiza conexões de banco de dados.
        """

        self.list_databases()

        counter = 0
        for defn in self._iter_resources("databases"):
            self.sync_database(defn["database_name"], defn)
            counter += 1

        log.info("Conexões de bancos de dados sincronizadas: %d", counter)

    def sync_dataset(self, table_name: str, schema: str | None, catalog: str | None, properties: dict):
        # TODO Trocar para database_name para não confundir o database: str com o database: int
        props = properties.copy()
        db_name = props.pop("database", None)
        db_id = None
        if db_name:
            db_ref = self._database_map.get(db_name)
            if db_ref is None:
                log.warning("  Database '%s' não encontrado — pulando dataset '%s'.", db_name, table_name)
                return
            db_id = db_ref.id

        if table_name not in self._dataset_map:
            creation_props = {k: props[k] for k in DatasetRef.CREATION_PARAMS if k in props}
            if db_id is not None:
                creation_props["database"] = db_id
            result = self._create("/api/v1/dataset/", creation_props)
            ref = DatasetRef(
                id=result["id"],
                uuid=result["uuid"],
                catalog=catalog,
                schema=schema,
                table_name=table_name,
                database=db_id,
            )
            self._dataset_map[table_name] = ref
            log.info("  Criado: %s (id=%s)", ref.table_name, ref.id)

        # PUT /api/v1/dataset/ não aceita 'database'; aplica demais campos
        # (inclui metrics, columns e main_dttm_col, que o POST também não aceita)
        self._update("/api/v1/dataset", self._dataset_map[table_name].id, props)
        log.info("  Atualizado: %s", table_name)

    def sync_datasets(self):
        """
        Cria ou atualiza datasets (tabelas físicas ou virtuais).

        Cada arquivo em {resources_dir}/datasets/*.json deve conter
        'table_name' e 'database' (nome da conexão, resolvido para ID).
        Opcionalmente: 'schema', 'sql' (para datasets virtuais),
        'columns' e 'metrics' (aplicados via PUT separado após criação).
        """
        self.list_databases()
        self.list_datasets()

        counter = 0
        for defn in self._iter_resources("datasets"):
            self.sync_dataset(
                defn["table_name"],
                defn.get("schema"),
                defn.get("catalog"),
                defn,
            )
            counter += 1

        log.info("Datasets sincronizados: %d", counter)

    def sync_charts(self):
        """
        Cria ou atualiza charts.

        Cada arquivo em {resources_dir}/charts/*.json deve conter:
        - 'slice_name': nome do chart
        - 'viz_type': tipo de visualização (ex: 'echarts_timeseries_bar')
        - 'datasource_table': nome da tabela (resolvido para datasource_id)
        - 'params': dict com configurações do chart

        O campo 'query_context' é gerado automaticamente a partir de 'params'.
        Sem ele, o Superset 4.x retorna "Empty query?" ao renderizar o chart.
        """
        resources = list(self._iter_resources("charts"))
        if not resources:
            log.info("Nenhuma definição de chart encontrada — pulando.")
            return

        if not self._dataset_map:
            self._dataset_map.update(self._list_unique_field("/api/v1/dataset/", "table_name"))

        existing = self._list_unique_field("/api/v1/chart/", "slice_name")
        log.info("Sincronizando %d chart(s)...", len(resources))

        for defn in resources:
            defn = dict(defn)
            name = defn["slice_name"]
            viz_type = defn["viz_type"]
            params = defn.get("params", {})

            # Resolve datasource_table → datasource_id
            ds_table = defn.pop("datasource_table", None)
            if ds_table:
                ds_id = self._dataset_map.get(ds_table)
                if ds_id is None:
                    log.warning("  Dataset '%s' não encontrado — pulando chart '%s'.", ds_table, name)
                    continue
                defn["datasource_id"] = ds_id
                defn.setdefault("datasource_type", "table")
            else:
                ds_id = defn.get("datasource_id")

            # form_data com datasource no formato "id__table" (obrigatório pelo Superset)
            form_data: dict[str, Any] = {
                "viz_type": viz_type,
                "adhoc_filters": [],
                **params,
            }
            if ds_id:
                form_data["datasource"] = f"{ds_id}__table"

            # Serializa params como string JSON (formato esperado pela API)
            defn["params"] = json.dumps(form_data)

            # query_context — necessário para o Superset 4.x executar a query ao renderizar
            if ds_id:
                defn["query_context"] = _build_query_context(viz_type, ds_id, params)

            if name in existing:
                self._update("/api/v1/chart", existing[name], defn)
                log.info("  Atualizado: %s", name)
                self._chart_map[name] = existing[name]
            else:
                try:
                    result = self._create("/api/v1/chart/", defn)
                except RuntimeError as exc:
                    if "500" in str(exc):
                        # Fallback sem query_context
                        log.warning("  500 ao criar '%s', retentando sem query_context...", name)
                        defn_fallback = {**defn, "query_context": ""}
                        result = self._create("/api/v1/chart/", defn_fallback)
                    else:
                        raise
                created_id = self._resolve_id(result)
                log.info("  Criado: %s (id=%s)", name, created_id)
                if created_id:
                    self._chart_map[name] = created_id

    def sync_dashboards(self):
        """
        Cria ou atualiza dashboards e associa charts.

        Cada arquivo em {resources_dir}/dashboards/*.json deve conter:
        - 'dashboard_title': título do dashboard
        - 'charts': lista de nomes (string) ou objetos com:
            { "slice_name": "...", "row": 0, "col": 0, "width": 4, "height": 50 }
        Opcionalmente: 'slug', 'published', 'native_filters'.

        'native_filters' é uma lista de objetos com:
            { "name": "...", "column": "...", "dataset": "...",
              "multi_select": true, "description": "...",
              "filter_type": "select"|"date" }

        A associação de charts é feita via json_metadata.positions (DashboardDAO).
        O embedding é habilitado automaticamente após criação/atualização.
        """
        resources = list(self._iter_resources("dashboards"))
        if not resources:
            log.info("Nenhuma definição de dashboard encontrada — pulando.")
            return

        if not self._chart_map:
            self._chart_map.update(self._list_unique_field("/api/v1/chart/", "slice_name"))

        existing = self._list_unique_field("/api/v1/dashboard/", "dashboard_title")
        log.info("Sincronizando %d dashboard(s)...", len(resources))

        for defn in resources:
            defn = dict(defn)
            title = defn["dashboard_title"]
            raw_charts = defn.pop("charts", [])
            native_filters_def = defn.pop("native_filters", [])

            # Normaliza charts para lista de objetos com slice_name + grid info
            chart_entries: list[dict] = []
            for idx, c in enumerate(raw_charts):
                if isinstance(c, str):
                    chart_entries.append({"slice_name": c, "row": idx, "col": 0, "width": 4, "height": 50})
                else:
                    chart_entries.append(c)

            # Resolve slice_name → chart_id + uuid
            charts_with_ids: list[dict] = []
            missing: list[str] = []
            for entry in chart_entries:
                slice_name = entry["slice_name"]
                chart_id = self._chart_map.get(slice_name)
                if chart_id is None:
                    missing.append(slice_name)
                    continue
                # Buscar UUID do chart (necessário para o position_json)
                chart_uuid = ""
                r = self.session.get(f"{self.url}/api/v1/chart/{chart_id}", timeout=15)
                if r.ok:
                    chart_uuid = r.json().get("result", {}).get("uuid", "")
                charts_with_ids.append({**entry, "chart_id": chart_id, "uuid": chart_uuid})

            if missing:
                log.warning("  Charts não encontrados (ignorados): %s", missing)

            position_json = _build_position_json(charts_with_ids, title=title)

            # Filtros nativos
            native_filter_config: list[dict] = []
            if native_filters_def:
                charts_in_scope = [item["chart_id"] for item in charts_with_ids]
                native_filter_config = _build_native_filters(
                    native_filters_def,
                    self._dataset_map,
                    charts_in_scope=charts_in_scope,
                )

            # json_metadata.positions é o que DashboardDAO.set_dash_metadata usa
            # para associar charts ao dashboard. Sem essa chave, os charts não
            # aparecem mesmo que position_json esteja correto.
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
                "slug": defn.get("slug"),
                "published": defn.get("published", False),
                "position_json": json.dumps(position_json),
                "json_metadata": json.dumps(json_metadata),
            }

            # POST primeiro (sem layout) — Superset 4.x não associa charts no POST
            create_payload = {
                "dashboard_title": title,
                "slug": defn.get("slug"),
                "published": defn.get("published", False),
            }

            if title in existing:
                dash_id = existing[title]
                log.info("  Atualizando: %s (id=%s)", title, dash_id)
            else:
                result = self._create("/api/v1/dashboard/", create_payload)
                dash_id = self._resolve_id(result)
                log.info("  Criado: %s (id=%s)", title, dash_id)
                if dash_id:
                    self._dashboard_map[title] = dash_id

            # PUT aplica layout + json_metadata — é aqui que os charts são associados
            if dash_id:
                self._update("/api/v1/dashboard", dash_id, full_payload)
                log.info("  Layout e charts aplicados: %s", title)
                self._dashboard_map[title] = dash_id

                # Habilitar embedding e armazenar UUID no cache
                try:
                    embed_uuid = _enable_embedding(self.session, self.url, dash_id)
                    log.info("  Embedding habilitado: uuid=%s", embed_uuid)
                    log.info("  Configure no .env: VITE_DASHBOARD_%s_UUID=%s",
                             defn.get("slug", title).upper().replace("-", "_"), embed_uuid)
                    # Salva UUID no cache para referência posterior
                    _cache = _load_ids_cache()
                    _cache.setdefault("embed_uuids", {})[title] = embed_uuid
                    _save_ids_cache(_cache)
                except Exception as exc:
                    log.warning("  Não foi possível habilitar embedding: %s", exc)

    def sync_all(self, steps: list[str] | None = None):
        """
        Executa todos os passos de provisionamento na ordem correta.

        Args:
            steps: lista de passos a executar; None executa todos.
                   Valores válidos: 'databases', 'datasets', 'charts', 'dashboards'.
        """
        pipeline: list[tuple[str, Any]] = [
            ("databases",   self.sync_databases),
            ("datasets",    self.sync_datasets),
            # ("charts",      self.sync_charts),
            # ("dashboards",  self.sync_dashboards),
        ]
        for name, fn in pipeline:
            if steps is None or name in steps:
                log.info("=== %s ===", name.upper())
                try:
                    fn()
                except Exception as exc:
                    log.error("Erro ao sincronizar %s: %s", name, exc)
                    raise
