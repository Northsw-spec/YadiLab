"""Bounded, literal OOXML and ODF readers for read-only source inspection."""
from __future__ import annotations

import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

from .model import ProjectValidationError
from .import_inspection import _column_name, _invalid, MAX_ROWS, MAX_COLUMNS, MAX_CELLS, PREVIEW_ROWS

X = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'
O = 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
S = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
M = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
ODF_MIME = b'application/vnd.oasis.opendocument.spreadsheet'
COORD = re.compile(r'([A-Z]{1,3})([1-9][0-9]*)\Z')
MAX_XML = 5 * 1024 * 1024


def q(ns, name):
    return f'{{{ns}}}{name}'


def fail(where, reason):
    _invalid(where, reason)


def xml(z, name):
    try:
        raw = z.read(name)
    except KeyError:
        fail(name, 'required XML part missing')
    except (zipfile.BadZipFile, EOFError, OSError):
        fail(name, 'corrupt ZIP part')
    if len(raw) > MAX_XML or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        fail(name, 'unsupported or oversized XML')
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        fail(name, 'malformed XML')


def archive(data, kind):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        entries = z.infolist()
        if not entries or len(entries) > 256:
            fail(kind, 'ZIP part count outside 1..256')
        names = [e.filename for e in entries]
        if len(set(names)) != len(names):
            fail(kind, 'duplicate ZIP parts')
        total = 0
        for e in entries:
            if (e.is_dir() or e.flag_bits & 1 or e.file_size > MAX_XML
                    or e.filename.startswith('/') or '..' in e.filename.split('/')
                    or '\\' in e.filename or e.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                fail(kind, f'unsafe ZIP part {e.filename}')
            total += e.file_size
            if total > 12 * 1024 * 1024:
                fail(kind, 'expanded ZIP exceeds 12 MiB')
            if e.compress_size and e.file_size > e.compress_size * 1500:
                fail(kind, 'extreme ZIP compression ratio')
        try:
            for e in entries:
                z.read(e)  # CRC and local headers, including ignored metadata parts.
        except (zipfile.BadZipFile, EOFError, OSError):
            fail(kind, 'corrupt ZIP member')
        return z
    except (zipfile.BadZipFile, EOFError, OSError):
        fail(kind, 'invalid ZIP structure')


def relationships(z, name):
    root = xml(z, name)
    if root.tag != q(P, 'Relationships') or root.attrib:
        fail(name, 'invalid relationships root')
    found = {}
    for rel in root:
        if rel.tag != q(P, 'Relationship') or set(rel.attrib) != {'Id', 'Type', 'Target'}:
            fail(name, 'external or unsupported relationship')
        rid, target, typ = rel.get('Id'), rel.get('Target'), rel.get('Type')
        if not rid or not target or not typ or rid in found or ':' in target or target.startswith('//') or '\\' in target or '..' in target.split('/'):
            fail(name, 'invalid or duplicate local relationship')
        found[rid] = (target, typ)
    return found


def index(ref, row, where):
    match = COORD.fullmatch(ref or '')
    if not match or int(match.group(2)) != row:
        fail(where, f'invalid cell coordinate {ref!r}')
    col = 0
    for letter in match.group(1):
        col = col * 26 + ord(letter) - 64
    if col > MAX_COLUMNS:
        fail(where, 'column exceeds 256')
    return col


def plain_text(element, ns, outer, where):
    if element.tag != q(ns, outer) or element.attrib or len(element) != 1 or element[0].tag != q(ns, 't') or len(element[0]) or set(element[0].attrib) - {'{http://www.w3.org/XML/1998/namespace}space'}:
        fail(where, 'rich or unsupported text')
    return element[0].text or ''


def xlsx_cell(cell, shared, where):
    if set(cell.attrib) - {'r', 't', 's'}:
        fail(where, 'unsupported cell attributes')
    kind = cell.get('t', 'n')
    if kind not in ('n', 's', 'inlineStr', 'b'):
        fail(where, f'unsupported cell type {kind!r}')
    if len(cell) == 0:
        return None
    if len(cell) != 1 or cell[0].tag not in {q(X, 'v'), q(X, 'is')}:
        fail(where, 'formula, cached formula or unsupported cell content')
    child = cell[0]
    if kind == 'inlineStr' and child.tag == q(X, 'is'):
        return 'text', plain_text(child, X, 'is', where)
    if child.tag != q(X, 'v') or len(child) or child.attrib or child.text is None:
        fail(where, 'invalid cell value')
    raw = child.text
    if kind == 's':
        if not raw.isascii() or not raw.isdecimal() or int(raw) >= len(shared):
            fail(where, 'invalid shared-string index')
        return 'text', shared[int(raw)]
    if kind == 'b' and raw in ('0', '1'):
        return 'boolean', raw
    if kind == 'n' and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?', raw):
        return 'number', raw
    if kind == 'str':
        fail(where, 'cached formula text unsupported')
    fail(where, f'unsupported cell type {kind!r}')


def xlsx_sheet(z, part, name, serial, shared, budget, from_row=1, row_limit=PREVIEW_ROWS):
    root = xml(z, part)
    if root.tag != q(X, 'worksheet'):
        fail(name, 'invalid worksheet root')
    allowed = {'dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'sheetData', 'pageMargins', 'printOptions', 'pageSetup', 'headerFooter'}
    if any(child.tag not in {q(X, k) for k in allowed} for child in root):
        fail(name, 'unsupported worksheet object or merged cells')
    data = root.find(q(X, 'sheetData'))
    if data is None or len(root.findall(q(X, 'sheetData'))) != 1:
        fail(name, 'missing sheetData')
    cols = root.find(q(X, 'cols'))
    if cols is not None:
        for col in cols:
            if col.tag != q(X, 'col') or col.get('hidden', '0').lower() not in ('0', 'false'):
                fail(name, 'hidden or unsupported column')
    last_row = 0
    high_row = 0
    high_col = 0
    populated = 0
    preview = []
    next_row = None
    for row in data:
        if row.tag != q(X, 'row'):
            fail(name, 'unsupported sheetData child')
        raw = row.get('r')
        if not raw or not raw.isascii() or not raw.isdecimal():
            fail(name, 'row lacks coordinate')
        number = int(raw)
        if number <= last_row or number > MAX_ROWS or row.get('hidden', '0').lower() not in ('0', 'false'):
            fail(name, f'invalid or hidden row {raw}')
        last_row = number
        cells = []
        previous = 0
        for cell in row:
            if cell.tag != q(X, 'c'):
                fail(name, f'unsupported row content {number}')
            ref = cell.get('r')
            col = index(ref, number, name)
            if col <= previous:
                fail(name, f'duplicate or unordered cell {ref}')
            previous = col
            value = xlsx_cell(cell, shared, f'{name}!{ref}')
            if value is None or value[1] == '':
                continue
            budget[0] += 1
            if budget[0] > MAX_CELLS:
                fail(name, 'more than 100000 stored cells')
            high_col = max(high_col, col)
            if number >= from_row and (row_limit is None or len(preview) < row_limit):
                cells.append({'address': ref, 'type': value[0], 'value': value[1]})
        if cells or any(xlsx_cell(c, shared, f'{name}!{c.get("r")}') not in (None, ('text', '')) for c in row):
            high_row = number
            populated += 1
            if number >= from_row and (row_limit is None or len(preview) < row_limit):
                preview.append({'row': number, 'cells': cells})
            elif number >= from_row and next_row is None:
                next_row = number
    return {'tableId': f'sheet-{serial}', 'name': name, 'rowCount': high_row,
            'populatedRowCount': populated, 'columnCount': high_col,
            'previewRows': preview, 'nextRow': next_row}


def xlsx(data, from_row=1, row_limit=PREVIEW_ROWS):
    with archive(data, 'XLSX') as z:
        names = set(z.namelist())
        required = {'[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels'}
        if not required <= names:
            fail('XLSX', 'missing OOXML package metadata')
        content = xml(z, '[Content_Types].xml')
        if content.tag != q(C, 'Types') or any(c.tag not in (q(C, 'Default'), q(C, 'Override')) for c in content):
            fail('XLSX', 'invalid content types')
        overrides = {}
        for item in content:
            if 'macro' in (item.get('ContentType') or '').lower():
                fail('XLSX', 'macros unsupported')
            if item.tag == q(C, 'Override'):
                part, typ = item.get('PartName'), item.get('ContentType')
                if not part or not typ or part in overrides:
                    fail('XLSX', 'invalid content type override')
                overrides[part] = typ
        if overrides.get('/xl/workbook.xml') != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml':
            fail('XLSX', 'workbook content type missing')
        root_rels = relationships(z, '_rels/.rels')
        if len(root_rels) != 1 or next(iter(root_rels.values())) not in {('xl/workbook.xml', R + '/officeDocument'), ('/xl/workbook.xml', R + '/officeDocument')}:
            fail('XLSX', 'invalid officeDocument relationship')
        workbook = xml(z, 'xl/workbook.xml')
        allowed_book = {q(X, k) for k in ('fileVersion', 'workbookPr', 'bookViews', 'sheets', 'calcPr')}
        if workbook.tag != q(X, 'workbook') or any(c.tag not in allowed_book for c in workbook):
            fail('XLSX', 'invalid workbook or external references')
        sheets = workbook.find(q(X, 'sheets'))
        if sheets is None or not 1 <= len(sheets) <= 32:
            fail('XLSX', 'sheet count outside 1..32')
        rels = relationships(z, 'xl/_rels/workbook.xml.rels')
        allowed_types = {R + '/worksheet', R + '/styles', R + '/sharedStrings', R + '/theme'}
        if any(typ not in allowed_types for _, typ in rels.values()):
            fail('XLSX', 'unsupported workbook relationship')
        permitted = required | {'xl/sharedStrings.xml', 'xl/styles.xml', 'xl/theme/theme1.xml', 'docProps/core.xml', 'docProps/app.xml'}
        shared = []
        if 'xl/sharedStrings.xml' in names:
            string_root = xml(z, 'xl/sharedStrings.xml')
            if string_root.tag != q(X, 'sst'):
                fail('XLSX', 'invalid sharedStrings')
            for item in string_root:
                shared.append(plain_text(item, X, 'si', 'sharedStrings'))
                if len(shared) > MAX_CELLS:
                    fail('XLSX', 'too many shared strings')
        result = []
        used = set()
        budget = [0]
        for serial, sheet in enumerate(sheets, 1):
            if sheet.tag != q(X, 'sheet') or sheet.get('state', 'visible') != 'visible':
                fail('XLSX', 'hidden or unsupported sheet')
            name, rid = sheet.get('name'), sheet.get(q(R, 'id'))
            if not name or not rid or name in used or rid not in rels:
                fail('XLSX', 'invalid or duplicate sheet')
            used.add(name)
            target, typ = rels[rid]
            part = posixpath.normpath(target[1:] if target.startswith('/') else posixpath.join('xl', target))
            if typ != R + '/worksheet' or not part.startswith('xl/worksheets/') or not part.endswith('.xml') or part not in names:
                fail(name, 'invalid local worksheet relationship')
            if overrides.get('/' + part) != 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml':
                fail(name, 'worksheet content type missing')
            permitted.add(part)
            result.append(xlsx_sheet(z, part, name, serial, shared, budget, from_row, row_limit))
        if names - permitted:
            fail('XLSX', f'unsupported package parts: {sorted(names - permitted)[:3]}')
        return result


def count(element, attr, where, limit):
    raw = element.get(q(T, attr), '1')
    if not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= limit:
        fail(where, f'invalid {attr}')
    return int(raw)


def odf_text(p, where):
    if p.tag != q(S, 'p') or p.attrib:
        fail(where, 'unsupported text paragraph')
    out = [p.text or '']
    for child in p:
        if child.tag == q(S, 'line-break') and not child.attrib and not len(child):
            out.append('\n')
        elif child.tag == q(S, 'tab') and not child.attrib and not len(child):
            out.append('\t')
        elif child.tag == q(S, 's') and not len(child):
            out.append(' ' * count_text_spaces(child, where))
        else:
            fail(where, 'rich text or embedded object unsupported')
        out.append(child.tail or '')
    return ''.join(out)


def count_text_spaces(element, where):
    raw = element.get(q(S, 'c'), '1')
    if set(element.attrib) - {q(S, 'c')} or not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= 1000:
        fail(where, 'invalid text spaces')
    return int(raw)


def odf_cell(cell, where):
    if cell.tag != q(T, 'table-cell'):
        fail(where, 'merged or unsupported cell')
    allowed = {q(O, 'value-type'), q(O, 'value'), q(O, 'boolean-value'), q(O, 'string-value'), q(T, 'style-name'), q(T, 'number-columns-repeated')}
    if set(cell.attrib) - allowed:
        fail(where, 'formula or unsupported cell attribute')
    if any(p.tag != q(S, 'p') for p in cell):
        fail(where, 'unsupported cell object')
    display = '\n'.join(odf_text(p, where) for p in cell)
    kind = cell.get(q(O, 'value-type'))
    if kind is None:
        if display or cell.get(q(O, 'value')) is not None:
            fail(where, 'untyped cell with data')
        return None
    if kind == 'string':
        declared = cell.get(q(O, 'string-value'))
        if declared is not None and declared != display:
            fail(where, 'text literal mismatch')
        return 'text', display
    if kind == 'float':
        value = cell.get(q(O, 'value'))
        if value is None or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?', value):
            fail(where, 'invalid numeric literal')
        if display and display != value:
            fail(where, 'formatted numeric display differs from literal')
        return 'number', value
    if kind == 'boolean':
        value = cell.get(q(O, 'boolean-value'))
        if value not in ('true', 'false') or (display and display.lower() != value):
            fail(where, 'invalid boolean literal')
        return 'boolean', value
    fail(where, f'unsupported value-type {kind!r}')


def ods_sheet(table, serial, budget, from_row=1, row_limit=PREVIEW_ROWS):
    name = table.get(q(T, 'name'))
    if not name or table.get(q(T, 'visibility'), 'visible') != 'visible':
        fail('ODS', 'unnamed or hidden sheet')
    if set(table.attrib) - {q(T, 'name'), q(T, 'visibility'), q(T, 'style-name')}:
        fail(name, 'unsupported table attributes')
    row_number = 0
    highest = 0
    high_row = 0
    populated = 0
    preview = []
    next_row = None
    started = False
    declared_columns = 0
    for row in table:
        if row.tag == q(T, 'table-column'):
            if started or row.get(q(T, 'visibility'), 'visible') != 'visible':
                fail(name, 'hidden or misplaced column')
            declared_columns += count(row, 'number-columns-repeated', name, MAX_COLUMNS)
            if declared_columns > MAX_COLUMNS:
                fail(name, 'column declarations exceed 256')
            continue
        started = True
        if row.tag != q(T, 'table-row') or row.get(q(T, 'visibility'), 'visible') != 'visible':
            fail(name, 'hidden or unsupported row')
        if set(row.attrib) - {q(T, 'visibility'), q(T, 'style-name'), q(T, 'default-cell-style-name'), q(T, 'number-rows-repeated')}:
            fail(name, 'unsupported row attributes')
        repeat = count(row, 'number-rows-repeated', name, MAX_ROWS)
        if row_number + repeat > MAX_ROWS:
            fail(name, 'row exceeds 5001')
        cells = []
        col_number = 0
        for cell in row:
            col_repeat = count(cell, 'number-columns-repeated', name, MAX_COLUMNS)
            if col_number + col_repeat > MAX_COLUMNS:
                fail(name, 'column exceeds 256')
            value = odf_cell(cell, f'{name}!{_column_name(col_number + 1)}{row_number + 1}')
            if value is not None and value[1] != '':
                budget[0] += col_repeat * repeat
                if budget[0] > MAX_CELLS:
                    fail(name, 'more than 100000 stored cells')
                highest = max(highest, col_number + col_repeat)
                for offset in range(col_repeat):
                    if row_number + repeat >= from_row and (row_limit is None or len(preview) < row_limit):
                        cells.append({'address': f'{_column_name(col_number + offset + 1)}{row_number + 1}', 'type': value[0], 'value': value[1]})
            col_number += col_repeat
        if cells or budget[0] and any(odf_cell(c, name) not in (None, ('text', '')) for c in row):
            populated += repeat
            high_row = row_number + repeat
            first = max(row_number + 1, from_row)
            if first <= row_number + repeat:
                available = (row_number + repeat - first + 1 if row_limit is None
                             else row_limit - len(preview))
                for number in range(first, min(row_number + repeat + 1, first + available)):
                    preview.append({'row': number, 'cells': [
                        {**c, 'address': re.sub(r'\d+$', str(number), c['address'])}
                        for c in cells]})
                if first + available <= row_number + repeat and next_row is None:
                    next_row = first + available
            row_number += repeat
        else:
            row_number += repeat
    return {'tableId': f'sheet-{serial}', 'name': name, 'rowCount': high_row,
            'populatedRowCount': populated, 'columnCount': highest,
            'previewRows': preview, 'nextRow': next_row}


def ods(data, from_row=1, row_limit=PREVIEW_ROWS):
    with archive(data, 'ODS') as z:
        names = set(z.namelist())
        required = {'mimetype', 'content.xml', 'META-INF/manifest.xml'}
        if not required <= names or z.infolist()[0].filename != 'mimetype' or z.infolist()[0].compress_type != zipfile.ZIP_STORED or z.read('mimetype') != ODF_MIME:
            fail('ODS', 'invalid ODF mimetype or package')
        if names - (required | {'styles.xml', 'meta.xml', 'settings.xml'}):
            fail('ODS', 'unsupported package parts')
        manifest = xml(z, 'META-INF/manifest.xml')
        if manifest.tag != q(M, 'manifest'):
            fail('ODS', 'invalid manifest')
        listed = set()
        for item in manifest:
            if item.tag != q(M, 'file-entry') or len(item):
                fail('ODS', 'encrypted or unsupported manifest entry')
            path, typ = item.get(q(M, 'full-path')), item.get(q(M, 'media-type'))
            if not path or typ is None or path in listed or path not in names | {'/'} or set(item.attrib) - {q(M, 'full-path'), q(M, 'media-type'), q(M, 'version')}:
                fail('ODS', 'invalid manifest entry')
            if (path == '/' and typ != ODF_MIME.decode('ascii')) or (path == 'content.xml' and typ != 'text/xml'):
                fail('ODS', 'manifest MIME mismatch')
            listed.add(path)
        if not {'/', 'content.xml'} <= listed or (names - {'mimetype', 'META-INF/manifest.xml'}) - listed:
            fail('ODS', 'missing manifest entries')
        root = xml(z, 'content.xml')
        if root.tag != q(O, 'document-content') or any(c.tag not in {q(O, 'font-face-decls'), q(O, 'automatic-styles'), q(O, 'body')} for c in root):
            fail('ODS', 'unsupported content root')
        body = root.find(q(O, 'body'))
        if body is None or len(body) != 1 or body[0].tag != q(O, 'spreadsheet'):
            fail('ODS', 'missing spreadsheet body')
        tables = list(body[0])
        if not 1 <= len(tables) <= 32 or any(t.tag != q(T, 'table') for t in tables):
            fail('ODS', 'unsupported spreadsheet objects or sheet count')
        seen = set()
        budget = [0]
        result = []
        for serial, table in enumerate(tables, 1):
            name = table.get(q(T, 'name'))
            if name in seen:
                fail('ODS', 'duplicate sheet name')
            seen.add(name)
            result.append(ods_sheet(table, serial, budget, from_row, row_limit))
        return result
