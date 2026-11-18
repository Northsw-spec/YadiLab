import {blank, copy, newNode, newZone, addPort, connect, used, nextId, exampleProject, KINDS} from './model.js';
import {TopologyCanvas} from './canvas.js';
import {$, el, field, heading, small, button, input, dropdown, check} from './ui/dom.js';
import {api} from './services/api.js';
import {prepareSave, saveSnapshot, listSavedProjects, readSavedProject} from './features/projects/persistence.js';
import {importKind, prepareImport, submitImport, prepareProjectExport, prepareSpreadsheetExport} from './features/projects/transfer.js';
import {presentArp, presentRoute, presentPing, presentIPv4} from './features/diagnostics/presenters.js';
import {queryArp, queryRoute, queryIPv4, queryPing} from './features/diagnostics/queries.js';
import {createDhcpInvestigationController} from './features/sessions/dhcp-investigation.js';
import {createIcmpInvestigationController} from './features/sessions/icmp-investigation.js';

let project = blank();
let selection = null;
let pendingPort = null;
let traceResult = null;
let highlightedLinks = [];
let arpDiagnostic = null;
let arpHighlightedLinks = [];
let dhcpDiagnostic = null;
let dhcpGeneration = 0;
let dhcpBusy = false;
let doraDiagnostic = null;
let doraGeneration = 0;
let doraBusy = false;
let doraSessionId = null;
let doraSessionGeneration = 0;
let doraSessionBusy = false;
let doraSessionState = null;
let doraSessionTrace = null;
let doraClockEvent = null;
let doraRenewalTrace = null;
let doraFaultEvent = null;
let doraPortFaultEvent = null;
let doraVlanFaultEvent = null;
let sessionId = null;
let sessionGeneration = 0;
let sessionBusy = false;
let sessionOperationCount = 0;
let sessionDiagnostic = null;
let sessionHighlightedLinks = [];
let routeLookup = null;
let ipv4Diagnostic = null;
let pingDiagnostic = null;
let troubleDiagnostic = null;
let filename = 'lab';
let savedName = null;
let savedSha = null;
let savedSnapshot = JSON.stringify(project);
let editRevision = 0;
let workspaceRevision = 0;
let savePending = false;
const diagnosticRuns = {arp: 0, route: 0, ipv4: 0, ping: 0};
const diagnosticFields = {
  arp: ['arp-source', 'arp-target-ip'],
  route: ['route-source', 'route-destination-ip'],
  ipv4: ['ipv4-source', 'ipv4-destination', 'ipv4-ttl'],
  ping: ['ping-source', 'ping-destination', 'ping-ttl', 'ping-identifier', 'ping-sequence'],
};
let toastTimer;
const investigation = createDhcpInvestigationController({
  getContext: () => ({workspaceRevision, editRevision, projectSnapshot: JSON.stringify(project)}),
  onChange: renderInvestigation,
});
const icmpInvestigation = createIcmpInvestigationController({
  getContext: () => ({workspaceRevision, editRevision, projectSnapshot: JSON.stringify(project)}),
  onChange: renderIcmpInvestigation,
});
const canvas = new TopologyCanvas($('topology'), {
  onSelect: selected => { selection = selected; render(); },
  onPort: handlePort,
  onMove: (id, x, y) => {
    const node = project.nodes.find(item => item.id === id);
    if (node) {
      node.x = Math.max(-100000, Math.min(100000, x));
      node.y = Math.max(-100000, Math.min(100000, y));
      editRevision += 1;
      traceResult = null; highlightedLinks = [];
      routeLookup = null;
      ipv4Diagnostic = null;
      pingDiagnostic = null;
      troubleDiagnostic = null;
      invalidateDhcpDiagnostics();
      invalidateDoraDiagnostics();
      invalidateDoraSession();
      invalidateSimulationSession();
      renderSessionDiagnostics();
      renderDhcpDiagnostics();
      renderDoraDiagnostics();
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

function isDirty() {
  return savedSnapshot === null || JSON.stringify(project) !== savedSnapshot;
}
function updateSaveIndicator() {
  const span = $('save-indicator');
  span.textContent = savedName && !isDirty() ? `Sparat · ${savedName}.yadilab`
    : !savedName && !isDirty() ? 'Nytt projekt · ej sparat' : 'Osparade ändringar';
  span.classList.toggle('saved', Boolean(savedName) && !isDirty());
}
function invalidateDhcpDiagnostics() {
  dhcpGeneration += 1;
  dhcpDiagnostic = null;
}
function invalidateDoraDiagnostics() {
  doraGeneration += 1;
  doraDiagnostic = null;
}
function invalidateInvestigation() { investigation.invalidate(); }

function invalidateIcmpInvestigation() { icmpInvestigation.invalidate(); }

function invalidateDoraSession() {
  invalidateIcmpInvestigation();
  invalidateInvestigation();
  doraSessionGeneration += 1;
  const previous = doraSessionId;
  doraSessionId = null;
  doraSessionBusy = false;
  doraSessionState = null;
  doraSessionTrace = null;
  doraClockEvent = null;
  doraRenewalTrace = null;
  doraFaultEvent = null;
  doraPortFaultEvent = null;
  doraVlanFaultEvent = null;
  if (previous) {
    // Best-effort release; backend also refuses any changed project snapshot.
    void api('/api/dhcp/session/stop', {sessionId: previous}).catch(() => {});
  }
}
function changed({keepTrace = false} = {}) {
  editRevision += 1;
  invalidateDhcpDiagnostics();
  invalidateDoraDiagnostics();
  invalidateDoraSession();
  if (!keepTrace) {traceResult = null; highlightedLinks = [];}
  routeLookup = null;
  ipv4Diagnostic = null;
  pingDiagnostic = null;
  troubleDiagnostic = null;
  // Any network/document change invalidates sessions bound to the old snapshot.
  invalidateSimulationSession();
  arpDiagnostic = null; arpHighlightedLinks = [];
  render();
}

function invalidateSimulationSession() {
  sessionGeneration += 1;
  const previous = sessionId;
  sessionId = null;
  sessionBusy = false;
  sessionOperationCount = 0;
  sessionDiagnostic = null;
  sessionHighlightedLinks = [];
  if (previous) {
    // Best-effort release only; the server still rejects any stale project.
    void api('/api/simulation/stop', {sessionId: previous}).catch(() => {});
  }
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

function renderArpDiagnostics() {
  const selector = $('arp-source');
  const previous = selector.value;
  const interfaces = project.nodes.filter(node => node.kind !== 'switch')
    .flatMap(node => node.ports.map(port => ({
      value: JSON.stringify([node.id, port.id]),
      label: `${node.label} / ${port.name} (${node.id}/${port.id})`,
    })));
  selector.replaceChildren(...interfaces.map(item => el('option', {value:item.value}, item.label)));
  if (interfaces.some(item => item.value === previous)) selector.value = previous;
  $('run-arp').disabled = interfaces.length === 0;

  const output = $('arp-result');
  const presentation = presentArp(arpDiagnostic);
  output.classList.toggle('ok', presentation.status === 'ok');
  output.classList.toggle('fail', presentation.status === 'fail');
  output.textContent = presentation.text;
}

function dhcpPortChoices(role) {
  return project.nodes
    .filter(n => role === 'client' ? n.kind === 'host' :
      (n.kind === 'host' || n.kind === 'router'))
    .flatMap(n => n.ports
      .filter(p => role === 'client' ? p.ipv4 === null : p.ipv4 !== null)
      .map(p => ({
        value: JSON.stringify([n.id, p.id]),
        label: n.label + ' / ' + p.name + ' (' + n.id + '/' + p.id + ')'
          + (p.mac ? '' : ' · MAC saknas'),
      })));
}
function populateDhcpPortSelectors(prefix) {
  const clientOptions = dhcpPortChoices('client');
  const serverOptions = dhcpPortChoices('server');
  for (const [id, options, empty] of [
    [prefix + '-client', clientOptions, 'Ingen hostport utan IPv4'],
    [prefix + '-server', serverOptions, 'Ingen host/routerport med IPv4'],
  ]) {
    const selector = $(id);
    const previous = selector.value;
    selector.replaceChildren(...(options.length
      ? options.map(item => el('option', {value: item.value}, item.label))
      : [el('option', {value: ''}, empty)]));
    if (options.some(item => item.value === previous)) selector.value = previous;
  }
  return {clientOptions, serverOptions};
}

function renderDhcpDiagnostics() {
  const {clientOptions, serverOptions} = populateDhcpPortSelectors('dhcp');
  $('run-dhcp').disabled = dhcpBusy || !clientOptions.length || !serverOptions.length;
  const output = $('dhcp-result');
  output.classList.remove('ok', 'fail');
  if (dhcpBusy && !dhcpDiagnostic) {
    output.textContent = 'Simulerar DHCPDISCOVER och eventuell DHCPOFFER över deklarerat Layer 2…';
    return;
  }
  if (!dhcpDiagnostic) {
    output.textContent = 'Ingen aktuell DHCP-diagnostik. Välj klient, server och föreslagen IPv4; inget tilldelas eller sparas.';
    return;
  }
  if (dhcpDiagnostic.error) {
    output.classList.add('fail');
    output.textContent = `DHCP-diagnostik avvisad: ${dhcpDiagnostic.error}\nIngen DHCP-adress har tilldelats.`;
    return;
  }
  const data = dhcpDiagnostic;
  output.classList.add(data.status === 'OFFER_RECEIVED' ? 'ok' : 'fail');
  const transmissions = items => items.length
    ? items.map(t =>
      `  ${t.linkId}: ${t.from.node}/${t.from.port} → ${t.to.node}/${t.to.port}`
      + (t.vlanId == null ? ' · otaggad' : ` · VLAN ${t.vlanId}`)
      + (t.tagged ? ' (802.1Q)' : '')).join('\n')
    : '  Inga';
  const vlanDrops = items => items.length
    ? items.map(d => `  ${d.switch}/${d.port}: ${d.reason} · VLAN ${d.vlanId ?? 'okänt'}`).join('\n')
    : '  Inga observerade';
  const learned = data.macTables.flatMap(t => [
    `  ${t.switchId}${t.vlanId == null ? ' (otaggad)' : ` VLAN ${t.vlanId}`}:`,
    ...Object.entries(t.entries).map(([mac, port]) => `    ${mac} → ${port}`),
  ]);
  output.textContent = [
    `DHCP-status: ${data.status} · transaktions-ID ${data.transactionId}`,
    data.meaning,
    `DISCOVER (klient → broadcast): ${data.discover.transmissions.length} fysisk(a) överföring(ar)\n`
      + transmissions(data.discover.transmissions),
    `Vald serverport nåddes: ${data.discover.receivedAtServer ? 'ja' : 'nej'}`,
    `OFFER (server → broadcast): ${data.offer.transmissions.length} fysisk(a) överföring(ar)\n`
      + transmissions(data.offer.transmissions),
    `VLAN-drop, Discover:\n${vlanDrops(data.discover.vlanDrops)}`,
    `VLAN-drop, Offer:\n${vlanDrops(data.offer.vlanDrops)}`,
    `Tillfälligt inlärda MAC-tabeller:\n${learned.join('\n') || '  Inga'}`,
    data.status === 'OFFER_RECEIVED'
      ? `Föreslagen IP: ${data.offeredIpv4} · mask ${data.subnetMask} · server ${data.serverIdentifier}`
      : 'Inget erbjudande bekräftat på klientporten.',
    'Lease skapad: NEJ. Ingen DHCPREQUEST/ACK. Ingen adress konfigureras, och ledighet i verkligt nät är inte verifierad.',
  ].join('\n\n');
}

function renderDoraDiagnostics() {
  const {clientOptions, serverOptions} = populateDhcpPortSelectors('dora');
  $('run-dora').disabled = doraBusy || doraSessionBusy || doraSessionId !== null
    || !clientOptions.length || !serverOptions.length;
  const output = $('dora-result');
  output.classList.remove('ok', 'fail');
  if (doraBusy && !doraDiagnostic) {
    output.textContent = 'Simulerar fyra DHCP-meddelanden. Ingen adress skrivs till projektet.';
    return;
  }
  if (!doraDiagnostic) {
    output.textContent = 'Ingen aktuell DORA-diagnostik. Välj klient, server och en uttrycklig pool. Ingen adress tilldelas i det sparade projektet.';
    return;
  }
  if (doraDiagnostic.error) {
    output.classList.add('fail');
    output.textContent = 'DORA avvisad: ' + doraDiagnostic.error
      + '\nIngen simulerad lease skapad. Dokumenterad IPv4 är oförändrad.';
    return;
  }
  const data = doraDiagnostic;
  const bound = data.status === 'ACK_RECEIVED' && data.leaseCommitted === true
    && data.lease && data.lease.state === 'BOUND';
  output.classList.add(bound ? 'ok' : 'fail');
  const phaseLines = (title, phase) => {
    const lines = [title + ' – ' + phase.transmissions.length + ' deklarerade överföringar'];
    for (const t of phase.transmissions) lines.push(
      '  ' + t.linkId + ': ' + t.from.node + '/' + t.from.port
      + ' → ' + t.to.node + '/' + t.to.port
      + (t.vlanId == null ? ' · otaggad' : ' · VLAN ' + t.vlanId)
      + (t.tagged ? ' (802.1Q)' : ''));
    for (const drop of phase.vlanDrops) lines.push(
      '  VLAN-drop: ' + drop.switch + '/' + drop.port + ' ' + drop.reason
      + (drop.vlanId == null ? '' : ' VLAN ' + drop.vlanId));
    if (phase.transmissions.length === 0 && phase.vlanDrops.length === 0) {
      lines.push('  Inga överföringar eller VLAN-droppar');
    }
    return lines.join('\n');
  };
  const macs = data.macTables.flatMap(t => [
    '  ' + t.switchId + (t.vlanId == null ? ' (otaggad)' : ' VLAN ' + t.vlanId) + ':',
    ...Object.entries(t.entries).map(([mac, port]) => '    ' + mac + ' → ' + port),
  ]);
  const resultLines = [
    'DORA-status: ' + data.status,
    data.meaning,
    'Transaktions-ID: ' + data.transactionId + ' · Pool: '
      + data.poolStart + ' – ' + data.poolEnd,
    phaseLines('DISCOVER (klient → server)', data.discover),
    'DISCOVER nådde vald serverport: ' + (data.discover.receivedAtServer ? 'ja' : 'nej'),
    phaseLines('OFFER (server → klient)', data.offer),
    phaseLines('REQUEST (klient → server)', data.request),
    'REQUEST nådde vald serverport: ' + (data.request.receivedAtServer ? 'ja' : 'nej'),
    phaseLines('ACK (server → klient)', data.ack),
    'ACK nådde ursprunglig klientport: ' + (data.ack.receivedAtClient ? 'ja' : 'nej'),
    'Tillfälligt inlärda MAC-tabeller:\n' + (macs.join('\n') || '  Inga'),
  ];
  if (bound) {
    const lease = data.lease;
    resultLines.push('SIMULERAD BOUND-lease: ' + lease.ipv4 + ' / ' + lease.subnetMask
      + '\nKlient: ' + lease.clientNode + '/' + lease.clientPort
      + ' · MAC: ' + lease.clientMac
      + '\nDHCP-server: ' + lease.serverIdentifier
      + ' · Leasetid: ' + lease.leaseSeconds + ' sekunder');
  } else {
    resultLines.push('Ingen simulerad lease bekräftad. ACK mottogs inte på klientporten.');
  }
  resultLines.push('Endast tillfällig DHCP-simuleringssession. Klientens kanoniska IPv4 ändras inte.'
    + ' Ingen fil sparas. Ingen faktisk adresskonfliktskontroll eller lease-förnyelse.');
  output.textContent = resultLines.join('\n\n');
}

function investigationDescription(probe, observation) {
  if (probe === 'advance') {
    return 'VIRTUELL TID: +' + observation.advancedSeconds + ' s'
      + ' · t=' + observation.clockSeconds + ' s · fas ' + observation.phase
      + (observation.expiredLeases.length
        ? '\n  EXPIRED: ' + observation.expiredLeases.map(x => x.ipv4).join(', ')
          + ' · ny DORA krävs'
        : '\n  Ingen ny DHCP-förnyelse skickades automatiskt.');
  }
  if (probe === 'lease') {
    return 'LEASE: ' + observation.status + ' · IPv4 ' + observation.ipv4
      + ' · t=' + observation.clockSeconds + ' s'
      + ' · T1 ' + observation.t1AtSeconds + ' s · T2 '
      + observation.t2AtSeconds + ' s · kvar ' + observation.remainingSeconds + ' s';
  }
  if (probe === 'renew') {
    return 'DHCPREQUEST: ' + observation.status + ' · fas ' + observation.phase
      + '\n  REQUEST nådde vald server: ' + (observation.requestReachedServer ? 'ja' : 'nej')
      + '\n  DHCPACK nådde klienten: ' + (observation.ackReachedClient ? 'ja' : 'nej')
      + '\n  Simulerade kablar: ' + (observation.transmissions.map(t => t.linkId).join(', ') || 'inga')
      + '\n  VLAN-droppar: ' + (observation.vlanDrops.length
        ? observation.vlanDrops.map(d => d.reason + ' vid ' + d.switch + '/' + d.port).join(', ')
        : 'inga observerade')
      + '\n  Lease förnyad: ' + (observation.leaseRenewed ? 'ja' : 'nej');
  }
  if (probe === 'link') {
    return 'LÄNKMÄTNING ' + observation.linkId + ': '
      + observation.observedCarrier + ' · dokumenterat aktiv: '
      + (observation.documentedActive ? 'ja' : 'nej')
      + '\n  ' + observation.endpoints.map(x => x.node + '/' + x.port).join(' ↔ ');
  }
  if (probe === 'port') {
    return 'SWITCHPORT ' + observation.nodeId + '/' + observation.portId
      + ' · administrativ status: ' + observation.observedAdmin
      + ' · operativ länk: ' + observation.observedCarrier;
  }
  if (probe === 'vlan') {
    return 'ACCESS-VLAN ' + observation.nodeId + '/' + observation.portId
      + ' · dokumenterat VLAN ' + observation.documentedVlan
      + ' · observerat VLAN ' + observation.observedVlan;
  }
  return 'Okänd observation';
}

function renderInvestigation() {
  const {id: investigationId, state: investigationState, busy: investigationBusy,
    log: investigationLog, verdict: investigationVerdict, recovery: investigationRecovery,
    error: investigationError, clockEvent: investigationClockEvent} = investigation.getState();
  const active = investigationId !== null;
  const busy = investigationBusy;
  const startValues = doraSessionInput();
  $('investigation-start').disabled = active || busy
    || !startValues[0] || !startValues[1] || !startValues[2] || !startValues[3];
  $('investigation-stop').disabled = !active;
  $('investigation-difficulty').disabled = active || busy;
  const nextClock = investigationState?.nextClockTargetSeconds;
  $('investigation-advance').disabled = !active || busy
    || !investigationState?.canAdvance || !Number.isInteger(nextClock);
  $('investigation-advance').textContent = active && Number.isInteger(nextClock)
    ? 'Flytta klockan till ' + (nextClock === investigationState.t2AtSeconds
      ? 'T2' : 'lease-expiration') + ' (t=' + nextClock + ' s)'
    : 'Flytta till nästa DHCP-gräns (T2 / expiration)';
  const clockResult = $('investigation-clock-result');
  clockResult.classList.remove('ok', 'fail');
  if (investigationClockEvent?.error) {
    clockResult.classList.add('fail');
    clockResult.textContent = 'Tidsändring avvisad: ' + investigationClockEvent.error;
  } else if (investigationClockEvent) {
    clockResult.textContent = investigationDescription('advance', investigationClockEvent);
  } else {
    clockResult.textContent = 'Ingen tid har flyttats fram i denna övning. '
      + 'Klockan kan först flyttas när den aktuella fasens DHCP-försök observerats.';
  }
  const links = project.links.filter(link => link.enabled
    && [link.a, link.b].every(endpoint => {
      const node = project.nodes.find(n => n.id === endpoint.node);
      return node?.ports.some(p => p.id === endpoint.port && p.enabled);
    }));
  const linkSelector = $('investigation-link');
  const previousLink = linkSelector.value;
  linkSelector.replaceChildren(...links.map(link =>
    el('option', {value:link.id}, link.id + ' · '
      + link.a.node + '/' + link.a.port + ' ↔ ' + link.b.node + '/' + link.b.port)));
  if (links.some(l => l.id === previousLink)) linkSelector.value = previousLink;
  const switches = project.nodes.filter(n => n.kind === 'switch')
    .flatMap(n => n.ports.filter(p => p.enabled && links.some(l =>
      (l.a.node === n.id && l.a.port === p.id)
      || (l.b.node === n.id && l.b.port === p.id)))
      .map(p => ({nodeId:n.id, portId:p.id})));
  const portSelector = $('investigation-port');
  const previousPort = portSelector.value;
  portSelector.replaceChildren(...switches.map(p => el('option',
    {value:JSON.stringify([p.nodeId, p.portId])}, p.nodeId + '/' + p.portId)));
  if (switches.some(p => JSON.stringify([p.nodeId, p.portId]) === previousPort)) {
    portSelector.value = previousPort;
  }
  const selectedProbe = $('investigation-probe').value;
  const needsLink = selectedProbe === 'link';
  const needsPort = selectedProbe === 'port' || selectedProbe === 'vlan';
  linkSelector.disabled = !active || busy || !needsLink;
  portSelector.disabled = !active || busy || !needsPort;
  $('investigation-probe').disabled = !active || busy;
  $('investigation-run-probe').disabled = !active || busy
    || (needsLink && !linkSelector.value) || (needsPort && !portSelector.value)
    || Boolean(investigationState?.repaired)
    || (selectedProbe === 'renew' && !investigationState?.leaseActive);
  const observed = new Set(investigationState?.probesPerformed ?? []);
  $('investigation-submit').disabled = !active || busy
    || Boolean(investigationState?.repaired) || Boolean(investigationState?.diagnosed)
    || !investigationState?.canDiagnose;
  $('investigation-diagnosis').disabled = !active || busy || Boolean(investigationState?.diagnosed);
  $('investigation-repair').disabled = !active || busy
    || !investigationState?.diagnosed || Boolean(investigationState?.repaired);
  $('investigation-repair').textContent = investigationState?.requiredRecovery === 'NEW_DORA'
    ? 'Återställ identifierat fel och starta ny DHCP DORA'
    : 'Återställ identifierat fel och testa riktig DHCPACK';
  const status = $('investigation-status');
  status.textContent = investigationBusy
    ? 'Undersökning pågår…'
    : investigationError ? 'Felsökningslabb: ' + investigationError
    : active
      ? 'Aktiv övning · ' + investigationState.clientNode + '/' + investigationState.clientPort
        + ' · simulerad tid ' + investigationState.clockSeconds + ' s'
        + ' · tidigare DHCP-lease ' + investigationState.leaseIpv4
        + ' · fas ' + investigationState.phase
        + ' · ' + investigationState.remainingSeconds + ' s kvar'
        + (investigationState.phase === 'EXPIRED'
          ? ' · lease har upphört, ny DORA krävs' : '')
        + ' · ' + investigationState.observations + ' observation(er)'
      : 'Ingen felsökningsövning. Starta från ett dokumenterat DHCP-nät.';
  const log = $('investigation-observations');
  log.classList.remove('ok', 'fail');
  log.textContent = investigationLog.length
    ? investigationLog.map((x, i) => (i + 1) + '. '
        + (x.error ? 'MÄTNING AVVISAD: ' + x.error :
          investigationDescription(x.probe, x.observation))).join('\n\n')
    : 'Inga observationer. Börja gärna med lease, skicka sedan DHCPREQUEST och undersök de möjliga felvägarna.';
  const verdict = $('investigation-verdict');
  verdict.classList.remove('ok', 'fail');
  if (investigationVerdict?.error) {
    verdict.classList.add('fail');
    verdict.textContent = investigationVerdict.error;
  } else if (investigationVerdict) {
    verdict.classList.add(investigationVerdict.correct ? 'ok' : 'fail');
    verdict.textContent = investigationVerdict.correct
      ? 'DIAGNOS BEKRÄFTAD. Du kan nu återställa den identifierade felkategorin '
        + 'och testa om ett faktiskt DHCPACK når klienten.'
      : 'HYPOTES AVVISAD. ' + investigationVerdict.feedback
        + ' Det verkliga felet avslöjas inte.';
  } else {
    verdict.textContent = 'Pröva en hypotes först efter ett faktiskt DHCPREQUEST och '
      + 'minst två andra olika slags observationer.';
  }
  const recovery = $('investigation-recovery');
  recovery.classList.remove('ok', 'fail');
  if (investigationRecovery?.error) {
    recovery.classList.add('fail');
    recovery.textContent = 'Åtgärd avvisad: ' + investigationRecovery.error;
  } else if (investigationRecovery) {
    recovery.classList.add(investigationRecovery.status === 'RECOVERED' ? 'ok' : 'fail');
    recovery.textContent = 'RESULTAT: ' + investigationRecovery.status
      + '\nVerifierad metod: ' + investigationRecovery.verifiedProtocol
      + (investigationRecovery.verifiedProtocol === 'NEW_DORA'
        ? '\nDHCPDISCOVER nådde servern: ' + (investigationRecovery.discoverReachedServer ? 'ja' : 'nej')
          + '\nDHCPOFFER nådde klienten: ' + (investigationRecovery.offerReachedClient ? 'ja' : 'nej')
        : '')
      + '\nREQUEST nådde servern: ' + (investigationRecovery.requestReachedServer ? 'ja' : 'nej')
      + '\nACK nådde klienten: ' + (investigationRecovery.ackReachedClient ? 'ja' : 'nej')
      + '\nNy simulerad slutsekund: ' + investigationRecovery.expiresAtSeconds
      + (investigationRecovery.status === 'RECOVERED'
        ? '\nBekräftat övningsfel: ' + investigationRecovery.cause
          + ' · identifierad dokumenterad målpunkt: ' + JSON.stringify(investigationRecovery.repair)
        : '\nIngen verifierad DHCP-reparation. Återställning av annan okänd orsak påstås inte.');
  } else {
    recovery.textContent = 'Ingen reparation. Återställning kräver bekräftad diagnos och verklig DHCPACK.';
  }
}

function renderDoraSession() {
  const active = doraSessionId !== null;
  const clients = dhcpPortChoices('client');
  const servers = dhcpPortChoices('server');
  const busy = doraSessionBusy || doraBusy;
  const faultSelector = $('dora-session-fault-link');
  const previousLink = faultSelector.value;
  const originallyActive = project.links.filter(link => {
    if (!link.enabled) return false;
    const a = project.nodes.find(n => n.id === link.a.node);
    const b = project.nodes.find(n => n.id === link.b.node);
    return a && b && a.ports.find(p => p.id === link.a.port && p.enabled)
      && b.ports.find(p => p.id === link.b.port && p.enabled);
  });
  const faultOptions = originallyActive.map(link => ({
    value: link.id,
    label: link.id + ': ' + link.a.node + '/' + link.a.port
      + ' ↔ ' + link.b.node + '/' + link.b.port,
  }));
  faultSelector.replaceChildren(...(faultOptions.length
    ? faultOptions.map(item => el('option', {value: item.value}, item.label))
    : [el('option', {value: ''}, 'Inga aktiva dokumenterade kablar')]));
  if (faultOptions.some(item => item.value === previousLink)) {
    faultSelector.value = previousLink;
  }
  const selectedFaultLink = faultSelector.value;
  const faultedLinks = active ? doraSessionState.faultedLinks : [];
  faultSelector.disabled = !active || busy || !faultOptions.length;
  $('dora-session-fault-break').disabled = !active || busy || !selectedFaultLink
    || faultedLinks.includes(selectedFaultLink);
  $('dora-session-fault-restore').disabled = !active || busy || !selectedFaultLink
    || !faultedLinks.includes(selectedFaultLink);
  const faultOutput = $('dora-session-fault-result');
  faultOutput.classList.remove('ok', 'fail');
  const faultSummary = faultedLinks.length
    ? 'Tillfälligt frånkopplade kablar: ' + faultedLinks.join(', ')
    : 'Inga tillfälliga kabelavbrott.';
  if (!active) {
    faultOutput.textContent = 'Ingen aktiv session. ' + faultSummary;
  } else if (doraFaultEvent?.error) {
    faultOutput.classList.add('fail');
    faultOutput.textContent = 'Kabelåtgärd avvisad: ' + doraFaultEvent.error
      + '\n' + faultSummary;
  } else if (doraFaultEvent) {
    faultOutput.textContent = (doraFaultEvent.disabled
      ? 'Frånkopplad endast i sessionen: '
      : 'Återansluten endast i sessionen: ')
      + doraFaultEvent.linkId
      + '. Switcharnas inlärda MAC-tabeller har tömts.\n'
      + faultSummary + '\nProjektets dokumenterade länkstatus är oförändrad.';
  } else {
    faultOutput.textContent = faultSummary
      + '\nKabelavbrott simuleras endast i denna DHCP-session.';
  }
  const activeSwitchPorts = project.nodes.filter(n => n.kind === 'switch').flatMap(n =>
    n.ports.filter(port => port.enabled && originallyActive.some(link =>
      (link.a.node === n.id && link.a.port === port.id)
      || (link.b.node === n.id && link.b.port === port.id))).map(port => ({
      nodeId: n.id, portId: port.id, port,
    })));
  const portSelector = $('dora-session-port-fault');
  const previousPort = portSelector.value;
  const portOptions = activeSwitchPorts.map(item => ({
    value: JSON.stringify([item.nodeId, item.portId]),
    label: item.nodeId + '/' + item.portId,
  }));
  portSelector.replaceChildren(...(portOptions.length
    ? portOptions.map(item => el('option', {value: item.value}, item.label))
    : [el('option', {value: ''}, 'Inga aktiva dokumenterade switchportar')]));
  if (portOptions.some(x => x.value === previousPort)) portSelector.value = previousPort;
  const selectedPort = portSelector.value;
  const faultedPorts = active ? doraSessionState.faultedPorts : [];
  const portIsDown = selectedPort && faultedPorts.some(p =>
    JSON.stringify([p.nodeId, p.portId]) === selectedPort);
  portSelector.disabled = !active || busy || !portOptions.length;
  $('dora-session-port-down').disabled = !active || busy || !selectedPort || portIsDown;
  $('dora-session-port-up').disabled = !active || busy || !selectedPort || !portIsDown;
  const portSummary = faultedPorts.length
    ? 'Avstängda switchportar i sessionen: '
      + faultedPorts.map(p => p.nodeId + '/' + p.portId).join(', ')
    : 'Inga simulerade avstängda switchportar.';
  const portResult = $('dora-session-port-result');
  portResult.classList.remove('ok', 'fail');
  if (doraPortFaultEvent?.error) {
    portResult.classList.add('fail');
    portResult.textContent = 'Portfel avvisat: ' + doraPortFaultEvent.error + '\n' + portSummary;
  } else {
    portResult.textContent = portSummary
      + '\nSwitchportens operativa status ändras bara i sessionen; källprojektets port är oförändrad.';
  }

  // Never synthesize a VLAN. Only original explicitly documented IDs are selectable.
  const documentedVlans = [...new Set(project.nodes.filter(n => n.kind === 'switch')
    .flatMap(n => n.ports.flatMap(port => port.vlan?.mode === 'access'
      ? [port.vlan.vlan]
      : port.vlan?.mode === 'trunk' ? port.vlan.allowedVlans : [])))].sort((a, b) => a - b);
  const vlanPorts = activeSwitchPorts.filter(item =>
    item.port.vlan?.mode === 'access'
    && originallyActive.some(link => {
      const neighbor = link.a.node === item.nodeId && link.a.port === item.portId
        ? project.nodes.find(n => n.id === link.b.node)
        : link.b.node === item.nodeId && link.b.port === item.portId
          ? project.nodes.find(n => n.id === link.a.node) : null;
      return neighbor && neighbor.kind !== 'switch';
    }));
  const vlanSelector = $('dora-session-vlan-port');
  const previousVlanPort = vlanSelector.value;
  const vlanOptions = vlanPorts.map(item => ({
    value: JSON.stringify([item.nodeId, item.portId]),
    label: item.nodeId + '/' + item.portId + ' · ursprungligt VLAN ' + item.port.vlan.vlan,
    original: item.port.vlan.vlan,
  }));
  vlanSelector.replaceChildren(...(vlanOptions.length
    ? vlanOptions.map(item => el('option', {value: item.value}, item.label))
    : [el('option', {value: ''}, 'Saknar dokumenterad accessport')]));
  if (vlanOptions.some(item => item.value === previousVlanPort)) {
    vlanSelector.value = previousVlanPort;
  }
  const chosenVlanPort = vlanSelector.value;
  const chosenInfo = vlanOptions.find(item => item.value === chosenVlanPort);
  const currentOverride = active ? doraSessionState.faultedAccessVlans.find(v =>
    JSON.stringify([v.nodeId, v.portId]) === chosenVlanPort) : null;
  const vlanTarget = $('dora-session-vlan-target');
  const previousVlanTarget = vlanTarget.value;
  const targetOptions = documentedVlans.filter(v => v !== chosenInfo?.original).map(v => ({
    value: String(v), label: 'VLAN ' + v,
  }));
  vlanTarget.replaceChildren(...(targetOptions.length
    ? targetOptions.map(item => el('option', {value: item.value}, item.label))
    : [el('option', {value: ''}, 'Inget annat dokumenterat VLAN')]));
  if (targetOptions.some(v => v.value === previousVlanTarget)) vlanTarget.value = previousVlanTarget;
  vlanSelector.disabled = !active || busy || !vlanOptions.length;
  vlanTarget.disabled = !active || busy || !targetOptions.length;
  $('dora-session-vlan-set').disabled = !active || busy || !chosenVlanPort
    || !vlanTarget.value || Number(vlanTarget.value) === currentOverride?.faultVlan;
  $('dora-session-vlan-restore').disabled = !active || busy || !currentOverride;
  const vlanFaults = active ? doraSessionState.faultedAccessVlans : [];
  const vlanSummary = vlanFaults.length
    ? 'Tillfälliga access-VLAN-fel: ' + vlanFaults.map(v => v.nodeId + '/' + v.portId
      + ' VLAN ' + v.originalVlan + ' → ' + v.faultVlan).join(', ')
    : 'Inga simulerade VLAN-ändringar.';
  const vlanResult = $('dora-session-vlan-result');
  vlanResult.classList.remove('ok', 'fail');
  if (doraVlanFaultEvent?.error) {
    vlanResult.classList.add('fail');
    vlanResult.textContent = 'VLAN-fel avvisat: ' + doraVlanFaultEvent.error + '\n' + vlanSummary;
  } else {
    vlanResult.textContent = vlanSummary
      + '\nBara uttryckligen dokumenterade VLAN och accessportar tillåts; MAC-inlärning töms vid ändring.';
  }

  $('dora-session-start').disabled = active || busy || !clients.length || !servers.length;
  $('dora-session-run').disabled = !active || busy || !clients.length;
  $('dora-session-reset').disabled = !active || busy;
  $('dora-session-stop').disabled = !active || busy;
  $('dora-session-advance').disabled = !active || busy;
  $('dora-session-advance-seconds').disabled = !active || busy;
  for (const id of ['dora-server', 'dora-pool-start', 'dora-pool-end']) {
    $(id).disabled = active || busy;
  }
  for (const id of ['dora-client', 'dora-transaction-id', 'dora-lease-seconds']) {
    $(id).disabled = busy;
  }
  const selectedClient = $('dora-client').value;
  const chosen = active && selectedClient ? JSON.parse(selectedClient) : [];
  const selectedLease = active ? doraSessionState.leases.find(l =>
    l.clientNode === chosen[0] && l.clientPort === chosen[1]) : null;
  $('dora-session-renew').disabled = !active || busy || !selectedLease
    || selectedLease.renewalPhase === 'BOUND';
  const count = doraSessionState?.leaseCount ?? 0;
  const operations = doraSessionState?.operationCount ?? 0;
  const clock = doraSessionState?.clockSeconds ?? 0;
  $('dora-session-status').textContent = doraSessionBusy
    ? 'DHCP-sessionoperation pågår…'
    : active
      ? 'Aktiv DHCP-session · simulerad tid ' + clock + ' s · ' + operations
        + ' operation(er) · ' + count + ' BOUND-lease(s) · server ' + doraSessionState.serverNode
        + '/' + doraSessionState.serverPort + ' · pool '
        + doraSessionState.poolStart + '–' + doraSessionState.poolEnd
      : 'Ingen aktiv DHCP-session. Starta för att behålla leases mellan klientkörningar.';
  const leaseOutput = $('dora-session-leases');
  leaseOutput.classList.remove('ok', 'fail');
  if (!active) {
    leaseOutput.textContent = 'Ingen aktiv lease-tabell. Inget lagras på disk.';
  } else {
    const leases = doraSessionState.leases;
    leaseOutput.textContent = leases.length
      ? leases.map(l => l.clientNode + '/' + l.clientPort + ' · '
          + l.clientMac + ' → ' + l.ipv4 + ' · ' + l.state
          + ' · kvar ' + l.remainingSeconds + ' s'
          + ' · T1 ' + l.t1AtSeconds + ' s · T2 ' + l.t2AtSeconds + ' s'
          + ' · fas ' + l.renewalPhase + ' · förnyelser ' + l.renewalCount
          + ' · slut vid ' + l.expiresAtSeconds + ' s').join('\n')
      : 'Inga BOUND-leases. Endast mottaget DHCPACK kan skapa en post.';
    if (leases.length) leaseOutput.classList.add('ok');
  }
  const clockOutput = $('dora-session-clock-result');
  clockOutput.classList.remove('ok', 'fail');
  if (!active || !doraClockEvent) {
    clockOutput.textContent = active
      ? 'Simulerad tid: ' + clock + ' s. Inga nya expiration-händelser.'
      : 'Ingen aktiv simuleringsklocka.';
  } else if (doraClockEvent.error) {
    clockOutput.classList.add('fail');
    clockOutput.textContent = 'Tidshopp avvisat: ' + doraClockEvent.error;
  } else {
    const expired = doraClockEvent.expiredLeases;
    clockOutput.textContent = 'Flyttade fram ' + doraClockEvent.advancedSeconds
      + ' s till simulerad tid ' + clock + ' s.\n'
      + (expired.length
        ? expired.map(l => 'EXPIRED: ' + l.clientNode + '/' + l.clientPort
          + ' · ' + l.ipv4 + ' · frigjord ur simulerad pool').join('\n')
        : 'Inga leases har gått ut i detta tidssteg.');
  }
  const renewalOutput = $('dora-session-renew-result');
  renewalOutput.classList.remove('ok', 'fail');
  if (!active || !doraRenewalTrace) {
    renewalOutput.textContent = active
      ? selectedLease
        ? 'Vald lease ' + selectedLease.ipv4 + ' · fas ' + selectedLease.renewalPhase
          + ' · T1 ' + selectedLease.t1AtSeconds + ' s · T2 '
          + selectedLease.t2AtSeconds + ' s. Förnyelse sker endast efter knapptryckning.'
        : 'Välj en klient med aktiv BOUND-lease för T1/T2-förnyelse.'
      : 'Ingen DHCP-förnyelse har begärts.';
  } else if (doraRenewalTrace.error) {
    renewalOutput.classList.add('fail');
    renewalOutput.textContent = 'DHCP-förnyelse avvisad: ' + doraRenewalTrace.error
      + '\nIngen lease förlängdes.';
  } else {
    const renewal = doraRenewalTrace;
    const approved = renewal.leaseRenewed === true && renewal.status === 'ACK_RECEIVED';
    renewalOutput.classList.add(approved ? 'ok' : 'fail');
    const wires = name => {
      const phase = renewal[name];
      return name.toUpperCase() + ': ' + phase.transmissions.length + ' överföringar\n'
        + phase.transmissions.map(t => '  ' + t.linkId + ': '
            + t.from.node + '/' + t.from.port + ' → ' + t.to.node + '/' + t.to.port
            + (t.vlanId == null ? '' : ' · VLAN ' + t.vlanId)).join('\n')
        + phase.vlanDrops.map(d => '\n  VLAN-drop: ' + d.reason).join('');
    };
    renewalOutput.textContent = [
      'DHCP-förnyelse: ' + renewal.status + ' · ' + renewal.phase,
      renewal.meaning,
      'DHCPREQUEST destination: ' + renewal.request.ipDestination
        + ' · MAC: ' + renewal.request.ethernetDestination,
      wires('request'),
      'REQUEST nådde server: ' + (renewal.request.receivedAtServer ? 'ja' : 'nej'),
      wires('ack'),
      'ACK nådde klient: ' + (renewal.ack.receivedAtClient ? 'ja' : 'nej'),
      approved
        ? 'FÖRNYAD BOUND-lease: ' + renewal.lease.ipv4
          + ' · ny sluttid ' + renewal.lease.expiresAtSeconds + ' s'
        : 'Ingen förnyelse. Ursprunglig lease och sluttid gäller oförändrade.',
    ].join('\n\n');
  }
  const output = $('dora-session-result');
  output.classList.remove('ok', 'fail');
  if (!doraSessionTrace) {
    output.textContent = active
      ? 'Sessionen är aktiv. Välj en klient och klicka Tilldela vald klient.'
      : 'Inga sessionoperationer har körts.';
    return;
  }
  if (doraSessionTrace.error) {
    output.classList.add('fail');
    output.textContent = 'DHCP-session avvisad: ' + doraSessionTrace.error
      + '\nTidigare bekräftade leases påverkas inte.';
    return;
  }
  const r = doraSessionTrace;
  const successful = r.status === 'ACK_RECEIVED' && r.leaseCommitted === true
    && r.lease?.state === 'BOUND';
  output.classList.add(successful ? 'ok' : 'fail');
  const phases = ['discover', 'offer', 'request', 'ack'].map(name => {
    const phase = r[name];
    const transmissions = phase.transmissions.map(t =>
      '  ' + t.linkId + ': ' + t.from.node + '/' + t.from.port
      + ' → ' + t.to.node + '/' + t.to.port
      + (t.vlanId == null ? '' : ' · VLAN ' + t.vlanId));
    const drops = phase.vlanDrops.map(d =>
      '  VLAN-drop: ' + d.switch + '/' + d.port + ' ' + d.reason);
    return name.toUpperCase() + ': ' + phase.transmissions.length
      + ' överföringar\n' + [...transmissions, ...drops].join('\n');
  });
  output.textContent = [
    'DORA-status: ' + r.status + ' · transaktions-ID ' + r.transactionId,
    r.meaning,
    ...phases,
    'REQUEST nådde server: ' + (r.request.receivedAtServer ? 'ja' : 'nej'),
    'ACK nådde klient: ' + (r.ack.receivedAtClient ? 'ja' : 'nej'),
    successful
      ? 'SIMULERAD BOUND-lease: ' + r.lease.ipv4 + ' · '
        + r.lease.clientNode + '/' + r.lease.clientPort
      : 'Ingen ny lease tilldelades.',
    'Endast processlokal simuleringssession; dokumenterad IPv4 och sparade projekt är oförändrade.',
  ].join('\n\n');
}

function renderSessionDiagnostics() {
  const field = $('session-source');
  const previous = field.value;
  const sources = project.nodes.filter(n => n.kind !== 'switch')
    .flatMap(n => n.ports.map(p => ({
      value: JSON.stringify([n.id, p.id]),
      label: `${n.label} / ${p.name} (${n.id}/${p.id})`,
    })));
  field.replaceChildren(...sources.map(s => el('option', {value:s.value}, s.label)));
  if (sources.some(s => s.value === previous)) field.value = previous;

  const active = sessionId !== null;
  $('session-start').disabled = active || sessionBusy || sources.length === 0;
  $('session-reset').disabled = !active || sessionBusy;
  $('session-stop').disabled = !active || sessionBusy;
  $('session-arp').disabled = !active || sessionBusy || sources.length === 0;
  $('session-ethernet').disabled = !active || sessionBusy || sources.length === 0;
  $('session-status').textContent = sessionBusy ? 'Kör sessionoperation…' :
    active ? `Aktiv session · ${sessionOperationCount} operation(er) · tillfälligt arbetsminne` :
    'Ingen aktiv session. Ändrad topologi, port eller projekt avslutar sessionen.';

  const output = $('session-result');
  output.classList.remove('ok', 'fail');
  if (!sessionDiagnostic) {
    output.textContent = active
      ? 'Sessionen är aktiv. Inga operationer utförda sedan senaste nollställning.'
      : 'Starta en session. Ingen ARP- eller Ethernetram skickas automatiskt.';
    return;
  }
  if (sessionDiagnostic.error) {
    output.classList.add('fail');
    output.textContent = `Sessionoperation avvisad: ${sessionDiagnostic.error}\nIngen ny lyckad kommunikation är bevisad.`;
    return;
  }
  const {data, sourceNode, sourcePort, target} = sessionDiagnostic;
  const r = data.result;
  const arp = data.operation === 'arp';
  if (r.status === 'NO_REPLY' || r.status === 'NO_ACTIVE_LINK' || r.status === 'UNKNOWN')
    output.classList.add('fail');
  else output.classList.add('ok');
  const transmissions = arp
    ? [...r.requestTransmissions, ...r.replyTransmissions]
    : r.transmissions;
  const drops = arp
    ? [...(r.requestVlanDrops || []), ...(r.replyVlanDrops || [])]
    : (r.vlanDrops || []);
  const switchTables = data.macTables.flatMap(t => [
    `  ${t.switchId}${t.vlanId == null ? ' (utan VLAN)' : ` VLAN ${t.vlanId}`}:`,
    ...Object.entries(t.entries).map(([mac, port]) => `    ${mac} → ${port}`),
  ]);
  const arpEntries = Object.entries(data.arpTable)
    .map(([ip, mac]) => `  ${ip} → ${mac}`);
  const wireLines = transmissions.map(t =>
    `  ${t.linkId}: ${t.from.node}/${t.from.port} → ${t.to.node}/${t.to.port}`
    + (t.vlanId == null ? '' : ` · VLAN ${t.vlanId}${t.tagged ? ' (taggad)' : ' (otaggad)'}`));
  const dropLines = drops.map(d => `  ${d.switch}/${d.port}: ${d.reason} VLAN ${d.vlanId ?? 'otaggad'}`);
  output.textContent = [
    `Operation ${data.operationCount}: ${arp ? 'ARP' : 'Ethernet II'} ${sourceNode}/${sourcePort} → ${target}`,
    `Status: ${r.status}`,
    r.meaning,
    `Faktiska överföringar: ${transmissions.length}\n${wireLines.join('\n') || '  Inga'}`,
    `VLAN-droppar:\n${dropLines.join('\n') || '  Inga observerade'}`,
    `Inlärda MAC-tabeller:\n${switchTables.join('\n') || '  Inga inlärda poster'}`,
    `ARP-cache på vald källport:\n${arpEntries.join('\n') || '  Tom'}`,
    arp ? 'ARP-upplösning är inte IP-reachability eller ping.' :
      'Ethernet II använder ett opakt test-EtherType 0x88B5. Ankomst bevisar inte att en NIC accepterar ramen.',
  ].join('\n\n');
}

function renderRouteLookup() {
  const selector = $('route-source');
  const previous = selector.value;
  const nodes = project.nodes.filter(node => node.kind !== 'switch');
  selector.replaceChildren(...nodes.map(node =>
    el('option', {value:node.id}, `${node.label} (${node.id})`)));
  if (nodes.some(n => n.id === previous)) selector.value = previous;
  $('run-route-lookup').disabled = !nodes.length;

  const output = $('route-result');
  const presentation = presentRoute(routeLookup);
  output.classList.toggle('ok', presentation.status === 'ok');
  output.classList.toggle('fail', presentation.status === 'fail');
  output.textContent = presentation.text;
}

function icmpInvestigationDescription(item) {
  if (item.error) return 'MÄTNING AVVISAD: ' + item.error;
  const o = item.observation;
  if (item.probe === 'address') {
    return 'IP/KLient: dokumenterad ' + o.documentedIpv4
      + ' · gränssnitt ' + (o.interfaceEnabled ? 'aktiverat' : 'avstängt')
      + '\nDHCP-ursprung: ' + o.origin + ' · kontroll: ' + o.dhcpStatus
      + '\n' + o.reason;
  }
  if (item.probe === 'route') {
    const formatStatic = (id, destination, nextHop, outPort) =>
      id + ' · ' + destination + ' via ' + nextHop + ' ut ' + outPort;
    const documented = o.documentedStaticRoutes.map(r =>
      formatStatic(r.id, r.destination, r.nextHop, r.outPort));
    const simulated = o.routes.filter(r => r.type === 'STATIC').map(r =>
      formatStatic(r.routeId, r.destination, r.nextHop, r.outInterface.port));
    return 'ROUTING (' + o.sourceNode + ' → ' + o.destinationIpv4 + '): ' + o.status
      + '\nVald route: ' + (o.selectedRoute
        ? o.selectedRoute.destination + ' via '
          + (o.selectedRoute.nextHop ?? 'CONNECTED')
          + ' ut ' + o.selectedRoute.outInterface.port : 'ingen entydig matchning')
      + '\nDokumenterade statiska routes: '
      + (documented.join(' | ') || 'inga')
      + '\nSimulerade aktiva statiska routes: '
      + (simulated.join(' | ') || 'inga')
      + '\nEn route-matchning bevisar inte ARP-svar eller ping.';
  }
  if (item.probe === 'ping') {
    const steps = [...o.requestSteps.map(step => 'UT'),
                   ...o.replySteps.map(step => 'RETUR')];
    const hops = [...o.requestSteps.map(step => ({direction:'UT', ...step})),
                  ...o.replySteps.map(step => ({direction:'RETUR', ...step}))];
    return 'ICMP: ' + o.status + ' · giltig Echo Reply: ' + (o.replyMatched ? 'ja' : 'nej')
      + '\nRequest: ' + o.requestStatus + ' · Reply: ' + (o.replyStatus ?? 'ej skickad')
      + '\n' + (hops.map(step => step.direction + ' · ' + step.node
        + ' · route ' + step.route.type + ' ' + step.route.destination
        + ' · ARP ' + step.arpStatus
        + ' · nästa hopp ' + step.nextHopIpv4
        + ' · kablar ' + (step.transmissions.map(t => t.linkId).join(', ') || 'inga')
        + ' · VLAN-drops ' + step.vlanDrops.length).join('\n') || 'Ingen paketväg nådd');
  }
  if (item.probe === 'link') {
    return 'KABEL ' + o.linkId + ': dokumenterat ' + (o.documentedEnabled ? 'UP' : 'DOWN')
      + ' · i aktuell simulering ' + (o.observedEnabled ? 'UP' : 'DOWN')
      + '\n' + o.endpoints.map(p => p.node + '/' + p.port).join(' ↔ ');
  }
  if (item.probe === 'port') {
    return 'PORT ' + o.nodeId + '/' + o.portId
      + ': dokumenterat admin ' + (o.documentedEnabled ? 'UP' : 'DOWN')
      + ' · simulerat admin ' + (o.observedEnabled ? 'UP' : 'DOWN')
      + '\nIPv4/CIDR dokumenterat: ' + (o.documentedIpv4 ?? 'ej konfigurerat')
      + ' · simulerat: ' + (o.observedIpv4 ?? 'ej konfigurerat');
  }
  if (item.probe === 'vlan') {
    return 'SWITCH VLAN ' + o.nodeId + '/' + o.portId
      + '\nDokumenterat: ' + JSON.stringify(o.documentedVlan)
      + '\nSimulerat: ' + JSON.stringify(o.observedVlan);
  }
  return JSON.stringify(o);
}

function renderIcmpInvestigation() {
  const {id: icmpInvestigationId, state: icmpInvestigationState,
    busy: icmpInvestigationBusy, log: icmpInvestigationLog,
    verdict: icmpInvestigationVerdict, recovery: icmpInvestigationRecovery,
    error: icmpInvestigationError} = icmpInvestigation.getState();
  const active = icmpInvestigationId !== null;
  const busy = icmpInvestigationBusy;
  const sourceSelector = $('icmp-investigation-source');
  const previousSource = sourceSelector.value;
  const sources = project.nodes.filter(n => n.kind !== 'switch').flatMap(n =>
    n.ports.filter(p => p.enabled && p.ipv4 !== null && p.mac !== null)
      .map(p => ({value: JSON.stringify([n.id,p.id]),
                  title: n.id + '/' + p.id + ' · ' + p.ipv4})));
  sourceSelector.replaceChildren(...sources.map(x => el('option', {value: x.value}, x.title)));
  if (sources.some(x => x.value === previousSource)) sourceSelector.value = previousSource;
  const linkSelector = $('icmp-investigation-link');
  const previousLink = linkSelector.value;
  const links = project.links;
  linkSelector.replaceChildren(...links.map(link => el('option', {value:link.id},
    link.id + ' · ' + link.a.node + '/' + link.a.port
    + ' ↔ ' + link.b.node + '/' + link.b.port)));
  if (links.some(x => x.id === previousLink)) linkSelector.value = previousLink;
  const routeSelector = $('icmp-investigation-route-node');
  const previousRoute = routeSelector.value;
  const nodes = project.nodes.filter(n => n.kind !== 'switch');
  routeSelector.replaceChildren(...nodes.map(n =>
    el('option', {value:n.id}, n.id + ' · ' + n.kind)));
  if (nodes.some(n => n.id === previousRoute)) routeSelector.value = previousRoute;
  const portSelector = $('icmp-investigation-port');
  const previousPort = portSelector.value;
  const ports = project.nodes.flatMap(n => n.ports.map(p => ({
    value: JSON.stringify([n.id,p.id]), title:n.id + '/' + p.id,
  })));
  portSelector.replaceChildren(...ports.map(p =>
    el('option', {value:p.value}, p.title)));
  if (ports.some(p => p.value === previousPort)) portSelector.value = previousPort;
  const vlanSelector = $('icmp-investigation-vlan');
  const previousVlan = vlanSelector.value;
  const vlans = project.nodes.filter(n => n.kind === 'switch').flatMap(n =>
    n.ports.filter(p => p.vlan !== null).map(p => ({
      value: JSON.stringify([n.id,p.id]), title:n.id + '/' + p.id,
    })));
  vlanSelector.replaceChildren(...vlans.map(v =>
    el('option', {value:v.value}, v.title)));
  if (vlans.some(v => v.value === previousVlan)) vlanSelector.value = previousVlan;

  const kind = $('icmp-investigation-probe').value;
  $('icmp-investigation-source').disabled = active || busy || !sources.length;
  $('icmp-investigation-destination').disabled = active || busy;
  $('icmp-investigation-ttl').disabled = active || busy;
  $('icmp-investigation-probe').disabled = !active || busy;
  $('icmp-investigation-route-node').disabled = !active || busy || kind !== 'route';
  $('icmp-investigation-route-destination').disabled = !active || busy || kind !== 'route';
  $('icmp-investigation-link').disabled = !active || busy || kind !== 'link';
  $('icmp-investigation-port').disabled = !active || busy || kind !== 'port';
  $('icmp-investigation-vlan').disabled = !active || busy || kind !== 'vlan';
  $('icmp-investigation-start').disabled = active || busy || !sourceSelector.value
    || !$('icmp-investigation-destination').value.trim();
  $('icmp-investigation-stop').disabled = !active;
  $('icmp-investigation-measure').disabled = !active || busy || icmpInvestigationState?.repaired
    || (kind === 'link' && !linkSelector.value)
    || (kind === 'port' && !portSelector.value)
    || (kind === 'vlan' && !vlanSelector.value)
    || (kind === 'route' && !routeSelector.value);
  $('icmp-investigation-diagnosis').disabled = !active || busy
    || Boolean(icmpInvestigationState?.diagnosed);
  $('icmp-investigation-diagnose').disabled = !active || busy
    || Boolean(icmpInvestigationState?.diagnosed)
    || Boolean(icmpInvestigationState?.repaired)
    || !icmpInvestigationState?.canDiagnose;
  $('icmp-investigation-repair').disabled = !active || busy
    || !icmpInvestigationState?.diagnosed || Boolean(icmpInvestigationState?.repaired)
    || !icmpInvestigationVerdict?.correct;

  $('icmp-investigation-status').textContent = busy
    ? 'ICMP-felsökning pågår…'
    : icmpInvestigationError ? 'ICMP-labb: ' + icmpInvestigationError
    : active
      ? 'Aktiv dold övning · ' + icmpInvestigationState.sourceNode
        + '/' + icmpInvestigationState.sourcePort
        + ' → ' + icmpInvestigationState.destinationIpv4
        + ' · ' + icmpInvestigationState.observations + ' mätningar'
        + ' · DHCP-ursprung: ' + icmpInvestigationState.dhcpCheck
      : 'Ingen ICMP-övning startad. En fungerande ICMP-baslinje krävs.';
  const observations = $('icmp-investigation-observations');
  observations.textContent = icmpInvestigationLog.length
    ? icmpInvestigationLog.map((x, i) =>
      (i + 1) + '. ' + icmpInvestigationDescription(x)).join('\n\n')
    : 'Börja med IP-uppgifter. Skicka sedan verklig ICMP och kontrollera routingtabeller '
      + 'samt länk, port/IPv4 och VLAN för att utesluta fel. DHCP-ursprung är okänt i modellen.';
  const verdict = $('icmp-investigation-verdict');
  verdict.classList.remove('ok', 'fail');
  if (icmpInvestigationVerdict?.error) {
    verdict.classList.add('fail');
    verdict.textContent = 'Diagnos avvisad: ' + icmpInvestigationVerdict.error;
  } else if (icmpInvestigationVerdict) {
    verdict.classList.add(icmpInvestigationVerdict.correct ? 'ok' : 'fail');
    verdict.textContent = icmpInvestigationVerdict.correct
      ? 'DIAGNOS BEKRÄFTAD. Återställ och verifiera en faktisk tur-och-retur Echo Reply.'
      : 'HYPOTES AVVISAD. Felkategorin avslöjas inte; kontrollera flera mätningar.';
  } else {
    verdict.textContent = 'Diagnosen kräver en verklig ICMP-mätning, route lookup '
      + 'och minst en annan oberoende kontroll.';
  }
  const recovery = $('icmp-investigation-recovery');
  recovery.classList.remove('ok', 'fail');
  if (icmpInvestigationRecovery?.error) {
    recovery.classList.add('fail');
    recovery.textContent = 'Reparation avvisad: ' + icmpInvestigationRecovery.error;
  } else if (icmpInvestigationRecovery) {
    recovery.classList.add(icmpInvestigationRecovery.status === 'RECOVERED' ? 'ok' : 'fail');
    recovery.textContent = 'RESULTAT: ' + icmpInvestigationRecovery.status
      + '\nFöre: ' + icmpInvestigationRecovery.failedEchoStatus
      + '\nEfter återställning: ' + icmpInvestigationRecovery.restoredEchoStatus
      + '\nGiltigt ICMP Echo Reply: ' + (icmpInvestigationRecovery.replyMatched ? 'ja' : 'nej')
      + (icmpInvestigationRecovery.status === 'RECOVERED'
        ? '\n\nFELSÖKNINGSRAPPORT'
          + '\nSymptom: ' + icmpInvestigationRecovery.report.symptom
          + '\nRotorsak: ' + icmpInvestigationRecovery.report.rootCause
          + '\nTeknisk evidens: ' + icmpInvestigationRecovery.report.evidence
          + '\nÅtgärd: ' + icmpInvestigationRecovery.report.action
          + '\nVerifiering: ' + icmpInvestigationRecovery.report.verification
        : '\nReparationen är inte verifierad; inga positiva slutsatser får dras.');
  } else {
    recovery.textContent = 'Ingen reparation eller tvåvägskommunikation har verifierats.';
  }
}

function renderTroubleshooting() {
  const sourceSelect = $('trouble-source');
  const previousSource = sourceSelect.value;
  const sources = project.nodes.filter(n => n.kind !== 'switch')
    .flatMap(n => n.ports.map(p => ({
      value:JSON.stringify([n.id,p.id]),
      label:`${n.label} / ${p.name} (${n.id}/${p.id})`,
    })));
  sourceSelect.replaceChildren(...sources.map(i => el('option',{value:i.value},i.label)));
  if (sources.some(i => i.value === previousSource)) sourceSelect.value = previousSource;

  const linkSelect = $('trouble-link');
  const previousLink = linkSelect.value;
  const links = project.links.filter(l => l.enabled);
  linkSelect.replaceChildren(...links.map(l => el('option',{value:l.id},
    `${l.id} (${l.a.node}/${l.a.port} ↔ ${l.b.node}/${l.b.port})`)));
  if (links.some(l => l.id === previousLink)) linkSelect.value = previousLink;
  const type = $('trouble-type').value;
  const ports = project.nodes.flatMap(n => n.ports.filter(p => p.enabled).map(p => ({
    value:JSON.stringify([n.id,p.id]),
    label:n.label + ' / ' + p.name + ' (' + n.id + '/' + p.id + ')',
  })));
  const portSelect = $('trouble-port');
  const previousPort = portSelect.value;
  portSelect.replaceChildren(...ports.map(p => el('option',{value:p.value},p.label)));
  if (ports.some(p => p.value === previousPort)) portSelect.value = previousPort;

  const vlanMode = type === 'TRUNK_VLAN_BLOCKED' ? 'trunk' : 'access';
  const vlanPorts = project.nodes.filter(n => n.kind === 'switch')
    .flatMap(n => n.ports.filter(p => p.enabled && p.vlan?.mode === vlanMode &&
      (vlanMode !== 'trunk' || p.vlan.allowedVlans.length > 1)).map(p => ({
      value:JSON.stringify([n.id,p.id]),
      label:n.label + ' / ' + p.name + ' (' + n.id + '/' + p.id + ')',
    })));
  const vlanSelect = $('trouble-vlan-port');
  const previousVlan = vlanSelect.value;
  vlanSelect.replaceChildren(...vlanPorts.map(p => el('option',{value:p.value},p.label)));
  if (vlanPorts.some(p => p.value === previousVlan)) vlanSelect.value = previousVlan;

  const ipv4Select = $('trouble-ipv4-port');
  const previousIpv4 = ipv4Select.value;
  const ipv4Ports = project.nodes.filter(n => n.kind !== 'switch')
    .flatMap(n => n.ports.filter(p => p.enabled && p.ipv4).map(p => ({
      value:JSON.stringify([n.id,p.id]),
      label:n.label + ' / ' + p.name + ' (' + p.ipv4 + ')',
    })));
  ipv4Select.replaceChildren(...ipv4Ports.map(p => el('option',{value:p.value},p.label)));
  if (ipv4Ports.some(p => p.value === previousIpv4)) ipv4Select.value = previousIpv4;

  const routeSelect = $('trouble-route');
  const previousRoute = routeSelect.value;
  const routes = project.nodes.filter(n => n.kind !== 'switch')
    .flatMap(n => (n.staticRoutes || []).map(route => ({
      value:JSON.stringify([n.id,route.id]),
      label:n.label + ' / ' + route.id + ' (' + route.destination
        + ' via ' + route.nextHop + ')',
    })));
  routeSelect.replaceChildren(...routes.map(r => el('option',{value:r.value},r.label)));
  if (routes.some(r => r.value === previousRoute)) routeSelect.value = previousRoute;

  $('trouble-link-fields').hidden = type !== 'LINK_DISABLED';
  $('trouble-port-fields').hidden = type !== 'PORT_DISABLED';
  $('trouble-vlan-fields').hidden = !['ACCESS_VLAN_CHANGED','TRUNK_VLAN_BLOCKED'].includes(type);
  $('trouble-ipv4-fields').hidden = type !== 'IPV4_PREFIX_CHANGED';
  $('trouble-route-fields').hidden = !['STATIC_ROUTE_REMOVED','STATIC_NEXT_HOP_CHANGED'].includes(type);
  $('trouble-next-hop-fields').hidden = type !== 'STATIC_NEXT_HOP_CHANGED';
  $('run-troubleshoot').disabled = !sources.length ||
    !(type === 'LINK_DISABLED' ? links.length :
      type === 'PORT_DISABLED' ? ports.length :
      ['ACCESS_VLAN_CHANGED','TRUNK_VLAN_BLOCKED'].includes(type) ? vlanPorts.length :
      type === 'IPV4_PREFIX_CHANGED' ? ipv4Ports.length : routes.length);

  const output = $('trouble-result');
  output.classList.remove('ok','fail');
  if (!troubleDiagnostic) {
    output.textContent = 'Inga jämförda ICMP Echo-spår. Resultatet är endast en förhandsvisning; inget projekt ändras.';
    return;
  }
  if (troubleDiagnostic.error) {
    output.classList.add('fail');
    output.textContent = `Felsökningsjämförelse avvisad: ${troubleDiagnostic.error}`;
    return;
  }
  const d = troubleDiagnostic;
  if (d.status === 'FAULT_CONFIRMED') output.classList.add('ok');
  else output.classList.add('fail');
  const detail = (label, trial, wires) => {
    const request = trial.request?.status || 'INGEN';
    const reply = trial.reply?.status || 'INGET';
    const ars = trial.request?.steps?.map(step=>step.arp.status).join(', ') || 'inga';
    return `${label}: ${trial.status} · request ${request}, reply ${reply}, ARP ${ars}`
      + `\n  Verkligt observerade kablar: ${wires.join(', ') || 'inga'}`;
  };
  const faultKind = d.fault.type;
  const target = d.fault.linkId || (d.fault.nodeId + '/' +
    (d.fault.routeId || d.fault.portId));
  const faultState = faultKind === 'ACCESS_VLAN_CHANGED'
    ? ('access ' + d.fault.fromVlan + ' → ' + d.fault.toVlan)
    : faultKind === 'TRUNK_VLAN_BLOCKED' ? ('trunk: blockera VLAN ' + d.fault.blockedVlan)
    : faultKind === 'IPV4_PREFIX_CHANGED' ? (d.fault.fromIpv4 + ' → ' + d.fault.toIpv4)
    : faultKind === 'STATIC_ROUTE_REMOVED' ? ('ta bort ' + d.fault.removedRoute.destination)
    : faultKind === 'STATIC_NEXT_HOP_CHANGED'
      ? (d.fault.fromNextHop + ' → ' + d.fault.toNextHop)
      : 'enabled true → false';
  const faultLabel = faultKind === 'LINK_DISABLED' ? 'Kabel avstängd'
    : faultKind === 'PORT_DISABLED' ? 'Port avstängd'
    : faultKind === 'IPV4_PREFIX_CHANGED' ? 'IPv4-prefix fel'
    : faultKind === 'STATIC_ROUTE_REMOVED' ? 'Statisk route borttagen'
    : faultKind === 'STATIC_NEXT_HOP_CHANGED' ? 'Fel next-hop' : 'VLAN-fel';
  const restoredLabel = faultKind === 'LINK_DISABLED' ? 'Återställd kabel'
    : faultKind === 'PORT_DISABLED' ? 'Återställd port'
    : faultKind === 'IPV4_PREFIX_CHANGED' ? 'Återställt IPv4-prefix'
    : ['STATIC_ROUTE_REMOVED','STATIC_NEXT_HOP_CHANGED'].includes(faultKind)
      ? 'Återställd route' : 'Återställt VLAN';
  const repair = d.repair.action === 'RESTORE_VLAN_CONFIG'
    ? ('återställ ' + target + ' till ' + JSON.stringify(d.repair.expectedVlan))
    : d.repair.action === 'RESTORE_IPV4' ? ('återställ ' + target + ' till ' + d.repair.expectedIpv4)
    : d.repair.action === 'RESTORE_STATIC_ROUTE'
      ? ('återställ ' + target + ' med ' + JSON.stringify(d.repair.expectedRoute))
    : d.repair.action === 'RESTORE_NEXT_HOP'
      ? ('återställ ' + target + ' till next-hop ' + d.repair.expectedNextHop)
    : ('återaktivera ' + target);
  output.textContent = [
    'Felsökningsstatus: ' + d.status,
    d.meaning,
    'Avgränsat fel: ' + target + ' · ' + faultState + ' (endast temporär kopia)',
    detail('Referens',d.baseline,d.observedLinkIds.baseline),
    detail(faultLabel,d.faulted,d.observedLinkIds.faulted),
    detail(restoredLabel,d.restored,d.observedLinkIds.restored),
    'Felkedja verifierad: ' + (d.verifiedFault ? 'JA' : 'NEJ'),
    'Återställning efter fel verifierad: ' + (d.verifiedRecovery ? 'JA' : 'NEJ'),
    'Föreslagen åtgärd: ' + repair + '.',
    'Åtgärden tillämpas INTE på arbetsytan. Ingen autosave, uppmätt RTT eller extern trafikkontroll.',
  ].join('\n\n');
}

function renderPing() {
  const selector = $('ping-source');
  const previous = selector.value;
  const sources = project.nodes.filter(n => n.kind !== 'switch')
    .flatMap(n => n.ports.map(p => ({
      value:JSON.stringify([n.id,p.id]),
      label:`${n.label} / ${p.name} (${n.id}/${p.id})`,
    })));
  selector.replaceChildren(...sources.map(s => el('option',{value:s.value},s.label)));
  if (sources.some(s => s.value === previous)) selector.value = previous;
  $('run-ping').disabled = !sources.length;

  const output = $('ping-result');
  const presentation = presentPing(pingDiagnostic);
  output.classList.toggle('ok', presentation.status === 'ok');
  output.classList.toggle('fail', presentation.status === 'fail');
  output.textContent = presentation.text;
}

function renderIPv4Trace() {
  const select = $('ipv4-source');
  const previous = select.value;
  const sources = project.nodes.filter(n => n.kind !== 'switch')
    .flatMap(n => n.ports.map(p => ({
      value:JSON.stringify([n.id,p.id]),
      label:`${n.label} / ${p.name} (${n.id}/${p.id})`,
    })));
  select.replaceChildren(...sources.map(i => el('option',{value:i.value},i.label)));
  if (sources.some(i => i.value === previous)) select.value = previous;
  $('run-ipv4-trace').disabled = !sources.length;

  const output = $('ipv4-result');
  const presentation = presentIPv4(ipv4Diagnostic);
  output.classList.toggle('ok', presentation.status === 'ok');
  output.classList.toggle('fail', presentation.status === 'fail');
  output.textContent = presentation.text;
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
      if (next === 'switch' && value.staticRoutes?.length) {
        notify('Ta bort statiska routes innan enheten ändras till Layer 2-switch.', true);
        renderInspector(); return;
      }
      if (next === 'switch') delete value.staticRoutes;
      if (next !== 'switch' && value.ports.some(port => port.vlan != null)) {
        notify('Ta bort VLAN-inställningarna innan switchen ändras till en annan typ.', true);
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
          // Legacy documents upgrade in memory on deliberate edit, never on Open.
          attempt.schemaVersion = '1.3';
          const portCopy = attempt.nodes.find(n => n.id === value.id).ports.find(p => p.id === port.id);
          portCopy.mac = next.trim() || null;
          try {
            const normalized = await api('/api/validate', attempt);
            project = normalized.project;
            changed();
          } catch (error) { notify(error.message, true); renderInspector(); }
        }, {dataset:{portMac:port.id},placeholder:'02:00:00:00:00:0A'})),
        value.kind !== 'switch' ? null : field('VLAN (access:10 eller trunk:10,20)', input(
          port.vlan?.mode === 'access' ? `access:${port.vlan.vlan}` :
            port.vlan?.mode === 'trunk' ? `trunk:${port.vlan.allowedVlans.join(',')}` : '',
          async next => {
            const attempt = copy(project);
            const portCopy = attempt.nodes.find(n => n.id === value.id).ports.find(p => p.id === port.id);
            const supplied = next.trim();
            if (supplied) {
              const access = /^access:([0-9]+)$/.exec(supplied);
              const trunk = /^trunk:([0-9]+(?:,[0-9]+)*)$/.exec(supplied);
              if (!access && !trunk) {
                notify('VLAN-format: access:10 eller trunk:10,20. Inget VLAN antas.', true);
                renderInspector(); return;
              }
              portCopy.vlan = access ?
                {mode:'access',vlan:Number(access[1])} :
                {mode:'trunk',allowedVlans:trunk[1].split(',').map(Number)};
            } else {
              delete portCopy.vlan;
            }
            attempt.schemaVersion = '1.3';
            try {
              const normalized = await api('/api/validate', attempt);
              project = normalized.project;
              changed();
            } catch (error) { notify(error.message, true); renderInspector(); }
          }, {dataset:{portVlan:port.id},placeholder:'access:10 eller trunk:10,20'})),
        check('Port aktiverad', port.enabled, enabled => { port.enabled = enabled; changed(); }),
        button('Ta bort port', () => {
          if (value.staticRoutes?.some(route => route.outPort === port.id)) {
            notify('Ta bort statiska routes som använder porten innan porten tas bort.', true);
            return;
          }
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
    if (value.kind !== 'switch') {
      const staticRoutes = value.staticRoutes || [];
      const choices = [{value:'',label:'Välj utgående port'}].concat(
        value.ports.map(p => ({value:p.id, label:`${p.name} (${p.id})${p.enabled ? '' : ' · inaktiv'}`})));
      box.append(heading(`Statiska IPv4-routes (${staticRoutes.length})`));
      box.append(small('Endast explicit next-hop i eget utgående IPv4-subnät. Routingtabell innebär inte paketleverans.'));
      const commitRouteChange = async (routeId, fieldName, newValue) => {
        const attempt = copy(project);
        attempt.schemaVersion = '1.3';
        const route = attempt.nodes.find(n => n.id === value.id)
          .staticRoutes.find(r => r.id === routeId);
        route[fieldName] = newValue;
        try {
          const normalized = await api('/api/validate', attempt);
          project = normalized.project; changed();
        } catch (error) { notify(error.message, true); renderInspector(); }
      };
      for (const route of staticRoutes) {
        box.append(el('div', {className:'port-card', dataset:{routeCard:route.id}},
          el('strong', {}, `Statisk route ${route.id}`),
          field('Destinationsprefix', input(route.destination,
            next => commitRouteChange(route.id,'destination',next.trim()),
            {dataset:{routeDestination:route.id},placeholder:'203.0.113.0/24'})),
          field('Next-hop IPv4', input(route.nextHop,
            next => commitRouteChange(route.id,'nextHop',next.trim()),
            {dataset:{routeNextHop:route.id},placeholder:'192.0.2.1'})),
          field('Utgående port', dropdown(choices, route.outPort,
            next => commitRouteChange(route.id,'outPort',next),
            {dataset:{routeOutPort:route.id}})),
          button('Ta bort statisk route', async () => {
            const attempt = copy(project);
            attempt.schemaVersion = '1.3';
            const node = attempt.nodes.find(n => n.id === value.id);
            node.staticRoutes = node.staticRoutes.filter(r => r.id !== route.id);
            try {
              const normalized = await api('/api/validate', attempt);
              project = normalized.project; changed();
            } catch (error) { notify(error.message, true); renderInspector(); }
          }, 'btn-outline danger', {dataset:{deleteRoute:route.id}})));
      }
      const destination = el('input', {className:'control',id:'new-route-destination',
        placeholder:'203.0.113.0/24',autocomplete:'off'});
      const nextHop = el('input', {className:'control',id:'new-route-next-hop',
        placeholder:'192.0.2.1',autocomplete:'off'});
      const outPort = dropdown(choices, '', () => {}, {id:'new-route-out-port'});
      const addRoute = button('+ Lägg till statisk route', async () => {
        if (!destination.value.trim() || !nextHop.value.trim() || !outPort.value) {
          notify('Ange destinationsprefix, next-hop och välj utgående port uttryckligen.', true);
          return;
        }
        const attempt = copy(project);
        attempt.schemaVersion = '1.3';
        const node = attempt.nodes.find(n => n.id === value.id);
        node.staticRoutes ||= [];
        node.staticRoutes.push({
          id: nextId('route', node.staticRoutes),
          destination: destination.value.trim(),
          nextHop: nextHop.value.trim(),
          outPort: outPort.value,
        });
        try {
          const normalized = await api('/api/validate', attempt);
          project = normalized.project; changed();
        } catch (error) { notify(error.message, true); }
      }, 'btn-soft', {id:'add-static-route'});
      box.append(field('Nytt destinationsprefix', destination),
        field('Next-hop', nextHop),
        field('Utgående port', outPort), addRoute);
    }
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
  canvas.setData(project, selection, pendingPort,
    sessionDiagnostic?.data ? sessionHighlightedLinks :
    arpDiagnostic ? arpHighlightedLinks : highlightedLinks);
  renderInspector();
  updateTraceSelectors();
  renderArpDiagnostics();
  renderDhcpDiagnostics();
  renderDoraDiagnostics();
  renderDoraSession();
  renderInvestigation();
  renderSessionDiagnostics();
  renderRouteLookup();
  renderIPv4Trace();
  renderPing();
  renderTroubleshooting();
  renderIcmpInvestigation();
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
  workspaceRevision += 1;
  project = value;
  delete $('trace-target').dataset.userSelected;
  arpDiagnostic = null; arpHighlightedLinks = [];
  selection = null;
  pendingPort = null;
  filename = 'lab'; savedName = null; savedSha = null;
  savedSnapshot = pristineBlank ? JSON.stringify(project) : null;
  changed(); canvas.fit();
}
async function saveProject() {
  // A server response describes the snapshot actually submitted, not any
  // edits made while the request was in flight. Never replace newer work.
  if (savePending) return;
  savePending = true;
  $('save-project').disabled = true;
  try {
    const request = prepareSave({filename, project, workspaceRevision, editRevision, savedName, savedSha});
    const result = await saveSnapshot(request, error => {
      // Never approve an overwrite using a document/filename that changed
      // after the original Save click, even if the server reports a conflict.
      if (workspaceRevision !== request.workspaceRevision || editRevision !== request.editRevision ||
          filename !== request.filename || JSON.stringify(project) !== request.serializedProject) {
        throw new Error('Arbetsytan ändrades under sparning. Spara igen för att välja aktuell version.');
      }
      return confirm(`Filen ${request.filename}.yadilab har annat innehåll eller finns redan. Skriv över den AKTUELLA versionen på disk?`);
    });
    if (workspaceRevision !== request.workspaceRevision || filename !== request.filename) {
      // Disk Save may have succeeded, but the user has changed documents;
      // never attach the old file's SHA or data to the new workspace.
      notify(`Den tidigare versionen sparades som ${result.filename}.yadilab. Aktuell arbetsyta ändrades inte.`);
      await refreshSavedProjects();
      return;
    }
    if (JSON.stringify(project) === request.serializedProject) {
      project = result.project;
    }
    savedName = result.filename;
    savedSha = result.sha256;
    savedSnapshot = JSON.stringify(result.project);
    render();
    await refreshSavedProjects();
    if (isDirty()) {
      notify(`Sparade tidigare version i ${savedName}.yadilab. Nyare ändringar är fortfarande osparade.`);
    } else {
      notify(`Sparat till lokal fil: ${savedName}.yadilab · ${result.bytes} byte · SHA-256 ${savedSha.slice(0,14)}…`);
    }
  } catch (error) {
    notify(`Kunde inte spara: ${error.message}`, true);
  } finally {
    savePending = false;
    $('save-project').disabled = false;
  }
}
async function refreshSavedProjects() {
  try {
    const list = await listSavedProjects();
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
  const requestedWorkspace = workspaceRevision;
  const requestedEdit = editRevision;
  const requestedFilename = filename;
  const requestedSnapshot = JSON.stringify(project);
  try {
    const loaded = await readSavedProject(slug);
    if (workspaceRevision !== requestedWorkspace || editRevision !== requestedEdit ||
        filename !== requestedFilename || JSON.stringify(project) !== requestedSnapshot ||
        $('saved-projects').value !== slug) {
      notify('Öppningen avbröts: arbetsytan eller projektvalet ändrades under inläsningen.');
      return;
    }
    workspaceRevision += 1;
    editRevision += 1;
    invalidateSimulationSession();
    routeLookup = null;
    ipv4Diagnostic = null;
    pingDiagnostic = null;
    troubleDiagnostic = null;
    project = loaded.project;
    filename = loaded.filename;
    savedName = loaded.filename;
    savedSha = loaded.sha256;
    savedSnapshot = JSON.stringify(project);
    selection = null; pendingPort = null; traceResult = null; highlightedLinks = [];
    arpDiagnostic = null; arpHighlightedLinks = [];
    invalidateDhcpDiagnostics();
    invalidateDoraDiagnostics();
    invalidateDoraSession();
    render(); canvas.fit();
    notify(`Öppnade verklig projektfil: ${loaded.filename}.yadilab · SHA-256 ${loaded.sha256.slice(0,14)}…`);
  } catch (error) { notify(`Kunde inte öppna: ${error.message}`,true); }
}
function transferContext() {
  return {workspaceRevision, editRevision, snapshot: JSON.stringify(project), filename};
}
function transferCurrent(context) {
  return workspaceRevision === context.workspaceRevision && editRevision === context.editRevision &&
    filename === context.filename && JSON.stringify(project) === context.snapshot;
}
function transferStale() {
  notify('Åtgärden avbröts: arbetsytan ändrades under import eller export. Försök igen.', true);
}
async function importProjects(files) {
  if (!files?.length) return;
  const context = transferContext();
  try {
    const kind = importKind(files);
    let projectName;
    if (kind !== 'project') {
      const label = kind === 'csv' ? 'CSV' : kind.toUpperCase();
      projectName = prompt(`Projektnamn för ${label}-importen:`, project.name);
      if (projectName === null) return;
    }
    const prepared = await prepareImport(files, kind, projectName);
    if (!transferCurrent(context)) return transferStale();
    const result = await submitImport(prepared);
    if (!transferCurrent(context)) return transferStale();
    const incoming = result.project;
    if (!confirmDiscard()) return;
    if (!confirm(`Importen innehåller ${incoming.nodes.length} enheter och ${incoming.links.length} uttryckligt deklarerade länkar. Ersätta nuvarande arbetsyta? Ingen fil skrivs automatiskt.`)) return;
    resetProject(incoming);
    notify(`Importerade ${incoming.nodes.length} enheter, ${incoming.links.length} länkar och ${incoming.zones.length} zoner. Inget sparades automatiskt.`);
  } catch (error) {
    if (!transferCurrent(context)) return transferStale();
    notify(`Import avvisad: ${error.message}`, true);
  }
}
function downloadExport({content, type, filename}) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const anchor = el('a', {href: url, download: filename});
  document.body.append(anchor);
  anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
async function exportSpreadsheet(format) {
  const context = transferContext();
  try {
    const result = await prepareSpreadsheetExport(context.snapshot, format);
    if (!transferCurrent(context)) return transferStale();
    downloadExport(result);
    notify('Kalkylbladsexport initierad. Projektet har inte sparats. Webbläsarens faktiska nedladdning är inte verifierad.');
  } catch (error) {
    if (!transferCurrent(context)) return transferStale();
    notify('Kalkylbladsexport avvisad: ' + error.message, true);
  }
}
async function exportProject() {
  const context = transferContext();
  try {
    const result = await prepareProjectExport(context.snapshot);
    if (!transferCurrent(context)) return transferStale();
    downloadExport({...result, filename: `${context.filename}.yadilab`});
    notify('Export/nedladdning initierad. Webbläsarens faktiska skrivning till disk är inte verifierad.');
  } catch (error) {
    if (!transferCurrent(context)) return transferStale();
    notify(`Export avvisad: ${error.message}`, true);
  }
}
function doraSessionInput() {
  return [
    $('dora-client').value, $('dora-server').value,
    $('dora-pool-start').value.trim(), $('dora-pool-end').value.trim(),
    $('dora-transaction-id').value.trim(), $('dora-lease-seconds').value.trim(),
  ];
}
function sessionInteger(value, min, max) {
  return /^[0-9]+$/.test(value) && Number.isSafeInteger(Number(value))
    && Number(value) >= min && Number(value) <= max ? Number(value) : null;
}
function investigationStartInputs() {
  return JSON.stringify([...doraSessionInput(), $('investigation-difficulty').value]);
}
function startInvestigation() {
  const inputs = doraSessionInput();
  const difficulty = $('investigation-difficulty').value;
  const [client, server, poolStart, poolEnd, , rawLease] = inputs;
  const leaseSeconds = sessionInteger(rawLease, 60, 604800);
  if (!client || !server || !poolStart || !poolEnd || leaseSeconds === null) {
    investigation.setInputError('Välj klient, server, explicit pool och giltig leasetid i DHCP-panelen.');
    return;
  }
  const [clientNode, clientPort] = JSON.parse(client);
  const [serverNode, serverPort] = JSON.parse(server);
  void investigation.start({clientNode, clientPort, serverNode, serverPort,
    poolStart, poolEnd, leaseSeconds, difficulty}, investigationStartInputs);
}
function advanceInvestigation() { void investigation.advance(); }
function probeInvestigation() {
  const kind = $('investigation-probe').value;
  let target = {};
  if (kind === 'link') {
    target = {linkId: $('investigation-link').value};
    if (!target.linkId) return;
  } else if (kind === 'port' || kind === 'vlan') {
    if (!$('investigation-port').value) return;
    const [nodeId, portId] = JSON.parse($('investigation-port').value);
    target = {nodeId, portId};
  }
  const readInputs = () => JSON.stringify([
    $('investigation-probe').value, $('investigation-link').value,
    $('investigation-port').value,
  ]);
  void investigation.probe(kind, target, readInputs);
}
function diagnoseInvestigation() {
  const diagnosis = $('investigation-diagnosis').value;
  void investigation.diagnose(diagnosis, () => $('investigation-diagnosis').value);
}
function repairInvestigation() { void investigation.repair(); }
function stopInvestigation() { void investigation.stop(); }

async function startDoraSession() {
  if (doraSessionBusy || doraSessionId !== null || doraBusy) return;
  doraClockEvent = null;
  doraRenewalTrace = null;
  doraFaultEvent = null;
  doraPortFaultEvent = null;
  doraVlanFaultEvent = null;
  const inputs = doraSessionInput();
  const [client, server, poolStart, poolEnd] = inputs;
  if (!client || !server || !poolStart || !poolEnd) {
    doraSessionTrace = {error: 'Välj klient, server och både poolgränserna uttryckligen.'};
    renderDoraSession();
    return;
  }
  const [serverNode, serverPort] = JSON.parse(server);
  const snapshot = JSON.stringify(project);
  const edit = editRevision, workspace = workspaceRevision;
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  doraSessionTrace = null;
  renderDoraSession();
  const stillCurrent = () => generation === doraSessionGeneration
    && edit === editRevision && workspace === workspaceRevision
    && JSON.stringify(project) === snapshot
    && JSON.stringify(doraSessionInput()) === JSON.stringify(inputs);
  try {
    const state = await api('/api/dhcp/session/start', {
      project: JSON.parse(snapshot), serverNode, serverPort, poolStart, poolEnd,
    });
    if (stillCurrent()) {
      doraSessionId = state.sessionId;
      doraSessionState = state;
    } else {
      // Stale Start may have allocated a server session; explicitly release it.
      void api('/api/dhcp/session/stop', {sessionId: state.sessionId}).catch(() => {});
    }
  } catch (error) {
    if (stillCurrent()) doraSessionTrace = {error: error.message};
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraDiagnostics();
      renderDoraSession();
    }
  }
}
async function runDoraSession() {
  if (!doraSessionId || doraSessionBusy) return;
  const inputs = doraSessionInput();
  const [client, , , , rawTransaction, rawLease] = inputs;
  const transactionId = sessionInteger(rawTransaction, 1, 4294967295);
  const leaseSeconds = sessionInteger(rawLease, 60, 604800);
  if (!client || transactionId === null || leaseSeconds === null) {
    doraSessionTrace = {error: 'Välj klient, giltigt transaktions-ID och leasetid 60–604800.'};
    renderDoraSession();
    return;
  }
  const [clientNode, clientPort] = JSON.parse(client);
  const id = doraSessionId;
  const edit = editRevision, workspace = workspaceRevision;
  const snapshot = JSON.stringify(project);
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  doraSessionTrace = null;
  renderDoraSession();
  const stillCurrent = () => generation === doraSessionGeneration
    && doraSessionId === id && edit === editRevision
    && workspace === workspaceRevision
    && JSON.stringify(project) === snapshot
    && JSON.stringify(doraSessionInput()) === JSON.stringify(inputs);
  try {
    const data = await api('/api/dhcp/session/run', {
      sessionId: id, project: JSON.parse(snapshot), clientNode, clientPort,
      transactionId, leaseSeconds,
    });
    if (stillCurrent()) {
      doraSessionState = data;
      doraSessionTrace = data.result;
      doraClockEvent = null;
      doraRenewalTrace = null;
    }
  } catch (error) {
    if (stillCurrent()) doraSessionTrace = {error: error.message};
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraSession();
    }
  }
}
async function setDoraSwitchFault(kind, restore) {
  if (!doraSessionId || doraSessionBusy || doraBusy) return;
  if (kind !== 'port' && kind !== 'vlan') return;
  const selectorId = kind === 'port' ? 'dora-session-port-fault' : 'dora-session-vlan-port';
  const selected = $(selectorId).value;
  if (!selected) return;
  const [nodeId, portId] = JSON.parse(selected);
  const target = kind === 'vlan' ? $('dora-session-vlan-target').value : null;
  if (kind === 'vlan' && !restore && !target) return;
  const parameter = kind === 'port'
    ? {disabled: !restore}
    : {vlanId: restore ? null : Number(target)};
  const id = doraSessionId;
  const snapshot = JSON.stringify(project);
  const edit = editRevision, workspace = workspaceRevision;
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  if (kind === 'port') doraPortFaultEvent = null;
  else doraVlanFaultEvent = null;
  renderDoraSession();
  try {
    const state = await api('/api/dhcp/session/' + (kind === 'port' ? 'port-fault' : 'vlan-fault'), {
      sessionId: id, project: JSON.parse(snapshot), nodeId, portId, ...parameter,
    });
    if (generation === doraSessionGeneration && doraSessionId === id
        && edit === editRevision && workspace === workspaceRevision
        && JSON.stringify(project) === snapshot
        && $(selectorId).value === selected) {
      doraSessionState = state;
      if (kind === 'port') doraPortFaultEvent = {nodeId, portId, ...parameter};
      else doraVlanFaultEvent = {nodeId, portId, ...parameter};
      doraSessionTrace = null;
      doraRenewalTrace = null;
      doraClockEvent = null;
      doraFaultEvent = null;
    }
  } catch (error) {
    if (generation === doraSessionGeneration && doraSessionId === id) {
      if (kind === 'port') doraPortFaultEvent = {error: error.message};
      else doraVlanFaultEvent = {error: error.message};
    }
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraSession();
    }
  }
}

async function setDoraLinkFault(disabled) {
  if (!doraSessionId || doraSessionBusy || doraBusy) return;
  const linkId = $('dora-session-fault-link').value;
  if (!linkId || typeof disabled !== 'boolean') {
    doraFaultEvent = {error: 'Välj en uttryckligt dokumenterad aktiv kabel.'};
    renderDoraSession();
    return;
  }
  const id = doraSessionId;
  const snapshot = JSON.stringify(project);
  const edit = editRevision, workspace = workspaceRevision;
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  doraFaultEvent = null;
  renderDoraSession();
  try {
    const state = await api('/api/dhcp/session/link-fault', {
      sessionId: id, project: JSON.parse(snapshot), linkId, disabled,
    });
    if (generation === doraSessionGeneration && doraSessionId === id
        && edit === editRevision && workspace === workspaceRevision
        && JSON.stringify(project) === snapshot
        && $('dora-session-fault-link').value === linkId) {
      doraSessionState = state;
      doraFaultEvent = {linkId, disabled};
      doraSessionTrace = null;
      doraRenewalTrace = null;
      doraClockEvent = null;
    }
  } catch (error) {
    if (generation === doraSessionGeneration && doraSessionId === id) {
      doraFaultEvent = {error: error.message};
    }
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraSession();
    }
  }
}

async function renewDoraSession() {
  if (!doraSessionId || doraSessionBusy) return;
  const inputs = doraSessionInput();
  const [client, , , , rawTransaction] = inputs;
  const transactionId = sessionInteger(rawTransaction, 1, 4294967295);
  if (!client || transactionId === null) {
    doraRenewalTrace = {error: 'Välj en giltig klient och ett transaktions-ID 1–4294967295.'};
    renderDoraSession();
    return;
  }
  const [clientNode, clientPort] = JSON.parse(client);
  const id = doraSessionId;
  const snapshot = JSON.stringify(project);
  const edit = editRevision, workspace = workspaceRevision;
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  doraRenewalTrace = null;
  renderDoraSession();
  const stillCurrent = () => generation === doraSessionGeneration
    && doraSessionId === id && edit === editRevision
    && workspace === workspaceRevision
    && JSON.stringify(project) === snapshot
    && JSON.stringify(doraSessionInput()) === JSON.stringify(inputs);
  try {
    const data = await api('/api/dhcp/session/renew', {
      sessionId: id, project: JSON.parse(snapshot),
      clientNode, clientPort, transactionId,
    });
    if (stillCurrent()) {
      doraSessionState = data;
      doraRenewalTrace = data.result;
      doraSessionTrace = null;
      doraClockEvent = null;
    }
  } catch (error) {
    if (stillCurrent()) doraRenewalTrace = {error: error.message};
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraSession();
    }
  }
}

async function advanceDoraSession() {
  if (!doraSessionId || doraSessionBusy) return;
  const seconds = sessionInteger($('dora-session-advance-seconds').value.trim(), 1, 604800);
  if (seconds === null) {
    doraClockEvent = {error: 'Ange ett heltal från 1 till 604800 sekunder.'};
    renderDoraSession();
    return;
  }
  const id = doraSessionId;
  const snapshot = JSON.stringify(project);
  const edit = editRevision, workspace = workspaceRevision;
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  renderDoraSession();
  try {
    const state = await api('/api/dhcp/session/advance', {
      sessionId: id, project: JSON.parse(snapshot), seconds,
    });
    if (generation === doraSessionGeneration && doraSessionId === id
        && edit === editRevision && workspace === workspaceRevision
        && JSON.stringify(project) === snapshot) {
      doraSessionState = state;
      doraSessionTrace = null;
      doraClockEvent = state;
      doraRenewalTrace = null;
    }
  } catch (error) {
    if (generation === doraSessionGeneration && doraSessionId === id) {
      doraClockEvent = {error: error.message};
    }
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraSession();
    }
  }
}

