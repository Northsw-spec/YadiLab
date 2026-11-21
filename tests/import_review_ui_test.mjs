import test from 'node:test';
import assert from 'node:assert/strict';
import {letter, displayKey, validateReviewPage, countCandidateVlans} from '../web/features/projects/import-review.js';

test('candidate VLAN metrics count only configured canonical port VLANs', () => {
  const access={vlan:{mode:'access',vlan:10}};
  const trunk={vlan:{mode:'trunk',allowedVlans:[10,20]}};
  assert.equal(countCandidateVlans([]),0);
  assert.equal(countCandidateVlans([{}]),0);
  assert.equal(countCandidateVlans([{vlan:null}]),0);
  assert.equal(countCandidateVlans([{vlanMode:'access'}]),0);
  assert.equal(countCandidateVlans([access]),1);
  assert.equal(countCandidateVlans([trunk]),1);
  assert.equal(countCandidateVlans([access,trunk,{vlan:null},{}]),2);
});

test('source column labels and composite identities retain canonical keys', () => {
  assert.deepEqual([0,25,26,51,52,255].map(letter),['A','Z','AA','AZ','BA','IV']);
  const targetKey='["SW1","g1"]';
  assert.equal(displayKey({kind:'port',targetKey}),'SW1/g1');
  assert.equal(targetKey,'["SW1","g1"]');
  assert.equal(displayKey({kind:'link',targetKey:'CABLE-1'}),'CABLE-1');
});

test('inspected pages keep real sparse rows, cell types and source identity', () => {
  const source={sha256:'a'.repeat(64),payload:{filename:'source.xlsx'},inspection:{source:{kind:'xlsx'}}};
  const table={tableId:'sheet-2',columnCount:3,previewRows:[{row:1,cells:[
    {address:'A1',type:'text',value:'Header'}]}]};
  const page={inspectionVersion:'1',source:{filename:'source.xlsx',kind:'xlsx',sha256:source.sha256},
    tableId:'sheet-2',rows:[{row:8,cells:[{address:'B8',type:'number',value:'12.5'},
      {address:'C8',type:'boolean',value:'true'}]},{row:12,cells:[{address:'A12',type:'text',value:'<script>'}]}],
    nextRow:null};
  assert.equal(validateReviewPage(page,source,table,2),page);
  assert.throws(()=>validateReviewPage({...page,source:{...page.source,sha256:'b'.repeat(64)}},source,table,2));
  assert.throws(()=>validateReviewPage({...page,tableId:'sheet-1'},source,table,2));
  assert.throws(()=>validateReviewPage({...page,rows:[page.rows[0],page.rows[0]]},source,table,2));
  assert.throws(()=>validateReviewPage({...page,rows:[{row:8,cells:[{address:'A9',type:'text',value:'x'}]}]},source,table,2));
});
