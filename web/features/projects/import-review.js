import {$, el} from '../../ui/dom.js';
import {api} from '../../services/api.js';
import {prepareInspection, submitInspection, submitInspectionPage, prepareSourceBundle, readSourceBundle} from './transfer.js';
import {validateMappingProfile, exportMappingProfile, bindMappingProfile} from './mapping-profiles.js';

const fields = {
  device_inventory:['node.id','node.label','node.kind','node.zoneId'],
  zone_inventory:['zone.id','zone.label'],
  interface_inventory:['port.nodeId','port.id','port.name','port.enabled','port.vlanMode','port.accessVlan','port.allowedVlans','port.ipv4'],
  ip_plan:['ip.nodeId','ip.portId','ip.ipv4'],
  static_route_register:['route.nodeId','route.id','route.destination','route.nextHop','route.outPort'],
  cable_register:['link.id','link.aNode','link.aPort','link.bNode','link.bPort','link.enabled'],
  documentation_only:[],
};
export const letter = index => { let value=index+1, result=''; while(value) { result=String.fromCharCode(65+(value-1)%26)+result; value=Math.floor((value-1)/26); } return result; };
export const displayKey = unit => {
  if (!['port','ipBinding','staticRoute'].includes(unit.kind)) return unit.targetKey;
  try { const parts=JSON.parse(unit.targetKey); return Array.isArray(parts) ? parts.join('/') : unit.targetKey; }
  catch { return unit.targetKey; }
};
const diagnosticHelp = {
  FIELD_CONFLICT:'Motstridiga uttryckliga källvärden. Kontrollera de angivna originalcellerna och korrigera mappningen eller källdokumentet.',
  MISSING_REQUIRED_FIELD:'Ett obligatoriskt fält saknas. Kontrollera kolumnmappning och uttryckliga radbeslut.',
  UNDECLARED_PORT:'Porten är inte deklarerad i de granskade uppgifterna. Kontrollera portregister och källreferenser.',
  UNDECLARED_NODE:'Noden är inte deklarerad i de granskade uppgifterna. Kontrollera enhetsregistret.',
  UNAVAILABLE_LINK_ENDPOINT:'En kabelände är inte tillgänglig i den valda planen. Granska porten och beroendena.',
  UNAVAILABLE_ROUTE_DEPENDENCY:'Ett nödvändigt routeberoende saknas i den valda planen.',
  NUMERIC_ID_REQUIRES_DECISION:'Ett numeriskt ID kräver ett uttryckligt radunikt textbeslut.',
  SELECTED_UNIT_NOT_ACTIONABLE:'Denna enhet kan inte väljas förrän blockerande fel har rättats.',
};

// Validate a whole page before either the displayed rows or selectable source rows change.
export function validateReviewPage(page, source, table, fromRow) {
  const bad = () => { throw new Error('Källsidans identitet, celler eller radnummer stämmer inte.'); };
  if (!page || Object.keys(page).sort().join(',') !== 'inspectionVersion,nextRow,rows,source,tableId' ||
      !page.source || Object.keys(page.source).sort().join(',') !== 'filename,kind,sha256' ||
      page.inspectionVersion !== '1' ||
      page.source?.sha256 !== source.sha256 ||
      page.source?.filename !== source.payload.filename ||
      page.source?.kind !== source.inspection.source.kind ||
      page.tableId !== table.tableId || !Array.isArray(page.rows) ||
      page.rows.length > 25 || !Number.isInteger(fromRow) || fromRow < 1 || fromRow > 5001 ||
      !Array.isArray(table.previewRows)) bad();
  const seen = new Set(table.previewRows.map(item => item.row));
  let previous = fromRow - 1;
  for (const record of page.rows) {
    if (!record || Object.keys(record).sort().join(',') !== 'cells,row' ||
        !Number.isInteger(record.row) || record.row <= previous || record.row > 5001 ||
        seen.has(record.row) || !Array.isArray(record.cells) ||
        !record.cells.length || record.cells.length > table.columnCount) bad();
    previous = record.row;
    const addresses = new Set();
    let lastColumn = 0;
    for (const cell of record.cells) {
      const match = /^([A-Z]{1,2})([1-9][0-9]*)$/.exec(cell?.address);
      let column = 0;
      if (match) for (const letter of match[1]) column = column * 26 + letter.charCodeAt(0) - 64;
      if (!cell || Object.keys(cell).sort().join(',') !== 'address,type,value' ||
          !match || Number(match[2]) !== record.row || column <= lastColumn ||
          column > table.columnCount || !['text','number','boolean'].includes(cell.type) ||
          typeof cell.value !== 'string' || addresses.has(cell.address)) bad();
      addresses.add(cell.address); lastColumn = column;
    }
  }
  if (page.nextRow !== null && (!Number.isInteger(page.nextRow) ||
      page.nextRow <= previous || page.nextRow > 5001 || !page.rows.length)) bad();
  if (!page.rows.length && page.nextRow !== null) bad();
  return page;
}