async function resetDoraSession() {
  if (!doraSessionId || doraSessionBusy) return;
  const id = doraSessionId;
  const snapshot = JSON.stringify(project);
  const edit = editRevision, workspace = workspaceRevision;
  const generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  renderDoraSession();
  try {
    const state = await api('/api/dhcp/session/reset', {
      sessionId: id, project: JSON.parse(snapshot),
    });
    if (generation === doraSessionGeneration && doraSessionId === id
        && edit === editRevision && workspace === workspaceRevision
        && JSON.stringify(project) === snapshot) {
      doraSessionState = state;
      doraSessionTrace = null;
      doraClockEvent = null;
      doraRenewalTrace = null;
      doraFaultEvent = null;
      doraPortFaultEvent = null;
      doraVlanFaultEvent = null;
    }
  } catch (error) {
    if (generation === doraSessionGeneration && doraSessionId === id) {
      doraSessionTrace = {error: error.message};
    }
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraSession();
    }
  }
}
async function stopDoraSession() {
  if (!doraSessionId || doraSessionBusy) return;
  const id = doraSessionId, generation = ++doraSessionGeneration;
  doraSessionBusy = true;
  renderDoraSession();
  try {
    await api('/api/dhcp/session/stop', {sessionId: id});
    if (generation === doraSessionGeneration) {
      doraSessionId = null;
      doraSessionState = null;
      doraSessionTrace = null;
      doraClockEvent = null;
      doraRenewalTrace = null;
      doraFaultEvent = null;
      doraPortFaultEvent = null;
      doraVlanFaultEvent = null;
    }
  } catch (error) {
    if (generation === doraSessionGeneration) {
      doraSessionTrace = {error: error.message};
    }
  } finally {
    if (generation === doraSessionGeneration) {
      doraSessionBusy = false;
      renderDoraDiagnostics();
      renderDoraSession();
    }
  }
}

