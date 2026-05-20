"""Dashboard position_json builders and decomposers.

apply  side: _build_position_json  — list[chart_entry] → Superset position tree
export side: _decompose_position_json — Superset position tree → list[chart_entry]
"""
from collections import defaultdict
from typing import Any


def build_position_json(charts_with_ids: list[dict], title: str = "") -> dict:
    """Build Superset's ``position_json`` from a flat list of chart entries.

    Each entry must have: ``chart_id``, ``row``, ``col``, ``width``, ``height``.
    Optional: ``uuid``, ``tab`` (tab name string).
    """
    positions: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID":   {"children": ["GRID_ID"], "id": "ROOT_ID",  "type": "ROOT"},
        "GRID_ID":   {"children": [],          "id": "GRID_ID",  "parents": ["ROOT_ID"], "type": "GRID"},
        "HEADER_ID": {"id": "HEADER_ID",       "type": "HEADER", "meta": {"text": title}},
    }

    def _add_row(row_id: str, row_items: list[dict], parent_id: str, parent_chain: list[str]) -> None:
        positions[parent_id]["children"].append(row_id)
        positions[row_id] = {
            "children": [],
            "id": row_id,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": parent_chain,
            "type": "ROW",
        }
        for item in sorted(row_items, key=lambda x: x.get("col", 0)):
            chart_key = f"CHART-{item['chart_id']}"
            positions[row_id]["children"].append(chart_key)
            meta: dict[str, Any] = {
                "chartId":   item["chart_id"],
                "height":    item.get("height", 50),
                "sliceName": item.get("slice_name", ""),
                "width":     item.get("width", 4),
            }
            if item.get("uuid"):
                meta["uuid"] = item["uuid"]
            positions[chart_key] = {
                "children": [],
                "id": chart_key,
                "meta": meta,
                "parents": [*parent_chain, row_id],
                "type": "CHART",
            }

    plain_rows: dict[int, list[dict]] = defaultdict(list)
    tabs_rows:  dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for item in charts_with_ids:
        tab_name = item.get("tab")
        if tab_name:
            tabs_rows[str(tab_name)][item.get("row", 0)].append(item)
        else:
            plain_rows[item.get("row", 0)].append(item)

    tab_anchor_row = None
    if tabs_rows:
        tab_anchor_row = min(min(rows.keys()) for rows in tabs_rows.values() if rows)

    blocks: list[tuple[int, str]] = [(r, f"plain:{r}") for r in plain_rows]
    if tab_anchor_row is not None:
        blocks.append((tab_anchor_row, "tabs"))

    for _, block in sorted(blocks, key=lambda x: (x[0], x[1])):
        if block.startswith("plain:"):
            row_idx = int(block.split(":", 1)[1])
            _add_row(f"ROW-{row_idx}", plain_rows[row_idx], "GRID_ID", ["ROOT_ID", "GRID_ID"])
            continue

        tabs_id = "TABS-0"
        positions["GRID_ID"]["children"].append(tabs_id)
        positions[tabs_id] = {
            "children": [], "id": tabs_id, "meta": {},
            "parents": ["ROOT_ID", "GRID_ID"], "type": "TABS",
        }
        for tab_idx, tab_name in enumerate(sorted(tabs_rows)):
            tab_id = f"TAB-{tab_idx}"
            positions[tabs_id]["children"].append(tab_id)
            positions[tab_id] = {
                "children": [], "id": tab_id,
                "meta": {"text": tab_name},
                "parents": ["ROOT_ID", "GRID_ID", tabs_id],
                "type": "TAB",
            }
            for row_idx in sorted(tabs_rows[tab_name]):
                _add_row(
                    f"ROW-TAB-{tab_idx}-{row_idx}",
                    tabs_rows[tab_name][row_idx],
                    tab_id,
                    ["ROOT_ID", "GRID_ID", tabs_id, tab_id],
                )

    return positions


def decompose_position_json(positions: dict, id_to_chart: dict[int, str]) -> list[dict]:
    """Inverse of :func:`build_position_json`.

    Converts Superset's position tree back to a flat list of chart entries.
    """
    charts: list[dict] = []

    def _extract_row(row_id: str, tab_name: str | None, row_idx: int) -> None:
        for col_idx, chart_key in enumerate(positions.get(row_id, {}).get("children", [])):
            m = positions.get(chart_key, {}).get("meta", {})
            chart_id = m.get("chartId")
            if chart_id is None:
                continue
            entry: dict[str, Any] = {
                "slice_name": id_to_chart.get(chart_id, str(chart_id)),
                "row":    row_idx,
                "col":    col_idx,
                "width":  m.get("width", 4),
                "height": m.get("height", 50),
            }
            if tab_name is not None:
                entry["tab"] = tab_name
            charts.append(entry)

    for counter, child_id in enumerate(positions.get("GRID_ID", {}).get("children", [])):
        node = positions.get(child_id, {})
        node_type = node.get("type")

        if node_type == "ROW":
            parts = child_id.split("-")
            try:
                row_idx = int(parts[1])
            except (IndexError, ValueError):
                row_idx = counter
            _extract_row(child_id, None, row_idx)

        elif node_type == "TABS":
            for tab_id in node.get("children", []):
                tab_node = positions.get(tab_id, {})
                tab_name = tab_node.get("meta", {}).get("text", "")
                for rc2, row_id in enumerate(tab_node.get("children", [])):
                    parts = row_id.split("-")
                    try:
                        row_idx = int(parts[-1])
                    except (IndexError, ValueError):
                        row_idx = rc2
                    _extract_row(row_id, tab_name, row_idx)

    return charts
