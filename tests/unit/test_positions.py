import pytest

from superset_codec._positions import (
    build_position_json,
    decompose_position_json,
)


def _chart(chart_id, row=0, col=0, *, tab=None, width=4, height=50, uuid=None,
           slice_name=""):
    entry = {
        "chart_id": chart_id,
        "row": row,
        "col": col,
        "width": width,
        "height": height,
        "slice_name": slice_name,
    }
    if tab is not None:
        entry["tab"] = tab
    if uuid is not None:
        entry["uuid"] = uuid
    return entry


def test_build_empty_charts_returns_skeleton_only():
    out = build_position_json([])
    assert out["DASHBOARD_VERSION_KEY"] == "v2"
    assert out["ROOT_ID"]["type"] == "ROOT"
    assert out["GRID_ID"]["children"] == []
    assert out["HEADER_ID"]["type"] == "HEADER"


def test_build_header_includes_title():
    out = build_position_json([], title="Painel X")
    assert out["HEADER_ID"]["meta"]["text"] == "Painel X"


def test_build_plain_rows_only():
    charts = [_chart(1, row=0, col=0), _chart(2, row=0, col=1), _chart(3, row=1, col=0)]
    out = build_position_json(charts)
    assert out["GRID_ID"]["children"] == ["ROW-0", "ROW-1"]
    assert out["ROW-0"]["children"] == ["CHART-1", "CHART-2"]
    assert out["ROW-1"]["children"] == ["CHART-3"]
    assert out["CHART-1"]["type"] == "CHART"


def test_build_sorts_charts_by_col_within_row():
    charts = [_chart(1, row=0, col=2), _chart(2, row=0, col=0), _chart(3, row=0, col=1)]
    out = build_position_json(charts)
    assert out["ROW-0"]["children"] == ["CHART-2", "CHART-3", "CHART-1"]


def test_build_tabs_only_sorted_by_name():
    charts = [
        _chart(1, row=0, col=0, tab="Beta"),
        _chart(2, row=0, col=0, tab="Alpha"),
    ]
    out = build_position_json(charts)
    assert out["GRID_ID"]["children"] == ["TABS-0"]
    assert out["TABS-0"]["children"] == ["TAB-0", "TAB-1"]
    assert out["TAB-0"]["meta"]["text"] == "Alpha"
    assert out["TAB-1"]["meta"]["text"] == "Beta"


def test_build_mixed_plain_and_tabs():
    charts = [
        _chart(1, row=0, col=0),
        _chart(2, row=2, col=0, tab="Detail"),
    ]
    out = build_position_json(charts)
    # plain row at 0 must come before TABS anchored at row 2.
    assert out["GRID_ID"]["children"] == ["ROW-0", "TABS-0"]


def test_build_tab_anchor_row_is_min_across_tabs():
    charts = [
        _chart(1, row=5, col=0, tab="A"),
        _chart(2, row=2, col=0, tab="B"),
        _chart(3, row=0, col=0),  # plain at row 0
    ]
    out = build_position_json(charts)
    # Tabs anchor at min row across tabs (2), so plain row 0 comes first, then TABS.
    assert out["GRID_ID"]["children"] == ["ROW-0", "TABS-0"]


def test_build_chart_meta_includes_optional_uuid():
    out = build_position_json([_chart(1, uuid="abc-123")])
    assert out["CHART-1"]["meta"]["uuid"] == "abc-123"

    out2 = build_position_json([_chart(2)])
    assert "uuid" not in out2["CHART-2"]["meta"]


def test_build_default_width_height():
    out = build_position_json([{"chart_id": 9, "row": 0, "col": 0}])
    assert out["CHART-9"]["meta"]["width"] == 4
    assert out["CHART-9"]["meta"]["height"] == 50


def test_decompose_empty_returns_empty_list():
    assert decompose_position_json({}, {}) == []


def test_decompose_plain_rows():
    positions = {
        "GRID_ID": {"children": ["ROW-3"]},
        "ROW-3": {"type": "ROW", "children": ["CHART-7"]},
        "CHART-7": {"meta": {"chartId": 7, "width": 4, "height": 50}},
    }
    out = decompose_position_json(positions, {7: "kpi"})
    assert out == [
        {"slice_name": "kpi", "row": 3, "col": 0, "width": 4, "height": 50}
    ]


