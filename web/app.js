import {blank, copy, newNode, newZone, addPort, connect, used, exampleProject, KINDS} from './model.js';
import {TopologyCanvas} from './canvas.js';

const $ = id => document.getElementById(id);
const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'className') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'value') node.value = value;
    else if (key === 'checked') node.checked = Boolean(value);
    else if (key === 'disabled') node.disabled = Boolean(value);
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else node.setAttribute(key, String(value));
  }
  for (const item of children.flat(3)) {
    if (item == null || item === false) continue;
    node.append(item instanceof Node ? item : document.createTextNode(String(item)));
  }
  return node;
};
const field = (title, control) => el('div', {className: 'field'}, el('label', {htmlFor: control.id || ''}, title), control);
const heading = title => el('h3', {className: 'section-title'}, title);
const small = text => el('p', {className: 'muted tiny'}, text);
const button = (text, onclick, variant = 'btn-outline', attrs = {}) =>
  el('button', {type: 'button', className: `btn ${variant}`, onclick, ...attrs}, text);
const input = (value, change, attrs = {}) => {
  const control = el('input', {type: 'text', className: 'control', value: value ?? '', ...attrs});
  control.addEventListener('change', () => change(control.value));
  return control;
};
const dropdown = (options, selected, change, attrs = {}) => {
  const control = el('select', {className: 'control', ...attrs});
  for (const option of options) control.append(el('option', {value: option.value}, option.label));
  control.value = selected == null ? '' : String(selected);
  control.addEventListener('change', () => change(control.value));
  return control;
};
const check = (label, checked, onChange) => {
  const control = el('input', {type: 'checkbox', checked});
  control.addEventListener('change', () => onChange(control.checked));
  return el('label', {className: 'check-line'}, control, label);
};

let project = blank();
let selection = null;
let pendingPort = null;
let traceResult = null;
let highlightedLinks = [];
let filename = 'lab';
let savedName = null;
let savedSha = null;
let savedSnapshot = JSON.stringify(project);
let toastTimer;
const canvas = new TopologyCanvas($('topology'), {
  onSelect: selected => { selection = selected; render(); },
  onPort: handlePort,
  onMove: (id, x, y) => {
    const node = project.nodes.find(item => item.id === id);
    if (node) {
      node.x = Math.max(-100000, Math.min(100000, x));
      node.y = Math.max(-100000, Math.min(100000, y));
      traceResult = null; highlightedLinks = [];
      canvas.setData(project, selection, pendingPort, highlightedLinks);
      updateSaveIndicator();
    }
  },
  onEndMove: render,
  onScale: percentage => { $('scale-label').textContent = `${percentage} %`; },
});

function notify(message, error = false) {
  const box = $('toast');
  box.textContent = message;
  box.hidden = false;
  box.style.borderColor = error ? '#a66b73' : '#487085';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.hidden = true; }, 6500);
}

async function api(path, payload = undefined) {
  const response = await fetch(path, payload === undefined ? undefined : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error(`Oväntat svar från lokal server (${response.status})`); }
  if (!response.ok) {
    const error = new Error(data.message || 'Åtgärden misslyckades');
    error.code = data.error;
    error.currentSha256 = data.currentSha256;
    throw error;
  }
  return data;
}

function isDirty() {
  return savedSnapshot === null || JSON.stringify(project) !== savedSnapshot;
}
function updateSaveIndicator() {
  const span = $('save-indicator');
  span.textContent = savedName && !isDirty() ? `Sparat · ${savedName}.yadilab`
    : !savedName && !isDirty() ? 'Nytt projekt · ej sparat' : 'Osparade ändringar';
  span.classList.toggle('saved', Boolean(savedName) && !isDirty());
}
function changed({keepTrace = false} = {}) {
  if (!keepTrace) {traceResult = null; highlightedLinks = [];}
  render();
}
function select(type, id) { selection = {type, id}; pendingPort = null; render(); }
function getSelected() {
  if (!selection) return null;
  const map = {node: project.nodes, link: project.links, zone: project.zones};
  const value = map[selection.type]?.find(item => item.id === selection.id);
  return value ? {...selection, value} : null;
}

