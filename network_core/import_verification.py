"""Read-only checks of a saved import receipt and reattached original files."""
from __future__ import annotations

import hashlib

from .import_plan import _sources, build_plan, canonical_json, fail, object_exact
from .model import ProjectValidationError, canonical_network_view, validate_project


def _validated_project(value):
    project = validate_project(value)
    if project['schemaVersion'] != '1.4':
        fail('project', 'historical evidence requires schema 1.4')
    return project


def _baseline_status(project):
    current = hashlib.sha256(canonical_json(canonical_network_view(project))).hexdigest()
    historical = project['importEvidence']['baselineNetworkSha256']
    return 'BASELINE_MATCH' if current == historical else 'CHANGED_SINCE_IMPORT'


def evidence_status(value):
    object_exact(value, {'project'}, 'evidence-status request')
    project = _validated_project(value['project'])
    return {'manifestStatus': 'MANIFEST_VALIDATED',
            'baselineStatus': _baseline_status(project)}


def _mismatch(status, code):
    return {**status, 'sourceStatus': 'SOURCE_HASH_MATCH', 'replayStatus': 'MISMATCH',
            'verifiedSourceIds': [],
            'diagnostics': [{'code': code, 'sourceId': None, 'tableId': None,
                             'row': None, 'message': code.replace('_', ' ').lower()}]}


def verify_sources(value):
    object_exact(value, {'project', 'sources'}, 'verify-sources request')
    if len(canonical_json(value)) > 8 * 1024 * 1024:
        fail('verify-sources', 'PAYLOAD_LIMIT: project and sources exceed 8 MiB')
    project = _validated_project(value['project'])
    historical = project['importEvidence']
    status = {'manifestStatus': 'MANIFEST_VALIDATED',
              'baselineStatus': _baseline_status(project)}
    supplied = value['sources']
    if type(supplied) is not list or len(supplied) != len(historical['sources']):
        fail('sources', 'every historical source must be reattached in order')
    manifest, _ = _sources(supplied)
    if manifest != historical['sources']:
        fail('sources', 'original bytes or source metadata differ from historical manifest')
    replay_request = {'contractVersion': '1',
                      'projectName': historical['projectNameAtImport'],
                      'sources': supplied,
                      'mappingViews': historical['mappingViews'],
                      'transformations': historical['transformations'],
                      'rowValues': historical['rowValues'],
                      'excludedUses': historical['excludedUses'],
                      'selectedUnitIds': historical['selectedUnitIds']}
    try:
        plan = build_plan(replay_request)['plan']
    except ProjectValidationError:
        return _mismatch(status, 'REPLAY_REJECTED')
    if (not plan['canApply'] or plan['proposedProject'] is None or
            plan['fingerprint'] != historical['planFingerprint']):
        return _mismatch(status, 'REPLAY_PLAN_MISMATCH')
    receipt = plan['proposedProject']['importEvidence']
    if (canonical_json(receipt['acceptedChanges']) != canonical_json(historical['acceptedChanges']) or
            receipt['baselineNetworkSha256'] != historical['baselineNetworkSha256'] or
            canonical_json(receipt['decisions']) != canonical_json(historical['decisions'])):
        return _mismatch(status, 'REPLAY_EVIDENCE_MISMATCH')
    return {**status, 'sourceStatus': 'SOURCE_VERIFIED', 'replayStatus': 'MATCH',
            'verifiedSourceIds': [item['sourceId'] for item in manifest],
            'diagnostics': []}
