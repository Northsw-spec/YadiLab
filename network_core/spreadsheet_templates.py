"""Downloadable example workbooks for the explicit schema-1.3 interchange.

A labelled demonstration network, never an observed/imported customer network.
Uses the authoritative V13 column contract; ZIP/XML serializers are independent
of the import readers and have no disk side effects or runtime dependencies.
"""
from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape, quoteattr

from .spreadsheet_schema import V13

SHEET_ORDER = ("Project", "Devices", "Interfaces", "Links", "Zones", "StaticRoutes")
SAMPLE = {
    "Project": [("1.3",)],
    "Devices": [
        ("demo-client", "DEMO client", "host", "30", "40", "demo-zone"),
        ("demo-switch-a", "DEMO switch A", "switch", "150", "40", "demo-zone"),
        ("demo-switch-b", "DEMO switch B", "switch", "270", "40", "demo-zone"),
        ("demo-router", "DEMO router", "router", "390", "40", "demo-zone"),
    ],
    "Interfaces": [
        ("demo-client", "eth0", "NIC", "true", "192.0.2.10/24",
         "02:00:00:00:00:0A", "", "", ""),
        ("demo-switch-a", "p1", "Client access", "true", "", "", "access", "10", ""),
        ("demo-switch-a", "p2", "Tagged uplink", "true", "", "", "trunk", "", "10|20"),
        ("demo-switch-b", "p1", "Tagged uplink", "true", "", "", "trunk", "", "10|20"),
        ("demo-switch-b", "p2", "Router access", "true", "", "", "access", "10", ""),
        ("demo-router", "lan", "LAN", "true", "192.0.2.1/24",
         "02:00:00:00:00:0B", "", "", ""),
        ("demo-router", "wan", "Uncabled demo subnet", "true", "203.0.113.1/24",
         "02:00:00:00:00:0C", "", "", ""),
    ],
    "Links": [
        ("demo-link-client", "demo-client", "eth0", "demo-switch-a", "p1", "true"),
        ("demo-link-trunk", "demo-switch-a", "p2", "demo-switch-b", "p1", "true"),
        ("demo-link-router", "demo-switch-b", "p2", "demo-router", "lan", "true"),
    ],
    "Zones": [("demo-zone", "DEMO only - replace with documented facts")],
    "StaticRoutes": [
        ("demo-client", "demo-via-router", "203.0.113.0/24", "192.0.2.1", "eth0"),
    ],
}
MIME_ODS = "application/vnd.oasis.opendocument.spreadsheet"
# ZIP's default writestr(name, ...) inserts the current wall-clock timestamp.
# Fixed metadata makes identical template/export content byte-identical, even
# across the two-second ZIP timestamp boundary or a full process restart.
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _zip_member(archive: zipfile.ZipFile, name: str, content: bytes,
                compression: int = zipfile.ZIP_DEFLATED) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = compression
    info.create_system = 3
    info.external_attr = 0o600 << 16
    archive.writestr(info, content)


ODS_NAMESPACES = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
)


def _cells(sheet: str, records_by_sheet=None, contract=None):
    schema = V13 if contract is None else contract
    source = SAMPLE if records_by_sheet is None else records_by_sheet
    headers = schema[sheet + ".csv"]
    records = source[sheet]
    for record in records:
        if len(record) != len(headers):
            raise ValueError("template row width does not match versioned column contract")
    return [headers, *records]