def test_decompose_row_with_malformed_id_falls_back_to_counter():
    positions = {
        "GRID_ID": {"children": ["ROW-XYZ"]},
        "ROW-XYZ": {"type": "ROW", "children": ["CHART-1"]},
        "CHART-1": {"meta": {"chartId": 1}},
    }
    out = decompose_position_json(positions, {1: "c"})
    assert out[0]["row"] == 0  # counter fallback


def test_decompose_skips_chart_without_chartId():
    positions = {
        "GRID_ID": {"children": ["ROW-0"]},
        "ROW-0": {"type": "ROW", "children": ["CHART-1", "CHART-2"]},
        "CHART-1": {"meta": {}},  # missing chartId
        "CHART-2": {"meta": {"chartId": 2}},
    }
    out = decompose_position_json(positions, {2: "c2"})
    assert len(out) == 1
    assert out[0]["slice_name"] == "c2"


def test_decompose_tabs_extracts_tab_name_from_meta_text():
    positions = {
        "GRID_ID": {"children": ["TABS-0"]},
        "TABS-0": {"type": "TABS", "children": ["TAB-0"]},
        "TAB-0": {"meta": {"text": "Resumo"}, "children": ["ROW-TAB-0-0"]},
        "ROW-TAB-0-0": {"type": "ROW", "children": ["CHART-1"]},
        "CHART-1": {"meta": {"chartId": 1}},
    }
    out = decompose_position_json(positions, {1: "kpi"})
    assert out[0]["tab"] == "Resumo"
    assert out[0]["row"] == 0


def test_decompose_tab_row_malformed_id_falls_back_to_counter():
    positions = {
        "GRID_ID": {"children": ["TABS-0"]},
        "TABS-0": {"type": "TABS", "children": ["TAB-0"]},
        "TAB-0": {"meta": {"text": "T"}, "children": ["BOGUS"]},
        "BOGUS": {"type": "ROW", "children": ["CHART-1"]},
        "CHART-1": {"meta": {"chartId": 1}},
    }
    out = decompose_position_json(positions, {1: "c"})
    # "BOGUS".split("-") → ["BOGUS"]; int("BOGUS") fails → counter (0)
    assert out[0]["row"] == 0


def test_decompose_uses_id_to_chart_mapping_for_slice_name():
    positions = {
        "GRID_ID": {"children": ["ROW-0"]},
        "ROW-0": {"type": "ROW", "children": ["CHART-99"]},
        "CHART-99": {"meta": {"chartId": 99}},
    }
    assert decompose_position_json(positions, {99: "named"})[0]["slice_name"] == "named"
    # unknown id → str(id) fallback
    assert decompose_position_json(positions, {})[0]["slice_name"] == "99"


def _normalize(entries):
    """Project entries to comparable fields, sorted canonically."""
    out = []
    for e in entries:
        out.append({
            "chart_id_or_name": e.get("slice_name"),
            "row": e["row"],
            "col": e["col"],
            "width": e["width"],
            "height": e["height"],
            "tab": e.get("tab"),
        })
    return sorted(out, key=lambda x: (x["tab"] or "", x["row"], x["col"]))


@pytest.mark.parametrize(
    "charts",
    [
        pytest.param([_chart(1, row=0, col=0, slice_name="a")], id="single_chart"),
        pytest.param(
            [_chart(1, row=0, col=0, slice_name="a"),
             _chart(2, row=1, col=0, slice_name="b")],
            id="two_rows",
        ),
        pytest.param(
            [_chart(1, row=0, col=0, tab="A", slice_name="a"),
             _chart(2, row=0, col=0, tab="B", slice_name="b")],
            id="tabs_only",
        ),
        pytest.param(
            [_chart(1, row=0, col=0, slice_name="a"),
             _chart(2, row=1, col=0, tab="T", slice_name="b")],
            id="mixed",
        ),
    ],
)
def test_positions_roundtrip(charts):
    id_to_name = {c["chart_id"]: c["slice_name"] for c in charts}
    positions = build_position_json(charts)
    decomposed = decompose_position_json(positions, id_to_name)

    expected = [
        {
            "chart_id_or_name": c["slice_name"],
            "row": c["row"],
            "col": c["col"],
            "width": c["width"],
            "height": c["height"],
            "tab": c.get("tab"),
        }
        for c in charts
    ]
    expected = sorted(expected, key=lambda x: (x["tab"] or "", x["row"], x["col"]))
    assert _normalize(decomposed) == expected
