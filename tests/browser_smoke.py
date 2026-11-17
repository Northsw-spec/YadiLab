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
from xlsx_fixture import make_workbook, workbook_parts, zip_parts
from ods_fixture import make_ods, ods_parts, zip_parts as zip_ods_parts


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
