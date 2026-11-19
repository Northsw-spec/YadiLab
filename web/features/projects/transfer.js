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
