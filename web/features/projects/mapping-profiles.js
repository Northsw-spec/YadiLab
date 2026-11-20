// A profile contains mapping rules only. Source identities and selected rows
// belong to the current inspection and are never serialized here.
const fields = {
  device_inventory: ['node.id','node.label','node.kind','node.zoneId'],
  zone_inventory: ['zone.id','zone.label'],
  interface_inventory: ['port.nodeId','port.id','port.name','port.enabled','port.vlanMode',
    'port.accessVlan','port.allowedVlans','port.ipv4'],
  ip_plan: ['ip.nodeId','ip.portId','ip.ipv4'],
  static_route_register: ['route.nodeId','route.id','route.destination','route.nextHop','route.outPort'],
  cable_register: ['link.id','link.aNode','link.aPort','link.bNode','link.bPort','link.enabled'],
  documentation_only: [],
};
const identity = new Set(['node.id','zone.id','port.nodeId','port.id','ip.nodeId','ip.portId',
  'route.nodeId','route.id','route.outPort','link.id','link.aNode','link.aPort','link.bNode','link.bPort']);
const transformations = {
  'port.accessVlan': ['parse_vlan_integer', null],
  'port.allowedVlans': ['split_vlan_integer_list', ','],
};
const dangerous = new Set(['__proto__','constructor','prototype']);
const exact = (value, keys, where) => {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join(',') !== [...keys].sort().join(',') ||
      Object.keys(value).some(key => dangerous.has(key)))
    throw new Error(`Ogiltiga fält i ${where}.`);
};
const bounded = (value, maximum, where) => {
  if (!Array.isArray(value) || value.length > maximum) throw new Error(`Ogiltig lista i ${where}.`);
};
const columnNumber = label => {
  if (typeof label !== 'string' || !/^[A-Z]{1,2}$/.test(label))
    throw new Error(`Ogiltig kolumn: ${String(label)}.`);
  const number = [...label].reduce((n,char) => n*26+char.charCodeAt(0)-64, 0);
  if (number > 256) throw new Error(`Kolumnen ${label} är utanför IV.`);
  return number;
};
const columnLabel = index => {
  let number=index+1, label='';
  while (number) { number--; label=String.fromCharCode(65+number%26)+label; number=Math.floor(number/26); }
  return label;
};
const typedConstant = (field, item) => {
  exact(item, ['type','value'], `constant ${field}`);
  const {type, value} = item;
  if (type === 'text' && typeof value === 'string' &&
      !['port.accessVlan','port.allowedVlans','port.enabled','link.enabled'].includes(field)) return;
  if (type === 'boolean' && typeof value === 'boolean' &&
      ['port.enabled','link.enabled'].includes(field)) return;
  if (type === 'null' && value === null && field === 'node.zoneId') return;
  if (type === 'integer' && field === 'port.accessVlan' && Number.isInteger(value) &&
      value >= 1 && value <= 4094) return;
  if (type === 'integer_list' && field === 'port.allowedVlans' && Array.isArray(value) &&
      value.length >= 1 && value.length <= 64 && value.every(v => Number.isInteger(v) && v >= 1 && v <= 4094) &&
      new Set(value).size === value.length) return;
  throw new Error(`Fel typ i constant ${field}.`);
};

export function validateMappingProfile(profile) {
  exact(profile, ['profileVersion','views'], 'profil');
  if (profile.profileVersion !== '1') throw new Error('Okänd profilversion.');
  bounded(profile.views, 64, 'views');
  if (!profile.views.length) throw new Error('Profilen saknar MappingViews.');
  for (const [index, view] of profile.views.entries()) {
    const where = `profilvy ${index+1}`;
    exact(view, ['role','headerRow','expectedHeaders','columns','valueMaps','constants','transformations','label'], where);
    if (typeof view.role !== 'string' || !Object.hasOwn(fields, view.role))
      throw new Error(`Ogiltig roll i ${where}.`);
    if (view.headerRow !== null && (!Number.isInteger(view.headerRow) || view.headerRow < 1 || view.headerRow > 5001))
      throw new Error(`Ogiltig headerRow i ${where}.`);
    bounded(view.expectedHeaders, 256, `${where}.expectedHeaders`);
    if (view.expectedHeaders.some(item => typeof item !== 'string') ||
        (view.headerRow === null && view.expectedHeaders.length))
      throw new Error(`Ogiltiga expectedHeaders i ${where}.`);
    if (typeof view.label !== 'string' || view.label.length > 240)
      throw new Error(`Ogiltig label i ${where}.`);
    for (const key of ['columns','valueMaps','constants']) {
      if (!view[key] || typeof view[key] !== 'object' || Array.isArray(view[key]) ||
          Object.keys(view[key]).some(field => dangerous.has(field) || !fields[view.role].includes(field)))
        throw new Error(`Otillåtet målfält i ${where}.${key}.`);
    }
    for (const [field, labels] of Object.entries(view.columns)) {
      bounded(labels, 64, field);
      if (!labels.length || new Set(labels).size !== labels.length) throw new Error(`Duplicerad eller tom kolumn i ${field}.`);
      labels.forEach(columnNumber);
    }
    for (const [field, mapping] of Object.entries(view.valueMaps)) {
      if (!Object.hasOwn(view.columns, field) || !mapping || typeof mapping !== 'object' ||
          Array.isArray(mapping) || !Object.keys(mapping).length ||
          Object.entries(mapping).some(([key,value]) => dangerous.has(key) || typeof value !== 'string' ||
            (['port.enabled','link.enabled'].includes(field) && !['true','false'].includes(value))))
        throw new Error(`Ogiltig valueMap för ${field}.`);
    }
    for (const [field, item] of Object.entries(view.constants)) {
      if (identity.has(field) || Object.hasOwn(view.columns, field))
        throw new Error(`Otillåten constant för ${field}.`);
      typedConstant(field, item);
    }
    bounded(view.transformations, 64, `${where}.transformations`);
    const seen = new Set();
    for (const item of view.transformations) {
      exact(item, ['targetField','operation','delimiter'], 'transformation');
      const expected = Object.hasOwn(transformations, item.targetField) ? transformations[item.targetField] : null;
      if (!expected || item.operation !== expected[0] || item.delimiter !== expected[1] ||
          !Object.hasOwn(view.columns, item.targetField) || view.columns[item.targetField].length !== 1 ||
          Object.hasOwn(view.valueMaps, item.targetField) || seen.has(item.targetField))
        throw new Error(`Ogiltig eller duplicerad transformation för ${String(item.targetField)}.`);
      seen.add(item.targetField);
    }
  }
  if (new TextEncoder().encode(JSON.stringify(profile)).length > 256*1024)
    throw new Error('Profilen överstiger 256 KiB.');
  return profile;
}

