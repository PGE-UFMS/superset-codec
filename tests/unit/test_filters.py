import datetime as _dt
import logging
import uuid

import pytest

from superset_codec._filters import build_native_filters, simplify_native_filter


_STABLE_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def stable_uuid(monkeypatch):
    monkeypatch.setattr("superset_codec._filters.uuid.uuid4", lambda: _STABLE_UUID)
    return _STABLE_UUID


class _FakeDateTime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return _dt.datetime(2099, 6, 15, 12, 0, 0)


@pytest.fixture
def fake_now(monkeypatch):
    monkeypatch.setattr("datetime.datetime", _FakeDateTime)


# --------------------------- build_native_filters ---------------------------


def test_build_raw_passthrough_updates_only_charts_in_scope():
    raw = {"id": "kept", "name": "f", "chartsInScope": [99]}
    out = build_native_filters([{"_raw": raw}], dataset_name_to_id={}, charts_in_scope=[1, 2])
    assert len(out) == 1
    assert out[0]["id"] == "kept"
    assert out[0]["name"] == "f"
    assert out[0]["chartsInScope"] == [1, 2]


def test_build_missing_dataset_skipped_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="superset_codec._filters"):
        out = build_native_filters(
            [{"name": "f", "column": "c", "dataset": "missing"}],
            dataset_name_to_id={},
        )
    assert out == []
    assert any("missing" in r.message for r in caplog.records)


def test_build_date_filter_shape(stable_uuid):
    out = build_native_filters(
        [{"name": "Periodo", "column": "ts", "dataset": "ds",
          "filter_type": "date", "default_value": "Last week"}],
        dataset_name_to_id={"ds": 7},
    )
    f = out[0]
    assert f["filterType"] == "filter_time"
    assert f["controlValues"]["enableEmptyFilter"] is False
    assert f["defaultDataMask"]["extraFormData"]["time_range"] == "Last week"
    assert f["defaultDataMask"]["filterState"]["value"] == "Last week"


def test_build_date_filter_default_no_filter(stable_uuid):
    out = build_native_filters(
        [{"name": "Periodo", "column": "ts", "dataset": "ds", "filter_type": "date"}],
        dataset_name_to_id={"ds": 7},
    )
    assert out[0]["defaultDataMask"]["extraFormData"]["time_range"] == "No filter"


def test_build_select_default_multi_select_true(stable_uuid):
    out = build_native_filters(
        [{"name": "Area", "column": "area", "dataset": "ds"}],
        dataset_name_to_id={"ds": 1},
    )
    assert out[0]["controlValues"]["multiSelect"] is True


@pytest.mark.parametrize(
    ("default_value", "expected_value", "expected_extra"),
    [
        pytest.param(2025, [2025], {"filters": [{"col": "ano", "op": "IN", "val": [2025]}]},
                     id="scalar_wrapped_in_list"),
        pytest.param([2024, 2025], [2024, 2025],
                     {"filters": [{"col": "ano", "op": "IN", "val": [2024, 2025]}]},
                     id="list_passthrough"),
        pytest.param(None, None, {}, id="none_yields_empty_extra"),
    ],
)
def test_build_select_default_value_variants(
    stable_uuid, default_value, expected_value, expected_extra
):
    decl = {"name": "Ano", "column": "ano", "dataset": "ds"}
    if default_value is not None:
        decl["default_value"] = default_value
    out = build_native_filters([decl], dataset_name_to_id={"ds": 1})
    assert out[0]["defaultDataMask"]["filterState"]["value"] == expected_value
    assert out[0]["defaultDataMask"]["extraFormData"] == expected_extra


def test_build_select_current_year_uses_datetime_now(stable_uuid, fake_now):
    out = build_native_filters(
        [{"name": "Ano", "column": "ano", "dataset": "ds",
          "default_value": "current_year"}],
        dataset_name_to_id={"ds": 1},
    )
    assert out[0]["defaultDataMask"]["filterState"]["value"] == [2099]


def test_build_filter_id_format(stable_uuid):
    out = build_native_filters(
        [{"name": "Area", "column": "area", "dataset": "ds"}],
        dataset_name_to_id={"ds": 1},
    )
    # uuid4().hex[:8].upper() of stable uuid → "11111111"
    assert out[0]["id"] == "NATIVE_FILTER-11111111"


