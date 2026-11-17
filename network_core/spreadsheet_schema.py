"""Single versioned table contract shared by strict XLSX and ODS readers.

Unversioned four-sheet documents retain schema 1.0. An explicit Project
sheet opts into schema 1.3 with full MAC/VLAN/static-route facts. Both paths
reuse the existing CSV parser and canonical project validator.
"""
from __future__ import annotations

import csv
import io
from collections.abc import Collection

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
    document = import_csv_tables({"projectName": value["projectName"], "files": legacy_files})
    document["schemaVersion"] = "1.3"
    nodes = {node["id"]: node for node in document["nodes"]}
    ports = {(node["id"], port["id"]): port for node in document["nodes"] for port in node["ports"]}

    for row in rows.get("Interfaces.csv", []):
        key = (row["nodeId"], row["id"])
        port = ports[key]  # validated by the canonical legacy CSV importer
        where = f"Interfaces.csv {key[0]}/{key[1]}"
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
            port["vlan"] = {"mode": "access", "vlan": _decimal(access, where + ".accessVlan")}
        elif mode == "trunk":
            if access or not allowed:
                _invalid(where, "trunk requires allowedVlans and no accessVlan")
            port["vlan"] = {
                "mode": "trunk",
                "allowedVlans": [_decimal(part, where + ".allowedVlans")
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
    return validate_project(document)
