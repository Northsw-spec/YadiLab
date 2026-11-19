"""Deterministic, read-only source claims and selected import candidates."""
from __future__ import annotations

import hashlib
import json
import math
import re

from .import_inspection import _decode_source, inspect_all_rows
from .model import (ProjectValidationError, NODE_KINDS, _id, _name,
                    validate_project, canonical_network_view)

FIELDS = frozenset({'node.id', 'node.label', 'node.kind', 'node.zoneId'})
ROLES = {'device_inventory': FIELDS, 'documentation_only': frozenset()}
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
    if value_type == 'text' and type(value) is str:
        return value
    if value_type == 'null' and value is None and field == 'node.zoneId':
        return None
    fail(where, 'unsupported or incorrectly typed user value')


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
            fail('mappingViews', f'role {role!r} not implemented in 4B2')
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
        constants = view['constants']
        if type(constants) is not dict or set(constants) & set(columns) or not set(constants) <= (ROLES[role] - {'node.id'}):
            fail('mappingViews', 'invalid constants or identity constant')
        for field, item in constants.items():
            object_exact(item, {'type', 'value'}, f'constant {field}')
            _typed_value(item['type'], item['value'], field, f'constant {field}')
        if type(view['label']) is not str or len(view['label']) > 240:
            fail('mappingViews', 'invalid label')
    return views


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
    if bounded_list(value['transformations'], 64, 'transformations'):
        fail('transformations', 'no supported transformation for the implemented roles')
    selected = bounded_list(value['selectedUnitIds'], 10000, 'selectedUnitIds')
    if any(type(x) is not str for x in selected) or selected != sorted(set(selected)):
        fail('selectedUnitIds', 'expected sorted unique unit IDs')
    return (sorted(row_values, key=lambda r: (r['viewId'], r['row'], r['targetField'])),
            sorted(excluded, key=lambda e: (e['viewId'], e['row'])), selected)