async function runDora() {
  if (doraBusy) return;
  const currentInputs = () => [
    $('dora-client').value, $('dora-server').value,
    $('dora-pool-start').value.trim(), $('dora-pool-end').value.trim(),
    $('dora-transaction-id').value.trim(), $('dora-lease-seconds').value.trim(),
  ];
  const inputs = currentInputs();
  const [client, server, poolStart, poolEnd, rawTransaction, rawLease] = inputs;
  const toInteger = value => /^[0-9]+$/.test(value) ? Number(value) : NaN;
  const transactionId = toInteger(rawTransaction);
  const leaseSeconds = toInteger(rawLease);
  if (!client || !server || !poolStart || !poolEnd
      || !Number.isSafeInteger(transactionId) || transactionId < 1
      || transactionId > 4294967295 || !Number.isSafeInteger(leaseSeconds)
      || leaseSeconds < 60 || leaseSeconds > 604800) {
    invalidateDoraDiagnostics();
    doraDiagnostic = {error: 'Välj giltiga klient-/serverportar, poolens start/slut, transaktions-ID 1–4294967295 och leasetid 60–604800.'};
    renderDoraDiagnostics();
    return;
  }
  const [clientNode, clientPort] = JSON.parse(client);
  const [serverNode, serverPort] = JSON.parse(server);
  const snapshot = JSON.stringify(project);
  const snapshotWorkspace = workspaceRevision;
  const snapshotEdit = editRevision;
  const generation = ++doraGeneration;
  doraBusy = true;
  doraDiagnostic = null;
  renderDoraDiagnostics();
  const stillCurrent = () => generation === doraGeneration
    && workspaceRevision === snapshotWorkspace && editRevision === snapshotEdit
    && JSON.stringify(project) === snapshot
    && JSON.stringify(currentInputs()) === JSON.stringify(inputs);
  try {
    const result = await api('/api/dhcp/dora', {
      project: JSON.parse(snapshot), clientNode, clientPort, serverNode, serverPort,
      poolStart, poolEnd, transactionId, leaseSeconds,
    });
    if (stillCurrent()) doraDiagnostic = result;
  } catch (error) {
    if (stillCurrent()) doraDiagnostic = {error: error.message};
  } finally {
    doraBusy = false;
    renderDoraDiagnostics();
  }
}

