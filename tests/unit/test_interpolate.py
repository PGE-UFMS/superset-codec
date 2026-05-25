import json
import logging

import pytest

from superset_codec._interpolate import (
    get_by_path,
    interpolate,
    inverse_interpolate,
)


def test_interpolate_substitutes_known_var():
    assert interpolate("host=${HOST}", {"HOST": "db.local"}) == "host=db.local"


def test_interpolate_leaves_unknown_var_unchanged(caplog):
    with caplog.at_level(logging.WARNING, logger="superset_codec._interpolate"):
        out = interpolate("x=${MISSING}", {})
    assert out == "x=${MISSING}"
    assert any("MISSING" in r.message for r in caplog.records)


def test_interpolate_multiple_vars_in_same_string():
    out = interpolate("${A}-${B}", {"A": "1", "B": "2"})
    assert out == "1-2"


def test_interpolate_no_placeholder_returns_input():
    assert interpolate("plain text", {"A": "1"}) == "plain text"


def test_interpolate_adjacent_placeholders():
    assert interpolate("${A}${B}", {"A": "ab", "B": "cd"}) == "abcd"


def test_inverse_interpolate_replaces_string_values():
    data = {"uri": "clickhouse://gold.local"}
    out = inverse_interpolate(data, {"GOLD_URI": "clickhouse://gold.local"})
    assert out == {"uri": "${GOLD_URI}"}


def test_inverse_interpolate_sorted_by_length_desc():
    # If sort order were ascending, "abc" would partially replace "abcdef".
    out = inverse_interpolate(
        {"val": "abcdef"}, {"SHORT": "abc", "LONG": "abcdef"}
    )
    assert out == {"val": "${LONG}"}


def test_inverse_interpolate_skips_empty_values():
    out = inverse_interpolate({"val": "hello"}, {"EMPTY": "", "X": "hello"})
    assert out == {"val": "${X}"}


def test_inverse_interpolate_handles_nested_structures():
    data = {"outer": {"inner": ["a", "secret"]}}
    out = inverse_interpolate(data, {"S": "secret"})
    assert out == {"outer": {"inner": ["a", "${S}"]}}


def test_inverse_interpolate_unicode_preserved():
    data = {"label": "Procuradoria-Geral"}
    out = inverse_interpolate(data, {"X": "Procuradoria-Geral"})
    assert out == {"label": "${X}"}


def test_get_by_path_returns_nested_value():
    assert get_by_path({"a": {"b": {"c": 42}}}, "a.b.c") == 42


def test_get_by_path_returns_default_on_missing_key():
    assert get_by_path({"a": {}}, "a.b", default="fallback") == "fallback"


def test_get_by_path_returns_default_when_intermediate_not_dict():
    assert get_by_path({"a": [1, 2]}, "a.b.c", default="fallback") == "fallback"


def test_get_by_path_custom_separator():
    assert get_by_path({"a": {"b": 7}}, "a/b", sep="/") == 7


@pytest.mark.parametrize(
    ("data", "variables"),
    [
        pytest.param({"k": "v"}, {}, id="plain"),
        pytest.param({"uri": "clickhouse://host"}, {"URI": "clickhouse://host"}, id="with_var"),
        pytest.param(
            {"outer": {"inner": "secret"}}, {"S": "secret"}, id="nested_dict"
        ),
        pytest.param({"label": "Procuradoria"}, {"P": "Procuradoria"}, id="unicode"),
    ],
)
def test_interpolate_roundtrip(data, variables):
    inverted = inverse_interpolate(data, variables)
    restored = json.loads(interpolate(json.dumps(inverted), variables))
    assert restored == data