def test_build_charts_in_scope_defaults_to_empty_list(stable_uuid):
    out = build_native_filters(
        [{"name": "f", "column": "c", "dataset": "ds"}],
        dataset_name_to_id={"ds": 1},
    )
    assert out[0]["chartsInScope"] == []


# --------------------------- simplify_native_filter ---------------------------


def test_simplify_filter_time_returns_filter_type_date():
    raw = {
        "name": "Periodo",
        "filterType": "filter_time",
        "targets": [{"column": {"name": "ts"}, "datasetId": 7}],
        "defaultDataMask": {"filterState": {"value": "Last week"}},
    }
    out = simplify_native_filter(raw, {7: "ds"})
    assert out["filter_type"] == "date"
    assert "multi_select" not in out
    assert out["default_value"] == "Last week"


def test_simplify_filter_select_includes_multi_select():
    raw = {
        "name": "Area",
        "filterType": "filter_select",
        "controlValues": {"multiSelect": False},
        "targets": [{"column": {"name": "area"}, "datasetId": 7}],
        "defaultDataMask": {"filterState": {}},
    }
    out = simplify_native_filter(raw, {7: "ds"})
    assert out["filter_type"] == "select"
    assert out["multi_select"] is False
    assert "default_value" not in out


def test_simplify_includes_default_value_when_present():
    raw = {
        "name": "Area",
        "filterType": "filter_select",
        "targets": [{"column": {"name": "area"}, "datasetId": 7}],
        "defaultDataMask": {"filterState": {"value": ["a", "b"]}},
    }
    out = simplify_native_filter(raw, {7: "ds"})
    assert out["default_value"] == ["a", "b"]


def test_simplify_includes_description_when_truthy():
    raw = {
        "name": "f", "filterType": "filter_select", "description": "info",
        "targets": [{"column": {"name": "c"}, "datasetId": 7}],
        "defaultDataMask": {"filterState": {}},
    }
    out = simplify_native_filter(raw, {7: "ds"})
    assert out["description"] == "info"


def test_simplify_safe_mode_unknown_type_adds_raw():
    raw = {
        "name": "f", "filterType": "filter_range",
        "targets": [{"column": {"name": "c"}, "datasetId": 7}],
        "defaultDataMask": {"filterState": {}},
    }
    out = simplify_native_filter(raw, {7: "ds"}, safe_mode=True)
    assert out["_raw"] is raw


def test_simplify_safe_mode_known_type_omits_raw():
    raw = {
        "name": "f", "filterType": "filter_select",
        "targets": [{"column": {"name": "c"}, "datasetId": 7}],
        "defaultDataMask": {"filterState": {}},
    }
    out = simplify_native_filter(raw, {7: "ds"}, safe_mode=True)
    assert "_raw" not in out


def test_simplify_handles_missing_targets_gracefully():
    raw = {"name": "f", "filterType": "filter_select", "defaultDataMask": {}}
    out = simplify_native_filter(raw, {})
    assert out["column"] == ""
    assert out["dataset"] == ""


# --------------------------- roundtrip ---------------------------


@pytest.mark.parametrize(
    "decl",
    [
        pytest.param(
            {"name": "Area", "column": "area", "dataset": "ds", "filter_type": "select",
             "multi_select": True},
            id="select_basic",
        ),
        pytest.param(
            {"name": "Ano", "column": "ano", "dataset": "ds", "filter_type": "select",
             "multi_select": True, "default_value": [2025]},
            id="select_with_default",
        ),
        pytest.param(
            {"name": "Area", "column": "area", "dataset": "ds", "filter_type": "select",
             "multi_select": False},
            id="select_multi_false",
        ),
        pytest.param(
            {"name": "Periodo", "column": "ts", "dataset": "ds", "filter_type": "date",
             "default_value": "Last month"},
            id="date_with_default",
        ),
    ],
)
def test_filters_roundtrip(decl, stable_uuid):
    built = build_native_filters([decl], dataset_name_to_id={"ds": 7})
    simplified = simplify_native_filter(built[0], {7: "ds"})
    expected = dict(decl)
    # build does not preserve filter_type ordering; simplify orders fields canonically.
    # date branch drops multi_select (correct); align expected.
    if decl["filter_type"] == "date":
        expected.pop("multi_select", None)
    assert simplified == expected
