import test from 'node:test';
import assert from 'node:assert/strict';
import {validateMappingProfile,exportMappingProfile,bindMappingProfile} from
  '../web/features/projects/mapping-profiles.js';

const view = (role='device_inventory') => ({role,headerRow:1,
  expectedHeaders:['Node','Label','Kind','Enabled'],
  columns:{'node.id':['A'],'node.label':['B'],'node.kind':['C']},
  valueMaps:{'node.kind':{'Router':'router'}},constants:{},transformations:[],label:'Nodes'});
const profile = () => ({profileVersion:'1',views:[view()]});
const sources = () => [{inspection:{tables:[{tableId:'sheet-1',columnCount:4,
  previewRows:[{row:1,cells:['Node','Label','Kind','Enabled'].map((value,index)=>({
    address:String.fromCharCode(65+index)+'1',type:'text',value}))}]}]}}];
const clone = item => structuredClone(item);
const rejects = (item, reason) => assert.throws(() => validateMappingProfile(item), reason);

test('profile export strips identities, rows and sources', () => {
  const mapping = {viewId:'view-9',sourceId:'src-4',tableId:'sheet-7',selectedRows:[2],
    ...view()};
  const actual = exportMappingProfile([mapping], []);
  assert.deepEqual(actual, profile());
  const text = JSON.stringify(actual);
  for (const forbidden of ['viewId','sourceId','tableId','selectedRows','importEvidence',
    'acceptedChanges','contentBase64','planFingerprint']) assert.ok(!text.includes(forbidden));
});

test('bind requires explicit inspected table and retains no old row selection', () => {
  const p = profile();
  assert.throws(() => bindMappingProfile(p,[{sourceIndex:-1,tableId:''}],sources()));
  assert.deepEqual(bindMappingProfile(p,[{sourceIndex:0,tableId:'sheet-1'}],sources()), [{
    table:'0:sheet-1',role:'device_inventory',header:'1',selected:'',
    columns:{'node.id':'A','node.label':'B','node.kind':'C'},
    maps:JSON.stringify({'node.kind':{'Router':'router'}}),constants:'{}',label:'Nodes',
    accessTransform:'',trunkTransform:''}]);
  const wrong=sources(); wrong[0].inspection.tables[0].previewRows[0].cells[0].value='Kind';
  assert.throws(() => bindMappingProfile(p,[{sourceIndex:0,tableId:'sheet-1'}],wrong), /kolumn A: Node.*Kind/);
  const narrow=sources(); narrow[0].inspection.tables[0].columnCount=2;
  assert.throws(() => bindMappingProfile(p,[{sourceIndex:0,tableId:'sheet-1'}],narrow), /Kolumn C/);
  const unheaded=profile();unheaded.views[0].headerRow=null;unheaded.views[0].expectedHeaders=[];
  assert.equal(bindMappingProfile(unheaded,[{sourceIndex:0,tableId:'sheet-1'}],sources())[0].header,'');
  unheaded.views[0].expectedHeaders=['Node'];rejects(unheaded,/expectedHeaders/);
});

test('all roles, booleans, maps and VLAN transformations retain exact types', () => {
  const roles=['device_inventory','zone_inventory','interface_inventory','ip_plan',
    'static_route_register','cable_register','documentation_only'];
  const views=roles.map(role => ({...view(role),columns:{},valueMaps:{},label:role}));
  views[0].columns={'node.id':['A'],'node.label':['B'],'node.kind':['C']};
  views[1].columns={'zone.id':['A'],'zone.label':['B']};
  views[3].columns={'ip.nodeId':['A'],'ip.portId':['B'],'ip.ipv4':['C']};
  views[4].columns={'route.nodeId':['A'],'route.id':['B'],'route.destination':['C'],
    'route.nextHop':['D'],'route.outPort':['E']};
  views[5].columns={'link.id':['A'],'link.aNode':['B'],'link.aPort':['C'],
    'link.bNode':['D'],'link.bPort':['E']};
  const port=views[2];
  port.columns={'port.nodeId':['A'],'port.id':['B'],'port.enabled':['D'],
    'port.accessVlan':['C'],'port.allowedVlans':['D']};
  port.valueMaps={'port.enabled':{'yes':'true','no':'false'}};
  const link=views[5]; link.constants={'link.enabled':{type:'boolean',value:false}};
  const out=exportMappingProfile(views.map((item,index)=>({...item,viewId:`view-${index+1}`})),[
    {viewId:'view-3',targetField:'port.accessVlan',operation:'parse_vlan_integer',delimiter:null},
    {viewId:'view-3',targetField:'port.allowedVlans',operation:'split_vlan_integer_list',delimiter:','},
  ]);
  assert.deepEqual(out.views.map(item=>item.role),roles);
  assert.equal(out.views[5].constants['link.enabled'].value,false);
  assert.deepEqual(out.views[2].transformations,[
    {targetField:'port.accessVlan',operation:'parse_vlan_integer',delimiter:null},
    {targetField:'port.allowedVlans',operation:'split_vlan_integer_list',delimiter:','}]);
});

