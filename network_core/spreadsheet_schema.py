"""Single versioned table contract shared by strict XLSX and ODS readers.

Unversioned four-sheet documents retain schema 1.0. An explicit Project
sheet opts into schema 1.3 with full MAC/VLAN/static-route facts. Both paths
reuse the existing CSV parser and canonical project validator.
"""
from __future__ import annotations

import csv
import io
from collections.abc import Collection
import re

from .csv_import import TABLES, _read_table, _invalid, import_csv_tables
from .model import ProjectValidationError, validate_project

V13 = {
    "Project.csv": ("schemaVersion",),
    "Devices.csv": TABLES["Devices.csv"],
    "Interfaces.csv": ("nodeId", "id", "name", "enabled", "ipv4",
                       "mac", "vlanMode", "accessVlan", "allowedVlans"),
    "Links.csv": TABLES["Links.csv"],
    "Zones.csv": TABLES["Zones.csv"],
    "StaticRoutes.csv": ("nodeId", "id", "destination", "nextHop", "outPort"),
}
KNOWN_SHEETS = frozenset(n[:-4] for n in V13)


def columns_for_sheets(names: Collection[str]) -> dict[str, tuple[str, ...]]:
    if not names or "Devices" not in names:
        _invalid("workbook", "Devices table required")
    unknown = set(names) - KNOWN_SHEETS
    if unknown:
        _invalid("workbook", f"unsupported tables: {', '.join(sorted(unknown))}")
    if "Project" not in names:
        if "StaticRoutes" in names:
            _invalid("workbook", "StaticRoutes requires explicit Project schemaVersion 1.3")
        return {n[:-4]: fields for n, fields in TABLES.items()}
    return {n[:-4]: fields for n, fields in V13.items()}


