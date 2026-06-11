"""
Unit Tests – JSON Data Transformation Processor
Tests each public function in src/processor.py in isolation.
"""

import json
import pytest
from src.processor import (
    load_json,
    flatten_record,
    flatten_records,
    filter_records,
    rename_fields,
    rename_fields_in_records,
    extract_field,
    summarise,
    transform_pipeline,
)

# ---------------------------------------------------------------------------
# load_json
# ---------------------------------------------------------------------------

class TestLoadJson:
    def test_parses_list(self):
        assert load_json('[1, 2, 3]') == [1, 2, 3]

    def test_parses_dict(self):
        assert load_json('{"a": 1}') == {"a": 1}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            load_json("{bad json}")

    def test_empty_list(self):
        assert load_json('[]') == []


# ---------------------------------------------------------------------------
# flatten_record
# ---------------------------------------------------------------------------

class TestFlattenRecord:
    def test_flat_record_unchanged(self):
        rec = {"a": 1, "b": 2}
        assert flatten_record(rec) == {"a": 1, "b": 2}

    def test_one_level_nesting(self):
        rec = {"user": {"name": "Alice", "age": 30}}
        assert flatten_record(rec) == {"user.name": "Alice", "user.age": 30}

    def test_deep_nesting(self):
        rec = {"a": {"b": {"c": 99}}}
        assert flatten_record(rec) == {"a.b.c": 99}

    def test_custom_separator(self):
        rec = {"a": {"b": 1}}
        assert flatten_record(rec, sep="_") == {"a_b": 1}

    def test_mixed_flat_and_nested(self):
        rec = {"x": 10, "y": {"z": 20}}
        result = flatten_record(rec)
        assert result["x"] == 10
        assert result["y.z"] == 20

    def test_empty_record(self):
        assert flatten_record({}) == {}


# ---------------------------------------------------------------------------
# flatten_records
# ---------------------------------------------------------------------------

class TestFlattenRecords:
    def test_flattens_all(self):
        records = [{"a": {"b": 1}}, {"a": {"b": 2}}]
        result = flatten_records(records)
        assert result == [{"a.b": 1}, {"a.b": 2}]

    def test_empty_list(self):
        assert flatten_records([]) == []


# ---------------------------------------------------------------------------
# filter_records
# ---------------------------------------------------------------------------

class TestFilterRecords:
    RECORDS = [
        {"status": "active", "score": 10},
        {"status": "inactive", "score": 20},
        {"status": "active", "score": 30},
    ]

    def test_filters_by_string(self):
        result = filter_records(self.RECORDS, "status", "active")
        assert len(result) == 2
        assert all(r["status"] == "active" for r in result)

    def test_no_match_returns_empty(self):
        result = filter_records(self.RECORDS, "status", "pending")
        assert result == []

    def test_missing_field_excluded(self):
        records = [{"a": 1}, {"b": 2}]
        result = filter_records(records, "a", 1)
        assert result == [{"a": 1}]

    def test_filter_by_integer(self):
        result = filter_records(self.RECORDS, "score", 20)
        assert len(result) == 1
        assert result[0]["score"] == 20


# ---------------------------------------------------------------------------
# rename_fields
# ---------------------------------------------------------------------------

class TestRenameFields:
    def test_renames_key(self):
        rec = {"old_name": 1, "keep": 2}
        result = rename_fields(rec, {"old_name": "new_name"})
        assert "new_name" in result
        assert "old_name" not in result
        assert result["keep"] == 2

    def test_empty_mapping(self):
        rec = {"a": 1}
        assert rename_fields(rec, {}) == {"a": 1}

    def test_multiple_renames(self):
        rec = {"x": 1, "y": 2}
        result = rename_fields(rec, {"x": "alpha", "y": "beta"})
        assert result == {"alpha": 1, "beta": 2}


# ---------------------------------------------------------------------------
# extract_field
# ---------------------------------------------------------------------------

class TestExtractField:
    def test_extracts_values(self):
        records = [{"score": 10}, {"score": 20}, {"score": 30}]
        assert extract_field(records, "score") == [10, 20, 30]

    def test_skips_missing(self):
        records = [{"score": 10}, {"other": 99}, {"score": 30}]
        assert extract_field(records, "score") == [10, 30]

    def test_empty_list(self):
        assert extract_field([], "score") == []


# ---------------------------------------------------------------------------
# summarise
# ---------------------------------------------------------------------------

class TestSummarise:
    RECORDS = [
        {"value": 10},
        {"value": 20},
        {"value": 30},
        {"value": 40},
    ]

    def test_count(self):
        assert summarise(self.RECORDS, "value")["count"] == 4

    def test_min_max(self):
        s = summarise(self.RECORDS, "value")
        assert s["min"] == 10
        assert s["max"] == 40

    def test_mean(self):
        assert summarise(self.RECORDS, "value")["mean"] == 25.0

    def test_median(self):
        assert summarise(self.RECORDS, "value")["median"] == 25.0

    def test_stdev_none_for_single_value(self):
        s = summarise([{"v": 5}], "v")
        assert s["stdev"] is None

    def test_no_numeric_values(self):
        records = [{"value": "text"}, {"value": None}]
        s = summarise(records, "value")
        assert s["count"] == 0
        assert s["min"] is None

    def test_missing_field_ignored(self):
        records = [{"value": 10}, {"other": 99}]
        assert summarise(records, "value")["count"] == 1


# ---------------------------------------------------------------------------
# transform_pipeline
# ---------------------------------------------------------------------------

class TestTransformPipeline:
    BASE_JSON = json.dumps([
        {"region": "EU", "metrics": {"sales": 100, "returns": 5}},
        {"region": "US", "metrics": {"sales": 200, "returns": 10}},
        {"region": "EU", "metrics": {"sales": 150, "returns": 8}},
    ])

    def test_no_config_returns_all(self):
        result = transform_pipeline(self.BASE_JSON, {})
        assert len(result["records"]) == 3
        assert result["summary"] is None

    def test_flatten_option(self):
        result = transform_pipeline(self.BASE_JSON, {"flatten": True})
        assert "metrics.sales" in result["records"][0]

    def test_filter_option(self):
        result = transform_pipeline(self.BASE_JSON, {"filter_field": "region", "filter_value": "EU"})
        assert len(result["records"]) == 2

    def test_flatten_then_filter(self):
        result = transform_pipeline(
            self.BASE_JSON,
            {"flatten": True, "filter_field": "region", "filter_value": "US"},
        )
        assert len(result["records"]) == 1
        assert result["records"][0]["metrics.sales"] == 200

    def test_summarise_after_flatten(self):
        result = transform_pipeline(
            self.BASE_JSON,
            {"flatten": True, "summarise_field": "metrics.sales"},
        )
        assert result["summary"]["count"] == 3
        assert result["summary"]["min"] == 100
        assert result["summary"]["max"] == 200

    def test_rename_fields(self):
        result = transform_pipeline(
            self.BASE_JSON,
            {"rename": {"region": "area"}},
        )
        assert all("area" in r for r in result["records"])

    def test_accepts_wrapped_data_key(self):
        wrapped = json.dumps({"data": [{"a": 1}, {"a": 2}]})
        result = transform_pipeline(wrapped, {})
        assert len(result["records"]) == 2
