import {api} from '../../services/api.js';

async function decodeUtf8(file) {
  // File.text() silently replaces malformed bytes.
  return new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer());
}

export function importKind(files) {
  if (files.every(file => file.name.endsWith('.csv'))) return 'csv';
  if (files.length === 1 && /\.(xlsx|ods)$/.test(files[0].name.toLowerCase())) {
    return files[0].name.toLowerCase().endsWith('.ods') ? 'ods' : 'xlsx';
  }
  if (files.length === 1 && ['.json', '.yadilab'].some(ext => files[0].name.toLowerCase().endsWith(ext))) {
    return 'project';
  }
  throw new Error('Välj en .json/.yadilab, en .xlsx/.ods med namngivna blad, eller explicita CSV-tabeller: Devices.csv, Interfaces.csv, Links.csv och eventuellt Zones.csv.');
}

export async function prepareImport(files, kind, projectName) {
  if (kind === 'csv') {
    if (files.length > 4) throw new Error('Välj högst fyra CSV-tabeller.');
    const sources = [];
    for (const file of files) {
      if (file.size > 8 * 1024 * 1024) throw new Error('CSV-fil är större än 8 MiB.');
      sources.push({name: file.name, text: await decodeUtf8(file)});
    }
    return {path: '/api/import/csv', payload: {projectName, files: sources}};
  }
  if (kind === 'xlsx' || kind === 'ods') {
    const workbook = files[0];
    if (workbook.size > 5 * 1024 * 1024) throw new Error('Arbetsboken är större än 5 MiB.');
    const bytes = new Uint8Array(await workbook.arrayBuffer());
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 32768) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
    }
    return {path: '/api/import/' + kind,
      payload: {filename: workbook.name, projectName, contentBase64: btoa(binary)}};
  }
  if (kind === 'project') {
    if (files[0].size > 8 * 1024 * 1024) throw new Error('Filen är större än 8 MiB.');
    return {path: '/api/validate', payload: JSON.parse(await decodeUtf8(files[0]))};
  }
  throw new Error('Okänt importformat.');
}

export function submitImport(prepared) {
  return api(prepared.path, prepared.payload);
}

export async function prepareProjectExport(serializedProject) {
  const validated = await api('/api/validate', JSON.parse(serializedProject));
  return {content: JSON.stringify(validated.project, null, 2) + '\n',
    type: 'application/json'};
}

export async function prepareSpreadsheetExport(serializedProject, format) {
  const reply = await api('/api/export/spreadsheet',
    {project: JSON.parse(serializedProject), format});
  if (reply.filename !== 'network-documentation.' + format ||
      typeof reply.contentBase64 !== 'string') {
    throw new Error('Servern returnerade felaktigt exportformat.');
  }
  const raw = atob(reply.contentBase64);
  const content = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) content[i] = raw.charCodeAt(i);
  const type = format === 'xlsx'
    ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    : 'application/vnd.oasis.opendocument.spreadsheet';
  return {content, type, filename: reply.filename};
}

export async function prepareInspection(file, delimiter) {
  if (!/\.(csv|xlsx|ods)$/i.test(file.name) || file.size > 5 * 1024 * 1024) {
    throw new Error('Välj en CSV-, XLSX- eller ODS-fil på högst 5 MiB.');
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 32768) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
  }
  const payload = {filename: file.name, contentBase64: btoa(binary)};
  if (/\.csv$/i.test(file.name)) {
    if (delimiter !== ',' && delimiter !== ';') throw new Error('Välj komma eller semikolon för CSV.');
    payload.csvDelimiter = delimiter;
  }
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const sha256 = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
  return {payload, sha256};
}

export function submitInspection(payload) {
  return api('/api/import/inspect', payload);
}

export function submitInspectionPage(payload, tableId, fromRow) {
  return api('/api/import/inspect-page', {...payload, tableId, fromRow});
}

export function prepareSourceBundle(sources) {
  if (!Array.isArray(sources) || !sources.length || sources.length > 8) {
    throw new Error('Källpaketet kräver 1–8 verifierade originalfiler.');
  }
  return {sourceBundleVersion:'1', sources:sources.map((entry, index) => ({
    sourceId:`src-${index + 1}`, filename:entry.payload.filename,
    kind:entry.inspection.source.kind, sha256:entry.sha256,
    csvDelimiter:entry.payload.csvDelimiter ?? null,
    contentBase64:entry.payload.contentBase64,
  }))};
}

export async function readSourceBundle(bundle) {
  if (!bundle || typeof bundle !== 'object' || Array.isArray(bundle) ||
      Object.keys(bundle).sort().join(',') !== 'sourceBundleVersion,sources' ||
      bundle.sourceBundleVersion !== '1' || !Array.isArray(bundle.sources) ||
      bundle.sources.length < 1 || bundle.sources.length > 8) {
    throw new Error('Ogiltigt källpaketsformat.');
  }
  let total = 0;
  const result = [];
  for (const [index, item] of bundle.sources.entries()) {
    if (!item || typeof item !== 'object' || Array.isArray(item) ||
        Object.keys(item).sort().join(',') !==
          'contentBase64,csvDelimiter,filename,kind,sha256,sourceId' ||
        item.sourceId !== `src-${index + 1}` ||
        typeof item.filename !== 'string' || !item.filename ||
        !['csv','xlsx','ods'].includes(item.kind) ||
        !item.filename.toLowerCase().endsWith(`.${item.kind}`) ||
        !/^[0-9a-f]{64}$/.test(item.sha256) ||
        (item.kind === 'csv' ? ![',',';'].includes(item.csvDelimiter) : item.csvDelimiter !== null) ||
        typeof item.contentBase64 !== 'string' ||
        !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(item.contentBase64)) {
      throw new Error('Felaktig eller duplicerad källpost i paketet.');
    }
    let raw;
    try { raw = atob(item.contentBase64); }
    catch { throw new Error('Källpaketet innehåller ogiltig base64.'); }
    if (btoa(raw) !== item.contentBase64) throw new Error('Källpaketet innehåller icke-kanonisk base64.');
    total += raw.length;
    if (total > 4 * 1024 * 1024) throw new Error('Källpaketet överstiger 4 MiB originalbytes.');
    const bytes = Uint8Array.from(raw, char => char.charCodeAt(0));
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const actual = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2,'0')).join('');
    if (actual !== item.sha256) throw new Error('Källpaketets SHA-256 matchar inte originalbytes.');
    const source = {sourceId:item.sourceId, filename:item.filename,
      contentBase64:item.contentBase64};
    if (item.kind === 'csv') source.csvDelimiter = item.csvDelimiter;
    result.push(source);
  }
  return result;
}
