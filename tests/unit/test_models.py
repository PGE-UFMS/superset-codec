import pytest

from superset_codec.models import (
    ChartRef,
    DashboardRef,
    DatabaseRef,
    DatasetRef,
)


def test_dataset_ref_provision_key_returns_tuple():
    ref = DatasetRef(
        id=10, catalog="cat", schema="public", table_name="orders", database=1
    )
    assert ref.provision_key() == ("cat", "public", "orders")

def test_dataset_ref_provision_key_returns_tuple_none():
    ref = DatasetRef(
        id=11, schema="public", table_name="receipts", database=2
    )
    assert ref.provision_key() == (None, "public", "receipts")


@pytest.mark.parametrize(
    ("cls", "kwargs"),
    [
        (DatabaseRef, {"id": 1, "database_name": "db"}),
        (DatasetRef, {"id": 1, "table_name": "t", "database": 1}),
        (ChartRef, {"id": 1, "slice_name": "s"}),
        (DashboardRef, {"id": 1, "slug": "s", "dashboard_title": "T"}),
    ],
    ids=["database", "dataset", "chart", "dashboard"],
)
def test_refs_extra_allow_accepts_unknown_fields(cls, kwargs):
    ref = cls(**kwargs, weird_field="x")
    assert ref.weird_field == "x"
