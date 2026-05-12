from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path_str: str | Path) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return project_root() / path


def ensure_directory(path: str | Path) -> Path:
    target = resolve_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_text(path: str | Path) -> str:
    return resolve_path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, content: str) -> Path:
    target = resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def load_json(path: str | Path) -> Any:
    return json.loads(read_text(path))


def dump_json(path: str | Path, payload: Any) -> Path:
    return write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def load_yaml_like(path: str | Path) -> Any:
    text = read_text(path)
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception:
        return json.loads(text)


def read_csv_records(path: str | Path) -> list[dict[str, str]]:
    with resolve_path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    target = resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return target


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    target = resolve_path(path)
    if not target.exists():
        return []
    rows = []
    with target.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    target = resolve_path(path)
    if not target.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in target.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_env_value(name: str, default: str | None = None) -> str | None:
    file_values = load_env_file()
    return os.getenv(name, file_values.get(name, default))