def _claim(view, row, cells, row_values, decision_ids):
    source_id, table_id, view_id = view['sourceId'], view['tableId'], view['viewId']
    by_column = {re.match(r'[A-Z]+', c['address']).group(): c for c in cells}
    fields, origins, issues, used = {}, {}, [], set()
    for field in sorted(set(view['columns']) | set(view['constants']) |
                        {key[2] for key in row_values if key[:2] == (view_id, row)}):
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
            if field == 'node.id' and cell['type'] != 'text':
                if (view_id, row, field) not in row_values:
                    issues.append(('NUMERIC_ID_REQUIRES_DECISION', 'BLOCKED', [source_ref(source_id, table_id, row, cell['address'])]))
                continue
            if mapped is not None:
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
            continue
        fields[field] = candidates[0][0]
        origins[field] = sorted(all_origins, key=lambda item: canonical_json(item))
    target_key = fields.get('node.id')
    if target_key is None:
        issues.append(('MISSING_NODE_ID', 'BLOCKED', [source_ref(source_id, table_id, row)]))
    claim_id = internal_id('cl-', [view_id, source_id, table_id, row, 'node', target_key])
    claim = {'claimId': claim_id, 'viewId': view_id,
             'sourceRef': {'sourceId': source_id, 'tableId': table_id, 'row': row},
             'role': 'device_inventory', 'targetKind': 'node', 'targetKey': target_key,
             'fields': fields, 'origins': origins}
    return claim, issues, used


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
    unavailable = [unit for unit in units if unit['status'] != 'ACTIONABLE' or
                   any(dep not in selected for dep in unit['dependencies'])]
    if unavailable:
        for unit in unavailable:
            item = diagnostic('SELECTED_UNIT_NOT_ACTIONABLE', [], unit['unitId'])
            unit['diagnostics'].append(item)
            plan['diagnostics'].append(item)
        plan['diagnostics'].sort(key=lambda d: (d['code'], d['unitId'] or '', canonical_json(d['sourceRefs'])))
        return
    if not units:
        return
    coordinates = node_layout([unit['targetKey'] for unit in units])
    claims_by_target = {}
    for claim in plan['claims']:
        if claim['targetKey'] in coordinates:
            claims_by_target.setdefault(claim['targetKey'], []).append(claim)
    nodes = []
    accepted = []
    derived = origin('derived_layout')
    for unit in sorted(units, key=lambda item: item['unitId']):
        target = unit['targetKey']
        group = claims_by_target[target]
        facts = {}
        provenance = {}
        for claim in group:
            for field, value in claim['fields'].items():
                facts[field] = value
                provenance.setdefault(field.removeprefix('node.'), []).extend(claim['origins'][field])
        x, y = coordinates[target]
        node = {'id': facts['node.id'], 'label': facts['node.label'],
                'kind': facts['node.kind'], 'x': x, 'y': y,
                'zoneId': facts.get('node.zoneId'), 'ports': []}
        node = validate_project({'schemaVersion': '1.3', 'name': project_name,
                                 'zones': [], 'nodes': [node], 'links': []})['nodes'][0]
        for field in ('id', 'label', 'kind'):
            provenance[field] = sorted(provenance[field], key=canonical_json)
        provenance['x'] = [derived]
        provenance['y'] = [derived]
        provenance.setdefault('zoneId', [])
        provenance['ports'] = []
        change_id = internal_id('c-', [unit['unitId'], 'create', '__object__'])
        change = {'changeId': change_id, 'operation': 'create',
                  'targetKind': 'node', 'targetKey': target,
                  'fieldValues': node, 'fieldOrigins': provenance}
        unit['changes'] = [change]
        accepted.append({'unitId': unit['unitId'], 'changeIds': [change_id],
                         'targetKind': 'node', 'targetKey': target,
                         'fieldValues': node, 'fieldOrigins': provenance})
        nodes.append(node)
    nodes.sort(key=lambda node: node['id'])
    draft = validate_project({'schemaVersion': '1.3', 'name': project_name,
                              'zones': [], 'nodes': nodes, 'links': []})
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
    row_values, excluded, selected = _decisions(value, views)
    row_value_map = {(r['viewId'], r['row'], r['targetField']): r for r in row_values}
    exclusions = {(e['viewId'], e['row']): e['reason'] for e in excluded}
    fingerprint_input = {'contractVersion': '1', 'projectName': project_name,
                         'validatorVersion': '1.4',
                         'sources': [{'sourceId': s['sourceId'], 'sha256': s['sha256'],
                                      'csvDelimiter': s['csvDelimiter']} for s in manifest],
                         'mappingViews': views, 'transformations': [],
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
            claim, issues, used = _claim(view, row, tables[key[:2]]['rows'][row],
                                         row_value_map, decision_ids)
            claims.append(claim)
            issues_by_claim[claim['claimId']] = issues
            review['unmappedAddresses'] -= used
            review['viewUses'].append({'viewId': view['viewId'], 'claimIds': [claim['claimId']],
                                       'unitIds': [], 'status': 'BLOCKED' if issues else 'ACTIONABLE',
                                       'reason': None})
    if len(claims) > 20000:
        fail('claims', 'more than 20000 claims')
    claim_ids = [claim['claimId'] for claim in claims]
    if len(set(claim_ids)) != len(claim_ids):
        fail('claims', 'internal claimId collision')
    grouped = {}
    for claim in claims:
        if claim['targetKey'] is not None:
            grouped.setdefault(claim['targetKey'], []).append(claim)
    if len(grouped) > 10000:
        fail('units', 'more than 10000 units')
    units, diagnostics = [], []
    unit_ids = {}
    for target, group in sorted(grouped.items()):
        unit_id = internal_id('u-', ['node', target])
        if unit_id in unit_ids and unit_ids[unit_id] != target:
            fail('units', 'internal unitId collision')
        unit_ids[unit_id] = target
        combined = {}
        origins = {}
        problems = []
        for claim in group:
            for field, item in claim['fields'].items():
                combined.setdefault(field, []).append(item)
                origins.setdefault(field, []).extend(claim['origins'][field])
            problems.extend(issues_by_claim[claim['claimId']])
        for field, values in combined.items():
            if len({canonical_json(item) for item in values}) > 1:
                refs = [source_ref(o['sourceId'], o['tableId'], o['row'], o['address'])
                        for o in origins[field] if o['kind'] == 'source_cell']
                problems.append(('FIELD_CONFLICT', 'BLOCKED', refs))
            if len(origins[field]) > 128:
                fail('origins', 'more than 128 origins for field')
        if not any(p[0] == 'FIELD_CONFLICT' for p in problems):
            for required in ('node.label', 'node.kind'):
                if required not in combined:
                    problems.append(('MISSING_REQUIRED_FIELD', 'BLOCKED',
                                     [source_ref(c['sourceRef']['sourceId'], c['sourceRef']['tableId'], c['sourceRef']['row']) for c in group]))
            for field in ('node.id', 'node.label', 'node.kind'):
                if field not in combined:
                    continue
                item = combined[field][0]
                try:
                    if field == 'node.id':
                        _id(item, field)
                    elif field == 'node.label':
                        _name(item, field)
                    elif item not in NODE_KINDS:
                        raise ProjectValidationError('invalid node.kind')
                except ProjectValidationError:
                    refs = [source_ref(o['sourceId'], o['tableId'], o['row'], o['address'])
                            for o in origins[field] if o['kind'] == 'source_cell']
                    problems.append(('INVALID_' + field.upper().replace('.', '_'), 'INVALID',
                                     refs or [source_ref(c['sourceRef']['sourceId'],
                                                         c['sourceRef']['tableId'], c['sourceRef']['row'])
                                              for c in group]))
            if combined.get('node.zoneId', [None])[0] is not None:
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
            review_use['unitIds'] = [unit_id]
            adds_facts = bool(set(claim['fields']) - seen_fields)
            review_use['status'] = status if status != 'ACTIONABLE' else 'ACTIONABLE' if adds_facts else 'NO_OP'
            seen_fields.update(claim['fields'])
        if len(uses) > 128:
            fail('units', 'more than 128 source uses for one unit')
        units.append({'unitId': unit_id, 'kind': 'node', 'targetKey': target,
                      'changes': [], 'dependencies': [], 'status': status,
                      'diagnostics': [d for d in diagnostics if d['unitId'] == unit_id],
                      'sourceUses': sorted(uses, key=lambda u: (u['viewId'], u['sourceId'], u['tableId'], u['row']))})
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
              'ports': 0, 'links': 0, 'zones': 0, 'routes': 0}
    plan = {'planVersion': '1', 'fingerprint': fingerprint, 'sourceManifest': manifest,
            'mappingViews': views, 'transformations': [], 'rowValues': row_values,
            'excludedUses': excluded, 'selectedUnitIds': selected, 'claims': claims,
            'units': units, 'recordReviews': review_list, 'diagnostics': diagnostics,
            'report': report, 'proposedProject': None, 'canApply': False}
    if selected:
        _candidate(plan, project_name)
    result = {'plan': plan}
    if len(canonical_json(result)) > 8 * 1024 * 1024:
        fail('response', 'PLAN_TOO_LARGE: serialized plan exceeds 8 MiB')
    return result
