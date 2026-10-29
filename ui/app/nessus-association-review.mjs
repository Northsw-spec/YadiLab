import React, { useState } from "react";
const e=React.createElement;
const MAX_VISIBLE=20;

/** Private ReportHost ordinal -> existing modeled resource, metadata-only. */
export function NessusHostAssociationReview({preview,model,onExport}){
  const [choices,setChoices]=useState({});
  const [ack,setAck]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [exported,setExported]=useState(false);
  const references=Object.entries(choices).filter(([,id])=>Boolean(id))
    .map(([hostOrdinal,targetResourceId])=>({hostOrdinal:Number(hostOrdinal),targetResourceId}))
    .sort((a,b)=>a.hostOrdinal-b.hostOrdinal);
  const dup=new Set(references.map(x=>x.targetResourceId)).size!==references.length;
  const canExport=!!model&&!!model.resources?.length&&references.length>0&&
    !dup&&ack&&!busy&&typeof onExport==="function";
  const run=async()=>{
    if(!canExport)return;
    setBusy(true);setError("");setExported(false);
    try{
      await onExport({
        sourceSha256:preview.sourceSha256,
        scenarioId:model.scenarioId,
        sourceRevision:model.sourceRevision,
        acknowledgeNotVerified:ack,
        references,
      });
      setExported(true);
    }catch(cause){
      const code=typeof cause?.code==="string" &&
        /^NESSUS_[A-Z0-9_]+$/.test(cause.code)?cause.code:"NESSUS_ASSOC_BLOCKED";
      setError(code);
    }finally{setBusy(false);}
  };
  return e("section",{"data-nessus-association-review":model?"REVIEW_REQUIRED":"BUILDER_REQUIRED",
    className:"network-import-preview"},
    e("h3",null,"Optional reviewed ReportHost references"),
    e("p",{"data-nessus-association-boundary":"true"},
      "ReportHost ordinal is a position in this specific file, NOT an independently verified device identity. Choose existing Builder resources manually. No host names, IPs or vulnerability details are disclosed or mapped."),
    model?e("p",{"data-nessus-model":"true"},
      "Builder resource count: "+model.resources.length+" · revision "+model.sourceRevision):
      e("p",{"data-nessus-no-builder":"true"},
      "Open a Builder scenario before exporting associations. Read-only severity preview remains available."),
    model?e("ol",{"data-nessus-review-hosts":"true",className:"validation-list"},
      ...Array.from({length:Math.min(preview.hostCount,MAX_VISIBLE)},(_,hostOrdinal)=>
        e("li",{key:hostOrdinal},
          e("label",null,"ReportHost #"+(hostOrdinal+1)+" · ",
            e("select",{"data-nessus-associate-host":String(hostOrdinal),
              value:choices[hostOrdinal]??"",disabled:busy,
              onChange:event=>{
                const targetResourceId=event.currentTarget.value;
                setChoices(prev=>({...prev,[hostOrdinal]:targetResourceId}));
                setAck(false);setExported(false);setError("");
              }},
              e("option",{value:""},"Not associated (default)"),
              ...model.resources.map(item=>e("option",{key:item.id,value:item.id},
                item.label+" ["+item.id+"]")))))):null,
    preview.hostCount>MAX_VISIBLE?e("p",{"data-nessus-association-limit":"true"},
      "Only the first 20 source positions can be reviewed in this bounded profile. Remaining positions stay unassociated."):null,
    dup?e("p",{role:"alert","data-nessus-association-conflict":"BLOCKED"},
      "Each modeled resource can be selected only once."):null,
    e("p",{"data-nessus-selected-count":String(references.length)},
      "Manually selected references: "+references.length),
    e("label",null,e("input",{type:"checkbox","data-nessus-association-ack":"true",
      checked:ack,disabled:busy||!model||!references.length||dup,
      onChange:event=>{setAck(event.currentTarget.checked);setExported(false);}}),
      " I acknowledge these are unverified source-position references, not confirmed identities or vulnerabilities."),
    e("button",{type:"button","data-nessus-association-export":"true",
      disabled:!canExport,onClick:()=>{void run();}},
      busy?"Rechecking original Nessus file…":"Export reviewed metadata-only references (JSON)"),
    error?e("p",{role:"alert","data-nessus-association-error":"BLOCKED"},error):null,
    exported?e("p",{"data-nessus-association-exported":"true"},
      "Local sidecar exported. Builder, physical topology and Engine unchanged."):null);
}
