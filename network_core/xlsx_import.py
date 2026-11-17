"""Strict, bounded OOXML/XLSX four-sheet import into the existing CSV contract.

The first supported workbook format has explicitly named simple data sheets
(Devices, Interfaces, Links, optional Zones) and exactly the CSV columns.
Unsupported workbook content is rejected instead of losing configuration.
No guessing of cables, MAC, VLANs, routes, hidden values or formulas.
"""
from __future__ import annotations

import base64
import binascii
import csv
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

from .spreadsheet_schema import KNOWN_SHEETS, columns_for_sheets, import_spreadsheet_tables
from .model import ProjectValidationError

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
WORKSHEET_REL = DOC_REL + "/worksheet"
MAX_XLSX_BYTES = 5 * 1024 * 1024
MAX_UNCOMPRESSED = 12 * 1024 * 1024
MAX_XML = 5 * 1024 * 1024
MAX_ROWS = 5001
SHEETS = {name: name + ".csv" for name in KNOWN_SHEETS}
COLREF = re.compile(r"([A-Z]{1,3})([1-9][0-9]*)\Z")
DATA_NAMES = {"x", "y", "enabled"}


def _fail(where: str, reason: str):
    raise ProjectValidationError(f"XLSX {where}: {reason}")


def _xml(archive: zipfile.ZipFile, part: str) -> ET.Element:
    try:
        raw = archive.read(part)
    except KeyError:
        _fail(part, "required OOXML part missing")
    if len(raw) > MAX_XML or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        _fail(part, "unsupported or oversized XML")
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        _fail(part, "malformed XML")


def _index(reference: str, row: int, where: str) -> int:
    match = COLREF.fullmatch(reference)
    if match is None or int(match.group(2)) != row:
        _fail(where, f"invalid or out-of-row cell coordinate {reference!r}")
    column = 0
    for letter in match.group(1):
        column = 26 * column + ord(letter) - 64
    return column - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _xml(archive, "xl/sharedStrings.xml")
    if root.tag != f"{{{NS}}}sst":
        _fail("sharedStrings", "invalid OOXML shared-string root")
    items = []
    for item in root:
        if item.tag != f"{{{NS}}}si" or len(item) != 1 or item[0].tag != f"{{{NS}}}t":
            _fail("sharedStrings", "rich text/phonetics or unsupported shared-string data")
        if len(item[0]):
            _fail("sharedStrings", "nested text unsupported")
        items.append(item[0].text or "")
        if len(items) > 100000:
            _fail("sharedStrings", "too many entries")
    return items


def _cell(cell: ET.Element, shared: list[str], where: str, field: str) -> str:
    if any(tag.tag not in {f"{{{NS}}}v", f"{{{NS}}}is"} for tag in cell):
        _fail(where, "formulas and unsupported cell content are forbidden")
    if len(cell) > 1:
        _fail(where, "multiple value elements")
    kind = cell.get("t", "n")
    value = cell.find(f"{{{NS}}}v")
    inline = cell.find(f"{{{NS}}}is")
    if kind == "inlineStr":
        if inline is None or value is not None or len(inline) != 1 or inline[0].tag != f"{{{NS}}}t":
            _fail(where, "inline string must contain one plain text element")
        if len(inline[0]):
            _fail(where, "nested inline text unsupported")
        return inline[0].text or ""
    if inline is not None:
        _fail(where, "unexpected inline text")
    if value is None or value.text is None:
        if len(cell) == 0:
            return ""
        _fail(where, "empty typed cell")
    raw = value.text
    if kind == "s":
        if not raw.isascii() or not raw.isdecimal():
            _fail(where, "invalid shared-string index")
        index = int(raw)
        if index >= len(shared):
            _fail(where, "missing shared-string reference")
        return shared[index]
    if kind == "b":
        if field != "enabled" or raw not in ("0", "1"):
            _fail(where, "boolean cell only supported for enabled")
        return "true" if raw == "1" else "false"
    if kind == "n":
        if field not in ("x", "y"):
            _fail(where, "numeric cells only supported for x/y; identifiers must be text")
        return raw
    _fail(where, f"cell type {kind!r} unsupported (including cached formulas/errors)")


