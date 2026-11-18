import {api} from '../../services/api.js';

// Each request receives a detached copy of the document captured at click time.
export function queryArp(snapshot, sourceNode, sourcePort, targetIpv4) {
  return api('/api/diagnostics/arp',
    {project: JSON.parse(snapshot), sourceNode, sourcePort, targetIpv4});
}

export function queryRoute(snapshot, nodeId, destinationIpv4) {
  return api('/api/routing/connected',
    {project: JSON.parse(snapshot), nodeId, destinationIpv4});
}

export function queryIPv4(snapshot, sourceNode, sourcePort, destinationIpv4, ttl) {
  return api('/api/ipv4/trace',
    {project: JSON.parse(snapshot), sourceNode, sourcePort, destinationIpv4, ttl});
}

export function queryPing(snapshot, sourceNode, sourcePort, destinationIpv4, ttl, identifier, sequence) {
  return api('/api/icmp/echo',
    {project: JSON.parse(snapshot), sourceNode, sourcePort, destinationIpv4, ttl, identifier, sequence});
}