function handlePort(endpoint) {
  if (used(project, endpoint.node, endpoint.port)) {
    notify(`Porten ${endpoint.node}/${endpoint.port} har redan en kabel. Välj en ledig port.`, true);
    return;
  }
  if (!pendingPort) {
    pendingPort = endpoint;
    selection = {type: 'node', id: endpoint.node};
    render();
    notify(`Port ${endpoint.node}/${endpoint.port} vald. Klicka på en ledig port på en annan enhet.`);
    return;
  }
  if (pendingPort.node === endpoint.node && pendingPort.port === endpoint.port) {
    pendingPort = null;
    render();
    notify('Kabelval avbrutet.');
    return;
  }
  try {
    const cable = connect(project, pendingPort, endpoint);
    pendingPort = null;
    selection = {type: 'link', id: cable.id};
    changed();
    notify(`Länk ${cable.id} skapades från två uttryckligen valda portar.`);
  } catch (error) {
    notify(error.message, true);
  }
}

function renderList(container, objects, type, description) {
  container.replaceChildren();
  if (!objects.length) {
    container.append(el('div', {className: 'empty-list'}, description));
    return;
  }
  for (const item of objects) {
    const isNode = type === 'node';
    const isLink = type === 'link';
    const icon = isNode ? {host:'PC', switch:'SW', router:'RT', firewall:'FW'}[item.kind] : isLink ? '—' : '◻';
    const subtitle = isNode ? `${item.id} · ${item.ports.length} portar` : isLink
      ? `${item.a.node}/${item.a.port} → ${item.b.node}/${item.b.port}` : item.id;
    const name = isNode || type === 'zone' ? item.label : item.id;
    container.append(el('button', {type:'button', className: `object${selection?.type === type && selection.id === item.id ? ' active' : ''}`,
      dataset: {itemType: type, itemId: item.id}, onclick: () => select(type, item.id)},
      el('span', {className:'object-icon'}, icon),
      el('span', {className:'object-text'}, el('strong', {}, name), el('small', {}, subtitle)),
      el('span', {className:'object-arrow'}, '›')));
  }
}
function updateTraceSelectors() {
  for (const id of ['trace-source', 'trace-target']) {
    const field = $(id), previous = field.value;
    field.replaceChildren(...project.nodes.map(node => el('option', {value:node.id}, node.label + ' (' + node.id + ')')));
    if (project.nodes.some(n => n.id === previous)) field.value = previous;
    else if (id === 'trace-target' && project.nodes.length > 1) field.value = project.nodes[1].id;
  }
  // Default to two distinct documented devices. A deliberate user selection
  // of the same node is retained and reported as SAME_NODE by the model.
  if (project.nodes.length > 1 && $('trace-source').value === $('trace-target').value
      && $('trace-target').dataset.userSelected !== 'true') {
    $('trace-target').value = project.nodes.find(n => n.id !== $('trace-source').value).id;
  }
  $('run-trace').disabled = project.nodes.length < 2;
  const output = $('trace-result');
  output.classList.remove('ok','fail');
  if (!traceResult) { output.textContent = 'Ingen aktuell spårning.'; return; }
  if (traceResult.status === 'PATH_PRESENT') {
    output.classList.add('ok');
    output.textContent = `Dokumenterad grafväg: ${traceResult.hops.length} länk(ar).\n${traceResult.hops.map(h => `${h.fromNode}/${h.fromPort} → ${h.toNode}/${h.toPort} (${h.linkId})`).join('\n')}\n\nIngen IP- eller routingsimulering utförd.`;
  } else {
    output.classList.add('fail');
    output.textContent = traceResult.status === 'NO_PATH' ? 'Ingen aktiverad dokumenterad grafväg. Kontrollera länkar och portar. Detta bevisar inte att IP-trafik misslyckas.' : traceResult.meaning;
  }
}

