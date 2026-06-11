#!/usr/bin/env bash
# =============================================================================
#  setup_project.sh
#  Creates the full folder & file structure for the JSON Data Processor project.
#  Run from the directory where you want the project root created.
#
#  Usage:
#    chmod +x setup_project.sh
#    ./setup_project.sh [project-name]        # default: data-processor
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_NAME="${1:-data-processor}"
ROOT="./${PROJECT_NAME}"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'   # no colour

log()   { echo -e "${CYAN}[setup]${NC} $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Abort if root already exists
# ---------------------------------------------------------------------------
if [[ -d "${ROOT}" ]]; then
    warn "Directory '${ROOT}' already exists. Aborting to avoid overwriting."
    exit 1
fi

log "Creating project structure in '${ROOT}' ..."

# ---------------------------------------------------------------------------
# Folder tree
# ---------------------------------------------------------------------------
mkdir -p \
    "${ROOT}/src" \
    "${ROOT}/tests/unit" \
    "${ROOT}/tests/integration" \
    "${ROOT}/reports" \
    "${ROOT}/data/samples" \
    "${ROOT}/docs" \
    "${ROOT}/scripts"

ok "Directories created."

# ---------------------------------------------------------------------------
# Python package markers
# ---------------------------------------------------------------------------
touch "${ROOT}/src/__init__.py"
touch "${ROOT}/tests/__init__.py"
touch "${ROOT}/tests/unit/__init__.py"
touch "${ROOT}/tests/integration/__init__.py"

ok "__init__.py files created."

# ---------------------------------------------------------------------------
# requirements.txt
# ---------------------------------------------------------------------------
cat > "${ROOT}/requirements.txt" << 'REQUIREMENTS'
# Runtime – stdlib only, no external runtime deps

# Testing & quality
pytest==8.2.0
pytest-cov==5.0.0
flake8==7.0.0
REQUIREMENTS

ok "requirements.txt written."

# ---------------------------------------------------------------------------
# pyproject.toml  (pytest + coverage config)
# ---------------------------------------------------------------------------
cat > "${ROOT}/pyproject.toml" << 'TOML'
[tool.pytest.ini_options]
testpaths   = ["tests"]
pythonpath  = ["."]
addopts     = "-v --tb=short"

[tool.coverage.run]
source = ["src"]
omit   = ["tests/*"]

[tool.coverage.report]
show_missing = true
TOML

ok "pyproject.toml written."

# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------
cat > "${ROOT}/.gitignore" << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.pyo
*.egg-info/
dist/
build/

# Virtual environments
.venv/
venv/
env/

# Test / coverage artefacts
reports/
.coverage
.pytest_cache/
htmlcov/

# Editor
.vscode/
.idea/
*.swp
GITIGNORE

ok ".gitignore written."

# ---------------------------------------------------------------------------
# src/processor.py  – main application
# ---------------------------------------------------------------------------
cat > "${ROOT}/src/processor.py" << 'PROCESSOR'
"""
JSON Data Transformation Processor
Core application logic for transforming, filtering, and summarising JSON datasets.
"""

import json
import statistics
from typing import Any


def load_json(data: str) -> Any:
    """Parse a JSON string and return the Python object."""
    return json.loads(data)


def flatten_record(record: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Recursively flatten a nested dictionary."""
    items: dict = {}
    for key, value in record.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_record(value, new_key, sep=sep))
        else:
            items[new_key] = value
    return items


def flatten_records(records: list[dict]) -> list[dict]:
    """Flatten every record in a list."""
    return [flatten_record(r) for r in records]


def filter_records(records: list[dict], field: str, value: Any) -> list[dict]:
    """Return only records where *field* equals *value*."""
    return [r for r in records if r.get(field) == value]


def rename_fields(record: dict, mapping: dict[str, str]) -> dict:
    """Rename keys in *record* according to *mapping* {old_name: new_name}."""
    return {mapping.get(k, k): v for k, v in record.items()}


def rename_fields_in_records(records: list[dict], mapping: dict[str, str]) -> list[dict]:
    """Apply rename_fields to every record."""
    return [rename_fields(r, mapping) for r in records]


def extract_field(records: list[dict], field: str) -> list:
    """Extract the value of *field* from every record (skips missing keys)."""
    return [r[field] for r in records if field in r]


def summarise(records: list[dict], numeric_field: str) -> dict:
    """Return basic statistics for *numeric_field* across all records."""
    values = [
        r[numeric_field]
        for r in records
        if isinstance(r.get(numeric_field), (int, float))
    ]
    if not values:
        return {"count": 0, "min": None, "max": None,
                "mean": None, "median": None, "stdev": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 4),
        "median": statistics.median(values),
        "stdev": round(statistics.stdev(values), 4) if len(values) >= 2 else None,
    }


def transform_pipeline(raw_json: str, config: dict) -> dict:
    """
    Run a configurable transformation pipeline on a JSON dataset.

    Config keys (all optional):
        flatten         (bool)  – flatten nested records
        filter_field    (str)   – field name to filter on
        filter_value    (any)   – value to match
        rename          (dict)  – {old: new} field rename mapping
        summarise_field (str)   – numeric field to summarise
    """
    data = load_json(raw_json)
    records: list[dict] = data.get("data", []) if isinstance(data, dict) else data

    if config.get("flatten"):
        records = flatten_records(records)
    if config.get("filter_field") is not None:
        records = filter_records(records, config["filter_field"], config.get("filter_value"))
    if config.get("rename"):
        records = rename_fields_in_records(records, config["rename"])

    summary = summarise(records, config["summarise_field"]) if config.get("summarise_field") else None
    return {"records": records, "summary": summary}
PROCESSOR

ok "src/processor.py written."

# ---------------------------------------------------------------------------
# tests/unit/test_processor.py  – unit tests
# ---------------------------------------------------------------------------
cat > "${ROOT}/tests/unit/test_processor.py" << 'UNIT_TESTS'
"""Unit Tests – JSON Data Transformation Processor"""

import json
import pytest
from src.processor import (
    load_json, flatten_record, flatten_records, filter_records,
    rename_fields, rename_fields_in_records, extract_field,
    summarise, transform_pipeline,
)


class TestLoadJson:
    def test_parses_list(self):       assert load_json('[1,2,3]') == [1, 2, 3]
    def test_parses_dict(self):       assert load_json('{"a":1}') == {"a": 1}
    def test_invalid_raises(self):
        with pytest.raises(json.JSONDecodeError): load_json("{bad}")
    def test_empty_list(self):        assert load_json('[]') == []


class TestFlattenRecord:
    def test_flat_unchanged(self):    assert flatten_record({"a": 1}) == {"a": 1}
    def test_one_level(self):         assert flatten_record({"u": {"n": "Alice"}}) == {"u.n": "Alice"}
    def test_deep(self):              assert flatten_record({"a": {"b": {"c": 9}}}) == {"a.b.c": 9}
    def test_custom_sep(self):        assert flatten_record({"a": {"b": 1}}, sep="_") == {"a_b": 1}
    def test_empty(self):             assert flatten_record({}) == {}


class TestFilterRecords:
    R = [{"s": "active", "v": 10}, {"s": "inactive", "v": 20}, {"s": "active", "v": 30}]
    def test_by_string(self):         assert len(filter_records(self.R, "s", "active")) == 2
    def test_no_match(self):          assert filter_records(self.R, "s", "x") == []
    def test_missing_excluded(self):  assert filter_records([{"a": 1}, {"b": 2}], "a", 1) == [{"a": 1}]


class TestSummarise:
    R = [{"v": 10}, {"v": 20}, {"v": 30}, {"v": 40}]
    def test_count(self):             assert summarise(self.R, "v")["count"] == 4
    def test_mean(self):              assert summarise(self.R, "v")["mean"] == 25.0
    def test_no_values(self):         assert summarise([{"v": "x"}], "v")["count"] == 0
    def test_single_stdev_none(self): assert summarise([{"v": 5}], "v")["stdev"] is None


class TestTransformPipeline:
    B = json.dumps([
        {"region": "EU", "metrics": {"sales": 100, "returns": 5}},
        {"region": "US", "metrics": {"sales": 200, "returns": 10}},
        {"region": "EU", "metrics": {"sales": 150, "returns": 8}},
    ])
    def test_no_config_all(self):     assert len(transform_pipeline(self.B, {})["records"]) == 3
    def test_flatten(self):           assert "metrics.sales" in transform_pipeline(self.B, {"flatten": True})["records"][0]
    def test_filter(self):            assert len(transform_pipeline(self.B, {"filter_field": "region", "filter_value": "EU"})["records"]) == 2
    def test_summarise(self):
        s = transform_pipeline(self.B, {"flatten": True, "summarise_field": "metrics.sales"})["summary"]
        assert s["count"] == 3
    def test_rename(self):
        r = transform_pipeline(self.B, {"rename": {"region": "area"}})["records"]
        assert all("area" in x for x in r)
UNIT_TESTS

ok "tests/unit/test_processor.py written."

# ---------------------------------------------------------------------------
# tests/integration/test_pipeline_integration.py  – integration tests
# ---------------------------------------------------------------------------
cat > "${ROOT}/tests/integration/test_pipeline_integration.py" << 'INT_TESTS'
"""Integration Tests – JSON Data Transformation Processor"""

import json
import pytest
from src.processor import transform_pipeline, load_json

SALES = [
    {"id": 1, "region": "EU",   "product": "Widget A", "metrics": {"sales": 120, "returns": 4}},
    {"id": 2, "region": "US",   "product": "Widget B", "metrics": {"sales": 340, "returns": 12}},
    {"id": 3, "region": "EU",   "product": "Widget C", "metrics": {"sales": 95,  "returns": 2}},
    {"id": 4, "region": "APAC", "product": "Widget A", "metrics": {"sales": 210, "returns": 7}},
    {"id": 5, "region": "US",   "product": "Widget C", "metrics": {"sales": 400, "returns": 15}},
]

@pytest.fixture
def sales_json():       return json.dumps(SALES)

@pytest.fixture
def sales_file(tmp_path):
    p = tmp_path / "sales.json"
    p.write_text(json.dumps(SALES), encoding="utf-8")
    return str(p)


class TestFileIO:
    def test_read_from_file(self, sales_file):
        with open(sales_file, encoding="utf-8") as fh: raw = fh.read()
        assert len(load_json(raw)) == 5

    def test_write_result_to_file(self, sales_json, tmp_path):
        result = transform_pipeline(sales_json, {"flatten": True})
        out = tmp_path / "output.json"
        out.write_text(json.dumps(result), encoding="utf-8")
        assert len(json.loads(out.read_text())["records"]) == 5

    def test_roundtrip_preserves_summary(self, sales_file, tmp_path):
        with open(sales_file, encoding="utf-8") as fh: raw = fh.read()
        result = transform_pipeline(raw, {"flatten": True, "summarise_field": "metrics.sales"})
        out = tmp_path / "result.json"
        out.write_text(json.dumps(result), encoding="utf-8")
        assert json.loads(out.read_text())["summary"]["count"] == 5


class TestFullPipeline:
    def test_eu_summary(self, sales_json):
        s = transform_pipeline(sales_json, {
            "flatten": True, "filter_field": "region",
            "filter_value": "EU", "summarise_field": "metrics.sales",
        })["summary"]
        assert s["count"] == 2 and s["min"] == 95

    def test_rename_us(self, sales_json):
        recs = transform_pipeline(sales_json, {
            "filter_field": "region", "filter_value": "US",
            "rename": {"region": "territory"},
        })["records"]
        assert all("territory" in r and "region" not in r for r in recs)

    def test_global_mean(self, sales_json):
        s = transform_pipeline(sales_json, {
            "flatten": True, "summarise_field": "metrics.sales",
        })["summary"]
        assert s["mean"] == round((120+340+95+210+400)/5, 4)

    def test_empty_input(self):
        r = transform_pipeline(json.dumps([]), {"summarise_field": "sales"})
        assert r["records"] == [] and r["summary"]["count"] == 0

    def test_apac_report(self, sales_json, tmp_path):
        result = transform_pipeline(sales_json, {
            "flatten": True, "filter_field": "region", "filter_value": "APAC",
            "rename": {"region": "market"}, "summarise_field": "metrics.sales",
        })
        assert result["records"][0]["market"] == "APAC"
        assert result["summary"]["mean"] == 210.0
        out = tmp_path / "apac.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        assert out.exists()
INT_TESTS

ok "tests/integration/test_pipeline_integration.py written."

# ---------------------------------------------------------------------------
# Jenkinsfile
# ---------------------------------------------------------------------------
cat > "${ROOT}/Jenkinsfile" << 'JENKINSFILE'
// =============================================================================
//  Jenkinsfile  –  JSON Data Processor CI/CD Pipeline
//  Stages: Setup → Lint → Unit Tests → Integration Tests → Reports → Deploy
// =============================================================================

pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.11'
        VENV_DIR       = '.venv'
        REPORTS_DIR    = 'reports'
        DEPLOY_HOST    = credentials('deploy-ssh-host')
        DEPLOY_PATH    = '/opt/data-processor'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        timestamps()
    }

    triggers { pollSCM('H/5 * * * *') }

    stages {

        stage('Setup') {
            steps {
                sh """
                    python${PYTHON_VERSION} -m venv ${VENV_DIR}
                    ${VENV_DIR}/bin/pip install --upgrade pip
                    ${VENV_DIR}/bin/pip install -r requirements.txt
                    mkdir -p ${REPORTS_DIR}
                """
            }
        }

        stage('Lint') {
            steps {
                sh "${VENV_DIR}/bin/flake8 src/ tests/ --max-line-length=100 --statistics"
            }
        }

        stage('Unit Tests') {
            steps {
                sh """
                    ${VENV_DIR}/bin/pytest tests/unit/ \
                        --junitxml=${REPORTS_DIR}/unit_results.xml \
                        --cov=src \
                        --cov-report=xml:${REPORTS_DIR}/coverage.xml \
                        --cov-report=html:${REPORTS_DIR}/coverage_html \
                        --cov-fail-under=80 \
                        -v
                """
            }
            post { always { junit "${REPORTS_DIR}/unit_results.xml" } }
        }

        stage('Integration Tests') {
            steps {
                sh """
                    ${VENV_DIR}/bin/pytest tests/integration/ \
                        --junitxml=${REPORTS_DIR}/integration_results.xml \
                        -v
                """
            }
            post { always { junit "${REPORTS_DIR}/integration_results.xml" } }
        }

        stage('Publish Reports') {
            steps {
                archiveArtifacts artifacts: "${REPORTS_DIR}/**", fingerprint: true
                publishHTML(target: [
                    allowMissing: false, alwaysLinkToLastBuild: true, keepAll: true,
                    reportDir: "${REPORTS_DIR}/coverage_html",
                    reportFiles: 'index.html', reportName: 'Coverage Report'
                ])
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                sshagent(credentials: ['deploy-ssh-key']) {
                    sh """
                        rsync -avz --delete \
                            --exclude='__pycache__' --exclude='*.pyc' \
                            src/ ${DEPLOY_HOST}:${DEPLOY_PATH}/src/
                        ssh ${DEPLOY_HOST} "cd ${DEPLOY_PATH} && pip install -r requirements.txt"
                    """
                }
            }
        }
    }

    post {
        success { echo "Pipeline completed successfully." }
        failure { echo "Pipeline FAILED." }
        always  { cleanWs(patterns: [[pattern: "${VENV_DIR}/**", type: 'INCLUDE']]) }
    }
}
JENKINSFILE

ok "Jenkinsfile written."

# ---------------------------------------------------------------------------
# docs/test_process.md
# ---------------------------------------------------------------------------
cat > "${ROOT}/docs/test_process.md" << 'DOCS'
# Test Process Document

## Who Runs the Tests

| Role             | Responsibility                                              |
|------------------|-------------------------------------------------------------|
| Developer        | Runs unit tests locally before every commit                 |
| CI System        | Runs full pipeline (lint + unit + integration) on every push|
| Tech Lead / QA   | Reviews coverage reports and approves merges to `main`      |

## When Tests Are Run

| Event                          | Tests Triggered                                |
|--------------------------------|------------------------------------------------|
| Developer commits (pre-push)   | Unit tests (`pytest tests/unit/`)              |
| Push / PR to any branch        | Lint + Unit + Integration (full Jenkins pipeline) |
| Merge to `main`                | Full pipeline + Deploy stage                   |
| Scheduled (every 5 min poll)   | Full pipeline if new commits detected          |

## How to Run Tests Locally

```bash
# 1. Create virtual environment
python3.11 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run unit tests only
pytest tests/unit/ -v

# 4. Run integration tests only
pytest tests/integration/ -v

# 5. Run all tests with coverage
pytest tests/ --cov=src --cov-report=html -v

# 6. Lint check
flake8 src/ tests/ --max-line-length=100
```

## Test Result Storage

- **JUnit XML** → `reports/unit_results.xml` and `reports/integration_results.xml`
  - Archived by Jenkins; viewable in the build's "Test Results" tab.
- **Coverage XML** → `reports/coverage.xml` (machine-readable)
- **Coverage HTML** → `reports/coverage_html/` (human-readable; linked in Jenkins UI)
- **Historical builds** → last 10 builds retained (configurable in Jenkinsfile)

## Test Suite Optimisation

- `--cov-fail-under=80`: build fails if coverage drops below 80 %, preventing regressions.
- `--lf` flag (last-failed): add to any local re-run to execute only previously failing tests.
- Unit and integration stages are **separate Jenkins stages** so a unit failure aborts before
  the slower integration suite runs, giving faster feedback.
DOCS

ok "docs/test_process.md written."

# ---------------------------------------------------------------------------
# data/samples/sample_input.json
# ---------------------------------------------------------------------------
cat > "${ROOT}/data/samples/sample_input.json" << 'SAMPLE'
[
  {"id": 1, "region": "EU",   "product": "Widget A", "metrics": {"sales": 120, "returns": 4}},
  {"id": 2, "region": "US",   "product": "Widget B", "metrics": {"sales": 340, "returns": 12}},
  {"id": 3, "region": "EU",   "product": "Widget C", "metrics": {"sales": 95,  "returns": 2}},
  {"id": 4, "region": "APAC", "product": "Widget A", "metrics": {"sales": 210, "returns": 7}},
  {"id": 5, "region": "US",   "product": "Widget C", "metrics": {"sales": 400, "returns": 15}}
]
SAMPLE

ok "data/samples/sample_input.json written."

# ---------------------------------------------------------------------------
# scripts/run_tests.sh  – convenience script for local dev
# ---------------------------------------------------------------------------
cat > "${ROOT}/scripts/run_tests.sh" << 'RUNTESTS'
#!/usr/bin/env bash
# Quick local test runner – mirrors the Jenkins pipeline stages.
set -euo pipefail

VENV=".venv"
REPORTS="reports"

echo "==> Setting up virtualenv..."
python3 -m venv "${VENV}"
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
mkdir -p "${REPORTS}"

echo "==> Linting..."
flake8 src/ tests/ --max-line-length=100 --statistics

echo "==> Unit tests..."
pytest tests/unit/ \
    --junitxml="${REPORTS}/unit_results.xml" \
    --cov=src \
    --cov-report=html:"${REPORTS}/coverage_html" \
    --cov-fail-under=80 \
    -v

echo "==> Integration tests..."
pytest tests/integration/ \
    --junitxml="${REPORTS}/integration_results.xml" \
    -v

echo ""
echo "All stages passed. Coverage report: ${REPORTS}/coverage_html/index.html"
RUNTESTS

chmod +x "${ROOT}/scripts/run_tests.sh"
ok "scripts/run_tests.sh written (executable)."

# ---------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------
cat > "${ROOT}/README.md" << 'README'
# JSON Data Processor

A Python data-processing pipeline with full CI/CD via Jenkins.

## Project Structure

```
data-processor/
├── src/                          # Application source
│   └── processor.py
├── tests/
│   ├── unit/                     # Unit tests (pytest)
│   │   └── test_processor.py
│   └── integration/              # Integration tests (pytest)
│       └── test_pipeline_integration.py
├── data/samples/                 # Sample JSON datasets
├── docs/
│   └── test_process.md           # Who / When / How process doc
├── reports/                      # Generated test & coverage reports (git-ignored)
├── scripts/
│   └── run_tests.sh              # Local test runner
├── Jenkinsfile                   # Declarative CD pipeline
├── pyproject.toml                # pytest & coverage config
├── requirements.txt
└── README.md
```

## Quick Start

```bash
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh
```

## Jenkins Setup

1. Create a **Pipeline** job in Jenkins.
2. Point it at this repository; set *Script Path* to `Jenkinsfile`.
3. Add two credentials:
   - `deploy-ssh-host` (Secret text) – SSH user@host for deployment
   - `deploy-ssh-key`  (SSH Username with private key) – private key for rsync/ssh
4. Install Jenkins plugins: **Pipeline**, **HTML Publisher**, **SSH Agent**.
README

ok "README.md written."

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Project '${PROJECT_NAME}' created!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  Directory layout:"
find "${ROOT}" -not -path '*/__pycache__/*' | sort | sed "s|${ROOT}||" | sed 's|^|  |'
echo ""
echo "  Next steps:"
echo "  1.  cd ${PROJECT_NAME}"
echo "  2.  ./scripts/run_tests.sh          # run everything locally"
echo "  3.  git init && git add . && git commit -m 'initial commit'"
echo "  4.  Point a Jenkins Pipeline job at the repo (see README.md)"
echo ""
