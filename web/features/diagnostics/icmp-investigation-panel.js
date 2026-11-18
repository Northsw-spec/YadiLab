import {$, el} from '../../ui/dom.js';

// Renders one ICMP panel from the canonical project and a copied session view.
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

export function renderIcmpInvestigationPanel(project, session) {
  const {id: icmpInvestigationId, state: icmpInvestigationState,
    busy: icmpInvestigationBusy, log: icmpInvestigationLog,
    verdict: icmpInvestigationVerdict, recovery: icmpInvestigationRecovery,
    error: icmpInvestigationError} = session;
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

