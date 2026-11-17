"""Strict, bounded OpenDocument Spreadsheet import through the existing CSV schema.

Only four explicitly named tables with the exact schema-1.0 CSV headers are
accepted. No invented ports, cables, rich spreadsheet semantics or autosave.
"""
from __future__ import annotations

import base64
import binascii
import csv
import io
import zipfile
import xml.etree.ElementTree as ET

from .spreadsheet_schema import KNOWN_SHEETS, columns_for_sheets, import_spreadsheet_tables
from .model import ProjectValidationError

OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
MANIFEST = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
MIMETYPE = b"application/vnd.oasis.opendocument.spreadsheet"
SHEETS = {n: n + ".csv" for n in KNOWN_SHEETS}
MAX_BYTES = 5 * 1024 * 1024
MAX_XML = 5 * 1024 * 1024
MAX_EXPANDED = 12 * 1024 * 1024
MAX_ROWS = 5001


def _q(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def _fail(where: str, reason: str):
    raise ProjectValidationError(f"ODS {where}: {reason}")


def _xml(archive: zipfile.ZipFile, path: str) -> ET.Element:
    try:
        data = archive.read(path)
    except KeyError:
        _fail(path, "required package part missing")
    if len(data) > MAX_XML or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        _fail(path, "unsupported or oversized XML")
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        _fail(path, "malformed XML")


def _count(element: ET.Element, attr: str, where: str, limit: int) -> int:
    raw = element.get(_q(TABLE, attr))
    if raw is None:
        return 1
    if not raw.isascii() or not raw.isdecimal():
        _fail(where, f"invalid {attr}")
    count = int(raw)
    if not 1 <= count <= limit:
        _fail(where, f"{attr} outside 1..{limit}")
    return count


def _text(paragraph: ET.Element, where: str) -> str:
    if paragraph.tag != _q(TEXT, "p") or paragraph.attrib:
        _fail(where, "only plain text paragraphs supported")
    result = [paragraph.text or ""]
    for child in paragraph:
        if child.tag == _q(TEXT, "line-break") and not child.attrib and not len(child):
            result.append("\n")
        elif child.tag == _q(TEXT, "tab") and not child.attrib and not len(child):
            result.append("\t")
        elif child.tag == _q(TEXT, "s") and not len(child):
            raw = child.get(_q(TEXT, "c"), "1")
            if not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= 1000:
                _fail(where, "invalid repeated spaces")
            if set(child.attrib) - {_q(TEXT, "c")}:
                _fail(where, "unsupported styled spaces")
            result.append(" " * int(raw))
        else:
            _fail(where, "rich text, links and embedded content unsupported")
        result.append(child.tail or "")
    text = "".join(result)
    if len(text) > 10000:
        _fail(where, "cell text too large")
    return text


def _cell(cell: ET.Element, where: str, field: str) -> tuple[str, int]:
    if cell.tag != _q(TABLE, "table-cell"):
        _fail(where, "covered/merged cells or unsupported cell elements")
    repeated = _count(cell, "number-columns-repeated", where, 1048576)
    attrs = set(cell.attrib) - {
        _q(OFFICE, "value-type"), _q(OFFICE, "value"), _q(OFFICE, "boolean-value"),
        _q(OFFICE, "string-value"), _q(TABLE, "style-name"),
        _q(TABLE, "number-columns-repeated"),
    }
    if attrs:
        _fail(where, "formula, annotation or unsupported cell attributes")
    for child in cell:
        if child.tag != _q(TEXT, "p"):
            _fail(where, "formula/object/unsupported cell content")
    displayed = "\n".join(_text(p, where) for p in cell)
    kind = cell.get(_q(OFFICE, "value-type"))
    if kind is None:
        if displayed or cell.get(_q(OFFICE, "value")) is not None:
            _fail(where, "untyped cell with data")
        return "", repeated
    if kind == "string":
        if cell.get(_q(OFFICE, "value")) is not None or cell.get(_q(OFFICE, "boolean-value")) is not None:
            _fail(where, "unexpected numeric/boolean attribute on text")
        value = cell.get(_q(OFFICE, "string-value"))
        if value is not None and value != displayed:
            _fail(where, "displayed and declared text differ")
        return displayed, repeated
    if kind == "float":
        if field not in ("x", "y"):
            _fail(where, "numeric cells only supported for x/y; IDs and headers must be text")
        value = cell.get(_q(OFFICE, "value"))
        if value is None or cell.get(_q(OFFICE, "boolean-value")) is not None:
            _fail(where, "missing numeric value")
        # Display formatting that differs from the machine number is not
        # silently used. The canonical CSV importer validates finite numbers.
        if displayed and displayed != value:
            _fail(where, "formatted numeric display differs from source value")
        return value, repeated
    if kind == "boolean":
        if field != "enabled":
            _fail(where, "boolean cells only supported for enabled")
        bit = cell.get(_q(OFFICE, "boolean-value"))
        if bit not in ("true", "false"):
            _fail(where, "invalid boolean-value")
        if displayed and displayed.lower() != bit:
            _fail(where, "boolean displayed text differs from value")
        return bit, repeated
    _fail(where, f"unsupported value-type {kind!r}, including dates and errors")


def _column_label(index: int) -> str:
    letters = ""
    while index:
        index, digit = divmod(index - 1, 26)
        letters = chr(65 + digit) + letters
    return letters


def _row(row: ET.Element, name: str, row_index: int, header: list[str] | None,
         columns: tuple[str, ...]) -> tuple[list[str], int]:
    where = f"{name} row {row_index}"
    if row.tag != _q(TABLE, "table-row"):
        _fail(where, "unsupported table row or group")
    if row.get(_q(TABLE, "visibility"), "visible") != "visible":
        _fail(where, "hidden/filtered rows unsupported")
    if set(row.attrib) - {
        _q(TABLE, "number-rows-repeated"), _q(TABLE, "style-name"),
        _q(TABLE, "visibility"), _q(TABLE, "default-cell-style-name"),
    }:
        _fail(where, "unsupported row attributes")
    times = _count(row, "number-rows-repeated", where, 1048576)
    width = len(columns)
    values: list[str] = []
    for cell in row:
        field = (header[len(values)] if header is not None and len(values) < width else "header")
        value, repeat = _cell(cell, f"{name}!{_column_label(len(values) + 1)}{row_index}", field)
        if repeat > 1 and value:
            _fail(where, "repeated nonempty cell not supported")
        if len(values) >= width:
            if value:
                _fail(where, "nonempty cell beyond declared columns")
            continue
        if len(values) + repeat > width:
            if value:
                _fail(where, "nonempty repeated cell exceeds defined columns")
            values.extend([""] * (width-len(values)))
        else:
            values.extend([value] * repeat)
    values.extend([""] * (width-len(values)))
    if times > 1 and any(values):
        _fail(where, "repeated populated rows not supported")
    return values, times


def _sheet(sheet: ET.Element, name: str, columns: tuple[str, ...]) -> str:
    where = f"sheet {name}"
    if sheet.get(_q(TABLE, "visibility"), "visible") != "visible":
        _fail(where, "hidden spreadsheet unsupported")
    if set(sheet.attrib) - {
        _q(TABLE, "name"), _q(TABLE, "style-name"), _q(TABLE, "visibility"),
    }:
        _fail(where, "unexpected sheet attributes")
    width = len(columns)
    rows: list[list[str]] = []
    trailing_padding = False
    row_index = 1
    for child in sheet:
        if child.tag == _q(TABLE, "table-column"):
            if child.get(_q(TABLE, "visibility"), "visible") != "visible":
                _fail(where, "hidden columns unsupported")
            if set(child.attrib) - {
                _q(TABLE, "number-columns-repeated"), _q(TABLE, "style-name"),
                _q(TABLE, "default-cell-style-name"), _q(TABLE, "visibility"),
            }:
                _fail(where, "unsupported column properties")
            _count(child, "number-columns-repeated", where, 1048576)
            if rows:
                _fail(where, "column after data row")
            continue
        if child.tag != _q(TABLE, "table-row"):
            _fail(where, "merged cells, table groups, database ranges or other data unsupported")
        values, times = _row(child, name, row_index, rows[0] if rows else None, columns)
        row_index += times
        if row_index > 1048577:
            _fail(where, "too many physical sheet rows")
        if not any(values):
            # ODF writers sometimes use repeated empty rows as trailing
            # padding. It contains no data, so permit it only at the end.
            if not rows:
                _fail(where, "missing header")
            trailing_padding = True
            continue
        if trailing_padding:
            _fail(where, "nonempty row after empty/repeated padding")
        if len(rows) >= MAX_ROWS:
            _fail(where, "more than 5000 data rows")
        rows.append(values)
    if not rows:
        _fail(where, "missing header")
    if len(set(rows[0])) != width or set(rows[0]) != set(columns):
        _fail(f"{name}!1 (header)", "expected exactly the named columns (any order)")
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue()


def _manifest(archive: zipfile.ZipFile, present: set[str]) -> None:
    root = _xml(archive, "META-INF/manifest.xml")
    if root.tag != _q(MANIFEST, "manifest"):
        _fail("manifest", "invalid manifest root")
    listed: set[str] = set()
    for element in root:
        if element.tag != _q(MANIFEST, "file-entry") or len(element):
            _fail("manifest", "encrypted/unsupported file-entry")
        path, kind = element.get(_q(MANIFEST, "full-path")), element.get(_q(MANIFEST, "media-type"))
        if not isinstance(path, str) or kind is None or path in listed:
            _fail("manifest", "invalid/duplicate manifest entry")
        if path not in (present | {"/"}):
            _fail("manifest", "manifest references unsupported package data")
        if path == "/" and kind != MIMETYPE.decode("ascii"):
            _fail("manifest", "spreadsheet MIME mismatch")
        listed.add(path)
    if not {"/", "content.xml"}.issubset(listed):
        _fail("manifest", "missing root/content file-entry")


def import_ods_workbook(value: object) -> dict:
    """Validate a real ODS ZIP and import legacy 1.0 or explicit 1.3."""
    if not isinstance(value, dict) or set(value) != {"filename", "projectName", "contentBase64"}:
        _fail("request", "expected exactly filename, projectName and contentBase64")
    filename, name, encoded = (value[k] for k in ("filename", "projectName", "contentBase64"))
    if not isinstance(filename, str) or not filename.lower().endswith(".ods") or "/" in filename or "\\" in filename:
        _fail("request", "expected one .ods filename")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        _fail("request", "projectName must be a nonempty string of at most 120 characters")
    if not isinstance(encoded, str) or len(encoded) > MAX_BYTES * 4 // 3 + 8:
        _fail("request", "invalid/oversized base64 content")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        _fail("request", "invalid base64")
    if not raw or len(raw) > MAX_BYTES:
        _fail("request", "invalid/oversized ODS")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not 3 <= len(entries) <= 10:
                _fail("archive", "unsupported ODS package part count")
            names = [item.filename for item in entries]
            if len(set(names)) != len(names):
                _fail("archive", "duplicate ZIP parts")
            if names[0] != "mimetype" or entries[0].compress_type != zipfile.ZIP_STORED:
                _fail("archive", "ODF mimetype must be the first uncompressed ZIP member")
            permitted = {
                "mimetype", "content.xml", "META-INF/manifest.xml",
                "styles.xml", "meta.xml", "settings.xml",
            }
            extra = set(names) - permitted
            if extra:
                _fail("archive", f"unsupported package parts: {', '.join(sorted(extra))}")
            if not {"mimetype", "content.xml", "META-INF/manifest.xml"}.issubset(names):
                _fail("archive", "missing required ODF parts")
            if archive.read("mimetype") != MIMETYPE:
                _fail("archive", "not an OpenDocument spreadsheet")
            expanded = 0
            for entry in entries:
                if entry.is_dir() or entry.flag_bits & 1 or entry.file_size > MAX_XML:
                    _fail("archive", "directory/encryption/oversized package part")
                expanded += entry.file_size
                if expanded > MAX_EXPANDED:
                    _fail("archive", "uncompressed package limit exceeded")
                if entry.compress_size and entry.file_size > entry.compress_size * 1500:
                    _fail("archive", "extreme ZIP compression ratio")
            _manifest(archive, set(names))
            root = _xml(archive, "content.xml")
            if root.tag != _q(OFFICE, "document-content"):
                _fail("content", "invalid document root")
            if any(child.tag not in {
                _q(OFFICE, "font-face-decls"), _q(OFFICE, "automatic-styles"), _q(OFFICE, "body"),
            } for child in root):
                _fail("content", "scripts, events and unsupported document features")
            body = root.find(_q(OFFICE, "body"))
            if body is None or len(body) != 1 or body[0].tag != _q(OFFICE, "spreadsheet"):
                _fail("content", "missing spreadsheet body")
            tables = list(body[0])
            names = []
            for table in tables:
                if table.tag != _q(TABLE, "table"):
                    _fail("content", "named ranges or unsupported spreadsheet objects")
                name_of_sheet = table.get(_q(TABLE, "name"))
                if name_of_sheet not in SHEETS or name_of_sheet in names:
                    _fail("content", f"unknown/duplicate sheet {name_of_sheet!r}")
                names.append(name_of_sheet)
            schema_columns = columns_for_sheets(names)
            found: dict[str, str] = {}
            for table, name_of_sheet in zip(tables, names):
                found[name_of_sheet] = _sheet(table, name_of_sheet,
                                               schema_columns[name_of_sheet])
    except (zipfile.BadZipFile, EOFError, OSError):
        _fail("archive", "invalid ODS ZIP")
    sources = [{"name": SHEETS[sheet], "text": text} for sheet, text in found.items()]
    return import_spreadsheet_tables({"projectName": name, "files": sources})
