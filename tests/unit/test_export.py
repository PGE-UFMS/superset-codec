from superset_codec._export import _build_inverse_dataset_map
from superset_codec.models import DatasetRef


def _ref(id, table_name, schema=None, catalog=None):
    return DatasetRef(
        id=id, table_name=table_name, schema=schema, catalog=catalog, database=1
    )


def test_inverse_dataset_map_unique_table_name_yields_string():
    refs = [_ref(10, "orders", schema="public")]
    assert _build_inverse_dataset_map(refs) == {10: "orders"}


def test_inverse_dataset_map_ambiguous_table_name_yields_dict():
    refs = [
        _ref(10, "orders", schema="public"),
        _ref(20, "orders", schema="analytics"),
    ]
    out = _build_inverse_dataset_map(refs)
    assert out[10] == {"table_name": "orders", "schema": "public"}
    assert out[20] == {"table_name": "orders", "schema": "analytics"}


def test_inverse_dataset_map_includes_catalog_when_present():
    refs = [
        _ref(10, "orders", schema="public", catalog="prod"),
        _ref(20, "orders", schema="public", catalog="staging"),
    ]
    out = _build_inverse_dataset_map(refs)
    assert out[10] == {"table_name": "orders", "schema": "public", "catalog": "prod"}
    assert out[20] == {"table_name": "orders", "schema": "public", "catalog": "staging"}


def test_inverse_dataset_map_omits_none_fields_in_dict_form():
    refs = [
        _ref(10, "orders"),  # no schema, no catalog
        _ref(20, "orders", schema="public"),
    ]
    out = _build_inverse_dataset_map(refs)
    assert out[10] == {"table_name": "orders"}
    assert out[20] == {"table_name": "orders", "schema": "public"}


def test_inverse_dataset_map_mixed_unique_and_ambiguous():
    refs = [
        _ref(10, "orders", schema="public"),
        _ref(20, "orders", schema="analytics"),
        _ref(30, "customers", schema="public"),
    ]
    out = _build_inverse_dataset_map(refs)
    assert isinstance(out[10], dict)
    assert isinstance(out[20], dict)
    assert out[30] == "customers"