async function runDhcp() {
  if (dhcpBusy) return;
  const currentInputs = () => [
    $('dhcp-client').value, $('dhcp-server').value,
    $('dhcp-offered-ip').value.trim(), $('dhcp-transaction-id').value.trim(),
    $('dhcp-lease-seconds').value.trim(),
  ];
  const inputs = currentInputs();
  const [client, server, proposedIpv4, rawTransaction, rawLease] = inputs;
  const parseInteger = value => /^[0-9]+$/.test(value) ? Number(value) : NaN;
  const transactionId = parseInteger(rawTransaction);
  const leaseSeconds = parseInteger(rawLease);
  if (!client || !server || !proposedIpv4 ||
      !Number.isSafeInteger(transactionId) || transactionId < 1 || transactionId > 4294967295 ||
      !Number.isSafeInteger(leaseSeconds) || leaseSeconds < 60 || leaseSeconds > 604800) {
    invalidateDhcpDiagnostics();
    dhcpDiagnostic = {error: 'Välj klient och server, ange föreslagen IPv4, transaktions-ID 1–4294967295 och leasetid 60–604800.'};
    renderDhcpDiagnostics();
    return;
  }
  const [clientNode, clientPort] = JSON.parse(client);
  const [serverNode, serverPort] = JSON.parse(server);
  const snapshot = JSON.stringify(project);
  const snapshotWorkspace = workspaceRevision;
  const snapshotEdit = editRevision;
  const generation = ++dhcpGeneration;
  dhcpDiagnostic = null;
  dhcpBusy = true;
  renderDhcpDiagnostics();
  const stillCurrent = () => generation === dhcpGeneration &&
    workspaceRevision === snapshotWorkspace && editRevision === snapshotEdit &&
    JSON.stringify(project) === snapshot && JSON.stringify(currentInputs()) === JSON.stringify(inputs);
  try {
    const response = await api('/api/dhcp/discover-offer', {
      project: JSON.parse(snapshot), clientNode, clientPort, serverNode, serverPort,
      proposedIpv4, transactionId, leaseSeconds,
    });
    if (stillCurrent()) dhcpDiagnostic = response;
  } catch (error) {
    if (stillCurrent()) dhcpDiagnostic = {error: error.message};
  } finally {
    dhcpBusy = false;
    renderDhcpDiagnostics();
  }
}

