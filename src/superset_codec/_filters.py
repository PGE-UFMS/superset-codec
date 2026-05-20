"""Native filter builders and simplifiers.

apply  side: build_native_filters    — declarative list → Superset filter config
export side: simplify_native_filter  — Superset filter config → declarative form
"""
import logging
import uuid
from typing import Any

log = logging.getLogger(__name__)

_KNOWN_FILTER_TYPES = {"filter_select", "filter_time"}


def build_native_filters(
    filters: list[dict],
    dataset_name_to_id: dict[str, int],
    charts_in_scope: list[int] | None = None,
) -> list[dict]:
    """Convert declarative filter definitions to Superset's native filter JSON.

    Each filter requires: ``name``, ``column``, ``dataset``.
    Optional: ``multi_select`` (default True), ``description``, ``default_value``,
    ``filter_type`` (``"select"`` | ``"date"``).

    If an entry contains a ``_raw`` key (written by safe-mode export), its value
    is used verbatim — only ``chartsInScope`` is updated to the current environment.
    """
    import datetime

    result: list[dict] = []
    scope = charts_in_scope or []

    for f in filters:
        # Passthrough: raw filter stored by safe-mode export
        if "_raw" in f:
            raw_f = dict(f["_raw"])
            raw_f["chartsInScope"] = scope
            result.append(raw_f)
            log.debug("  Filter '%s' restored from _raw.", f.get("name", "?"))
            continue

        dataset_id = dataset_name_to_id.get(f["dataset"])
        if not dataset_id:
            log.warning(
                "Dataset '%s' not found for filter '%s' — skipping.", f["dataset"], f["name"]
            )
            continue

        filter_id = f"NATIVE_FILTER-{uuid.uuid4().hex[:8].upper()}"
        filter_type = f.get("filter_type", "select")

        if filter_type == "date":
            default_val = f.get("default_value", "No filter")
            result.append({
                "id":         filter_id,
                "name":       f["name"],
                "filterType": "filter_time",
                "targets":    [{"datasetId": dataset_id, "column": {"name": f["column"]}}],
                "controlValues":   {"enableEmptyFilter": False},
                "defaultDataMask": {
                    "extraFormData": {"time_range": default_val},
                    "filterState":   {"value": default_val},
                },
                "scope":         {"rootPath": ["ROOT_ID"], "excluded": []},
                "type":          "NATIVE_FILTER",
                "description":   f.get("description", ""),
                "chartsInScope": scope,
                "tabsInScope":   [],
            })
            continue

        raw_default = f.get("default_value")
        if raw_default == "current_year":
            default_val: Any = [datetime.datetime.now().year]
        elif raw_default is not None:
            default_val = raw_default if isinstance(raw_default, list) else [raw_default]
        else:
            default_val = None

        result.append({
            "id":         filter_id,
            "name":       f["name"],
            "filterType": "filter_select",
            "targets":    [{"datasetId": dataset_id, "column": {"name": f["column"]}}],
            "controlValues": {
                "multiSelect":        f.get("multi_select", True),
                "enableEmptyFilter":  False,
                "defaultToFirstItem": False,
                "searchAllOptions":   False,
                "sortAscending":      True,
            },
            "defaultDataMask": {
                "extraFormData": (
                    {"filters": [{"col": f["column"], "op": "IN", "val": default_val}]}
                    if default_val is not None else {}
                ),
                "filterState": {"value": default_val},
            },
            "scope":         {"rootPath": ["ROOT_ID"], "excluded": []},
            "type":          "NATIVE_FILTER",
            "description":   f.get("description", ""),
            "chartsInScope": scope,
            "tabsInScope":   [],
        })

    return result


def simplify_native_filter(
    f: dict,
    id_to_dataset: dict[int, str],
    *,
    safe_mode: bool = False,
) -> dict:
    """Inverse of :func:`build_native_filters`.

    Converts a full Superset filter object to its declarative form.
    In safe_mode, unknown filter types get a ``_raw`` key with the full
    original object so apply can restore them verbatim.
    """
    targets = f.get("targets", [{}])
    target = targets[0] if targets else {}
    filter_type_raw = f.get("filterType", "")
    is_known = filter_type_raw in _KNOWN_FILTER_TYPES

    simplified: dict[str, Any] = {
        "name":        f["name"],
        "column":      (target.get("column") or {}).get("name", ""),
        "dataset":     id_to_dataset.get(target.get("datasetId"), ""),
        "filter_type": "date" if filter_type_raw == "filter_time" else "select",
    }
    if simplified["filter_type"] == "select":
        simplified["multi_select"] = f.get("controlValues", {}).get("multiSelect", True)
    val = f.get("defaultDataMask", {}).get("filterState", {}).get("value")
    if val is not None:
        simplified["default_value"] = val
    if f.get("description"):
        simplified["description"] = f["description"]

    if safe_mode and not is_known:
        # Preserve the full original object so build_native_filters can restore it.
        simplified["_raw"] = f
        log.debug("  Filter '%s' (type=%s) stored with _raw for safe roundtrip.", f["name"], filter_type_raw)

    return simplified