export function exportMappingProfile(mappingViews, selectedTransformations) {
  bounded(mappingViews, 64, 'MappingViews');
  bounded(selectedTransformations, 64, 'transformationer');
  const ids = new Set(mappingViews.map(view => view.viewId));
  if (ids.size !== mappingViews.length || selectedTransformations.some(item => !ids.has(item?.viewId)))
    throw new Error('Transformationen saknar aktuell MappingView.');
  const views = mappingViews.map(view => ({
    role:view.role, headerRow:view.headerRow, expectedHeaders:view.expectedHeaders,
    columns:view.columns, valueMaps:view.valueMaps, constants:view.constants,
    transformations:selectedTransformations.filter(item => item.viewId === view.viewId)
      .map(({targetField,operation,delimiter}) => ({targetField,operation,delimiter}))
      .sort((a,b) => a.targetField.localeCompare(b.targetField)), label:view.label,
  }));
  return validateMappingProfile({profileVersion:'1',views});
}

export function bindMappingProfile(profile, selections, sources) {
  validateMappingProfile(profile);
  bounded(selections, 64, 'bindningar');
  if (selections.length !== profile.views.length) throw new Error('Alla profilvyer behöver en tabellbindning.');
  return profile.views.map((view,index) => {
    const choice = selections[index];
    exact(choice, ['sourceIndex','tableId'], 'tabellbindning');
    const source = Number.isInteger(choice.sourceIndex) && sources[choice.sourceIndex];
    const table = source?.inspection?.tables?.find(item => item.tableId === choice.tableId);
    if (!table) throw new Error(`Välj en inspekterad tabell för profilvy ${index+1}.`);
    const header = view.headerRow === null ? null : table.previewRows.find(row => row.row === view.headerRow);
    if (view.headerRow !== null && !header)
      throw new Error(`Rubrikrad ${view.headerRow} saknas i profilvy ${index+1}; visa den i originalgranskningen.`);
    const actual = header?.cells.map(cell => cell.value) ?? [];
    if (JSON.stringify(actual) !== JSON.stringify(view.expectedHeaders)) {
      const position = actual.findIndex((value,i) => value !== view.expectedHeaders[i]);
      const n = position >= 0 ? position : Math.min(actual.length, view.expectedHeaders.length);
      const letter = columnLabel(n);
      throw new Error(`Profilen förväntar sig kolumn ${letter}: ${view.expectedHeaders[n] ?? '(saknas)'}, men den aktuella källan innehåller: ${actual[n] ?? '(saknas)'}.`);
    }
    for (const labels of Object.values(view.columns)) for (const label of labels) {
      if (columnNumber(label) > table.columnCount)
        throw new Error(`Kolumn ${label} finns inte i profilvy ${index+1} i den aktuella tabellen.`);
    }
    return {table:`${choice.sourceIndex}:${choice.tableId}`, role:view.role,
      header:view.headerRow === null ? '' : String(view.headerRow), selected:'',
      columns:Object.fromEntries(Object.entries(view.columns).map(([field,labels]) => [field,labels.join(',')])),
      maps:JSON.stringify(view.valueMaps), constants:JSON.stringify(view.constants), label:view.label,
      accessTransform:view.transformations.find(item => item.targetField === 'port.accessVlan')?.operation ?? '',
      trunkTransform:view.transformations.find(item => item.targetField === 'port.allowedVlans')?.operation ?? ''};
  });
}