function diagnosticInputs(kind) {
  return diagnosticFields[kind].map(id => $(id).value.trim());
}
function beginDiagnostic(kind) {
  return {kind, run: ++diagnosticRuns[kind], workspaceRevision, editRevision,
    snapshot: JSON.stringify(project), inputs: diagnosticInputs(kind)};
}
function diagnosticCurrent(context) {
  return diagnosticRuns[context.kind] === context.run &&
    workspaceRevision === context.workspaceRevision && editRevision === context.editRevision &&
    JSON.stringify(project) === context.snapshot &&
    JSON.stringify(diagnosticInputs(context.kind)) === JSON.stringify(context.inputs);
}
function clearDiagnostic(kind) {
  diagnosticRuns[kind] += 1;
  if (kind === 'arp') {
    arpDiagnostic = null; arpHighlightedLinks = []; render();
  } else if (kind === 'route') {
    routeLookup = null; renderRouteLookup();
  } else if (kind === 'ipv4') {
    ipv4Diagnostic = null; renderIPv4Trace();
  } else {
    pingDiagnostic = null; renderPing();
  }
}
async function runArp() {
  const [selected, targetIpv4] = diagnosticInputs('arp');
  if (!selected) return;
  const context = beginDiagnostic('arp');
  if (!targetIpv4) {
    arpDiagnostic = {error:'Ange mål-IPv4 uttryckligen.'};
    arpHighlightedLinks = [];
    render();
    return;
  }
  const [sourceNode, sourcePort] = JSON.parse(selected);
  try {
    const result = await queryArp(context.snapshot, sourceNode, sourcePort, targetIpv4);
    if (!diagnosticCurrent(context)) return;
    arpDiagnostic = result;
    arpHighlightedLinks = [...new Set([
      ...result.result.requestTransmissions, ...result.result.replyTransmissions,
    ].map(t => t.linkId))];
  } catch (error) {
    if (!diagnosticCurrent(context)) return;
    arpDiagnostic = {error: error.message};
    arpHighlightedLinks = [];
  }
  render();
}

