export async function api(path, payload = undefined) {
  // Protocol requests carry only the network projection. The full project
  // remains authoritative for editing, revisions, Save/Open and history.
  const protocol = /^\/api\/(?:trace|troubleshoot\/|routing\/|ipv4\/|icmp\/|dhcp\/|simulation\/|diagnostics\/)/.test(path);
  if (protocol && payload?.project?.schemaVersion === '1.4') {
    const {name, zones, nodes, links} = payload.project;
    payload = {...payload, project: {schemaVersion: '1.3', name, zones, nodes, links}};
  }
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
