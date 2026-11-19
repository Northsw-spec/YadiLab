"""Read-only, source-faithful inspection of external tabular documentation.

CSV and bounded workbook readers share one literal, non-semantic result.
No source cell is converted into a network object or written to disk.
"""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io

from .model import ProjectValidationError

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5001
MAX_COLUMNS = 256
MAX_CELLS = 100000
PREVIEW_ROWS = 25


def _invalid(location: str, reason: str) -> None:
    raise ProjectValidationError(f"import inspect {location}: {reason}")


def _column_name(index: int) -> str:
    """Convert a one-based column index to A..IV sheet notation."""
    label = ""
    while index:
        index, digit = divmod(index - 1, 26)
        label = chr(65 + digit) + label
    return label


def _decode_source(value: object) -> tuple[str, str, bytes, str | None]:
    if not isinstance(value, dict):
        _invalid("request", "expected an object")
    filename = value.get("filename")
    encoded = value.get("contentBase64")
    if (not isinstance(filename, str) or not filename
            or "/" in filename or "\\" in filename or "\x00" in filename):
        _invalid("filename", "expected a single filename without a path")
    if len(filename) > 255 or filename in (".", ".."):
        _invalid("filename", "invalid filename")
    extension = filename.rpartition(".")[2].lower()
    if extension not in ("csv", "xlsx", "ods"):
        _invalid("filename", "expected .csv, .xlsx or .ods")
    expected = {"filename", "contentBase64"} | ({"csvDelimiter"} if extension == "csv" else set())
    if set(value) != expected:
        _invalid("request", "unexpected or missing fields for source type")
    delimiter = value.get("csvDelimiter")
    if extension == "csv" and (not isinstance(delimiter, str) or delimiter not in (",", ";")):
        _invalid("csvDelimiter", "choose comma or semicolon explicitly")
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_SOURCE_BYTES + 2) // 3):
        _invalid("contentBase64", "invalid or oversized base64")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        _invalid("contentBase64", "invalid base64")
    if len(data) > MAX_SOURCE_BYTES:
        _invalid("contentBase64", "source file exceeds 5 MiB")
    return filename, extension, data, delimiter


def _csv_table(filename: str, data: bytes, delimiter: str) -> dict:
    try:
        content = data.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        _invalid(filename, "invalid UTF-8")
    if "\x00" in content:
        _invalid(filename, "NUL bytes are not supported")

    reader = csv.reader(io.StringIO(content, newline=""), delimiter=delimiter, strict=True)
    row_count = 0
    first_width: int | None = None
    populated = 0
    cell_count = 0
    preview = []
    try:
        for record in reader:
            row_count += 1
            if row_count > MAX_ROWS:
                _invalid(filename, f"more than {MAX_ROWS} logical CSV records")
            if len(record) > MAX_COLUMNS:
                _invalid(f"{filename} row {row_count}", "more than 256 columns")
            if record and first_width is None:
                first_width = len(record)
            elif record and len(record) != first_width:
                _invalid(f"{filename} row {row_count}",
                         f"inconsistent column count: expected {first_width}, got {len(record)}")
            cells = []
            for column, raw in enumerate(record, start=1):
                if raw == "":
                    continue
                cell_count += 1
                if cell_count > MAX_CELLS:
                    _invalid(filename, f"more than {MAX_CELLS} populated cells")
                if len(preview) < PREVIEW_ROWS:
                    cells.append({"address": f"{_column_name(column)}{row_count}",
                                  "type": "text", "value": raw})
            if cells or any(record):
                populated += 1
                if len(preview) < PREVIEW_ROWS:
                    preview.append({"row": row_count, "cells": cells})
    except csv.Error as error:
        _invalid(f"{filename} CSV logical record {row_count + 1}", f"malformed quoting: {error}")
    return {"tableId": "sheet-1", "name": filename, "rowCount": row_count,
            "populatedRowCount": populated, "columnCount": first_width or 0,
            "previewRows": preview}


def inspect_source(value: object) -> dict:
    """Inspect only; never change the current project or saved files."""
    filename, kind, data, delimiter = _decode_source(value)
    if kind == "csv":
        tables = [_csv_table(filename, data, delimiter)]
    else:
        from .import_workbooks import xlsx, ods
        tables = (xlsx if kind == "xlsx" else ods)(data)
    return {"inspectionVersion": "1",
            "source": {"filename": filename, "kind": kind,
                       "sha256": hashlib.sha256(data).hexdigest()},
            "tables": tables,
            "previewRowLimit": PREVIEW_ROWS}