function renderInspector() {
  const box = $('inspector');
  box.replaceChildren();
  const selected = getSelected();
  if (!selected) {
    $('inspector-heading').textContent = 'Projekt';
    $('inspector-subtitle').textContent = 'Kanonisk dokumentation, utan härledda nätverksfakta.';
    box.append(field('Projektnamn', input(project.name, value => {
      if (!value.trim() || value.length > 120) return notify('Projektnamnet måste vara 1–120 tecken.', true);
      project.name = value.trim(); changed();
    }, {id:'project-name'})));
    box.append(field('Lokalt filnamn (utan .yadilab)', input(filename, value => {
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(value)) return notify('Filnamn: 1–64 tecken, endast A–Z, 0–9, _ och -.', true);
      // Do not synchronously replace a focused input during its own change
      // event: that can fire a second blur/change and corrupt DOM replacement.
      filename = value;
    }, {id:'project-filename'})));
    box.append(el('div', {className:'muted-panel'}, 'Börja med en enhet, lägg till portar och anslut två lediga portar. Kabeln skapas först efter två uttryckliga val.'));
    box.append(button('Skapa enhet', createNode, 'btn-soft'));
    return;
  }
  const {type, value} = selected;
  $('inspector-heading').textContent = type === 'node' ? value.label : type === 'link' ? value.id : value.label;
  $('inspector-subtitle').textContent = `${type === 'node' ? 'Kanonisk enhet' : type === 'link' ? 'Källdeklarerad länk' : 'Dokumenterad zon'} · ${value.id}`;
  if (type === 'node') {
    box.append(field('Visningsnamn', input(value.label, next => {
      if (!next.trim() || next.length > 120) return notify('Ange ett giltigt namn.', true);
      value.label = next.trim(); changed();
    }, {id:'node-label'})));
    box.append(field('Enhetstyp', dropdown(KINDS.map(v => ({value:v,label:v})), value.kind, next => {
      if (next === 'switch' && value.ports.some(port => port.mac != null)) {
        notify('Ta bort konfigurerade MAC-adresser innan enheten ändras till switch.', true);
        renderInspector(); return;
      }
      value.kind = next; changed();
    }, {id:'node-kind'})));
    box.append(field('Dokumenterad zon', dropdown([{value:'',label:'Ingen zon'}, ...project.zones.map(z => ({value:z.id,label:z.label}))], value.zoneId || '', next => {
      value.zoneId = next || null; changed();
    }, {id:'node-zone'})));
    box.append(el('div', {className:'mini-grid'},
      field('X', input(String(value.x), next => moveCoord(value,'x',next), {id:'node-x',type:'number'})),
      field('Y', input(String(value.y), next => moveCoord(value,'y',next), {id:'node-y',type:'number'}))));
    box.append(heading(`Portar (${value.ports.length})`));
    if (!value.ports.length) box.append(small('Lägg till minst en port för att skapa en fysisk länk.'));
    for (const port of value.ports) {
      const occupied = used(project, value.id, port.id);
      const card = el('div', {className:'port-card', dataset:{portCard:port.id}},
        el('div', {className:'port-head'},
          el('strong', {}, port.name),
          el('small', {}, `${port.id}${occupied ? ' · ansluten' : ' · ledig'}`)),
        field('Portnamn', input(port.name, next => {
          if (!next.trim() || next.length > 120) return notify('Portnamn saknas.',true);
          port.name = next.trim(); changed();
        }, {dataset:{portName:port.id}})),
        field('IPv4/CIDR (valfritt)', input(port.ipv4 || '', async next => {
          const attempt = copy(project);
          const portCopy = attempt.nodes.find(n => n.id === value.id).ports.find(p => p.id === port.id);
          portCopy.ipv4 = next.trim() || null;
          try {
            const normalized = await api('/api/validate', attempt);
            project = normalized.project;
            changed();
          } catch (error) { notify(error.message, true); renderInspector(); }
        }, {dataset:{portIpv4:port.id},placeholder:'192.0.2.1/24'})),
        value.kind === 'switch' ? null : field('MAC-adress (valfri, explicit)', input(port.mac || '', async next => {
          const attempt = copy(project);
          // A legacy 1.0 file is upgraded in memory only after deliberate editing.
          attempt.schemaVersion = '1.1';
          const portCopy = attempt.nodes.find(n => n.id === value.id).ports.find(p => p.id === port.id);
          portCopy.mac = next.trim() || null;
          try {
            const normalized = await api('/api/validate', attempt);
            project = normalized.project;
            changed();
          } catch (error) { notify(error.message, true); renderInspector(); }
        }, {dataset:{portMac:port.id},placeholder:'02:00:00:00:00:0A'})),
        check('Port aktiverad', port.enabled, enabled => { port.enabled = enabled; changed(); }),
        button('Ta bort port', () => {
          if (occupied && !confirm('Porten har en ansluten länk. Ta bort BÅDE porten och den uttryckligen valda länken?')) return;
          project.links = project.links.filter(l => !(l.a.node === value.id && l.a.port === port.id) && !(l.b.node === value.id && l.b.port === port.id));
          value.ports = value.ports.filter(p => p.id !== port.id);
          changed();
        }, 'btn-outline', {dataset:{deletePort:port.id}}));
      box.append(card);
    }
    const portName = el('input', {className:'control',placeholder:'t.ex. eth0',id:'new-port-name',maxLength:120});
    const add = button('+ Lägg till port', () => {
      try {
        addPort(value, portName.value); changed();
      } catch (error) { notify(error.message,true); }
    }, 'btn-soft', {id:'submit-port'});
    box.append(el('div', {className:'field'}, el('label',{htmlFor:'new-port-name'},'Ny port'),portName,add));
    box.append(el('div', {className:'muted-panel'}, 'Koppla två lediga portar genom att klicka på deras cirklar i nätverksvyn. Inga anslutningar skapas utifrån närhet.'));
    box.append(button('Ta bort enhet', () => {
      const associated = project.links.filter(l => l.a.node === value.id || l.b.node === value.id);
      if (!confirm(`Ta bort ${value.label} samt dess ${associated.length} deklarerade länkar?`)) return;
      project.nodes = project.nodes.filter(n => n.id !== value.id);
      project.links = project.links.filter(l => l.a.node !== value.id && l.b.node !== value.id);
      selection = null; pendingPort = null; changed();
    }, 'btn-outline danger', {id:'delete-node'}));
  } else if (type === 'link') {
    box.append(el('div', {className:'link-card'},
      el('div', {className:'small-muted'}, 'EXAKTA DEKLARERADE ÄNDPUNKTER'),
      el('strong', {}, `${value.a.node} / ${value.a.port}`),
      el('div', {className:'small-muted'}, '↓ FYSISK LÄNK ↓'),
      el('strong', {}, `${value.b.node} / ${value.b.port}`)));
    box.append(check('Länk aktiverad (felinjicering)', value.enabled, enabled => {
      value.enabled = enabled; changed();
    }));
    box.append(small('Avaktivering påverkar endast den dokumenterade grafspårningen. Den simulerar inte nätverksprotokoll.'));
    box.append(button('Ta bort länk', () => {
      if (!confirm(`Ta bort deklarerad länk ${value.id}?`)) return;
      project.links = project.links.filter(l => l.id !== value.id);
      selection = null; changed();
    }, 'btn-outline danger', {id:'delete-link'}));
  } else if (type === 'zone') {
    box.append(field('Zonnamn',input(value.label, next => {
      if (!next.trim() || next.length > 120) return notify('Ogiltigt zonnamn.',true);
      value.label = next.trim(); changed();
    }, {id:'zone-label'})));
    box.append(small(`Medlemmar: ${project.nodes.filter(n => n.zoneId === value.id).length}. Zonindelning skapar inga kablar.`));
    box.append(button('Ta bort zon', () => {
      if (!confirm(`Ta bort zon ${value.label}? Enheterna behålls men får "Ingen zon".`)) return;
      project.nodes.forEach(n => { if (n.zoneId === value.id) n.zoneId = null; });
      project.zones = project.zones.filter(z => z.id !== value.id);
      selection = null; changed();
    }, 'btn-outline danger'));
  }
}
function moveCoord(node, axis, next) {
  const num = Number(next);
  if (next.trim() === '' || !Number.isFinite(num) || Math.abs(num) > 100000) return notify('Koordinaten måste vara mellan −100000 och 100000.',true);
  node[axis] = num; changed();
}
let rendering = false;
let rerenderRequested = false;
function render() {
  // DOM removal can synchronously blur focused inputs, causing another change
  // event during replaceChildren. Coalesce it instead of re-entering rendering.
  if (rendering) { rerenderRequested = true; return; }
  rendering = true;
  try {
  if (getSelected() === null) selection = null;
  $('breadcrumb').textContent = project.name;
  $('count-nodes').textContent = String(project.nodes.length);
  $('count-links').textContent = String(project.links.length);
  $('count-zones').textContent = String(project.zones.length);
  $('node-list-size').textContent = String(project.nodes.length);
  $('link-list-size').textContent = String(project.links.length);
  renderList($('node-list'), project.nodes, 'node', 'Inga dokumenterade enheter');
  renderList($('link-list'), project.links, 'link', 'Inga deklarerade länkar');
  renderList($('zone-list'), project.zones, 'zone', 'Inga zoner');
  $('empty-state').hidden = project.nodes.length > 0;
  $('canvas-hint').textContent = pendingPort ? `Vald port: ${pendingPort.node}/${pendingPort.port}. Klicka en andra ledig port eller samma port för att avbryta.`
    : 'Dra enheter för att placera dem. Klicka två lediga portcirklar för att skapa en länk.';
  canvas.setData(project, selection, pendingPort, highlightedLinks);
  renderInspector();
  updateTraceSelectors();
  updateSaveIndicator();
  } finally {
    rendering = false;
    if (rerenderRequested) {
      rerenderRequested = false;
      queueMicrotask(render);
    }
  }
}
function createNode() {
  const node = newNode(project);
  selection = {type:'node',id:node.id}; pendingPort = null;
  changed(); canvas.fit();
  notify(`Enhet ${node.id} skapades utan antagna anslutningar.`);
}
function createZone() {
  const zone = newZone(project);
  selection = {type:'zone',id:zone.id}; changed();
}
function confirmDiscard() {
  return !isDirty() || confirm('Det finns osparade ändringar. Lämna projektet utan att spara?');
}
function resetProject(value = blank(), pristineBlank = false) {
  project = value;
  delete $('trace-target').dataset.userSelected;
  selection = null;
  pendingPort = null;
  filename = 'lab'; savedName = null; savedSha = null;
  savedSnapshot = pristineBlank ? JSON.stringify(project) : null;
  changed(); canvas.fit();
}
async function saveProject() {
  try {
    let expectedSha256 = savedName === filename ? savedSha : null;
    let result;
    try { result = await api('/api/save', {filename, project, expectedSha256}); }
    catch (error) {
      if (error.code !== 'CONFLICT' || !confirm(`Filen ${filename}.yadilab har annat innehåll eller finns redan. Skriv över den AKTUELLA versionen på disk?`)) throw error;
      expectedSha256 = error.currentSha256 || null;
      if (expectedSha256 === null) throw new Error('Filen ändrades eller försvann. Försök spara igen.');
      result = await api('/api/save', {filename, project, expectedSha256});
    }
    project = result.project;
    savedName = result.filename;
    savedSha = result.sha256;
    savedSnapshot = JSON.stringify(project);
    render();
    await refreshSavedProjects();
    notify(`Sparat till lokal fil: ${savedName}.yadilab · ${result.bytes} byte · SHA-256 ${savedSha.slice(0,14)}…`);
  } catch (error) {
    notify(`Kunde inte spara: ${error.message}`, true);
  }
}
async function refreshSavedProjects() {
  try {
    const list = await api('/api/projects');
    const select = $('saved-projects');
    const previous = select.value;
    select.replaceChildren(el('option',{value:''},'Välj sparat projekt…'),
      ...list.projects.map(item => el('option',{value:item.filename},`${item.filename}.yadilab`)));
    if (list.projects.some(item => item.filename === previous)) select.value = previous;
  } catch (error) { notify(`Projektlistan kunde inte läsas: ${error.message}`,true); }
}
async function openProject() {
  const slug = $('saved-projects').value;
  if (!slug) return notify('Välj en sparad projektfil först.',true);
  if (!confirmDiscard()) return;
  try {
    const loaded = await api(`/api/projects/${encodeURIComponent(slug)}`);
    project = loaded.project;
    filename = loaded.filename;
    savedName = loaded.filename;
    savedSha = loaded.sha256;
    savedSnapshot = JSON.stringify(project);
    selection = null; pendingPort = null; traceResult = null; highlightedLinks = [];
    render(); canvas.fit();
    notify(`Öppnade verklig projektfil: ${loaded.filename}.yadilab · SHA-256 ${loaded.sha256.slice(0,14)}…`);
  } catch (error) { notify(`Kunde inte öppna: ${error.message}`,true); }
}
async function decodeUtf8(file) {
  // File.text() silently substitutes malformed bytes; canonical imports must
  // either preserve the input or report an error without replacing the project.
  return new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer());
}
async function importProjects(files) {
  if (!files?.length) return;
  try {
    let result;
    if (files.every(file => file.name.endsWith('.csv'))) {
      if (files.length > 4) throw new Error('Välj högst fyra CSV-tabeller.');
      const projectName = prompt('Projektnamn för CSV-importen:', project.name);
      if (projectName === null) return;
      const sources = [];
      for (const file of files) {
        if (file.size > 8 * 1024 * 1024) throw new Error('CSV-fil är större än 8 MiB.');
        sources.push({name: file.name, text: await decodeUtf8(file)});
      }
      result = await api('/api/import/csv', {projectName, files: sources});
    } else if (files.length === 1 && ['.json', '.yadilab'].some(extension => files[0].name.toLowerCase().endsWith(extension))) {
      if (files[0].size > 8 * 1024 * 1024) throw new Error('Filen är större än 8 MiB.');
      result = await api('/api/validate', JSON.parse(await decodeUtf8(files[0])));
    } else {
      throw new Error('Välj antingen en .json/.yadilab-fil eller CSV-tabellerna Devices.csv, Interfaces.csv, Links.csv och eventuellt Zones.csv.');
    }
    // Validate completely before asking to replace the current workspace.
    // Cancel or invalid CSV must not disturb existing edits or disk bytes.
    const incoming = result.project;
    if (!confirmDiscard()) return;
    if (!confirm(`Importen innehåller ${incoming.nodes.length} enheter och ${incoming.links.length} uttryckligt deklarerade länkar. Ersätta nuvarande arbetsyta? Ingen fil skrivs automatiskt.`)) return;
    resetProject(incoming);
    notify(`Importerade ${incoming.nodes.length} enheter, ${incoming.links.length} länkar och ${incoming.zones.length} zoner. Inget sparades automatiskt.`);
  } catch (error) { notify(`Import avvisad: ${error.message}`, true); }
}

