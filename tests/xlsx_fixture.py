"""Independently constructed, real OOXML ZIP fixtures for XLSX import tests.

The writer builds OOXML bytes without consulting the parser under test. It
also exposes raw OOXML parts to inject malformed/unsupported workbook content.
"""
from __future__ import annotations

import csv
import io
import zipfile
from xml.sax.saxutils import escape, quoteattr

from test_csv_import import DEV, PORTS, LINKS, ZONES

STANDARD_SHEETS = {
    "Devices": DEV,
    "Interfaces": PORTS,
    "Links": LINKS,
    "Zones": ZONES,
}


def _column(number: int) -> str:
    answer = ""
    while number:
        number, rem = divmod(number-1, 26)
        answer = chr(65+rem) + answer
    return answer


def _xml_text(value: str) -> str:
    return escape(value, {'"': '&quot;'})


def workbook_parts(sheets=None, *, shared_strings=False, reorder=False) -> dict[str, bytes]:
    data = dict(STANDARD_SHEETS if sheets is None else sheets)
    if reorder:
        data = dict(reversed(list(data.items())))
    names = list(data)
    package = {
        "[Content_Types].xml": b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            b'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            b'<Default Extension="xml" ContentType="application/xml"/>'
            b'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            b'</Types>',
        "_rels/.rels": b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rIdX" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            b'</Relationships>',
    }
    sheets_xml = []
    rels = []
    shared = []
    for index, (name, contents) in enumerate(data.items(), 1):
        sheets_xml.append(
            f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"/>')
        rels.append(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>')
        table = list(csv.reader(io.StringIO(contents, newline="")))
        header = table[0] if table else []
        xml_rows = []
        for rid, fields in enumerate(table, 1):
            cells = []
            for cid, text in enumerate(fields, 1):
                if text == "":
                    continue
                coord = f"{_column(cid)}{rid}"
                field = header[cid-1] if cid <= len(header) else ""
                if rid > 1 and field in ("x", "y"):
                    cells.append(f'<c r="{coord}" t="n"><v>{escape(text)}</v></c>')
                elif rid > 1 and field == "enabled":
                    # Genuine Excel boolean cell, not a fake text rendition
                    bit = "1" if text == "true" else "0"
                    cells.append(f'<c r="{coord}" t="b"><v>{bit}</v></c>')
                elif shared_strings:
                    if text not in shared:
                        shared.append(text)
                    ix = shared.index(text)
                    cells.append(f'<c r="{coord}" t="s"><v>{ix}</v></c>')
                else:
                    cells.append(
                        f'<c r="{coord}" t="inlineStr"><is><t>{_xml_text(text)}</t></is></c>')
            xml_rows.append(f'<row r="{rid}">{"".join(cells)}</row>')
        data_xml = '<?xml version="1.0" encoding="UTF-8"?>' + (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/>'
            f'<sheetData>{"".join(xml_rows)}</sheetData>'
            '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
            '</worksheet>')
        package[f"xl/worksheets/sheet{index}.xml"] = data_xml.encode("utf-8")
    # Declare actual Open Packaging Convention content types instead of
    # relying on the importer's permissive XML filename resolution.
    content_overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet' + str(i) + '.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(names)+1))
    if shared_strings:
        content_overrides += (
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>')
        rels.append(
            '<Relationship Id="rIdShared" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>')
    package["[Content_Types].xml"] = package["[Content_Types].xml"].replace(
        b"</Types>", content_overrides.encode("utf-8") + b"</Types>")
    package["xl/workbook.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheets_xml)}</sheets></workbook>'
    ).encode("utf-8")
    package["xl/_rels/workbook.xml.rels"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}</Relationships>'
    ).encode("utf-8")
    if shared_strings:
        values = "".join(f'<si><t>{_xml_text(item)}</t></si>' for item in shared)
        package["xl/sharedStrings.xml"] = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{len(shared)}" uniqueCount="{len(shared)}">{values}</sst>'
        ).encode("utf-8")
    return package


def zip_parts(parts: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, raw in parts.items():
            archive.writestr(path, raw)
    return out.getvalue()


def make_workbook(sheets=None, *, shared_strings=False, reorder=False) -> bytes:
    return zip_parts(workbook_parts(
        sheets, shared_strings=shared_strings, reorder=reorder))
