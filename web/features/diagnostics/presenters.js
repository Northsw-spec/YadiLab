export function presentArp(arpDiagnostic) {
  let tone = '';
  let text = '';
  if (!arpDiagnostic) {
    text = 'Ingen aktuell ARP-simulering. Varje körning startar med tomma MAC- och ARP-tabeller.';
    return {status: tone, text};
  }
  if (arpDiagnostic.error) {
    tone = 'fail';
    text = `ARP-simulering avvisad: ${arpDiagnostic.error}\nIngen ARP-upplösning bevisad.`;
    return {status: tone, text};
  }
  const {result, macTables, arpTable} = arpDiagnostic;
  if (result.status === 'RESOLVED') tone = 'ok';
  else tone = 'fail';
  const traces = (name, transmissions) => `${name}: ${transmissions.length} fysisk(a) överföring(ar)\n`
    + (transmissions.length ? transmissions.map(t =>
        `  ${t.linkId}: ${t.from.node}/${t.from.port} → ${t.to.node}/${t.to.port}`
        + (t.vlanId == null ? '' : ` · VLAN ${t.vlanId}${t.tagged ? ' (taggad)' : ' (otaggad)'}`)
      ).join('\n') : '  Inga');
  const drops = ['requestVlanDrops', 'replyVlanDrops'].flatMap(key =>
    (result[key] || []).map(item => `  ${key}: ${item.switch}/${item.port} · ${item.reason} · VLAN ${item.vlanId ?? 'otaggad'}`));
  const tables = macTables.flatMap(table => [
    `  ${table.switchId}${table.vlanId == null ? ' (otaggad)' : ` VLAN ${table.vlanId}`}:`,
    ...Object.entries(table.entries).map(([mac, port]) => `    ${mac} → ${port}`),
  ]);
  const cache = Object.entries(arpTable).map(([ip, mac]) => `  ${ip} → ${mac}`);
  text = [
    `ARP-status: ${result.status}`,
    result.meaning,
    traces('Förfrågan', result.requestTransmissions),
    traces('Svar', result.replyTransmissions),
    'VLAN-droppar:\n' + (drops.length ? drops.join('\n') : '  Inga observerade'),
    'Inlärda switch-MAC-tabeller:\n' + (tables.length ? tables.join('\n') : '  Inga inlärda poster'),
    'ARP-cache på avsändarporten:\n' + (cache.length ? cache.join('\n') : '  Tom'),
    'Endast denna tillfälliga simulering. Inte ping, IP-routing eller verklig NIC-acceptans.',
  ].join('\n\n');
  return {status: tone, text};
}

export function presentRoute(routeLookup) {
  let tone = '';
  let text = '';
  if (!routeLookup) {
    text = 'Ingen aktuell route lookup. Tabellen är konfigurerad information, inte simulerad IP-leverans.';
    return {status: tone, text};
  }
  if (routeLookup.error) {
    tone = 'fail';
    text = `Route lookup avvisad: ${routeLookup.error}\nIngen IP-leverans har simulerats.`;
    return {status: tone, text};
  }
  const {status, sourceNode, destinationIpv4, routes, candidates, selectedRoute, meaning} = routeLookup;
  if (status === 'MATCH') tone = 'ok';
  else tone = 'fail';
  const describe = route =>
    `  ${route.destination} · ${route.type} · ${route.outInterface.node}/${route.outInterface.port}`
    + ` · lokal IP ${route.sourceIpv4} · next-hop: ${route.nextHop ?? 'ingen (on-link)'}`;
  text = [
    `Routingstatus: ${status}`,
    `Enhet: ${sourceNode} · Destination: ${destinationIpv4}`,
    meaning,
    'Konfigurerade connected och statiska routes:\n' + (routes.length ? routes.map(describe).join('\n') : '  Inga'),
    status === 'MATCH' ?
      'Vald längsta prefixmatchning:\n' + describe(selectedRoute) :
      status === 'AMBIGUOUS' ?
      'Lika specifika kandidatvägar, inget antaget beslut:\n' + candidates.map(describe).join('\n') :
      'Ingen matchande route.',
    'Ingen faktisk paketöverföring eller ARP-förfrågan utfördes. Grafväg, VLAN, länkstatus och NIC-acceptans är inte verifierade.',
  ].join('\n\n');
  return {status: tone, text};
}

