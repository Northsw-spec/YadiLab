import React, { useState } from "react";
const e=React.createElement;
const MAX_REFERENCES=20;

/** Never expose source labels, IDs, IPs, geometry or drawn-edge endpoints. */
export function DrawioVertexAssociationReview({preview,model,onExport}){
  const [choices,setChoices]=useState({});
  const [ack,setAck]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [exported,setExported]=useState(false);
  const visible=[];
  for(const p of preview.pages){
    for(let vertexOrdinal=0;vertexOrdinal<p.vertexCount&&visible.length<MAX_REFERENCES;vertexOrdinal++){
      visible.push({pageOrdinal:p.pageOrdinal,vertexOrdinal,key:p.pageOrdinal+":"+vertexOrdinal});
    }
    if(visible.length===MAX_REFERENCES)break;
  }
  const references=visible.filter(x=>Boolean(choices[x.key])).map(x=>({
    pageOrdinal:x.pageOrdinal,vertexOrdinal:x.vertexOrdinal,targetResourceId:choices[x.key]
  }));
  const duplicateTarget=new Set(references.map(x=>x.targetResourceId)).size!==references.length;
  const canExport=!!model&&model.resources?.length>0&&references.length>0&&
    !duplicateTarget&&ack&&!busy&&typeof onExport==="function";
  const send=async()=>{
    if(!canExport)return;
    setBusy(true);setError("");setExported(false);
    try{
      await onExport({
        sourceSha256:preview.sourceSha256,scenarioId:model.scenarioId,
        sourceRevision:model.sourceRevision,acknowledgeNotVerified:ack,references
      });
      setExported(true);
    }catch(cause){
      const code=typeof cause?.code==="string"&&/^DRAWIO_[A-Z0-9_]+$/.test(cause.code)
        ?cause.code:"DRAWIO_ASSOC_BLOCKED";
      setError(code);
    }finally{setBusy(false);}
  };
  return e("section",{className:"network-import-preview",
      "data-drawio-association-review":model?"REVIEW_REQUIRED":"BUILDER_REQUIRED"},
    e("h3",null,"Optional reviewed vertex-position references"),
    e("p",{"data-drawio-association-boundary":"true"},
      "A page/vertex ordinal is a position in this exact diagram file, NOT a verified real device. "+
      "Choose modeled Builder resources manually. Drawn edges cannot be associated or activated."),
    model?e("p",{"data-drawio-builder-model":"true"},
      "Builder resources: "+model.resources.length+" · revision "+model.sourceRevision):
      e("p",{"data-drawio-no-builder":"true"},
      "Open a Builder scenario to export a metadata-only reviewed reference."),
    model?e("ol",{className:"validation-list","data-drawio-vertex-positions":"true"},
      ...visible.map(x=>e("li",{key:x.key},
        e("label",null,"Page #"+(x.pageOrdinal+1)+" · drawn vertex #"+(x.vertexOrdinal+1)+" · ",
          e("select",{
            "data-drawio-associate-vertex":x.key,
            value:choices[x.key]??"",disabled:busy,
            onChange:event=>{
              const value=event.currentTarget.value;
              setChoices(old=>({...old,[x.key]:value}));
              setAck(false);setExported(false);setError("");
            }},
            e("option",{value:""},"Not associated (default)"),
            ...model.resources.map(r=>e("option",{key:r.id,value:r.id},r.label+" ["+r.id+"]"))))))):null,
    preview.vertexCount>MAX_REFERENCES?e("p",{"data-drawio-association-limit":"true"},
      "Only the first 20 drawn vertex positions are available in this bounded profile. "+
      "All remaining positions stay unassociated."):null,
    duplicateTarget?e("p",{role:"alert","data-drawio-association-duplicate":"BLOCKED"},
      "Each Builder resource may be selected at most once."):null,
    e("p",{"data-drawio-reference-count":String(references.length)},
      "Selected unverified references: "+references.length),
    e("label",null,e("input",{type:"checkbox","data-drawio-association-ack":"true",
      checked:ack,disabled:busy||!model||!references.length||duplicateTarget,
      onChange:event=>{setAck(event.currentTarget.checked);setExported(false);}}),
      " I acknowledge these positions are not verified device identities or physical network links."),
    e("button",{type:"button","data-drawio-association-export":"true",disabled:!canExport,
      onClick:()=>{void send();}},
      busy?"Rechecking original diagram and Builder…":"Export metadata-only reviewed references (JSON)"),
    error?e("p",{role:"alert","data-drawio-association-error":"BLOCKED"},error):null,
    exported?e("p",{"data-drawio-association-exported":"true"},
      "Metadata-only sidecar exported; Builder, topology and Engine unchanged."):null);
}
