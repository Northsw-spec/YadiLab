import test from 'node:test';
import assert from 'node:assert/strict';
import {packetJourneyFrames} from '../web/canvas.js';

const a={node:'pc-a',port:'eth0'}, b={node:'sw',port:'p1'};
const c={node:'sw',port:'p2'}, d={node:'pc-b',port:'eth0'};
const project={links:[
  {id:'wire-a',a,b,enabled:true},
  {id:'wire-b',a:c,b:d,enabled:true},
]};
const w=(linkId,from,to)=>({linkId,from,to});
const step=(req=[],reply=[],ip=[])=>({
  arp:{requestTransmissions:req,replyTransmissions:reply},
  ipv4Transmissions:ip,
});
const sample=()=>({
  status:'REPLIED',
  request:{steps:[step([w('wire-a',a,b),w('wire-b',c,d)],
    [w('wire-b',d,c),w('wire-a',b,a)],
    [w('wire-a',a,b),w('wire-b',c,d)])]},
  reply:{steps:[step([],[],[w('wire-b',d,c),w('wire-a',b,a)])]},
  icmpError:null,
});
test('only explicit directional wire records are animated',()=>{
  const frames=packetJourneyFrames(project,sample());
  assert.equal(frames.length,8);
  assert.deepEqual(frames.map(x=>x.stage),[
    'ARP Request','ARP Request','ARP Reply','ARP Reply',
    'ICMP Echo Request','ICMP Echo Request','ICMP Echo Reply','ICMP Echo Reply']);
  assert.deepEqual(frames.map(x=>x.linkId),[
    'wire-a','wire-b','wire-b','wire-a','wire-a','wire-b','wire-b','wire-a']);
  assert.deepEqual(frames.map(x=>x.reverse),[false,false,true,true,false,false,true,true]);
});
test('no engine transmissions never fabricates a path',()=>{
  assert.deepEqual(packetJourneyFrames(project,{status:'REQUEST_FAILED',request:{steps:[]},reply:null}),[]);
  assert.deepEqual(packetJourneyFrames(project,{status:'REPLY_FAILED',request:{steps:[step()]},reply:{steps:[]}}),[]);
});
test('unknown, disabled and wrong-port references fail closed',()=>{
  const payload=sample();
  payload.request.steps[0].ipv4Transmissions=[w('unknown',a,b)];
  assert.throws(()=>packetJourneyFrames(project,payload),/okänd eller avstängd kabel/);
  payload.request.steps[0].ipv4Transmissions=[w('wire-a',a,c)];
  assert.throws(()=>packetJourneyFrames(project,payload),/matchar inte kabelns deklarerade portar/);
  payload.request.steps[0].ipv4Transmissions=[w('wire-a',a,b)];
  const disabled={links:project.links.map(x=>({...x,enabled:x.id!=='wire-a'}))};
  assert.throws(()=>packetJourneyFrames(disabled,payload),/avstängd kabel/);
});
test('incomplete traces and too many events must be rejected',()=>{
  assert.throws(()=>packetJourneyFrames(project,{}),/Ingen verifierbar ICMP-request/);
  assert.throws(()=>packetJourneyFrames(project,{request:{steps:[{}]}}),/saknar ARP-resultat/);
  assert.throws(()=>packetJourneyFrames(project,{request:{steps:[{arp:{requestTransmissions:[],replyTransmissions:[]}}]}}),/IPv4-transmissioner saknas/);
  assert.throws(()=>packetJourneyFrames(project,{
    request:{steps:[step(Array.from({length:601},()=>w('wire-a',a,b)))]},
  }),/max 600/);
});
test('router-error packets use engine trace and do not masquerade as echo reply',()=>{
  const failed={status:'REQUEST_FAILED',
    request:{steps:[step([],[],[w('wire-a',a,b)])]},reply:null,
    icmpError:{trace:{steps:[step([],[],[w('wire-a',b,a)])]}}};
  assert.deepEqual(packetJourneyFrames(project,failed).map(x=>x.stage),[
    'ICMP Echo Request','ICMP routerfel']);
});
