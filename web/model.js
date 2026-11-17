// Canonical browser state. Only explicitly declared source facts are represented.
export const KINDS = Object.freeze(['host', 'switch', 'router', 'firewall']);
export const blank = () => ({schemaVersion: '1.1', name: 'Nytt nätverkslabb', zones: [], nodes: [], links: []});
export const copy = value => structuredClone(value);
export function nextId(prefix, records) {
  const taken = new Set(records.map(record => record.id));
  for (let i = 1; i < 100000; i++) if (!taken.has(`${prefix}-${i}`)) return `${prefix}-${i}`;
  throw new Error('Inga lediga identifierare');
}
export function newNode(project, kind = 'host') {
  const id = nextId('node', project.nodes);
  const node = {id, label: `Enhet ${project.nodes.length + 1}`, kind,
    x: 110 + (project.nodes.length % 4) * 260,
    y: 110 + Math.floor(project.nodes.length / 4) * 220,
    zoneId: null, ports: []};
  project.nodes.push(node);
  return node;
}
export function newZone(project) {
  const id = nextId('zone', project.zones);
  const zone = {id, label: `Zon ${project.zones.length + 1}`};
  project.zones.push(zone);
  return zone;
}
export function addPort(node, name) {
  const clean = String(name).trim();
  if (!clean || clean.length > 120) throw new Error('Portnamn måste vara 1–120 tecken.');
  const port = {id: nextId('port', node.ports), name: clean, enabled: true, ipv4: null};
  node.ports.push(port);
  return port;
}
export const used = (project, nodeId, portId) => project.links.some(l =>
  (l.a.node === nodeId && l.a.port === portId) || (l.b.node === nodeId && l.b.port === portId));
export function connect(project, a, b) {
  if (a.node === b.node) throw new Error('En länk måste koppla två olika enheter.');
  for (const end of [a, b]) {
    const node = project.nodes.find(n => n.id === end.node);
    if (!node || !node.ports.some(p => p.id === end.port)) throw new Error(`Port saknas: ${end.node}/${end.port}`);
    if (used(project, end.node, end.port)) throw new Error(`Port redan ansluten: ${end.node}/${end.port}`);
  }
  const link = {id: nextId('link', project.links), a: {...a}, b: {...b}, enabled: true};
  project.links.push(link);
  return link;
}
export function exampleProject() {
  // Deliberately labeled example: declared nodes and cables, not discovered data.
  return {
    schemaVersion: '1.1', name: 'DEMO – två klienter och en switch',
    zones: [{id: 'zone-lab', label: 'Exempelzon'}],
    nodes: [
      {id: 'pc-1', label: 'Klient A', kind: 'host', x: 90, y: 235, zoneId: 'zone-lab', ports: [{id: 'eth0', name: 'eth0', enabled: true, ipv4: '192.0.2.10/24'}]},
      {id: 'sw-1', label: 'Switch 1', kind: 'switch', x: 400, y: 215, zoneId: 'zone-lab', ports: [
        {id: 'ge1', name: 'GigabitEthernet1', enabled: true, ipv4: null},
        {id: 'ge2', name: 'GigabitEthernet2', enabled: true, ipv4: null}]},
      {id: 'pc-2', label: 'Klient B', kind: 'host', x: 740, y: 235, zoneId: 'zone-lab', ports: [{id: 'eth0', name: 'eth0', enabled: true, ipv4: '192.0.2.11/24'}]},
    ],
    links: [
      {id: 'cable-1', a: {node: 'pc-1', port: 'eth0'}, b: {node: 'sw-1', port: 'ge1'}, enabled: true},
      {id: 'cable-2', a: {node: 'sw-1', port: 'ge2'}, b: {node: 'pc-2', port: 'eth0'}, enabled: true},
    ],
  };
}
export function truncate(value, length = 23) {
  const text = String(value);
  return text.length > length ? text.slice(0, length - 1) + '…' : text;
}