def _as_csv(rows: list[dict[str, str]], columns: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows([[row[c] for c in columns] for row in rows])
    return output.getvalue()


def _decimal(value: str, where: str) -> int:
    if not value or not value.isascii() or not value.isdecimal():
        _invalid(where, "expected explicit canonical decimal VLAN ID")
    number = int(value)
    if str(number) != value or not 1 <= number <= 4094:
        _invalid(where, "VLAN ID must be a canonical integer 1..4094")
    return number



_CANONICAL_LOCATION = re.compile(
    r"^project\.(nodes|links|zones)\[(\d+)\](?:\.(.*?))?: (.*)$"
)
_PORT_LOCATION = re.compile(r"^ports\[(\d+)\](?:\.(.*))?$")
_ROUTE_LOCATION = re.compile(r"^staticRoutes\[(\d+)\](?:\.(.*))?$")


def _source_ref(rows: dict[str, list[dict[str, str]]], sheet: str,
                index: int, field: str) -> str | None:
    """Actual input cell, using original worksheet header order."""
    data = rows.get(sheet + ".csv", [])
    if not 0 <= index < len(data):
        return None
    names = list(data[index])
    if field not in names:
        return None
    column = names.index(field) + 1
    letters = ""
    while column:
        column, digit = divmod(column - 1, 26)
        letters = chr(65 + digit) + letters
    return f"{sheet}!{letters}{index + 2} ({field})"


def _canonical_source_error(message: str, rows: dict[str, list[dict[str, str]]]) -> str:
    """Only annotate model errors that map unambiguously to a source cell."""
    m = _CANONICAL_LOCATION.fullmatch(message)
    if not m:
        return message
    collection, ordinal, suffix, _reason = m.groups()
    index = int(ordinal)
    ref = None
    if collection == "zones":
        ref = _source_ref(rows, "Zones", index, (suffix or "id").split(".")[0])
    elif collection == "links":
        parts = (suffix or "id").split(".")
        field = parts[0]
        if field in ("a", "b"):
            field += "Port" if len(parts) > 1 and parts[1] == "port" else "Node"
        ref = _source_ref(rows, "Links", index, field)
    else:
        devices = rows.get("Devices.csv", [])
        if index >= len(devices):
            return message
        node_id = devices[index]["id"]
        port_match = _PORT_LOCATION.fullmatch(suffix or "")
        route_match = _ROUTE_LOCATION.fullmatch(suffix or "")
        if port_match:
            port_index = int(port_match.group(1))
            candidates = [i for i, row in enumerate(rows.get("Interfaces.csv", []))
                          if row["nodeId"] == node_id]
            if port_index < len(candidates):
                field = port_match.group(2) or "id"
                if field == "vlan":
                    field = "vlanMode"
                elif field == "vlan.vlan":
                    field = "accessVlan"
                elif field.startswith("vlan.allowedVlans"):
                    field = "allowedVlans"
                else:
                    field = field.split(".")[0]
                ref = _source_ref(rows, "Interfaces", candidates[port_index], field)
        elif route_match:
            route_index = int(route_match.group(1))
            candidates = [i for i, row in enumerate(rows.get("StaticRoutes.csv", []))
                          if row["nodeId"] == node_id]
            if route_index < len(candidates):
                field = (route_match.group(2) or "id").split(".")[0]
                ref = _source_ref(rows, "StaticRoutes", candidates[route_index], field)
        else:
            ref = _source_ref(rows, "Devices", index, (suffix or "id").split(".")[0])
    return f"{ref}: {message}" if ref is not None else message

def import_spreadsheet_tables(value: object) -> dict:
    """Workbook decoded into named CSV-shaped text tables (no I/O/persistence)."""
    if not isinstance(value, dict) or set(value) != {"projectName", "files"}:
        _invalid("workbook", "expected exactly projectName and files")
    files = value["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= len(V13):
        _invalid("workbook", "expected 1..6 named tables")
    seen = set()
    for source in files:
        if not isinstance(source, dict) or set(source) != {"name", "text"}:
            _invalid("workbook", "expected exactly name and text for each table")
        if not isinstance(source["name"], str) or source["name"] in seen:
            _invalid("workbook", "invalid or duplicate table name")
        seen.add(source["name"])
    names = {n[:-4] if n.endswith(".csv") else n for n in seen}
    columns = columns_for_sheets(names)
    if "Project.csv" not in seen:
        return import_csv_tables(value)

    rows = {}
    for source in files:
        filename = source["name"]
        if filename not in V13:
            _invalid("workbook", f"unknown table {filename!r}")
        rows[filename] = _read_table(filename, source["text"], V13[filename])
    version = rows.get("Project.csv")
    if version != [{"schemaVersion": "1.3"}]:
        _invalid("Project!A2 (schemaVersion)", "expected exactly one schemaVersion row with '1.3'")

    # The legacy CSV importer remains the sole authority for devices, ports,
    # links, endpoints, zone IDs and ordinary types. Drop only versioned
    # extension columns that are handled explicitly below.
    legacy_files = []
    for filename in TABLES:
        if filename not in rows:
            continue
        legacy_files.append({
            "name": filename,
            "text": _as_csv(rows[filename], TABLES[filename]),
        })
    try:
        document = import_csv_tables({"projectName": value["projectName"], "files": legacy_files})
    except ProjectValidationError as error:
        raise ProjectValidationError(_canonical_source_error(error.message, rows)) from None
    document["schemaVersion"] = "1.3"
    nodes = {node["id"]: node for node in document["nodes"]}
    ports = {(node["id"], port["id"]): port for node in document["nodes"] for port in node["ports"]}

    for index, row in enumerate(rows.get("Interfaces.csv", [])):
        key = (row["nodeId"], row["id"])
        port = ports[key]  # validated by the canonical legacy CSV importer
        where = _source_ref(rows, "Interfaces", index, "vlanMode") or "Interfaces.csv"
        if row["mac"]:
            port["mac"] = row["mac"]
        mode, access, allowed = row["vlanMode"], row["accessVlan"], row["allowedVlans"]
        if not mode:
            if access or allowed:
                _invalid(where, "VLAN values without explicit vlanMode")
            continue
        if mode == "access":
            if allowed:
                _invalid(where, "access VLAN must not also declare trunk allowedVlans")
            port["vlan"] = {"mode": "access", "vlan": _decimal(access, _source_ref(rows, "Interfaces", index, "accessVlan") or where)}
        elif mode == "trunk":
            if access or not allowed:
                _invalid(where, "trunk requires allowedVlans and no accessVlan")
            port["vlan"] = {
                "mode": "trunk",
                "allowedVlans": [_decimal(part, _source_ref(rows, "Interfaces", index, "allowedVlans") or where)
                                 for part in allowed.split("|")],
            }
        else:
            _invalid(where, "expected blank, access or trunk vlanMode")

    for row in rows.get("StaticRoutes.csv", []):
        where = f"StaticRoutes.csv {row['nodeId']}/{row['id']}"
        node = nodes.get(row["nodeId"])
        if node is None:
            _invalid(where, "unknown source node")
        node.setdefault("staticRoutes", []).append({
            "id": row["id"], "destination": row["destination"],
            "nextHop": row["nextHop"], "outPort": row["outPort"],
        })
    try:
        return validate_project(document)
    except ProjectValidationError as error:
        raise ProjectValidationError(_canonical_source_error(error.message, rows)) from None