async function exportProject() {
  try {
    const validated = await api('/api/validate',project);
    const bytes = JSON.stringify(validated.project,null,2) + '\n';
    const url = URL.createObjectURL(new Blob([bytes],{type:'application/json'}));
    const a = el('a',{href:url,download:`${filename}.yadilab`});
    document.body.append(a);
    a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url),30000);
    notify('Export/nedladdning initierad. Webbläsarens faktiska skrivning till disk är inte verifierad.');
  } catch (error) { notify(`Export avvisad: ${error.message}`,true); }
}
async function runTrace() {
  const source = $('trace-source').value, target = $('trace-target').value;
  if (!source || !target) return;
  try {
    const result = await api('/api/trace', {project, source, target});
    traceResult = result; highlightedLinks = result.hops.map(h => h.linkId);
    render();
  } catch (error) { notify(`Spårning avvisad: ${error.message}`,true); }
}

$('add-node').addEventListener('click', createNode);
$('empty-add').addEventListener('click', createNode);
$('add-zone').addEventListener('click', createZone);
$('save-project').addEventListener('click', saveProject);
$('open-project').addEventListener('click', openProject);
$('new-project').addEventListener('click', () => {if (confirmDiscard()) resetProject(blank(), true);});
$('load-example').addEventListener('click', () => {
  if (!confirmDiscard()) return;
  resetProject(exampleProject());
  notify('Märkt demoexempel inläst. Detta är inte importerad dokumentation.');
});
$('import-project').addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', async event => {
  const files = Array.from(event.target.files);
  await importProjects(files);
  event.target.value = '';
});
$('export-project').addEventListener('click', exportProject);
$('run-trace').addEventListener('click', runTrace);
$('trace-target').addEventListener('change', () => { $('trace-target').dataset.userSelected = 'true'; });
$('zoom-in').addEventListener('click', () => canvas.zoom(1.2));
$('zoom-out').addEventListener('click', () => canvas.zoom(1 / 1.2));
$('zoom-fit').addEventListener('click', () => canvas.fit());
window.addEventListener('beforeunload', event => {
  if (!isDirty()) return;
  event.preventDefault();
  event.returnValue = '';
});
render();
canvas.fit();
refreshSavedProjects();
