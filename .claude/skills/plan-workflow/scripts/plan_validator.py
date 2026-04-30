#!/usr/bin/env python3
"""Validate feature-list.json against JSON Schema + DAG checks.

Pure stdlib. Implements the subset of JSON Schema 2020-12 used by
.claude/schemas/feature-list.schema.json: type, required, properties,
additionalProperties, enum, pattern, minLength, maxLength, minItems,
maxItems, items, uniqueItems, $ref (#/$defs/X), allOf, if/then, $defs.

Usage: plan_validator.py <path-to-feature-list.json> [--schema <path>]

Exit codes:
  0  PASS — schema + DAG OK
  1  FAIL — schema or DAG violations
  2  cannot read file
"""
from __future__ import annotations
import sys
import json
import re
import argparse
from pathlib import Path


# ----- JSON Schema validator (subset) -----

class SchemaError(Exception):
    pass


def resolve_ref(root: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise SchemaError(f"unsupported $ref: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _check_type(data, t: str) -> bool:
    return {
        "object": isinstance(data, dict),
        "array": isinstance(data, list),
        "string": isinstance(data, str),
        "number": isinstance(data, (int, float)) and not isinstance(data, bool),
        "integer": isinstance(data, int) and not isinstance(data, bool),
        "boolean": isinstance(data, bool),
        "null": data is None,
    }.get(t, False)


def validate(data, schema: dict, root: dict, path: str = "$") -> list[str]:
    errors: list[str] = []

    if "$ref" in schema:
        return validate(data, resolve_ref(root, schema["$ref"]), root, path)

    if "allOf" in schema:
        for sub in schema["allOf"]:
            errors.extend(validate(data, sub, root, path))

    if "if" in schema:
        if_errors = validate(data, schema["if"], root, path)
        if not if_errors and "then" in schema:
            errors.extend(validate(data, schema["then"], root, path))
        elif if_errors and "else" in schema:
            errors.extend(validate(data, schema["else"], root, path))

    if "not" in schema:
        not_errors = validate(data, schema["not"], root, path)
        if not not_errors:
            errors.append(f"{path}: matched schema under 'not'")

    if "const" in schema:
        if data != schema["const"]:
            errors.append(f"{path}: must equal const {schema['const']!r}")

    if "type" in schema:
        t = schema["type"]
        if isinstance(t, list):
            if not any(_check_type(data, ti) for ti in t):
                errors.append(f"{path}: type must be one of {t}")
        elif not _check_type(data, t):
            errors.append(f"{path}: type must be {t}, got {type(data).__name__}")

    if isinstance(data, dict):
        if "required" in schema:
            for k in schema["required"]:
                if k not in data:
                    errors.append(f"{path}: missing required field '{k}'")
        if "properties" in schema:
            for k, v in data.items():
                if k in schema["properties"]:
                    errors.extend(validate(v, schema["properties"][k], root, f"{path}.{k}"))
        if schema.get("additionalProperties") is False and "properties" in schema:
            for k in data:
                if k not in schema["properties"]:
                    errors.append(f"{path}: additional property '{k}' not allowed")

    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path}: array len {len(data)} < min {schema['minItems']}")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errors.append(f"{path}: array len {len(data)} > max {schema['maxItems']}")
        if "items" in schema:
            for i, item in enumerate(data):
                errors.extend(validate(item, schema["items"], root, f"{path}[{i}]"))
        if schema.get("uniqueItems"):
            seen = []
            for i, item in enumerate(data):
                if item in seen:
                    errors.append(f"{path}[{i}]: duplicate item")
                seen.append(item)

    if isinstance(data, str):
        if "pattern" in schema:
            if not re.search(schema["pattern"], data):
                errors.append(f"{path}: '{data}' does not match pattern {schema['pattern']!r}")
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: length {len(data)} < min {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"{path}: length {len(data)} > max {schema['maxLength']}")

    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append(f"{path}: '{data}' not in enum {schema['enum']}")

    return errors


# ----- DAG checks -----

def check_dag_cycles(features: list[dict]) -> list[list[str]]:
    by_id = {f["id"]: f for f in features}
    color: dict[str, str] = {fid: "white" for fid in by_id}
    cycles: list[list[str]] = []

    def dfs(fid: str, stack: list[str]):
        if color[fid] == "gray":
            cycles.append(stack[stack.index(fid):] + [fid])
            return
        if color[fid] == "black":
            return
        color[fid] = "gray"
        for dep in by_id[fid].get("depends_on", []):
            if dep in by_id:
                dfs(dep, stack + [fid])
        color[fid] = "black"

    for fid in by_id:
        if color[fid] == "white":
            dfs(fid, [])
    return cycles


def check_missing_deps(features: list[dict]) -> list[str]:
    by_id = {f["id"] for f in features}
    out = []
    for f in features:
        for dep in f.get("depends_on", []):
            if dep not in by_id:
                out.append(f"{f['id']} depends on {dep} which doesn't exist in this batch")
    return out


def check_p1_priority_chain(features: list[dict]) -> list[str]:
    by_id = {f["id"]: f for f in features}
    out = []
    for f in features:
        if f.get("priority") == "P1":
            for dep in f.get("depends_on", []):
                if dep in by_id and by_id[dep].get("priority") in ("P2", "P3"):
                    out.append(f"{f['id']} (P1) depends on {dep} ({by_id[dep]['priority']}) — P1 cannot rely on lower-priority features")
    return out


# ----- Main -----

def main():
    p = argparse.ArgumentParser()
    p.add_argument("feature_list", help="path to specs/_batch/feature-list.json")
    p.add_argument("--schema", default=None, help="path to feature-list.schema.json (auto-detected if omitted)")
    args = p.parse_args()

    fl_path = Path(args.feature_list)
    if not fl_path.is_file():
        print(json.dumps({"status": "ERROR", "error": f"file not found: {fl_path}"}))
        sys.exit(2)

    if args.schema:
        schema_path = Path(args.schema)
    else:
        schema_path = Path(__file__).resolve().parents[3] / "schemas" / "feature-list.schema.json"

    if not schema_path.is_file():
        print(json.dumps({"status": "ERROR", "error": f"schema not found: {schema_path}"}))
        sys.exit(2)

    try:
        data = json.loads(fl_path.read_text())
        schema = json.loads(schema_path.read_text())
    except Exception as e:
        print(json.dumps({"status": "ERROR", "error": f"json parse: {e}"}))
        sys.exit(2)

    schema_errs = validate(data, schema, schema)
    features = data.get("features", []) if isinstance(data, dict) else []
    cycles = check_dag_cycles(features)
    missing = check_missing_deps(features)
    p1_violations = check_p1_priority_chain(features)

    failed = bool(schema_errs or cycles or missing or p1_violations)

    report = {
        "status": "FAIL" if failed else "PASS",
        "schema_errors": schema_errs,
        "cycles": cycles,
        "missing_deps": missing,
        "p1_priority_violations": p1_violations,
    }
    print(json.dumps(report, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