def _table(archive: zipfile.ZipFile, part: str, name: str,
           shared: list[str], columns: tuple[str, ...]) -> str:
    root = _xml(archive, part)
    if root.tag != f"{{{NS}}}worksheet":
        _fail(name, "invalid worksheet root")
    data = root.find(f"{{{NS}}}sheetData")
    if data is None:
        _fail(name, "missing sheetData")
    allowed = {f"{{{NS}}}{tag}" for tag in (
        "dimension", "sheetViews", "sheetFormatPr", "cols", "sheetData", "pageMargins",
        "printOptions", "pageSetup", "headerFooter")}
    if any(tag.tag not in allowed for tag in root):
        _fail(name, "unsupported worksheet content (merged cells, tables, drawings, or other data)")
    for col in root.findall(f"{{{NS}}}cols/{{{NS}}}col"):
        if col.get("hidden") in ("true", "1"):
            _fail(name, "hidden columns not importable")
    rows = []
    expected_row = 1
    for item in data:
        if item.tag != f"{{{NS}}}row":
            _fail(name, "unsupported worksheet row content")
        raw_row = item.get("r")
        if raw_row is None or not raw_row.isascii() or not raw_row.isdecimal() or int(raw_row) != expected_row:
            _fail(name, "rows must be consecutive from row 1")
        if item.get("hidden") in ("1", "true"):
            _fail(name, f"hidden row {expected_row} not importable")
        if expected_row > MAX_ROWS:
            _fail(name, "too many rows")
        fields = {}
        for cell in item:
            if cell.tag != f"{{{NS}}}c":
                _fail(name, "unsupported row content")
            ref = cell.get("r")
            if not ref:
                _fail(name, "cell missing explicit reference")
            col = _index(ref, expected_row, name)
            if col >= len(columns) or col in fields:
                _fail(name, f"duplicate/out-of-range column {ref}")
            # Column meaning is determined by the first, literal header row.
            field = rows[0][col] if rows and col < len(rows[0]) else "header"
            fields[col] = _cell(cell, shared, f"{name}!{ref}", field)
        if not fields:
            _fail(name, f"empty formatted row {expected_row} is not a record")
        rows.append([fields.get(i, "") for i in range(len(columns))])
        expected_row += 1
    if not rows:
        _fail(name, "missing header row")
    header = rows[0]
    if len(set(header)) != len(header) or set(header) != set(columns):
        _fail(f"{name}!1 (header)", "expected exactly the named columns (any order)")
    # Type-check data against the actual header's column order, independent
    # of cell XML formatting and implicit empty cells.
    # Numeric/bool verification above uses header[row 1]; for header itself
    # a numeric value was already refused.
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue()


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    root = _xml(archive, part)
    if root.tag != f"{{{PKG_REL}}}Relationships":
        _fail(part, "invalid package relationships root")
    result = {}
    for link in root:
        if link.tag != f"{{{PKG_REL}}}Relationship":
            _fail(part, "unexpected relationship child")
        rid, target, kind = link.get("Id"), link.get("Target"), link.get("Type")
        if not rid or not target or not kind or rid in result:
            _fail(part, "missing or duplicate relationship")
        if link.get("TargetMode") is not None:
            _fail(part, "external relationship unsupported")
        result[rid] = (target, kind)
    return result