export function presentPing(pingDiagnostic) {
  let tone = '';
  let text = '';
  if (!pingDiagnostic) {
    text = 'Ingen aktuell ICMP Echo-utväxling. Varje körning har isolerad ARP- och MAC-inlärning.';
    return {status: tone, text};
  }
  if (pingDiagnostic.error) {
    tone = 'fail';
    text = `ICMP Echo avvisad: ${pingDiagnostic.error}\nIngen tur-och-retur-leverans verifierad.`;
    return {status: tone, text};
  }
  const data = pingDiagnostic;
  tone = data.status === 'REPLIED' ? 'ok' : 'fail';
  const lines = [
    `Ping-status: ${data.status}`,
    data.meaning,
    `Echo id=${data.identifier} seq=${data.sequence}`,
    `Echo Reply matchad: ${data.replyMatched ? 'JA' : 'NEJ'}`,
  ];
  if (!data.icmpError) {
    lines.push('ICMP-routerfel: inget paket genererat eller mottaget.');
  } else {
    const error = data.icmpError;
    const kind = error.type === 11 ? 'Time Exceeded' : error.type === 3 ?
      'Destination Unreachable (Network)' : 'Unsupported';
    lines.push(`ICMP-routerfel: ${kind} · typ ${error.type}/kod ${error.code} · ${error.status}`);
    lines.push(`  Genererande router: ${error.sourceNode}/${error.sourcePort}`);
    lines.push(`  Citerat original-IP: ${error.quotedSourceIpv4} → ${error.quotedDestinationIpv4}`);
    lines.push(`  Felpaketets returtransport: ${error.trace.status}`);
    for (const [i,step] of error.trace.steps.entries()) {
      lines.push(`    Hopp ${i+1}: ${step.node}/${step.outPort}, ${step.route.type} ${step.route.destination}`);
      lines.push(`    ARP: ${step.arp.status} · ${step.arp.resolvedMac || 'MAC ej upplöst'}`);
      lines.push(`    Kablar: ${step.ipv4Transmissions.map(t=>t.linkId).join(', ') || 'inga'}`);
    }
    if (error.status !== 'RECEIVED') {
      lines.push('ICMP-felet nådde INTE ursprungsporten; endast felsymptom observerades.');
    }
  }
  for (const [label, trace] of [['Request',data.request],['Reply',data.reply]]) {
    if (!trace) {
      lines.push(`${label}: ingen faktisk datagramöverföring`);
      continue;
    }
    lines.push(`${label}: ${trace.status} · IP ${trace.sourceIpv4} → ${trace.destinationIpv4}`
      + ` · TTL ${trace.initialTtl} → ${trace.finalTtl}`);
    for (const [i,step] of trace.steps.entries()) {
      lines.push(`  Hopp ${i+1}: ${step.node}/${step.outPort}, ${step.route.type} ${step.route.destination}`);
      lines.push(`    ARP: ${step.arp.status} · ${step.arp.resolvedMac || 'MAC ej upplöst'}`);
      lines.push(`    IPv4-kablar: ${step.ipv4Transmissions.map(t=>t.linkId).join(', ') || 'inga'}`);
      for (const d of [...(step.arp.requestVlanDrops || []),
          ...(step.arp.replyVlanDrops || []),...step.vlanDrops]) {
        lines.push(`    VLAN-drop: ${d.switch}/${d.port} ${d.reason}`);
      }
    }
  }
  lines.push('Svarstid: ej uppmätt. ICMP-fel visas endast när paketet faktiskt returnerat. Inga externa nät verifieras.');
  text = lines.join('\n');
  return {status: tone, text};
}

export function presentIPv4(ipv4Diagnostic) {
  let tone = '';
  let text = '';
  if (!ipv4Diagnostic) {
    text = 'Ingen aktuell IPv4-simulering. Paketet skickas bara på uttrycklig begäran.';
    return {status: tone, text};
  }
  if (ipv4Diagnostic.error) {
    tone = 'fail';
    text = `IPv4-simulering avvisad: ${ipv4Diagnostic.error}\nIngen leverans är verifierad.`;
    return {status: tone, text};
  }
  const r = ipv4Diagnostic;
  tone = r.status === 'DELIVERED' ? 'ok' : 'fail';
  const lines = [
    `IPv4-status: ${r.status}`,
    r.meaning,
    `IP ${r.sourceIpv4} → ${r.destinationIpv4}; TTL ${r.initialTtl} → ${r.finalTtl}`,
    r.receiver ? `Mottagande port: ${r.receiver.node}/${r.receiver.port}` : 'Ingen verifierad mottagande IPv4-port.',
  ];
  for (const [i, step] of r.steps.entries()) {
    lines.push(`Hopp ${i+1}: ${step.node}/${step.outPort}, TTL ${step.ttlSent}`);
    lines.push(`  ${step.route.type} ${step.route.destination}`
      + ` · next-hop ${step.nextHopIpv4}`
      + (step.route.routeId ? ` · ${step.route.routeId}` : ''));
    lines.push(`  ARP: ${step.arp.status}, ${step.arp.resolvedMac || 'MAC ej upplöst'}`);
    const a = [...step.arp.requestTransmissions, ...step.arp.replyTransmissions];
    lines.push(`  ARP på kablar: ${a.map(t=>t.linkId).join(', ') || 'inga'}`);
    lines.push(`  IPv4-ramar: ${step.ipv4Transmissions.length}`);
    for (const wire of step.ipv4Transmissions) lines.push(
      `    ${wire.linkId}: ${wire.from.node}/${wire.from.port} → ${wire.to.node}/${wire.to.port}`
      + (wire.vlanId == null ? '' : ` · VLAN ${wire.vlanId}`));
    const drops = [...(step.arp.requestVlanDrops || []),
      ...(step.arp.replyVlanDrops || []), ...step.vlanDrops];
    for (const drop of drops) lines.push(
      `  VLAN-drop: ${drop.switch}/${drop.port} ${drop.reason}`);
  }
  lines.push('Ingen ICMP Echo/Time Exceeded, IP-tjänst, returväg eller applikationsleverans simuleras.');
  text = lines.join('\n');
  return {status: tone, text};
}
