export async function api(path, payload = undefined) {
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
