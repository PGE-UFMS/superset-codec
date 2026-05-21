import logging

import pytest

from superset_codec._client import SupersetClient


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
