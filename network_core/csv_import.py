"""Import explicit four-table UTF-8 CSV documentation into the canonical model.

This is a deliberately defined interchange format, not an attempt to guess
arbitrary spreadsheet columns or infer physical links from names and addresses.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from .model import ProjectValidationError, validate_project

# CSV header order is immaterial; column spelling and every value are explicit.
TABLES = {
    "Devices.csv": ("id", "label", "kind", "x", "y", "zoneId"),
    "Interfaces.csv": ("nodeId", "id", "name", "enabled", "ipv4"),
    "Links.csv": ("id", "aNode", "aPort", "bNode", "bPort", "enabled"),
    "Zones.csv": ("id", "label"),
}


def _invalid(where: str, reason: str) -> None:
    raise ProjectValidationError(f"{where}: {reason}")


def _read_table(name: str, text: str, columns: tuple[str, ...] | None = None) -> list[dict[str, str]]:
    if not isinstance(text, str):
        _invalid(name, "expected UTF-8 text")
    if "\x00" in text or "\ufffd" in text:
        _invalid(name, "invalid text encoding or NUL character")
    if text.startswith("\ufeff"):
        text = text[1:]  # UTF-8 BOM is a file encoding marker, not a column name
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
        expected = set(columns if columns is not None else TABLES[name])
        if len(header) != len(expected) or len(set(header)) != len(header) or set(header) != expected:
            _invalid(f"{name} header row 1", f"expected exactly these columns (any order): {', '.join(columns if columns is not None else TABLES[name])}")
        records = []
        for row in reader:
            line = reader.line_num
            if len(row) != len(header):
                _invalid(f"{name} line {line}", f"expected {len(header)} values; got {len(row)}")
            if not any(cell.strip() for cell in row):
                _invalid(f"{name} line {line}", "empty data row")
            records.append(dict(zip(header, row)))
            if len(records) > 5000:
                _invalid(name, "too many rows (maximum 5000)")
        return records
    except csv.Error as error:
        _invalid(f"{name} line {reader.line_num}", f"invalid CSV syntax: {error}")
    except StopIteration:
        _invalid(name, "missing header")


def _boolean(value: str, where: str) -> bool:
    if value not in ("true", "false"):
        _invalid(where, "expected exact 'true' or 'false'; no assumed default")
    return value == "true"


def _coordinate(value: str, where: str) -> float:
    try:
        return float(value)
    except ValueError:
        _invalid(where, "expected explicit numeric coordinate")


def import_csv_tables(value: Any) -> dict:
    """Return a validated canonical project; never reads or writes project files."""
    if not isinstance(value, dict) or set(value) != {"projectName", "files"}:
        _invalid("CSV import", "expected projectName and files")
    name = value["projectName"]
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        _invalid("CSV import.projectName", "expected a nonempty name of at most 120 characters")
    files = value["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= len(TABLES):
        _invalid("CSV import.files", "expected 1–4 named files")
    tables: dict[str, list[dict[str, str]]] = {}
    for index, source in enumerate(files):
        where = f"CSV import.files[{index}]"
        if not isinstance(source, dict) or set(source) != {"name", "text"}:
            _invalid(where, "expected exactly name and text")
        filename = source["name"]
        if not isinstance(filename, str) or filename not in TABLES:
            _invalid(where, f"unsupported filename {filename!r}; expected {', '.join(TABLES)}")
        if filename in tables:
            _invalid(where, f"duplicate file {filename!r}")
        tables[filename] = _read_table(filename, source["text"])
    if "Devices.csv" not in tables:
        _invalid("CSV import.files", "Devices.csv is required")
    # A present but empty file is valid only for optional tables, e.g. no links.
    devices = tables["Devices.csv"]
    interfaces = tables.get("Interfaces.csv", [])
    links = tables.get("Links.csv", [])
    zones = tables.get("Zones.csv", [])
    if not devices:
        _invalid("Devices.csv", "at least one documented device is required")

    project = {"schemaVersion": "1.0", "name": name, "zones": [], "nodes": [], "links": []}
    for row in zones:
        project["zones"].append({"id": row["id"], "label": row["label"]})
    index: dict[str, dict] = {}
    for row in devices:
        identity = row["id"]
        if identity in index:
            _invalid("Devices.csv", f"duplicate node ID {identity!r}")
        node = {"id": identity, "label": row["label"], "kind": row["kind"],
                "x": _coordinate(row["x"], f"Devices.csv {identity}.x"),
                "y": _coordinate(row["y"], f"Devices.csv {identity}.y"),
                "zoneId": row["zoneId"] or None, "ports": []}
        index[identity] = node
        project["nodes"].append(node)
    for row in interfaces:
        identity = row["nodeId"]
        if identity not in index:
            _invalid("Interfaces.csv", f"undeclared device {identity!r}")
        index[identity]["ports"].append({
            "id": row["id"], "name": row["name"],
            "enabled": _boolean(row["enabled"], f"Interfaces.csv {identity}/{row['id']}.enabled"),
            "ipv4": row["ipv4"] or None,
        })
    for row in links:
        project["links"].append({
            "id": row["id"], "a": {"node": row["aNode"], "port": row["aPort"]},
            "b": {"node": row["bNode"], "port": row["bPort"]},
            "enabled": _boolean(row["enabled"], f"Links.csv {row['id']}.enabled"),
        })
    return validate_project(project)
