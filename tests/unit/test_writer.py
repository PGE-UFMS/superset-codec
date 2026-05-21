from superset_codec.writer import _to_commented_map


def test_to_commented_map_attaches_comments_for_existing_keys():
    out = _to_commented_map({"a": 1, "b": 2}, {"a": "comment for a"})
    assert "a" in out.ca.items


def test_to_commented_map_skips_comments_for_missing_keys():
    out = _to_commented_map({"a": 1}, {"missing": "should be ignored"})
    assert "missing" not in out.ca.items
    assert "a" not in out.ca.items
