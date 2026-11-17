"""Real Chromium end-to-end: UI, link semantics, faults and restart Save/Open."""
from __future__ import annotations

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
    app = app.replace("import {blank, copy, newNode, newZone, addPort, connect, used, exampleProject, KINDS} from './model.js';", '')
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

            # Save real bytes under local app data directory.
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

            # Explicit export contains only the canonical document format.
            with page.expect_download(timeout=12000) as download_event:
                page.locator('#export-project').click()
            download = download_event.value
            assert download.suggested_filename == 'lab.yadilab'
            exported = json.loads(Path(download.path()).read_bytes())
            assert exported == parsed, 'exported bytes do not represent saved canonical facts'

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
                dialog.accept('CSV acceptance lab') if dialog.type == 'prompt' else dialog.accept()
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
