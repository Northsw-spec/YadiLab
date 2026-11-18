"""Real Chromium end-to-end: UI, link semantics, faults and restart Save/Open."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from playwright._impl._errors import Error as PlaywrightError


try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    raise SystemExit('Playwright is not installed. Run: pip install playwright')

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from network_core import config
from network_core.icmp_investigation import _candidates
from network_core.icmp_ping import EchoExchange
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.session_idle import IDLE_TIMEOUT_SECONDS
from xlsx_fixture import make_workbook, workbook_parts, zip_parts
from ods_fixture import make_ods, ods_parts, zip_parts as zip_ods_parts
from spreadsheet_v13_fixture import TABLES_13, expected_v13, xlsx_v13, ods_v13
from network_core.xlsx_import import import_xlsx_workbook
from network_core.ods_import import import_ods_workbook
from test_dhcp import topology as dhcp_topology
from test_dhcp_registry import clients as dhcp_multi_clients
from test_dhcp_port_vlan_fault import vlan_clients as dhcp_vlan_clients
from test_icmp_echo import routed_reply_lab as icmp_routed_lab
from test_icmp_investigation_lan import lan_lab as icmp_lan_lab


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def spawn_server(port_number, directory):
    process = subprocess.Popen([sys.executable, '-m', 'network_core', '--port', str(port_number),
                                '--data-dir', str(directory), '--no-browser'],
                               cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError('server ended early: ' + process.stderr.read().decode(errors='replace'))
        try:
            with urlopen(f'http://127.0.0.1:{port_number}/api/health', timeout=.2) as response:
                if response.status == 200:
                    return process
        except Exception:
            time.sleep(.08)
    process.terminate()
    raise AssertionError('local server never became ready')


def stop_server(process):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=4)
    process.stderr.close()


def browser_open(page, base):
    """Prefer real HTTP. Isolated fallback for administrative Chromium loopback blocks.

    The fallback still executes the actual app code and calls the REAL
    Python HTTP server via urllib; only the browser's forbidden socket is
    bridged. Never report fallback as proof of direct browser HTTP networking.
    """
    try:
        page.goto(base, wait_until='domcontentloaded', timeout=10000)
        return 'DIRECT_HTTP'
    except PlaywrightError as error:
        if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):
            raise
    try:
        page.goto('about:blank')
    except PlaywrightError:
        # The previously blocked navigation may still be finishing the error page.
        page.wait_for_timeout(400)
        page.goto('about:blank')

    def handle_request(relative_url, options):
        from urllib.parse import urljoin
        method = options.get('method', 'GET')
        body = options.get('body')
        url = urljoin(base, relative_url)
        request = Request(url, method=method,
                          data=body.encode('utf-8') if body is not None else None,
                          headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=12) as response:
                return {'status': response.status, 'body': response.read().decode('utf-8')}
        except HTTPError as error:
            return {'status': error.code, 'body': error.read().decode('utf-8')}

    page.expose_function('__test_http_request', handle_request)
    html = urlopen(base, timeout=5).read().decode('utf-8')
    html = html.replace('<link rel="stylesheet" href="/styles.css">', '')
    html = html.replace('<script type="module" src="/app.js"></script>', '')
    page.set_content(html, wait_until='domcontentloaded')
    page.add_style_tag(content=(ROOT / 'web/styles.css').read_text(encoding='utf8'))
    page.evaluate("""() => {
      window.fetch = async (url, init = {}) => {
        const answer = await window.__test_http_request(String(url), {method: init?.method || 'GET', body: init?.body ?? null});
        return new Response(answer.body, {status: answer.status,
          headers: {'content-type': 'application/json'}});
      };
    }""")
    model = (ROOT / 'web/model.js').read_text(encoding='utf8').replace('export ', '')
    canvas = (ROOT / 'web/canvas.js').read_text(encoding='utf8')
    canvas = canvas.replace("import {truncate} from './model.js';", '').replace('export ', '')
    dom = (ROOT / 'web/ui/dom.js').read_text(encoding='utf8').replace('export ', '')
    api = (ROOT / 'web/services/api.js').read_text(encoding='utf8').replace('export ', '')
    persistence = (ROOT / 'web/features/projects/persistence.js').read_text(encoding='utf8')
    persistence = persistence.replace("import {api} from '../../services/api.js';", '').replace('export ', '')
    transfer = (ROOT / 'web/features/projects/transfer.js').read_text(encoding='utf8')
    transfer = transfer.replace("import {api} from '../../services/api.js';", '').replace('export ', '')
    queries = (ROOT / 'web/features/diagnostics/queries.js').read_text(encoding='utf8')
    queries = queries.replace("import {api} from '../../services/api.js';", '').replace('export ', '')
    presenters = (ROOT / 'web/features/diagnostics/presenters.js').read_text(encoding='utf8').replace('export ', '')
    investigation = (ROOT / 'web/features/sessions/dhcp-investigation.js').read_text(encoding='utf8')
    investigation = investigation.replace("import {api} from '../../services/api.js';", '').replace('export ', '')
    icmp_investigation = (ROOT / 'web/features/sessions/icmp-investigation.js').read_text(encoding='utf8')
    icmp_investigation = icmp_investigation.replace("import {api} from '../../services/api.js';", '').replace('export ', '')
    dora_session = (ROOT / 'web/features/sessions/dora-session.js').read_text(encoding='utf8')
    dora_session = dora_session.replace("import {api} from '../../services/api.js';", '').replace('export ', '')
    app = (ROOT / 'web/app.js').read_text(encoding='utf8')
    app = app.replace("import {blank, copy, newNode, newZone, addPort, connect, used, nextId, exampleProject, KINDS} from './model.js';", '')
    app = app.replace("import {TopologyCanvas} from './canvas.js';", '')
    app = app.replace("import {$, el, field, heading, small, button, input, dropdown, check} from './ui/dom.js';", '')
    app = app.replace("import {api} from './services/api.js';", '')
    app = app.replace("import {prepareSave, saveSnapshot, listSavedProjects, readSavedProject} from './features/projects/persistence.js';", '')
    app = app.replace("import {importKind, prepareImport, submitImport, prepareProjectExport, prepareSpreadsheetExport} from './features/projects/transfer.js';", '')
    app = app.replace("import {presentArp, presentRoute, presentPing, presentIPv4} from './features/diagnostics/presenters.js';", '')
    app = app.replace("import {queryArp, queryRoute, queryIPv4, queryPing} from './features/diagnostics/queries.js';", '')
    app = app.replace("import {createDhcpInvestigationController} from './features/sessions/dhcp-investigation.js';", '')
    app = app.replace("import {createIcmpInvestigationController} from './features/sessions/icmp-investigation.js';", '')
    app = app.replace("import {createDoraSessionController} from './features/sessions/dora-session.js';", '')
    page.add_script_tag(content=model + '\n' + canvas + '\n' + dom + '\n' + api + '\n' + persistence + '\n' + transfer + '\n' + queries + '\n' + presenters + '\n' + investigation + '\n' + icmp_investigation + '\n' + dora_session + '\n' + app)
    return 'BRIDGED_LOCAL_HTTP'


def hold_http_reply(page, path, first_only=False):
    """Delay delivery to app code only after real HTTP and disk work finish."""
    page.evaluate("""({path, firstOnly}) => {
      const originalFetch = window.fetch;
      let seen = 0;
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      window.__heldReply = false;
      window.__releaseReply = () => { release(); window.fetch = originalFetch; };
      window.fetch = async (...args) => {
        const response = await originalFetch(...args);
        if (String(args[0]) === path && (!firstOnly || ++seen === 1)) {
          window.__heldReply = true;
          await gate;
        }
        return response;
      };
    }""", {'path': path, 'firstOnly': first_only})


def release_http_reply(page):
    page.evaluate('window.__releaseReply()')


def abandoned_investigation_cleanup(context, network_mode, errors):
    """Real Chromium and HTTP; only the server's monotonic worker reaps IDs."""
    class Clock:
        now = 100.0

        def __call__(self):
            return self.now

    clock = Clock()
    with tempfile.TemporaryDirectory() as directory:
        server = LabHTTPServer(('127.0.0.1', 0), ProjectStore(directory),
                               clock=clock, cleanup_interval=.01)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}/'
        cleaned = threading.Event()
        original_cleanup = server.investigations.cleanup_expired

        def observe_cleanup():
            count = original_cleanup()
            if count:
                cleaned.set()
            return count

        server.investigations.cleanup_expired = observe_cleanup
        try:
            def fresh():
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
                assert browser_open(page, base) == network_mode
                page.once('dialog', lambda dialog: dialog.accept())
                with page.expect_response('**/api/validate') as imported:
                    page.locator('#import-file').set_input_files({
                        'name': 'abandoned-dhcp.json', 'mimeType': 'application/json',
                        'buffer': json.dumps(dhcp_vlan_clients()).encode('utf-8'),
                    })
                assert imported.value.status == 200
                page.locator('#dora-client').select_option('["client","eth0"]')
                page.locator('#dora-server').select_option('["server","eth0"]')
                page.locator('#dora-pool-start').fill('192.0.2.70')
                page.locator('#dora-pool-end').fill('192.0.2.71')
                page.locator('#dora-lease-seconds').fill('60')
                return page

            page = fresh()
            with page.expect_response('**/api/dhcp/investigation/start') as started:
                page.locator('#investigation-start').click()
            old = started.value.json()['sessionId']
            assert old in server.investigations._sessions
            page.close()  # No Stop request and no subsequent HTTP request.
            assert old in server.investigations._sessions
            clock.now += IDLE_TIMEOUT_SECONDS
            assert cleaned.wait(2), 'server did not reap the abandoned browser session'
            assert old not in server.investigations._sessions

            page = fresh()
            with page.expect_response('**/api/dhcp/investigation/start') as restarted:
                page.locator('#investigation-start').click()
            current = restarted.value.json()['sessionId']
            assert current != old
            page.evaluate("""() => {
              const original = window.fetch;
              window.fetch = (url, init) => {
                if (url === '/api/dhcp/investigation/stop') {
                  window.fetch = original;
                  return Promise.reject(new TypeError('lost Stop request'));
                }
                return original(url, init);
              };
            }""")
            page.locator('#investigation-stop').click()
            expect(page.locator('#investigation-status')).to_contain_text('Kunde inte avsluta')
            page.close()
            assert current in server.investigations._sessions
            cleaned.clear()
            clock.now += IDLE_TIMEOUT_SECONDS
            assert cleaned.wait(2), 'failed Stop left a permanent server resource'
            assert current not in server.investigations._sessions

            page = fresh()
            with page.expect_response('**/api/dhcp/investigation/start') as live_start:
                page.locator('#investigation-start').click()
            live = live_start.value.json()['sessionId']
            clock.now += IDLE_TIMEOUT_SECONDS - 1
            with page.expect_response('**/api/dhcp/investigation/probe') as active:
                page.locator('#investigation-run-probe').click()
            assert active.value.json()['sessionId'] == live
            clock.now += 1
            assert server.investigations.cleanup_expired() == 0
            cleaned.clear()
            clock.now += IDLE_TIMEOUT_SECONDS
            assert cleaned.wait(2)
            with page.expect_response('**/api/dhcp/investigation/probe') as expired:
                page.locator('#investigation-run-probe').click()
            assert expired.value.status == 422
            assert 'faulted' not in expired.value.body().decode('utf-8')
            expect(page.locator('#investigation-status')).to_contain_text('Sessionen har upphört')
            expect(page.locator('#investigation-start')).to_be_enabled()
            with page.expect_response('**/api/dhcp/investigation/start') as new_start:
                page.locator('#investigation-start').click()
            assert new_start.value.status == 200
            page.close()
            assert not errors, errors
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
            assert not worker.is_alive()
            assert not server._cleanup_thread.is_alive()


def investigation_lifecycle_races(context, base, network_mode, errors):
    """Exercise real allocated server sessions while delaying browser delivery."""
    fixture = dhcp_vlan_clients()
    encoded = json.dumps(fixture).encode('utf-8')

    def fresh():
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
        assert browser_open(page, base) == network_mode
        page.once('dialog', lambda dialog: dialog.accept())
        with page.expect_response('**/api/validate') as imported:
            page.locator('#import-file').set_input_files({
                'name': 'race-dhcp.json', 'mimeType': 'application/json', 'buffer': encoded,
            })
        assert imported.value.status == 200
        page.locator('#dora-client').select_option('["client","eth0"]')
        page.locator('#dora-server').select_option('["server","eth0"]')
        page.locator('#dora-pool-start').fill('192.0.2.70')
        page.locator('#dora-pool-end').fill('192.0.2.71')
        page.locator('#dora-lease-seconds').fill('60')
        return page

    def start(page):
        with page.expect_response('**/api/dhcp/investigation/start') as response:
            page.locator('#investigation-start').click()
        assert response.value.status == 200
        session_id = response.value.json()['sessionId']
        expect(page.locator('#investigation-status')).to_contain_text('Aktiv övning')
        return session_id

    def server_status(page, session_id):
        return page.evaluate("""async id => (await fetch('/api/dhcp/investigation/stop', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({sessionId: id})})).status""", session_id)

    # A/B/J: server allocates A before Start is delivered; two clicks yield one
    # allocation. Switching workspaces must issue targeted Stop for A.
    page = fresh()
    starts = []
    page.on('request', lambda request: starts.append(request) if
            request.url.endswith('/api/dhcp/investigation/start') else None)
    hold_http_reply(page, '/api/dhcp/investigation/start')
    with page.expect_response('**/api/dhcp/investigation/start') as allocated:
        page.locator('#investigation-start').click()
    page.wait_for_function('window.__heldReply', timeout=5000)
    expect(page.locator('#investigation-start')).to_be_disabled()
    page.locator('#investigation-start').dispatch_event('click')
    assert len(starts) == 1
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#new-project').click()
    with page.expect_response('**/api/dhcp/investigation/stop') as cleaned:
        release_http_reply(page)
    old_id = allocated.value.json()['sessionId']
    assert cleaned.value.status == 200
    assert server_status(page, old_id) == 422
    expect(page.locator('#investigation-status')).to_contain_text('Ingen felsökningsövning')
    page.close()

    # C/I: a real probe response processed by the server cannot resurrect the
    # observation after project invalidation.
    page = fresh()
    old_id = start(page)
    hold_http_reply(page, '/api/dhcp/investigation/probe')
    with page.expect_response('**/api/dhcp/investigation/probe') as probed:
        page.locator('#investigation-run-probe').click()
    assert probed.value.status == 200
    page.wait_for_function('window.__heldReply')
    with page.expect_response('**/api/dhcp/investigation/stop') as cleaned:
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#new-project').click()
    assert cleaned.value.status == 200
    release_http_reply(page)
    expect(page.locator('#investigation-observations')).to_contain_text('Inga observationer')
    assert server_status(page, old_id) == 422
    page.close()

    # D: Advance for A is complete at the server, but B must retain its own
    # clock after the old reply arrives.
    page = fresh()
    page.locator('#investigation-difficulty').select_option('EXPIRY_RECOVERY')
    old_id = start(page)
    page.locator('#investigation-probe').select_option('renew')
    with page.expect_response('**/api/dhcp/investigation/probe'):
        page.locator('#investigation-run-probe').click()
    expect(page.locator('#investigation-advance')).to_be_enabled()
    hold_http_reply(page, '/api/dhcp/investigation/advance')
    with page.expect_response('**/api/dhcp/investigation/advance') as advanced:
        page.locator('#investigation-advance').click()
    page.wait_for_function('window.__heldReply')
    with page.expect_response('**/api/dhcp/investigation/stop') as stopped:
        page.locator('#investigation-stop').click()
    assert stopped.value.status == 200
    new_id = start(page)
    assert new_id != old_id
    release_http_reply(page)
    assert advanced.value.json()['clockSeconds'] == 53
    expect(page.locator('#investigation-status')).to_contain_text('Aktiv övning')
    expect(page.locator('#investigation-observations')).to_contain_text('Inga observationer')
    assert page.locator('#investigation-clock-result').inner_text().find('53') == -1
    assert server_status(page, old_id) == 422
    with page.expect_response('**/api/dhcp/investigation/stop'):
        page.locator('#investigation-stop').click()
    page.close()

    # G: the HTTP Stop for A is held after the server removed it. A workspace
    # switch permits B to start; the late A response must not clear B.
    page = fresh()
    old_id = start(page)
    hold_http_reply(page, '/api/dhcp/investigation/stop', first_only=True)
    with page.expect_response('**/api/dhcp/investigation/stop') as stopped:
        page.locator('#investigation-stop').click()
    assert stopped.value.status == 200
    page.wait_for_function('window.__heldReply')
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#new-project').click()
    page.once('dialog', lambda dialog: dialog.accept())
    with page.expect_response('**/api/validate'):
        page.locator('#import-file').set_input_files({
            'name': 'race-dhcp.json', 'mimeType': 'application/json', 'buffer': encoded,
        })
    page.locator('#dora-client').select_option('["client","eth0"]')
    page.locator('#dora-server').select_option('["server","eth0"]')
    page.locator('#dora-pool-start').fill('192.0.2.70')
    page.locator('#dora-pool-end').fill('192.0.2.71')
    page.locator('#dora-lease-seconds').fill('60')
    new_id = start(page)
    assert new_id != old_id
    release_http_reply(page)
    expect(page.locator('#investigation-status')).to_contain_text('Aktiv övning')
    assert server_status(page, old_id) == 422
    with page.expect_response('**/api/dhcp/investigation/stop'):
        page.locator('#investigation-stop').click()
    page.close()

    # H: real API validation failure releases busy and allows a valid probe.
    page = fresh()
    start(page)
    page.locator('#investigation-probe').select_option('link')
    page.locator('#investigation-link').select_option('to-server')
    page.evaluate("""() => {
      const original = window.fetch;
      window.fetch = (url, init) => {
        if (url === '/api/dhcp/investigation/probe') {
          const body = JSON.parse(init.body);
          body.target = {linkId: 'not-a-link'};
          window.fetch = original;
          return original(url, {...init, body: JSON.stringify(body)});
        }
        return original(url, init);
      };
    }""")
    with page.expect_response('**/api/dhcp/investigation/probe') as failed:
        page.locator('#investigation-run-probe').click()
    assert failed.value.status == 422
    expect(page.locator('#investigation-observations')).to_contain_text('MÄTNING AVVISAD: inspection: undeclared link')
    expect(page.locator('#investigation-run-probe')).to_be_enabled()
    with page.expect_response('**/api/dhcp/investigation/probe') as succeeded:
        page.locator('#investigation-run-probe').click()
    assert succeeded.value.status == 200
    expect(page.locator('#investigation-observations')).to_contain_text('LÄNKMÄTNING to-server')
    page.evaluate("""() => {
      const original = window.fetch;
      window.fetch = (url, init) => {
        if (url === '/api/dhcp/investigation/stop') {
          const body = JSON.parse(init.body);
          body.sessionId = 'expired-race-id';
          window.fetch = original;
          return original(url, {...init, body: JSON.stringify(body)});
        }
        return original(url, init);
      };
    }""")
    with page.expect_response('**/api/dhcp/investigation/stop') as failed_stop:
        page.locator('#investigation-stop').click()
    assert failed_stop.value.status == 422
    expect(page.locator('#investigation-status')).to_contain_text('Kunde inte avsluta sessionen')
    expect(page.locator('#investigation-stop')).to_be_enabled()
    with page.expect_response('**/api/dhcp/investigation/stop') as retried_stop:
        page.locator('#investigation-stop').click()
    assert retried_stop.value.status == 200
    assert not errors, errors
    page.close()

    def ready_for_diagnosis(page):
        start(page)
        for kind in ('lease', 'renew'):
            page.locator('#investigation-probe').select_option(kind)
            with page.expect_response('**/api/dhcp/investigation/probe') as measured:
                page.locator('#investigation-run-probe').click()
            assert measured.value.status == 200
        page.locator('#investigation-probe').select_option('link')
        page.locator('#investigation-link').select_option('to-server')
        with page.expect_response('**/api/dhcp/investigation/probe') as link:
            page.locator('#investigation-run-probe').click()
        page.locator('#investigation-probe').select_option('port')
        page.locator('#investigation-port').select_option('["sw","s"]')
        with page.expect_response('**/api/dhcp/investigation/probe') as port:
            page.locator('#investigation-run-probe').click()
        page.locator('#investigation-probe').select_option('vlan')
        page.locator('#investigation-port').select_option('["sw","c"]')
        with page.expect_response('**/api/dhcp/investigation/probe') as vlan:
            page.locator('#investigation-run-probe').click()
        link_value = link.value.json()['observation']
        port_value = port.value.json()['observation']
        vlan_value = vlan.value.json()['observation']
        if link_value['observedCarrier'] == 'DOWN':
            cause = ('PORT_SHUTDOWN' if port_value['observedAdmin'] == 'DOWN'
                     else 'CABLE_DOWN')
        else:
            assert vlan_value['observedVlan'] == 20
            cause = 'VLAN_MISMATCH'
        expect(page.locator('#investigation-submit')).to_be_enabled()
        return cause

    # E: the server returns a genuine 422 for an invalid session ID. A
    # delayed error after workspace replacement must not appear in the new UI.
    page = fresh()
    ready_for_diagnosis(page)
    page.locator('#investigation-diagnosis').select_option('CABLE_DOWN')
    page.evaluate("""() => {
      const original = window.fetch;
      window.fetch = (url, init) => {
        if (url === '/api/dhcp/investigation/diagnose') {
          const body = JSON.parse(init.body);
          body.sessionId = 'expired-race-id';
          window.fetch = original;
          return original(url, {...init, body: JSON.stringify(body)});
        }
        return original(url, init);
      };
    }""")
    hold_http_reply(page, '/api/dhcp/investigation/diagnose')
    with page.expect_response('**/api/dhcp/investigation/diagnose') as rejected:
        page.locator('#investigation-submit').click()
    assert rejected.value.status == 422
    page.wait_for_function('window.__heldReply')
    with page.expect_response('**/api/dhcp/investigation/stop'):
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#new-project').click()
    release_http_reply(page)
    expect(page.locator('#investigation-verdict')).not_to_contain_text('avvisad')
    expect(page.locator('#investigation-status')).to_contain_text('Ingen felsökningsövning')
    page.close()

    # F: repair really succeeds on the server before its response is held,
    # then Stop must make that late RECOVERED result invisible.
    page = fresh()
    cause = ready_for_diagnosis(page)
    page.locator('#investigation-diagnosis').select_option(cause)
    with page.expect_response('**/api/dhcp/investigation/diagnose') as confirmed:
        page.locator('#investigation-submit').click()
    assert confirmed.value.json()['correct'] is True
    hold_http_reply(page, '/api/dhcp/investigation/repair')
    with page.expect_response('**/api/dhcp/investigation/repair') as recovered:
        page.locator('#investigation-repair').click()
    page.wait_for_function('window.__heldReply')
    with page.expect_response('**/api/dhcp/investigation/stop') as stopped:
        page.locator('#investigation-stop').click()
    assert stopped.value.status == 200
    release_http_reply(page)
    assert recovered.value.json()['status'] == 'RECOVERED'
    expect(page.locator('#investigation-status')).to_contain_text('Ingen felsökningsövning')
    expect(page.locator('#investigation-recovery')).not_to_contain_text('RESULTAT: RECOVERED')
    assert not errors, errors
    page.close()


