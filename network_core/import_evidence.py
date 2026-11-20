"""Validation of immutable, compact historical import receipts.

The receipt is checked against its own manifest, never against the editable
current network or unavailable original source bytes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from .import_plan import (canonical_json, internal_id, node_layout, object_exact, bounded_list,
                          column_index, fail, FIELDS, ROLES, VIEW_KEYS, _transformations, _typed_value)
from .model import _id, _name, validate_project, canonical_network_view

EVIDENCE_KEYS = {'evidenceVersion', 'contractVersion', 'projectNameAtImport',
                 'planFingerprint', 'baselineNetworkSha256', 'selectedUnitIds',
                 'excludedUses', 'transformations', 'sources', 'mappingViews',
                 'rowValues', 'decisions', 'acceptedChanges', 'sourceStorage'}
SHA = re.compile(r'[0-9a-f]{64}\Z')
UNIT_ID = re.compile(r'u-[0-9a-f]{32}\Z')
ORIGIN_KEYS = {'kind', 'sourceId', 'tableId', 'row', 'address', 'decisionId'}
NODE_FIELDS = {'id', 'label', 'kind', 'x', 'y', 'zoneId', 'ports'}
ZONE_FIELDS = {'id', 'label'}
PORT_FIELDS = {'nodeId', 'id', 'name', 'enabled', 'ipv4'}
VLAN_FIELDS = {'vlanMode', 'accessVlan', 'allowedVlans'}


def _array(value, maximum, where):
    return bounded_list(value, maximum, where)


def _sha(value, where):
    if type(value) is not str or not SHA.fullmatch(value):
        fail(where, 'expected lowercase SHA-256')


def _sorted_unique(items, where):
    if any(type(item) is not str for item in items) or items != sorted(set(items)):
        fail(where, 'expected sorted unique IDs')


def _remember_decision(registry, payload, kind, field):
    identifier = internal_id('d-', payload)
    row = payload[1] if type(payload[1]) is int else None
    meaning = (kind, field.split('.', 1)[-1], canonical_json(payload), payload[0], row)
    if identifier in registry and registry[identifier] != meaning:
        fail('decisions', 'decision ID collision')
    registry[identifier] = meaning


def _origin(item, tables, decisions, where, *, field=None, views=(), unit=None,
            historical_units=None, target_kind='node'):
    object_exact(item, ORIGIN_KEYS, where)
    kind = item['kind']
    if kind == 'source_cell':
        key = (item['sourceId'], item['tableId'])
        table = tables.get(key)
        address = item['address']
        if (table is None or type(item['row']) is not int or
                not 1 <= item['row'] <= table['rowCount'] or
                type(address) is not str or
                not re.fullmatch(r'[A-Z]{1,2}[1-9][0-9]*', address) or
                int(re.search(r'\d+$', address).group()) != item['row'] or
                column_index(re.match(r'[A-Z]+', address).group()) > table['columnCount'] or
                item['decisionId'] is not None):
            fail(where, 'invalid source cell reference')
        if field is not None:
            mapped = any((view['sourceId'], view['tableId']) == key and
                         item['row'] in view['selectedRows'] and
                         unit in historical_units.get((key[0], key[1], item['row'], view['viewId']), []) and
                         address[:len(address.rstrip('0123456789'))] in
                         (sum((view['columns'].get('port.' + name, []) for name in VLAN_FIELDS), [])
                          if target_kind == 'port' and field == 'vlan' else
                          view['columns'].get(target_kind + '.' + field, []))
                         for view in views)
            if not mapped:
                fail(where, 'source cell was not mapped to this field')
    elif kind in ('user_constant', 'user_decision'):
        if (any(item[key] is not None for key in ('sourceId', 'tableId', 'row', 'address')) or
                type(item['decisionId']) is not str or
                item['decisionId'] not in decisions or
                decisions[item['decisionId']][0] != kind or
                (field is not None and decisions[item['decisionId']][1] not in
                 (VLAN_FIELDS if target_kind == 'port' and field == 'vlan' else {field})) or
                not any(unit in units and view_id == decisions[item['decisionId']][3] and
                        (decisions[item['decisionId']][4] is None or row == decisions[item['decisionId']][4])
                        for (_, _, row, view_id), units in historical_units.items())):
            fail(where, 'invalid user decision reference')
    elif kind == 'derived_layout':
        if field not in ('x', 'y') or any(item[key] is not None for key in ('sourceId', 'tableId', 'row',
                                                'address', 'decisionId')):
            fail(where, 'derived layout cannot claim a source')
    else:
        fail(where, 'unknown origin kind')


def validate_evidence(value):
    object_exact(value, EVIDENCE_KEYS, 'importEvidence')
    if len(canonical_json(value)) > 2 * 1024 * 1024:
        fail('importEvidence', 'receipt exceeds 2 MiB')
    if (value['evidenceVersion'] != '1' or value['contractVersion'] != '1' or
            value['sourceStorage'] != 'external_not_embedded'):
        fail('importEvidence', 'unsupported receipt version or storage')
    name = _name(value['projectNameAtImport'], 'importEvidence.projectNameAtImport')
    if name != value['projectNameAtImport']:
        fail('importEvidence', 'project name must be normalized')
    _sha(value['planFingerprint'], 'planFingerprint')
    _sha(value['baselineNetworkSha256'], 'baselineNetworkSha256')

    sources = _array(value['sources'], 8, 'sources')
    if not sources:
        fail('sources', 'empty source manifest')
    tables = {}
    total_tables = 0
    total_bytes = 0
    for index, source in enumerate(sources, 1):
        object_exact(source, {'sourceId', 'filename', 'kind', 'sha256',
                              'csvDelimiter', 'byteLength', 'tables'}, 'source')
        if source['sourceId'] != f'src-{index}':
            fail('sources', 'nonsequential source ID')
        if (type(source['filename']) is not str or not source['filename'] or
                source['kind'] not in ('csv', 'xlsx', 'ods') or
                type(source['byteLength']) is not int or source['byteLength'] < 0 or
                (source['csvDelimiter'] not in (',', ';') if source['kind'] == 'csv'
                 else source['csvDelimiter'] is not None)):
            fail('source', 'invalid source metadata')
        _sha(source['sha256'], 'source.sha256')
        if not source['filename'].lower().endswith('.' + source['kind']):
            fail('source', 'filename extension does not match source kind')
        total_bytes += source['byteLength']
        if total_bytes > 4 * 1024 * 1024:
            fail('sources', 'combined original size exceeds 4 MiB')
        sheet_list = _array(source['tables'], 32, 'source.tables')
        total_tables += len(sheet_list)
        if total_tables > 256:
            fail('sources', 'more than 256 tables')
        for serial, table in enumerate(sheet_list, 1):
            object_exact(table, {'tableId', 'name', 'rowCount',
                                 'populatedRowCount', 'columnCount'}, 'table')
            if (table['tableId'] != f'sheet-{serial}' or
                    type(table['name']) is not str or not table['name'] or
                    any(type(table[k]) is not int for k in ('rowCount', 'populatedRowCount', 'columnCount')) or
                    not 0 <= table['populatedRowCount'] <= table['rowCount'] <= 5001 or
                    not 0 <= table['columnCount'] <= 256):
                fail('table', 'invalid table metadata')
            tables[(source['sourceId'], table['tableId'])] = table

    views = _array(value['mappingViews'], 64, 'mappingViews')
    view_by_id = {}
    uses = set()
    for index, view in enumerate(views, 1):
        object_exact(view, VIEW_KEYS, 'mappingView')
        table = tables.get((view['sourceId'], view['tableId']))
        if view['viewId'] != f'view-{index}' or table is None or view['role'] not in ROLES:
            fail('mappingViews', 'invalid view identity or role')
        view_by_id[view['viewId']] = view
        header = view['headerRow']
        if header is not None and (type(header) is not int or not 1 <= header <= table['rowCount']):
            fail('mappingViews', 'invalid header row')
        if (type(view['expectedHeaders']) is not list or
                any(type(h) is not str for h in view['expectedHeaders']) or
                (header is None and view['expectedHeaders'])):
            fail('mappingViews', 'invalid headers')
        rows = _array(view['selectedRows'], 5001, 'selectedRows')
        if (any(type(r) is not int or not 1 <= r <= table['rowCount'] or r == header for r in rows)
                or rows != sorted(set(rows))):
            fail('mappingViews', 'invalid selected rows')
        uses.update((view['viewId'], row) for row in rows)
        if (type(view['columns']) is not dict or not set(view['columns']) <= ROLES[view['role']] or
                type(view['constants']) is not dict or
                not set(view['constants']) <= (ROLES[view['role']] - {'node.id', 'zone.id', 'port.nodeId', 'port.id'}) or
                set(view['columns']) & set(view['constants']) or
                type(view['valueMaps']) is not dict or not set(view['valueMaps']) <= set(view['columns']) or
                type(view['label']) is not str or len(view['label']) > 240):
            fail('mappingViews', 'invalid bindings')
        for labels in view['columns'].values():
            if not 1 <= len(_array(labels, 64, 'columns')) <= 64 or len(set(labels)) != len(labels):
                fail('columns', 'invalid source columns')
            for label in labels:
                if column_index(label) > table['columnCount']:
                    fail('columns', 'column out of table')
        for field, mapping in view['valueMaps'].items():
            if type(mapping) is not dict or not mapping or any(type(k) is not str or type(v) is not str for k, v in mapping.items()):
                fail('valueMaps', 'invalid mapping')
            if field == 'port.enabled' and any(v not in ('true', 'false') for v in mapping.values()):
                fail('valueMaps', 'invalid port.enabled mapping')
        for field, item in view['constants'].items():
            object_exact(item, {'type', 'value'}, 'constant')
            _typed_value(item['type'], item['value'], field, 'constant')
    if len(uses) > 20000:
        fail('mappingViews', 'too many uses')

    transformations = _transformations(value['transformations'], views)
    if value['transformations'] != transformations:
        fail('transformations', 'not sorted')
    row_values = _array(value['rowValues'], 10000, 'rowValues')
    decision_ids = {}
    for view in views:
        for field, mapping in view['valueMaps'].items():
            for before, after in mapping.items():
                _remember_decision(decision_ids, [view['viewId'], 'valueMap', field,
                                                  before, after], 'user_decision', field)
        for field, item in view['constants'].items():
            _remember_decision(decision_ids, [view['viewId'], 'constant', field,
                                              item['type'], item['value']], 'user_constant', field)
    for item in transformations:
        _remember_decision(decision_ids, [item['viewId'], 'transformation', item['targetField'],
                                          item['operation'], item['delimiter']],
                           'user_decision', item['targetField'])
    seen_rows = set()
    for item in row_values:
        object_exact(item, {'viewId', 'row', 'targetField', 'valueType', 'value'}, 'rowValue')
        view = view_by_id.get(item['viewId'])
        key = (item['viewId'], item['row'], item['targetField'])
        if (view is None or type(item['row']) is not int or item['row'] not in view['selectedRows'] or
                item['targetField'] not in ROLES[view['role']] or key in seen_rows):
            fail('rowValues', 'invalid row decision')
        _typed_value(item['valueType'], item['value'], item['targetField'], 'rowValue')
        seen_rows.add(key)
        _remember_decision(decision_ids, [item['viewId'], item['row'], item['targetField'],
                                          item['valueType'], item['value']],
                           'user_decision', item['targetField'])
    if row_values != sorted(row_values, key=lambda r: (r['viewId'], r['row'], r['targetField'])):
        fail('rowValues', 'not sorted')

    excluded = _array(value['excludedUses'], 10000, 'excludedUses')
    exclusions = set()
    for item in excluded:
        object_exact(item, {'viewId', 'row', 'reason'}, 'excludedUse')
        key = (item['viewId'], item['row'])
        if (key not in uses or key in exclusions or type(item['reason']) is not str or
                not 1 <= len(item['reason']) <= 240):
            fail('excludedUses', 'invalid exclusion')
        exclusions.add(key)
    if excluded != sorted(excluded, key=lambda e: (e['viewId'], e['row'])):
        fail('excludedUses', 'not sorted')
    selected = _array(value['selectedUnitIds'], 10000, 'selectedUnitIds')
    _sorted_unique(selected, 'selectedUnitIds')
    if not selected:
        fail('selectedUnitIds', 'an imported project requires at least one selected node')
    if any(not UNIT_ID.fullmatch(item) for item in selected):
        fail('selectedUnitIds', 'invalid unit ID')
    fingerprint_input = {'contractVersion': '1', 'projectName': name,
                         'validatorVersion': '1.4',
                         'sources': [{k: s[k] for k in ('sourceId', 'sha256', 'csvDelimiter')} for s in sources],
                         'mappingViews': views, 'transformations': transformations, 'rowValues': row_values,
                         'excludedUses': excluded, 'selectedUnitIds': selected}
    if hashlib.sha256(canonical_json(fingerprint_input)).hexdigest() != value['planFingerprint']:
        fail('planFingerprint', 'does not match historical inputs')

    historical_uses = set()
    historical_units = {}
    decision_list = _array(value['decisions'], 20000, 'decisions')
    for item in decision_list:
        object_exact(item, {'sourceId', 'tableId', 'row', 'viewId', 'status', 'reason', 'unitIds'}, 'decision')
        table = tables.get((item['sourceId'], item['tableId']))
        key = (item['sourceId'], item['tableId'], item['row'], item['viewId'])
        view = view_by_id.get(item['viewId']) if item['viewId'] is not None else None
        if (table is None or type(item['row']) is not int or not 1 <= item['row'] <= table['rowCount'] or
                key in historical_uses or
                (view is not None and (view['sourceId'] != item['sourceId'] or
                                       view['tableId'] != item['tableId'] or item['row'] not in view['selectedRows'])) or
                (item['viewId'] is not None and view is None) or
                item['status'] not in ('ACTIONABLE', 'NO_OP', 'BLOCKED', 'INVALID',
                                       'EXCLUDED', 'DOCUMENTATION_ONLY') or
                (item['viewId'] is None and (item['status'] != 'DOCUMENTATION_ONLY' or item['reason'] is not None)) or
                (item['status'] == 'EXCLUDED') != ((item['viewId'], item['row']) in exclusions) or
                (item['status'] == 'EXCLUDED' and item['reason'] != next(
                    e['reason'] for e in excluded if (e['viewId'], e['row']) == (item['viewId'], item['row']))) or
                (item['status'] != 'EXCLUDED' and item['reason'] is not None)):
            fail('decisions', 'invalid historical use')
        ids = _array(item['unitIds'], 10000, 'decision.unitIds')
        _sorted_unique(ids, 'decision.unitIds')
        if any(not UNIT_ID.fullmatch(unit) for unit in ids):
            fail('decision.unitIds', 'invalid unit ID')
        if item['status'] in ('EXCLUDED', 'DOCUMENTATION_ONLY') and ids:
            fail('decision.unitIds', 'non-network use cannot own a unit')
        historical_uses.add(key)
        historical_units[key] = ids
    for view in views:
        for row in view['selectedRows']:
            if (view['sourceId'], view['tableId'], row, view['viewId']) not in historical_uses:
                fail('decisions', 'selected source use missing')
    for key, table in tables.items():
        records = {r for source_id, table_id, r, _ in historical_uses
                   if (source_id, table_id) == key}
        if len(records) != table['populatedRowCount']:
            fail('decisions', 'source records missing from historical receipt')
        for row in records:
            null_use = (key[0], key[1], row, None) in historical_uses
            mapped_use = any((key[0], key[1], row, view_id) in historical_uses
                             for view_id in view_by_id)
            if null_use == mapped_use:
                fail('decisions', 'unmapped record disposition is inconsistent')

    changes = _array(value['acceptedChanges'], 10000, 'acceptedChanges')
    if len(changes) != len(selected):
        fail('acceptedChanges', 'must match selected units')
    accepted = set()
    for change in changes:
        object_exact(change, {'unitId', 'changeIds', 'targetKind', 'targetKey',
                              'fieldValues', 'fieldOrigins'}, 'acceptedChange')
        unit = change['unitId']
        kind = change['targetKind']
        if (type(unit) is not str or unit not in selected or unit in accepted or
                kind not in ('node', 'zone', 'port') or type(change['targetKey']) is not str or
                internal_id('u-', [kind, change['targetKey']]) != unit):
            fail('acceptedChanges', 'invalid unit identity')
        if kind == 'port':
            try:
                pair = json.loads(change['targetKey'])
            except (TypeError, ValueError) as error:
                fail('acceptedChanges', 'invalid port targetKey')
            if (type(pair) is not list or len(pair) != 2 or
                    any(type(value) is not str for value in pair) or
                    canonical_json(pair).decode('utf-8') != change['targetKey']):
                fail('acceptedChanges', 'noncanonical port targetKey')
            for element in pair:
                _id(element, 'acceptedChange.targetKey')
        else:
            _id(change['targetKey'], 'acceptedChange.targetKey')
        if change['changeIds'] != [internal_id('c-', [unit, 'create', '__object__'])]:
            fail('acceptedChanges', 'invalid change ID')
        fields, origins = change['fieldValues'], change['fieldOrigins']
        expected_fields = NODE_FIELDS if kind == 'node' else PORT_FIELDS if kind == 'port' else ZONE_FIELDS
        if kind == 'port' and 'vlan' in fields:
            expected_fields = expected_fields | {'vlan'}
        object_exact(fields, expected_fields, 'acceptedChange.fieldValues')
        object_exact(origins, expected_fields, 'acceptedChange.fieldOrigins')
        if kind == 'port':
            if (fields['nodeId'] != pair[0] or fields['id'] != pair[1] or
                    fields['ipv4'] is not None or origins['ipv4']):
                fail('acceptedChanges', 'port identity or absent IPv4 invalid')
        elif fields['id'] != change['targetKey'] or (kind == 'node' and fields['ports'] != []):
            fail('acceptedChanges', 'unsupported historical fields')
        for field, refs in origins.items():
            refs = _array(refs, 128, f'fieldOrigins.{field}')
            if field in ('x', 'y') and (len(refs) != 1 or refs[0].get('kind') != 'derived_layout'):
                fail('fieldOrigins', 'missing derived layout')
            if field in ('ports', 'ipv4') and refs:
                fail('fieldOrigins', 'structural defaults have no source origin')
            if field == 'zoneId' and fields['zoneId'] is None and any(ref.get('kind') == 'source_cell' for ref in refs):
                fail('fieldOrigins', 'null zone cannot be attributed to a source cell')
            if field == 'zoneId' and fields['zoneId'] is not None and not refs:
                fail('fieldOrigins', 'declared zone needs a source or decision origin')
            if field in ('id', 'label', 'nodeId', 'name', 'enabled') or (kind == 'node' and field == 'kind'):
                if not refs:
                    fail('fieldOrigins', 'missing source or decision origin')
            if kind == 'port' and field == 'vlan' and not refs:
                fail('fieldOrigins', 'VLAN needs explicit origins')
            for ref in refs:
                _origin(ref, tables, decision_ids, f'fieldOrigins.{field}',
                        field=field,
                        views=views, unit=unit, historical_units=historical_units,
                        target_kind=kind)
        accepted.add(unit)
    if [c['unitId'] for c in changes] != selected:
        fail('acceptedChanges', 'not sorted by selected unit ID')
    zone_changes = [c for c in changes if c['targetKind'] == 'zone']
    node_changes = [c for c in changes if c['targetKind'] == 'node']
    port_changes = [c for c in changes if c['targetKind'] == 'port']
    zones = sorted((c['fieldValues'] for c in zone_changes), key=lambda z: z['id'])
    nodes = sorted((deepcopy(c['fieldValues']) for c in node_changes), key=lambda n: n['id'])
    nodes_by_id = {node['id']: node for node in nodes}
    for change in port_changes:
        values = change['fieldValues']
        owner = nodes_by_id.get(values['nodeId'])
        if owner is None:
            fail('acceptedChanges', 'port has no selected parent node')
        owner['ports'].append({k: deepcopy(values[k]) for k in ('id', 'name', 'enabled', 'ipv4', 'vlan') if k in values})
    for node in nodes:
        node['ports'].sort(key=lambda port: port['id'])
    if not nodes:
        fail('acceptedChanges', 'at least one selected node required')
    positions = node_layout([c['targetKey'] for c in node_changes])
    for change in node_changes:
        if (change['fieldValues']['x'], change['fieldValues']['y']) != positions[change['targetKey']]:
            fail('acceptedChanges', 'historical layout differs from selected node set')
    historical = {'schemaVersion': '1.3', 'name': name, 'zones': zones,
                  'nodes': nodes, 'links': []}
    if validate_project(historical) != historical:
        fail('acceptedChanges', 'historical values are not canonical')
    actual_baseline = hashlib.sha256(canonical_json(canonical_network_view(historical))).hexdigest()
    if actual_baseline != value['baselineNetworkSha256']:
        fail('baselineNetworkSha256', 'does not match historical accepted network')
    referenced = {unit for decision in decision_list
                  if decision['status'] in ('ACTIONABLE', 'NO_OP')
                  for unit in decision['unitIds']}
    if not accepted <= referenced:
        fail('acceptedChanges', 'accepted unit has no source use')
    return deepcopy(value)
