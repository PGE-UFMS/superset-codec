import json

import pytest

from superset_codec._apply import _build_query_context


def _qc(viz_type, dataset_id=1, **params):
    return json.loads(_build_query_context(viz_type, dataset_id, params))


def _q(qc):
    return qc["queries"][0]


def test_query_context_basic_envelope():
    qc = _qc("table", metrics=["count"])
    assert qc["datasource"] == {"id": 1, "type": "table"}
    assert qc["force"] is False
    assert qc["result_format"] == "json"
    assert qc["result_type"] == "full"
    assert isinstance(qc["queries"], list) and len(qc["queries"]) == 1


def test_query_context_metric_singular_wrapped_in_list():
    qc = _qc("table", metric="count")
    assert _q(qc)["metrics"] == ["count"]


def test_query_context_metrics_plural_passthrough():
    qc = _qc("table", metrics=["a", "b"])
    assert _q(qc)["metrics"] == ["a", "b"]


def test_query_context_no_metrics_empty_list():
    qc = _qc("table")
    assert _q(qc)["metrics"] == []


def test_query_context_big_number_total_row_limit_1_and_no_columns():
    qc = _qc("big_number_total", metric="count", groupby=["area"])
    q = _q(qc)
    assert q["row_limit"] == 1
    assert q["columns"] == []


@pytest.mark.parametrize(
    "entity",
    [
        pytest.param("uf", id="string"),
        pytest.param({"column_name": "uf"}, id="dict"),
    ],
)
def test_query_context_country_map_uses_entity_as_column(entity):
    qc = _qc("country_map", entity=entity, metric="count")
    assert _q(qc)["columns"] == ["uf"]


def test_query_context_country_map_default_row_limit_50():
    qc = _qc("country_map", entity="uf", metric="count")
    assert _q(qc)["row_limit"] == 50


@pytest.mark.parametrize(
    ("viz_type", "params", "expected_columns"),
    [
        pytest.param(
            "echarts_timeseries_bar",
            {"x_axis": "ts", "groupby": ["area", "ts"], "metric": "count"},
            ["ts", "area"],
            id="echarts_bar_dedupes_x_axis",
        ),
        pytest.param(
            "echarts_timeseries_line",
            {"x_axis": "ts", "groupby": [], "metric": "count"},
            ["ts"],
            id="echarts_line",
        ),
        pytest.param(
            "pie",
            {"groupby": ["categoria"], "metric": "count"},
            ["categoria"],
            id="pie_uses_groupby_only",
        ),
        pytest.param(
            "custom_viz",
            {"x_axis": "ts", "groupby": ["area"], "metric": "count"},
            ["ts", "area"],
            id="fallback_with_x_axis",
        ),
        pytest.param(
            "custom_viz",
            {"groupby": ["a", "b"], "metric": "count"},
            ["a", "b"],
            id="fallback_no_x_axis",
        ),
    ],
)
def test_query_context_columns_resolution(viz_type, params, expected_columns):
    qc = _qc(viz_type, **params)
    assert _q(qc)["columns"] == expected_columns


def test_query_context_default_row_limit_10000_when_not_specified():
    qc = _qc("table", groupby=["a"], metric="count")
    assert _q(qc)["row_limit"] == 10000


def test_query_context_time_range_default_no_filter():
    qc = _qc("table", metric="count")
    assert _q(qc)["time_range"] == "No filter"


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param({"granularity": "g1"}, "g1", id="granularity"),
        pytest.param({"granularity_sqla": "gs"}, "gs", id="granularity_sqla"),
        pytest.param({"time_column": "tc"}, "tc", id="time_column"),
        # priority: granularity > granularity_sqla > time_column
        pytest.param(
            {"granularity": "g1", "granularity_sqla": "gs", "time_column": "tc"},
            "g1",
            id="priority_granularity_wins",
        ),
        pytest.param(
            {"granularity_sqla": "gs", "time_column": "tc"}, "gs",
            id="priority_granularity_sqla_over_time_column",
        ),
    ],
)
def test_query_context_granularity_resolution_order(params, expected):
    qc = _qc("table", metric="count", **params)
    assert _q(qc)["granularity"] == expected


def test_query_context_granularity_omitted_when_none():
    qc = _qc("table", metric="count")
    assert "granularity" not in _q(qc)


