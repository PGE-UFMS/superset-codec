import logging

import pytest

from superset_codec._client import SupersetClient
from superset_codec.models import DatasetRef


def test_map_by_field_builds_dict_keyed_by_field():
    items = [{"name": "a"}, {"name": "b"}]
    out = SupersetClient._map_by_field([10, 20], items, "name")
    assert set(out.keys()) == {"a", "b"}
    assert out["a"]["id"] == 10
    assert out["b"]["id"] == 20


def test_map_by_field_warns_on_duplicate_key(caplog):
    items = [{"name": "dup"}, {"name": "dup"}]
    with caplog.at_level(logging.WARNING, logger="superset_codec._client"):
        out = SupersetClient._map_by_field([1, 2], items, "name")
    assert any("dup" in r.message for r in caplog.records)
    assert out["dup"]["id"] == 2


def test_map_by_field_dotted_field_path():
    items = [{"meta": {"name": "a"}}, {"meta": {"name": "b"}}]
    out = SupersetClient._map_by_field([1, 2], items, "meta.name")
    assert set(out.keys()) == {"a", "b"}


def test_map_by_field_zip_strict_raises_on_length_mismatch():
    with pytest.raises(ValueError):
        SupersetClient._map_by_field([1], [{"name": "a"}, {"name": "b"}], "name")


# --------------------------- _build_dataset_map ---------------------------


def _ds_item(table_name, *, catalog=None, schema=None, database_id=1):
    return {
        "table_name": table_name,
        "catalog": catalog,
        "schema": schema,
        "database": {"id": database_id},
    }


def test_build_dataset_map_keys_by_provision_key_tuple():
    items = [_ds_item("orders", schema="public")]
    out = SupersetClient._build_dataset_map([10], items)
    assert list(out.keys()) == [(None, "public", "orders")]
    assert out[(None, "public", "orders")].id == 10


def test_build_dataset_map_distinguishes_same_table_name_across_schemas():
    items = [
        _ds_item("orders", schema="public"),
        _ds_item("orders", schema="analytics"),
    ]
    out = SupersetClient._build_dataset_map([10, 20], items)
    assert (None, "public", "orders") in out
    assert (None, "analytics", "orders") in out
    assert out[(None, "public", "orders")].id == 10
    assert out[(None, "analytics", "orders")].id == 20


def test_build_dataset_map_distinguishes_same_schema_table_across_catalogs():
    items = [
        _ds_item("orders", catalog="prod", schema="public"),
        _ds_item("orders", catalog="staging", schema="public"),
    ]
    out = SupersetClient._build_dataset_map([10, 20], items)
    assert out[("prod", "public", "orders")].id == 10
    assert out[("staging", "public", "orders")].id == 20


def test_build_dataset_map_warns_on_true_duplicate(caplog):
    items = [
        _ds_item("orders", schema="public"),
        _ds_item("orders", schema="public"),
    ]
    with caplog.at_level(logging.WARNING, logger="superset_codec._client"):
        out = SupersetClient._build_dataset_map([10, 20], items)
    assert any("orders" in r.message for r in caplog.records)
    # last write wins (same provision_key)
    assert out[(None, "public", "orders")].id == 20


# --------------------------- find_dataset_by_table_name ---------------------------


def _client_with_datasets(*refs):
    c = SupersetClient.__new__(SupersetClient)
    c._dataset_map = {r.provision_key(): r for r in refs}
    return c


def test_find_dataset_by_table_name_returns_match():
    ref = DatasetRef(id=1, table_name="orders", schema="public", database=1)
    c = _client_with_datasets(ref)
    assert c.find_dataset_by_table_name("orders") is ref


def test_find_dataset_by_table_name_returns_none_when_absent():
    c = _client_with_datasets()
    assert c.find_dataset_by_table_name("missing") is None


def test_find_dataset_by_table_name_warns_on_ambiguity(caplog):
    a = DatasetRef(id=1, table_name="orders", schema="public", database=1)
    b = DatasetRef(id=2, table_name="orders", schema="analytics", database=1)
    c = _client_with_datasets(a, b)
    with caplog.at_level(logging.WARNING, logger="superset_codec._client"):
        match = c.find_dataset_by_table_name("orders")
    assert match in (a, b)
    assert any("Ambiguous" in r.message for r in caplog.records)


# --------------------------- resolve_dataset_ref ---------------------------


def test_resolve_dataset_ref_string_uses_fuzzy_lookup():
    ref = DatasetRef(id=1, table_name="orders", schema="public", database=1)
    c = _client_with_datasets(ref)
    assert c.resolve_dataset_ref("orders") is ref


def test_resolve_dataset_ref_dict_does_exact_tuple_lookup():
    a = DatasetRef(id=1, table_name="orders", schema="public", database=1)
    b = DatasetRef(id=2, table_name="orders", schema="analytics", database=1)
    c = _client_with_datasets(a, b)
    assert c.resolve_dataset_ref({"table_name": "orders", "schema": "public"}) is a
    assert c.resolve_dataset_ref({"table_name": "orders", "schema": "analytics"}) is b


def test_resolve_dataset_ref_dict_defaults_missing_keys_to_none():
    # Dataset created without catalog/schema → key is (None, None, "orders")
    ref = DatasetRef(id=1, table_name="orders", database=1)
    c = _client_with_datasets(ref)
    assert c.resolve_dataset_ref({"table_name": "orders"}) is ref


def test_resolve_dataset_ref_dict_returns_none_on_mismatch():
    ref = DatasetRef(id=1, table_name="orders", schema="public", database=1)
    c = _client_with_datasets(ref)
    # Schema differs → no match (no fallback to fuzzy).
    assert c.resolve_dataset_ref({"table_name": "orders", "schema": "other"}) is None


def test_resolve_dataset_ref_with_catalog():
    a = DatasetRef(id=1, table_name="orders", catalog="prod", schema="public", database=1)
    b = DatasetRef(id=2, table_name="orders", catalog="staging", schema="public", database=1)
    c = _client_with_datasets(a, b)
    assert c.resolve_dataset_ref(
        {"table_name": "orders", "catalog": "prod", "schema": "public"}
    ) is a