def _xlsx(records_by_sheet=None, contract=None) -> bytes:
    schema = V13 if contract is None else contract
    sheet_order = SHEET_ORDER if records_by_sheet is None else tuple(records_by_sheet)
    content_overrides = []
    sheet_tags = []
    worksheet_rels = []
    members: dict[str, bytes] = {}
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    for sheet_number, sheet in enumerate(sheet_order, 1):
        sheet_tags.append(
            f'<sheet name={quoteattr(sheet)} sheetId="{sheet_number}" r:id="rId{sheet_number}"/>')
        worksheet_rels.append(
            f'<Relationship Id="rId{sheet_number}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{sheet_number}.xml"/>')
        content_overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{sheet_number}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        xml_rows = []
        for row_number, cells in enumerate(_cells(sheet, records_by_sheet, schema), 1):
            xml_cells = []
            for column_number, (field, value) in enumerate(zip(schema[sheet + ".csv"], cells), 1):
                if not value:
                    continue
                letter = chr(ord("A") + column_number - 1)
                ref = f"{letter}{row_number}"
                if row_number > 1 and field in ("x", "y"):
                    xml_cells.append(f'<c r="{ref}" t="n"><v>{escape(value)}</v></c>')
                elif row_number > 1 and field == "enabled":
                    bit = "1" if value == "true" else "0"
                    xml_cells.append(f'<c r="{ref}" t="b"><v>{bit}</v></c>')
                else:
                    xml_cells.append(
                        f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
            xml_rows.append(f'<row r="{row_number}">{"".join(xml_cells)}</row>')
        members[f"xl/worksheets/sheet{sheet_number}.xml"] = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<worksheet xmlns="{main_ns}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
        ).encode("utf-8")
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(content_overrides) + '</Types>'
    )
    members["[Content_Types].xml"] = content_types.encode("utf-8")
    members["_rels/.rels"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdWorkbook" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    ).encode("utf-8")
    members["xl/workbook.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheet_tags)}</sheets></workbook>'
    ).encode("utf-8")
    members["xl/_rels/workbook.xml.rels"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(worksheet_rels) + '</Relationships>'
    ).encode("utf-8")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, contents in members.items():
            _zip_member(z, name, contents)
    return out.getvalue()


def _odf_text(value: str) -> str:
    # Preserve explicit newlines/tabs within one text cell.
    return (escape(value).replace("\t", "<text:tab/>")
                         .replace("\n", "<text:line-break/>"))


def _ods(records_by_sheet=None, contract=None) -> bytes:
    schema = V13 if contract is None else contract
    sheet_order = SHEET_ORDER if records_by_sheet is None else tuple(records_by_sheet)
    sheets_xml = []
    for sheet in sheet_order:
        row_xml = []
        for row_index, cells in enumerate(_cells(sheet, records_by_sheet, schema)):
            cell_xml = []
            for field, value in zip(schema[sheet + ".csv"], cells):
                if not value:
                    cell_xml.append("<table:table-cell/>")
                elif row_index > 0 and field in ("x", "y"):
                    cell_xml.append(
                        f'<table:table-cell office:value-type="float" office:value={quoteattr(value)}>'
                        f'<text:p>{escape(value)}</text:p></table:table-cell>')
                elif row_index > 0 and field == "enabled":
                    cell_xml.append(
                        f'<table:table-cell office:value-type="boolean" '
                        f'office:boolean-value="{value}"/>')
                else:
                    cell_xml.append(
                        f'<table:table-cell office:value-type="string">'
                        f'<text:p>{_odf_text(value)}</text:p></table:table-cell>')
            row_xml.append(f'<table:table-row>{"".join(cell_xml)}</table:table-row>')
        sheets_xml.append(
            f'<table:table table:name={quoteattr(sheet)}>{"".join(row_xml)}</table:table>')
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<office:document-content {ODS_NAMESPACES} office:version="1.2">'
        f'<office:body><office:spreadsheet>{"".join(sheets_xml)}</office:spreadsheet>'
        '</office:body></office:document-content>'
    )
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.2">'
        f'<manifest:file-entry manifest:full-path="/" manifest:media-type="{MIME_ODS}"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        '</manifest:manifest>'
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        _zip_member(z, "mimetype", MIME_ODS.encode("ascii"), zipfile.ZIP_STORED)
        _zip_member(z, "content.xml", content.encode("utf-8"))
        _zip_member(z, "META-INF/manifest.xml", manifest.encode("utf-8"))
    return out.getvalue()


def template_bytes(extension: str) -> bytes:
    """An explicit, reproducible demo. No project file is opened or written."""
    if extension == "xlsx":
        return _xlsx()
    if extension == "ods":
        return _ods()
    raise ValueError("unsupported template extension")
