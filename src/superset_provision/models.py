from pydantic import BaseModel, ConfigDict
from typing import ClassVar, Optional
from uuid import UUID


class Table(BaseModel):
    catalog: Optional[str] = None
    schema: Optional[str] = None
    table_name: str



class _Ref(BaseModel):
    """Refs — identificação mínima de cada recurso na API do Superset.
    Usados como chave para resolver nome → id antes de criar/atualizar
    recursos dependentes (datasets → database, charts → dataset, etc.)."""

    model_config = ConfigDict(extra="allow")


class DatabaseRef(_Ref):
    """Referência nativa de uma conexão de banco em /api/v1/database."""
    id: int
    uuid: Optional[UUID]
    database_name: str

    def provision_key(self):
        return self.database_name

class DatasetRef(_Ref):
    """Referência nativa de um dataset em /api/v1/dataset.

    A chave natural é ``[[catalog.]schema.]table_name`` — o id da database
    desambigua tabelas com o mesmo nome em conexões distintas.
    """
    id: int = None
    uuid: Optional[UUID]
    catalog: Optional[str] = None
    schema: Optional[str] = None
    table_name: str
    database: int
    sql: Optional[str] = None

    CREATION_PARAMS: ClassVar[tuple[str,...]] = (
        "always_filter_main_dttm",
        "catalog",
        "database",
        "external_url",
        "is_managed_externally",
        "normalize_columns",
        "owners",
        "schema",
        "sql",
        "table_name",
        "template_params",
        "uuid",
    )

    def provision_key(self):
        return (self.catalog, self.schema, self.table_name)


class ChartRef(_Ref):
    """Referência nativa de um chart (slice) em /api/v1/chart."""
    id: int
    uuid: Optional[UUID] = None
    slice_name: str
    datasource_id: int
    datasource_type: str

    def provision_key(self):
        return self.slice_name


class DashboardRef(_Ref):
    """Referência nativa de um dashboard em /api/v1/dashboard."""
    id: int
    uuid: Optional[UUID] = None
    slug: str
    dashboard_title: str

    def provision_key(self):
        return self.slug
