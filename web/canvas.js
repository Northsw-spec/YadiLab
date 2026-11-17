import {truncate} from './model.js';

const NS = 'http://www.w3.org/2000/svg';
const WIDTH = 202;
const HEAD = 66;
const PORT_ROW = 23;
const HEIGHT = node => Math.max(96, HEAD + node.ports.length * PORT_ROW + 12);
const svgElement = (tag, attributes = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, String(value));
  return el;
};
const svgText = (attributes, label) => {
  const text = svgElement('text', attributes);
  text.textContent = label;
  return text;
};
const entry = (project, nodeId) => project.nodes.find(n => n.id === nodeId);
function endpoint(project, endpoint) {
  const node = entry(project, endpoint.node);
  const index = node.ports.findIndex(p => p.id === endpoint.port);
  const link = project.links.find(l => (l.a.node === endpoint.node && l.a.port === endpoint.port) || (l.b.node === endpoint.node && l.b.port === endpoint.port));
  const remote = link && entry(project, (link.a.node === endpoint.node ? link.b : link.a).node);
  const side = remote && remote.x + WIDTH / 2 < node.x + WIDTH / 2 ? 'left' : 'right';
  return {x: node.x + (side === 'left' ? 0 : WIDTH), y: node.y + HEAD + index * PORT_ROW + 5, side};
}
function route(a, b) {
  // The path starts/ends exactly at the visible port circles. Geometry does
  // not create new links or assert that a cable is collision-free.
  const da = a.side === 'right' ? 1 : -1;
  const db = b.side === 'right' ? 1 : -1;
  if (da === -db && (a.x - b.x) * da < 0) {
    // Opposing visible port faces on ordered nodes: use a direct, exact cable
    // when aligned, otherwise a simple midpoint elbow (even at short gaps).
    if (a.y === b.y) return `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
    const midpoint = (a.x + b.x) / 2;
    return `M ${a.x} ${a.y} L ${midpoint} ${a.y} L ${midpoint} ${b.y} L ${b.x} ${b.y}`;
  }
  const outA = a.x + da * 36;
  const outB = b.x + db * 36;
  const middleY = (a.y + b.y) / 2 + (a.y === b.y ? 28 : 0);
  return `M ${a.x} ${a.y} L ${outA} ${a.y} L ${outA} ${middleY} L ${outB} ${middleY} L ${outB} ${b.y} L ${b.x} ${b.y}`;
}

export class TopologyCanvas {
  constructor(svg, {onSelect, onPort, onMove, onEndMove, onScale}) {
    this.svg = svg;
    this.callbacks = {onSelect, onPort, onMove, onEndMove, onScale};
    this.view = {x: -30, y: -30, w: 1200, h: 740};
    this.project = null;
    this.selected = null;
    this.pending = null;
    this.highlight = [];
    this.interaction = null;
    this.setView();
    svg.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target !== svg) return;
      this.capture(event, {kind: 'pan', x: event.clientX, y: event.clientY, start: {...this.view}});
      onSelect(null);
    });
    svg.addEventListener('pointermove', event => {
      const current = this.interaction;
      if (!current || event.pointerId !== current.pointerId) return;
      if (current.kind === 'pan') {
        const rect = svg.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        this.view.x = current.start.x - (event.clientX - current.x) * this.view.w / rect.width;
        this.view.y = current.start.y - (event.clientY - current.y) * this.view.h / rect.height;
        this.setView();
      } else if (current.kind === 'node') {
        const world = this.toWorld(event.clientX, event.clientY);
        const x = Math.round(current.nodeX + world.x - current.worldX);
        const y = Math.round(current.nodeY + world.y - current.worldY);
        if (x !== current.lastX || y !== current.lastY) {
          current.lastX = x;
          current.lastY = y;
          onMove(current.id, x, y);
        }
      }
    });
    const finish = event => {
      if (!this.interaction || this.interaction.pointerId !== event.pointerId) return;
      if (this.interaction.kind === 'node') onEndMove();
      this.interaction = null;
      try { if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId); } catch (_) { /* browser already released */ }
    };
    svg.addEventListener('pointerup', finish);
    svg.addEventListener('pointercancel', finish);
    svg.addEventListener('wheel', event => {
      event.preventDefault();
      this.zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12, event.clientX, event.clientY);
    }, {passive: false});
  }

  capture(event, state) {
    this.interaction = {...state, pointerId: event.pointerId};
    this.svg.setPointerCapture(event.pointerId);
  }

  toWorld(clientX, clientY) {
    const rect = this.svg.getBoundingClientRect();
    return {x: this.view.x + (clientX - rect.left) / Math.max(1, rect.width) * this.view.w,
      y: this.view.y + (clientY - rect.top) / Math.max(1, rect.height) * this.view.h};
  }

  setView() {
    this.svg.setAttribute('viewBox', `${this.view.x} ${this.view.y} ${this.view.w} ${this.view.h}`);
    const r = this.svg.getBoundingClientRect();
    this.callbacks.onScale(Math.round((r.width || 900) / this.view.w * 100));
  }

  zoom(factor, x, y) {
    const point = this.toWorld(x ?? (this.svg.getBoundingClientRect().left + this.svg.clientWidth / 2),
      y ?? (this.svg.getBoundingClientRect().top + this.svg.clientHeight / 2));
    const w = Math.max(160, Math.min(9000, this.view.w / factor));
    const h = this.view.h * w / this.view.w;
    const fx = (point.x - this.view.x) / this.view.w;
    const fy = (point.y - this.view.y) / this.view.h;
    this.view = {x: point.x - fx * w, y: point.y - fy * h, w, h};
    this.setView();
  }

  fit() {
    const nodes = this.project?.nodes || [];
    const rect = this.svg.getBoundingClientRect();
    const aspect = Math.max(.5, rect.width / Math.max(1, rect.height));
    if (!nodes.length) {
      this.view = {x: -30, y: -30, w: 1200, h: 1200 / aspect};
    } else {
      const minX = Math.min(...nodes.map(n => n.x)) - 95;
      const minY = Math.min(...nodes.map(n => n.y)) - 105;
      const maxX = Math.max(...nodes.map(n => n.x + WIDTH)) + 95;
      const maxY = Math.max(...nodes.map(n => n.y + HEIGHT(n))) + 105;
      const w = Math.max(520, maxX - minX, (maxY - minY) * aspect);
      const h = w / aspect;
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      this.view = {x: cx - w / 2, y: cy - h / 2, w, h};
    }
    this.setView();
  }

  setData(project, selected, pending, highlighted = []) {
    this.project = project;
    this.selected = selected;
    this.pending = pending;
    this.highlight = highlighted;
    this.render();
  }

  render() {
    const project = this.project;
    if (!project) return;
    const children = [];
    // Zones are derived from explicitly assigned membership. They are
    // presentation backgrounds, never physical nodes or inferred links.
    for (const zone of project.zones) {
      const members = project.nodes.filter(node => node.zoneId === zone.id);
      if (!members.length) continue;
      const minX = Math.min(...members.map(n => n.x)) - 35;
      const maxX = Math.max(...members.map(n => n.x + WIDTH)) + 35;
      const minY = Math.min(...members.map(n => n.y)) - 50;
      const maxY = Math.max(...members.map(n => n.y + HEIGHT(n))) + 30;
      children.push(svgElement('rect', {x: minX, y: minY, width: maxX - minX, height: maxY - minY, rx: 15,
        class: 'zone-background', 'data-zone-id': zone.id}));
      children.push(svgText({x: minX + 17, y: minY + 26, class: 'zone-label'}, truncate(zone.label, 35)));
    }
    for (const link of project.links) {
      const a = endpoint(project, link.a), b = endpoint(project, link.b);
      const d = route(a, b);
      const highlighted = this.highlight.includes(link.id);
      const selected = this.selected?.type === 'link' && this.selected.id === link.id;
      const p = svgElement('path', {d, class: `network-edge${link.enabled ? '' : ' offline'}${highlighted ? ' highlight' : ''}${selected ? ' selected' : ''}`,
        'data-link-id': link.id, 'data-from-node': link.a.node, 'data-from-port': link.a.port,
        'data-to-node': link.b.node, 'data-to-port': link.b.port});
      children.push(p);
      const hit = svgElement('path', {d, class: 'edge-hit', 'data-link-hit': link.id});
      hit.addEventListener('pointerdown', event => { event.stopPropagation(); this.callbacks.onSelect({type: 'link', id: link.id}); });
      children.push(hit);
    }
    for (const node of project.nodes) {
      const group = svgElement('g', {class: `network-node${this.selected?.type === 'node' && this.selected.id === node.id ? ' selected' : ''}`,
        transform: `translate(${node.x} ${node.y})`, 'data-node-id': node.id});
      group.append(svgElement('rect', {width: WIDTH, height: HEIGHT(node), class: 'node-box'}));
      group.append(svgElement('rect', {x: 12, y: 13, width: 49, height: 24, rx: 6, class: 'node-kind-badge'}));
      group.append(svgText({x: 36.5, y: 29, 'text-anchor': 'middle', class: 'node-badge-label'},
        {host: 'PC', switch: 'SW', router: 'RTR', firewall: 'FW'}[node.kind] || '?'));
      group.append(svgText({x: 72, y: 29, class: 'node-title'}, truncate(node.label, 16)));
      group.append(svgText({x: 14, y: 52, class: 'node-kind'}, node.id + ' · ' + node.kind.toUpperCase()));
      group.append(svgElement('line', {x1: 12, y1: 59, x2: WIDTH - 12, y2: 59, class: 'node-separator'}));
      for (let i = 0; i < node.ports.length; i++) {
        const port = node.ports[i];
        const pt = endpoint(project, {node: node.id, port: port.id});
        const px = pt.x - node.x, py = pt.y - node.y;
        group.append(svgText({x: pt.side === 'right' ? WIDTH - 15 : 15, y: py + 4,
          class: `node-port${port.enabled ? '' : ' offline'}`,
          'text-anchor': pt.side === 'right' ? 'end' : 'start'}, truncate(port.name, 23)));
        const dot = svgElement('circle', {cx: px, cy: py, r: 6,
          class: `port-dot${port.enabled ? '' : ' offline'}${this.pending?.node === node.id && this.pending?.port === port.id ? ' pending' : ''}`,
          'data-port-node': node.id, 'data-port-id': port.id});
        dot.addEventListener('pointerdown', event => {
          event.stopPropagation();
          this.callbacks.onPort({node: node.id, port: port.id});
        });
        group.append(dot);
      }
      group.addEventListener('pointerdown', event => {
        if (event.button !== 0) return;
        event.stopPropagation();
        const pt = this.toWorld(event.clientX, event.clientY);
        this.capture(event, {kind: 'node', id: node.id, worldX: pt.x, worldY: pt.y,
          nodeX: node.x, nodeY: node.y, lastX: node.x, lastY: node.y});
        this.callbacks.onSelect({type: 'node', id: node.id});
      });
      children.push(group);
    }
    this.svg.replaceChildren(...children);
  }
}