def dora_session_races(context, network_mode, errors):
    """Real DORA sessions, delayed HTTP delivery, and exact server cleanup."""
    class Clock:
        now = 100.0

        def __call__(self):
            return self.now

    clock = Clock()
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(directory)
        project = dhcp_vlan_clients()
        # Three documented access VLANs permit a real changed target choice.
        next(port for port in project['nodes'][1]['ports'] if port['id'] == 'p-2')['vlan']['vlan'] = 30
        store.save('dora-race', project)
        saved_file = Path(directory) / 'dora-race.yadilab'
        digest = hashlib.sha256(saved_file.read_bytes()).hexdigest()
        server = LabHTTPServer(('127.0.0.1', 0), store,
                               clock=clock, cleanup_interval=.01)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}/'
        try:
            def load(page):
                page.once('dialog', lambda dialog: dialog.accept())
                with page.expect_response('**/api/validate') as imported:
                    page.locator('#import-file').set_input_files({
                        'name': 'dora-race.json', 'mimeType': 'application/json',
                        'buffer': json.dumps(project).encode('utf-8'),
                    })
                assert imported.value.status == 200
                page.locator('#dora-client').select_option('["client","eth0"]')
                page.locator('#dora-server').select_option('["server","eth0"]')
                page.locator('#dora-pool-start').fill('192.0.2.70')
                page.locator('#dora-pool-end').fill('192.0.2.71')
                page.locator('#dora-transaction-id').fill('101')
                page.locator('#dora-lease-seconds').fill('3600')

            def fresh():
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
                assert browser_open(page, base) == network_mode
                load(page)
                return page

            def replace(page):
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#new-project').click()
                load(page)

            def start(page):
                with page.expect_response('**/api/dhcp/session/start') as response:
                    page.locator('#dora-session-start').click()
                assert response.value.status == 200
                sid = response.value.json()['sessionId']
                assert sid in server.dhcp_sessions._sessions
                return sid

            def run(page):
                with page.expect_response('**/api/dhcp/session/run') as response:
                    page.locator('#dora-session-run').click()
                assert response.value.status == 200
                return response.value.json()

            def prepare_renew(page):
                run(page)
                page.locator('#dora-session-advance-seconds').fill('1800')
                with page.expect_response('**/api/dhcp/session/advance') as advanced:
                    page.locator('#dora-session-advance').click()
                assert advanced.value.json()['clockSeconds'] == 1800
                expect(page.locator('#dora-session-renew')).to_be_enabled()

            def stop(page, sid):
                with page.expect_response('**/api/dhcp/session/stop') as response:
                    page.locator('#dora-session-stop').click()
                assert response.value.status == 200
                assert response.value.json() == {'status': 'STOPPED'}
                assert sid not in server.dhcp_sessions._sessions

            def change(page, selector, value):
                page.evaluate("""({selector, value}) => {
                  const field = document.querySelector(selector);
                  field.value = value;
                  field.dispatchEvent(new Event(field.tagName === 'SELECT' ? 'change' : 'input',
                    {bubbles: true}));
                }""", {'selector': selector, 'value': value})

            # Double Start, then a project replacement before the allocated
            # ID reaches app code. The exact orphan is stopped.
            page = fresh()
            starts = []
            page.on('request', lambda request: starts.append(request) if
                    request.url.endswith('/api/dhcp/session/start') else None)
            hold_http_reply(page, '/api/dhcp/session/start')
            with page.expect_response('**/api/dhcp/session/start') as allocated:
                page.locator('#dora-session-start').click()
            page.wait_for_function('window.__heldReply')
            page.locator('#dora-session-start').dispatch_event('click')
            assert len(starts) == 1
            page.once('dialog', lambda dialog: dialog.accept())
            page.locator('#new-project').click()
            with page.expect_response('**/api/dhcp/session/stop') as cleanup:
                release_http_reply(page)
            old = allocated.value.json()['sessionId']
            assert cleanup.value.status == 200
            assert old not in server.dhcp_sessions._sessions
            expect(page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
            page.close()

            # A changed Start input also makes an allocated server ID stale.
            page = fresh()
            hold_http_reply(page, '/api/dhcp/session/start')
            with page.expect_response('**/api/dhcp/session/start') as allocated:
                page.locator('#dora-session-start').click()
            page.wait_for_function('window.__heldReply')
            change(page, '#dora-pool-end', '192.0.2.72')
            with page.expect_response('**/api/dhcp/session/stop') as cleanup:
                release_http_reply(page)
            assert cleanup.value.status == 200
            old = allocated.value.json()['sessionId']
            assert old not in server.dhcp_sessions._sessions
            expect(page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
            page.close()

            # A processed Run retains the real lease even when its client
            # choice changes before delivery; its old trace is not relabelled.
            page = fresh()
            sid = start(page)
            hold_http_reply(page, '/api/dhcp/session/run')
            with page.expect_response('**/api/dhcp/session/run') as processed:
                page.locator('#dora-session-run').click()
            assert processed.value.status == 200
            page.wait_for_function('window.__heldReply')
            change(page, '#dora-client', '["client-2","eth0"]')
            release_http_reply(page)
            assert processed.value.json()['leaseCount'] == 1
            expect(page.locator('#dora-session-status')).to_contain_text('1 BOUND-lease')
            expect(page.locator('#dora-session-leases')).to_contain_text('client/eth0')
            expect(page.locator('#dora-session-result')).not_to_contain_text('DORA-status: ACK_RECEIVED')
            assert server.dhcp_sessions._sessions[sid].state()['operationCount'] == 1
            stop(page, sid)
            page.close()

            # A delayed Renew updates the actual lease, but a changed XID
            # must not receive the old renewal trace.
            page = fresh()
            sid = start(page)
            prepare_renew(page)
            hold_http_reply(page, '/api/dhcp/session/renew')
            with page.expect_response('**/api/dhcp/session/renew') as renewed:
                page.locator('#dora-session-renew').click()
            assert renewed.value.status == 200
            page.wait_for_function('window.__heldReply')
            change(page, '#dora-transaction-id', '102')
            release_http_reply(page)
            assert renewed.value.json()['result']['status'] == 'ACK_RECEIVED'
            expect(page.locator('#dora-session-leases')).to_contain_text('förnyelser 1')
            expect(page.locator('#dora-session-renew-result')).not_to_contain_text('DHCP-förnyelse:')
            stop(page, sid)
            page.close()

            # Stop may overtake Advance, Run, or Renew. Old replies and
            # finally blocks cannot revive the removed session.
            for path, setup, button in (
                ('run', lambda page: None, '#dora-session-run'),
                ('advance', lambda page: page.locator('#dora-session-advance-seconds').fill('1'),
                 '#dora-session-advance'),
                ('renew', prepare_renew, '#dora-session-renew'),
            ):
                page = fresh()
                sid = start(page)
                setup(page)
                hold_http_reply(page, '/api/dhcp/session/' + path)
                with page.expect_response('**/api/dhcp/session/' + path) as processed:
                    page.locator(button).click()
                assert processed.value.status == 200
                page.wait_for_function('window.__heldReply')
                stop(page, sid)
                release_http_reply(page)
                expect(page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
                page.close()

            # Real fault mutations survive a changed selector in the server
            # state but do not masquerade as a result for the new target.
            for path, button, selector, before, after, field in (
                ('link-fault', '#dora-session-fault-break', '#dora-session-fault-link',
                 'to-server', 'to-client', 'faultedLinks'),
                ('port-fault', '#dora-session-port-down', '#dora-session-port-fault',
                 '["sw","s"]', '["sw","c"]', 'faultedPorts'),
                ('vlan-fault', '#dora-session-vlan-set', '#dora-session-vlan-target',
                 '20', '30', 'faultedAccessVlans'),
                ('vlan-fault', '#dora-session-vlan-set', '#dora-session-vlan-port',
                 '["sw","c"]', '["sw","p-2"]', 'faultedAccessVlans'),
            ):
                page = fresh()
                sid = start(page)
                if path == 'vlan-fault':
                    page.locator('#dora-session-vlan-port').select_option('["sw","c"]')
                page.locator(selector).select_option(before)
                hold_http_reply(page, '/api/dhcp/session/' + path)
                with page.expect_response('**/api/dhcp/session/' + path) as processed:
                    page.locator(button).click()
                assert processed.value.status == 200
                page.wait_for_function('window.__heldReply')
                change(page, selector, after)
                release_http_reply(page)
                assert server.dhcp_sessions._sessions[sid].state()[field]
                expect(page.locator('#dora-session-status')).to_contain_text('Aktiv DHCP-session')
                stop(page, sid)
                page.close()

            # Reset processed before a workspace replacement cannot restore
            # old leases or old status in the replacement project.
            page = fresh()
            old = start(page)
            run(page)
            hold_http_reply(page, '/api/dhcp/session/reset')
            with page.expect_response('**/api/dhcp/session/reset') as reset:
                page.locator('#dora-session-reset').click()
            assert reset.value.status == 200
            page.wait_for_function('window.__heldReply')
            with page.expect_response('**/api/dhcp/session/stop'):
                replace(page)
            release_http_reply(page)
            assert reset.value.json()['leaseCount'] == 0
            expect(page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
            assert old not in server.dhcp_sessions._sessions
            page.close()

            # New, Open, and Import each invalidate an in-flight Run after
            # the server has processed it; no old lease enters the workspace.
            for replacement in ('new', 'open', 'import'):
                page = fresh()
                old = start(page)
                hold_http_reply(page, '/api/dhcp/session/run')
                with page.expect_response('**/api/dhcp/session/run') as processed:
                    page.locator('#dora-session-run').click()
                assert processed.value.status == 200
                page.wait_for_function('window.__heldReply')
                with page.expect_response('**/api/dhcp/session/stop') as cleanup:
                    if replacement == 'new':
                        page.once('dialog', lambda dialog: dialog.accept())
                        page.locator('#new-project').click()
                    elif replacement == 'open':
                        page.locator('#saved-projects').select_option('dora-race')
                        page.once('dialog', lambda dialog: dialog.accept())
                        with page.expect_response('**/api/projects/dora-race') as opened:
                            page.locator('#open-project').click()
                        assert opened.value.status == 200
                    else:
                        page.on('dialog', lambda dialog: dialog.accept())
                        with page.expect_response('**/api/validate') as imported:
                            page.locator('#import-file').set_input_files({
                                'name': 'dora-race.json', 'mimeType': 'application/json',
                                'buffer': json.dumps(project).encode('utf-8'),
                            })
                        assert imported.value.status == 200
                assert cleanup.value.status == 200
                release_http_reply(page)
                assert processed.value.json()['leaseCount'] == 1
                assert old not in server.dhcp_sessions._sessions
                expect(page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
                expect(page.locator('#dora-session-leases')).to_contain_text('Ingen aktiv lease-tabell')
                page.close()

            # A real validation 422 from A, delayed until B exists, may not
            # expire B or unlock B's current operation.
            page = fresh()
            old = start(page)
            page.evaluate("""() => {
              const original = window.fetch;
              window.fetch = (url, init) => {
                if (url === '/api/dhcp/session/run') {
                  const body = JSON.parse(init.body);
                  body.transactionId = 0;
                  window.fetch = original;
                  return original(url, {...init, body: JSON.stringify(body)});
                }
                return original(url, init);
              };
            }""")
            hold_http_reply(page, '/api/dhcp/session/run')
            with page.expect_response('**/api/dhcp/session/run') as stale_error:
                page.locator('#dora-session-run').click()
            assert stale_error.value.status == 422
            page.wait_for_function('window.__heldReply')
            with page.expect_response('**/api/dhcp/session/stop'):
                replace(page)
            newer = start(page)
            release_http_reply(page)
            assert stale_error.value.json()['error'] == 'INVALID_PROJECT'
            assert old not in server.dhcp_sessions._sessions
            assert newer in server.dhcp_sessions._sessions
            expect(page.locator('#dora-session-status')).to_contain_text('Aktiv DHCP-session')
            stop(page, newer)
            page.close()

            # A delayed Stop for A cannot clear B, including while B is busy.
            page = fresh()
            old = start(page)
            hold_http_reply(page, '/api/dhcp/session/stop', first_only=True)
            with page.expect_response('**/api/dhcp/session/stop') as stopped:
                page.locator('#dora-session-stop').click()
            assert stopped.value.status == 200
            page.wait_for_function('window.__heldReply')
            replace(page)
            newer = start(page)
            page.evaluate('window.__releaseOldStop = window.__releaseReply')
            hold_http_reply(page, '/api/dhcp/session/run')
            with page.expect_response('**/api/dhcp/session/run') as b_run:
                page.locator('#dora-session-run').click()
            assert b_run.value.status == 200
            page.wait_for_function('window.__heldReply')
            page.evaluate('window.__releaseOldStop()')
            assert stopped.value.json() == {'status': 'STOPPED'}
            expect(page.locator('#dora-session-run')).to_be_disabled()
            release_http_reply(page)
            assert newer != old and newer in server.dhcp_sessions._sessions
            expect(page.locator('#dora-session-status')).to_contain_text('Aktiv DHCP-session')
            stop(page, newer)
            page.close()

            # A real Stop is processed, but its response is lost in fetch.
            # The retry receives an exact real 422 and permits a new B.
            page = fresh()
            old = start(page)
            page.evaluate("""() => {
              const original = window.fetch;
              window.__lostDoraStop = null;
              window.fetch = async (url, init) => {
                if (url !== '/api/dhcp/session/stop') return original(url, init);
                window.fetch = original;
                const response = await original(url, init);
                window.__lostDoraStop = {
                  status: response.status, body: await response.clone().json(),
                };
                throw new TypeError('Stop reply lost after server processing');
              };
            }""")
            with page.expect_response('**/api/dhcp/session/stop') as processed_stop:
                page.locator('#dora-session-stop').click()
            assert processed_stop.value.status == 200
            page.wait_for_function('window.__lostDoraStop !== null')
            assert page.evaluate('window.__lostDoraStop') == {
                'status': 200, 'body': {'status': 'STOPPED'}}
            assert old not in server.dhcp_sessions._sessions
            expect(page.locator('#dora-session-result')).to_contain_text('Kunde inte bekräfta Stop')
            with page.expect_response('**/api/dhcp/session/stop') as missing:
                page.locator('#dora-session-stop').click()
            assert missing.value.status == 422
            assert missing.value.json() == {'error': 'INVALID_PROJECT',
                'message': 'dhcp session: unknown or expired session; start a new session'}
            expect(page.locator('#dora-session-start')).to_be_enabled()
            newer = start(page)
            assert newer != old and newer in server.dhcp_sessions._sessions
            stop(page, newer)
            page.close()

            # The server's existing idle worker reaps an abandoned ID.
            page = fresh()
            abandoned = start(page)
            page.close()
            assert abandoned in server.dhcp_sessions._sessions
            expired = threading.Event()
            original_cleanup = server.dhcp_sessions.cleanup_expired

            def observed_cleanup():
                count = original_cleanup()
                if abandoned not in server.dhcp_sessions._sessions:
                    expired.set()
                return count

            server.dhcp_sessions.cleanup_expired = observed_cleanup
            clock.now += IDLE_TIMEOUT_SECONDS
            assert expired.wait(2), 'server worker did not reap abandoned DORA session'
            page = fresh()
            current = start(page)
            clock.now += IDLE_TIMEOUT_SECONDS
            with page.expect_response('**/api/dhcp/session/run') as stale:
                page.locator('#dora-session-run').click()
            assert stale.value.status == 422
            expect(page.locator('#dora-session-start')).to_be_enabled()
            assert current not in server.dhcp_sessions._sessions
            page.close()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert not errors, errors
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
            assert not worker.is_alive()
            assert not server._cleanup_thread.is_alive()


def icmp_investigation_races(context, network_mode, errors):
    """Real ICMP server sessions with delivery held after HTTP processing."""
    class Clock:
        now = 100.0

        def __call__(self):
            return self.now

    clock = Clock()
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(directory)
        project = icmp_routed_lab()
        store.save('icmp-race', project)
        saved_file = Path(directory) / 'icmp-race.yadilab'
        digest = hashlib.sha256(saved_file.read_bytes()).hexdigest()
        server = LabHTTPServer(('127.0.0.1', 0), store,
                               clock=clock, cleanup_interval=.01)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}/'
        try:
            def load(page):
                page.once('dialog', lambda dialog: dialog.accept())
                with page.expect_response('**/api/validate') as imported:
                    page.locator('#import-file').set_input_files({
                        'name': 'icmp-race.json', 'mimeType': 'application/json',
                        'buffer': json.dumps(project).encode('utf-8'),
                    })
                assert imported.value.status == 200
                page.locator('#icmp-investigation-source').select_option('["a","eth0"]')
                page.locator('#icmp-investigation-destination').fill('203.0.113.20')
                page.locator('#icmp-investigation-ttl').fill('5')

            def fresh():
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
                assert browser_open(page, base) == network_mode
                load(page)
                return page

            def replace(page):
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#new-project').click()
                load(page)

            def start(page):
                # The first independently verified candidate is a real cable fault.
                with patch('network_core.icmp_investigation.secrets.randbelow', return_value=0):
                    with page.expect_response('**/api/icmp/investigation/start') as response:
                        page.locator('#icmp-investigation-start').click()
                assert response.value.status == 200
                sid = response.value.json()['sessionId']
                assert sid in server.icmp_investigations._sessions
                return sid

            def ready(page):
                for kind in ('address', 'ping', 'route'):
                    page.locator('#icmp-investigation-probe').select_option(kind)
                    with page.expect_response('**/api/icmp/investigation/probe') as measured:
                        page.locator('#icmp-investigation-measure').click()
                    assert measured.value.status == 200
                    if kind == 'ping':
                        observation = measured.value.json()['observation']
                        assert observation['status'] != 'REPLIED'
                        assert observation['replyMatched'] is False
                expect(page.locator('#icmp-investigation-diagnose')).to_be_enabled()

            def invalid_link_once(page):
                page.evaluate("""() => {
                  const original = window.fetch;
                  window.fetch = (url, init) => {
                    if (url === '/api/icmp/investigation/probe') {
                      const body = JSON.parse(init.body);
                      body.target = {linkId: 'not-a-documented-link'};
                      window.fetch = original;
                      return original(url, {...init, body: JSON.stringify(body)});
                    }
                    return original(url, init);
                  };
                }""")

            # C01–C03: one server allocation despite two Start events; a
            # workspace replacement before delivery causes targeted cleanup.
            page = fresh()
            requests = []
            page.on('request', lambda request: requests.append(request) if
                    request.url.endswith('/api/icmp/investigation/start') else None)
            hold_http_reply(page, '/api/icmp/investigation/start')
            with patch('network_core.icmp_investigation.secrets.randbelow', return_value=0):
                with page.expect_response('**/api/icmp/investigation/start') as allocated:
                    page.locator('#icmp-investigation-start').click()
            page.wait_for_function('window.__heldReply')
            page.locator('#icmp-investigation-start').dispatch_event('click')
            assert len(requests) == 1
            page.once('dialog', lambda dialog: dialog.accept())
            page.locator('#new-project').click()
            with page.expect_response('**/api/icmp/investigation/stop') as cleanup:
                release_http_reply(page)
            old = allocated.value.json()['sessionId']
            assert cleanup.value.status == 200
            assert old not in server.icmp_investigations._sessions
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Ingen ICMP-övning')
            page.close()

            # C05/C14: old link target is not labelled as the new one; a
            # second click while busy cannot mutate the server twice.
            page = fresh()
            sid = start(page)
            page.locator('#icmp-investigation-probe').select_option('link')
            page.locator('#icmp-investigation-link').select_option('la')
            probe_requests = []
            page.on('request', lambda request: probe_requests.append(request) if
                    request.url.endswith('/api/icmp/investigation/probe') else None)
            hold_http_reply(page, '/api/icmp/investigation/probe')
            with page.expect_response('**/api/icmp/investigation/probe') as first_probe:
                page.locator('#icmp-investigation-measure').click()
            page.wait_for_function('window.__heldReply')
            page.locator('#icmp-investigation-measure').dispatch_event('click')
            assert len(probe_requests) == 1
            page.evaluate("""() => {
              const field = document.querySelector('#icmp-investigation-link');
              field.value = 'lb'; field.dispatchEvent(new Event('change', {bubbles: true}));
            }""")
            release_http_reply(page)
            assert first_probe.value.json()['observation']['linkId'] == 'la'
            expect(page.locator('#icmp-investigation-observations')).not_to_contain_text('LÄNK la')
            assert server.icmp_investigations._sessions[sid].state()['observations'] == 1
            with page.expect_response('**/api/icmp/investigation/probe') as next_probe:
                page.locator('#icmp-investigation-measure').click()
            assert next_probe.value.json()['observation']['linkId'] == 'lb'
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.locator('#icmp-investigation-stop').click()
            page.close()

            # All six probe kinds freeze their relevant UI choices. Address
            # and ping become stale when kind changes; targeted probes become
            # stale when their route/link/port/VLAN selector changes.
            page = fresh()
            sid = start(page)
            for kind, selector, before, after in (
                ('address', '#icmp-investigation-probe', 'address', 'ping'),
                ('ping', '#icmp-investigation-probe', 'ping', 'address'),
                ('route', '#icmp-investigation-route-node', 'a', 'b'),
                ('link', '#icmp-investigation-link', 'la', 'lb'),
                ('port', '#icmp-investigation-port', '["a","eth0"]', '["b","eth0"]'),
                ('vlan', '#icmp-investigation-vlan', '["sw-left","a"]', '["sw-right","b"]'),
            ):
                page.locator('#icmp-investigation-probe').select_option(kind)
                if selector != '#icmp-investigation-probe':
                    page.locator(selector).select_option(before)
                hold_http_reply(page, '/api/icmp/investigation/probe')
                with page.expect_response('**/api/icmp/investigation/probe') as processed:
                    page.locator('#icmp-investigation-measure').click()
                assert processed.value.status == 200
                page.wait_for_function('window.__heldReply')
                page.evaluate("""({selector, value}) => {
                  const field = document.querySelector(selector);
                  field.value = value;
                  field.dispatchEvent(new Event('change', {bubbles: true}));
                }""", {'selector': selector, 'value': after})
                release_http_reply(page)
                expect(page.locator('#icmp-investigation-observations')).to_contain_text('Börja med IP-uppgifter')
            assert server.icmp_investigations._sessions[sid].state()['observations'] == 6
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.locator('#icmp-investigation-stop').click()
            page.close()

            # C06/C07: a processed old hypothesis updates server attempts but
            # never becomes a verdict for the newly selected hypothesis.
            page = fresh()
            sid = start(page)
            ready(page)
            page.locator('#icmp-investigation-diagnosis').select_option('PORT_SHUTDOWN')
            hold_http_reply(page, '/api/icmp/investigation/diagnose')
            with page.expect_response('**/api/icmp/investigation/diagnose') as old_guess:
                page.locator('#icmp-investigation-diagnose').click()
            page.wait_for_function('window.__heldReply')
            page.evaluate("""() => {
              const field = document.querySelector('#icmp-investigation-diagnosis');
              field.value = 'CABLE_DOWN'; field.dispatchEvent(new Event('change', {bubbles: true}));
            }""")
            release_http_reply(page)
            assert old_guess.value.json()['correct'] is False
            assert server.icmp_investigations._sessions[sid].state()['diagnosisAttempts'] == 1
            expect(page.locator('#icmp-investigation-verdict')).not_to_contain_text('DIAGNOS BEKRÄFTAD')
            with page.expect_response('**/api/icmp/investigation/diagnose') as right_guess:
                page.locator('#icmp-investigation-diagnose').click()
            assert right_guess.value.json()['correct'] is True
            expect(page.locator('#icmp-investigation-repair')).to_be_enabled()
            hold_http_reply(page, '/api/icmp/investigation/repair')
            with page.expect_response('**/api/icmp/investigation/repair') as repaired:
                page.locator('#icmp-investigation-repair').click()
            page.wait_for_function('window.__heldReply')
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.locator('#icmp-investigation-stop').click()
            release_http_reply(page)
            assert repaired.value.json()['status'] == 'RECOVERED'
            expect(page.locator('#icmp-investigation-recovery')).not_to_contain_text('RESULTAT: RECOVERED')
            assert sid not in server.icmp_investigations._sessions
            page.close()

            # C04: a real completed Probe cannot append to a replaced project.
            page = fresh()
            old = start(page)
            hold_http_reply(page, '/api/icmp/investigation/probe')
            with page.expect_response('**/api/icmp/investigation/probe') as measured:
                page.locator('#icmp-investigation-measure').click()
            assert measured.value.status == 200
            page.wait_for_function('window.__heldReply')
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#new-project').click()
            release_http_reply(page)
            expect(page.locator('#icmp-investigation-observations')).to_contain_text('Börja med IP-uppgifter')
            assert old not in server.icmp_investigations._sessions
            page.close()

            # C08: Stop for A is processed, but its response cannot clear B.
            page = fresh()
            old = start(page)
            hold_http_reply(page, '/api/icmp/investigation/stop', first_only=True)
            with page.expect_response('**/api/icmp/investigation/stop') as stopped:
                page.locator('#icmp-investigation-stop').click()
            assert stopped.value.status == 200
            page.wait_for_function('window.__heldReply')
            replace(page)
            newer = start(page)
            release_http_reply(page)
            assert newer != old
            assert newer in server.icmp_investigations._sessions
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Aktiv dold övning')
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.locator('#icmp-investigation-stop').click()
            page.close()

            # C09/C11: a real 422 from an invalid link is not expiration, and
            # a late 422 from A cannot invalidate a later session B.
            page = fresh()
            start(page)
            page.locator('#icmp-investigation-probe').select_option('link')
            page.locator('#icmp-investigation-link').select_option('la')
            invalid_link_once(page)
            with page.expect_response('**/api/icmp/investigation/probe') as rejected:
                page.locator('#icmp-investigation-measure').click()
            assert rejected.value.status == 422
            expect(page.locator('#icmp-investigation-observations')).to_contain_text('MÄTNING AVVISAD')
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Aktiv dold övning')
            invalid_link_once(page)
            hold_http_reply(page, '/api/icmp/investigation/probe')
            with page.expect_response('**/api/icmp/investigation/probe') as late_error:
                page.locator('#icmp-investigation-measure').click()
            assert late_error.value.status == 422
            page.wait_for_function('window.__heldReply')
            replace(page)
            newer = start(page)
            release_http_reply(page)
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Aktiv dold övning')
            expect(page.locator('#icmp-investigation-observations')).to_contain_text('Börja med IP-uppgifter')
            assert newer in server.icmp_investigations._sessions
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.locator('#icmp-investigation-stop').click()
            page.close()

            # An exact expiration error for A delivered after B starts must
            # not invalidate B or borrow its busy flag.
            page = fresh()
            old = start(page)
            clock.now += IDLE_TIMEOUT_SECONDS
            hold_http_reply(page, '/api/icmp/investigation/probe')
            with page.expect_response('**/api/icmp/investigation/probe') as stale_expiry:
                page.locator('#icmp-investigation-measure').click()
            assert stale_expiry.value.status == 422
            page.wait_for_function('window.__heldReply')
            replace(page)
            newer = start(page)
            release_http_reply(page)
            assert newer != old
            assert newer in server.icmp_investigations._sessions
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Aktiv dold övning')
            with page.expect_response('**/api/icmp/investigation/stop'):
                page.locator('#icmp-investigation-stop').click()
            page.close()

            # C12/C13: an uncertain Stop keeps the exact ID available for a
            # retry; neither a sent request nor a browser error proves removal.
            page = fresh()
            sid = start(page)
            page.evaluate("""() => {
              const original = window.fetch;
              window.fetch = (url, init) => {
                if (url === '/api/icmp/investigation/stop') {
                  window.fetch = original;
                  return Promise.reject(new TypeError('lost Stop request'));
                }
                return original(url, init);
              };
            }""")
            page.locator('#icmp-investigation-stop').click()
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Kunde inte bekräfta Stop')
            assert sid in server.icmp_investigations._sessions
            with page.expect_response('**/api/icmp/investigation/stop') as retried:
                page.locator('#icmp-investigation-stop').click()
            assert retried.value.status == 200
            assert sid not in server.icmp_investigations._sessions
            page.close()

            # Stop processed, response lost: the server has removed A, but
            # the controller must retain A until a real 422 confirms absence.
            page = fresh()
            old = start(page)
            stop_requests = []
            page.on('request', lambda request: stop_requests.append(request.post_data_json)
                    if request.url.endswith('/api/icmp/investigation/stop') else None)
            page.evaluate("""() => {
              const original = window.fetch;
              window.__lostStopResponse = null;
              window.fetch = async (url, init) => {
                if (url !== '/api/icmp/investigation/stop') return original(url, init);
                window.fetch = original;
                const response = await original(url, init);
                window.__lostStopResponse = {
                  status: response.status, body: await response.clone().json(),
                };
                throw new TypeError('Stop response lost after server processing');
              };
            }""")
            with page.expect_response('**/api/icmp/investigation/stop') as processed_stop:
                page.locator('#icmp-investigation-stop').click()
            assert processed_stop.value.status == 200
            assert processed_stop.value.json() == {'status': 'STOPPED'}
            page.wait_for_function('window.__lostStopResponse !== null')
            assert page.evaluate('window.__lostStopResponse') == {
                'status': 200, 'body': {'status': 'STOPPED'},
            }
            assert old not in server.icmp_investigations._sessions
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Kunde inte bekräfta Stop')
            expect(page.locator('#icmp-investigation-stop')).to_be_enabled()
            expect(page.locator('#icmp-investigation-start')).to_be_disabled()
            assert stop_requests == [{'sessionId': old}]

            with page.expect_response('**/api/icmp/investigation/stop') as absent_stop:
                page.locator('#icmp-investigation-stop').click()
            assert absent_stop.value.status == 422
            assert absent_stop.value.json() == {
                'error': 'INVALID_PROJECT',
                'message': 'icmp investigation: unknown or expired session',
            }
            assert stop_requests == [{'sessionId': old}, {'sessionId': old}]
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Ingen ICMP-övning')
            expect(page.locator('#icmp-investigation-status')).not_to_contain_text('Kunde inte bekräfta Stop')
            expect(page.locator('#icmp-investigation-start')).to_be_enabled()
            expect(page.locator('#icmp-investigation-stop')).to_be_disabled()

            newer = start(page)
            assert newer != old
            assert newer in server.icmp_investigations._sessions
            assert old not in server.icmp_investigations._sessions
            assert stop_requests == [{'sessionId': old}, {'sessionId': old}]
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Aktiv dold övning')
            with page.expect_response('**/api/icmp/investigation/stop') as final_stop:
                page.locator('#icmp-investigation-stop').click()
            assert final_stop.value.status == 200
            assert final_stop.value.json() == {'status': 'STOPPED'}
            assert stop_requests == [{'sessionId': old}, {'sessionId': old},
                                     {'sessionId': newer}]
            assert newer not in server.icmp_investigations._sessions
            page.close()

            # C15/C16: project replacement during processed Diagnose or
            # Repair prevents stale verdict and recovery in the new workspace.
            for path in ('diagnose', 'repair'):
                page = fresh()
                old = start(page)
                ready(page)
                page.locator('#icmp-investigation-diagnosis').select_option('CABLE_DOWN')
                if path == 'repair':
                    with page.expect_response('**/api/icmp/investigation/diagnose') as accepted:
                        page.locator('#icmp-investigation-diagnose').click()
                    assert accepted.value.json()['correct'] is True
                hold_http_reply(page, '/api/icmp/investigation/' + path)
                with page.expect_response('**/api/icmp/investigation/' + path) as processed:
                    page.locator('#icmp-investigation-' + path).click()
                assert processed.value.status == 200
                page.wait_for_function('window.__heldReply')
                with page.expect_response('**/api/icmp/investigation/stop'):
                    page.once('dialog', lambda dialog: dialog.accept())
                    page.locator('#new-project').click()
                release_http_reply(page)
                expect(page.locator('#icmp-investigation-verdict')).not_to_contain_text('DIAGNOS BEKRÄFTAD')
                expect(page.locator('#icmp-investigation-recovery')).not_to_contain_text('RESULTAT: RECOVERED')
                assert old not in server.icmp_investigations._sessions
                page.close()

            # C17: invalid TTL is rejected before any server allocation.
            page = fresh()
            before = len(server.icmp_investigations._sessions)
            page.locator('#icmp-investigation-ttl').fill('0')
            page.locator('#icmp-investigation-start').dispatch_event('click')
            expect(page.locator('#icmp-investigation-status')).to_contain_text('giltig TTL')
            assert len(server.icmp_investigations._sessions) == before
            page.close()

            # C10/C18: the server reaps an abandoned ID with no browser call;
            # an expired ID is rejected and the UI offers a new Start.
            page = fresh()
            old = start(page)
            page.close()
            assert old in server.icmp_investigations._sessions
            expired = threading.Event()
            original_cleanup = server.icmp_investigations.cleanup_expired

            def observed_cleanup():
                count = original_cleanup()
                if old not in server.icmp_investigations._sessions:
                    expired.set()
                return count

            server.icmp_investigations.cleanup_expired = observed_cleanup
            clock.now += IDLE_TIMEOUT_SECONDS
            assert expired.wait(2), 'server worker did not reap abandoned ICMP session'
            page = fresh()
            current = start(page)
            clock.now += IDLE_TIMEOUT_SECONDS
            with page.expect_response('**/api/icmp/investigation/probe') as old_probe:
                page.locator('#icmp-investigation-measure').click()
            assert old_probe.value.status == 422
            expect(page.locator('#icmp-investigation-status')).to_contain_text('Sessionen har upphört')
            expect(page.locator('#icmp-investigation-start')).to_be_enabled()
            assert current not in server.icmp_investigations._sessions
            new = start(page)
            assert new != current
            page.close()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert not errors, errors
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
            assert not worker.is_alive()
            assert not server._cleanup_thread.is_alive()


def persistence_races(context, base, network_mode, store, errors):
    """Exercise late Save/Open replies against actual server-backed files."""
    def fresh():
        test_page = context.new_page()
        test_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
        assert browser_open(test_page, base) == network_mode
        return test_page

    # A: a completed disk Save must not erase a newer local edit.
    page = fresh()
    page.locator('#project-filename').fill('race-save-edit')
    page.locator('#project-filename').dispatch_event('change')
    page.locator('#empty-add').click()
    page.locator('#node-label').fill('Original')
    page.locator('#node-label').dispatch_event('change')
    save_requests = []
    page.on('request', lambda request: save_requests.append(request)
            if request.url.endswith('/api/save') else None)
    hold_http_reply(page, '/api/save')
    page.locator('#save-project').click()
    page.wait_for_function('window.__heldReply')
    assert page.locator('#save-project').is_disabled()
    page.evaluate("document.querySelector('#save-project').click()")
    assert len(save_requests) == 1
    disk = store / 'race-save-edit.yadilab'
    original = disk.read_bytes()
    assert json.loads(original)['nodes'][0]['label'] == 'Original'
    page.locator('#node-label').fill('Newer edit')
    page.locator('#node-label').dispatch_event('change')
    release_http_reply(page)
    expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
    assert page.locator('#node-label').input_value() == 'Newer edit'
    assert disk.read_bytes() == original
    page.locator('#save-project').click()
    expect(page.locator('#save-indicator')).to_contain_text('Sparat · race-save-edit.yadilab')
    assert ProjectStore(store).read('race-save-edit')['project']['nodes'][0]['label'] == 'Newer edit'
    page.close()

    # C/F: a real disk conflict held until after another local edit cannot
    # retry the stale snapshot; the UI recovers for a later explicit Save.
    page = fresh()
    page.locator('#saved-projects').select_option('race-save-edit')
    page.locator('#open-project').click()
    expect(page.locator('#save-indicator')).to_contain_text('Sparat · race-save-edit.yadilab')
    page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
    page.locator('#node-label').fill('Local before conflict')
    page.locator('#node-label').dispatch_event('change')
    current = ProjectStore(store).read('race-save-edit')
    external = json.loads(json.dumps(current['project']))
    external['nodes'][0]['label'] = 'External change'
    external_saved = ProjectStore(store).save('race-save-edit', external, current['sha256'])
    hold_http_reply(page, '/api/save')
    page.locator('#save-project').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#node-label').fill('Local after conflict')
    page.locator('#node-label').dispatch_event('change')
    release_http_reply(page)
    expect(page.locator('#toast')).to_contain_text('Arbetsytan ändrades under sparning')
    expect(page.locator('#save-project')).to_be_enabled()
    expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
    assert ProjectStore(store).read('race-save-edit')['sha256'] == external_saved['sha256']
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#save-project').click()
    expect(page.locator('#save-indicator')).to_contain_text('Sparat · race-save-edit.yadilab')
    assert ProjectStore(store).read('race-save-edit')['project']['nodes'][0]['label'] == 'Local after conflict'
    page.close()

    # B: an old Save response cannot attach its SHA to a fresh workspace.
    page = fresh()
    page.locator('#project-filename').fill('race-save-switch')
    page.locator('#project-filename').dispatch_event('change')
    page.locator('#empty-add').click()
    hold_http_reply(page, '/api/save')
    page.locator('#save-project').click()
    page.wait_for_function('window.__heldReply')
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#new-project').click()
    expect(page.locator('#empty-state')).to_be_visible()
    release_http_reply(page)
    expect(page.locator('#save-project')).to_be_enabled()
    expect(page.locator('#save-indicator')).to_contain_text('Nytt projekt · ej sparat')
    assert ProjectStore(store).read('race-save-switch')['project']['nodes']
    page.close()

    # D: editing the current workspace while Open waits rejects the old file.
    page = fresh()
    page.locator('#empty-add').click()
    page.locator('#saved-projects').select_option('race-save-edit')
    hold_http_reply(page, '/api/projects/race-save-edit')
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#open-project').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#node-label').fill('Keep local edit')
    page.locator('#node-label').dispatch_event('change')
    release_http_reply(page)
    expect(page.locator('#toast')).to_contain_text('Öppningen avbröts')
    assert page.locator('#node-label').input_value() == 'Keep local edit'
    expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
    page.close()

    # E: changing the selected file prevents a late Open of the old choice.
    page = fresh()
    page.locator('#saved-projects').select_option('race-save-edit')
    hold_http_reply(page, '/api/projects/race-save-edit')
    page.locator('#open-project').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#saved-projects').select_option('race-save-switch')
    release_http_reply(page)
    expect(page.locator('#toast')).to_contain_text('Öppningen avbröts')
    expect(page.locator('#empty-state')).to_be_visible()
    page.close()


def transfer_races(context, base, network_mode, store, errors):
    """Keep real import/export HTTP replies pending while the Builder changes."""
    def fresh():
        test_page = context.new_page()
        test_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
        assert browser_open(test_page, base) == network_mode
        return test_page

    source = (store / 'csv-demo.yadilab').read_bytes()
    source_project = json.loads(source)
    source_file = {'name': 'source.yadilab', 'mimeType': 'application/json', 'buffer': source}
    saved_hash = hashlib.sha256(source).hexdigest()

    # A: a newer local edit makes a completed, valid import obsolete.
    page = fresh()
    page.locator('#empty-add').click()
    hold_http_reply(page, '/api/validate')
    page.locator('#import-file').set_input_files(source_file)
    page.wait_for_function('window.__heldReply')
    page.locator('#node-label').fill('Keep newer work')
    page.locator('#node-label').dispatch_event('change')
    release_http_reply(page)
    expect(page.locator('#toast')).to_contain_text('arbetsytan ändrades under import eller export')
    assert page.locator('#node-label').input_value() == 'Keep newer work'
    assert page.locator('[data-link-id]').count() == 0
    page.close()

    # B: even another workspace with similar content must reject the old import.
    page = fresh()
    hold_http_reply(page, '/api/validate')
    page.locator('#import-file').set_input_files(source_file)
    page.wait_for_function('window.__heldReply')
    page.locator('#load-example').click()
    expect(page.locator('#empty-state')).to_be_hidden()
    release_http_reply(page)
    expect(page.locator('#toast')).to_contain_text('arbetsytan ändrades under import eller export')
    expect(page.locator('[data-node-id="pc-1"]')).to_have_count(1)
    assert page.locator('[data-node-id="pc-a"]').count() == 0
    page.close()

    # C/D: declined, malformed and unsupported imports retain unsaved work.
    page = fresh()
    page.locator('#empty-add').click()
    page.locator('#node-label').fill('Unsaved local node')
    page.locator('#node-label').dispatch_event('change')
    page.once('dialog', lambda dialog: dialog.dismiss())
    with page.expect_response('**/api/validate') as valid_response:
        page.locator('#import-file').set_input_files(source_file)
    assert valid_response.value.status == 200
    page.wait_for_function('document.querySelector("#import-file").value === ""')
    assert page.locator('#node-label').input_value() == 'Unsaved local node'
    for name, data in (('invalid.yadilab', b'\xff'),
                       ('invalid.json', b'{"schemaVersion":"invalid"}'),
                       ('unsupported.txt', source)):
        page.locator('#import-file').set_input_files({
            'name': name, 'mimeType': 'application/octet-stream', 'buffer': data})
        expect(page.locator('#toast')).to_contain_text('Import avvisad:')
        page.wait_for_function('document.querySelector("#import-file").value === ""')
        assert page.locator('#node-label').input_value() == 'Unsaved local node'
        expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
    assert hashlib.sha256((store / 'csv-demo.yadilab').read_bytes()).hexdigest() == saved_hash
    page.close()

    # E: a delayed project export cannot combine old content with a new workspace.
    page = fresh()
    page.locator('#empty-add').click()
    downloads = []
    page.on('download', lambda download: downloads.append(download))
    hold_http_reply(page, '/api/validate')
    page.locator('#export-project').click()
    page.wait_for_function('window.__heldReply')
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#new-project').click()
    release_http_reply(page)
    expect(page.locator('#toast')).to_contain_text('arbetsytan ändrades under import eller export')
    assert not downloads
    expect(page.locator('#empty-state')).to_be_visible()
    page.close()

    # F: both spreadsheet formats suppress a download after a local edit.
    for format in ('xlsx', 'ods'):
        page = fresh()
        page.locator('#empty-add').click()
        downloads = []
        page.on('download', lambda download: downloads.append(download))
        hold_http_reply(page, '/api/export/spreadsheet')
        page.locator('#export-' + format).click()
        page.wait_for_function('window.__heldReply')
        page.locator('#node-label').fill('Changed during ' + format)
        page.locator('#node-label').dispatch_event('change')
        release_http_reply(page)
        expect(page.locator('#toast')).to_contain_text('arbetsytan ändrades under import eller export')
        assert not downloads
        page.close()

    # G: unchanged import and real browser download preserve explicit IDs.
    page = fresh()
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#import-file').set_input_files(source_file)
    expect(page.locator('[data-node-id="pc-a"]')).to_have_count(1)
    expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)
    with page.expect_download() as downloaded:
        page.locator('#export-project').click()
    assert downloaded.value.suggested_filename == 'lab.yadilab'
    exported = store / 'transfer-export.yadilab'
    downloaded.value.save_as(str(exported))
    assert json.loads(exported.read_bytes()) == source_project
    assert not (store / 'transfer-export-automatic.yadilab').exists()
    page.close()
    assert hashlib.sha256((store / 'csv-demo.yadilab').read_bytes()).hexdigest() == saved_hash


def diagnostic_races(context, base, network_mode, errors):
    """Use the routed saved lab and delay actual diagnostic HTTP replies."""
    source = json.dumps(['node-1', 'port-1'], separators=(',', ':'))

    def fresh():
        test_page = context.new_page()
        test_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
        assert browser_open(test_page, base) == network_mode
        test_page.locator('#saved-projects').select_option('lab')
        test_page.locator('#open-project').click()
        expect(test_page.locator('#save-indicator')).to_contain_text('Sparat · lab.yadilab')
        return test_page

    # A/B: real ARP learns MACs and highlights only currently documented wires.
    page = fresh()
    page.locator('#arp-source').select_option(source)
    page.locator('#arp-target-ip').fill('192.0.2.20')
    page.locator('#run-arp').click()
    expect(page.locator('#arp-result')).to_contain_text('ARP-status: RESOLVED')
    expect(page.locator('#arp-result')).to_contain_text('Inlärda switch-MAC-tabeller:')
    assert page.locator('.network-edge.highlight').count() > 0
    hold_http_reply(page, '/api/diagnostics/arp')
    page.locator('#run-arp').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#new-project').click()
    release_http_reply(page)
    expect(page.locator('#arp-result')).to_contain_text('Ingen aktuell ARP-simulering')
    assert page.locator('.network-edge.highlight').count() == 0
    page.close()

    # C: changing the route destination invalidates a delayed match.
    page = fresh()
    page.locator('#route-source').select_option('node-1')
    page.locator('#route-destination-ip').fill('192.0.2.20')
    hold_http_reply(page, '/api/routing/connected')
    page.locator('#run-route-lookup').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#route-destination-ip').fill('198.51.100.55')
    release_http_reply(page)
    expect(page.locator('#route-result')).to_contain_text('Ingen aktuell route lookup')
    page.close()

    # D: an old IPv4 hop sequence cannot survive a TTL edit.
    page = fresh()
    page.locator('#ipv4-source').select_option(source)
    page.locator('#ipv4-destination').fill('192.0.2.20')
    page.locator('#ipv4-ttl').fill('1')
    hold_http_reply(page, '/api/ipv4/trace')
    page.locator('#run-ipv4-trace').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#ipv4-ttl').fill('2')
    release_http_reply(page)
    expect(page.locator('#ipv4-result')).to_contain_text('Ingen aktuell IPv4-simulering')
    page.close()

    # E: an old Echo result cannot claim a reply for a changed destination.
    page = fresh()
    page.locator('#ping-source').select_option(source)
    page.locator('#ping-destination').fill('192.0.2.20')
    hold_http_reply(page, '/api/icmp/echo')
    page.locator('#run-ping').click()
    page.wait_for_function('window.__heldReply')
    page.locator('#ping-destination').fill('198.51.100.55')
    release_http_reply(page)
    expect(page.locator('#ping-result')).to_contain_text('Ingen aktuell ICMP Echo-utväxling')
    page.close()

    # F/G: second result wins, and a late 422 cannot erase a later success.
    for first, second, expected in (
        ('192.0.2.20', '198.51.100.55', 'Routingstatus: NO_ROUTE'),
        ('2001:db8::1', '192.0.2.20', 'Routingstatus: MATCH'),
    ):
        page = fresh()
        page.locator('#route-source').select_option('node-1')
        page.locator('#route-destination-ip').fill(first)
        hold_http_reply(page, '/api/routing/connected', first_only=True)
        page.locator('#run-route-lookup').click()
        page.wait_for_function('window.__heldReply')
        page.locator('#route-destination-ip').fill(second)
        page.locator('#run-route-lookup').click()
        expect(page.locator('#route-result')).to_contain_text(expected)
        release_http_reply(page)
        expect(page.locator('#route-result')).to_contain_text(expected)
        assert 'avvisad' not in page.locator('#route-result').inner_text()
        page.close()


def run():
    with tempfile.TemporaryDirectory() as td, sync_playwright() as playwright:
        store = Path(td)
        server_port = port()
        proc = spawn_server(server_port, store)
        executable = shutil.which('chromium') or shutil.which('chromium-browser')
        browser = playwright.chromium.launch(headless=True, executable_path=executable,
                                            args=['--no-sandbox'] if executable else [])
        context = browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
        errors=[]
        page=context.new_page()
        page.on('pageerror',lambda error: errors.append(getattr(error, 'stack', str(error))))
        module_responses = {}
        def record_module(response):
            for module in ('ui/dom.js', 'services/api.js', 'features/projects/persistence.js',
                           'features/projects/transfer.js', 'features/diagnostics/queries.js',
                           'features/diagnostics/presenters.js',
                           'features/sessions/dhcp-investigation.js',
                           'features/sessions/icmp-investigation.js',
                           'features/sessions/dora-session.js'):
                if response.url.endswith('/' + module):
                    module_responses[module] = response
        page.on('response', record_module)
        base=f'http://127.0.0.1:{server_port}/'
        try:
            network_mode = browser_open(page, base)
            expect(page.locator('#empty-state')).to_be_visible()
            if network_mode == 'DIRECT_HTTP':
                for module in ('ui/dom.js', 'services/api.js', 'features/projects/persistence.js',
                               'features/projects/transfer.js', 'features/diagnostics/queries.js',
                               'features/diagnostics/presenters.js',
                               'features/sessions/dhcp-investigation.js',
                               'features/sessions/icmp-investigation.js',
                               'features/sessions/dora-session.js'):
                    response = module_responses.get(module)
                    assert response is not None and response.status == 200, f'{module} was not loaded'
                    assert response.headers['content-type'].split(';')[0] in (
                        'text/javascript', 'application/javascript'), f'{module} has wrong MIME type'
            assert page.title() == config.APP_NAME + ' · Nätverkslabb'
            assert page.locator('.brand').get_attribute('aria-label') == config.APP_NAME
            expect(page.locator('.brand strong')).to_have_text(config.APP_NAME)
            expect(page.locator('.canvas-footer')).to_contain_text(config.APP_NAME)
            assert page.locator('.network-edge').count() == 0

            # First device is created with no inferred ports or links.
            page.locator('#empty-add').click()
            expect(page.locator('[data-node-id="node-1"]')).to_have_count(1)
            assert page.locator('[data-link-id]').count() == 0
            page.locator('#node-label').fill('Client Alpha')
            page.locator('#node-label').dispatch_event('change')
            page.locator('#new-port-name').fill('eth0')
            page.locator('#submit-port').click()
            expect(page.locator('[data-port-node="node-1"]')).to_have_count(1)
            # Deliberate configuration: real validator and no implicit autosave.
            page.locator('[data-port-mac="port-1"]').fill('02:00:00:00:00:0a')
            page.locator('[data-port-mac="port-1"]').dispatch_event('change')
            expect(page.locator('[data-port-mac="port-1"]')).to_have_value('02:00:00:00:00:0A')
            assert not (store / 'lab.yadilab').exists()

            page.locator('#add-node').click()
            expect(page.locator('[data-node-id="node-2"]')).to_have_count(1)
            page.locator('#node-kind').select_option('switch')
            page.locator('#new-port-name').fill('Gi1')
            page.locator('#submit-port').click()
            page.locator('#new-port-name').fill('Gi2')
            page.locator('#submit-port').click()
            # Explicit VLAN entry, validated by the real server; no file yet.
            page.locator('[data-port-vlan="port-1"]').fill('access:10')
            page.locator('[data-port-vlan="port-1"]').dispatch_event('change')
            expect(page.locator('[data-port-vlan="port-1"]')).to_have_value('access:10')
            page.locator('[data-port-vlan="port-2"]').fill('trunk:10,20')
            page.locator('[data-port-vlan="port-2"]').dispatch_event('change')
            expect(page.locator('[data-port-vlan="port-2"]')).to_have_value('trunk:10,20')
            assert not (store / 'lab.yadilab').exists()

            # Explicit physical connection (two deliberately chosen ports).
            page.locator('[data-port-node="node-1"]').click()
            page.locator('[data-port-node="node-2"][data-port-id="port-1"]').click()
            expect(page.locator('[data-link-id="link-1"]')).to_have_count(1)
            assert page.locator('[data-link-id]').count() == 1
            # The actual SVG path must start and end at the visible port dot.
            path = page.locator('[data-link-id="link-1"]').get_attribute('d')
            assert path.startswith('M ') and ' L ' in path, path
            # The path is grounded to the exact geometric center of both port circles.
            from_anchor = page.locator('[data-port-node="node-1"][data-port-id="port-1"]')
            to_anchor = page.locator('[data-port-node="node-2"][data-port-id="port-1"]')
            source = from_anchor.evaluate("el => ({x: el.cx.baseVal.value, y: el.cy.baseVal.value, transform: el.parentElement.getAttribute('transform')})")
            target = to_anchor.evaluate("el => ({x: el.cx.baseVal.value, y: el.cy.baseVal.value, transform: el.parentElement.getAttribute('transform')})")
            def absolute(point):
                import re
                match = re.fullmatch(r'translate\(([-.\d]+) ([-.\d]+)\)', point['transform'])
                assert match, point
                return (float(match[1]) + point['x'], float(match[2]) + point['y'])
            a, b = absolute(source), absolute(target)
            assert path.startswith(f'M {a[0]:g} {a[1]:g}'), (path,a)
            assert path.endswith(f'L {b[0]:g} {b[1]:g}'), (path,b)

            page.locator('#run-trace').click()
            expect(page.locator('#trace-result')).to_contain_text('Dokumenterad grafväg: 1 länk')
            expect(page.locator('#trace-result')).to_contain_text('Ingen IP- eller routingsimulering')

            # Fault injection affects graph trace but keeps the canonical link.
            page.locator('[data-item-type="link"][data-item-id="link-1"]').click()
            page.locator('#inspector input[type="checkbox"]').uncheck()
            assert page.locator('[data-link-id="link-1"]').count() == 1
            page.locator('#run-trace').click()
            expect(page.locator('#trace-result')).to_contain_text('Ingen aktiverad dokumenterad grafväg')
            page.locator('#inspector input[type="checkbox"]').check()

            # A delayed Save acknowledgment must not restore an older DOM
            # snapshot over edits made after clicking Save. The HTTP server
            # really writes the staged file before we release its response.
            page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            page.locator('#node-label').fill('Client Alpha at Save')
            page.locator('#node-label').dispatch_event('change')
            page.evaluate("""() => {
              window.__unwrappedFetch = window.fetch;
              window.__releaseSave = null;
              window.fetch = async (...args) => {
                const response = await window.__unwrappedFetch(...args);
                if (args[0] === '/api/save') {
                  return new Promise(resolve => {
                    window.__releaseSave = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            page.locator('#save-project').click()
            page.wait_for_function("typeof window.__releaseSave === 'function'")
            expect(page.locator('#save-project')).to_be_disabled()
            initial_disk = json.loads((store / 'lab.yadilab').read_bytes())
            assert initial_disk['nodes'][0]['label'] == 'Client Alpha at Save'
            page.locator('#node-label').fill('Client Alpha after Save click')
            page.locator('#node-label').dispatch_event('change')
            expect(page.locator('#node-label')).to_have_value('Client Alpha after Save click')
            page.evaluate('window.__releaseSave()')
            expect(page.locator('#save-project')).to_be_enabled()
            expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            expect(page.locator('#node-label')).to_have_value('Client Alpha after Save click')
            assert json.loads((store / 'lab.yadilab').read_bytes()) == initial_disk
            page.evaluate('window.fetch = window.__unwrappedFetch')

            # A new explicit Save writes the newer state, never autosave.
            page.locator('#save-project').click()
            expect(page.locator('#save-indicator')).to_contain_text('Sparat · lab.yadilab',timeout=12000)
            saved_file=store / 'lab.yadilab'
            assert saved_file.is_file(), 'No real .yadilab created on disk'
            saved_data=saved_file.read_bytes()
            digest=hashlib.sha256(saved_data).hexdigest()
            parsed=json.loads(saved_data)
            assert len(parsed['nodes']) == 2 and len(parsed['links']) == 1
            assert parsed['schemaVersion'] == '1.3'
            assert parsed['nodes'][0]['ports'][0]['mac'] == '02:00:00:00:00:0A'
            assert parsed['nodes'][1]['ports'][0]['vlan'] == {'mode':'access','vlan':10}
            assert parsed['nodes'][1]['ports'][1]['vlan'] == {'mode':'trunk','allowedVlans':[10,20]}
            assert parsed['links'][0]['a'] == {'node':'node-1','port':'port-1'}
            assert parsed['links'][0]['b'] == {'node':'node-2','port':'port-1'}
            assert parsed['links'][0]['enabled'] is True
            assert not errors, errors
            # Product UI screenshot from the same real Chromium interaction.
            page.screenshot(path=str(ROOT / 'ui_preview.png'), full_page=True)
            page.close()
            context.close(); browser.close()
            stop_server(proc)

            # Full server process restart and NEW browser process/session.
            proc=spawn_server(server_port,store)
            browser=playwright.chromium.launch(headless=True, executable_path=executable,
                                               args=['--no-sandbox'] if executable else [])
            context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
            page=context.new_page()
            page.on('pageerror',lambda error: errors.append(getattr(error, 'stack', str(error))))
            network_mode = browser_open(page, base)
            page.locator('#saved-projects').select_option('lab')
            page.locator('#open-project').click()
            expect(page.locator('#save-indicator')).to_contain_text('Sparat · lab.yadilab',timeout=12000)
            expect(page.locator('[data-node-id="node-1"]')).to_have_count(1)
            expect(page.locator('[data-node-id="node-2"]')).to_have_count(1)
            expect(page.locator('[data-link-id="link-1"]')).to_have_count(1)
            page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            expect(page.locator('[data-port-mac="port-1"]')).to_have_value('02:00:00:00:00:0A')
            page.locator('[data-item-type="node"][data-item-id="node-2"]').click()
            expect(page.locator('[data-port-vlan="port-1"]')).to_have_value('access:10')
            expect(page.locator('[data-port-vlan="port-2"]')).to_have_value('trunk:10,20')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # A stale Open result must not overwrite a workspace replaced
            # while the real server read was in flight.
            page.evaluate("""() => {
              window.__unwrappedFetch = window.fetch;
              window.__releaseOpen = null;
              window.fetch = async (...args) => {
                const response = await window.__unwrappedFetch(...args);
                if (args[0] === '/api/projects/lab') {
                  return new Promise(resolve => {
                    window.__releaseOpen = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            page.locator('#saved-projects').select_option('lab')
            page.locator('#open-project').click()
            page.wait_for_function("typeof window.__releaseOpen === 'function'")
            page.locator('#new-project').click()
            expect(page.locator('#empty-state')).to_be_visible()
            page.evaluate('window.__releaseOpen()')
            expect(page.locator('#toast')).to_contain_text('Öppningen avbröts')
            expect(page.locator('#empty-state')).to_be_visible()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            page.evaluate('window.fetch = window.__unwrappedFetch')
            page.locator('#saved-projects').select_option('lab')
            page.locator('#open-project').click()
            expect(page.locator('#save-indicator')).to_contain_text('Sparat · lab.yadilab')
            expect(page.locator('[data-link-id="link-1"]')).to_have_count(1)

            # Explicit export contains only the canonical document format.
            with page.expect_download(timeout=12000) as download_event:
                page.locator('#export-project').click()
            download = download_event.value
            assert download.suggested_filename == 'lab.yadilab'
            exported = json.loads(Path(download.path()).read_bytes())
            assert exported == parsed, 'exported bytes do not represent saved canonical facts'

            # PR30: a separate real Chromium window imports explicit
            # DHCP network facts. The diagnostic must NOT allocate an IP,
            # modify another saved project or invent links/MAC addresses.
            dhcp_page = context.new_page()
            dhcp_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
            assert browser_open(dhcp_page, base) == network_mode
            dhcp_page.once('dialog', lambda dialog: dialog.accept())
            with dhcp_page.expect_response('**/api/validate') as imported_dhcp:
                dhcp_page.locator('#import-file').set_input_files({
                    'name': 'explicit-dhcp.json',
                    'mimeType': 'application/json',
                    'buffer': json.dumps(dhcp_topology()).encode('utf-8'),
                })
            assert imported_dhcp.value.status == 200
            expect(dhcp_page.locator('[data-node-id="client"]')).to_have_count(1)
            expect(dhcp_page.locator('[data-node-id="server"]')).to_have_count(1)
            expect(dhcp_page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            dhcp_page.locator('#dhcp-client').select_option(
                json.dumps(['client', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dhcp-server').select_option(
                json.dumps(['server', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dhcp-offered-ip').fill('192.0.2.70')
            dhcp_page.locator('#dhcp-transaction-id').fill('305419896')
            dhcp_page.locator('#dhcp-lease-seconds').fill('3600')
            with dhcp_page.expect_response('**/api/dhcp/discover-offer') as valid_dhcp:
                dhcp_page.locator('#run-dhcp').click()
            assert valid_dhcp.value.status == 200
            data = valid_dhcp.value.json()
            assert data['status'] == 'OFFER_RECEIVED'
            assert [t['linkId'] for t in data['discover']['transmissions']] == [
                'to-client', 'to-server']
            assert [t['linkId'] for t in data['offer']['transmissions']] == [
                'to-server', 'to-client']
            assert data['leaseCommitted'] is False
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('DHCP-status: OFFER_RECEIVED')
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('to-server: sw/s → server/eth0')
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('Lease skapad: NEJ')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert sorted(x.name for x in store.glob('*.yadilab')) == ['lab.yadilab']

            # Disconnect the existing server wire. Seeing a switch and a
            # client is not enough to fabricate reception or an offer.
            dhcp_page.locator('[data-item-type="link"][data-item-id="to-server"]').click()
            dhcp_page.locator('#inspector input[type="checkbox"]').uncheck()
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('Ingen aktuell DHCP-diagnostik')
            with dhcp_page.expect_response('**/api/dhcp/discover-offer') as broken_dhcp:
                dhcp_page.locator('#run-dhcp').click()
            assert broken_dhcp.value.json()['status'] == 'DISCOVER_NOT_RECEIVED'
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('DHCP-status: DISCOVER_NOT_RECEIVED')
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('OFFER (server → broadcast): 0')
            dhcp_page.locator('#inspector input[type="checkbox"]').check()

            # Switch access VLAN 10 and 20 must isolate the DHCP server.
            dhcp_page.locator('[data-item-type="node"][data-item-id="sw"]').click()
            dhcp_page.locator('[data-port-vlan="c"]').fill('access:10')
            dhcp_page.locator('[data-port-vlan="c"]').dispatch_event('change')
            expect(dhcp_page.locator('[data-port-vlan="c"]')).to_have_value('access:10')
            dhcp_page.locator('[data-port-vlan="s"]').fill('access:20')
            dhcp_page.locator('[data-port-vlan="s"]').dispatch_event('change')
            expect(dhcp_page.locator('[data-port-vlan="s"]')).to_have_value('access:20')
            with dhcp_page.expect_response('**/api/dhcp/discover-offer') as isolated_dhcp:
                dhcp_page.locator('#run-dhcp').click()
            assert isolated_dhcp.value.json()['status'] == 'DISCOVER_NOT_RECEIVED'
            assert isolated_dhcp.value.json()['offer']['transmissions'] == []
            dhcp_page.locator('[data-port-vlan="s"]').fill('access:10')
            dhcp_page.locator('[data-port-vlan="s"]').dispatch_event('change')
            with dhcp_page.expect_response('**/api/dhcp/discover-offer') as restored_dhcp:
                dhcp_page.locator('#run-dhcp').click()
            assert restored_dhcp.value.json()['status'] == 'OFFER_RECEIVED'
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('DHCP-status: OFFER_RECEIVED')

            # Server's own address is already in use; fail closed with HTTP
            # 422 and never show a stale previous success.
            dhcp_page.locator('#dhcp-offered-ip').fill('192.0.2.1')
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('Ingen aktuell DHCP-diagnostik')
            with dhcp_page.expect_response('**/api/dhcp/discover-offer') as bad_offer:
                dhcp_page.locator('#run-dhcp').click()
            assert bad_offer.value.status == 422
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('DHCP-diagnostik avvisad')
            assert 'OFFER_RECEIVED' not in dhcp_page.locator('#dhcp-result').inner_text()

            # An HTTP request may complete on the server but the browser
            # must discard its response if the proposal changed meanwhile.
            dhcp_page.locator('#dhcp-offered-ip').fill('192.0.2.70')
            dhcp_page.evaluate("""() => {
              window.__originalDhcpFetch = window.fetch;
              window.__releaseDhcp = null;
              window.fetch = async (...args) => {
                const response = await window.__originalDhcpFetch(...args);
                if (args[0] === '/api/dhcp/discover-offer') {
                  return new Promise(resolve => {
                    window.__releaseDhcp = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            dhcp_page.locator('#run-dhcp').click()
            dhcp_page.wait_for_function("typeof window.__releaseDhcp === 'function'")
            expect(dhcp_page.locator('#run-dhcp')).to_be_disabled()
            dhcp_page.locator('#dhcp-offered-ip').fill('192.0.2.71')
            dhcp_page.evaluate('window.__releaseDhcp()')
            expect(dhcp_page.locator('#run-dhcp')).to_be_enabled()
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('Ingen aktuell DHCP-diagnostik')
            dhcp_page.evaluate('window.fetch = window.__originalDhcpFetch')
            with dhcp_page.expect_response('**/api/dhcp/discover-offer') as fresh_dhcp:
                dhcp_page.locator('#run-dhcp').click()
            assert fresh_dhcp.value.json()['offeredIpv4'] == '192.0.2.71'
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('Föreslagen IP: 192.0.2.71')
            dhcp_page.locator('[data-item-type="node"][data-item-id="client"]').click()
            expect(dhcp_page.locator('[data-port-ipv4="eth0"]')).to_have_value('')

            # PR32: the new DORA Builder panel must execute the genuine
            # four-packet HTTP exchange, not infer a lease from an Offer.
            # The documented project is still the same unsaved imported one.
            dhcp_page.locator('#dora-client').select_option(
                json.dumps(['client', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dora-server').select_option(
                json.dumps(['server', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dora-pool-start').fill('192.0.2.70')
            dhcp_page.locator('#dora-pool-end').fill('192.0.2.72')
            dhcp_page.locator('#dora-transaction-id').fill('12345')
            dhcp_page.locator('#dora-lease-seconds').fill('3600')
            with dhcp_page.expect_response('**/api/dhcp/dora') as dora_good:
                dhcp_page.locator('#run-dora').click()
            dora_good_data = dora_good.value.json()
            assert dora_good.value.status == 200
            assert dora_good_data['status'] == 'ACK_RECEIVED'
            assert dora_good_data['leaseCommitted'] is True
            assert dora_good_data['lease']['ipv4'] == '192.0.2.70'
            assert dora_good_data['lease']['state'] == 'BOUND'
            assert dora_good_data['transactionId'] == 12345
            for phase, wires in (
                ('discover', ['to-client', 'to-server']),
                ('offer', ['to-server', 'to-client']),
                ('request', ['to-client', 'to-server']),
                ('ack', ['to-server', 'to-client']),
            ):
                assert [t['linkId'] for t in dora_good_data[phase]['transmissions']] == wires
            expect(dhcp_page.locator('#dora-result')).to_contain_text('DORA-status: ACK_RECEIVED')
            expect(dhcp_page.locator('#dora-result')).to_contain_text('SIMULERAD BOUND-lease: 192.0.2.70')
            expect(dhcp_page.locator('#dora-result')).to_contain_text('ACK nådde ursprunglig klientport: ja')
            # The separate legacy read-only diagnostic remains unchanged.
            expect(dhcp_page.locator('#dhcp-result')).to_contain_text('DHCP-status: OFFER_RECEIVED')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # Every HTTP request starts with no old leases. The same pool
            # selects the first unused address again; no shared server state.
            with dhcp_page.expect_response('**/api/dhcp/dora') as dora_repeat:
                dhcp_page.locator('#run-dora').click()
            assert dora_repeat.value.json()['lease']['ipv4'] == '192.0.2.70'

            # Server's own IP cannot be offered from a one-address pool.
            dhcp_page.locator('#dora-pool-start').fill('192.0.2.1')
            dhcp_page.locator('#dora-pool-end').fill('192.0.2.1')
            expect(dhcp_page.locator('#dora-result')).to_contain_text('Ingen aktuell DORA-diagnostik')
            with dhcp_page.expect_response('**/api/dhcp/dora') as bad_dora:
                dhcp_page.locator('#run-dora').click()
            assert bad_dora.value.status == 422
            expect(dhcp_page.locator('#dora-result')).to_contain_text('DORA avvisad:')
            assert 'SIMULERAD BOUND-lease' not in dhcp_page.locator('#dora-result').inner_text()

            dhcp_page.locator('#dora-pool-start').fill('192.0.2.70')
            dhcp_page.locator('#dora-pool-end').fill('192.0.2.72')
            # Broken existing cable means no DISCOVER at server and no ACK.
            dhcp_page.locator('[data-item-type="link"][data-item-id="to-server"]').click()
            dhcp_page.locator('#inspector input[type="checkbox"]').uncheck()
            with dhcp_page.expect_response('**/api/dhcp/dora') as dora_disconnected:
                dhcp_page.locator('#run-dora').click()
            disconnected = dora_disconnected.value.json()
            assert disconnected['status'] == 'DISCOVER_NOT_RECEIVED'
            assert disconnected['leaseCommitted'] is False
            assert disconnected['ack']['transmissions'] == []
            expect(dhcp_page.locator('#dora-result')).to_contain_text('DORA-status: DISCOVER_NOT_RECEIVED')
            expect(dhcp_page.locator('#dora-result')).to_contain_text('Ingen simulerad lease bekräftad')
            dhcp_page.locator('#inspector input[type="checkbox"]').check()

            # VLAN isolation also prevents a lease; restoring the VLAN
            # permits all four packets again with no guessed relay.
            dhcp_page.locator('[data-item-type="node"][data-item-id="sw"]').click()
            dhcp_page.locator('[data-port-vlan="s"]').fill('access:20')
            dhcp_page.locator('[data-port-vlan="s"]').dispatch_event('change')
            with dhcp_page.expect_response('**/api/dhcp/dora') as dora_isolated:
                dhcp_page.locator('#run-dora').click()
            assert dora_isolated.value.json()['status'] == 'DISCOVER_NOT_RECEIVED'
            assert dora_isolated.value.json()['lease'] is None
            dhcp_page.locator('[data-port-vlan="s"]').fill('access:10')
            dhcp_page.locator('[data-port-vlan="s"]').dispatch_event('change')
            with dhcp_page.expect_response('**/api/dhcp/dora') as dora_restored:
                dhcp_page.locator('#run-dora').click()
            assert dora_restored.value.json()['status'] == 'ACK_RECEIVED'
            expect(dhcp_page.locator('#dora-result')).to_contain_text('SIMULERAD BOUND-lease: 192.0.2.70')

            # A delayed but genuinely completed DORA HTTP response must
            # be discarded after its input snapshot has been superseded.
            dhcp_page.evaluate("""() => {
              window.__unwrappedDoraFetch = window.fetch;
              window.__releaseDora = null;
              window.fetch = async (...args) => {
                const response = await window.__unwrappedDoraFetch(...args);
                if (args[0] === '/api/dhcp/dora') {
                  return new Promise(resolve => {
                    window.__releaseDora = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            dhcp_page.locator('#run-dora').click()
            dhcp_page.wait_for_function("typeof window.__releaseDora === 'function'")
            expect(dhcp_page.locator('#run-dora')).to_be_disabled()
            dhcp_page.locator('#dora-pool-start').fill('192.0.2.71')
            dhcp_page.evaluate('window.__releaseDora()')
            expect(dhcp_page.locator('#run-dora')).to_be_enabled()
            expect(dhcp_page.locator('#dora-result')).to_contain_text('Ingen aktuell DORA-diagnostik')
            dhcp_page.evaluate('window.fetch = window.__unwrappedDoraFetch')
            with dhcp_page.expect_response('**/api/dhcp/dora') as fresh_dora:
                dhcp_page.locator('#run-dora').click()
            assert fresh_dora.value.status == 200
            assert fresh_dora.value.json()['lease']['ipv4'] == '192.0.2.71'
            expect(dhcp_page.locator('#dora-result')).to_contain_text('SIMULERAD BOUND-lease: 192.0.2.71')
            dhcp_page.locator('[data-item-type="node"][data-item-id="client"]').click()
            expect(dhcp_page.locator('[data-port-ipv4="eth0"]')).to_have_value('')
            expect(dhcp_page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert sorted(x.name for x in store.glob('*.yadilab')) == ['lab.yadilab']

            # PR33: real browser imports explicit multi-client topology, then
            # assigns two UNIQUE IPs in the SAME process-local DHCP session.
            # A second session must start fresh and no project is auto-saved.
            # This workspace is dirty: import must explicitly approve BOTH
            # discard of unsaved edits and replacement of the current graph.
            dhcp_page.on('dialog', lambda dialog: dialog.accept())
            with dhcp_page.expect_response('**/api/validate') as imported_multi:
                dhcp_page.locator('#import-file').set_input_files({
                    'name': 'explicit-dhcp-multi.json',
                    'mimeType': 'application/json',
                    'buffer': json.dumps(dhcp_multi_clients()).encode('utf-8'),
                })
            assert imported_multi.value.status == 200
            expect(dhcp_page.locator('[data-node-id="client-2"]')).to_have_count(1)
            expect(dhcp_page.locator('[data-node-id="client-3"]')).to_have_count(1)
            dhcp_page.locator('#dora-server').select_option(
                json.dumps(['server', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dora-client').select_option(
                json.dumps(['client', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dora-pool-start').fill('192.0.2.70')
            dhcp_page.locator('#dora-pool-end').fill('192.0.2.71')
            dhcp_page.locator('#dora-transaction-id').fill('101')
            dhcp_page.locator('#dora-lease-seconds').fill('3600')
            with dhcp_page.expect_response('**/api/dhcp/session/start') as multi_start:
                dhcp_page.locator('#dora-session-start').click()
            assert multi_start.value.status == 200
            assert multi_start.value.json()['leaseCount'] == 0
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('Aktiv DHCP-session')
            expect(dhcp_page.locator('#dora-session-run')).to_be_enabled()
            expect(dhcp_page.locator('#dora-server')).to_be_disabled()
            expect(dhcp_page.locator('#dora-pool-start')).to_be_disabled()
            expect(dhcp_page.locator('#run-dora')).to_be_disabled()
            with dhcp_page.expect_response('**/api/dhcp/session/run') as multi_first:
                dhcp_page.locator('#dora-session-run').click()
            first_lease = multi_first.value.json()
            assert first_lease['result']['status'] == 'ACK_RECEIVED'
            assert first_lease['leaseCount'] == 1
            assert first_lease['result']['lease']['ipv4'] == '192.0.2.70'
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text(
                'client/eth0 · 02:00:00:00:00:0A → 192.0.2.70')
            dhcp_page.locator('#dora-client').select_option(
                json.dumps(['client-2', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dora-transaction-id').fill('102')
            # Choosing another client must preserve the first lease.
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('192.0.2.70')
            with dhcp_page.expect_response('**/api/dhcp/session/run') as multi_second:
                dhcp_page.locator('#dora-session-run').click()
            second_lease = multi_second.value.json()
            assert second_lease['result']['status'] == 'ACK_RECEIVED'
            assert second_lease['result']['lease']['ipv4'] == '192.0.2.71'
            assert second_lease['leaseCount'] == 2
            assert [v['ipv4'] for v in second_lease['leases']] == [
                '192.0.2.70', '192.0.2.71']
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('client-2/eth0')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('192.0.2.71')
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('2 BOUND-lease')
            # Exhaustion returns 422; existing table cannot be cleared
            # or claim a successful DHCP ACK for the third client.
            dhcp_page.locator('#dora-client').select_option(
                json.dumps(['client-3', 'eth0'], separators=(',', ':')))
            dhcp_page.locator('#dora-transaction-id').fill('103')
            with dhcp_page.expect_response('**/api/dhcp/session/run') as multi_full:
                dhcp_page.locator('#dora-session-run').click()
            assert multi_full.value.status == 422
            expect(dhcp_page.locator('#dora-session-result')).to_contain_text('pool exhausted')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('192.0.2.70')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('192.0.2.71')
            assert 'client-3/eth0' not in dhcp_page.locator('#dora-session-leases').inner_text()

            # PR34: explicit simulated time, never real-time waiting.
            # Leases remain BOUND at t=3599, then expire exactly at 3600.
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('simulerad tid 0 s')
            dhcp_page.locator('#dora-session-advance-seconds').fill('0')
            dhcp_page.locator('#dora-session-advance').click()
            expect(dhcp_page.locator('#dora-session-clock-result')).to_contain_text(
                'Tidshopp avvisat')
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('simulerad tid 0 s')
            dhcp_page.locator('#dora-session-advance-seconds').fill('3599')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as clock_3599:
                dhcp_page.locator('#dora-session-advance').click()
            almost_expired = clock_3599.value.json()
            assert clock_3599.value.status == 200
            assert almost_expired['clockSeconds'] == 3599
            assert almost_expired['expiredLeases'] == []
            assert almost_expired['leaseCount'] == 2
            assert [v['remainingSeconds'] for v in almost_expired['leases']] == [1, 1]
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('kvar 1 s')
            dhcp_page.locator('#dora-session-advance-seconds').fill('1')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as clock_3600:
                dhcp_page.locator('#dora-session-advance').click()
            now_expired = clock_3600.value.json()
            assert now_expired['clockSeconds'] == 3600
            assert now_expired['leaseCount'] == 0
            assert len(now_expired['expiredLeases']) == 2
            assert {v['ipv4'] for v in now_expired['expiredLeases']} == {
                '192.0.2.70', '192.0.2.71'}
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('simulerad tid 3600 s')
            expect(dhcp_page.locator('#dora-session-clock-result')).to_contain_text(
                'EXPIRED: client/eth0')
            expect(dhcp_page.locator('#dora-session-clock-result')).to_contain_text(
                'EXPIRED: client-2/eth0')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text(
                'Inga BOUND-leases')
            # The same exact pool is now eligible for a genuinely new DORA.
            with dhcp_page.expect_response('**/api/dhcp/session/run') as reused_after_expiry:
                dhcp_page.locator('#dora-session-run').click()
            reused = reused_after_expiry.value.json()
            assert reused['result']['status'] == 'ACK_RECEIVED'
            assert reused['result']['lease']['ipv4'] == '192.0.2.70'
            assert reused['result']['lease']['startedAtSeconds'] == 3600
            assert reused['result']['lease']['expiresAtSeconds'] == 7200
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text(
                'client-3/eth0')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text(
                'kvar 3600 s')

            # PR35: no automatic renewal; the first explicit T1 operation
            # must send a unicast DHCPREQUEST with ciaddr and receive ACK.
            expect(dhcp_page.locator('#dora-session-renew')).to_be_disabled()
            assert reused['leases'][0]['t1AtSeconds'] == 5400
            assert reused['leases'][0]['t2AtSeconds'] == 6750
            dhcp_page.locator('#dora-session-advance-seconds').fill('1800')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as t1_reached:
                dhcp_page.locator('#dora-session-advance').click()
            first_t1 = t1_reached.value.json()
            assert first_t1['clockSeconds'] == 5400
            assert first_t1['leases'][0]['renewalPhase'] == 'RENEWING'
            assert first_t1['leases'][0]['expiresAtSeconds'] == 7200
            expect(dhcp_page.locator('#dora-session-renew')).to_be_enabled()
            dhcp_page.locator('#dora-transaction-id').fill('104')
            with dhcp_page.expect_response('**/api/dhcp/session/renew') as t1_renew:
                dhcp_page.locator('#dora-session-renew').click()
            t1_renewal = t1_renew.value.json()
            assert t1_renew.value.status == 200
            assert t1_renewal['result']['phase'] == 'RENEWING'
            assert t1_renewal['result']['status'] == 'ACK_RECEIVED'
            assert t1_renewal['result']['leaseRenewed'] is True
            assert t1_renewal['result']['request']['ipDestination'] == '192.0.2.1'
            assert t1_renewal['result']['request']['ethernetDestination'] == '02:00:00:00:00:0B'
            assert [t['linkId'] for t in t1_renewal['result']['request']['transmissions']] == [
                'wire-3', 'to-server']
            assert t1_renewal['leases'][0]['expiresAtSeconds'] == 9000
            assert t1_renewal['leases'][0]['t1AtSeconds'] == 7200
            assert t1_renewal['leases'][0]['t2AtSeconds'] == 8550
            assert t1_renewal['leases'][0]['renewalCount'] == 1
            expect(dhcp_page.locator('#dora-session-renew-result')).to_contain_text(
                'FÖRNYAD BOUND-lease: 192.0.2.70')
            expect(dhcp_page.locator('#dora-session-renew')).to_be_disabled()

            # At the later T2 threshold this SAME leased client broadcasts
            # DHCPREQUEST, without inventing a second DHCP server or router.
            dhcp_page.locator('#dora-session-advance-seconds').fill('3150')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as t2_reached:
                dhcp_page.locator('#dora-session-advance').click()
            second_t2 = t2_reached.value.json()
            assert second_t2['clockSeconds'] == 8550
            assert second_t2['leases'][0]['renewalPhase'] == 'REBINDING'
            expect(dhcp_page.locator('#dora-session-renew')).to_be_enabled()
            dhcp_page.locator('#dora-transaction-id').fill('105')
            with dhcp_page.expect_response('**/api/dhcp/session/renew') as t2_renew:
                dhcp_page.locator('#dora-session-renew').click()
            t2_renewal = t2_renew.value.json()
            assert t2_renew.value.status == 200
            assert t2_renewal['result']['phase'] == 'REBINDING'
            assert t2_renewal['result']['request']['ipDestination'] == '255.255.255.255'
            assert t2_renewal['result']['request']['ethernetDestination'] == 'FF:FF:FF:FF:FF:FF'
            assert t2_renewal['result']['ack']['receivedAtClient'] is True
            assert t2_renewal['leases'][0]['ipv4'] == '192.0.2.70'
            assert t2_renewal['leases'][0]['expiresAtSeconds'] == 12150
            assert t2_renewal['leases'][0]['renewalCount'] == 2
            expect(dhcp_page.locator('#dora-session-renew-result')).to_contain_text(
                'DHCP-förnyelse: ACK_RECEIVED · REBINDING')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('förnyelser 2')
            # Neither renewal wrote a real client NIC IP or a project file.
            dhcp_page.locator('[data-item-type="node"][data-item-id="client-3"]').click()
            expect(dhcp_page.locator('[data-port-ipv4="eth0"]')).to_have_value('')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            with dhcp_page.expect_response('**/api/dhcp/session/reset') as multi_reset:
                dhcp_page.locator('#dora-session-reset').click()
            assert multi_reset.value.status == 200
            assert multi_reset.value.json()['leases'] == []
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('0 BOUND-lease')
            with dhcp_page.expect_response('**/api/dhcp/session/run') as multi_after_reset:
                dhcp_page.locator('#dora-session-run').click()
            assert multi_after_reset.value.json()['result']['lease']['ipv4'] == '192.0.2.70'

            # PR36: break an EXISTING physically documented server cable
            # after ACK, without changing graph/link flags or Save bytes.
            dhcp_page.locator('#dora-session-fault-link').select_option('to-server')
            expect(dhcp_page.locator('#dora-session-fault-break')).to_be_enabled()
            expect(dhcp_page.locator('#dora-session-fault-restore')).to_be_disabled()
            with dhcp_page.expect_response('**/api/dhcp/session/link-fault') as link_down:
                dhcp_page.locator('#dora-session-fault-break').click()
            down = link_down.value.json()
            assert link_down.value.status == 200
            assert down['faultedLinks'] == ['to-server']
            assert down['leaseCount'] == 1
            assert down['clockSeconds'] == 0
            assert down['macTables'] == []
            expect(dhcp_page.locator('#dora-session-fault-result')).to_contain_text(
                'Frånkopplad endast i sessionen: to-server')
            expect(dhcp_page.locator('#dora-session-fault-break')).to_be_disabled()
            expect(dhcp_page.locator('#dora-session-fault-restore')).to_be_enabled()
            dhcp_page.locator('[data-item-type="link"][data-item-id="to-server"]').click()
            expect(dhcp_page.locator('#inspector input[type="checkbox"]')).to_be_checked()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            dhcp_page.locator('#dora-session-advance-seconds').fill('1800')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as fault_t1_clock:
                dhcp_page.locator('#dora-session-advance').click()
            assert fault_t1_clock.value.json()['leases'][0]['renewalPhase'] == 'RENEWING'
            dhcp_page.locator('#dora-transaction-id').fill('106')
            with dhcp_page.expect_response('**/api/dhcp/session/renew') as fault_t1_renew:
                dhcp_page.locator('#dora-session-renew').click()
            lost_t1 = fault_t1_renew.value.json()
            assert lost_t1['result']['phase'] == 'RENEWING'
            assert lost_t1['result']['status'] == 'REQUEST_NOT_RECEIVED'
            assert lost_t1['result']['leaseRenewed'] is False
            assert lost_t1['result']['ack']['transmissions'] == []
            # Switch MAC learning was flushed by the cable transition.
            # Unknown unicast floods to other live client ports, never to
            # the disconnected server cable.
            assert [t['linkId'] for t in lost_t1['result']['request']['transmissions']] == [
                'wire-3', 'to-client', 'wire-2']
            assert lost_t1['result']['request']['receivedAtServer'] is False
            assert lost_t1['leases'][0]['expiresAtSeconds'] == 3600
            expect(dhcp_page.locator('#dora-session-renew-result')).to_contain_text(
                'DHCP-förnyelse: REQUEST_NOT_RECEIVED · RENEWING')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('slut vid 3600 s')

            dhcp_page.locator('#dora-session-advance-seconds').fill('1350')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as fault_t2_clock:
                dhcp_page.locator('#dora-session-advance').click()
            assert fault_t2_clock.value.json()['clockSeconds'] == 3150
            assert fault_t2_clock.value.json()['leases'][0]['renewalPhase'] == 'REBINDING'
            dhcp_page.locator('#dora-transaction-id').fill('107')
            with dhcp_page.expect_response('**/api/dhcp/session/renew') as fault_t2_renew:
                dhcp_page.locator('#dora-session-renew').click()
            lost_t2 = fault_t2_renew.value.json()
            assert lost_t2['result']['phase'] == 'REBINDING'
            assert lost_t2['result']['status'] == 'REQUEST_NOT_RECEIVED'
            assert lost_t2['result']['request']['ipDestination'] == '255.255.255.255'
            assert lost_t2['leases'][0]['expiresAtSeconds'] == 3600
            assert lost_t2['faultedLinks'] == ['to-server']

            dhcp_page.locator('#dora-session-advance-seconds').fill('450')
            with dhcp_page.expect_response('**/api/dhcp/session/advance') as fault_expire:
                dhcp_page.locator('#dora-session-advance').click()
            assert fault_expire.value.json()['clockSeconds'] == 3600
            assert fault_expire.value.json()['leaseCount'] == 0
            assert fault_expire.value.json()['expiredLeases'][0]['ipv4'] == '192.0.2.70'
            expect(dhcp_page.locator('#dora-session-clock-result')).to_contain_text('EXPIRED:')
            with dhcp_page.expect_response('**/api/dhcp/session/link-fault') as link_up:
                dhcp_page.locator('#dora-session-fault-restore').click()
            assert link_up.value.status == 200
            assert link_up.value.json()['faultedLinks'] == []
            expect(dhcp_page.locator('#dora-session-fault-result')).to_contain_text(
                'Återansluten endast i sessionen: to-server')
            dhcp_page.locator('#dora-transaction-id').fill('108')
            with dhcp_page.expect_response('**/api/dhcp/session/run') as after_link_restore:
                dhcp_page.locator('#dora-session-run').click()
            assert after_link_restore.value.json()['result']['status'] == 'ACK_RECEIVED'
            assert after_link_restore.value.json()['result']['lease']['ipv4'] == '192.0.2.70'
            expect(dhcp_page.locator('#inspector input[type="checkbox"]')).to_be_checked()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            with dhcp_page.expect_response('**/api/dhcp/session/stop') as multi_stop:
                dhcp_page.locator('#dora-session-stop').click()
            assert multi_stop.value.status == 200
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('Ingen aktiv lease-tabell')
            expect(dhcp_page.locator('#dora-pool-start')).to_be_enabled()
            with dhcp_page.expect_response('**/api/dhcp/session/start') as fresh_multi:
                dhcp_page.locator('#dora-session-start').click()
            assert fresh_multi.value.json()['leaseCount'] == 0

            # A real session run can finish on the server but be delayed in
            # the browser. An explicit topology edit must invalidate/stop
            # the session; its late response must not restore stale leases.
            dhcp_page.evaluate("""() => {
              window.__originalMultiFetch = window.fetch;
              window.__releaseMulti = null;
              window.fetch = async (...args) => {
                const response = await window.__originalMultiFetch(...args);
                if (args[0] === '/api/dhcp/session/run') {
                  return new Promise(resolve => {
                    window.__releaseMulti = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            dhcp_page.locator('#dora-session-run').click()
            dhcp_page.wait_for_function("typeof window.__releaseMulti === 'function'")
            expect(dhcp_page.locator('#dora-session-run')).to_be_disabled()
            dhcp_page.locator('[data-item-type="link"][data-item-id="to-server"]').click()
            dhcp_page.locator('#inspector input[type="checkbox"]').uncheck()
            expect(dhcp_page.locator('#dora-session-status')).to_contain_text('Ingen aktiv DHCP-session')
            dhcp_page.evaluate('window.__releaseMulti()')
            expect(dhcp_page.locator('#dora-session-leases')).to_contain_text('Ingen aktiv lease-tabell')
            dhcp_page.evaluate('window.fetch = window.__originalMultiFetch')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert sorted(x.name for x in store.glob('*.yadilab')) == ['lab.yadilab']
            expect(dhcp_page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert not errors, errors
            dhcp_page.close()

            # PR37: independent real Chromium VLAN lab. All hosts and
            # switch access VLANs are explicitly supplied by the imported
            # canonical project. Faults must never edit that source document.
            vlan_page = context.new_page()
            vlan_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
            assert browser_open(vlan_page, base) == network_mode
            vlan_page.once('dialog', lambda dialog: dialog.accept())
            with vlan_page.expect_response('**/api/validate') as vlan_import:
                vlan_page.locator('#import-file').set_input_files({
                    'name': 'declared-vlan-dhcp.json',
                    'mimeType': 'application/json',
                    'buffer': json.dumps(dhcp_vlan_clients()).encode('utf-8'),
                })
            assert vlan_import.value.status == 200
            expect(vlan_page.locator('[data-node-id="sw"]')).to_have_count(1)
            vlan_page.locator('#dora-client').select_option(
                json.dumps(['client', 'eth0'], separators=(',', ':')))
            vlan_page.locator('#dora-server').select_option(
                json.dumps(['server', 'eth0'], separators=(',', ':')))
            vlan_page.locator('#dora-pool-start').fill('192.0.2.70')
            vlan_page.locator('#dora-pool-end').fill('192.0.2.71')
            vlan_page.locator('#dora-transaction-id').fill('301')
            vlan_page.locator('#dora-lease-seconds').fill('60')
            with vlan_page.expect_response('**/api/dhcp/session/start') as vlan_start:
                vlan_page.locator('#dora-session-start').click()
            assert vlan_start.value.status == 200
            with vlan_page.expect_response('**/api/dhcp/session/run') as vlan_bound:
                vlan_page.locator('#dora-session-run').click()
            bound = vlan_bound.value.json()
            assert bound['result']['status'] == 'ACK_RECEIVED'
            assert bound['leases'][0]['expiresAtSeconds'] == 60
            expect(vlan_page.locator('#dora-session-vlan-port')).to_be_enabled()
            vlan_page.locator('#dora-session-port-fault').select_option(
                json.dumps(['sw', 's'], separators=(',', ':')))
            expect(vlan_page.locator('#dora-session-port-down')).to_be_enabled()
            with vlan_page.expect_response('**/api/dhcp/session/port-fault') as browser_port_down:
                vlan_page.locator('#dora-session-port-down').click()
            port_down = browser_port_down.value.json()
            assert browser_port_down.value.status == 200
            assert port_down['faultedPorts'] == [{'nodeId': 'sw', 'portId': 's'}]
            assert port_down['macTables'] == []
            expect(vlan_page.locator('#dora-session-port-result')).to_contain_text(
                'Avstängda switchportar i sessionen: sw/s')
            vlan_page.locator('[data-item-type="node"][data-item-id="sw"]').click()
            expect(vlan_page.locator('[data-port-vlan="s"]')).to_have_value('access:10')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            vlan_page.locator('#dora-session-advance-seconds').fill('30')
            with vlan_page.expect_response('**/api/dhcp/session/advance') as vlan_t1_time:
                vlan_page.locator('#dora-session-advance').click()
            assert vlan_t1_time.value.json()['leases'][0]['renewalPhase'] == 'RENEWING'
            vlan_page.locator('#dora-transaction-id').fill('302')
            with vlan_page.expect_response('**/api/dhcp/session/renew') as vlan_t1_attempt:
                vlan_page.locator('#dora-session-renew').click()
            t1_fault = vlan_t1_attempt.value.json()
            assert t1_fault['result']['status'] == 'REQUEST_NOT_RECEIVED'
            assert t1_fault['result']['request']['receivedAtServer'] is False
            assert t1_fault['leases'][0]['expiresAtSeconds'] == 60
            with vlan_page.expect_response('**/api/dhcp/session/port-fault') as browser_port_up:
                vlan_page.locator('#dora-session-port-up').click()
            assert browser_port_up.value.json()['faultedPorts'] == []
            expect(vlan_page.locator('#dora-session-port-down')).to_be_enabled()
            vlan_page.locator('#dora-session-vlan-port').select_option(
                json.dumps(['sw', 'c'], separators=(',', ':')))
            vlan_page.locator('#dora-session-vlan-target').select_option('20')
            expect(vlan_page.locator('#dora-session-vlan-set')).to_be_enabled()
            with vlan_page.expect_response('**/api/dhcp/session/vlan-fault') as browser_vlan_bad:
                vlan_page.locator('#dora-session-vlan-set').click()
            bad_vlan = browser_vlan_bad.value.json()
            assert browser_vlan_bad.value.status == 200
            assert bad_vlan['faultedAccessVlans'] == [{
                'nodeId': 'sw', 'portId': 'c', 'originalVlan': 10, 'faultVlan': 20,
            }]
            assert bad_vlan['macTables'] == []
            expect(vlan_page.locator('#dora-session-vlan-result')).to_contain_text(
                'sw/c VLAN 10 → 20')
            expect(vlan_page.locator('[data-port-vlan="c"]')).to_have_value('access:10')
            vlan_page.locator('#dora-session-advance-seconds').fill('23')
            with vlan_page.expect_response('**/api/dhcp/session/advance') as vlan_t2_time:
                vlan_page.locator('#dora-session-advance').click()
            assert vlan_t2_time.value.json()['leases'][0]['renewalPhase'] == 'REBINDING'
            vlan_page.locator('#dora-transaction-id').fill('303')
            with vlan_page.expect_response('**/api/dhcp/session/renew') as vlan_t2_attempt:
                vlan_page.locator('#dora-session-renew').click()
            t2_fault = vlan_t2_attempt.value.json()
            assert t2_fault['result']['phase'] == 'REBINDING'
            assert t2_fault['result']['status'] == 'REQUEST_NOT_RECEIVED'
            assert t2_fault['result']['request']['ipDestination'] == '255.255.255.255'
            assert t2_fault['leases'][0]['expiresAtSeconds'] == 60
            with vlan_page.expect_response('**/api/dhcp/session/vlan-fault') as browser_vlan_restore:
                vlan_page.locator('#dora-session-vlan-restore').click()
            assert browser_vlan_restore.value.json()['faultedAccessVlans'] == []
            vlan_page.locator('#dora-transaction-id').fill('304')
            with vlan_page.expect_response('**/api/dhcp/session/renew') as vlan_recovered:
                vlan_page.locator('#dora-session-renew').click()
            restored_lease = vlan_recovered.value.json()
            assert restored_lease['result']['status'] == 'ACK_RECEIVED'
            assert restored_lease['result']['ack']['receivedAtClient'] is True
            assert restored_lease['leases'][0]['expiresAtSeconds'] == 113
            assert restored_lease['leases'][0]['renewalCount'] == 1
            expect(vlan_page.locator('#dora-session-port-result')).to_contain_text(
                'Inga simulerade avstängda switchportar')
            expect(vlan_page.locator('#dora-session-vlan-result')).to_contain_text(
                'Inga simulerade VLAN-ändringar')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert sorted(x.name for x in store.glob('*.yadilab')) == ['lab.yadilab']
            expect(vlan_page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            with vlan_page.expect_response('**/api/dhcp/session/reset') as vlan_reset:
                vlan_page.locator('#dora-session-reset').click()
            assert vlan_reset.value.json()['clockSeconds'] == 0
            assert vlan_reset.value.json()['faultedPorts'] == []
            assert vlan_reset.value.json()['faultedAccessVlans'] == []
            assert vlan_reset.value.json()['leases'] == []
            assert not errors, errors

            # PR38: student sees only real observations; the server never
            # reveals hidden fault metadata before successful diagnosis.
            with vlan_page.expect_response('**/api/dhcp/investigation/start') as exercise_start:
                vlan_page.locator('#investigation-start').click()
            exercise = exercise_start.value.json()
            assert exercise_start.value.status == 200
            assert exercise['clockSeconds'] == 30
            assert exercise['remainingSeconds'] == 30
            assert exercise['expiresAtSeconds'] == 60
            assert 'faulted' not in json.dumps(exercise)
            assert not any(x in json.dumps(exercise) for x in (
                'CABLE_DOWN', 'PORT_SHUTDOWN', 'VLAN_MISMATCH'))
            expect(vlan_page.locator('#investigation-status')).to_contain_text(
                'Aktiv övning')
            expect(vlan_page.locator('#investigation-submit')).to_be_disabled()
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as measured_lease:
                vlan_page.locator('#investigation-run-probe').click()
            assert measured_lease.value.json()['observation']['status'] == 'BOUND'
            assert measured_lease.value.json()['observation']['remainingSeconds'] == 30
            vlan_page.locator('#investigation-probe').select_option('renew')
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as measured_renew:
                vlan_page.locator('#investigation-run-probe').click()
            symptom = measured_renew.value.json()['observation']
            assert symptom['status'] == 'REQUEST_NOT_RECEIVED'
            assert symptom['requestReachedServer'] is False
            assert symptom['ackReachedClient'] is False
            expect(vlan_page.locator('#investigation-observations')).to_contain_text(
                'DHCPREQUEST: REQUEST_NOT_RECEIVED')
            vlan_page.locator('#investigation-probe').select_option('link')
            vlan_page.locator('#investigation-link').select_option('to-server')
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as measured_link:
                vlan_page.locator('#investigation-run-probe').click()
            link_observation = measured_link.value.json()['observation']
            assert link_observation['documentedActive'] is True
            vlan_page.locator('#investigation-probe').select_option('port')
            vlan_page.locator('#investigation-port').select_option(
                json.dumps(['sw', 's'], separators=(',', ':')))
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as measured_port:
                vlan_page.locator('#investigation-run-probe').click()
            port_observation = measured_port.value.json()['observation']
            vlan_page.locator('#investigation-probe').select_option('vlan')
            vlan_page.locator('#investigation-port').select_option(
                json.dumps(['sw', 'c'], separators=(',', ':')))
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as measured_vlan:
                vlan_page.locator('#investigation-run-probe').click()
            vlan_observation = measured_vlan.value.json()['observation']
            assert vlan_observation['documentedVlan'] == 10
            if link_observation['observedCarrier'] == 'DOWN':
                inferred = ('PORT_SHUTDOWN'
                            if port_observation['observedAdmin'] == 'DOWN'
                            else 'CABLE_DOWN')
            else:
                assert link_observation['observedCarrier'] == 'UP'
                assert vlan_observation['observedVlan'] == 20
                inferred = 'VLAN_MISMATCH'
            wrong = next(x for x in ('CABLE_DOWN', 'PORT_SHUTDOWN', 'VLAN_MISMATCH')
                         if x != inferred)
            expect(vlan_page.locator('#investigation-submit')).to_be_enabled()
            vlan_page.locator('#investigation-diagnosis').select_option(wrong)
            with vlan_page.expect_response('**/api/dhcp/investigation/diagnose') as incorrect_guess:
                vlan_page.locator('#investigation-submit').click()
            wrong_reply = incorrect_guess.value.json()
            assert incorrect_guess.value.status == 200
            assert wrong_reply['correct'] is False
            assert inferred not in json.dumps(wrong_reply)
            expect(vlan_page.locator('#investigation-repair')).to_be_disabled()
            vlan_page.locator('#investigation-diagnosis').select_option(inferred)
            with vlan_page.expect_response('**/api/dhcp/investigation/diagnose') as correct_guess:
                vlan_page.locator('#investigation-submit').click()
            assert correct_guess.value.json()['correct'] is True
            expect(vlan_page.locator('#investigation-verdict')).to_contain_text(
                'DIAGNOS BEKRÄFTAD')
            expect(vlan_page.locator('#investigation-repair')).to_be_enabled()
            with vlan_page.expect_response('**/api/dhcp/investigation/repair') as verified_repair:
                vlan_page.locator('#investigation-repair').click()
            repair = verified_repair.value.json()
            assert verified_repair.value.status == 200
            assert repair['status'] == 'RECOVERED'
            assert repair['requestReachedServer'] is True
            assert repair['ackReachedClient'] is True
            assert repair['expiresAtSeconds'] == 90
            assert repair['cause'] == inferred
            expect(vlan_page.locator('#investigation-recovery')).to_contain_text(
                'RESULTAT: RECOVERED')
            vlan_page.locator('[data-item-type="node"][data-item-id="sw"]').click()
            expect(vlan_page.locator('[data-port-vlan="c"]')).to_have_value('access:10')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            expect(vlan_page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            with vlan_page.expect_response('**/api/dhcp/investigation/stop') as exercise_stop:
                vlan_page.locator('#investigation-stop').click()
            assert exercise_stop.value.status == 200
            expect(vlan_page.locator('#investigation-status')).to_contain_text(
                'Ingen felsökningsövning')

            # PR39: explicit advanced T1 -> T2 -> expiration with a
            # second opaque fault and *actual* fresh DORA after loss of lease.
            vlan_page.locator('#investigation-difficulty').select_option('EXPIRY_RECOVERY')
            with vlan_page.expect_response('**/api/dhcp/investigation/start') as advanced_start:
                vlan_page.locator('#investigation-start').click()
            advanced = advanced_start.value.json()
            assert advanced_start.value.status == 200
            assert advanced['difficulty'] == 'EXPIRY_RECOVERY'
            assert advanced['clockSeconds'] == 30
            assert advanced['phase'] == 'RENEWING'
            assert advanced['t2AtSeconds'] == 53
            assert advanced['expiresAtSeconds'] == 60
            assert not advanced['canAdvance']
            assert 'faulted' not in json.dumps(advanced)
            expect(vlan_page.locator('#investigation-advance')).to_be_disabled()
            vlan_page.locator('#investigation-probe').select_option('lease')
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as advanced_lease:
                vlan_page.locator('#investigation-run-probe').click()
            assert advanced_lease.value.json()['observation']['status'] == 'BOUND'
            vlan_page.locator('#investigation-probe').select_option('renew')
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as advanced_t1:
                vlan_page.locator('#investigation-run-probe').click()
            a_t1 = advanced_t1.value.json()
            assert a_t1['observation']['phase'] == 'RENEWING'
            assert a_t1['observation']['status'] == 'REQUEST_NOT_RECEIVED'
            assert a_t1['expiresAtSeconds'] == 60
            expect(vlan_page.locator('#investigation-advance')).to_be_enabled()
            with vlan_page.expect_response('**/api/dhcp/investigation/advance') as advanced_to_t2:
                vlan_page.locator('#investigation-advance').click()
            a_t2_time = advanced_to_t2.value.json()
            assert advanced_to_t2.value.status == 200
            assert a_t2_time['advancedSeconds'] == 23
            assert a_t2_time['clockSeconds'] == 53
            assert a_t2_time['phase'] == 'REBINDING'
            assert a_t2_time['expiresAtSeconds'] == 60
            assert not a_t2_time['canAdvance']
            expect(vlan_page.locator('#investigation-advance')).to_be_disabled()
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as advanced_t2:
                vlan_page.locator('#investigation-run-probe').click()
            a_t2 = advanced_t2.value.json()
            assert a_t2['observation']['phase'] == 'REBINDING'
            assert a_t2['observation']['status'] == 'REQUEST_NOT_RECEIVED'
            assert a_t2['observation']['requestReachedServer'] is False
            assert a_t2['expiresAtSeconds'] == 60
            expect(vlan_page.locator('#investigation-advance')).to_be_enabled()
            with vlan_page.expect_response('**/api/dhcp/investigation/advance') as advanced_to_expiry:
                vlan_page.locator('#investigation-advance').click()
            a_expired = advanced_to_expiry.value.json()
            assert advanced_to_expiry.value.status == 200
            assert a_expired['advancedSeconds'] == 7
            assert a_expired['clockSeconds'] == 60
            assert a_expired['phase'] == 'EXPIRED'
            assert a_expired['leaseActive'] is False
            assert a_expired['remainingSeconds'] == 0
            assert a_expired['requiredRecovery'] == 'NEW_DORA'
            assert a_expired['expiredLeases'] == [{
                'ipv4': '192.0.2.70', 'state': 'EXPIRED', 'expiresAtSeconds': 60,
            }]
            expect(vlan_page.locator('#investigation-status')).to_contain_text(
                'lease har upphört, ny DORA krävs')
            expect(vlan_page.locator('#investigation-run-probe')).to_be_disabled()
            expect(vlan_page.locator('#investigation-advance')).to_be_disabled()
            vlan_page.locator('#investigation-probe').select_option('lease')
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as expired_lease_probe:
                vlan_page.locator('#investigation-run-probe').click()
            assert expired_lease_probe.value.json()['observation']['status'] == 'EXPIRED'
            vlan_page.locator('#investigation-probe').select_option('link')
            vlan_page.locator('#investigation-link').select_option('to-server')
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as advanced_link:
                vlan_page.locator('#investigation-run-probe').click()
            observed_link = advanced_link.value.json()['observation']
            vlan_page.locator('#investigation-probe').select_option('port')
            vlan_page.locator('#investigation-port').select_option(
                json.dumps(['sw', 's'], separators=(',', ':')))
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as advanced_port:
                vlan_page.locator('#investigation-run-probe').click()
            observed_port = advanced_port.value.json()['observation']
            vlan_page.locator('#investigation-probe').select_option('vlan')
            vlan_page.locator('#investigation-port').select_option(
                json.dumps(['sw', 'c'], separators=(',', ':')))
            with vlan_page.expect_response('**/api/dhcp/investigation/probe') as advanced_vlan:
                vlan_page.locator('#investigation-run-probe').click()
            observed_vlan = advanced_vlan.value.json()['observation']
            if observed_link['observedCarrier'] == 'DOWN':
                advanced_cause = ('PORT_SHUTDOWN'
                                  if observed_port['observedAdmin'] == 'DOWN'
                                  else 'CABLE_DOWN')
            else:
                assert observed_link['observedCarrier'] == 'UP'
                assert observed_vlan['observedVlan'] == 20
                advanced_cause = 'VLAN_MISMATCH'
            expect(vlan_page.locator('#investigation-submit')).to_be_enabled()
            vlan_page.locator('#investigation-diagnosis').select_option(advanced_cause)
            with vlan_page.expect_response('**/api/dhcp/investigation/diagnose') as advanced_diagnose:
                vlan_page.locator('#investigation-submit').click()
            assert advanced_diagnose.value.status == 200
            assert advanced_diagnose.value.json()['correct'] is True
            expect(vlan_page.locator('#investigation-repair')).to_be_enabled()
            expect(vlan_page.locator('#investigation-repair')).to_contain_text('ny DHCP DORA')
            with vlan_page.expect_response('**/api/dhcp/investigation/repair') as advanced_repair:
                vlan_page.locator('#investigation-repair').click()
            a_recovered = advanced_repair.value.json()
            assert advanced_repair.value.status == 200
            assert a_recovered['status'] == 'RECOVERED'
            assert a_recovered['verifiedProtocol'] == 'NEW_DORA'
            assert a_recovered['discoverReachedServer'] is True
            assert a_recovered['offerReachedClient'] is True
            assert a_recovered['requestReachedServer'] is True
            assert a_recovered['ackReachedClient'] is True
            assert a_recovered['leaseActive'] is True
            assert a_recovered['phase'] == 'BOUND'
            assert a_recovered['expiresAtSeconds'] == 120
            expect(vlan_page.locator('#investigation-recovery')).to_contain_text(
                'Verifierad metod: NEW_DORA')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert sorted(x.name for x in store.glob('*.yadilab')) == ['lab.yadilab']
            with vlan_page.expect_response('**/api/dhcp/investigation/stop') as advanced_stop:
                vlan_page.locator('#investigation-stop').click()
            assert advanced_stop.value.status == 200
            vlan_page.locator('#investigation-difficulty').select_option('T1_ONLY')

            # Late probe responses must not resurrect an exercise after a
            # canonical topology edit; saved bytes are never overwritten.
            with vlan_page.expect_response('**/api/dhcp/investigation/start') as stale_start:
                vlan_page.locator('#investigation-start').click()
            assert stale_start.value.status == 200
            vlan_page.evaluate("""() => {
              window.__actualInvestigateFetch = window.fetch;
              window.__finishInvestigate = null;
              window.fetch = async (...args) => {
                const response = await window.__actualInvestigateFetch(...args);
                if (args[0] === '/api/dhcp/investigation/probe') {
                  return new Promise(resolve => {
                    window.__finishInvestigate = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            vlan_page.locator('#investigation-run-probe').click()
            vlan_page.wait_for_function("typeof window.__finishInvestigate === 'function'")
            expect(vlan_page.locator('#investigation-run-probe')).to_be_disabled()
            vlan_page.locator('[data-item-type="link"][data-item-id="to-server"]').click()
            vlan_page.locator('#inspector input[type="checkbox"]').uncheck()
            expect(vlan_page.locator('#investigation-status')).to_contain_text(
                'Ingen felsökningsövning')
            vlan_page.evaluate('window.__finishInvestigate()')
            expect(vlan_page.locator('#investigation-observations')).to_contain_text(
                'Inga observationer')
            vlan_page.evaluate('window.fetch = window.__actualInvestigateFetch')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert not errors, errors
            vlan_page.close()

            # PR40: separate routed two-way Echo investigation. An opaque
            # cause is chosen ONLY among real failed/recovered ARP/IP/L2 trials.
            # The student must not infer DHCP from a documented IPv4.
            icmp_page = context.new_page()
            icmp_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
            assert browser_open(icmp_page, base) == network_mode
            icmp_page.once('dialog', lambda dialog: dialog.accept())
            with icmp_page.expect_response('**/api/validate') as routed_import:
                icmp_page.locator('#import-file').set_input_files({
                    'name': 'routed-echo-investigation.json',
                    'mimeType': 'application/json',
                    'buffer': json.dumps(icmp_routed_lab()).encode('utf-8'),
                })
            assert routed_import.value.status == 200
            expect(icmp_page.locator('[data-node-id="a"]')).to_have_count(1)
            expect(icmp_page.locator('[data-node-id="r"]')).to_have_count(1)
            icmp_page.locator('#icmp-investigation-source').select_option(
                json.dumps(['a', 'eth0'], separators=(',', ':')))
            icmp_page.locator('#icmp-investigation-destination').fill('203.0.113.20')
            icmp_page.locator('#icmp-investigation-ttl').fill('5')
            with icmp_page.expect_response('**/api/icmp/investigation/start') as icmp_started:
                icmp_page.locator('#icmp-investigation-start').click()
            started = icmp_started.value.json()
            assert icmp_started.value.status == 200, started
            assert started['sourceIpv4'] == '192.0.2.10'
            assert started['destinationIpv4'] == '203.0.113.20'
            assert started['dhcpAddressOrigin'] == 'UNKNOWN'
            assert started['dhcpCheck'] == 'NOT_VERIFIED'
            assert 'fault' not in json.dumps(started)
            assert not any(name in json.dumps(started) for name in (
                'CABLE_DOWN', 'PORT_SHUTDOWN', 'VLAN_MISMATCH',
                'STATIC_ROUTE_MISSING', 'IPV4_PREFIX_MISMATCH',
                'STATIC_NEXT_HOP_UNREACHABLE', 'IPV4_HOST_ADDRESS_MISMATCH'))
            expect(icmp_page.locator('#icmp-investigation-status')).to_contain_text(
                'Aktiv dold övning')
            expect(icmp_page.locator('#icmp-investigation-diagnose')).to_be_disabled()
            with icmp_page.expect_response('**/api/icmp/investigation/probe') as icmp_ip:
                icmp_page.locator('#icmp-investigation-measure').click()
            ip_observation = icmp_ip.value.json()['observation']
            assert ip_observation['dhcpStatus'] == 'NOT_VERIFIED'
            assert ip_observation['origin'] == 'UNKNOWN'
            expect(icmp_page.locator('#icmp-investigation-observations')).to_contain_text(
                'DHCP-ursprung: UNKNOWN · kontroll: NOT_VERIFIED')
            icmp_page.locator('#icmp-investigation-probe').select_option('ping')
            with icmp_page.expect_response('**/api/icmp/investigation/probe') as icmp_ping:
                icmp_page.locator('#icmp-investigation-measure').click()
            echo = icmp_ping.value.json()['observation']
            assert echo['status'] != 'REPLIED'
            assert echo['replyMatched'] is False
            assert echo['source'] == 'SIMULATED'
            assert echo['requestStatus']
            expect(icmp_page.locator('#icmp-investigation-observations')).to_contain_text(
                'ICMP:')
            icmp_page.locator('#icmp-investigation-probe').select_option('route')
            icmp_page.locator('#icmp-investigation-route-node').select_option('a')
            with icmp_page.expect_response('**/api/icmp/investigation/probe') as icmp_forward:
                icmp_page.locator('#icmp-investigation-measure').click()
            forward = icmp_forward.value.json()['observation']
            assert forward['destinationIpv4'] == '203.0.113.20'
            assert forward['status'] in ('MATCH', 'NO_ROUTE')
            icmp_page.locator('#icmp-investigation-route-node').select_option('b')
            icmp_page.locator('#icmp-investigation-route-destination').select_option('source')
            with icmp_page.expect_response('**/api/icmp/investigation/probe') as icmp_reverse:
                icmp_page.locator('#icmp-investigation-measure').click()
            reverse = icmp_reverse.value.json()['observation']
            assert reverse['destinationIpv4'] == '192.0.2.10'
            assert reverse['status'] in ('MATCH', 'NO_ROUTE')
            missing_routes = []
            wrong_next_hops = []
            for lookup in (forward, reverse):
                documented = {r['id']: r for r in lookup['documentedStaticRoutes']}
                simulated = {r['routeId']: r for r in lookup['routes']
                             if r['type'] == 'STATIC'}
                for route_id, expected in documented.items():
                    actual = simulated.get(route_id)
                    if actual is None:
                        missing_routes.append((lookup['sourceNode'], route_id))
                    elif actual['nextHop'] != expected['nextHop']:
                        assert actual['destination'] == expected['destination']
                        assert actual['outInterface']['port'] == expected['outPort']
                        wrong_next_hops.append((lookup['sourceNode'], route_id))
            icmp_page.locator('#icmp-investigation-probe').select_option('link')
            disconnected = []
            for link_id in ('la', 'lr1', 'lr2', 'lb'):
                icmp_page.locator('#icmp-investigation-link').select_option(link_id)
                with icmp_page.expect_response('**/api/icmp/investigation/probe') as link_check:
                    icmp_page.locator('#icmp-investigation-measure').click()
                link_observation = link_check.value.json()['observation']
                assert link_observation['documentedEnabled'] is True
                if link_observation['observedEnabled'] is False:
                    disconnected.append(link_id)
            icmp_page.locator('#icmp-investigation-probe').select_option('vlan')
            mismatched = []
            for nid, pid in (('sw-left', 'a'), ('sw-left', 'r'),
                             ('sw-right', 'r'), ('sw-right', 'b')):
                icmp_page.locator('#icmp-investigation-vlan').select_option(
                    json.dumps([nid, pid], separators=(',', ':')))
                with icmp_page.expect_response('**/api/icmp/investigation/probe') as vlan_check:
                    icmp_page.locator('#icmp-investigation-measure').click()
                vlan_observation = vlan_check.value.json()['observation']
                if vlan_observation['documentedVlan'] != vlan_observation['observedVlan']:
                    mismatched.append((nid, pid))
            icmp_page.locator('#icmp-investigation-probe').select_option('port')
            shut_ports = []
            for nid, pid in (('sw-left', 'a'), ('sw-left', 'r'),
                             ('sw-right', 'r'), ('sw-right', 'b')):
                icmp_page.locator('#icmp-investigation-port').select_option(
                    json.dumps([nid, pid], separators=(',', ':')))
                with icmp_page.expect_response('**/api/icmp/investigation/probe') as port_check:
                    icmp_page.locator('#icmp-investigation-measure').click()
                port_observation = port_check.value.json()['observation']
                assert port_observation['documentedEnabled'] is True
                if port_observation['observedEnabled'] is False:
                    shut_ports.append((nid, pid))
            # Investigate the documented IPv4/CIDR on every routed interface;
            # unlike route lookup, this can distinguish a wrong prefix from
            # a route that has actually been removed.
            prefix_changes = []
            address_changes = []
            for nid, pid in (('a', 'eth0'), ('r', 'wan'),
                             ('r', 'lan'), ('b', 'eth0')):
                icmp_page.locator('#icmp-investigation-port').select_option(
                    json.dumps([nid, pid], separators=(',', ':')))
                with icmp_page.expect_response('**/api/icmp/investigation/probe') as ip_check:
                    icmp_page.locator('#icmp-investigation-measure').click()
                ip_observation = ip_check.value.json()['observation']
                assert ip_observation['documentedIpv4'] is not None
                if ip_observation['documentedIpv4'] != ip_observation['observedIpv4']:
                    if (ip_observation['documentedIpv4'].split('/')[0] ==
                            ip_observation['observedIpv4'].split('/')[0]):
                        prefix_changes.append((nid, pid))
                    else:
                        assert (ip_observation['documentedIpv4'].split('/')[1] ==
                                ip_observation['observedIpv4'].split('/')[1])
                        address_changes.append((nid, pid))
            if disconnected:
                assert len(disconnected) == 1
                inferred = 'CABLE_DOWN'
            elif shut_ports:
                assert len(shut_ports) == 1
                inferred = 'PORT_SHUTDOWN'
            elif mismatched:
                assert len(mismatched) == 1
                inferred = 'VLAN_MISMATCH'
            elif prefix_changes:
                assert len(prefix_changes) == 1
                inferred = 'IPV4_PREFIX_MISMATCH'
            elif address_changes:
                assert address_changes == [('b', 'eth0')]
                assert echo['requestStatus'] == 'ARP_FAILED'
                assert any(step['arpStatus'] == 'NO_REPLY'
                           and step['nextHopIpv4'] == '203.0.113.20'
                           for step in echo['requestSteps'])
                inferred = 'IPV4_HOST_ADDRESS_MISMATCH'
            elif wrong_next_hops:
                assert len(wrong_next_hops) == 1
                assert not missing_routes
                assert 'ARP_FAILED' in (echo['requestStatus'], echo['replyStatus'])
                inferred = 'STATIC_NEXT_HOP_UNREACHABLE'
            else:
                assert len(missing_routes) == 1
                inferred = 'STATIC_ROUTE_MISSING'
            expect(icmp_page.locator('#icmp-investigation-diagnose')).to_be_enabled()
            wrong = next(x for x in ('CABLE_DOWN', 'PORT_SHUTDOWN', 'VLAN_MISMATCH',
                                     'STATIC_ROUTE_MISSING', 'IPV4_PREFIX_MISMATCH',
                                     'STATIC_NEXT_HOP_UNREACHABLE',
                                     'IPV4_HOST_ADDRESS_MISMATCH')
                         if x != inferred)
            icmp_page.locator('#icmp-investigation-diagnosis').select_option(wrong)
            with icmp_page.expect_response('**/api/icmp/investigation/diagnose') as false_guess:
                icmp_page.locator('#icmp-investigation-diagnose').click()
            guess = false_guess.value.json()
            assert false_guess.value.status == 200
            assert guess['correct'] is False
            assert inferred not in json.dumps(guess)
            expect(icmp_page.locator('#icmp-investigation-repair')).to_be_disabled()
            icmp_page.locator('#icmp-investigation-diagnosis').select_option(inferred)
            with icmp_page.expect_response('**/api/icmp/investigation/diagnose') as correct_guess:
                icmp_page.locator('#icmp-investigation-diagnose').click()
            assert correct_guess.value.json()['correct'] is True
            expect(icmp_page.locator('#icmp-investigation-verdict')).to_contain_text(
                'DIAGNOS BEKRÄFTAD')
            expect(icmp_page.locator('#icmp-investigation-repair')).to_be_enabled()
            expect(icmp_page.locator('#icmp-investigation-recovery')).not_to_contain_text(
                'FELSÖKNINGSRAPPORT')
            with icmp_page.expect_response('**/api/icmp/investigation/repair') as repair_action:
                icmp_page.locator('#icmp-investigation-repair').click()
            fixed = repair_action.value.json()
            assert repair_action.value.status == 200
            assert fixed['status'] == 'RECOVERED'
            assert fixed['failedEchoStatus'] != 'REPLIED'
            assert fixed['restoredEchoStatus'] == 'REPLIED'
            assert fixed['replyMatched'] is True
            assert fixed['faultCategory'] == inferred
            assert fixed['repair']['scope'] == 'PREVIEW_ONLY'
            assert set(fixed['report']) == {'symptom', 'rootCause', 'evidence',
                                            'action', 'verification'}
            expect(icmp_page.locator('#icmp-investigation-recovery')).to_contain_text(
                'RESULTAT: RECOVERED')
            for label in ('Symptom:', 'Rotorsak:', 'Teknisk evidens:', 'Åtgärd:',
                          'Verifiering:', 'matchande Echo Reply'):
                expect(icmp_page.locator('#icmp-investigation-recovery')).to_contain_text(label)
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert sorted(x.name for x in store.glob('*.yadilab')) == ['lab.yadilab']
            with icmp_page.expect_response('**/api/icmp/investigation/stop') as icmp_stop:
                icmp_page.locator('#icmp-investigation-stop').click()
            assert icmp_stop.value.status == 200
            expect(icmp_page.locator('#icmp-investigation-status')).to_contain_text(
                'Ingen ICMP-övning')

            # Same-subnet hosts, one declared switch, connected routes and
            # real ARP/Ethernet evidence through a complete hidden-fault flow.
            lan_page = context.new_page()
            lan_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
            assert browser_open(lan_page, base) == network_mode
            lan_page.once('dialog', lambda dialog: dialog.accept())
            with lan_page.expect_response('**/api/validate') as lan_import:
                lan_page.locator('#import-file').set_input_files({
                    'name': 'lan-echo-investigation.json',
                    'mimeType': 'application/json',
                    'buffer': json.dumps(icmp_lan_lab()).encode('utf-8'),
                })
            assert lan_import.value.status == 200
            expect(lan_page.locator('[data-node-id="sw"]')).to_have_count(1)
            lan_page.locator('#icmp-investigation-source').select_option(
                json.dumps(['a', 'eth0'], separators=(',', ':')))
            lan_page.locator('#icmp-investigation-destination').fill('192.168.10.20')
            with lan_page.expect_response('**/api/icmp/investigation/start') as lan_start:
                lan_page.locator('#icmp-investigation-start').click()
            assert lan_start.value.status == 200
            assert not any(kind in json.dumps(lan_start.value.json()) for kind in
                           ('CABLE_DOWN', 'PORT_SHUTDOWN', 'VLAN_MISMATCH',
                            'IPV4_HOST_ADDRESS_MISMATCH', 'IPV4_PREFIX_MISMATCH'))
            lan_page.locator('#icmp-investigation-probe').select_option('ping')
            with lan_page.expect_response('**/api/icmp/investigation/probe') as lan_ping:
                lan_page.locator('#icmp-investigation-measure').click()
            ping_observation = lan_ping.value.json()['observation']
            assert ping_observation['status'] != 'REPLIED'
            assert ping_observation['replyMatched'] is False
            lan_page.locator('#icmp-investigation-probe').select_option('route')
            with lan_page.expect_response('**/api/icmp/investigation/probe') as lan_route:
                lan_page.locator('#icmp-investigation-measure').click()
            route_observation = lan_route.value.json()['observation']
            assert route_observation['status'] in ('MATCH', 'NO_ROUTE')
            if route_observation['status'] == 'MATCH':
                assert route_observation['selectedRoute']['type'] == 'CONNECTED'
            assert route_observation['documentedStaticRoutes'] == []
            lan_page.locator('#icmp-investigation-route-node').select_option('b')
            lan_page.locator('#icmp-investigation-route-destination').select_option('source')
            with lan_page.expect_response('**/api/icmp/investigation/probe') as lan_reverse:
                lan_page.locator('#icmp-investigation-measure').click()
            reverse_observation = lan_reverse.value.json()['observation']
            assert reverse_observation['status'] in ('MATCH', 'NO_ROUTE')
            assert reverse_observation['documentedStaticRoutes'] == []
            lan_page.locator('#icmp-investigation-probe').select_option('link')
            disconnected = []
            for link_id in ('la', 'lb'):
                lan_page.locator('#icmp-investigation-link').select_option(link_id)
                with lan_page.expect_response('**/api/icmp/investigation/probe') as lan_link:
                    lan_page.locator('#icmp-investigation-measure').click()
                measured = lan_link.value.json()['observation']
                if not measured['observedEnabled']:
                    disconnected.append(link_id)
            # Infer the hidden cause from independent documented-versus-
            # simulated observations; the normal exercise chooses at random.
            lan_page.locator('#icmp-investigation-probe').select_option('port')
            shut_ports, changed_addresses, changed_prefixes = [], [], []
            for nid, pid in (('sw', 'a'), ('sw', 'b'), ('a', 'eth0'), ('b', 'eth0')):
                lan_page.locator('#icmp-investigation-port').select_option(
                    json.dumps([nid, pid], separators=(',', ':')))
                with lan_page.expect_response('**/api/icmp/investigation/probe') as lan_port:
                    lan_page.locator('#icmp-investigation-measure').click()
                measured = lan_port.value.json()['observation']
                if measured['documentedEnabled'] and not measured['observedEnabled']:
                    shut_ports.append((nid, pid))
                if measured['documentedIpv4'] != measured['observedIpv4']:
                    documented_ip, documented_prefix = measured['documentedIpv4'].split('/')
                    observed_ip, observed_prefix = measured['observedIpv4'].split('/')
                    if documented_ip == observed_ip:
                        assert documented_prefix != observed_prefix
                        changed_prefixes.append((nid, pid))
                    else:
                        assert documented_prefix == observed_prefix
                        changed_addresses.append((nid, pid))
            lan_page.locator('#icmp-investigation-probe').select_option('vlan')
            changed_vlans = []
            for nid, pid in (('sw', 'a'), ('sw', 'b')):
                lan_page.locator('#icmp-investigation-vlan').select_option(
                    json.dumps([nid, pid], separators=(',', ':')))
                with lan_page.expect_response('**/api/icmp/investigation/probe') as lan_vlan:
                    lan_page.locator('#icmp-investigation-measure').click()
                measured = lan_vlan.value.json()['observation']
                if measured['documentedVlan'] != measured['observedVlan']:
                    changed_vlans.append((nid, pid))
            assert sum(bool(x) for x in
                       (disconnected, shut_ports, changed_vlans,
                        changed_addresses, changed_prefixes)) == 1
            if disconnected:
                assert len(disconnected) == 1
                inferred, failure_point = 'CABLE_DOWN', disconnected[0]
            elif shut_ports:
                assert len(shut_ports) == 1
                inferred, failure_point = 'PORT_SHUTDOWN', shut_ports[0][1]
            elif changed_vlans:
                assert len(changed_vlans) == 1
                inferred, failure_point = 'VLAN_MISMATCH', changed_vlans[0][1]
            elif changed_prefixes:
                assert len(changed_prefixes) == 1
                changed_node, failure_point = changed_prefixes[0]
                assert failure_point == 'eth0'
                assert ping_observation['requestStatus' if changed_node == 'a'
                                        else 'replyStatus'] == 'NO_ROUTE'
                assert route_observation['status'] == ('NO_ROUTE' if changed_node == 'a'
                                                       else 'MATCH')
                assert reverse_observation['status'] == ('NO_ROUTE' if changed_node == 'b'
                                                         else 'MATCH')
                inferred = 'IPV4_PREFIX_MISMATCH'
            else:
                assert changed_addresses == [('b', 'eth0')]
                inferred, failure_point = 'IPV4_HOST_ADDRESS_MISMATCH', 'eth0'
            if inferred == 'IPV4_PREFIX_MISMATCH':
                assert 'ARP_FAILED' not in (ping_observation['requestStatus'],
                                            ping_observation['replyStatus'])
            else:
                assert ping_observation['requestStatus'] == 'ARP_FAILED'
                assert ping_observation['requestSteps'][0]['arpStatus'] in (
                    'NO_REPLY', 'NO_ACTIVE_LINK')
            lan_page.locator('#icmp-investigation-diagnosis').select_option(inferred)
            with lan_page.expect_response('**/api/icmp/investigation/diagnose') as lan_diagnose:
                lan_page.locator('#icmp-investigation-diagnose').click()
            assert lan_diagnose.value.json()['correct'] is True
            with lan_page.expect_response('**/api/icmp/investigation/repair') as lan_repair:
                lan_page.locator('#icmp-investigation-repair').click()
            repaired_lan = lan_repair.value.json()
            assert repaired_lan['status'] == 'RECOVERED'
            assert repaired_lan['restoredEchoStatus'] == 'REPLIED'
            assert repaired_lan['replyMatched'] is True
            assert repaired_lan['faultCategory'] == inferred
            assert failure_point in repaired_lan['report']['rootCause']
            if inferred == 'IPV4_PREFIX_MISMATCH':
                assert 'NO_ROUTE' in repaired_lan['report']['evidence']
                assert 'ARP för' not in repaired_lan['report']['evidence']
                assert 'Värdadressen var oförändrad' in repaired_lan['report']['rootCause']
            expect(lan_page.locator('#icmp-investigation-recovery')).to_contain_text(
                'matchande Echo Reply')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            lan_page.close()

            # Select the existing prefix candidate on a local test server.
            # Only the random choice is controlled; Chromium still measures
            # real API results from EchoExchange and the canonical model.
            prefix_project = icmp_lan_lab()
            prefix_baseline = EchoExchange(prefix_project).ping(
                'a', 'eth0', '192.168.10.20', 5, 101, 1)
            prefix_choice = next(i for i, (kind, _) in enumerate(
                _candidates(prefix_project, prefix_baseline))
                if kind == 'IPV4_PREFIX_MISMATCH')
            prefix_server = LabHTTPServer(('127.0.0.1', 0),
                                          ProjectStore(store / 'prefix-browser'))
            prefix_thread = threading.Thread(target=prefix_server.serve_forever, daemon=True)
            prefix_thread.start()
            try:
                with patch('network_core.icmp_investigation.secrets.randbelow',
                           return_value=prefix_choice):
                    prefix_page = context.new_page()
                    prefix_page.on('pageerror', lambda error: errors.append(
                        getattr(error, 'stack', str(error))))
                    prefix_base = f'http://127.0.0.1:{prefix_server.server_port}/'
                    assert browser_open(prefix_page, prefix_base) == network_mode
                    prefix_page.once('dialog', lambda dialog: dialog.accept())
                    with prefix_page.expect_response('**/api/validate') as prefix_import:
                        prefix_page.locator('#import-file').set_input_files({
                            'name': 'lan-prefix-investigation.json',
                            'mimeType': 'application/json',
                            'buffer': json.dumps(prefix_project).encode('utf-8'),
                        })
                    assert prefix_import.value.status == 200
                    prefix_page.locator('#icmp-investigation-source').select_option(
                        json.dumps(['a', 'eth0'], separators=(',', ':')))
                    prefix_page.locator('#icmp-investigation-destination').fill('192.168.10.20')
                    with prefix_page.expect_response('**/api/icmp/investigation/start') as prefix_start:
                        prefix_page.locator('#icmp-investigation-start').click()
                    assert prefix_start.value.status == 200
                    assert 'IPV4_PREFIX_MISMATCH' not in json.dumps(prefix_start.value.json())
                    prefix_page.locator('#icmp-investigation-probe').select_option('ping')
                    with prefix_page.expect_response('**/api/icmp/investigation/probe') as prefix_ping:
                        prefix_page.locator('#icmp-investigation-measure').click()
                    measured_ping = prefix_ping.value.json()['observation']
                    assert measured_ping['requestStatus'] == 'NO_ROUTE'
                    assert measured_ping['requestSteps'] == []
                    assert measured_ping['replyMatched'] is False
                    prefix_page.locator('#icmp-investigation-probe').select_option('route')
                    with prefix_page.expect_response('**/api/icmp/investigation/probe') as prefix_route:
                        prefix_page.locator('#icmp-investigation-measure').click()
                    assert prefix_route.value.json()['observation']['status'] == 'NO_ROUTE'
                    prefix_page.locator('#icmp-investigation-probe').select_option('port')
                    prefix_page.locator('#icmp-investigation-port').select_option(
                        json.dumps(['a', 'eth0'], separators=(',', ':')))
                    with prefix_page.expect_response('**/api/icmp/investigation/probe') as prefix_port:
                        prefix_page.locator('#icmp-investigation-measure').click()
                    measured_port = prefix_port.value.json()['observation']
                    assert measured_port['documentedIpv4'] == '192.168.10.10/24'
                    assert measured_port['observedIpv4'] == '192.168.10.10/28'
                    prefix_page.locator('#icmp-investigation-diagnosis').select_option(
                        'IPV4_PREFIX_MISMATCH')
                    with prefix_page.expect_response('**/api/icmp/investigation/diagnose') as prefix_diagnose:
                        prefix_page.locator('#icmp-investigation-diagnose').click()
                    assert prefix_diagnose.value.json()['correct'] is True
                    with prefix_page.expect_response('**/api/icmp/investigation/repair') as prefix_repair:
                        prefix_page.locator('#icmp-investigation-repair').click()
                    prefix_fixed = prefix_repair.value.json()
                    assert prefix_fixed['status'] == 'RECOVERED'
                    assert prefix_fixed['restoredEchoStatus'] == 'REPLIED'
                    assert prefix_fixed['replyMatched'] is True
                    assert 'NO_ROUTE' in prefix_fixed['report']['evidence']
                    assert 'ARP för' not in prefix_fixed['report']['evidence']
                    expect(prefix_page.locator('#icmp-investigation-recovery')).to_contain_text(
                        'Värdadressen var oförändrad')
                    assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
                    prefix_page.close()
            finally:
                prefix_server.shutdown()
                prefix_server.server_close()
                prefix_thread.join(timeout=5)

            # Delayed measurement after project edit must not resurrect the
            # old hidden session, replace the graph or modify saved bytes.
            with icmp_page.expect_response('**/api/icmp/investigation/start') as stale_icmp:
                icmp_page.locator('#icmp-investigation-start').click()
            assert stale_icmp.value.status == 200
            icmp_page.evaluate("""() => {
              window.__icmpRealFetch = window.fetch;
              window.__finishIcmpProbe = null;
              window.fetch = async (...args) => {
                const response = await window.__icmpRealFetch(...args);
                if (args[0] === '/api/icmp/investigation/probe') {
                  return new Promise(resolve => {
                    window.__finishIcmpProbe = () => resolve(response);
                  });
                }
                return response;
              };
            }""")
            icmp_page.locator('#icmp-investigation-probe').select_option('address')
            icmp_page.locator('#icmp-investigation-measure').click()
            icmp_page.wait_for_function("typeof window.__finishIcmpProbe === 'function'")
            icmp_page.locator('[data-item-type="link"][data-item-id="la"]').click()
            icmp_page.locator('#inspector input[type="checkbox"]').uncheck()
            expect(icmp_page.locator('#icmp-investigation-status')).to_contain_text(
                'Ingen ICMP-övning')
            icmp_page.evaluate('window.__finishIcmpProbe()')
            expect(icmp_page.locator('#icmp-investigation-observations')).to_contain_text(
                'Börja med IP-uppgifter')
            icmp_page.evaluate('window.fetch = window.__icmpRealFetch')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert not errors, errors
            icmp_page.close()

            # A different saved project must not be silently overwritten.
            page.locator('#new-project').click()
            page.locator('#empty-add').click()
            # Conflict must request explicit consent; decline without changing bytes.
            page.once('dialog',lambda dialog: dialog.dismiss())
            page.locator('#save-project').click()
            expect(page.locator('#toast')).to_contain_text('Kunde inte spara:',timeout=10000)
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # CSV rejected: malformed canonical links cannot overwrite the
            # current unsaved workspace and must not change existing disk data.
            page.once('dialog', lambda dialog: dialog.accept('Invalid CSV test'))
            page.locator('#import-file').set_input_files({
                'name': 'Links.csv', 'mimeType': 'text/csv',
                'buffer': (ROOT / 'examples/csv/Links.csv').read_bytes(),
            })
            expect(page.locator('#toast')).to_contain_text('Import avvisad:', timeout=10000)
            expect(page.locator('[data-node-id="node-1"]')).to_have_count(1)
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # Explicit, user-approved four-table CSV import. No guessed nodes,
            # implicit links, or write to disk occurs during import.
            prompts = []
            def accept_import_dialog(dialog):
                prompts.append(dialog.type)
                dialog.accept(
                    'ODS Browser Lab' if 'ODS' in dialog.message else (
                      'XLSX Browser Lab' if 'XLSX' in dialog.message else 'CSV acceptance lab')
                ) if dialog.type == 'prompt' else dialog.accept()
            page.on('dialog', accept_import_dialog)
            page.locator('#import-file').set_input_files([
                {'name': name, 'mimeType': 'text/csv',
                 'buffer': (ROOT / 'examples/csv' / name).read_bytes()}
                for name in ('Devices.csv', 'Interfaces.csv', 'Links.csv', 'Zones.csv')
            ])
            expect(page.locator('[data-node-id="pc-a"]')).to_have_count(1, timeout=12000)
            expect(page.locator('[data-node-id="sw-a"]')).to_have_count(1)
            expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)
            assert page.locator('[data-link-id]').count() == 1
            assert prompts.count('confirm') >= 2 and prompts.count('prompt') == 1, prompts
            expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            assert not (store / 'csv-demo.yadilab').exists()
            page.locator('#project-filename').fill('csv-demo')
            page.locator('#project-filename').dispatch_event('change')
            page.locator('#save-project').click()
            expect(page.locator('#save-indicator')).to_contain_text('Sparat · csv-demo.yadilab',timeout=12000)
            actual_csv = json.loads((store / 'csv-demo.yadilab').read_bytes())
            assert [n['id'] for n in actual_csv['nodes']] == ['pc-a', 'sw-a']
            assert actual_csv['links'][0]['a'] == {'node': 'pc-a', 'port': 'eth0'}
            assert actual_csv['links'][0]['b'] == {'node': 'sw-a', 'port': 'gi1'}
            page.locator('#new-project').click()
            page.locator('#saved-projects').select_option('csv-demo')
            page.locator('#open-project').click()
            expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)

            # PR23: genuinely zipped OOXML files, not CSV masquerading as
            # a workbook. Unsupported hidden worksheets must be rejected
            # without replacing the still-open project or changing on-disk SHA.
            csv_sha = hashlib.sha256((store/'csv-demo.yadilab').read_bytes()).hexdigest()
            invalid_parts = workbook_parts()
            workbook_xml = invalid_parts['xl/workbook.xml'].decode('utf-8')
            assert 'name="Devices" sheetId="1"' in workbook_xml
            invalid_parts['xl/workbook.xml'] = workbook_xml.replace(
                'name="Devices" sheetId="1"',
                'name="Devices" state="hidden" sheetId="1"'
            ).encode('utf-8')
            with page.expect_response('**/api/import/xlsx') as bad_xlsx:
                page.locator('#import-file').set_input_files({
                    'name':'bad-hidden.xlsx',
                    'mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'buffer':zip_parts(invalid_parts),
                })
            assert bad_xlsx.value.status == 422
            expect(page.locator('#toast')).to_contain_text('Import avvisad:')
            expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)
            assert hashlib.sha256((store/'csv-demo.yadilab').read_bytes()).hexdigest() == csv_sha
            assert not (store/'xlsx-demo.yadilab').exists()

            # Real XLSX with reordered XML sheet declarations, shared strings,
            # numeric coordinates and boolean enabled cells. Import validates
            # before asking for consent to replace working data. No autosave.
            real_xlsx = make_workbook(shared_strings=True, reorder=True)
            with page.expect_response('**/api/import/xlsx') as good_xlsx:
                page.locator('#import-file').set_input_files({
                    'name':'documentation.xlsx',
                    'mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'buffer':real_xlsx,
                })
            assert good_xlsx.value.status == 200
            incoming = good_xlsx.value.json()['project']
            assert incoming['schemaVersion'] == '1.0'
            assert incoming['name'] == 'XLSX Browser Lab'
            assert [n['id'] for n in incoming['nodes']] == ['pc-a','sw-a']
            assert incoming['links'][0]['id'] == 'cable-1'
            expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert not (store/'xlsx-demo.yadilab').exists()
            assert hashlib.sha256((store/'csv-demo.yadilab').read_bytes()).hexdigest() == csv_sha
            page.locator('#project-filename').fill('xlsx-demo')
            page.locator('#project-filename').dispatch_event('change')
            page.locator('#save-project').click()
            expect(page.locator('#save-indicator')).to_contain_text(
                'Sparat · xlsx-demo.yadilab', timeout=12000)
            saved_xlsx = json.loads((store/'xlsx-demo.yadilab').read_bytes())
            assert saved_xlsx == incoming
            xlsx_sha = hashlib.sha256((store/'xlsx-demo.yadilab').read_bytes()).hexdigest()
            page.locator('#new-project').click()
            page.locator('#saved-projects').select_option('xlsx-demo')
            page.locator('#open-project').click()
            expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)
            assert hashlib.sha256((store/'xlsx-demo.yadilab').read_bytes()).hexdigest() == xlsx_sha
            assert hashlib.sha256((store/'csv-demo.yadilab').read_bytes()).hexdigest() == csv_sha

            # PR24: actual zipped OpenDocument workbook bytes, not XLSX or
            # renamed CSV. Hidden ODS sheet is rejected before workspace
            # replacement, without touching prior on-disk files.
            bad_ods = ods_parts()
            ods_xml = bad_ods['content.xml'].decode('utf-8')
            assert '<table:table table:name="Devices">' in ods_xml
            bad_ods['content.xml'] = ods_xml.replace(
                '<table:table table:name="Devices">',
                '<table:table table:name="Devices" table:visibility="collapse">',
                1
            ).encode('utf-8')
            with page.expect_response('**/api/import/ods') as invalid_ods:
                page.locator('#import-file').set_input_files({
                    'name':'hidden.ods',
                    'mimeType':'application/vnd.oasis.opendocument.spreadsheet',
                    'buffer':zip_ods_parts(bad_ods),
                })
            assert invalid_ods.value.status == 422
            expect(page.locator('#toast')).to_contain_text('Import avvisad:')
            expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)
            assert hashlib.sha256((store/'xlsx-demo.yadilab').read_bytes()).hexdigest() == xlsx_sha
            assert not (store/'ods-demo.yadilab').exists()

            # Real ODF manifest and stored MIME, reordered named tables,
            # boolean/float cells and harmless repeated empty padding.
            # HTTP validation precedes explicit discard and replace prompts.
            ods_prompts_before = prompts.count('prompt')
            with page.expect_response('**/api/import/ods') as actual_ods:
                page.locator('#import-file').set_input_files({
                    'name':'declared-net.ods',
                    'mimeType':'application/vnd.oasis.opendocument.spreadsheet',
                    'buffer':make_ods(reorder=True,trailing=True,styles=True),
                })
            assert actual_ods.value.status == 200
            ods_project = actual_ods.value.json()['project']
            assert ods_project['schemaVersion'] == '1.0'
            assert ods_project['name'] == 'ODS Browser Lab'
            assert [n['id'] for n in ods_project['nodes']] == ['pc-a','sw-a']
            assert ods_project['links'][0]['a'] == {'node':'pc-a','port':'eth0'}
            assert ods_project['links'][0]['b'] == {'node':'sw-a','port':'gi1'}
            assert prompts.count('prompt') == ods_prompts_before + 1
            expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert not (store/'ods-demo.yadilab').exists()
            page.locator('#project-filename').fill('ods-demo')
            page.locator('#project-filename').dispatch_event('change')
            page.locator('#save-project').click()
            expect(page.locator('#save-indicator')).to_contain_text(
                'Sparat · ods-demo.yadilab', timeout=12000)
            ods_raw=(store/'ods-demo.yadilab').read_bytes()
            assert json.loads(ods_raw) == ods_project
            ods_sha=hashlib.sha256(ods_raw).hexdigest()
            page.locator('#new-project').click()
            page.locator('#saved-projects').select_option('ods-demo')
            page.locator('#open-project').click()
            expect(page.locator('[data-link-id="cable-1"]')).to_have_count(1)
            assert hashlib.sha256((store/'ods-demo.yadilab').read_bytes()).hexdigest() == ods_sha
            assert hashlib.sha256((store/'xlsx-demo.yadilab').read_bytes()).hexdigest() == xlsx_sha
            assert hashlib.sha256((store/'csv-demo.yadilab').read_bytes()).hexdigest() == csv_sha

            # PR25: both REAL workbook formats with explicit Project=1.3,
            # declared MACs, access/trunk VLAN and bidirectional static routes.
            # First refuse off-link next-hop before user accepts replacement.
            malformed_v13 = dict(TABLES_13)
            malformed_v13['StaticRoutes'] = malformed_v13['StaticRoutes'].replace(
                '192.0.2.1,eth0','198.51.100.1,eth0',1)
            with page.expect_response('**/api/import/xlsx') as rejected_v13:
                page.locator('#import-file').set_input_files({
                    'name':'invalid-route.xlsx',
                    'mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'buffer':make_workbook(malformed_v13,shared_strings=True),
                })
            assert rejected_v13.value.status == 422
            expect(page.locator('#toast')).to_contain_text('Import avvisad:')
            expect(page.locator('[data-node-id="pc-a"]')).to_have_count(1)
            assert hashlib.sha256((store/'ods-demo.yadilab').read_bytes()).hexdigest() == ods_sha

            for ext, payload, mime, filename, project_name in [
                ('xlsx',xlsx_v13(shared_strings=True,reorder=True),
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                 'v13-rich.xlsx','XLSX Browser Lab'),
                ('ods',ods_v13(reorder=True,trailing=True,styles=True),
                 'application/vnd.oasis.opendocument.spreadsheet',
                 'v13-rich.ods','ODS Browser Lab'),
            ]:
                previous_sha = hashlib.sha256(
                    (store/'ods-demo.yadilab').read_bytes()).hexdigest()
                with page.expect_response('**/api/import/'+ext) as v13_import:
                    page.locator('#import-file').set_input_files({
                        'name':filename,'mimeType':mime,'buffer':payload,
                    })
                assert v13_import.value.status == 200
                imported = v13_import.value.json()['project']
                assert imported == expected_v13(project_name)
                assert imported['schemaVersion'] == '1.3'
                assert imported['nodes'][0]['ports'][0]['mac'] == '02:00:00:00:00:0A'
                assert imported['nodes'][1]['ports'][1]['vlan'] == {
                    'mode':'trunk','allowedVlans':[10,20]}
                assert imported['nodes'][0]['staticRoutes'][0]['nextHop'] == '192.0.2.1'
                expect(page.locator('[data-node-id="ha"]')).to_have_count(1)
                expect(page.locator('[data-link-id="trunk"]')).to_have_count(1)
                expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
                saved_name='v13-'+ext
                assert not (store/(saved_name+'.yadilab')).exists()
                assert hashlib.sha256((store/'ods-demo.yadilab').read_bytes()).hexdigest() == previous_sha
                page.locator('#project-filename').fill(saved_name)
                page.locator('#project-filename').dispatch_event('change')
                page.locator('#save-project').click()
                expect(page.locator('#save-indicator')).to_contain_text(
                    'Sparat · '+saved_name+'.yadilab',timeout=12000)
                stored=(store/(saved_name+'.yadilab')).read_bytes()
                assert json.loads(stored) == imported
                saved_sha=hashlib.sha256(stored).hexdigest()
                page.locator('#new-project').click()
                page.locator('#saved-projects').select_option(saved_name)
                page.locator('#open-project').click()
                expect(page.locator('[data-node-id="ha"]')).to_have_count(1)
                expect(page.locator('[data-link-id="trunk"]')).to_have_count(1)
                assert hashlib.sha256((store/(saved_name+'.yadilab')).read_bytes()).hexdigest() == saved_sha
                assert hashlib.sha256((store/'ods-demo.yadilab').read_bytes()).hexdigest() == previous_sha
                assert hashlib.sha256((store/'xlsx-demo.yadilab').read_bytes()).hexdigest() == xlsx_sha
                assert hashlib.sha256((store/'csv-demo.yadilab').read_bytes()).hexdigest() == csv_sha

            # PR26: actual browser download from the local server, real ZIP
            # persisted by Playwright, then uploaded through the same UI.
            # A URL click is not evidence of a download unless bytes arrive.
            if network_mode == 'DIRECT_HTTP':
                template_hashes = {
                    name: hashlib.sha256((store/(name+'.yadilab')).read_bytes()).hexdigest()
                    for name in ('lab','csv-demo','xlsx-demo','ods-demo','v13-xlsx','v13-ods')
                }
                for ext, mime in (
                    ('xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('ods','application/vnd.oasis.opendocument.spreadsheet'),
                ):
                    with page.expect_download(timeout=12000) as download_event:
                        page.locator('#template-'+ext).click()
                    download = download_event.value
                    assert download.suggested_filename == 'network-schema13-demo.'+ext
                    downloaded_file = store / ('downloaded-template.'+ext)
                    download.save_as(str(downloaded_file))
                    template_data = downloaded_file.read_bytes()
                    assert template_data[:2] == b'PK'
                    assert len(template_data) > 400
                    assert hashlib.sha256(template_data).hexdigest() == hashlib.sha256(
                        urlopen(base+'api/templates/'+ext).read()).hexdigest()

                    with page.expect_response('**/api/import/'+ext) as template_import:
                        page.locator('#import-file').set_input_files({
                            'name':download.suggested_filename,
                            'mimeType':mime,
                            'buffer':template_data,
                        })
                    assert template_import.value.status == 200
                    example = template_import.value.json()['project']
                    assert example['schemaVersion'] == '1.3'
                    assert len(example['nodes']) == 4
                    assert example['nodes'][0]['id'] == 'demo-client'
                    assert example['nodes'][0]['staticRoutes'][0]['id'] == 'demo-via-router'
                    assert example['nodes'][1]['ports'][1]['vlan'] == {
                        'mode':'trunk','allowedVlans':[10,20]}
                    expect(page.locator('[data-node-id="demo-client"]')).to_have_count(1)
                    expect(page.locator('[data-link-id="demo-link-trunk"]')).to_have_count(1)
                    expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
                    assert not (store/('template-'+ext+'.yadilab')).exists()
                    for name, old_hash in template_hashes.items():
                        assert hashlib.sha256(
                            (store/(name+'.yadilab')).read_bytes()).hexdigest() == old_hash
                # Persist the imported ODS example only on explicit Save,
                # then reopen real bytes; neither template download modifies
                # any earlier .yadilab project.
                page.locator('#project-filename').fill('template-ods')
                page.locator('#project-filename').dispatch_event('change')
                page.locator('#save-project').click()
                expect(page.locator('#save-indicator')).to_contain_text(
                    'Sparat · template-ods.yadilab', timeout=12000)
                persisted = (store/'template-ods.yadilab').read_bytes()
                assert json.loads(persisted) == example
                persisted_sha = hashlib.sha256(persisted).hexdigest()
                page.locator('#new-project').click()
                page.locator('#saved-projects').select_option('template-ods')
                page.locator('#open-project').click()
                expect(page.locator('[data-node-id="demo-client"]')).to_have_count(1)
                assert hashlib.sha256(
                    (store/'template-ods.yadilab').read_bytes()).hexdigest() == persisted_sha
                for name, old_hash in template_hashes.items():
                    assert hashlib.sha256(
                        (store/(name+'.yadilab')).read_bytes()).hexdigest() == old_hash
                assert not errors, errors

            # PR27: current actual *working* schema-1.3 project is exported
            # through both new controls. Inspect actual browser-written file
            # bytes and reimport via the real two independent binary readers.
            current_name = 'template-ods' if network_mode == 'DIRECT_HTTP' else 'v13-ods'
            current_file = store/(current_name+'.yadilab')
            current_bytes = current_file.read_bytes()
            before_export = json.loads(current_bytes)
            before_sha = hashlib.sha256(current_bytes).hexdigest()
            workbook_downloads = {}
            for extension, parser in (('xlsx', import_xlsx_workbook),
                                      ('ods', import_ods_workbook)):
                with page.expect_response('**/api/export/spreadsheet') as export_response:
                    with page.expect_download(timeout=12000) as exported_event:
                        page.locator('#export-'+extension).click()
                response = export_response.value
                assert response.status == 200
                assert exported_event.value.suggested_filename == (
                    'network-documentation.'+extension)
                destination = store/('actual-export.'+extension)
                exported_event.value.save_as(str(destination))
                raw = destination.read_bytes()
                assert raw[:2] == b'PK'
                encoded = response.json()['contentBase64']
                assert hashlib.sha256(raw).digest() == hashlib.sha256(
                    base64.b64decode(encoded,validate=True)).digest()
                restored = parser({
                    'filename':'download.'+extension,
                    'projectName':before_export['name'],
                    'contentBase64':encoded,
                })
                assert restored == before_export
                assert restored['nodes'][0]['staticRoutes'][0]['nextHop'] == (
                    before_export['nodes'][0]['staticRoutes'][0]['nextHop'])
                workbook_downloads[extension] = raw
                assert hashlib.sha256(current_file.read_bytes()).hexdigest() == before_sha
                assert not (store/('export-roundtrip-'+extension+'.yadilab')).exists()

            # Upload precisely the downloaded bytes via both UI routes:
            # no autosave; separate user Save; real disk reopen unchanged.
            for extension in ('xlsx','ods'):
                with page.expect_response('**/api/import/'+extension) as imported_event:
                    page.locator('#import-file').set_input_files({
                        'name':'actual-export.'+extension,
                        'mimeType':(
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            if extension == 'xlsx' else
                            'application/vnd.oasis.opendocument.spreadsheet'
                        ),
                        'buffer':workbook_downloads[extension],
                    })
                assert imported_event.value.status == 200
                result = imported_event.value.json()['project']
                assert result['schemaVersion'] == before_export['schemaVersion']
                assert result['nodes'] == before_export['nodes']
                assert result['links'] == before_export['links']
                assert result['zones'] == before_export['zones']
                expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
                assert hashlib.sha256(current_file.read_bytes()).hexdigest() == before_sha
                slug='export-roundtrip-'+extension
                assert not (store/(slug+'.yadilab')).exists()
                page.locator('#project-filename').fill(slug)
                page.locator('#project-filename').dispatch_event('change')
                page.locator('#save-project').click()
                expect(page.locator('#save-indicator')).to_contain_text(
                    'Sparat · '+slug+'.yadilab',timeout=12000)
                disk=(store/(slug+'.yadilab')).read_bytes()
                assert json.loads(disk) == result
                sha=hashlib.sha256(disk).hexdigest()
                page.locator('#new-project').click()
                page.locator('#saved-projects').select_option(slug)
                page.locator('#open-project').click()
                expect(page.locator('[data-node-id="'+before_export['nodes'][0]['id']+'"]')).to_have_count(1)
                assert hashlib.sha256((store/(slug+'.yadilab')).read_bytes()).hexdigest() == sha
                assert hashlib.sha256(current_file.read_bytes()).hexdigest() == before_sha
            assert not errors, errors

            # Browser ARP diagnostics use real HTTP and unsaved current workspace.
            # Reopen the previous genuinely persisted VLAN 1.2 file, then edit
            # only browser memory to build two configured IPv4 endpoints.
            page.locator('#saved-projects').select_option('lab')
            page.locator('#open-project').click()
            expect(page.locator('[data-node-id="node-2"]')).to_have_count(1)
            source_option = json.dumps(['node-1', 'port-1'], separators=(',', ':'))
            page.locator('#arp-source').select_option(source_option)
            page.locator('#arp-target-ip').fill('192.0.2.20')
            page.locator('#run-arp').click()
            expect(page.locator('#arp-result')).to_contain_text('ARP-simulering avvisad:')
            expect(page.locator('#arp-result')).to_contain_text('explicit IPv4 and MAC')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            page.locator('[data-port-ipv4="port-1"]').fill('192.0.2.10/24')
            with page.expect_response('**/api/validate') as validation:
                page.locator('[data-port-ipv4="port-1"]').dispatch_event('change')
            assert validation.value.status == 200
            page.locator('[data-item-type="node"][data-item-id="node-2"]').click()
            page.locator('[data-port-vlan="port-2"]').fill('access:10')
            with page.expect_response('**/api/validate') as validation:
                page.locator('[data-port-vlan="port-2"]').dispatch_event('change')
            assert validation.value.status == 200
            expect(page.locator('[data-port-vlan="port-2"]')).to_have_value('access:10')
            page.locator('#add-node').click()
            expect(page.locator('[data-node-id="node-3"]')).to_have_count(1)
            page.locator('#new-port-name').fill('eth0')
            page.locator('#submit-port').click()
            page.locator('[data-port-mac="port-1"]').fill('02:00:00:00:00:0B')
            with page.expect_response('**/api/validate') as validation:
                page.locator('[data-port-mac="port-1"]').dispatch_event('change')
            assert validation.value.status == 200
            page.locator('[data-port-ipv4="port-1"]').fill('192.0.2.20/24')
            with page.expect_response('**/api/validate') as validation:
                page.locator('[data-port-ipv4="port-1"]').dispatch_event('change')
            assert validation.value.status == 200
            page.locator('[data-port-node="node-3"][data-port-id="port-1"]').click()
            page.locator('[data-port-node="node-2"][data-port-id="port-2"]').click()
            expect(page.locator('[data-link-id="link-2"]')).to_have_count(1)

            page.locator('#arp-source').select_option(source_option)
            page.locator('#run-arp').click()
            expect(page.locator('#arp-result')).to_contain_text('ARP-status: RESOLVED')
            expect(page.locator('#arp-result')).to_contain_text('192.0.2.20 → 02:00:00:00:00:0B')
            expect(page.locator('#arp-result')).to_contain_text('VLAN 10')
            expect(page.locator('#arp-result')).to_contain_text('Inlärda switch-MAC-tabeller:')
            expect(page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # Moving just one switchport to VLAN 20 makes same /24 ARP fail.
            page.locator('[data-item-type="node"][data-item-id="node-2"]').click()
            page.locator('[data-port-vlan="port-2"]').fill('access:20')
            with page.expect_response('**/api/validate') as validation:
                page.locator('[data-port-vlan="port-2"]').dispatch_event('change')
            assert validation.value.status == 200
            expect(page.locator('#arp-result')).to_contain_text('Ingen aktuell ARP-simulering')
            page.locator('#run-arp').click()
            expect(page.locator('#arp-result')).to_contain_text('ARP-status: NO_REPLY')
            expect(page.locator('#arp-result')).to_contain_text('ARP-cache på avsändarporten:')
            expect(page.locator('#arp-result')).to_contain_text('Tom')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # Explicit memory-backed Layer-2 session over REAL local HTTP.
            # VLAN 20 first isolates the two clients despite matching IPv4 /24.
            page.locator('#session-source').select_option(source_option)
            page.locator('#session-ip').fill('192.0.2.20')
            page.locator('#session-mac').fill('02:00:00:00:00:0B')
            page.locator('#session-start').click()
            expect(page.locator('#session-status')).to_contain_text('Aktiv session')
            assert page.locator('#session-start').is_disabled()
            page.locator('#session-arp').click()
            expect(page.locator('#session-result')).to_contain_text('Status: NO_REPLY')
            expect(page.locator('#session-result')).to_contain_text('ARP-cache på vald källport:')
            expect(page.locator('#session-result')).to_contain_text('Tom')
            expect(page.locator('#session-status')).to_contain_text('1 operation')

            # Changing the documented VLAN revokes the active session.
            page.locator('[data-item-type="node"][data-item-id="node-2"]').click()
            page.locator('[data-port-vlan="port-2"]').fill('access:10')
            with page.expect_response('**/api/validate') as validation:
                page.locator('[data-port-vlan="port-2"]').dispatch_event('change')
            assert validation.value.status == 200
            expect(page.locator('#session-status')).to_contain_text('Ingen aktiv session')
            assert page.locator('#session-arp').is_disabled()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # New session: real ARP learns return path, second run is CACHE_HIT
            # without any fabricated transmissions; opaque Ethernet reuses
            # the same switch MAC state.
            page.locator('#session-start').click()
            expect(page.locator('#session-status')).to_contain_text('Aktiv session')
            page.locator('#session-arp').click()
            expect(page.locator('#session-result')).to_contain_text('Status: RESOLVED')
            expect(page.locator('#session-result')).to_contain_text('192.0.2.20 → 02:00:00:00:00:0B')
            expect(page.locator('#session-result')).to_contain_text('VLAN 10')
            page.locator('#session-arp').click()
            expect(page.locator('#session-result')).to_contain_text('Status: CACHE_HIT')
            expect(page.locator('#session-result')).to_contain_text('Faktiska överföringar: 0')
            page.locator('#session-ethernet').click()
            expect(page.locator('#session-result')).to_contain_text('Status: SIMULATED')
            expect(page.locator('#session-result')).to_contain_text('0x88B5')
            expect(page.locator('#session-result')).to_contain_text('Inlärda MAC-tabeller:')
            expect(page.locator('#session-status')).to_contain_text('3 operation')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest
            page.locator('#session-reset').click()
            expect(page.locator('#session-status')).to_contain_text('0 operation')
            expect(page.locator('#session-result')).to_contain_text('Inga operationer utförda')
            page.locator('#session-arp').click()
            expect(page.locator('#session-result')).to_contain_text('Status: RESOLVED')
            page.locator('#session-stop').click()
            expect(page.locator('#session-status')).to_contain_text('Ingen aktiv session')
            assert page.locator('#session-ethernet').is_disabled()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # First Layer 3 step: real connected-route lookup, NOT ping or
            # network forwarding. Uses explicit host IPv4/CIDR only.
            assert 'node-2' not in page.locator('#route-source option').evaluate_all(
                '(options) => options.map(option => option.value)')
            page.locator('#route-source').select_option('node-1')
            page.locator('#route-destination-ip').fill('192.0.2.20')
            with page.expect_response('**/api/routing/connected') as lookup:
                page.locator('#run-route-lookup').click()
            assert lookup.value.status == 200
            expect(page.locator('#route-result')).to_contain_text('Routingstatus: MATCH')
            expect(page.locator('#route-result')).to_contain_text('192.0.2.0/24')
            expect(page.locator('#route-result')).to_contain_text('node-1/port-1')
            expect(page.locator('#route-result')).to_contain_text('Ingen faktisk paketöverföring')

            page.locator('#route-destination-ip').fill('198.51.100.55')
            with page.expect_response('**/api/routing/connected') as lookup:
                page.locator('#run-route-lookup').click()
            assert lookup.value.status == 200
            expect(page.locator('#route-result')).to_contain_text('Routingstatus: NO_ROUTE')
            page.locator('#route-destination-ip').fill('2001:db8::1')
            with page.expect_response('**/api/routing/connected') as invalid:
                page.locator('#run-route-lookup').click()
            assert invalid.value.status == 422
            expect(page.locator('#route-result')).to_contain_text('Route lookup avvisad')

            # Disabled interface removes its connected prefix. No hidden
            # cable traversal, no simulation success and NO auto-save.
            page.locator('#route-destination-ip').fill('192.0.2.20')
            page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            page.locator('#inspector input[type="checkbox"]').uncheck()
            expect(page.locator('#route-result')).to_contain_text('Ingen aktuell route lookup')
            page.locator('#run-route-lookup').click()
            expect(page.locator('#route-result')).to_contain_text('Routingstatus: NO_ROUTE')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # Schema 1.3 static route: reject off-link gateway, accept explicit
            # next-hop and output interface, inspect the real route lookup.
            page.locator('#inspector input[type="checkbox"]').check()
            page.locator('#new-route-destination').fill('203.0.113.0/24')
            page.locator('#new-route-next-hop').fill('172.16.0.1')
            page.locator('#new-route-out-port').select_option('port-1')
            with page.expect_response('**/api/validate') as rejected:
                page.locator('#add-static-route').click()
            assert rejected.value.status == 422
            expect(page.locator('[data-route-card]')).to_have_count(0)
            page.locator('#new-route-next-hop').fill('192.0.2.1')
            with page.expect_response('**/api/validate') as accepted:
                page.locator('#add-static-route').click()
            assert accepted.value.status == 200
            expect(page.locator('[data-route-card="route-1"]')).to_have_count(1)
            expect(page.locator('[data-route-destination="route-1"]')).to_have_value('203.0.113.0/24')
            expect(page.locator('[data-route-next-hop="route-1"]')).to_have_value('192.0.2.1')
            expect(page.locator('[data-route-out-port="route-1"]')).to_have_value('port-1')
            page.locator('[data-route-next-hop="route-1"]').fill('198.51.100.1')
            with page.expect_response('**/api/validate') as bad_edit:
                page.locator('[data-route-next-hop="route-1"]').dispatch_event('change')
            assert bad_edit.value.status == 422
            expect(page.locator('[data-route-next-hop="route-1"]')).to_have_value('192.0.2.1')

            page.locator('#route-destination-ip').fill('203.0.113.10')
            with page.expect_response('**/api/routing/connected') as lookup:
                page.locator('#run-route-lookup').click()
            assert lookup.value.status == 200
            expect(page.locator('#route-result')).to_contain_text('Routingstatus: MATCH')
            expect(page.locator('#route-result')).to_contain_text('STATIC')
            expect(page.locator('#route-result')).to_contain_text('192.0.2.1')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == digest

            # Administratively disabled out-port suppresses the static route,
            # while its declaration remains available for re-enablement.
            page.locator('#inspector input[type="checkbox"]').uncheck()
            page.locator('#run-route-lookup').click()
            expect(page.locator('#route-result')).to_contain_text('Routingstatus: NO_ROUTE')
            expect(page.locator('[data-route-card="route-1"]')).to_have_count(1)
            page.locator('#inspector input[type="checkbox"]').check()

            # Actual Save, full server process restart, NEW Chromium process,
            # Open and verify identical declared route identity and SHA-256.
            page.locator('#save-project').click()
            expect(page.locator('#save-indicator')).to_contain_text('Sparat · lab.yadilab',timeout=12000)
            routes_raw=saved_file.read_bytes()
            routes_sha=hashlib.sha256(routes_raw).hexdigest()
            assert routes_sha != digest
            routes_doc=json.loads(routes_raw)
            assert routes_doc['schemaVersion'] == '1.3'
            assert routes_doc['nodes'][0]['staticRoutes'] == [{
                'id':'route-1','destination':'203.0.113.0/24',
                'nextHop':'192.0.2.1','outPort':'port-1'}]
            page.close()
            context.close(); browser.close()
            stop_server(proc)

            proc=spawn_server(server_port,store)
            browser=playwright.chromium.launch(headless=True, executable_path=executable,
                                               args=['--no-sandbox'] if executable else [])
            context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
            page=context.new_page()
            page.on('pageerror',lambda error: errors.append(getattr(error,'stack',str(error))))
            network_mode=browser_open(page,base)
            page.locator('#saved-projects').select_option('lab')
            page.locator('#open-project').click()
            expect(page.locator('#save-indicator')).to_contain_text('Sparat · lab.yadilab',timeout=12000)
            page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            expect(page.locator('[data-route-card="route-1"]')).to_have_count(1)
            expect(page.locator('[data-route-next-hop="route-1"]')).to_have_value('192.0.2.1')
            page.locator('#route-source').select_option('node-1')
            page.locator('#route-destination-ip').fill('203.0.113.10')
            page.locator('#run-route-lookup').click()
            expect(page.locator('#route-result')).to_contain_text('Routingstatus: MATCH')
            expect(page.locator('#route-result')).to_contain_text('STATIC')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # PR17: actual IPv4 datagram bytes, ARP and Ethernet on the real
            # documented VLAN 10. A /24-connected peer can receive TTL=1.
            page.locator('#ipv4-source').select_option(source_option)
            page.locator('#ipv4-destination').fill('192.0.2.20')
            page.locator('#ipv4-ttl').fill('1')
            with page.expect_response('**/api/ipv4/trace') as delivered:
                page.locator('#run-ipv4-trace').click()
            assert delivered.value.status == 200
            assert delivered.value.json()['status'] == 'DELIVERED'
            expect(page.locator('#ipv4-result')).to_contain_text('IPv4-status: DELIVERED')
            expect(page.locator('#ipv4-result')).to_contain_text('Mottagande port: node-3/port-1')
            expect(page.locator('#ipv4-result')).to_contain_text('IPv4-ramar: 2')
            expect(page.locator('#ipv4-result')).to_contain_text('Ingen ICMP Echo/Time Exceeded')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # Static next-hop is declared, but nobody at 192.0.2.1 is on
            # the actual wires; no fabricated L3 delivery.
            page.locator('#ipv4-destination').fill('203.0.113.10')
            page.locator('#ipv4-ttl').fill('4')
            with page.expect_response('**/api/ipv4/trace') as not_reached:
                page.locator('#run-ipv4-trace').click()
            assert not_reached.value.status == 200
            assert not_reached.value.json()['status'] == 'ARP_FAILED'
            expect(page.locator('#ipv4-result')).to_contain_text('IPv4-status: ARP_FAILED')
            expect(page.locator('#ipv4-result')).to_contain_text('IPv4-ramar: 0')
            page.locator('#ipv4-ttl').fill('0')
            with page.expect_response('**/api/ipv4/trace') as invalid_ttl:
                page.locator('#run-ipv4-trace').click()
            assert invalid_ttl.value.status == 422
            expect(page.locator('#ipv4-result')).to_contain_text('IPv4-simulering avvisad')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # Real ICMP Echo Request + Reply over explicit same-subnet VLAN
            # cables. Verifies both directions; this is not merely graph/BFS.
            page.locator('#ping-source').select_option(source_option)
            page.locator('#ping-destination').fill('192.0.2.20')
            page.locator('#ping-ttl').fill('1')
            page.locator('#ping-identifier').fill('345')
            page.locator('#ping-sequence').fill('7')
            with page.expect_response('**/api/icmp/echo') as round_trip:
                page.locator('#run-ping').click()
            assert round_trip.value.status == 200
            assert round_trip.value.json()['status'] == 'REPLIED'
            assert round_trip.value.json()['replyMatched'] is True
            expect(page.locator('#ping-result')).to_contain_text('Ping-status: REPLIED')
            expect(page.locator('#ping-result')).to_contain_text('Echo id=345 seq=7')
            expect(page.locator('#ping-result')).to_contain_text('Request: DELIVERED')
            expect(page.locator('#ping-result')).to_contain_text('Reply: DELIVERED')
            expect(page.locator('#ping-result')).to_contain_text('Echo Reply matchad: JA')
            expect(page.locator('#ping-result')).to_contain_text('Svarstid: ej uppmätt')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # A configured static destination route without a reachable
            # next-hop is NOT proof of an Echo Reply or ping success.
            page.locator('#ping-destination').fill('203.0.113.10')
            page.locator('#ping-ttl').fill('4')
            with page.expect_response('**/api/icmp/echo') as unresolved:
                page.locator('#run-ping').click()
            assert unresolved.value.status == 200
            assert unresolved.value.json()['status'] == 'REQUEST_FAILED'
            assert unresolved.value.json()['request']['status'] == 'ARP_FAILED'
            expect(page.locator('#ping-result')).to_contain_text('Ping-status: REQUEST_FAILED')
            expect(page.locator('#ping-result')).to_contain_text('Reply: ingen faktisk datagramöverföring')
            page.locator('#ping-destination').fill('2001:db8::20')
            with page.expect_response('**/api/icmp/echo') as invalid_ip:
                page.locator('#run-ping').click()
            assert invalid_ip.value.status == 422
            expect(page.locator('#ping-result')).to_contain_text('ICMP Echo avvisad')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # PR19: the previously documented nonreachable gateway is NOT
            # a router. Explicitly reconfigure existing reached client node
            # into a router, and point the already declared static next-hop
            # to that real port. No new cable or address is inferred.
            page.locator('[data-item-type="node"][data-item-id="node-3"]').click()
            page.locator('#node-kind').select_option('router')
            page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            page.locator('[data-route-next-hop="route-1"]').fill('192.0.2.20')
            with page.expect_response('**/api/validate') as edited_gateway:
                page.locator('[data-route-next-hop="route-1"]').dispatch_event('change')
            assert edited_gateway.value.status == 200
            expect(page.locator('[data-route-next-hop="route-1"]')).to_have_value('192.0.2.20')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            page.locator('#ping-destination').fill('203.0.113.10')
            page.locator('#ping-ttl').fill('1')
            with page.expect_response('**/api/icmp/echo') as exceeded:
                page.locator('#run-ping').click()
            assert exceeded.value.status == 200
            exceeded_data = exceeded.value.json()
            assert exceeded_data['status'] == 'REQUEST_FAILED'
            assert exceeded_data['request']['status'] == 'TTL_EXPIRED'
            assert exceeded_data['icmpError']['type'] == 11
            assert exceeded_data['icmpError']['status'] == 'RECEIVED'
            assert exceeded_data['icmpError']['trace']['receiver'] == {'node':'node-1','port':'port-1'}
            assert exceeded_data['replyMatched'] is False
            expect(page.locator('#ping-result')).to_contain_text('ICMP-routerfel: Time Exceeded')
            expect(page.locator('#ping-result')).to_contain_text('typ 11/kod 0 · RECEIVED')
            expect(page.locator('#ping-result')).to_contain_text('Felpaketets returtransport: DELIVERED')

            # The same real router has no route toward 203.0.113.10; this
            # invokes distinct RFC 792 Type 3 / Code 0, not a fabricated
            # "destination host ping" or guessed gateway.
            page.locator('#ping-ttl').fill('4')
            with page.expect_response('**/api/icmp/echo') as no_route:
                page.locator('#run-ping').click()
            assert no_route.value.status == 200
            err_data = no_route.value.json()
            assert err_data['status'] == 'REQUEST_FAILED'
            assert err_data['request']['status'] == 'NO_ROUTE'
            assert err_data['icmpError']['type'] == 3
            assert err_data['icmpError']['code'] == 0
            assert err_data['icmpError']['status'] == 'RECEIVED'
            expect(page.locator('#ping-result')).to_contain_text('Destination Unreachable (Network)')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # PR20: repeat the very same real ICMP exchange under three
            # independent canonical snapshots: known-good, one link down,
            # and precisely restored. Nothing changes in the user's Builder
            # project or in the real .yadilab bytes.
            page.locator('#trouble-source').select_option(source_option)
            page.locator('#trouble-destination').fill('192.0.2.20')
            page.locator('#trouble-link').select_option('link-1')
            page.locator('#trouble-ttl').fill('5')
            with page.expect_response('**/api/troubleshoot/link') as comparison:
                page.locator('#run-troubleshoot').click()
            assert comparison.value.status == 200
            result = comparison.value.json()
            assert result['status'] == 'FAULT_CONFIRMED'
            assert result['baseline']['status'] == 'REPLIED'
            assert result['faulted']['status'] == 'REQUEST_FAILED'
            assert result['faulted']['request']['status'] == 'ARP_FAILED'
            assert result['restored']['status'] == 'REPLIED'
            assert result['repair']['scope'] == 'PREVIEW_ONLY'
            assert result['repair']['linkId'] == 'link-1'
            assert result['verifiedRecovery'] is True
            expect(page.locator('#trouble-result')).to_contain_text('Felsökningsstatus: FAULT_CONFIRMED')
            expect(page.locator('#trouble-result')).to_contain_text('Referens: REPLIED')
            expect(page.locator('#trouble-result')).to_contain_text('Kabel avstängd: REQUEST_FAILED')
            expect(page.locator('#trouble-result')).to_contain_text('Återställd kabel: REPLIED')
            expect(page.locator('#trouble-result')).to_contain_text('Återställning efter fel verifierad: JA')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha
            page.locator('[data-item-type="link"][data-item-id="link-1"]').click()
            expect(page.locator('#inspector input[type="checkbox"]')).to_be_checked()

            # Baseline already fails for this destination: no fabricated root
            # cause, despite the explicit selected link fault.
            page.locator('#trouble-destination').fill('203.0.113.10')
            expect(page.locator('#trouble-result')).to_contain_text('Inga jämförda ICMP Echo-spår')
            with page.expect_response('**/api/troubleshoot/link') as baseline_failed:
                page.locator('#run-troubleshoot').click()
            assert baseline_failed.value.status == 200
            failed = baseline_failed.value.json()
            assert failed['status'] == 'BASELINE_NOT_REPLIED'
            assert failed['verifiedFault'] is False
            expect(page.locator('#trouble-result')).to_contain_text('Felsökningsstatus: BASELINE_NOT_REPLIED')
            page.locator('#trouble-ttl').fill('0')
            page.locator('#run-troubleshoot').click()
            expect(page.locator('#trouble-result')).to_contain_text('Felsökningsjämförelse avvisad')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # PR21: the same THREE real ICMP trials on a temporarily disabled
            # existing switch port. Builder port stays enabled throughout.
            page.locator('#trouble-destination').fill('192.0.2.20')
            page.locator('#trouble-ttl').fill('5')
            page.locator('#trouble-type').select_option('PORT_DISABLED')
            switch_port = json.dumps(['node-2','port-1'], separators=(',', ':'))
            page.locator('#trouble-port').select_option(switch_port)
            with page.expect_response('**/api/troubleshoot/fault') as port_fault:
                page.locator('#run-troubleshoot').click()
            assert port_fault.value.status == 200
            port_data = port_fault.value.json()
            assert port_data['status'] == 'FAULT_CONFIRMED'
            assert port_data['fault']['type'] == 'PORT_DISABLED'
            assert port_data['fault']['nodeId'] == 'node-2'
            assert port_data['fault']['portId'] == 'port-1'
            assert port_data['baseline']['status'] == 'REPLIED'
            assert port_data['faulted']['status'] != 'REPLIED'
            assert port_data['restored']['status'] == 'REPLIED'
            assert port_data['repair']['action'] == 'RE_ENABLE_PORT'
            expect(page.locator('#trouble-result')).to_contain_text('Port avstängd: REQUEST_FAILED')
            expect(page.locator('#trouble-result')).to_contain_text('Återställd port: REPLIED')
            page.locator('[data-item-type="node"][data-item-id="node-2"]').click()
            expect(page.locator('#inspector input[type="checkbox"]').first).to_be_checked()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # Moving only the second real switch port from access VLAN 10 to
            # VLAN 20 isolates two otherwise correctly addressed endpoints.
            page.locator('#trouble-type').select_option('ACCESS_VLAN_CHANGED')
            vlan_port = json.dumps(['node-2','port-2'], separators=(',', ':'))
            page.locator('#trouble-vlan-port').select_option(vlan_port)
            page.locator('#trouble-vlan').fill('20')
            with page.expect_response('**/api/troubleshoot/fault') as vlan_fault:
                page.locator('#run-troubleshoot').click()
            assert vlan_fault.value.status == 200
            vlan_data = vlan_fault.value.json()
            assert vlan_data['status'] == 'FAULT_CONFIRMED'
            assert vlan_data['fault']['type'] == 'ACCESS_VLAN_CHANGED'
            assert vlan_data['fault']['fromVlan'] == 10
            assert vlan_data['fault']['toVlan'] == 20
            assert vlan_data['faulted']['request']['status'] == 'ARP_FAILED'
            assert vlan_data['restored']['status'] == 'REPLIED'
            assert vlan_data['repair']['expectedVlan'] == {'mode':'access','vlan':10}
            expect(page.locator('#trouble-result')).to_contain_text('VLAN-fel: REQUEST_FAILED')
            expect(page.locator('#trouble-result')).to_contain_text('Återställt VLAN: REPLIED')
            expect(page.locator('[data-port-vlan="port-2"]')).to_have_value('access:10')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # Strict negative: the configured VLAN cannot be "changed" to
            # itself and then falsely counted as a network fault.
            page.locator('#trouble-vlan').fill('10')
            with page.expect_response('**/api/troubleshoot/fault') as invalid_vlan_fault:
                page.locator('#run-troubleshoot').click()
            assert invalid_vlan_fault.value.status == 422
            expect(page.locator('#trouble-result')).to_contain_text('Felsökningsjämförelse avvisad')
            page.locator('#trouble-type').select_option('TRUNK_VLAN_BLOCKED')
            assert page.locator('#run-troubleshoot').is_disabled()
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # PR22: changing only the destination's configured IPv4 mask to
            # /28 prevents its Reply route back to source 192.0.2.10.
            # Real ICMP request delivery remains intact; rollback restores Echo.
            page.locator('#trouble-type').select_option('IPV4_PREFIX_CHANGED')
            page.locator('#trouble-destination').fill('192.0.2.20')
            page.locator('#trouble-prefix').fill('28')
            page.locator('#trouble-ipv4-port').select_option(
                json.dumps(['node-3','port-1'],separators=(',',':')))
            with page.expect_response('**/api/troubleshoot/fault') as mask_fault:
                page.locator('#run-troubleshoot').click()
            assert mask_fault.value.status == 200
            mask = mask_fault.value.json()
            assert mask['status'] == 'FAULT_CONFIRMED'
            assert mask['fault']['fromIpv4'] == '192.0.2.20/24'
            assert mask['fault']['toIpv4'] == '192.0.2.20/28'
            assert mask['baseline']['status'] == 'REPLIED'
            assert mask['faulted']['request']['status'] == 'DELIVERED'
            assert mask['faulted']['status'] == 'REPLY_FAILED'
            assert mask['faulted']['reply']['status'] == 'NO_ROUTE'
            assert mask['restored']['status'] == 'REPLIED'
            assert mask['repair']['expectedIpv4'] == '192.0.2.20/24'
            expect(page.locator('#trouble-result')).to_contain_text('IPv4-prefix fel: REPLY_FAILED')
            expect(page.locator('#trouble-result')).to_contain_text('Återställt IPv4-prefix: REPLIED')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha
            page.locator('[data-item-type="node"][data-item-id="node-3"]').click()
            expect(page.locator('[data-port-ipv4="port-1"]')).to_have_value('192.0.2.20/24')

            # Reusing a route that already fails in baseline may not yield
            # FAULT_CONFIRMED, even if deleting it changes the error reason.
            page.locator('#trouble-destination').fill('203.0.113.10')
            page.locator('#trouble-type').select_option('STATIC_ROUTE_REMOVED')
            page.locator('#trouble-route').select_option(
                json.dumps(['node-1','route-1'],separators=(',',':')))
            with page.expect_response('**/api/troubleshoot/fault') as route_fault:
                page.locator('#run-troubleshoot').click()
            assert route_fault.value.status == 200
            removed = route_fault.value.json()
            assert removed['status'] == 'BASELINE_NOT_REPLIED'
            assert removed['fault']['type'] == 'STATIC_ROUTE_REMOVED'
            assert removed['fault']['removedRoute']['id'] == 'route-1'
            assert removed['verifiedFault'] is False
            expect(page.locator('#trouble-result')).to_contain_text('Statisk route borttagen')
            expect(page.locator('#trouble-result')).to_contain_text('BASELINE_NOT_REPLIED')
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # Off-link next-hop is rejected, never silently inferred or saved.
            page.locator('#trouble-type').select_option('STATIC_NEXT_HOP_CHANGED')
            page.locator('#trouble-route').select_option(
                json.dumps(['node-1','route-1'],separators=(',',':')))
            page.locator('#trouble-next-hop').fill('198.51.100.1')
            with page.expect_response('**/api/troubleshoot/fault') as bad_hop:
                page.locator('#run-troubleshoot').click()
            assert bad_hop.value.status == 422
            expect(page.locator('#trouble-result')).to_contain_text('Felsökningsjämförelse avvisad')
            page.locator('#trouble-next-hop').fill('192.0.2.254')
            with page.expect_response('**/api/troubleshoot/fault') as wrong_hop:
                page.locator('#run-troubleshoot').click()
            assert wrong_hop.value.status == 200
            wrong = wrong_hop.value.json()
            assert wrong['fault']['fromNextHop'] == '192.0.2.20'
            assert wrong['fault']['toNextHop'] == '192.0.2.254'
            assert wrong['status'] == 'BASELINE_NOT_REPLIED'
            assert wrong['repair']['action'] == 'RESTORE_NEXT_HOP'
            assert wrong['verifiedFault'] is False
            assert hashlib.sha256(saved_file.read_bytes()).hexdigest() == routes_sha

            # Builder Save/Open keeps the exact version token. A later real
            # disk update must surface a conflict without claiming success.
            save_page = context.new_page()
            save_page.on('pageerror', lambda error: errors.append(getattr(error, 'stack', str(error))))
            assert browser_open(save_page, base) == network_mode
            save_page.locator('#project-filename').fill('concurrent-ui')
            save_page.locator('#project-filename').dispatch_event('change')
            save_page.locator('#empty-add').click()
            save_page.locator('#node-label').fill('Initial client')
            save_page.locator('#node-label').dispatch_event('change')
            with save_page.expect_response('**/api/save') as initial_ui_save:
                save_page.locator('#save-project').click()
            assert initial_ui_save.value.status == 200
            ui_file = store / 'concurrent-ui.yadilab'
            first_sha = hashlib.sha256(ui_file.read_bytes()).hexdigest()
            save_page.reload(wait_until='domcontentloaded')
            save_page.locator('#saved-projects').select_option('concurrent-ui')
            save_page.locator('#open-project').click()
            expect(save_page.locator('#save-indicator')).to_contain_text(
                'Sparat · concurrent-ui.yadilab')
            save_page.locator('[data-item-type="node"][data-item-id="node-1"]').click()
            save_page.locator('#node-label').fill('Edited after Open')
            save_page.locator('#node-label').dispatch_event('change')
            with save_page.expect_response('**/api/save') as updated_ui_save:
                save_page.locator('#save-project').click()
            assert updated_ui_save.value.status == 200
            assert json.loads(updated_ui_save.value.request.post_data)[
                'expectedSha256'] == first_sha
            loaded_ui = ProjectStore(store).read('concurrent-ui')
            assert loaded_ui['project']['nodes'][0]['label'] == 'Edited after Open'
            external = json.loads(json.dumps(loaded_ui['project']))
            external['nodes'][0]['label'] = 'External writer'
            external_saved = ProjectStore(store).save(
                'concurrent-ui', external, loaded_ui['sha256'])
            save_page.locator('#node-label').fill('Stale browser edit')
            save_page.locator('#node-label').dispatch_event('change')
            save_page.once('dialog', lambda dialog: dialog.dismiss())
            with save_page.expect_response('**/api/save') as rejected_ui_save:
                save_page.locator('#save-project').click()
            assert rejected_ui_save.value.status == 409
            expect(save_page.locator('#toast')).to_contain_text('Kunde inte spara:')
            expect(save_page.locator('#save-indicator')).to_contain_text('Osparade ändringar')
            assert hashlib.sha256(ui_file.read_bytes()).hexdigest() == external_saved['sha256']
            assert ProjectStore(store).read('concurrent-ui')['project'] == external
            save_page.close()
            persistence_races(context, base, network_mode, store, errors)
            transfer_races(context, base, network_mode, store, errors)
            diagnostic_races(context, base, network_mode, errors)
            investigation_lifecycle_races(context, base, network_mode, errors)
            abandoned_investigation_cleanup(context, network_mode, errors)
            icmp_investigation_races(context, network_mode, errors)
            dora_session_races(context, network_mode, errors)
            assert not errors, errors
            print(f'Browser HTTP mode: {network_mode}')
            print('PASS real Chromium: canonical graph, explicit ports, fault injection,')
            print('     persisted bytes, SHA-256, full process restart, reopen, no silent overwrite')
        finally:
            try: context.close()
            except Exception: pass
            try: browser.close()
            except Exception: pass
            stop_server(proc)


if __name__ == '__main__':
    run()