async function startSimulationSession() {
  if (sessionId || sessionBusy) return;
  const generation = sessionGeneration;
  const snapshot = JSON.stringify(project);
  sessionBusy = true;
  renderSessionDiagnostics();
  try {
    const response = await api('/api/simulation/start', {project});
    if (generation !== sessionGeneration || snapshot !== JSON.stringify(project)) {
      void api('/api/simulation/stop', {sessionId:response.sessionId}).catch(() => {});
      return;
    }
    sessionId = response.sessionId;
    sessionOperationCount = response.operationCount;
    sessionDiagnostic = null;
  } catch (error) {
    if (generation !== sessionGeneration) return;
    sessionDiagnostic = {error:error.message};
  } finally {
    if (generation === sessionGeneration) {
      sessionBusy = false;
      render();
    }
  }
}

async function runSimulationOperation(operation) {
  if (!sessionId || sessionBusy) return;
  const selected = $('session-source').value;
  if (!selected) return;
  const [sourceNode, sourcePort] = JSON.parse(selected);
  const target = $(operation === 'arp' ? 'session-ip' : 'session-mac').value.trim();
  if (!target) {
    sessionDiagnostic = {error:'Ange måladressen uttryckligen.'};
    renderSessionDiagnostics();
    return;
  }
  const id = sessionId, generation = sessionGeneration;
  const snapshot = JSON.stringify(project);
  sessionBusy = true;
  renderSessionDiagnostics();
  try {
    const data = await api('/api/simulation/run', {
      sessionId:id, project, operation, sourceNode, sourcePort, target,
    });
    if (generation !== sessionGeneration || snapshot !== JSON.stringify(project) ||
        id !== sessionId) return;
    sessionOperationCount = data.operationCount;
    sessionDiagnostic = {data, sourceNode, sourcePort, target};
    const r = data.result;
    const transmissions = operation === 'arp'
      ? [...r.requestTransmissions, ...r.replyTransmissions]
      : r.transmissions;
    sessionHighlightedLinks = [...new Set(transmissions.map(t => t.linkId))];
  } catch (error) {
    if (generation !== sessionGeneration || id !== sessionId) return;
    sessionDiagnostic = {error:error.message};
    sessionHighlightedLinks = [];
    if (/unknown or expired session|project changed since session/.test(error.message)) {
      invalidateSimulationSession();
      sessionDiagnostic = {error:error.message};
    }
  } finally {
    if (generation === sessionGeneration) {
      sessionBusy = false;
      render();
    } else if (sessionId === null) {
      render();
    }
  }
}

