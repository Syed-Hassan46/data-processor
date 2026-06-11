import json
import pytest
from src.processor import run, load_json


SALES = [
    {"id": 1, "region": "EU",   "product": "Widget A", "metrics": {"sales": 120, "returns": 4}},
    {"id": 2, "region": "US",   "product": "Widget B", "metrics": {"sales": 340, "returns": 12}},
    {"id": 3, "region": "EU",   "product": "Widget C", "metrics": {"sales": 95,  "returns": 2}},
    {"id": 4, "region": "APAC", "product": "Widget A", "metrics": {"sales": 210, "returns": 7}},
    {"id": 5, "region": "US",   "product": "Widget C", "metrics": {"sales": 400, "returns": 15}},
]


@pytest.fixture
def sales_json():
    return json.dumps(SALES)


@pytest.fixture
def sales_file(tmp_path):
    p = tmp_path / "sales.json"
    p.write_text(json.dumps(SALES), encoding="utf-8")
    return str(p)


class TestFileIO:
    def test_read_file(self, sales_file):
        with open(sales_file, encoding="utf-8") as f:
            data = load_json(f.read())
        assert len(data) == 5

    def test_write_output(self, sales_json, tmp_path):
        res = run(sales_json, {"flatten": True})
        out = tmp_path / "out.json"
        out.write_text(json.dumps(res), encoding="utf-8")
        reloaded = json.loads(out.read_text())
        assert len(reloaded["rows"]) == 5

    def test_roundtrip(self, sales_file, tmp_path):
        with open(sales_file, encoding="utf-8") as f:
            raw = f.read()
        res = run(raw, {"flatten": True, "summarise_field": "metrics.sales"})
        out = tmp_path / "result.json"
        out.write_text(json.dumps(res), encoding="utf-8")
        assert json.loads(out.read_text())["stats"]["count"] == 5


class TestFullPipeline:
    def test_eu_summary(self, sales_json):
        cfg = {
            "flatten": True,
            "filter_field": "region",
            "filter_value": "EU",
            "summarise_field": "metrics.sales"
        }
        s = run(sales_json, cfg)["stats"]
        assert s["count"] == 2
        assert s["min"] == 95
        assert s["max"] == 120

    def test_rename_us(self, sales_json):
        cfg = {
            "filter_field": "region",
            "filter_value": "US",
            "rename": {"region": "territory", "product": "item"}
        }
        rows = run(sales_json, cfg)["rows"]
        assert len(rows) == 2
        assert all("territory" in r for r in rows)
        assert all("region" not in r for r in rows)

    def test_nested_keys_exposed(self, sales_json):
        rows = run(sales_json, {"flatten": True})["rows"]
        for r in rows:
            assert "metrics.sales" in r
            assert "metrics" not in r

    def test_global_mean(self, sales_json):
        s = run(sales_json, {"flatten": True, "summarise_field": "metrics.sales"})["stats"]
        assert s["count"] == 5
        expected = round((120 + 340 + 95 + 210 + 400) / 5, 4)
        assert s["mean"] == expected

    def test_empty_input(self):
        res = run(json.dumps([]), {"summarise_field": "sales"})
        assert res["rows"] == []
        assert res["stats"]["count"] == 0

    def test_single_record_no_stdev(self):
        data = json.dumps([{"region": "EU", "sales": 50}])
        assert run(data, {"summarise_field": "sales"})["stats"]["stdev"] is None

    def test_no_match_filter(self, sales_json):
        cfg = {"filter_field": "region", "filter_value": "NOWHERE"}
        assert run(sales_json, cfg)["rows"] == []

    def test_wrapped_json(self):
        wrapped = json.dumps({"data": SALES})
        s = run(wrapped, {"flatten": True, "summarise_field": "metrics.sales"})["stats"]
        assert s["count"] == 5


class TestRealistic:
    def test_apac_report(self, sales_json, tmp_path):
        cfg = {
            "flatten": True,
            "filter_field": "region",
            "filter_value": "APAC",
            "rename": {"region": "market", "product": "sku"},
            "summarise_field": "metrics.sales"
        }
        res = run(sales_json, cfg)

        assert len(res["rows"]) == 1
        row = res["rows"][0]
        assert row["market"] == "APAC"
        assert row["sku"] == "Widget A"
        assert row["metrics.sales"] == 210

        assert res["stats"]["count"] == 1
        assert res["stats"]["mean"] == 210.0

        out = tmp_path / "apac.json"
        out.write_text(json.dumps(res, indent=2), encoding="utf-8")
        assert out.exists()
        assert json.loads(out.read_text())["stats"]["min"] == 210