// Review state is transient. The workspace controller in app.js alone owns the project.
export function createImportReview({context, current, getProject, replaceProject, confirmDiscard, download, notify, getPreviewGeneration}) {
  const dialog = $('external-dialog');
  let sources = [], fileChoices = [], views = [], plan = null, candidate = null, planToken = null, candidateToken = null, attached = false;
  let revision = 0, statusGeneration = 0, sourceGeneration = 0, navigationGeneration = 0;
  let pendingProfile = null, pendingToken = null;
  function clearPendingProfile() {
    pendingProfile = null; pendingToken = null;
    $('external-profile-bindings').replaceChildren();
    $('external-profile-confirm').disabled = true;
  }
  const note = message => { $('external-plan-result').textContent = message; };
  const stale = () => notify('Granskningen ändrades under anropet. Upprepa granskningen.', true);
  const guard = () => ({context: context(), revision, sourceGeneration,
    hashes: sources.map(s => s.sha256).join(','),
    preview: getPreviewGeneration(), choices: JSON.stringify(views.map(v => v.data)),
    fingerprint: plan?.fingerprint ?? null});
  const valid = token => current(token.context) && token.revision === revision &&
    token.sourceGeneration === sourceGeneration &&
    token.hashes === sources.map(s => s.sha256).join(',') &&
    token.preview === getPreviewGeneration() &&
    token.choices === JSON.stringify(views.map(v => v.data)) &&
    token.fingerprint === (plan?.fingerprint ?? null);
  function invalidate() {
    clearPendingProfile();
    revision++; plan = null; candidate = null; planToken = null; candidateToken = null;
    $('external-candidate-button').disabled = true;
    $('external-apply').disabled = true;
    $('external-candidate-result').replaceChildren();
    $('external-plan-result').replaceChildren();
  }
  function sourceRequest() { return sources.map((s,i) => ({sourceId:`src-${i+1}`, ...s.payload})); }
  function setStatus(message) {
    $('external-status').textContent = message;
    $('import-evidence-status').textContent = message;
  }
  function renderHistory(project, manifestStatus, baseline) {
    const target=$('external-history'); target.replaceChildren();
    const evidence=project.importEvidence;
    if(!evidence)return;
    target.append(el('h4',{},'Historisk proveniens'),
      el('p',{},`Manifestets integritet: ${manifestStatus}`),
      el('p',{},`Originalkällor: ${attached ? 'SOURCE_VERIFIED' : 'Källfil ej ansluten; ursprungsceller kan inte kontrolleras.'}`),
      el('p',{},`Projekt jämfört med importbaslinje: ${baseline}`),
      el('p',{},`Importens planfingerprint: ${evidence.planFingerprint}`),
      el('p',{},'Projektfilen innehåller historiskt kvitto, inte originalarbetsböcker. Återanslut alla originalfiler eller ett separat källpaket för cellkontroll.'));
    const files=el('details',{},el('summary',{},`${evidence.sources.length} historiska originalfiler`));
    for(const item of evidence.sources) files.append(el('p',{},`${item.sourceId} · ${item.filename} · SHA-256 ${item.sha256}`));
    target.append(files);
    const changes=el('details',{},el('summary',{},`${evidence.acceptedChanges.length} accepterade ändringar och deras ursprung`));
    for(const change of evidence.acceptedChanges) {
      const section=el('section',{className:'review-diagnostic'},
        el('strong',{},`${change.targetKind} · ${displayKey({kind:change.targetKind,targetKey:change.targetKey})}`));
      for(const [field,origins] of Object.entries(change.fieldOrigins)) {
        const line=el('p',{},`${field}: `);
        for(const origin of origins) {
          if(origin.kind==='source_cell') line.append(sourceLink(origin));
          else line.append(el('span',{},`${origin.kind} ${origin.decisionId || ''} `));
        }
        section.append(line);
      }
      changes.append(section);
    }
    target.append(changes);
  }
  async function refreshStatus() {
    const generation = ++statusGeneration, ctx = context();
    const project = getProject();
    if (project.schemaVersion !== '1.4') {
      attached = false; $('external-history').replaceChildren(); setStatus('Inget historiskt importkvitto.'); return;
    }
    try {
      const result = await api('/api/import/evidence-status', {project});
      if (generation !== statusGeneration || !current(ctx)) return;
      setStatus(`${result.manifestStatus} · ${result.baselineStatus} · ${attached ? 'SOURCE_VERIFIED (ansluten historisk källa)' : 'Källfil ej ansluten; ursprungsceller kan inte kontrolleras.'}`);
      renderHistory(project,result.manifestStatus,result.baselineStatus);
    } catch (error) {
      if (generation !== statusGeneration || !current(ctx)) return;
      attached = false; setStatus(`Historiskt importkvitto kunde inte valideras: ${error.message}`);
      $('external-history').replaceChildren();
    }
  }
  function onWorkspace() {
    invalidate(); sources = []; fileChoices = []; views = []; attached = false; ++sourceGeneration; ++navigationGeneration;
    $('external-views').replaceChildren(); $('external-sources').replaceChildren();
    $('external-source-focus').replaceChildren();
    $('external-row-values').value='[]'; $('external-exclusions').value='[]'; renderDecisions();
    $('external-file-choices').replaceChildren(); $('external-inspect-files').disabled = true;
    $('external-verification').replaceChildren();
    $('external-add-view').disabled = true; $('external-plan-button').disabled = true;
    $('external-bundle-export').disabled = true;
    $('external-profile-export').disabled = true;
    $('external-profile-status').textContent='';
    ++statusGeneration;
    queueMicrotask(refreshStatus);
  }
  function onEdit() { invalidate(); refreshStatus(); }
  const showError = error => notify(error.message || String(error), true);
  function findTable(value) {
    const [index,id]=value.split(':');
    return sources[Number(index)]?.inspection.tables.find(table=>table.tableId===id);
  }
  function headerFor(index, table) {
    const entry=views.find(view=>view.data?.table===`${index}:${table.tableId}` && view.data.header);
    return table.previewRows.find(row=>row.row===Number(entry?.data.header));
  }
  function renderSources(highlight=null) {
    $('external-sources').replaceChildren(...sources.map((source,index) => {
      const section = el('section', {className:'source-review'}, el('h4', {}, `${index+1}. ${source.payload.filename}`),
        el('p',{},`${source.inspection.source.kind.toUpperCase()} · ${source.payload.csvDelimiter ? `CSV-avskiljare ${source.payload.csvDelimiter} · ` : ''}${source.inspection.tables.length} blad · ${source.inspection.tables.reduce((sum,t)=>sum+t.populatedRowCount,0)} befolkade rader · SHA-256 ${source.sha256}`));
      for (const table of source.inspection.tables) {
        const wrapper=el('div',{className:'source-table-scroll'});
        const grid=el('table',{className:'source-grid'});
        const head=el('thead',{}), body=el('tbody',{});
        const draw = items => {
          const headers=headerFor(index,table);
          head.replaceChildren(el('tr',{},el('th',{},'Rad'),...Array.from({length:table.columnCount},(_,i)=>{
            const col=letter(i), cell=headers?.cells.find(c=>c.address===`${col}${headers.row}`);
            return el('th',{},`${col}${cell ? ` – ${cell.value}` : ''}`);
          })));
          for (const row of items) {
            const cells=new Map(row.cells.map(cell=>[cell.address,cell]));
            const tr=el('tr',{'data-row':row.row});
            tr.append(el('th',{},String(row.row)));
            for(let i=0;i<table.columnCount;i++) {
              const cell=cells.get(`${letter(i)}${row.row}`);
              const td=el('td',{'data-address':cell?.address || ''});
              if(cell) td.append(el('span',{},cell.value),el('small',{},`${cell.address} · ${cell.type}`));
              if(highlight?.sourceId===`src-${index+1}` && highlight.tableId===table.tableId && highlight.address===cell?.address)
                td.classList.add('source-highlight');
              tr.append(td);
            }
            body.append(tr);
          }
        };
        grid.append(head,body); wrapper.append(grid);
        draw(table.previewRows);
        const count=el('p',{className:'muted'},`Förhandsvisade ${table.previewRows.length} av ${table.populatedRowCount} befolkade källrader`);
        const next = el('button', {type:'button'}, 'Visa fler originalrader');
        let from = table.previewRows.at(-1)?.row + 1 || 1;
        next.disabled = table.previewRows.length >= table.populatedRowCount;
        next.addEventListener('click', async () => {
          if (next.disabled) return;
          const token = guard(), generation=sourceGeneration;
          next.disabled = true;
          try {
            const page = await submitInspectionPage(source.payload, table.tableId, from);
            if (!valid(token) || generation!==sourceGeneration) return stale();
            validateReviewPage(page, source, table, from);
            table.previewRows.push(...page.rows);
            draw(page.rows); from = page.nextRow;
            count.textContent=`Förhandsvisade ${table.previewRows.length} av ${table.populatedRowCount} befolkade källrader`;
            renderViews();
          } catch (error) { if (valid(token)) showError(error); }
          finally { if (next.isConnected) next.disabled = from===null; }
        });
        section.append(el('h5', {}, `${table.name} · ${table.columnCount} kolumner`),wrapper,count,next);
      }
      return section;
    }));
    $('external-add-view').disabled = !sources.length;
    $('external-plan-button').disabled = !sources.length;
    $('external-bundle-export').disabled = !sources.length;
  }
  function discardInspections() {
    ++sourceGeneration; ++navigationGeneration; sources = []; views = []; attached = false;
    $('external-source-focus').replaceChildren();
    $('external-row-values').value='[]'; $('external-exclusions').value='[]';
    refreshStatus(); invalidate(); renderViews(); renderSources();
    $('external-profile-status').textContent='Ny källa vald; tidigare profilbindning är ogiltig.';
  }
  function renderFileChoices() {
    const target = $('external-file-choices'); target.replaceChildren();
    fileChoices.forEach((choice, index) => {
      if (!/\.csv$/i.test(choice.file.name)) {
        target.append(el('p', {}, `${index+1}. ${choice.file.name} · arbetsbok, ingen CSV-avskiljare`));
        return;
      }
      const select = el('select', {}, el('option', {value:''}, 'Välj avskiljare'),
        el('option', {value:','}, 'Komma (,)'), el('option', {value:';'}, 'Semikolon (;)'));
      select.value = choice.delimiter;
      select.addEventListener('change', () => {
        choice.delimiter = select.value;
        discardInspections();
        $('external-inspect-files').disabled = fileChoices.some(item =>
          /\.csv$/i.test(item.file.name) && ![',',';'].includes(item.delimiter));
      });
      target.append(el('label', {}, `${index+1}. ${choice.file.name} · CSV-avskiljare `, select));
    });
    $('external-inspect-files').disabled = !fileChoices.length || fileChoices.some(item =>
      /\.csv$/i.test(item.file.name) && ![',',';'].includes(item.delimiter));
  }
  async function loadFiles(choices) {
    if (!choices.length || choices.length > 8 || choices.some(item =>
        /\.csv$/i.test(item.file.name) && ![',',';'].includes(item.delimiter)))
      throw new Error('Välj 1–8 originalfiler och avskiljare för varje CSV-fil.');
    const generation = ++sourceGeneration, token = guard();
    sources = []; views = []; attached = false; refreshStatus(); invalidate(); $('external-views').replaceChildren();
    $('external-sources').textContent = 'Läser originalbytes och inspekterar tabeller…';
    let total = 0, loaded = [];
    for (const {file, delimiter} of choices) {
      total += file.size;
      if (total > 4 * 1024 * 1024) throw new Error('Högst 4 MiB sammanlagda originalbytes.');
      const prepared = await prepareInspection(file, delimiter);
      if (generation !== sourceGeneration || !current(token.context)) return stale();
      const inspection = await submitInspection(prepared.payload);
      if (generation !== sourceGeneration || !current(token.context)) return stale();
      if (inspection.inspectionVersion !== '1' ||
          inspection.source?.sha256 !== prepared.sha256 ||
          inspection.source?.filename !== file.name ||
          inspection.source?.kind !== file.name.toLowerCase().split('.').at(-1))
        throw new Error('Inspektionens filidentitet stämmer inte med originalfilen.');
      loaded.push({...prepared, inspection});
    }
    if (generation !== sourceGeneration || !current(token.context)) return stale();
    sources = loaded; invalidate(); renderSources();
  }
  function tableOptions() {
    return sources.flatMap((source,index) => source.inspection.tables.map(table =>
      { const option = el('option',{value:`${index}:${table.tableId}`},`${source.payload.filename} / ${table.name}`); return option; }));
  }
  function renderViews() {
    const container = $('external-views'); container.replaceChildren();
    views.forEach((view,index) => {
      const box = el('fieldset', {}, el('legend', {}, `MappingView ${index+1}`));
      const table = el('select',{},...tableOptions());
      const role = el('select',{},el('option',{value:'device_inventory'},'device_inventory'),
        el('option',{value:'zone_inventory'},'zone_inventory'),
        el('option',{value:'interface_inventory'},'interface_inventory'),
        el('option',{value:'ip_plan'},'ip_plan'),
        el('option',{value:'static_route_register'},'static_route_register'),
        el('option',{value:'cable_register'},'cable_register'),
        el('option',{value:'documentation_only'},'documentation_only'));
      const header = el('input',{type:'number',min:'1',placeholder:'Rubrikrad, tomt = ingen'});
      const selected = el('input',{type:'text',placeholder:'Valda originalrader, t.ex. 2,3'});
      const columns = {}, columnLabels = {};
      for (const field of Object.values(fields).flat()) {
        columns[field] = el('input',{type:'text',placeholder:'Kolumnbokstav, t.ex. A'});
        columnLabels[field] = el('label',{},field,columns[field]);
        box.append(columnLabels[field]);
      }
      const maps = el('textarea',{rows:'2',placeholder:'valueMaps JSON, t.ex. {"node.kind":{"Server":"host"}}'},'{}');
      const accessTransform = el('select',{},el('option',{value:''},'Ingen'),
        el('option',{value:'parse_vlan_integer'},'parse_vlan_integer → heltal'));
      const trunkTransform = el('select',{},el('option',{value:''},'Ingen'),
        el('option',{value:'split_vlan_integer_list'},'split_vlan_integer_list → heltalslista'));
      const constants = el('textarea',{rows:'2',placeholder:'constants JSON'},'{}');
      const label = el('input',{type:'text',placeholder:'Beskriv denna vy'});
      const remove = el('button',{type:'button'},'Ta bort vy');
      const controls = [table,role,header,selected,...Object.values(columns),accessTransform,trunkTransform,maps,constants,label];
      const update = () => { view.data = {table:table.value,role:role.value,header:header.value,
        selected:selected.value, columns:Object.fromEntries(Object.entries(columns).map(([key,value])=>[key,value.value])),
        maps:maps.value,constants:constants.value,label:label.value,
        accessTransform:accessTransform.value,trunkTransform:trunkTransform.value}; invalidate(); };
      box.prepend(el('label',{},'Källa och blad',table),el('label',{},'Roll',role),
        el('label',{},'Rubrikrad',header),el('label',{},'Valda originalrader',selected));
      box.append(el('details',{},el('summary',{},'Avancerad JSON för ValueMaps och Constants'),
          el('label',{},'valueMaps',maps),el('label',{},'constants',constants)),
        el('label',{},'port.accessVlan: källtext → JSON-heltal',accessTransform),
        el('label',{},'port.allowedVlans: källtext → JSON-heltalslista',trunkTransform),
        el('label',{},'Vynamn',label),remove);
      const visual=el('div',{className:'review-decision-controls'});
      const mapField=el('select',{}), mapFrom=el('input',{type:'text',placeholder:'Originalvärde'}),
        mapTo=el('input',{type:'text',placeholder:'Uttryckligt målvärde'}),
        constantField=el('select',{}), constantType=el('select',{},
          ...['text','boolean','null','integer','integer_list'].map(type=>el('option',{value:type},type))),
        constantValue=el('input',{type:'text',placeholder:'Uttryckligt konstantvärde'});
      const decisionsList=el('div',{});
      const identities=new Set(['node.id','zone.id','port.nodeId','port.id','ip.nodeId','ip.portId',
        'route.nodeId','route.id','route.outPort','link.id','link.aNode','link.aPort','link.bNode','link.bPort']);
      const drawDecisions=()=>{
        let mapData={}, constantData={};
        try { mapData=JSON.parse(maps.value); constantData=JSON.parse(constants.value); }
        catch { decisionsList.textContent='Avancerad JSON är ogiltig.'; return; }
        const previousMap=mapField.value, previousConstant=constantField.value;
        mapField.replaceChildren(...(fields[role.value] || []).filter(field=>columns[field].value.trim())
          .map(field=>el('option',{value:field},field)));
        constantField.replaceChildren(...(fields[role.value] || []).filter(field=>!identities.has(field) && !columns[field].value.trim())
          .map(field=>el('option',{value:field},field)));
        if(previousMap)mapField.value=previousMap;
        if(previousConstant)constantField.value=previousConstant;
        decisionsList.replaceChildren();
        for(const [field,entries] of Object.entries(mapData)) for(const [before,after] of Object.entries(entries)) {
          const removeMap=el('button',{type:'button'},'Ta bort');
          removeMap.addEventListener('click',()=>{delete mapData[field][before]; if(!Object.keys(mapData[field]).length)delete mapData[field];
            maps.value=JSON.stringify(mapData); update(); drawDecisions();});
          decisionsList.append(el('p',{},`ValueMap ${field}: ${before} → ${after} `,removeMap));
        }
        for(const [field,item] of Object.entries(constantData)) {
          const removeConstant=el('button',{type:'button'},'Ta bort');
          removeConstant.addEventListener('click',()=>{delete constantData[field]; constants.value=JSON.stringify(constantData);update();drawDecisions();});
          decisionsList.append(el('p',{},`Constant ${field}: ${item.type} · ${JSON.stringify(item.value)} `,removeConstant));
        }
      };
      const addMap=el('button',{type:'button'},'Lägg till ValueMap');
      addMap.addEventListener('click',()=>{
        if(!mapField.value || !mapFrom.value)return showError(new Error('Välj ett mappat målfält och ett originalvärde.'));
        try {const data=JSON.parse(maps.value); data[mapField.value] ??= {}; data[mapField.value][mapFrom.value]=mapTo.value;
          maps.value=JSON.stringify(data);update();drawDecisions();}
        catch(error){showError(error);}
      });
      const addConstant=el('button',{type:'button'},'Lägg till Constant');
      addConstant.addEventListener('click',()=>{
        if(!constantField.value)return showError(new Error('Välj ett tillåtet målfält.'));
        try {let value=constantValue.value;
          if(constantType.value==='boolean') {if(!['true','false'].includes(value))throw new Error('Boolean ska vara true eller false.');value=value==='true';}
          if(constantType.value==='null')value=null;
          if(constantType.value==='integer') {if(!/^[0-9]+$/.test(value))throw new Error('Ange ett heltal.');value=Number(value);}
          if(constantType.value==='integer_list') {if(!/^[0-9]+(,[0-9]+)*$/.test(value))throw new Error('Ange kommaseparerade heltal.');value=value.split(',').map(Number);}
          const data=JSON.parse(constants.value);data[constantField.value]={type:constantType.value,value};
          constants.value=JSON.stringify(data);update();drawDecisions();
        }catch(error){showError(error);}
      });
      visual.append(el('h5',{},'ValueMaps'),el('label',{},'Målfält',mapField),
        el('label',{},'Originalvärde',mapFrom),el('label',{},'Målvärde',mapTo),addMap,
        el('h5',{},'Constants'),el('label',{},'Målfält',constantField),el('label',{},'Typ',constantType),
        el('label',{},'Värde',constantValue),addConstant,decisionsList);
      box.append(visual);
      const rowPicker=el('div',{className:'row-picker'});
      const columnList=el('datalist',{id:`external-columns-${index}`});
      box.append(el('p',{},'Välj granskade originalrader för denna vy'),rowPicker,
        el('p',{},'Källkolumner visas som bokstav och verifierad rubrik när rubrikrad valts.'),columnList);
      for(const input of Object.values(columns)) input.setAttribute('list',columnList.id);
      if (view.data) {
        table.value=view.data.table; role.value=view.data.role; header.value=view.data.header;
        selected.value=view.data.selected; label.value=view.data.label;
        for (const [key,value] of Object.entries(view.data.columns)) columns[key].value=value;
        maps.value=view.data.maps; constants.value=view.data.constants;
        accessTransform.value=view.data.accessTransform || '';
        trunkTransform.value=view.data.trunkTransform || '';
      } else update();
      const showRows = () => {
        rowPicker.replaceChildren();
        const meta=findTable(table.value);
        if(!meta)return;
        const picked=new Set(selected.value.split(',').map(Number));
        rowPicker.append(el('p',{},`${picked.size && !picked.has(0) ? picked.size : 0} valda rader`));
        for(const row of meta.previewRows) {
          const check=el('input',{type:'checkbox',checked:picked.has(row.row)});
          check.addEventListener('change',()=>{
            const next=new Set(selected.value.split(',').filter(Boolean).map(Number));
            if(check.checked) next.add(row.row); else next.delete(row.row);
            selected.value=[...next].sort((a,b)=>a-b).join(','); update(); showRows(); renderDecisions();
          });
          rowPicker.append(el('label',{className:'check-line'},check,`Rad ${row.row}: ${row.cells.slice(0,3).map(c=>c.value).join(' · ')}`));
        }
      };
      const showColumns = () => {
        const meta=findTable(table.value);
        const headerRow=meta?.previewRows.find(row=>row.row===Number(header.value));
        columnList.replaceChildren(...Array.from({length:meta?.columnCount ?? 0},(_,i)=>{
          const col=letter(i), cell=headerRow?.cells.find(c=>c.address===`${col}${headerRow.row}`);
          return el('option',{value:col,label:`${col}${cell ? ` – ${cell.value}` : ''}`});
        }));
      };
      const showRole = () => {
        for (const [field, control] of Object.entries(columns)) {
          const supported = fields[role.value].includes(field);
          columnLabels[field].hidden = !supported;
          if (!supported) control.value = '';
        }
      };
      showRole(); showRows(); showColumns();
      drawDecisions();
      controls.forEach(control => control.addEventListener('change', () => {
        if (control === role) showRole();
        if (control === table) { selected.value=''; showRows(); }
        if (control === selected) showRows();
        update();
        drawDecisions();
        if (control === header || control === table) { showColumns(); renderSources(); }
        renderDecisions();
      }));
      remove.addEventListener('click',()=>{views.splice(index,1); invalidate(); renderViews();});
      container.append(box);
    });
    $('external-profile-export').disabled = !views.length;
    renderDecisions();
  }
  function renderDecisions() {
    const target=$('external-decision-editor'), list=$('external-decision-list');
    target.replaceChildren(); list.replaceChildren();
    let values, exclusions;
    try { values=JSON.parse($('external-row-values').value); exclusions=JSON.parse($('external-exclusions').value); }
    catch { list.textContent='Avancerad JSON är ogiltig.'; return; }
    if(!Array.isArray(values) || !Array.isArray(exclusions)) { list.textContent='Besluten måste vara JSON-arrayer.'; return; }
    const rows=views.flatMap((view,index)=>{
      const meta=findTable(view.data?.table || '');
      const chosen=new Set((view.data?.selected || '').split(',').map(Number));
      return (meta?.previewRows || []).filter(row=>chosen.has(row.row)).map(row=>({viewId:`view-${index+1}`,row:row.row,
        role:view.data.role, name:`${sources[Number(view.data.table.split(':')[0])].payload.filename} / ${meta.name} / rad ${row.row} / view-${index+1}`}));
    });
    if(!rows.length) { target.textContent='Välj först granskade originalrader i en MappingView.'; return; }
    const rowSelect=el('select',{},...rows.map(item=>el('option',{value:`${item.viewId}:${item.row}`},item.name)));
    const fieldSelect=el('select',{}), typeSelect=el('select',{},
      el('option',{value:'text'},'Text'),el('option',{value:'boolean'},'Boolean'),
      el('option',{value:'null'},'Null'),el('option',{value:'integer'},'Heltal (VLAN)'),
      el('option',{value:'integer_list'},'Heltalslista (VLAN)'));
    const input=el('input',{type:'text',placeholder:'Uttryckligt värde'});
    const reason=el('input',{type:'text',placeholder:'Motivering till exkludering'});
    const refreshFields=()=>{
      const row=rows.find(item=>`${item.viewId}:${item.row}`===rowSelect.value);
      fieldSelect.replaceChildren(...(fields[row?.role] || []).map(field=>el('option',{value:field},field)));
      refreshTypes();
    };
    const refreshTypes=()=>{
      const permitted=fieldSelect.value==='port.accessVlan' ? ['integer'] :
        fieldSelect.value==='port.allowedVlans' ? ['integer_list'] :
        ['port.enabled','link.enabled'].includes(fieldSelect.value) ? ['boolean'] :
        fieldSelect.value==='node.zoneId' ? ['text','null'] : ['text'];
      for(const option of typeSelect.options) option.disabled=!permitted.includes(option.value);
      if(!permitted.includes(typeSelect.value)) typeSelect.value=permitted[0];
    };
    fieldSelect.addEventListener('change',refreshTypes);
    rowSelect.addEventListener('change',refreshFields); refreshFields();
    const save=(id,items)=>{ $(id).value=JSON.stringify(items); invalidate(); renderDecisions(); };
    const add=el('button',{type:'button'},'Lägg till radbeslut');
    add.addEventListener('click',()=>{
      const [viewId,rowText]=rowSelect.value.split(':'), row=Number(rowText), targetField=fieldSelect.value;
      if(!targetField)return showError(new Error('Välj ett målfält för vyn.'));
      let value=input.value;
      if(typeSelect.value==='boolean') {
        if(!['true','false'].includes(value))return showError(new Error('Boolean måste anges som true eller false.'));
        value=value==='true';
      } else if(typeSelect.value==='null') value=null;
      else if(typeSelect.value==='integer' || typeSelect.value==='integer_list') {
        const values=typeSelect.value==='integer_list' ? value.split(',') : [value];
        if(values.length>64 || values.some(item=>!/^[1-9][0-9]{0,3}$/.test(item) || Number(item)>4094) ||
            new Set(values).size!==values.length)
          return showError(new Error('Ange 1–64 unika VLAN-heltal 1–4094 utan mellanslag eller ledande nollor.'));
        value=typeSelect.value==='integer_list' ? values.map(Number) : Number(value);
      }
      const next=values.filter(item=>!(item.viewId===viewId && item.row===row && item.targetField===targetField));
      next.push({viewId,row,targetField,valueType:typeSelect.value,value}); save('external-row-values',next);
    });
    const exclude=el('button',{type:'button'},'Exkludera denna radanvändning');
    exclude.addEventListener('click',()=>{
      const [viewId,rowText]=rowSelect.value.split(':'), row=Number(rowText);
      if(!reason.value.trim())return showError(new Error('Ange en motivering.'));
      save('external-exclusions',[...exclusions.filter(item=>!(item.viewId===viewId && item.row===row)),
        {viewId,row,reason:reason.value.trim()}]);
    });
    target.append(el('label',{},'Källa, vy och originalrad',rowSelect),el('label',{},'Målfält',fieldSelect),
      el('label',{},'Värdetyp',typeSelect),el('label',{},'Värde',input),add,
      el('label',{},'Exkluderingsorsak',reason),exclude);
    for(const [id,items] of [['external-row-values',values],['external-exclusions',exclusions]])
      items.forEach((item,index)=>{
        const row=rows.find(entry=>entry.viewId===item.viewId && entry.row===item.row);
        const edit=el('button',{type:'button'},'Redigera');
        edit.addEventListener('click',()=>{
          rowSelect.value=`${item.viewId}:${item.row}`; refreshFields();
          if(id==='external-row-values') {fieldSelect.value=item.targetField;typeSelect.value=item.valueType;
            input.value=item.value===null ? '' : String(item.value);}
          else reason.value=item.reason;
          target.scrollIntoView({block:'center'});
        });
        const remove=el('button',{type:'button'},'Ta bort');
        remove.addEventListener('click',()=>save(id,items.filter((_,i)=>i!==index)));
        list.append(el('p',{},`${row?.name || `${item.viewId} / rad ${item.row}`} · ${item.targetField || 'Exkluderad'} · ${item.valueType || ''} ${item.value ?? ''} ${item.reason || ''} `,edit,remove));
      });
  }
  function mappingViewsRequest() {
    return views.map((view,index) => {
      const data=view.data, [sourceIndex,tableId]=data.table.split(':');
      const meta=sources[Number(sourceIndex)].inspection.tables.find(t=>t.tableId===tableId);
      const headerRow=data.header === '' ? null : Number(data.header);
      const headerCells=meta.previewRows.find(r=>r.row===headerRow)?.cells;
      if (headerRow !== null && !headerCells) throw new Error('Rubrikraden måste vara en synlig originalrad. Bläddra till raden och välj den.');
      const columns=Object.fromEntries(Object.entries(data.columns)
        .filter(([,value])=>value.trim()).map(([key,value])=>[key,value.split(',').map(x=>x.trim())]));
      const selectedRows=[...new Set(data.selected.split(',').filter(Boolean).map(x=>Number(x.trim())))].sort((a,b)=>a-b);
      if (selectedRows.some(row=>!meta.previewRows.some(item=>item.row===row)))
        throw new Error('Visa varje vald originalrad före mappning.');
      return {viewId:`view-${index+1}`,sourceId:`src-${Number(sourceIndex)+1}`,tableId,
        role:data.role,headerRow,selectedRows,
        columns,valueMaps:JSON.parse(data.maps),constants:JSON.parse(data.constants),
        expectedHeaders:headerCells?.map(c=>c.value) ?? [],label:data.label};
    });
  }
  function transformationsRequest() {
    return views.flatMap((view,index) => [
      view.data.accessTransform && {viewId:`view-${index+1}`,targetField:'port.accessVlan',operation:view.data.accessTransform,delimiter:null},
      view.data.trunkTransform && {viewId:`view-${index+1}`,targetField:'port.allowedVlans',operation:view.data.trunkTransform,delimiter:','},
    ].filter(Boolean));
  }
  function request(selectedUnitIds) {
    const mappingViews = mappingViewsRequest();
    return {contractVersion:'1',projectName:$('external-project-name').value,
      sources:sourceRequest(),mappingViews,
      transformations:transformationsRequest(),
      rowValues:JSON.parse($('external-row-values').value),
      excludedUses:JSON.parse($('external-exclusions').value),selectedUnitIds};
  }
  function sourceLink(ref) {
    const source=sources[Number(ref.sourceId?.replace('src-',''))-1];
    const table=source?.inspection.tables.find(item=>item.tableId===ref.tableId);
    const historical=(plan?.sourceManifest || getProject().importEvidence?.sources || [])
      .find(item=>item.sourceId===ref.sourceId);
    const button=el('button',{type:'button',className:'source-link'},
      `${source?.payload.filename || historical?.filename || ref.sourceId} / ${table?.name || historical?.tables.find(item=>item.tableId===ref.tableId)?.name || ref.tableId} / ${ref.address || `rad ${ref.row}`}`);
    button.addEventListener('click',()=>navigateSource(ref));
    return button;
  }
  async function navigateSource(ref) {
    const generation=++navigationGeneration, token=guard();
    const source=sources[Number(ref.sourceId?.replace('src-',''))-1];
    const table=source?.inspection.tables.find(item=>item.tableId===ref.tableId);
    const manifest=(plan?.sourceManifest || getProject().importEvidence?.sources || [])
      .find(item=>item.sourceId===ref.sourceId);
    const focus=$('external-source-focus'); focus.replaceChildren();
    if(!source || !table || (manifest && manifest.sha256!==source.sha256)) {
      focus.textContent='Källfil ej ansluten eller SHA-256 avviker; ursprungscellen kan inte kontrolleras. Återanslut originalfilen eller källpaketet.';
      return;
    }
    try {
      let row=table.previewRows.find(item=>item.row===ref.row);
      if(!row) {
        const page=await submitInspectionPage(source.payload,table.tableId,ref.row);
        if(generation!==navigationGeneration || !valid(token))return;
        // Validate returned identity and coordinates without mutating the paged preview.
        validateReviewPage(page,source,{...table,previewRows:[]},ref.row);
        row=page.rows.find(item=>item.row===ref.row);
      }
      if(generation!==navigationGeneration || !valid(token))return;
      const cell=ref.address ? row?.cells.find(item=>item.address===ref.address) : null;
      if(!row || (ref.address && !cell)) {
        focus.textContent='Den angivna originalraden eller cellen finns inte i verifierad källa.'; return;
      }
      focus.replaceChildren(el('strong',{},`${source.payload.filename} / ${table.name} / rad ${row.row}`),
        el('p',{},cell ? `${cell.address} · ${cell.type} · ${cell.value}` : 'Originalrad utan angiven celladress'));
      if(table.previewRows.some(item=>item.row===row.row)) {
        renderSources(ref);
        $('external-sources').querySelector('.source-highlight')?.scrollIntoView({block:'center'});
      }
    } catch(error) { if(generation===navigationGeneration && valid(token)) showError(error); }
  }
  function renderPlan(value) {
    const target=$('external-plan-result'); target.replaceChildren();
    const report=value.report;
    target.append(el('p',{},`Planfingerprint: ${value.fingerprint}`),
      el('h4',{},'Granskningsrapport (källradanvändningar)'),
      el('dl',{className:'review-metrics'},...Object.entries({
        'Importerbara':report.actionable,'Redan representerade':report.noOp,
        'Blockerade':report.blocked,'Ogiltiga':report.invalid,'Uttryckligen exkluderade':report.excluded,
        'Omappade celler':report.unmappedCells,'Valda enheter':report.selectedUnits,
      }).flatMap(([name,count])=>[el('dt',{},name),el('dd',{},String(count))])),
      el('p',{},`${value.units.length} unika planunits · ${report.sourceRows} källrader · ${report.sourceUses} radanvändningar`));
    const filter=el('select',{},el('option',{value:''},'Alla statusar'),
      ...['ACTIONABLE','NO_OP','BLOCKED','INVALID','EXCLUDED'].map(status=>el('option',{value:status},status)));
    const kind=el('select',{},el('option',{value:''},'Alla måltyper'),
      ...[...new Set(value.units.map(unit=>unit.kind))].map(item=>el('option',{value:item},item)));
    const source=el('select',{},el('option',{value:''},'Alla källor'),
      ...value.sourceManifest.map(item=>el('option',{value:item.sourceId},item.filename)));
    const onlyBlocked=el('input',{type:'checkbox'});
    target.append(el('h4',{},'Planunits'),el('label',{},'Status',filter),el('label',{},'Måltyp',kind),
      el('label',{},'Källa',source),el('label',{},onlyBlocked,' Visa bara blockerade'));
    const grid=el('table',{className:'review-grid'},el('thead',{},el('tr',{},
      ...['Välj','Status','Typ','Objekt','Beroenden','Källor'].map(title=>el('th',{},title)))));
    const body=el('tbody',{}); grid.append(body); target.append(el('div',{className:'source-table-scroll'},grid));
    const byId=new Map(value.units.map(unit=>[unit.unitId,unit]));
    const rows=value.units.map(unit=>{
      const check=el('input',{type:'checkbox',className:'unit-choice',value:unit.unitId,disabled:unit.status!=='ACTIONABLE'});
      check.addEventListener('change',()=>{candidate=null; candidateToken=null; revision++; planToken=guard(); $('external-apply').disabled=true; $('external-candidate-result').replaceChildren();
        const picked=new Set(selected());
        const missing=[...new Set(value.units.filter(item=>picked.has(item.unitId))
          .flatMap(item=>item.dependencies.filter(dep=>!picked.has(dep))))];
        $('external-selection-warning').textContent=missing.length ? `Obligatoriska beroenden saknas: ${missing.map(dep=>displayKey(byId.get(dep) || {kind:'',targetKey:dep})).join(', ')}` : '';
      });
      const refs=unit.sourceUses.map(use=>({sourceId:use.sourceId,tableId:use.tableId,row:use.row,address:null}));
      const row=el('tr',{},el('td',{},check),el('td',{},unit.status),el('td',{},unit.kind),
        el('td',{},displayKey(unit),el('small',{},unit.targetKey)),
        el('td',{},unit.dependencies.length ? unit.dependencies.map(dep=>displayKey(byId.get(dep) || {kind:'',targetKey:dep})).join(', ') : '–'),
        el('td',{},...refs.map(sourceLink)));
      body.append(row); return {unit,row};
    });
    const updateFilter=()=>rows.forEach(({unit,row})=>{row.hidden=Boolean((filter.value && unit.status!==filter.value) ||
      (kind.value && unit.kind!==kind.value) || (source.value && !unit.sourceUses.some(use=>use.sourceId===source.value)) ||
      (onlyBlocked.checked && unit.status!=='BLOCKED'));});
    [filter,kind,source,onlyBlocked].forEach(control=>control.addEventListener('change',updateFilter));
    target.append(el('p',{id:'external-selection-warning',role:'status'}),el('h4',{},'Diagnostik och konflikter'));
    if(!value.diagnostics.length)target.append(el('p',{},'Inga diagnostiska fel.'));
    for(const diagnostic of value.diagnostics) {
      const unit=byId.get(diagnostic.unitId);
      const conflicting=[];
      if(diagnostic.code==='FIELD_CONFLICT' && unit) {
        const claims=value.claims.filter(claim=>claim.targetKind===unit.kind && claim.targetKey===unit.targetKey);
        for(const field of new Set(claims.flatMap(claim=>Object.keys(claim.fields)))) {
          if(new Set(claims.filter(claim=>field in claim.fields).map(claim=>JSON.stringify(claim.fields[field]))).size>1)
            conflicting.push(field);
        }
      }
      target.append(el('div',{className:'review-diagnostic'},
        el('strong',{},`${diagnostic.severity}: ${diagnostic.code}`),
        el('p',{},`${unit ? `${displayKey(unit)} · ` : ''}${conflicting.length ? `Fält: ${conflicting.join(', ')} · ` : ''}${diagnosticHelp[diagnostic.code] || diagnostic.message}`),
        ...diagnostic.sourceRefs.map(sourceLink)));
    }
    const claims=el('details',{},el('summary',{},`${value.claims.length} källpåståenden (SourceClaims)`));
    for(const claim of value.claims) claims.append(el('p',{},
      `${claim.targetKind} · ${claim.targetKey ?? 'olöst'} · ${Object.keys(claim.fields).join(', ')} · `,
      sourceLink(claim.sourceRef)));
    target.append(claims);
    target.append(el('h4',{},'Ofullständig dokumentation'),
      el('p',{},`Importerbara enheter: ${report.nodes} noder, ${report.ports} portar, ${report.zones} zoner, ${report.routes} routes, ${report.links} kablar.`),
      el('p',{},value.claims.some(claim=>claim.targetKind==='link') ? 'Kabeluppgifter finns i granskade källor; se status för varje enhet.' : 'Fysisk kabeldragning är inte dokumenterad i de granskade källorna.'),
      el('p',{},value.claims.some(claim=>claim.targetKind==='ipBinding' || claim.fields['port.ipv4']) ? 'IPv4-uppgifter finns i granskade källor.' : 'IPv4-bindningar är inte dokumenterade i de granskade källorna.'),
      el('p',{},value.claims.some(claim=>claim.targetKind==='staticRoute') ? 'Routeuppgifter finns i granskade källor.' : 'Statiska routes är inte dokumenterade i de granskade källorna.'),
      el('p',{},value.claims.some(claim=>Object.keys(claim.fields).some(field=>field.startsWith('port.vlan') || field==='port.accessVlan' || field==='port.allowedVlans')) ? 'VLAN-uppgifter finns i granskade källor.' : 'VLAN-uppgifter är inte dokumenterade i de granskade källorna.'),
      el('p',{},`${report.unmappedCells} omappade originalceller:`));
    for(const review of value.recordReviews) for(const address of review.unmappedAddresses)
      target.append(sourceLink({sourceId:review.sourceId,tableId:review.tableId,row:review.row,address}));
    const raw=el('details',{},el('summary',{},'Avancerad teknisk planvy'),
      el('pre',{},JSON.stringify(value,null,2))); target.append(raw);
    $('external-candidate-button').disabled=!value.units.some(u=>u.status==='ACTIONABLE');
  }
  async function buildPreview() {
    invalidate(); const token=guard();
    try {
      const response=await api('/api/import/build-candidate',request([]));
      if (!valid(token)) return stale();
      plan=response.plan; renderPlan(plan); planToken=guard();
    } catch (error) { if (valid(token)) showError(error); }
  }
  const selected = () => [...$('external-plan-result').querySelectorAll('.unit-choice:checked')].map(x=>x.value).sort();
  async function buildCandidate() {
    if (!planToken || !valid(planToken)) return stale();
    const choices=selected(), token=guard();
    try {
      const response=await api('/api/import/build-candidate',request(choices));
      if (!valid(token) || choices.join(',')!==selected().join(',')) return stale();
      candidate=response.plan;
      candidateToken=guard();
      const project=candidate.proposedProject;
      const ports=project?.nodes.flatMap(node=>node.ports) || [];
      const metrics={Zoner:project?.zones.length || 0,Noder:project?.nodes.length || 0,
        Portar:ports.length,'VLAN-konfigurationer':ports.filter(port=>port.vlanMode!=null).length,
        'IPv4-bindningar':ports.filter(port=>port.ipv4!=null).length,
        'Statiska routes':project?.nodes.reduce((sum,node)=>sum+(node.staticRoutes?.length || 0),0) || 0,
        Kablar:project?.links.length || 0,'Inaktiva kablar':project?.links.filter(link=>!link.enabled).length || 0};
      $('external-candidate-result').replaceChildren(el('p',{},`Fingerprint: ${candidate.fingerprint}`),
        el('p',{},`Tillämpbar: ${candidate.canApply} · ${candidate.selectedUnitIds.length} valda planunits`),
        el('p',{},`Föreslaget projekt: ${metrics.Noder} noder, ${metrics.Zoner} zoner`),
        el('dl',{className:'review-metrics'},...Object.entries(metrics).flatMap(([name,count])=>[el('dt',{},name),el('dd',{},String(count))])),
        el('p',{},`${candidate.report.unmappedCells} omappade källceller; ${candidate.diagnostics.length} diagnoser.`),
        el('details',{},el('summary',{},'Avancerad teknisk kandidatvy'),el('pre',{},JSON.stringify(project || candidate.diagnostics,null,2))));
      $('external-apply').disabled=!candidate.canApply || !$('external-warning').checked;
    } catch(error) { if (valid(token)) showError(error); }
  }
  async function applyCandidate() {
    if (!candidate?.canApply || !$('external-warning').checked) return;
    if (!candidateToken || !valid(candidateToken)) return stale();
    const picked=selected(), old=candidate, token=guard();
    if (!confirmDiscard()) return;
    if (!confirm(`Ersätta arbetsytan med ${old.proposedProject.nodes.length} uttryckliga noder och ${old.proposedProject.zones.length} zoner? Ingen fil sparas automatiskt.`)) return;
    if (!valid(token) || picked.join(',')!==selected().join(',')) return stale();
    try {
      const fresh=(await api('/api/import/build-candidate',request(picked))).plan;
      if (!valid(token) || picked.join(',')!==selected().join(',') ||
          !fresh.canApply || fresh.fingerprint!==old.fingerprint ||
          JSON.stringify(fresh.proposedProject)!==JSON.stringify(old.proposedProject)) return stale();
      const original=sources;
      replaceProject(fresh.proposedProject);
      sources=original; attached=true; renderSources(); refreshStatus();
      notify(`Importerade ${fresh.proposedProject.nodes.length} noder och ${fresh.proposedProject.zones.length} zoner. Ingen automatisk Save.`);
    } catch(error) { if(valid(token)) showError(error); }
  }
  async function verify(reconnected) {
    const ctx=context(), generation=++sourceGeneration;
    attached=false; sources=[]; views=[]; invalidate(); renderViews(); renderSources(); refreshStatus();
    try {
      const result=await api('/api/import/verify-sources',{project:getProject(),sources:reconnected});
      if (!current(ctx) || generation!==sourceGeneration) return stale();
      if (result.sourceStatus==='SOURCE_VERIFIED') {
        const reviewed=[];
        for (const item of reconnected) {
          const payload={...item}; delete payload.sourceId;
          const inspection=await submitInspection(payload);
          if (!current(ctx) || generation!==sourceGeneration) return stale();
          reviewed.push({payload,sha256:inspection.source.sha256,inspection});
        }
        sources=reviewed; renderSources(); attached=true;
      }
      $('external-verification').textContent=JSON.stringify(result);
      refreshStatus();
    } catch(error) {
      if (!current(ctx) || generation!==sourceGeneration) return stale();
      attached=false; $('external-verification').textContent=`Källverifiering avvisad: ${error.message}`;
      refreshStatus();
    }
  }
  $('external-import').addEventListener('click',()=>dialog.showModal());
  $('external-close').addEventListener('click',()=>dialog.close());
  $('external-files').addEventListener('change',event=>{
    fileChoices = [...event.target.files].map(file => ({file, delimiter:null}));
    discardInspections(); renderFileChoices();
  });
  $('external-inspect-files').addEventListener('click',async ()=>{
    const nextGeneration=sourceGeneration+1, ctx=context();
    try { await loadFiles(fileChoices.map(item => ({...item}))); }
    catch(error) {
      if (sourceGeneration!==nextGeneration || !current(ctx)) return stale();
      sources=[]; invalidate(); renderSources(); showError(error);
    }
  });
  $('external-add-view').addEventListener('click',()=>{ if(views.length>=64)return showError(new Error('Högst 64 MappingViews.')); views.push({}); renderViews(); invalidate(); });
  $('external-profile-export').addEventListener('click',()=>{
    try {
      const profile=exportMappingProfile(mappingViewsRequest(),transformationsRequest());
      download({content:JSON.stringify(profile,null,2)+'\n',type:'application/json',filename:'mapping-profile.json'});
      $('external-profile-status').textContent='Nedladdning initierad, filens skrivning till disk ej verifierad';
    } catch(error) { showError(error); }
  });
  $('external-profile-file').addEventListener('change',async event=>{
    const file=event.target.files[0]; if(!file)return;
    event.target.value='';
    clearPendingProfile();
    const token=guard();
    try {
      if (!sources.length) throw new Error('Inspektera aktuella originalfiler före profilimport.');
      if (!file.name.toLowerCase().endsWith('.json') || file.size===0 || file.size>256*1024)
        throw new Error('Välj en JSON-profil på högst 256 KiB.');
      const raw=await file.arrayBuffer();
      if (!valid(token)) return stale();
      let decoded, parsed;
      try { decoded=new TextDecoder('utf-8',{fatal:true}).decode(raw); }
      catch { throw new Error('Profilen är inte giltig UTF-8.'); }
      try { parsed=JSON.parse(decoded); }
      catch { throw new Error('Profilen innehåller ogiltig JSON.'); }
      const profile=validateMappingProfile(parsed);
      if (!valid(token)) return stale();
      pendingProfile=profile; pendingToken=token;
      const bindings=$('external-profile-bindings');
      bindings.replaceChildren(...profile.views.map((item,index) => el('label',{},
        `Profilvy ${index+1}: ${item.role} · ${item.label} · rubrikrad ${item.headerRow ?? 'ingen'} · `,
        el('select',{},el('option',{value:''},'Välj inspekterad källtabell'),...tableOptions()))));
      $('external-profile-confirm').disabled=false;
      $('external-profile-status').textContent='Välj uttryckligen en tabell för varje profilvy. Inga originalrader väljs automatiskt.';
    } catch(error) {
      if (valid(token)) { $('external-profile-status').textContent=error.message; showError(error); }
    }
  });
  $('external-profile-confirm').addEventListener('click',()=>{
    try {
      if (!pendingProfile || !pendingToken || !valid(pendingToken)) return stale();
      const choices=[...$('external-profile-bindings').querySelectorAll('select')].map(control=>{
        const [sourceIndex,tableId]=control.value.split(':');
        return {sourceIndex:control.value ? Number(sourceIndex) : -1,tableId:tableId || ''};
      });
      const bound=bindMappingProfile(pendingProfile,choices,sources);
      if (!confirm(`Ersätta aktuella MappingViews med ${bound.length} profilvyer? Välj originalrader på nytt. Inget projekt skapas eller sparas.`)) return;
      if (!valid(pendingToken)) return stale();
      views=bound.map(data=>({data}));
      invalidate(); renderViews();
      $('external-profile-status').textContent=`${bound.length} profilvyer bundna till aktuella källtabeller. Välj originalrader på nytt.`;
    } catch(error) { $('external-profile-status').textContent=error.message; showError(error); }
  });
  for(const id of ['external-project-name','external-row-values','external-exclusions']) $(''+id).addEventListener('input',invalidate);
  $('external-plan-button').addEventListener('click',buildPreview);
  $('external-candidate-button').addEventListener('click',buildCandidate);
  $('external-warning').addEventListener('change',()=>{$('external-apply').disabled=!candidate?.canApply || !$('external-warning').checked;});
  $('external-apply').addEventListener('click',applyCandidate);
  $('external-bundle-export').addEventListener('click',()=>{
    try { const bundle=prepareSourceBundle(sources);
      download({content:JSON.stringify(bundle,null,2)+'\n',type:'application/json',filename:'original-sources.json'});
      notify('Nedladdning initierad, filens skrivning till disk ej verifierad.');
    } catch(error) {showError(error);}
  });
  $('external-bundle-file').addEventListener('change',async event=>{
    const file=event.target.files[0]; if(!file)return;
    const ctx=context(), generation=++sourceGeneration;
    try { const bundle=JSON.parse(await file.text()); const decoded=await readSourceBundle(bundle);
      if (!current(ctx) || generation!==sourceGeneration) return stale();
      await verify(decoded); }
    catch(error) {
      if (!current(ctx) || generation!==sourceGeneration) return stale();
      attached=false;refreshStatus();showError(error);
    }
  });
  $('external-reattach-files').addEventListener('change',async event=>{
    const ctx=context(), generation=++sourceGeneration;
    try {const files=[...event.target.files], manifest=getProject().importEvidence?.sources;
      if(!manifest || files.length!==manifest.length)throw new Error('Alla historiska filer krävs i ordning.');
      const reconnected=[];
      for(const [index,file] of files.entries()) {
        const item=manifest[index];
        const prepared=await prepareInspection(file,item.csvDelimiter);
        if (!current(ctx) || generation!==sourceGeneration) return stale();
        reconnected.push({sourceId:`src-${index+1}`,...prepared.payload});
      }
      await verify(reconnected);
    }catch(error){
      if (!current(ctx) || generation!==sourceGeneration) return stale();
      attached=false;refreshStatus();showError(error);
    }
  });
  refreshStatus();
  return {onWorkspace,onEdit};
}