async function resetSimulationSession() {
  if (!sessionId || sessionBusy) return;
  const id = sessionId, generation = sessionGeneration;
  sessionBusy = true;
  renderSessionDiagnostics();
  try {
    const result = await api('/api/simulation/reset', {sessionId:id, project});
    if (generation !== sessionGeneration || id !== sessionId) return;
    sessionOperationCount = result.operationCount;
    sessionDiagnostic = null;
    sessionHighlightedLinks = [];
  } catch (error) {
    if (generation !== sessionGeneration) return;
    sessionDiagnostic = {error:error.message};
  } finally {
    if (generation === sessionGeneration) {
      sessionBusy = false;
      render();
    }
  }
}

async function stopSimulationSession() {
  if (!sessionId || sessionBusy) return;
  invalidateSimulationSession();
  render();
}

function icmpInvestigationStartInputs() {
  return JSON.stringify([
    $('icmp-investigation-source').value,
    $('icmp-investigation-destination').value.trim(),
    $('icmp-investigation-ttl').value.trim(),
  ]);
}
function startIcmpInvestigation() {
  const selected = $('icmp-investigation-source').value;
  const destinationIpv4 = $('icmp-investigation-destination').value.trim();
  const ttl = sessionInteger($('icmp-investigation-ttl').value.trim(), 2, 255);
  if (!selected || !destinationIpv4 || ttl === null) {
    icmpInvestigation.setInputError('Välj en dokumenterad IPv4-källa, destinations-IP och giltig TTL.');
    return;
  }
  const [sourceNode, sourcePort] = JSON.parse(selected);
  void icmpInvestigation.start({sourceNode, sourcePort, destinationIpv4, ttl},
    icmpInvestigationStartInputs);
}
function measureIcmpInvestigation() {
  const kind = $('icmp-investigation-probe').value;
  const state = icmpInvestigation.getState().state;
  if (!state) return;
  let target = {};
  let readInputs = () => $('icmp-investigation-probe').value;
  if (kind === 'route') {
    const nodeId = $('icmp-investigation-route-node').value;
    if (!nodeId) return;
    const destinationChoice = $('icmp-investigation-route-destination').value;
    target = {nodeId, destinationIpv4: destinationChoice === 'source'
      ? state.sourceIpv4 : state.destinationIpv4};
    readInputs = () => JSON.stringify([$('icmp-investigation-probe').value,
      $('icmp-investigation-route-node').value,
      $('icmp-investigation-route-destination').value]);
  } else if (kind === 'link') {
    target = {linkId: $('icmp-investigation-link').value};
    if (!target.linkId) return;
    readInputs = () => JSON.stringify([$('icmp-investigation-probe').value,
      $('icmp-investigation-link').value]);
  } else if (kind === 'port' || kind === 'vlan') {
    const selected = $(kind === 'port' ? 'icmp-investigation-port'
      : 'icmp-investigation-vlan').value;
    if (!selected) return;
    const [nodeId, portId] = JSON.parse(selected);
    target = {nodeId, portId};
    readInputs = () => JSON.stringify([$('icmp-investigation-probe').value,
      $(kind === 'port' ? 'icmp-investigation-port' : 'icmp-investigation-vlan').value]);
  }
  void icmpInvestigation.probe(kind, target, readInputs);
}
function diagnoseIcmpInvestigation() {
  const diagnosis = $('icmp-investigation-diagnosis').value;
  void icmpInvestigation.diagnose(diagnosis, () => $('icmp-investigation-diagnosis').value);
}
function repairIcmpInvestigation() { void icmpInvestigation.repair(); }
function stopIcmpInvestigation() { void icmpInvestigation.stop(); }

