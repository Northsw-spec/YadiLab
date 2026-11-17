"""Lossless, read-only canonical project interchange to XLSX and ODS.

Uses the same physical writers as the downloadable demo templates and the
same real importers for a final roundtrip check. No inferred network facts.
"""
from __future__ import annotations

import base64
import re

from .csv_import import TABLES
from .model import ProjectValidationError, validate_project
from .spreadsheet_schema import V13
from .spreadsheet_templates import _xlsx, _ods

_ILLEGAL_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\r]")


def _fail(where: str, reason: str) -> None:
    raise ProjectValidationError(f"spreadsheet export {where}: {reason}")


def _text(value: str, where: str) -> str:
    if _ILLEGAL_XML.search(value):
        _fail(where, "XML-unsupported control character; export rejected rather than losing data")
    return value


def _name(value: str | None) -> str:
    return "" if value is None else value


def _serialize(project: dict) -> tuple[dict[str, list[tuple[str, ...]]],
                                         dict[str, tuple[str, ...]]]:
    version = project["schemaVersion"]
    if version not in ("1.0", "1.3"):
        _fail("schemaVersion", f"schema {version} is not in the explicit workbook contract (1.0/1.3); no automatic migration")
    contract = V13 if version == "1.3" else TABLES
    rows: dict[str, list[tuple[str, ...]]] = {}
    if version == "1.3":
        rows["Project"] = [("1.3",)]
    rows["Devices"] = []
    rows["Interfaces"] = []
    rows["Links"] = []
    rows["Zones"] = []
    if version == "1.3":
        rows["StaticRoutes"] = []

    for ni, node in enumerate(project["nodes"]):
        where = f"nodes[{ni}]"
        rows["Devices"].append((
            node["id"], node["label"], node["kind"], str(node["x"]), str(node["y"]),
            _name(node["zoneId"]),
        ))
        for pi, port in enumerate(node["ports"]):
            loc = f"{where}.ports[{pi}]"
            base = (node["id"], port["id"], port["name"],
                    "true" if port["enabled"] else "false", _name(port["ipv4"]))
            if version == "1.0":
                rows["Interfaces"].append(base)
                continue
            # The current 1.3 workbook has no presence bit; blank means
            # absent, *not* explicitly present null. Reject ambiguous fields.
            if ("mac" in port and port["mac"] is None) or (
                    "vlan" in port and port["vlan"] is None):
                _fail(loc, "explicit null optional MAC/VLAN cannot be represented; remove the null field explicitly before exporting")
            mac = port.get("mac", "")
            vlan = port.get("vlan")
            if vlan is None:
                mode, access, allowed = "", "", ""
            elif vlan["mode"] == "access":
                mode, access, allowed = "access", str(vlan["vlan"]), ""
            else:
                mode, access, allowed = (
                    "trunk", "", "|".join(map(str, vlan["allowedVlans"])))
            rows["Interfaces"].append(base + (mac, mode, access, allowed))
        if version == "1.3":
            if "staticRoutes" in node and not node["staticRoutes"]:
                _fail(where, "explicit empty staticRoutes cannot be represented; remove the empty property explicitly before exporting")
            for route in node.get("staticRoutes", []):
                rows["StaticRoutes"].append((
                    node["id"], route["id"], route["destination"],
                    route["nextHop"], route["outPort"],
                ))

    for link in project["links"]:
        rows["Links"].append((
            link["id"], link["a"]["node"], link["a"]["port"],
            link["b"]["node"], link["b"]["port"],
            "true" if link["enabled"] else "false",
        ))
    for zone in project["zones"]:
        rows["Zones"].append((zone["id"], zone["label"]))

    for sheet, data in rows.items():
        fields = contract[sheet + ".csv"]
        if len(data) > 5000:
            _fail(sheet, "more than 5000 records; source preserved, no workbook created")
        for index, record in enumerate(data, 2):
            if len(record) != len(fields):
                _fail(f"{sheet} row {index}", "not all contract fields could be exported")
            for key, value in zip(fields, record):
                if not isinstance(value, str):
                    _fail(f"{sheet} row {index}.{key}", "non-string workbook value")
                _text(value, f"{sheet} row {index}.{key}")
    return rows, contract


def export_workbook(project: object, extension: str) -> bytes:
    """Return real binary workbook, rejecting any change to canonical semantics."""
    if extension not in ("xlsx", "ods"):
        _fail("format", "expected exactly xlsx or ods")
    canonical = validate_project(project)
    if not canonical["nodes"]:
        _fail("Devices", "workbook import requires at least one declared device")
    rows, contract = _serialize(canonical)
    data = _xlsx(rows, contract) if extension == "xlsx" else _ods(rows, contract)

    # Never deliver a workbook that our actual importer will reject, or one
    # that changes canonical identities/fields. This is a functional check,
    # not a claim about physical reachability or Excel's presentation.
    from .xlsx_import import import_xlsx_workbook
    from .ods_import import import_ods_workbook
    payload = {
        "filename": "export." + extension,
        "projectName": canonical["name"],
        "contentBase64": base64.b64encode(data).decode("ascii"),
    }
    restored = (import_xlsx_workbook(payload) if extension == "xlsx"
                else import_ods_workbook(payload))
    if restored != canonical:
        _fail("roundtrip", "workbook cannot preserve the exact canonical data; original project unchanged")
    return data
