import json
import pytest
from src.processor import (
    load_json, flatten, flatten_all,
    filter_rows, rename_keys,
    pluck, get_stats, run
)


class TestLoadJson:
    def test_list(self):
        assert load_json('[1, 2, 3]') == [1, 2, 3]

    def test_dict(self):
        assert load_json('{"name": "hassan"}') == {"name": "hassan"}

    def test_bad_input(self):
        with pytest.raises(json.JSONDecodeError):
            load_json("not valid json")

    def test_empty(self):
        assert load_json('[]') == []


class TestFlatten:
    def test_already_flat(self):
        assert flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_one_level(self):
        result = flatten({"user": {"name": "Ali", "age": 25}})
        assert result == {"user.name": "Ali", "user.age": 25}

    def test_nested_deep(self):
        assert flatten({"a": {"b": {"c": 42}}}) == {"a.b.c": 42}

    def test_custom_sep(self):
        assert flatten({"a": {"b": 1}}, sep="_") == {"a_b": 1}

    def test_mixed(self):
        r = flatten({"x": 10, "y": {"z": 20}})
        assert r["x"] == 10
        assert r["y.z"] == 20

    def test_empty_dict(self):
        assert flatten({}) == {}


class TestFlattenAll:
    def test_flattens_list(self):
        rows = [{"a": {"b": 1}}, {"a": {"b": 2}}]
        assert flatten_all(rows) == [{"a.b": 1}, {"a.b": 2}]

    def test_empty_list(self):
        assert flatten_all([]) == []


class TestFilterRows:
    data = [
        {"status": "active", "score": 10},
        {"status": "inactive", "score": 20},
        {"status": "active", "score": 30},
    ]

    def test_basic_filter(self):
        res = filter_rows(self.data, "status", "active")
        assert len(res) == 2

    def test_no_match(self):
        assert filter_rows(self.data, "status", "pending") == []

    def test_missing_field_skipped(self):
        rows = [{"a": 1}, {"b": 2}]
        assert filter_rows(rows, "a", 1) == [{"a": 1}]

    def test_int_value(self):
        res = filter_rows(self.data, "score", 20)
        assert res[0]["score"] == 20


class TestRenameKeys:
    def test_rename_one(self):
        r = rename_keys({"old": 1, "keep": 2}, {"old": "new"})
        assert "new" in r
        assert "old" not in r

    def test_empty_mapping(self):
        assert rename_keys({"a": 1}, {}) == {"a": 1}

    def test_rename_multiple(self):
        r = rename_keys({"x": 1, "y": 2}, {"x": "alpha", "y": "beta"})
        assert r == {"alpha": 1, "beta": 2}


class TestPluck:
    def test_basic(self):
        rows = [{"score": 10}, {"score": 20}]
        assert pluck(rows, "score") == [10, 20]

    def test_skips_missing(self):
        rows = [{"score": 5}, {"other": 99}]
        assert pluck(rows, "score") == [5]

    def test_empty(self):
        assert pluck([], "score") == []


class TestGetStats:
    rows = [{"v": 10}, {"v": 20}, {"v": 30}, {"v": 40}]

    def test_count(self):
        assert get_stats(self.rows, "v")["count"] == 4

    def test_min_max(self):
        s = get_stats(self.rows, "v")
        assert s["min"] == 10
        assert s["max"] == 40

    def test_mean(self):
        assert get_stats(self.rows, "v")["mean"] == 25.0

    def test_median(self):
        assert get_stats(self.rows, "v")["median"] == 25.0

    def test_single_no_stdev(self):
        assert get_stats([{"v": 5}], "v")["stdev"] is None

    def test_no_numbers(self):
        assert get_stats([{"v": "text"}], "v")["count"] == 0

    def test_missing_field(self):
        assert get_stats([{"v": 10}, {"x": 9}], "v")["count"] == 1


class TestRun:
    base = json.dumps([
        {"region": "EU", "metrics": {"sales": 100, "returns": 5}},
        {"region": "US", "metrics": {"sales": 200, "returns": 10}},
        {"region": "EU", "metrics": {"sales": 150, "returns": 8}},
    ])

    def test_no_config(self):
        res = run(self.base, {})
        assert len(res["rows"]) == 3
        assert res["stats"] is None

    def test_flatten(self):
        res = run(self.base, {"flatten": True})
        assert "metrics.sales" in res["rows"][0]

    def test_filter(self):
        cfg = {"filter_field": "region", "filter_value": "EU"}
        assert len(run(self.base, cfg)["rows"]) == 2

    def test_flatten_and_filter(self):
        cfg = {"flatten": True, "filter_field": "region", "filter_value": "US"}
        res = run(self.base, cfg)
        assert len(res["rows"]) == 1
        assert res["rows"][0]["metrics.sales"] == 200

    def test_stats(self):
        cfg = {"flatten": True, "summarise_field": "metrics.sales"}
        s = run(self.base, cfg)["stats"]
        assert s["count"] == 3
        assert s["min"] == 100

    def test_rename(self):
        res = run(self.base, {"rename": {"region": "area"}})
        assert all("area" in r for r in res["rows"])

    def test_wrapped_data_key(self):
        wrapped = json.dumps({"data": [{"a": 1}, {"a": 2}]})
        assert len(run(wrapped, {})["rows"]) == 2
