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
import time
from pathlib import Path
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
from xlsx_fixture import make_workbook, workbook_parts, zip_parts
from ods_fixture import make_ods, ods_parts, zip_parts as zip_ods_parts
from spreadsheet_v13_fixture import TABLES_13, expected_v13, xlsx_v13, ods_v13
from network_core.xlsx_import import import_xlsx_workbook
from network_core.ods_import import import_ods_workbook
from test_dhcp import topology as dhcp_topology
from test_dhcp_registry import clients as dhcp_multi_clients


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
    app = (ROOT / 'web/app.js').read_text(encoding='utf8')
    app = app.replace("import {blank, copy, newNode, newZone, addPort, connect, used, nextId, exampleProject, KINDS} from './model.js';", '')
    app = app.replace("import {TopologyCanvas} from './canvas.js';", '')
    page.add_script_tag(content=model + '\n' + canvas + '\n' + app)
    return 'BRIDGED_LOCAL_HTTP'


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
        base=f'http://127.0.0.1:{server_port}/'
        try:
            network_mode = browser_open(page, base)
            expect(page.locator('#empty-state')).to_be_visible()
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
            assert [t['linkId'] for t in lost_t1['result']['request']['transmissions']] == ['wire-3']
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