async function runTroubleshooting() {
  const selected = $('trouble-source').value;
  const kind = $('trouble-type').value;
  if (!selected) return;
  const [sourceNode,sourcePort] = JSON.parse(selected);
  const destinationIpv4 = $('trouble-destination').value.trim();
  const ttlText = $('trouble-ttl').value.trim();
  const chosen = kind === 'LINK_DISABLED' ? $('trouble-link').value :
    kind === 'PORT_DISABLED' ? $('trouble-port').value :
    ['ACCESS_VLAN_CHANGED','TRUNK_VLAN_BLOCKED'].includes(kind)
      ? $('trouble-vlan-port').value :
    kind === 'IPV4_PREFIX_CHANGED' ? $('trouble-ipv4-port').value :
      $('trouble-route').value;
  const vlanText = $('trouble-vlan').value.trim();
  const prefixText = $('trouble-prefix').value.trim();
  const hopText = $('trouble-next-hop').value.trim();
  if (!chosen || !destinationIpv4 || !/^[0-9]+$/.test(ttlText) ||
      Number(ttlText) < 1 || Number(ttlText) > 255 ||
      (['ACCESS_VLAN_CHANGED','TRUNK_VLAN_BLOCKED'].includes(kind) &&
       (!/^[0-9]+$/.test(vlanText) || Number(vlanText) < 1 || Number(vlanText) > 4094)) ||
      (kind === 'IPV4_PREFIX_CHANGED' &&
       (!/^[0-9]+$/.test(prefixText) || Number(prefixText) < 1 || Number(prefixText) > 32)) ||
      (kind === 'STATIC_NEXT_HOP_CHANGED' && !hopText)) {
    troubleDiagnostic = {error:'Ange källa, mål-IPv4, TTL, och ett explicit giltigt värde för det valda felet.'};
    renderTroubleshooting();
    return;
  }
  const ttl = Number(ttlText);
  const [nodeId,targetId] = kind !== 'LINK_DISABLED' ? JSON.parse(chosen) : [null,null];
  const fault = kind === 'LINK_DISABLED' ? {type:kind,linkId:chosen}
    : kind === 'PORT_DISABLED' ? {type:kind,nodeId,portId:targetId}
    : kind === 'ACCESS_VLAN_CHANGED' ? {type:kind,nodeId,portId:targetId,newVlan:Number(vlanText)}
    : kind === 'TRUNK_VLAN_BLOCKED' ? {type:kind,nodeId,portId:targetId,blockedVlan:Number(vlanText)}
    : kind === 'IPV4_PREFIX_CHANGED' ? {type:kind,nodeId,portId:targetId,newPrefix:Number(prefixText)}
    : kind === 'STATIC_ROUTE_REMOVED' ? {type:kind,nodeId,routeId:targetId}
    : {type:kind,nodeId,routeId:targetId,newNextHop:hopText};
  const snapshot = JSON.stringify(project);
  const inputSnapshot = [selected,kind,chosen,destinationIpv4,ttlText,vlanText,
    prefixText,hopText].join('|');
  const currentInputs = () => {
    const currentType = $('trouble-type').value;
    const currentTarget = currentType === 'LINK_DISABLED' ? $('trouble-link').value :
      currentType === 'PORT_DISABLED' ? $('trouble-port').value :
      ['ACCESS_VLAN_CHANGED','TRUNK_VLAN_BLOCKED'].includes(currentType)
        ? $('trouble-vlan-port').value :
      currentType === 'IPV4_PREFIX_CHANGED' ? $('trouble-ipv4-port').value :
        $('trouble-route').value;
    return [ $('trouble-source').value, currentType,currentTarget,
      $('trouble-destination').value.trim(),$('trouble-ttl').value.trim(),
      $('trouble-vlan').value.trim(),$('trouble-prefix').value.trim(),
      $('trouble-next-hop').value.trim() ].join('|');
  };
  const stillCurrent = () => snapshot === JSON.stringify(project) &&
    currentInputs() === inputSnapshot;
  const path = kind === 'LINK_DISABLED' ? '/api/troubleshoot/link' : '/api/troubleshoot/fault';
  const body = {project,sourceNode,sourcePort,destinationIpv4,ttl,identifier:1,sequence:1};
  if (kind === 'LINK_DISABLED') body.linkId = chosen;
  else body.fault = fault;
  try {
    const result = await api(path,body);
    if (!stillCurrent()) return;
    troubleDiagnostic = result;
  } catch (error) {
    if (!stillCurrent()) return;
    troubleDiagnostic = {error:error.message};
  }
  renderTroubleshooting();
}

async function runPing() {
  const [selected, destinationIpv4, rawTtl, rawIdentifier, rawSequence] = diagnosticInputs('ping');
  if (!selected) return;
  const context = beginDiagnostic('ping');
  const [sourceNode, sourcePort] = JSON.parse(selected);
  const number = value => /^[0-9]+$/.test(value) ? Number(value) : NaN;
  const ttl = number(rawTtl), identifier = number(rawIdentifier), sequence = number(rawSequence);
  if (!destinationIpv4 || !Number.isInteger(ttl) || ttl < 1 || ttl > 255 ||
      !Number.isInteger(identifier) || identifier < 0 || identifier > 65535 ||
      !Number.isInteger(sequence) || sequence < 0 || sequence > 65535) {
    pingDiagnostic = {error:'Ange mål-IP, TTL 1–255, identifierare och sekvens 0–65535.'};
    renderPing();
    return;
  }
  try {
    const result = await queryPing(context.snapshot, sourceNode, sourcePort,
      destinationIpv4, ttl, identifier, sequence);
    if (!diagnosticCurrent(context)) return;
    pingDiagnostic = result;
  } catch (error) {
    if (!diagnosticCurrent(context)) return;
    pingDiagnostic = {error:error.message};
  }
  renderPing();
}

async function runIPv4Trace() {
  const [selected, destinationIpv4, rawTtl] = diagnosticInputs('ipv4');
  if (!selected) return;
  const context = beginDiagnostic('ipv4');
  const [sourceNode, sourcePort] = JSON.parse(selected);
  if (!destinationIpv4 || !/^[0-9]+$/.test(rawTtl)) {
    ipv4Diagnostic = {error:'Ange uttrycklig destinations-IPv4 och heltals-TTL 1–255.'};
    renderIPv4Trace();
    return;
  }
  try {
    const result = await queryIPv4(context.snapshot, sourceNode, sourcePort,
      destinationIpv4, Number(rawTtl));
    if (!diagnosticCurrent(context)) return;
    ipv4Diagnostic = result;
  } catch (error) {
    if (!diagnosticCurrent(context)) return;
    ipv4Diagnostic = {error:error.message};
  }
  renderIPv4Trace();
}

async function runRouteLookup() {
  const [nodeId, destinationIpv4] = diagnosticInputs('route');
  if (!nodeId) return;
  const context = beginDiagnostic('route');
  if (!destinationIpv4) {
    routeLookup = {error:'Ange destinations-IPv4 uttryckligen.'};
    renderRouteLookup();
    return;
  }
  try {
    const result = await queryRoute(context.snapshot, nodeId, destinationIpv4);
    if (!diagnosticCurrent(context)) return;
    routeLookup = result;
  } catch (error) {
    if (!diagnosticCurrent(context)) return;
    routeLookup = {error:error.message};
  }
  renderRouteLookup();
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
$('export-xlsx').addEventListener('click', () => exportSpreadsheet('xlsx'));
$('export-ods').addEventListener('click', () => exportSpreadsheet('ods'));
$('run-trace').addEventListener('click', runTrace);
$('run-route-lookup').addEventListener('click', runRouteLookup);
$('run-ipv4-trace').addEventListener('click', runIPv4Trace);
$('run-ping').addEventListener('click', runPing);
$('icmp-investigation-start').addEventListener('click', startIcmpInvestigation);
$('icmp-investigation-stop').addEventListener('click', stopIcmpInvestigation);
$('icmp-investigation-measure').addEventListener('click', measureIcmpInvestigation);
$('icmp-investigation-diagnose').addEventListener('click', diagnoseIcmpInvestigation);
$('icmp-investigation-repair').addEventListener('click', repairIcmpInvestigation);
$('icmp-investigation-probe').addEventListener('change', renderIcmpInvestigation);
$('icmp-investigation-source').addEventListener('change', renderIcmpInvestigation);
$('icmp-investigation-destination').addEventListener('input', renderIcmpInvestigation);
$('icmp-investigation-ttl').addEventListener('input', renderIcmpInvestigation);
$('run-troubleshoot').addEventListener('click', runTroubleshooting);
for (const id of ['trouble-source','trouble-link','trouble-type','trouble-port',
                  'trouble-vlan-port','trouble-vlan','trouble-ipv4-port','trouble-prefix',
                  'trouble-route','trouble-next-hop','trouble-destination','trouble-ttl']) {
  $(id).addEventListener(['trouble-vlan','trouble-prefix','trouble-next-hop',
      'trouble-destination','trouble-ttl'].includes(id)
    ? 'input' : 'change', () => {
    troubleDiagnostic = null; renderTroubleshooting();
  });
}
for (const id of ['ping-source','ping-destination','ping-ttl','ping-identifier','ping-sequence']) {
  $(id).addEventListener(id === 'ping-source' ? 'change' : 'input', () => {
    pingDiagnostic = null; renderPing();
  });
}
for (const id of ['ipv4-source','ipv4-destination','ipv4-ttl']) {
  $(id).addEventListener(id === 'ipv4-source' ? 'change' : 'input', () => {
    ipv4Diagnostic = null; renderIPv4Trace();
  });
}
$('route-source').addEventListener('change', () => {
  routeLookup = null; renderRouteLookup();
});
$('route-destination-ip').addEventListener('input', () => {
  routeLookup = null; renderRouteLookup();
});
$('run-arp').addEventListener('click', runArp);
for (const kind of ['arp', 'route', 'ipv4', 'ping']) {
  for (const id of diagnosticFields[kind]) {
    $(id).addEventListener('input', () => clearDiagnostic(kind));
    if ($(id).tagName === 'SELECT') $(id).addEventListener('change', () => clearDiagnostic(kind));
  }
}
$('run-dhcp').addEventListener('click', runDhcp);
$('run-dora').addEventListener('click', runDora);
$('investigation-start').addEventListener('click', startInvestigation);
$('investigation-stop').addEventListener('click', stopInvestigation);
$('investigation-run-probe').addEventListener('click', probeInvestigation);
$('investigation-advance').addEventListener('click', advanceInvestigation);
$('investigation-submit').addEventListener('click', diagnoseInvestigation);
$('investigation-repair').addEventListener('click', repairInvestigation);
$('investigation-probe').addEventListener('change', renderInvestigation);
$('dora-session-start').addEventListener('click', startDoraSession);
$('dora-session-run').addEventListener('click', runDoraSession);
$('dora-session-renew').addEventListener('click', renewDoraSession);
$('dora-session-fault-break').addEventListener('click', () => setDoraLinkFault(true));
$('dora-session-fault-restore').addEventListener('click', () => setDoraLinkFault(false));
$('dora-session-port-down').addEventListener('click', () => setDoraSwitchFault('port', false));
$('dora-session-port-up').addEventListener('click', () => setDoraSwitchFault('port', true));
$('dora-session-vlan-set').addEventListener('click', () => setDoraSwitchFault('vlan', false));
$('dora-session-vlan-restore').addEventListener('click', () => setDoraSwitchFault('vlan', true));
for (const id of ['dora-session-port-fault', 'dora-session-vlan-port',
                  'dora-session-vlan-target']) {
  $(id).addEventListener('change', () => {
    doraPortFaultEvent = null;
    doraVlanFaultEvent = null;
    renderDoraSession();
  });
}
$('dora-session-fault-link').addEventListener('change', () => {
  doraFaultEvent = null;
  renderDoraSession();
});
$('dora-session-advance').addEventListener('click', advanceDoraSession);
$('dora-session-reset').addEventListener('click', resetDoraSession);
$('dora-session-stop').addEventListener('click', stopDoraSession);

for (const id of ['dora-client', 'dora-server', 'dora-pool-start', 'dora-pool-end',
                  'dora-transaction-id', 'dora-lease-seconds']) {
  $(id).addEventListener(id === 'dora-client' || id === 'dora-server' ? 'change' : 'input', () => {
    invalidateDoraDiagnostics();
    if (doraSessionId !== null && ['dora-client', 'dora-transaction-id',
                                     'dora-lease-seconds'].includes(id)) {
      doraSessionGeneration += 1;
      doraSessionTrace = null;
      doraRenewalTrace = null;
    }
    renderDoraDiagnostics();
    renderDoraSession();
    renderInvestigation();
  });
}

for (const id of ['dhcp-client', 'dhcp-server', 'dhcp-offered-ip',
                  'dhcp-transaction-id', 'dhcp-lease-seconds']) {
  $(id).addEventListener(id === 'dhcp-client' || id === 'dhcp-server' ? 'change' : 'input', () => {
    invalidateDhcpDiagnostics();
    renderDhcpDiagnostics();
  });
}
$('session-start').addEventListener('click', startSimulationSession);
$('session-arp').addEventListener('click', () => runSimulationOperation('arp'));
$('session-ethernet').addEventListener('click', () => runSimulationOperation('ethernet'));
$('session-reset').addEventListener('click', resetSimulationSession);
$('session-stop').addEventListener('click', stopSimulationSession);
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
