"""Deterministic, read-only source claims and selected import candidates."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from .import_inspection import _decode_source, inspect_all_rows
from .model import (ProjectValidationError, NODE_KINDS, _id, _name,
                    validate_project, canonical_network_view, _static_route)

FIELDS = frozenset({'node.id', 'node.label', 'node.kind', 'node.zoneId'})
ZONE_FIELDS = frozenset({'zone.id', 'zone.label'})
PORT_FIELDS = frozenset({'port.nodeId', 'port.id', 'port.name', 'port.enabled',
                         'port.vlanMode', 'port.accessVlan', 'port.allowedVlans', 'port.ipv4'})
IP_FIELDS = frozenset({'ip.nodeId', 'ip.portId', 'ip.ipv4'})
ROUTE_FIELDS = frozenset({'route.nodeId', 'route.id', 'route.destination',
                          'route.nextHop', 'route.outPort'})
VLAN_INTEGER = re.compile(r'[1-9][0-9]{0,3}\Z')
VLAN_LIST = re.compile(r'[1-9][0-9]{0,3}(,[1-9][0-9]{0,3})*\Z')
ROLES = {'device_inventory': FIELDS, 'zone_inventory': ZONE_FIELDS,
         'interface_inventory': PORT_FIELDS, 'ip_plan': IP_FIELDS,
         'static_route_register': ROUTE_FIELDS,
         'documentation_only': frozenset()}
ROLE_KIND = {'device_inventory': 'node', 'zone_inventory': 'zone',
             'interface_inventory': 'port', 'ip_plan': 'ipBinding',
             'static_route_register': 'staticRoute'}
VIEW_KEYS = {'viewId', 'sourceId', 'tableId', 'role', 'headerRow', 'selectedRows',
             'columns', 'valueMaps', 'constants', 'expectedHeaders', 'label'}
REQUEST_KEYS = {'contractVersion', 'projectName', 'sources', 'mappingViews',
                'transformations', 'rowValues', 'excludedUses', 'selectedUnitIds'}
COLUMN = re.compile(r'[A-Z]{1,2}\Z')
HEX_ID = re.compile(r'[a-f0-9]{64}\Z')


def fail(where, reason):
    raise ProjectValidationError(f'import plan {where}: {reason}')


def canonical_json(value):
    """§7.4 canonicalJson for already validated data, returning UTF-8 bytes."""
    def check(item):
        if item is None or type(item) in (bool, str, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict) and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        fail('canonicalJson', 'unsupported or non-finite JSON value')
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _metadata_only(value):
    """A plan request contains no network coordinates or arbitrary JSON floats."""
    if type(value) is float:
        fail('request', 'floating-point metadata is not supported')
    if isinstance(value, list):
        for item in value:
            _metadata_only(item)
    elif isinstance(value, dict):
        for item in value.values():
            _metadata_only(item)


def internal_id(prefix, value):
    return prefix + hashlib.sha256(canonical_json(value)).hexdigest()[:32]


def _decision_id(payload, seen):
    value = canonical_json(payload)
    decision_id = internal_id('d-', payload)
    if decision_id in seen and seen[decision_id] != value:
        fail('decisions', 'internal decisionId collision')
    seen[decision_id] = value
    return decision_id


def object_exact(value, keys, where):
    if type(value) is not dict or set(value) != keys:
        fail(where, 'expected exact fields: ' + ', '.join(sorted(keys)))
    return value


def bounded_list(value, limit, where):
    if type(value) is not list or len(value) > limit:
        fail(where, f'expected an array of at most {limit} items')
    return value


def column_index(label):
    if type(label) is not str or not COLUMN.fullmatch(label):
        fail('column', f'invalid column {label!r}')
    result = 0
    for char in label:
        result = result * 26 + ord(char) - 64
    if result > 256:
        fail('column', 'column beyond IV')
    return result


def source_ref(source_id, table_id, row, address=None):
    return {'sourceId': source_id, 'tableId': table_id, 'row': row, 'address': address}


def origin(kind, *, source_id=None, table_id=None, row=None, address=None, decision_id=None):
    return {'kind': kind, 'sourceId': source_id, 'tableId': table_id,
            'row': row, 'address': address, 'decisionId': decision_id}


def diagnostic(code, refs, unit_id=None, severity='ERROR'):
    refs = sorted({(r['sourceId'], r['tableId'], r['row'], r['address']) for r in refs},
                  key=lambda v: (v[0], v[1], v[2], v[3] or ''))
    return {'code': code, 'severity': severity, 'message': code.replace('_', ' ').lower(),
            'sourceRefs': [source_ref(*ref) for ref in refs], 'unitId': unit_id}


def _typed_value(value_type, value, field, where):
    if value_type == 'text' and type(value) is str and field not in ('port.accessVlan', 'port.allowedVlans'):
        return value
    if value_type == 'boolean' and type(value) is bool and field == 'port.enabled':
        return value
    if value_type == 'null' and value is None and field == 'node.zoneId':
        return None
    if value_type == 'integer' and field == 'port.accessVlan' and type(value) is int and 1 <= value <= 4094:
        return value
    if (value_type == 'integer_list' and field == 'port.allowedVlans' and
            type(value) is list and 1 <= len(value) <= 64 and
            all(type(item) is int and 1 <= item <= 4094 for item in value) and
            len(set(value)) == len(value)):
        return value
    fail(where, 'unsupported or incorrectly typed user value')


def _canonical_ipv4(value):
    """Use the canonical project validator for explicit IPv4 interface syntax."""
    if type(value) is not str:
        raise ProjectValidationError('IPv4/CIDR must be text')
    sample = {'schemaVersion': '1.3', 'name': 'Validation', 'zones': [], 'links': [],
              'nodes': [{'id': 'Validation', 'label': 'Validation', 'kind': 'host',
                         'x': 0, 'y': 0, 'zoneId': None,
                         'ports': [{'id': 'Port', 'name': 'Port', 'enabled': True,
                                    'ipv4': value}]}]}
    return validate_project(sample)['nodes'][0]['ports'][0]['ipv4']


def _sources(raw_sources):
    sources = bounded_list(raw_sources, 8, 'sources')
    if not sources:
        fail('sources', 'at least one source required')
    manifest, tables = [], {}
    total_bytes = total_rows = total_cells = 0
    for index, entry in enumerate(sources, 1):
        if type(entry) is not dict or entry.get('sourceId') != f'src-{index}':
            fail('sources', 'sourceId must be sequential src-1..src-8')
        payload = {k: v for k, v in entry.items() if k != 'sourceId'}
        filename, kind, raw, delimiter = _decode_source(payload)
        total_bytes += len(raw)
        if total_bytes > 4 * 1024 * 1024:
            fail('sources', 'combined original bytes exceed 4 MiB')
        inspection = inspect_all_rows(payload)
        info = []
        for table in inspection['tables']:
            rows = {row['row']: row['cells'] for row in table['previewRows']}
            total_rows += len(rows)
            total_cells += sum(len(cells) for cells in rows.values())
            if total_rows > 10000 or total_cells > 100000:
                fail('sources', 'combined row or cell budget exceeded')
            tables[(entry['sourceId'], table['tableId'])] = {'meta': table, 'rows': rows}
            info.append({key: table[key] for key in ('tableId', 'name', 'rowCount',
                                                     'populatedRowCount', 'columnCount')})
        manifest.append({'sourceId': entry['sourceId'], 'filename': filename,
                         'kind': kind, 'sha256': inspection['source']['sha256'],
                         'csvDelimiter': delimiter, 'byteLength': len(raw), 'tables': info})
    return manifest, tables


def _views(raw_views, tables):
    views = bounded_list(raw_views, 64, 'mappingViews')
    total_uses = 0
    for index, view in enumerate(views, 1):
        object_exact(view, VIEW_KEYS, f'mappingViews[{index - 1}]')
        if view['viewId'] != f'view-{index}':
            fail('mappingViews', 'viewId must be sequential view-1..view-64')
        if type(view['sourceId']) is not str or type(view['tableId']) is not str:
            fail('mappingViews', 'sourceId and tableId must be strings')
        table = tables.get((view['sourceId'], view['tableId']))
        if table is None:
            fail('mappingViews', 'unknown sourceId/tableId')
        role = view['role']
        if type(role) is not str or role not in ROLES:
            fail('mappingViews', f'role {role!r} not implemented')
        rows = table['rows']
        header = view['headerRow']
        if header is not None and (type(header) is not int or header not in rows):
            fail('mappingViews', 'headerRow must be a real populated source row')
        headers = [cell['value'] for cell in rows[header]] if header is not None else []
        if (type(view['expectedHeaders']) is not list or
                view['expectedHeaders'] != headers):
            fail('mappingViews', 'expectedHeaders differ from original header cells')
        selected = bounded_list(view['selectedRows'], 5001, 'selectedRows')
        if any(type(row) is not int or row not in rows or row == header for row in selected):
            fail('mappingViews', 'selectedRows contain missing/header row')
        if selected != sorted(set(selected)):
            fail('mappingViews', 'selectedRows must be sorted and unique')
        total_uses += len(selected)
        if total_uses > 20000:
            fail('mappingViews', 'more than 20000 selected row uses')
        columns = view['columns']
        if type(columns) is not dict or not set(columns) <= ROLES[role]:
            fail('mappingViews', 'unsupported target field')
        for field, labels in columns.items():
            if (not 1 <= len(bounded_list(labels, 64, field)) <= 64 or
                    any(type(label) is not str for label in labels) or len(labels) != len(set(labels))):
                fail('mappingViews', 'invalid or duplicate source columns')
            for label in labels:
                if column_index(label) > table['meta']['columnCount']:
                    fail('mappingViews', 'source column outside actual table')
        maps = view['valueMaps']
        if type(maps) is not dict or not set(maps) <= set(columns):
            fail('mappingViews', 'valueMaps need bound source columns')
        for field, mapping in maps.items():
            if type(mapping) is not dict or not mapping or any(type(a) is not str or type(b) is not str for a, b in mapping.items()):
                fail('mappingViews', f'invalid valueMap for {field}')
            if field == 'port.enabled' and any(b not in ('true', 'false') for b in mapping.values()):
                fail('mappingViews', 'port.enabled valueMaps must produce exact true/false strings')
        constants = view['constants']
        if type(constants) is not dict or set(constants) & set(columns) or not set(constants) <= (ROLES[role] - {'node.id', 'zone.id', 'port.nodeId', 'port.id', 'ip.nodeId', 'ip.portId', 'route.nodeId', 'route.id', 'route.outPort'}):
            fail('mappingViews', 'invalid constants or identity constant')
        for field, item in constants.items():
            object_exact(item, {'type', 'value'}, f'constant {field}')
            _typed_value(item['type'], item['value'], field, f'constant {field}')
        if type(view['label']) is not str or len(view['label']) > 240:
            fail('mappingViews', 'invalid label')
    return views


def _transformations(raw, views):
    by_view = {view['viewId']: view for view in views}
    result, seen = [], set()
    for item in bounded_list(raw, 64, 'transformations'):
        object_exact(item, {'viewId', 'targetField', 'operation', 'delimiter'}, 'transformation')
        view = by_view.get(item['viewId']) if type(item['viewId']) is str else None
        field = item['targetField']
        expected = {'port.accessVlan': ('parse_vlan_integer', None),
                    'port.allowedVlans': ('split_vlan_integer_list', ',')}.get(field) if type(field) is str else None
        key = (item['viewId'], field)
        if (view is None or expected != (item['operation'], item['delimiter']) or
                field not in view['columns'] or len(view['columns'][field]) != 1 or
                field in view['valueMaps'] or key in seen):
            fail('transformations', 'invalid, overlapping or duplicate VLAN transformation')
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: (item['viewId'], item['targetField']))


def _decisions(value, views):
    view_by_id = {v['viewId']: v for v in views}
    row_values = bounded_list(value['rowValues'], 10000, 'rowValues')
    seen = set()
    for item in row_values:
        object_exact(item, {'viewId', 'row', 'targetField', 'valueType', 'value'}, 'rowValue')
        if (type(item['viewId']) is not str or type(item['row']) is not int or
                type(item['targetField']) is not str or type(item['valueType']) is not str):
            fail('rowValues', 'invalid field types')
        view = view_by_id.get(item['viewId'])
        key = (item['viewId'], item['row'], item['targetField'])
        if view is None or item['row'] not in view['selectedRows'] or item['targetField'] not in ROLES[view['role']] or key in seen:
            fail('rowValues', 'unknown, duplicate or unsupported row value')
        _typed_value(item['valueType'], item['value'], item['targetField'], 'rowValue')
        seen.add(key)
    excluded = bounded_list(value['excludedUses'], 10000, 'excludedUses')
    seen = set()
    for item in excluded:
        object_exact(item, {'viewId', 'row', 'reason'}, 'excludedUse')
        if type(item['viewId']) is not str or type(item['row']) is not int:
            fail('excludedUses', 'invalid viewId or row')
        view = view_by_id.get(item['viewId'])
        key = (item['viewId'], item['row'])
        if (view is None or type(item['row']) is not int or item['row'] not in view['selectedRows'] or key in seen or
                type(item['reason']) is not str or not 1 <= len(item['reason']) <= 240):
            fail('excludedUses', 'invalid or duplicate excluded use')
        seen.add(key)
    transformations = _transformations(value['transformations'], views)
    selected = bounded_list(value['selectedUnitIds'], 10000, 'selectedUnitIds')
    if any(type(x) is not str for x in selected) or selected != sorted(set(selected)):
        fail('selectedUnitIds', 'expected sorted unique unit IDs')
    return (sorted(row_values, key=lambda r: (r['viewId'], r['row'], r['targetField'])),
            sorted(excluded, key=lambda e: (e['viewId'], e['row'])), selected, transformations)


def _claim(view, row, cells, row_values, decision_ids, transformations):
    source_id, table_id, view_id = view['sourceId'], view['tableId'], view['viewId']
    by_column = {re.match(r'[A-Z]+', c['address']).group(): c for c in cells}
    fields, origins, issues, ip_issues, used = {}, {}, [], [], set()
    for field in sorted(set(view['columns']) | set(view['constants']) |
                        {key[2] for key in row_values if key[:2] == (view_id, row)}):
        issue_start = len(issues)
        candidates = []
        for label in view['columns'].get(field, []):
            cell = by_column.get(label)
            if cell is None:
                continue
            used.add(cell['address'])
            src = origin('source_cell', source_id=source_id, table_id=table_id,
                         row=row, address=cell['address'])
            raw = cell['value']
            mapped = view['valueMaps'].get(field)
            transformation = transformations.get((view_id, field))
            if field in ('port.accessVlan', 'port.allowedVlans'):
                if transformation is None:
                    issues.append(('VLAN_TRANSFORMATION_REQUIRED', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                    continue
                pattern = VLAN_INTEGER if field == 'port.accessVlan' else VLAN_LIST
                if cell['type'] not in ('text', 'number') or not pattern.fullmatch(raw):
                    issues.append(('INVALID_VLAN_SYNTAX', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                    continue
                parsed = int(raw) if field == 'port.accessVlan' else [int(part) for part in raw.split(',')]
                try:
                    _typed_value('integer' if field == 'port.accessVlan' else 'integer_list', parsed, field, 'VLAN')
                except ProjectValidationError:
                    issues.append(('INVALID_VLAN_VALUE', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                    continue
                decision = _decision_id([view_id, 'transformation', field,
                                         transformation['operation'], transformation['delimiter']], decision_ids)
                candidates.append((parsed, [src, origin('user_decision', decision_id=decision)]))
                continue
            if field in ('node.id', 'zone.id', 'port.id', 'port.nodeId', 'ip.nodeId', 'ip.portId',
                         'route.nodeId', 'route.id', 'route.outPort') and cell['type'] != 'text':
                if (view_id, row, field) not in row_values:
                    issues.append(('NUMERIC_ID_REQUIRES_DECISION', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                continue
            if field == 'port.enabled':
                if cell['type'] == 'boolean':
                    if mapped is not None:
                        issues.append(('BOOLEAN_MAPPING_TYPE_MISMATCH', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                    elif raw in ('true', '1'):
                        candidates.append((True, [src]))
                    elif raw in ('false', '0'):
                        candidates.append((False, [src]))
                    else:
                        issues.append(('BOOLEAN_SOURCE_TYPE', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                elif cell['type'] != 'text':
                    issues.append(('BOOLEAN_SOURCE_TYPE', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                else:
                    translated = mapped.get(raw) if mapped is not None else raw
                    if translated not in ('true', 'false'):
                        issues.append(('UNMAPPED_BOOLEAN', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                    else:
                        refs = [src]
                        if mapped is not None:
                            decision = _decision_id([view_id, 'valueMap', field, raw, translated], decision_ids)
                            refs.append(origin('user_decision', decision_id=decision))
                        candidates.append((translated == 'true', refs))
            elif mapped is not None:
                if raw not in mapped:
                    issues.append(('UNMAPPED_VALUE', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                    continue
                transformed = mapped[raw]
                decision = _decision_id([view_id, 'valueMap', field, raw, transformed], decision_ids)
                candidates.append((transformed, [src, origin('user_decision', decision_id=decision)]))
            elif cell['type'] == 'text':
                candidates.append((raw, [src]))
            else:
                issues.append(('SOURCE_TYPE_MISMATCH', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
        if field in view['constants']:
            item = view['constants'][field]
            decision = _decision_id([view_id, 'constant', field, item['type'], item['value']], decision_ids)
            candidates.append((item['value'], [origin('user_constant', decision_id=decision)]))
        if (view_id, row, field) in row_values:
            item = row_values[(view_id, row, field)]
            decision = _decision_id([view_id, row, field, item['valueType'], item['value']], decision_ids)
            candidates.append((item['value'], [origin('user_decision', decision_id=decision)]))
        if not candidates:
            if field == 'port.ipv4':
                ip_issues.extend(issues[issue_start:]); del issues[issue_start:]
            continue
        distinct = {canonical_json(value) for value, _ in candidates}
        all_origins = [entry for _, refs in candidates for entry in refs]
        if len(all_origins) > 128:
            fail('origins', 'more than 128 origins for field')
        if len(distinct) > 1:
            refs = [source_ref(item['sourceId'], item['tableId'], item['row'], item['address'])
                    for item in all_origins if item['kind'] == 'source_cell']
            origins[field] = sorted(all_origins, key=lambda item: canonical_json(item))
            issues.append(('FIELD_CONFLICT', 'BLOCKED', refs or [source_ref(source_id, table_id, row)]))
            if field == 'port.ipv4':
                ip_issues.extend(issues[issue_start:]); del issues[issue_start:]
            continue
        value = candidates[0][0]
        if field in ('port.ipv4', 'ip.ipv4'):
            try:
                value = _canonical_ipv4(value)
            except ProjectValidationError:
                refs = [source_ref(ref['sourceId'], ref['tableId'], ref['row'], ref['address'])
                        for ref in all_origins if ref['kind'] == 'source_cell']
                issues.append(('INVALID_IPV4', 'INVALID', refs or [source_ref(source_id, table_id, row)]))
                if field == 'port.ipv4':
                    ip_issues.extend(issues[issue_start:]); del issues[issue_start:]
                continue
        fields[field] = value
        origins[field] = sorted(all_origins, key=lambda item: canonical_json(item))
        if field == 'port.ipv4':
            ip_issues.extend(issues[issue_start:]); del issues[issue_start:]
    target_kind = ROLE_KIND[view['role']]
    if target_kind in ('port', 'ipBinding', 'staticRoute'):
        node_id, port_id = (fields.get('port.nodeId'), fields.get('port.id')) if target_kind == 'port' else (fields.get('ip.nodeId'), fields.get('ip.portId'))
        if target_kind == 'staticRoute':
            node_id, port_id = fields.get('route.nodeId'), fields.get('route.id')
        target_key = canonical_json([node_id, port_id]).decode('utf-8') if node_id is not None and port_id is not None else None
    else:
        target_key = fields.get(target_kind + '.id')
    if target_key is None:
        code = 'MISSING_PORT_IDENTITY' if target_kind in ('port', 'ipBinding') else 'MISSING_ROUTE_IDENTITY' if target_kind == 'staticRoute' else 'MISSING_' + target_kind.upper() + '_ID'
        issues.append((code, 'BLOCKED', [source_ref(source_id, table_id, row)]))
    claim_id = internal_id('cl-', [view_id, source_id, table_id, row, target_kind, target_key])
    claim = {'claimId': claim_id, 'viewId': view_id,
             'sourceRef': {'sourceId': source_id, 'tableId': table_id, 'row': row},
             'role': view['role'], 'targetKind': target_kind, 'targetKey': target_key,
             'fields': fields, 'origins': origins}
    result = [(claim, issues)]
    if target_kind == 'port' and ('port.ipv4' in fields or ip_issues):
        value = fields.pop('port.ipv4', None)
        refs = origins.pop('port.ipv4', [])
        ip_claim = {'claimId': internal_id('cl-', [view_id, source_id, table_id, row, 'ipBinding', target_key]),
                    'viewId': view_id, 'sourceRef': claim['sourceRef'], 'role': view['role'],
                    'targetKind': 'ipBinding', 'targetKey': target_key,
                    'fields': {'port.ipv4': value} if value is not None else {},
                    'origins': {'port.ipv4': refs} if value is not None else {}}
        result.append((ip_claim, ip_issues))
    return result, used


def node_layout(node_ids):
    """§8.2 layout, only for a unique, explicitly selected valid node set."""
    ids = sorted(set(node_ids))
    if len(ids) != len(node_ids) or len(ids) > 2000:
        fail('layout', 'duplicate node IDs or more than 2000 selected nodes')
    if not ids:
        return {}
    cols = 1 + math.isqrt(len(ids) - 1)
    return {node_id: (110 + 260 * (index % cols),
                      110 + 220 * (index // cols))
            for index, node_id in enumerate(ids)}


def _candidate(plan, project_name):
    selected = set(plan['selectedUnitIds'])
    units = [unit for unit in plan['units'] if unit['unitId'] in selected]
    all_units = {unit['unitId']: unit for unit in plan['units']}
    unavailable = [unit for unit in units if unit['status'] != 'ACTIONABLE' or
                   any(dep not in selected or all_units[dep]['status'] != 'ACTIONABLE'
                       for dep in unit['dependencies'])]
    if unavailable:
        for unit in unavailable:
            item = diagnostic('SELECTED_UNIT_NOT_ACTIONABLE', [], unit['unitId'])
            unit['diagnostics'].append(item)
            plan['diagnostics'].append(item)
        plan['diagnostics'].sort(key=lambda d: (d['code'], d['unitId'] or '', canonical_json(d['sourceRefs'])))
        return
    if not units:
        return
    coordinates = node_layout([unit['targetKey'] for unit in units if unit['kind'] == 'node'])
    if not coordinates:
        return
    claims_by_target = {}
    selected_targets = {(unit['kind'], unit['targetKey']) for unit in units}
    for claim in plan['claims']:
        if (claim['targetKind'], claim['targetKey']) in selected_targets:
            claims_by_target.setdefault((claim['targetKind'], claim['targetKey']), []).append(claim)
    nodes, zones = [], []
    accepted = []
    derived = origin('derived_layout')
    for unit in sorted(units, key=lambda item: ({'zone': 0, 'node': 1, 'port': 2,
                                                'ipBinding': 3, 'staticRoute': 4}[item['kind']], item['targetKey'])):
        target, kind = unit['targetKey'], unit['kind']
        group = claims_by_target[(kind, target)]
        facts = {}
        provenance = {}
        for claim in group:
            for field, value in claim['fields'].items():
                if kind == 'ipBinding':
                    if field in ('ip.nodeId', 'ip.portId'):
                        continue
                    facts['port.ipv4'] = value
                    provenance.setdefault('port.ipv4', []).extend(claim['origins'][field])
                else:
                    facts[field] = value
                    prefix = 'route.' if kind == 'staticRoute' else kind + '.'
                    provenance.setdefault(field.removeprefix(prefix), []).extend(claim['origins'][field])
        if kind == 'zone':
            zone = {'id': facts['zone.id'], 'label': facts['zone.label']}
            zone = validate_project({'schemaVersion': '1.3', 'name': project_name,
                                     'zones': [zone], 'nodes': [], 'links': []})['zones'][0]
            fields = zone
            zones.append(zone)
        elif kind == 'node':
            x, y = coordinates[target]
            node = {'id': facts['node.id'], 'label': facts['node.label'],
                    'kind': facts['node.kind'], 'x': x, 'y': y,
                    'zoneId': facts.get('node.zoneId'), 'ports': []}
            node = validate_project({'schemaVersion': '1.3', 'name': project_name,
                                     'zones': zones, 'nodes': [node], 'links': []})['nodes'][0]
            provenance['x'] = [derived]
            provenance['y'] = [derived]
            provenance.setdefault('zoneId', [])
            provenance['ports'] = []
            fields = node
            nodes.append(node)
        elif kind == 'port':
            owner_id = facts['port.nodeId']
            owner = next(n for n in nodes if n['id'] == owner_id)
            port = {'id': facts['port.id'], 'name': facts['port.name'],
                    'enabled': facts['port.enabled'], 'ipv4': None}
            vlan_fields = {'port.vlanMode', 'port.accessVlan', 'port.allowedVlans'}
            if vlan_fields & facts.keys():
                mode = facts['port.vlanMode']
                port['vlan'] = ({'mode': 'access', 'vlan': facts['port.accessVlan']}
                                if mode == 'access' else
                                {'mode': 'trunk', 'allowedVlans': facts['port.allowedVlans']})
                provenance['vlan'] = sorted((ref for key in vlan_fields
                                             for ref in provenance.pop(key.removeprefix('port.'), [])),
                                            key=canonical_json)
            owner['ports'].append(port)
            provenance['ipv4'] = []
            fields = {'nodeId': owner_id, **port}
        elif kind == 'ipBinding':
            node_id, port_id = json.loads(target)
            owner = next(n for n in nodes if n['id'] == node_id)
            port = next(p for p in owner['ports'] if p['id'] == port_id)
            port['ipv4'] = facts['port.ipv4']
            fields = {'port.ipv4': facts['port.ipv4']}
            provenance['port.ipv4'] = sorted(provenance['port.ipv4'], key=canonical_json)
        else:
            node_id, route_id = json.loads(target)
            owner = next(n for n in nodes if n['id'] == node_id)
            route = {'id': route_id, 'destination': facts['route.destination'],
                     'nextHop': facts['route.nextHop'], 'outPort': facts['route.outPort']}
            owner.setdefault('staticRoutes', []).append(route)
            fields = {'nodeId': node_id, **route}
        for field in (('id', 'label', 'kind') if kind == 'node' else
                      ('nodeId', 'id', 'name', 'enabled') if kind == 'port' else
                      ('id', 'label') if kind == 'zone' else
                      ('nodeId', 'id', 'destination', 'nextHop', 'outPort') if kind == 'staticRoute' else ()):
            provenance[field] = sorted(provenance[field], key=canonical_json)
        operation = 'setExplicitField' if kind == 'ipBinding' else 'create'
        change_id = internal_id('c-', [unit['unitId'], operation,
                                       'port.ipv4' if kind == 'ipBinding' else '__object__'])
        change = {'changeId': change_id, 'operation': operation,
                  'targetKind': kind, 'targetKey': target,
                  'fieldValues': deepcopy(fields), 'fieldOrigins': deepcopy(provenance)}
        unit['changes'] = [change]
        accepted.append({'unitId': unit['unitId'], 'changeIds': [change_id],
                         'targetKind': kind, 'targetKey': target,
                         'fieldValues': deepcopy(fields), 'fieldOrigins': deepcopy(provenance)})
    for node in nodes:
        node['ports'].sort(key=lambda port: port['id'])
        if 'staticRoutes' in node:
            node['staticRoutes'].sort(key=lambda route: route['id'])
    nodes.sort(key=lambda node: node['id'])
    zones.sort(key=lambda zone: zone['id'])
    accepted.sort(key=lambda change: change['unitId'])
    draft = validate_project({'schemaVersion': '1.3', 'name': project_name,
                              'zones': zones, 'nodes': nodes, 'links': []})
    baseline = hashlib.sha256(canonical_json(canonical_network_view(draft))).hexdigest()
    decisions = []
    for review in plan['recordReviews']:
        uses = review['viewUses'] or [{'viewId': None, 'status': 'DOCUMENTATION_ONLY',
                                       'reason': None, 'unitIds': []}]
        for use in uses:
            decisions.append({'sourceId': review['sourceId'], 'tableId': review['tableId'],
                              'row': review['row'], 'viewId': use['viewId'],
                              'status': use['status'], 'reason': use['reason'],
                              'unitIds': use['unitIds']})
    evidence = {'evidenceVersion': '1', 'contractVersion': '1',
                'projectNameAtImport': project_name, 'planFingerprint': plan['fingerprint'],
                'baselineNetworkSha256': baseline, 'selectedUnitIds': plan['selectedUnitIds'],
                'excludedUses': plan['excludedUses'], 'transformations': plan['transformations'],
                'sources': plan['sourceManifest'], 'mappingViews': plan['mappingViews'],
                'rowValues': plan['rowValues'], 'decisions': decisions,
                'acceptedChanges': accepted, 'sourceStorage': 'external_not_embedded'}
    candidate = {**draft, 'schemaVersion': '1.4', 'importEvidence': evidence}
    plan['proposedProject'] = validate_project(candidate)
    plan['canApply'] = True


def build_plan(value):
    """Build a read-only discovery response from actual source bytes and explicit decisions."""
    object_exact(value, REQUEST_KEYS, 'request')
    if value['contractVersion'] != '1':
        fail('contractVersion', 'expected 1')
    _metadata_only(value)
    project_name = _name(value['projectName'], 'projectName')
    if len(canonical_json(value)) > 8 * 1024 * 1024:
        fail('request', 'PAYLOAD_LIMIT: JSON request exceeds 8 MiB')
    manifest, tables = _sources(value['sources'])
    views = _views(value['mappingViews'], tables)
    row_values, excluded, selected, transformations = _decisions(value, views)
    row_value_map = {(r['viewId'], r['row'], r['targetField']): r for r in row_values}
    exclusions = {(e['viewId'], e['row']): e['reason'] for e in excluded}
    fingerprint_input = {'contractVersion': '1', 'projectName': project_name,
                         'validatorVersion': '1.4',
                         'sources': [{'sourceId': s['sourceId'], 'sha256': s['sha256'],
                                      'csvDelimiter': s['csvDelimiter']} for s in manifest],
                         'mappingViews': views, 'transformations': transformations,
                         'rowValues': row_values, 'excludedUses': excluded,
                         'selectedUnitIds': selected}
    fingerprint = hashlib.sha256(canonical_json(fingerprint_input)).hexdigest()
    reviews = {}
    for (source_id, table_id), table in tables.items():
        for row, cells in table['rows'].items():
            reviews[(source_id, table_id, row)] = {
                'sourceId': source_id, 'tableId': table_id, 'row': row,
                'viewUses': [], 'unmappedAddresses': {cell['address'] for cell in cells}}
    claims, issues_by_claim, decision_ids = [], {}, {}
    for view in views:
        for row in view['selectedRows']:
            key = (view['sourceId'], view['tableId'], row)
            review = reviews[key]
            reason = exclusions.get((view['viewId'], row))
            if reason is not None:
                review['viewUses'].append({'viewId': view['viewId'], 'claimIds': [],
                                           'unitIds': [], 'status': 'EXCLUDED', 'reason': reason})
                continue
            if view['role'] == 'documentation_only':
                review['viewUses'].append({'viewId': view['viewId'], 'claimIds': [],
                                           'unitIds': [], 'status': 'DOCUMENTATION_ONLY', 'reason': None})
                continue
            claim_pairs, used = _claim(view, row, tables[key[:2]]['rows'][row],
                                       row_value_map, decision_ids,
                                       {(t['viewId'], t['targetField']): t for t in transformations})
            for claim, issues in claim_pairs:
                claims.append(claim)
                issues_by_claim[claim['claimId']] = issues
            review['unmappedAddresses'] -= used
            review['viewUses'].append({'viewId': view['viewId'], 'claimIds': [c['claimId'] for c, _ in claim_pairs],
                                       'unitIds': [], 'status': 'BLOCKED' if any(i for _, i in claim_pairs) else 'ACTIONABLE',
                                       'reason': None})
    if len(claims) > 20000:
        fail('claims', 'more than 20000 claims')
    claim_ids = [claim['claimId'] for claim in claims]
    if len(set(claim_ids)) != len(claim_ids):
        fail('claims', 'internal claimId collision')
    grouped = {}
    for claim in claims:
        if claim['targetKey'] is not None:
            grouped.setdefault((claim['targetKind'], claim['targetKey']), []).append(claim)
    if len(grouped) > 10000:
        fail('units', 'more than 10000 units')
    units, diagnostics = [], []
    unit_ids = {}
    for (kind, target), group in sorted(grouped.items()):
        unit_id = internal_id('u-', [kind, target])
        if unit_id in unit_ids and unit_ids[unit_id] != (kind, target):
            fail('units', 'internal unitId collision')
        unit_ids[unit_id] = (kind, target)
        combined = {}
        origins = {}
        problems = []
        for claim in group:
            for field, item in claim['fields'].items():
                canonical_field = 'port.ipv4' if kind == 'ipBinding' and field == 'ip.ipv4' else field
                if kind == 'ipBinding' and field in ('ip.nodeId', 'ip.portId'):
                    continue
                combined.setdefault(canonical_field, []).append(item)
                origins.setdefault(canonical_field, []).extend(claim['origins'][field])
            problems.extend(issues_by_claim[claim['claimId']])
        for field, values in combined.items():
            if len({canonical_json(item) for item in values}) > 1:
                refs = [source_ref(o['sourceId'], o['tableId'], o['row'], o['address'])
                        for o in origins[field] if o['kind'] == 'source_cell']
                problems.append(('FIELD_CONFLICT', 'BLOCKED', refs))
            if len(origins[field]) > 128:
                fail('origins', 'more than 128 origins for field')
        if not any(p[0] == 'FIELD_CONFLICT' for p in problems):
            for required in (('node.label', 'node.kind') if kind == 'node' else
                             ('port.nodeId', 'port.id', 'port.name', 'port.enabled') if kind == 'port' else
                             ('port.ipv4',) if kind == 'ipBinding' else
                             ('route.nodeId', 'route.id', 'route.destination', 'route.nextHop', 'route.outPort') if kind == 'staticRoute' else
                             ('zone.label',)):
                if required not in combined:
                    problems.append(('MISSING_REQUIRED_FIELD', 'BLOCKED',
                                     [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
            for field in (('node.id', 'node.label', 'node.kind') if kind == 'node' else
                          ('port.nodeId', 'port.id', 'port.name', 'port.enabled') if kind == 'port' else
                          ('zone.id', 'zone.label')):
                if field not in combined:
                    continue
                item = combined[field][0]
                try:
                    if field in ('node.id', 'zone.id', 'port.id', 'port.nodeId'):
                        _id(item, field)
                    elif field in ('node.label', 'zone.label', 'port.name'):
                        _name(item, field)
                    elif field == 'port.enabled':
                        if type(item) is not bool:
                            raise ProjectValidationError('invalid port.enabled')
                    elif item not in NODE_KINDS:
                        raise ProjectValidationError('invalid node.kind')
                except ProjectValidationError:
                    refs = [source_ref(o['sourceId'], o['tableId'], o['row'], o['address'])
                            for o in origins[field] if o['kind'] == 'source_cell']
                    problems.append(('INVALID_' + field.upper().replace('.', '_'), 'INVALID',
                                     refs or [source_ref(c['sourceRef']['sourceId'],
                                                         c['sourceRef']['tableId'], c['sourceRef']['row'])
                                              for c in group]))
            if kind == 'port' and 'port.nodeId' in combined:
                owner = combined['port.nodeId'][0]
                if ('node', owner) not in grouped:
                    problems.append(('UNDECLARED_NODE', 'BLOCKED',
                                     [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
                vlan_fields = {'port.vlanMode', 'port.accessVlan', 'port.allowedVlans'}
                if vlan_fields & combined.keys():
                    mode = combined.get('port.vlanMode', [None])[0]
                    valid = ((mode == 'access' and 'port.accessVlan' in combined and 'port.allowedVlans' not in combined) or
                             (mode == 'trunk' and 'port.allowedVlans' in combined and 'port.accessVlan' not in combined))
                    owner_claims = grouped.get(('node', owner), [])
                    switch = any(c['fields'].get('node.kind') == 'switch' for c in owner_claims)
                    if not valid or not switch:
                        problems.append(('INVALID_VLAN_COMBINATION' if not valid else 'VLAN_REQUIRES_SWITCH', 'BLOCKED',
                                         [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
            if kind == 'ipBinding' and ('port', target) not in grouped:
                problems.append(('UNDECLARED_PORT', 'BLOCKED',
                                 [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
            if kind == 'ipBinding':
                try:
                    node_id, port_id = json.loads(target)
                    _id(node_id, 'ip.nodeId'); _id(port_id, 'ip.portId')
                except (ValueError, TypeError, ProjectValidationError):
                    problems.append(('INVALID_IP_IDENTITY', 'INVALID',
                                     [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
            if kind == 'staticRoute':
                try:
                    node_id, route_id = json.loads(target)
                    _id(node_id, 'route.nodeId'); _id(route_id, 'route.id')
                except (ValueError, TypeError, ProjectValidationError):
                    problems.append(('INVALID_ROUTE_IDENTITY', 'INVALID',
                                     [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
                else:
                    refs = [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]
                    owner_claims = grouped.get(('node', node_id), [])
                    if not owner_claims:
                        problems.append(('UNDECLARED_NODE', 'BLOCKED', refs))
                    elif any(c['fields'].get('node.kind') == 'switch' for c in owner_claims):
                        problems.append(('ROUTE_REQUIRES_L3_NODE', 'INVALID', refs))
                    port_id = combined.get('route.outPort', [None])[0]
                    port_key = canonical_json([node_id, port_id]).decode('utf-8') if port_id is not None else None
                    if port_key is not None and ('port', port_key) not in grouped:
                        problems.append(('UNDECLARED_PORT', 'BLOCKED', refs))
                    bindings = grouped.get(('ipBinding', port_key), []) if port_key else []
                    if port_key is not None and not bindings:
                        problems.append(('MISSING_PORT_IPV4', 'BLOCKED', refs))
                    ip_values = [c['fields'].get('ip.ipv4', c['fields'].get('port.ipv4'))
                                 for c in bindings]
                    if not problems and all(key in combined for key in
                                            ('route.id', 'route.destination', 'route.nextHop', 'route.outPort')) and ip_values and ip_values[0]:
                        try:
                            _static_route({'id': route_id,
                                           'destination': combined['route.destination'][0],
                                           'nextHop': combined['route.nextHop'][0],
                                           'outPort': port_id}, 'import.route',
                                          {port_id: {'ipv4': ip_values[0]}})
                        except ProjectValidationError as error:
                            detail = str(error)
                            field = ('route.destination' if '.destination' in detail else
                                     'route.nextHop' if '.nextHop' in detail else
                                     'route.outPort' if '.outPort' in detail else 'route.id')
                            cells = [source_ref(o['sourceId'], o['tableId'], o['row'], o['address'])
                                     for o in origins.get(field, []) if o['kind'] == 'source_cell']
                            problems.append(('INVALID_' + field.upper().replace('.', '_'),
                                             'INVALID', cells or refs))
            if kind == 'node' and combined.get('node.zoneId', [None])[0] is not None:
                zone_key = combined['node.zoneId'][0]
                zone_group = grouped.get(('zone', zone_key))
                if not zone_group:
                    problems.append(('UNDECLARED_ZONE', 'BLOCKED',
                                     [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
        status = 'INVALID' if any(p[1] == 'INVALID' for p in problems) else 'BLOCKED' if problems else 'ACTIONABLE'
        for code, _, refs in problems:
            diagnostics.append(diagnostic(code, refs, unit_id))
        uses = []
        seen_fields = set()
        for claim in group:
            ref = claim['sourceRef']
            uses.append({'viewId': claim['viewId'], **ref, 'claimId': claim['claimId']})
            review_use = next(u for u in reviews[(ref['sourceId'], ref['tableId'], ref['row'])]['viewUses']
                              if u['viewId'] == claim['viewId'])
            review_use['unitIds'] = sorted(set(review_use['unitIds']) | {unit_id})
            adds_facts = bool(set(claim['fields']) - seen_fields)
            if status != 'ACTIONABLE':
                review_use['status'] = status
            elif review_use['status'] not in ('BLOCKED', 'INVALID'):
                review_use['status'] = 'ACTIONABLE' if adds_facts else 'NO_OP'
            seen_fields.update(claim['fields'])
        if len(uses) > 128:
            fail('units', 'more than 128 source uses for one unit')
        dependencies = []
        if kind == 'node' and combined.get('node.zoneId', [None])[0] is not None:
            zone_key = combined['node.zoneId'][0]
            if ('zone', zone_key) in grouped:
                dependencies = [internal_id('u-', ['zone', zone_key])]
        elif kind == 'port' and 'port.nodeId' in combined:
            if ('node', combined['port.nodeId'][0]) in grouped:
                dependencies = [internal_id('u-', ['node', combined['port.nodeId'][0]])]
        elif kind == 'ipBinding' and ('port', target) in grouped:
            dependencies = [internal_id('u-', ['port', target])]
        elif kind == 'staticRoute' and 'route.outPort' in combined:
            node_id = json.loads(target)[0]
            port_key = canonical_json([node_id, combined['route.outPort'][0]]).decode('utf-8')
            dependencies = sorted(internal_id('u-', [dep_kind, dep_key])
                                  for dep_kind, dep_key in (('node', node_id), ('port', port_key),
                                                             ('ipBinding', port_key))
                                  if (dep_kind, dep_key) in grouped)
        units.append({'unitId': unit_id, 'kind': kind, 'targetKey': target,
                      'changes': [], 'dependencies': dependencies, 'status': status,
                      'diagnostics': [d for d in diagnostics if d['unitId'] == unit_id],
                      'sourceUses': sorted(uses, key=lambda u: (u['viewId'], u['sourceId'], u['tableId'], u['row']))})
    by_unit_id = {unit['unitId']: unit for unit in units}
    route_facts = {}
    for unit in units:
        if unit['kind'] != 'staticRoute' or unit['status'] != 'ACTIONABLE':
            continue
        facts = {field: value for claim in grouped[('staticRoute', unit['targetKey'])]
                 for field, value in claim['fields'].items()}
        key = (facts['route.nodeId'], facts['route.destination'], facts['route.nextHop'],
               facts['route.outPort'])
        route_facts.setdefault(key, []).append(unit)
    for duplicates in route_facts.values():
        if len(duplicates) < 2:
            continue
        for unit in duplicates:
            item = diagnostic('DUPLICATE_STATIC_ROUTE', [], unit['unitId'])
            unit['status'] = 'BLOCKED'
            unit['diagnostics'].append(item)
            diagnostics.append(item)
            for use in unit['sourceUses']:
                review_use = next(u for u in reviews[(use['sourceId'], use['tableId'], use['row'])]['viewUses']
                                  if u['viewId'] == use['viewId'])
                review_use['status'] = 'BLOCKED'
    for unit in units:
        if unit['kind'] not in ('ipBinding', 'staticRoute') or unit['status'] != 'ACTIONABLE':
            continue
        if any(by_unit_id[dep]['status'] != 'ACTIONABLE' for dep in unit['dependencies']):
            item = diagnostic('UNAVAILABLE_ROUTE_DEPENDENCY' if unit['kind'] == 'staticRoute' else 'UNAVAILABLE_PORT', [], unit['unitId'])
            unit['status'] = 'BLOCKED'
            unit['diagnostics'].append(item)
            diagnostics.append(item)
            for use in unit['sourceUses']:
                review_use = next(u for u in reviews[(use['sourceId'], use['tableId'], use['row'])]['viewUses']
                                  if u['viewId'] == use['viewId'])
                review_use['status'] = 'BLOCKED'
    for claim in claims:
        if claim['targetKey'] is None:
            ref = claim['sourceRef']
            for code, _, refs in issues_by_claim[claim['claimId']]:
                diagnostics.append(diagnostic(code, refs))
    if selected and any(item not in unit_ids for item in selected):
        fail('selectedUnitIds', 'unknown unit ID')
    review_list = []
    for review in reviews.values():
        review['viewUses'].sort(key=lambda use: use['viewId'])
        review['unmappedAddresses'] = sorted(review['unmappedAddresses'])
        review_list.append(review)
    review_list.sort(key=lambda r: (r['sourceId'], r['tableId'], r['row']))
    if len(review_list) > 10000:
        fail('recordReviews', 'more than 10000 records')
    claims.sort(key=lambda c: (c['viewId'], c['sourceRef']['sourceId'], c['sourceRef']['tableId'],
                                c['sourceRef']['row'], c['targetKind'], c['targetKey'] or ''))
    diagnostics.sort(key=lambda d: (d['code'], d['unitId'] or '', canonical_json(d['sourceRefs'])))
    if len(diagnostics) > 20000:
        fail('diagnostics', 'more than 20000 diagnostics')
    dispositions = [use['status'] for review in review_list for use in review['viewUses']]
    report = {'sourceRows': len(review_list), 'sourceUses': len(dispositions),
              'actionable': dispositions.count('ACTIONABLE'), 'noOp': dispositions.count('NO_OP'),
              'blocked': dispositions.count('BLOCKED'), 'invalid': dispositions.count('INVALID'),
              'excluded': dispositions.count('EXCLUDED'),
              'unmappedCells': sum(len(r['unmappedAddresses']) for r in review_list),
              'selectedUnits': len(selected),
              'nodes': sum(u['kind'] == 'node' and u['status'] == 'ACTIONABLE' for u in units),
              'ports': sum(u['kind'] == 'port' and u['status'] == 'ACTIONABLE' for u in units),
              'links': 0, 'zones': sum(u['kind'] == 'zone' and u['status'] == 'ACTIONABLE' for u in units), 'routes': 0}
    plan = {'planVersion': '1', 'fingerprint': fingerprint, 'sourceManifest': manifest,
            'mappingViews': views, 'transformations': transformations, 'rowValues': row_values,
            'excludedUses': excluded, 'selectedUnitIds': selected, 'claims': claims,
            'units': units, 'recordReviews': review_list, 'diagnostics': diagnostics,
            'report': report, 'proposedProject': None, 'canApply': False}
    if selected:
        _candidate(plan, project_name)
    result = {'plan': plan}
    if len(canonical_json(result)) > 8 * 1024 * 1024:
        fail('response', 'PLAN_TOO_LARGE: serialized plan exceeds 8 MiB')
    return result
