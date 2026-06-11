import json
import pytest
from src.processor import transform_pipeline, load_json


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SALES_DATASET = [
    {"id": 1, "region": "EU", "product": "Widget A", "metrics": {"sales": 120, "returns": 4}},
    {"id": 2, "region": "US", "product": "Widget B", "metrics": {"sales": 340, "returns": 12}},
    {"id": 3, "region": "EU", "product": "Widget C", "metrics": {"sales": 95,  "returns": 2}},
    {"id": 4, "region": "APAC", "product": "Widget A", "metrics": {"sales": 210, "returns": 7}},
    {"id": 5, "region": "US", "product": "Widget C", "metrics": {"sales": 400, "returns": 15}},
]


@pytest.fixture
def sales_json():
    return json.dumps(SALES_DATASET)


@pytest.fixture
def sales_json_file(tmp_path):
    """Write the sales dataset to a temporary JSON file and return its path."""
    p = tmp_path / "sales.json"
    p.write_text(json.dumps(SALES_DATASET), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# File I/O integration
# ---------------------------------------------------------------------------

class TestFileIO:
    def test_read_from_file(self, sales_json_file):
        with open(sales_json_file, encoding="utf-8") as fh:
            raw = fh.read()
        data = load_json(raw)
        assert len(data) == 5

    def test_write_result_to_file(self, sales_json, tmp_path):
        result = transform_pipeline(sales_json, {"flatten": True})
        out_path = tmp_path / "output.json"
        out_path.write_text(json.dumps(result), encoding="utf-8")
        reloaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert len(reloaded["records"]) == 5

    def test_roundtrip_preserves_data(self, sales_json_file, tmp_path):
        with open(sales_json_file, encoding="utf-8") as fh:
            raw = fh.read()
        result = transform_pipeline(raw, {"flatten": True, "summarise_field": "metrics.sales"})
        out = tmp_path / "result.json"
        out.write_text(json.dumps(result), encoding="utf-8")
        reloaded = json.loads(out.read_text())
        assert reloaded["summary"]["count"] == 5


# ---------------------------------------------------------------------------
# Full pipeline end-to-end scenarios
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_eu_sales_summary(self, sales_json):
        """Filter EU records, flatten, then summarise sales."""
        result = transform_pipeline(
            sales_json,
            {
                "flatten": True,
                "filter_field": "region",
                "filter_value": "EU",
                "summarise_field": "metrics.sales",
            },
        )
        assert result["summary"]["count"] == 2
        assert result["summary"]["min"] == 95
        assert result["summary"]["max"] == 120

    def test_us_records_renamed(self, sales_json):
        """Filter US records and rename 'region' -> 'territory'."""
        result = transform_pipeline(
            sales_json,
            {
                "filter_field": "region",
                "filter_value": "US",
                "rename": {"region": "territory", "product": "item"},
            },
        )
        assert len(result["records"]) == 2
        assert all("territory" in r for r in result["records"])
        assert all("region" not in r for r in result["records"])

    def test_flatten_exposes_nested_keys(self, sales_json):
        result = transform_pipeline(sales_json, {"flatten": True})
        for rec in result["records"]:
            assert "metrics.sales" in rec
            assert "metrics.returns" in rec
            assert "metrics" not in rec

    def test_global_summary_all_records(self, sales_json):
        result = transform_pipeline(
            sales_json,
            {"flatten": True, "summarise_field": "metrics.sales"},
        )
        s = result["summary"]
        assert s["count"] == 5
        assert s["min"] == 95
        assert s["max"] == 400
        expected_mean = round((120 + 340 + 95 + 210 + 400) / 5, 4)
        assert s["mean"] == expected_mean

    def test_empty_dataset(self):
        result = transform_pipeline(json.dumps([]), {"flatten": True, "summarise_field": "sales"})
        assert result["records"] == []
        assert result["summary"]["count"] == 0

    def test_single_record_stdev_is_none(self):
        data = json.dumps([{"region": "EU", "sales": 50}])
        result = transform_pipeline(data, {"summarise_field": "sales"})
        assert result["summary"]["stdev"] is None

    def test_filter_produces_empty_subset(self, sales_json):
        result = transform_pipeline(
            sales_json,
            {"filter_field": "region", "filter_value": "UNKNOWN"},
        )
        assert result["records"] == []

    def test_pipeline_with_wrapped_data_key(self):
        wrapped = json.dumps({"data": SALES_DATASET})
        result = transform_pipeline(
            wrapped,
            {"flatten": True, "summarise_field": "metrics.sales"},
        )
        assert result["summary"]["count"] == 5


# ---------------------------------------------------------------------------
# Realistic multi-step scenario
# ---------------------------------------------------------------------------

class TestRealisticScenario:
    def test_apac_report(self, sales_json, tmp_path):
        """
        Simulate a reporting workflow:
        1. Read raw JSON
        2. Flatten
        3. Filter to APAC
        4. Rename fields for downstream system
        5. Summarise
        6. Write to output file
        7. Verify output
        """
        result = transform_pipeline(
            sales_json,
            {
                "flatten": True,
                "filter_field": "region",
                "filter_value": "APAC",
                "rename": {"region": "market", "product": "sku"},
                "summarise_field": "metrics.sales",
            },
        )

        # Should have exactly 1 APAC record
        assert len(result["records"]) == 1
        rec = result["records"][0]
        assert rec["market"] == "APAC"
        assert rec["sku"] == "Widget A"
        assert rec["metrics.sales"] == 210

        # Summary reflects the single record
        assert result["summary"]["count"] == 1
        assert result["summary"]["mean"] == 210.0

        # Persist to file
        out = tmp_path / "apac_report.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        assert out.exists()
        reloaded = json.loads(out.read_text())
        assert reloaded["summary"]["min"] == 210
