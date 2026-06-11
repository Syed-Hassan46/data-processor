import json
import statistics


def load_json(raw):
    return json.loads(raw)


def flatten(rec, prefix="", sep="."):
    out = {}
    for k, v in rec.items():
        key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key, sep))
        else:
            out[key] = v
    return out


def flatten_all(rows):
    return [flatten(r) for r in rows]


def filter_rows(rows, field, val):
    return [r for r in rows if r.get(field) == val]


def rename_keys(rec, mapping):
    return {mapping.get(k, k): v for k, v in rec.items()}


def rename_all(rows, mapping):
    return [rename_keys(r, mapping) for r in rows]


def pluck(rows, field):
    return [r[field] for r in rows if field in r]


def get_stats(rows, field):
    nums = [r[field] for r in rows if isinstance(r.get(field), (int, float))]
    if not nums:
        return {"count": 0, "min": None, "max": None,
                "mean": None, "median": None, "stdev": None}
    return {
        "count": len(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": round(statistics.mean(nums), 4),
        "median": statistics.median(nums),
        "stdev": round(statistics.stdev(nums), 4) if len(nums) >= 2 else None,
    }


def run(raw, cfg):
    data = load_json(raw)
    rows = data.get("data", []) if isinstance(data, dict) else data

    if cfg.get("flatten"):
        rows = flatten_all(rows)

    if cfg.get("filter_field") is not None:
        rows = filter_rows(rows, cfg["filter_field"], cfg.get("filter_value"))

    if cfg.get("rename"):
        rows = rename_all(rows, cfg["rename"])

    stats = get_stats(rows, cfg["summarise_field"]) if cfg.get("summarise_field") else None

    return {"rows": rows, "stats": stats}