test('malformed schemas and unsafe keys fail before binding', () => {
  for (const [index,mutate] of [
    p=>{p.profileVersion='2'}, p=>{p.selectedRows=[2]},
    p=>{p.views[0].sourceId='src-1'}, p=>{delete p.views[0].label},
    p=>{p.views='wrong'}, p=>{p.views=Array(65).fill(view())},
    p=>{p.views[0].role='unknown'}, p=>{p.views[0].headerRow=1.5},
    p=>{p.views[0].expectedHeaders='Node'}, p=>{p.views[0].columns['node.id']=['A','A']},
    p=>{p.views[0].columns['node.id']=['ZZ']}, p=>{p.views[0].columns['port.id']=['D']},
    p=>{p.views[0].valueMaps['node.zoneId']={x:'y'}},
    p=>{p.views[0].constants['node.id']={type:'text',value:'A'}},
    p=>{p.views[0].constants['node.zoneId']={type:'boolean',value:true}},
    p=>{p.views[0].transformations=[{targetField:'port.accessVlan',operation:'parse_vlan_integer',delimiter:null}]},
    p=>{p.views[0].columns=JSON.parse('{"__proto__":["A"]}')},
  ].entries()) {const p=profile();mutate(p);assert.throws(() => validateMappingProfile(p), undefined, `mutation ${index}`);}
  for (const extra of ['sourceId','tableId','acceptedChanges','importEvidence','contentBase64']) {
    const p=profile();p.views[0][extra]='x';rejects(p);
  }
});

test('boolean and transformation contradictions fail closed', () => {
  const p=profile();p.views[0].role='interface_inventory';
  p.views[0].columns={'port.enabled':['D']};p.views[0].valueMaps={'port.enabled':{'yes':'on'}};
  rejects(p,/valueMap/);
  p.views[0].valueMaps={'port.enabled':{'yes':'true'}};
  p.views[0].constants={'port.enabled':{type:'boolean',value:true}};
  rejects(p,/constant/);
  delete p.views[0].columns['port.enabled'];delete p.views[0].valueMaps['port.enabled'];
  p.views[0].constants={'port.enabled':{type:'text',value:'true'}};
  rejects(p,/constant/);
  p.views[0].constants={};p.views[0].columns={'port.accessVlan':['C']};
  const item={targetField:'port.accessVlan',operation:'parse_vlan_integer',delimiter:null};
  p.views[0].transformations=[item,item];rejects(p,/transformation/);
  p.views[0].transformations=[{...item,viewId:'view-1'}];rejects(p,/transformation/);
});

test('invalid bytes, boundaries and multi-view failure never produce bound views', () => {
  assert.throws(() => JSON.parse('{broken'));
  assert.throws(() => new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.of(0xff)));
  assert.throws(() => JSON.parse(''));
  const profileWithTwo = {profileVersion:'1',views:[view(),view()]};
  profileWithTwo.views[1].columns={'link.id':['A']};
  rejects(profileWithTwo,/målfält/);
  assert.throws(() => bindMappingProfile(profile(),[],sources()), /Alla profilvyer/);
  const missing=sources(); missing[0].inspection.tables[0].previewRows=[];
  assert.throws(() => bindMappingProfile(profile(),[{sourceIndex:0,tableId:'sheet-1'}],missing), /Rubrikrad/);
  const large=profile();large.views[0].label='x'.repeat(256*1024);
  rejects(large,/label/);
  const oversized=profile();
  oversized.views[0].valueMaps['node.kind']=Object.fromEntries(
    Array.from({length:2500},(_,i)=>[`source-${i}`,`target-${i}-${'x'.repeat(90)}`]));
  rejects(oversized,/256 KiB/);
  const unknown=view();unknown.expectedHeaders=['Node','Label','Kind','Enabled'];
  unknown.columns={'node.id':['D']};unknown.valueMaps={};
  const narrow=sources();narrow[0].inspection.tables[0].columnCount=3;
  assert.throws(() => bindMappingProfile({profileVersion:'1',views:[unknown]},
    [{sourceIndex:0,tableId:'sheet-1'}],narrow), /Kolumn D/);
  assert.throws(() => exportMappingProfile([{...view(),viewId:'view-1'}],
    [{viewId:'view-2',targetField:'port.accessVlan',operation:'parse_vlan_integer',delimiter:null}]),
  /saknar aktuell MappingView/);
});

test('historical metadata, malformed columns, maps and constants are rejected', () => {
  for (const extra of ['viewId','selectedUnitIds','rowValues','excludedUses','planFingerprint',
    'claimId','unitId','changeId','sourceManifest','originalBytes','acceptedChanges','importEvidence']) {
    const p=profile();p.views[0][extra]='old source';rejects(p,/Ogiltiga fält/);
  }
  for (const field of ['node.id','node.label']) {
    const p=profile();p.views[0].columns[field]=['a'];rejects(p,/kolumn/);
  }
  const badMap=profile();badMap.views[0].valueMaps['node.kind']={'Router':1};rejects(badMap,/valueMap/);
  const badType=profile();badType.views[0].constants['node.zoneId']={type:'boolean',value:'true'};
  rejects(badType,/constant/);
  const missingHeader=profile();missingHeader.views[0].expectedHeaders.pop();
  assert.throws(() => bindMappingProfile(missingHeader,[{sourceIndex:0,tableId:'sheet-1'}],sources()),
    /kolumn D/);
  const special=profile();special.views[0].valueMaps['node.kind']=JSON.parse('{"constructor":"host"}');
  rejects(special,/valueMap/);
});
