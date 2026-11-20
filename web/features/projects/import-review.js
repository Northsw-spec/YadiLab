import {$, el} from '../../ui/dom.js';
import {api} from '../../services/api.js';
import {prepareInspection, submitInspection, submitInspectionPage, prepareSourceBundle, readSourceBundle} from './transfer.js';
import {validateMappingProfile, exportMappingProfile, bindMappingProfile} from './mapping-profiles.js';

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
  let revision = 0, statusGeneration = 0, sourceGeneration = 0;
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
  async function refreshStatus() {
    const generation = ++statusGeneration, ctx = context();
    const project = getProject();
    if (project.schemaVersion !== '1.4') {
      attached = false; setStatus('Inget historiskt importkvitto.'); return;
    }
    try {
      const result = await api('/api/import/evidence-status', {project});
      if (generation !== statusGeneration || !current(ctx)) return;
      setStatus(`${result.manifestStatus} · ${result.baselineStatus} · ${attached ? 'SOURCE_VERIFIED (ansluten historisk källa)' : 'Källfil ej ansluten; ursprungsceller kan inte kontrolleras.'}`);
    } catch (error) {
      if (generation !== statusGeneration || !current(ctx)) return;
      attached = false; setStatus(`Historiskt importkvitto kunde inte valideras: ${error.message}`);
    }
  }
  function onWorkspace() {
    invalidate(); sources = []; fileChoices = []; views = []; attached = false; ++sourceGeneration;
    $('external-views').replaceChildren(); $('external-sources').replaceChildren();
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
  function renderSources() {
    $('external-sources').replaceChildren(...sources.map((source,index) => {
      const section = el('section', {}, el('h4', {}, `${index+1}. ${source.payload.filename} · ${source.inspection.source.kind} · ${source.payload.csvDelimiter ? `CSV-avskiljare ${source.payload.csvDelimiter} · ` : ''}SHA-256 ${source.sha256}`));
      for (const table of source.inspection.tables) {
        const rows = el('div', {});
        const draw = items => rows.append(...items.map(row => el('p', {},
          `Rad ${row.row}: ${row.cells.map(cell => `${cell.address}=${JSON.stringify(cell.value)}`).join(' · ')}`)));
        draw(table.previewRows);
        const next = el('button', {type:'button'}, 'Visa fler originalrader');
        let from = table.previewRows.at(-1)?.row + 1 || 1;
        next.disabled = table.previewRows.length < 25;
        next.addEventListener('click', async () => {
          if (next.disabled) return;
          const token = guard();
          next.disabled = true;
          try {
            const page = await submitInspectionPage(source.payload, table.tableId, from);
            if (!valid(token)) return stale();
            validateReviewPage(page, source, table, from);
            table.previewRows.push(...page.rows);
            draw(page.rows); from = page.nextRow;
            next.disabled = !from;
          } catch (error) { if (valid(token)) showError(error); }
          finally { if (next.isConnected && from !== null) next.disabled = false; }
        });
        section.append(el('h5', {}, `${table.name} · ${table.populatedRowCount} poster · ${table.columnCount} kolumner`), rows, next);
      }
      return section;
    }));
    $('external-add-view').disabled = !sources.length;
    $('external-plan-button').disabled = !sources.length;
    $('external-bundle-export').disabled = !sources.length;
  }
  function discardInspections() {
    ++sourceGeneration; sources = []; views = []; attached = false;
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
      for (const field of ['node.id','node.label','node.kind','node.zoneId','zone.id','zone.label',
        'port.nodeId','port.id','port.name','port.enabled','port.vlanMode','port.accessVlan','port.allowedVlans','port.ipv4',
        'ip.nodeId','ip.portId','ip.ipv4',
        'route.nodeId','route.id','route.destination','route.nextHop','route.outPort',
        'link.id','link.aNode','link.aPort','link.bNode','link.bPort','link.enabled']) {
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
      box.append(el('label',{},'valueMaps',maps),el('label',{},'constants',constants),
        el('label',{},'port.accessVlan: källtext → JSON-heltal',accessTransform),
        el('label',{},'port.allowedVlans: källtext → JSON-heltalslista',trunkTransform),
        el('label',{},'Vynamn',label),remove);
      if (view.data) {
        table.value=view.data.table; role.value=view.data.role; header.value=view.data.header;
        selected.value=view.data.selected; label.value=view.data.label;
        for (const [key,value] of Object.entries(view.data.columns)) columns[key].value=value;
        maps.value=view.data.maps; constants.value=view.data.constants;
        accessTransform.value=view.data.accessTransform || '';
        trunkTransform.value=view.data.trunkTransform || '';
      } else update();
      const showRole = () => {
        for (const [field, control] of Object.entries(columns)) {
          const supported = role.value === 'device_inventory' ? field.startsWith('node.')
            : role.value === 'zone_inventory' ? field.startsWith('zone.')
            : role.value === 'interface_inventory' ? field.startsWith('port.')
            : role.value === 'ip_plan' ? field.startsWith('ip.')
            : role.value === 'static_route_register' ? field.startsWith('route.')
            : role.value === 'cable_register' && field.startsWith('link.');
          columnLabels[field].hidden = !supported;
          if (!supported) control.value = '';
        }
      };
      showRole();
      controls.forEach(control => control.addEventListener('change', () => {
        if (control === role) showRole();
        update();
      }));
      remove.addEventListener('click',()=>{views.splice(index,1); invalidate(); renderViews();});
      container.append(box);
    });
    $('external-profile-export').disabled = !views.length;
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
  function renderPlan(value) {
    const target=$('external-plan-result'); target.replaceChildren();
    target.append(el('p',{},`Fingerprint: ${value.fingerprint}`),
      el('p',{},`Rapport: ${JSON.stringify(value.report)}`),
      el('h4',{},'Valda typade transformationer'),el('pre',{},JSON.stringify(value.transformations,null,2)),
      el('h4',{},'SourceClaims'),el('pre',{},JSON.stringify(value.claims,null,2)),
      el('h4',{},'Konflikter och diagnostik'),el('pre',{},JSON.stringify(value.diagnostics,null,2)),
      el('h4',{},'Originalrader och omappade celler'),el('pre',{},JSON.stringify(value.recordReviews,null,2)),
      el('h4',{},'ImportUnits'));
    for (const unit of value.units) {
      const item=el('label',{},`${unit.status} · ${unit.kind} ${unit.targetKey} · ${unit.unitId} · beroenden: ${unit.dependencies.join(', ') || 'inga'}`);
      if (unit.status==='ACTIONABLE') {
        const check=el('input',{type:'checkbox',value:unit.unitId});
        check.addEventListener('change',()=>{candidate=null; candidateToken=null; revision++; planToken=guard(); $('external-apply').disabled=true; $('external-candidate-result').replaceChildren();});
        item.prepend(check);
      }
      target.append(item,el('br'));
    }
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
  const selected = () => [...$('external-plan-result').querySelectorAll('input:checked')].map(x=>x.value).sort();
  async function buildCandidate() {
    if (!planToken || !valid(planToken)) return stale();
    const choices=selected(), token=guard();
    try {
      const response=await api('/api/import/build-candidate',request(choices));
      if (!valid(token) || choices.join(',')!==selected().join(',')) return stale();
      candidate=response.plan;
      candidateToken=guard();
      $('external-candidate-result').replaceChildren(el('p',{},`Fingerprint: ${candidate.fingerprint}`),
        el('p',{},`Tillämpbar: ${candidate.canApply}`),
        el('p',{},`Föreslaget projekt: ${candidate.proposedProject?.nodes.length ?? 0} noder, ${candidate.proposedProject?.zones.length ?? 0} zoner`),
        el('pre',{},JSON.stringify(candidate.proposedProject ? {
          nodes:candidate.proposedProject.nodes, links:candidate.proposedProject.links
        } : candidate.diagnostics,null,2)));
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