def _workbook_sheets(archive: zipfile.ZipFile) -> dict[str, str]:
    root = _xml(archive, "xl/workbook.xml")
    if root.tag != f"{{{NS}}}workbook":
        _fail("workbook", "invalid workbook root")
    if root.find(f"{{{NS}}}externalReferences") is not None or root.find(f"{{{NS}}}definedNames") is not None:
        _fail("workbook", "external links/defined names unsupported")
    sheets = root.find(f"{{{NS}}}sheets")
    if sheets is None:
        _fail("workbook", "no worksheets")
    rels = _relationships(archive, "xl/_rels/workbook.xml.rels")
    found = {}
    for sheet in sheets:
        if sheet.tag != f"{{{NS}}}sheet":
            _fail("workbook", "unexpected worksheet declaration")
        name, rid = sheet.get("name"), sheet.get(f"{{{DOC_REL}}}id")
        if name not in SHEETS or name in found:
            _fail("workbook", f"unknown or duplicate sheet {name!r}")
        if sheet.get("state", "visible") != "visible":
            _fail(name, "hidden worksheet unsupported")
        if rid not in rels:
            _fail(name, "missing relationship")
        target, kind = rels[rid]
        if kind != WORKSHEET_REL or target.startswith(("http:", "https:", "../")):
            _fail(name, "not a local worksheet relationship")
        if target.startswith("/xl/"):
            resolved = target[1:]
        else:
            resolved = posixpath.normpath(posixpath.join("xl", target))
        if not resolved.startswith("xl/worksheets/") or not resolved.endswith(".xml"):
            _fail(name, "invalid worksheet target")
        if resolved not in archive.namelist() or resolved in found.values():
            _fail(name, "missing or duplicate worksheet data part")
        found[name] = resolved
    if "Devices" not in found:
        _fail("workbook", "Devices sheet required")
    return found


def import_xlsx_workbook(value: object) -> dict:
    """Return a validated legacy schema-1.0 or explicit schema-1.3 project."""
    if not isinstance(value, dict) or set(value) != {"filename", "projectName", "contentBase64"}:
        _fail("request", "expected exactly filename, projectName and contentBase64")
    filename, name, encoded = (value[k] for k in ("filename", "projectName", "contentBase64"))
    if not isinstance(filename, str) or not filename.lower().endswith(".xlsx") or "/" in filename or "\\" in filename:
        _fail("request", "expected a single .xlsx filename")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        _fail("request", "projectName must be a nonempty string of at most 120 characters")
    if not isinstance(encoded, str) or len(encoded) > (MAX_XLSX_BYTES * 4 // 3 + 8):
        _fail("request", "invalid or oversized base64 content")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        _fail("request", "invalid base64")
    if not data or len(data) > MAX_XLSX_BYTES:
        _fail("request", "invalid or oversized XLSX file")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if not 1 <= len(entries) <= 24:
                _fail("archive", "unexpected part count")
            names = [info.filename for info in entries]
            if len(set(names)) != len(names):
                _fail("archive", "duplicate ZIP parts")
            total = 0
            for info in entries:
                if info.is_dir() or info.file_size > MAX_XML or info.flag_bits & 1:
                    _fail("archive", "directories, encrypted or oversized parts unsupported")
                total += info.file_size
                if total > MAX_UNCOMPRESSED:
                    _fail("archive", "uncompressed size limit exceeded")
                if info.compress_size and info.file_size > info.compress_size * 1500:
                    _fail("archive", "extreme compression ratio")
            sheets = _workbook_sheets(archive)
            allowed = {
                "[Content_Types].xml", "_rels/.rels", "xl/workbook.xml",
                "xl/_rels/workbook.xml.rels", "xl/sharedStrings.xml",
                "xl/styles.xml", "xl/theme/theme1.xml",
                "docProps/core.xml", "docProps/app.xml",
            } | set(sheets.values())
            if not {"[Content_Types].xml", "_rels/.rels"}.issubset(names):
                _fail("archive", "missing OOXML package metadata")
            extra = set(names) - allowed
            if extra:
                _fail("archive", f"unsupported workbook parts: {', '.join(sorted(extra))}")
            _relationships(archive, "_rels/.rels")  # reject external package links
            shared = _shared_strings(archive)
            schema_columns = columns_for_sheets(sheets.keys())
            sources = [
                {"name": SHEETS[name], "text": _table(archive, part, name, shared,
                                                       schema_columns[name])}
                for name, part in sheets.items()
            ]
    except (zipfile.BadZipFile, EOFError, OSError):
        _fail("archive", "invalid XLSX ZIP structure")
    return import_spreadsheet_tables({"projectName": name, "files": sources})
