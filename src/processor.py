"""
JSON Data Transformation Processor
Core application logic for transforming, filtering, and summarising JSON datasets.
"""

import json
import statistics
from typing import Any


# ---------------------------------------------------------------------------
# Transform helpers
# ---------------------------------------------------------------------------

def load_json(data: str) -> Any:
    """Parse a JSON string and return the Python object."""
    return json.loads(data)


def flatten_record(record: dict, parent_key: str = "", sep: str = ".") -> dict:
    """
    Recursively flatten a nested dictionary.

    Example:
        {"a": {"b": 1}} -> {"a.b": 1}
    """
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
    """
    Rename keys in *record* according to *mapping* {old_name: new_name}.
    Keys not in *mapping* are kept as-is.
    """
    return {mapping.get(k, k): v for k, v in record.items()}


def rename_fields_in_records(records: list[dict], mapping: dict[str, str]) -> list[dict]:
    """Apply :func:`rename_fields` to every record."""
    return [rename_fields(r, mapping) for r in records]


def extract_field(records: list[dict], field: str) -> list:
    """Extract the value of *field* from every record (skips missing keys)."""
    return [r[field] for r in records if field in r]


def summarise(records: list[dict], numeric_field: str) -> dict:
    """
    Return basic statistics for *numeric_field* across all records.

    Returns:
        dict with keys: count, min, max, mean, median, stdev (or None if < 2 values)
    """
    values = []
    for r in records:
        val = r.get(numeric_field)
        if isinstance(val, (int, float)):
            values.append(val)

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
        flatten       (bool)   – flatten nested records
        filter_field  (str)    – field name to filter on
        filter_value  (any)    – value to match
        rename        (dict)   – {old: new} field rename mapping
        summarise_field (str)  – numeric field to summarise

    Returns:
        {"records": [...], "summary": {...} | None}
    """
    data = load_json(raw_json)

    # Accept either a top-level list or {"data": [...]}
    if isinstance(data, dict):
        records: list[dict] = data.get("data", [])
    else:
        records = data

    if config.get("flatten"):
        records = flatten_records(records)

    if config.get("filter_field") is not None:
        records = filter_records(records, config["filter_field"], config.get("filter_value"))

    if config.get("rename"):
        records = rename_fields_in_records(records, config["rename"])

    summary = None
    if config.get("summarise_field"):
        summary = summarise(records, config["summarise_field"])

    return {"records": records, "summary": summary}
