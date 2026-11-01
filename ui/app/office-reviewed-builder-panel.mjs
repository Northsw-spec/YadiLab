import React, { useEffect, useRef, useState } from "react";
const e=React.createElement;
const MAX=4;
const errCode=cause=>{
  const code=cause?.code;
  return typeof code==="string" && /^(?:IC040_|DOCX_|ODT_|IMPORT_)[A-Z0-9_]+$/.test(code)
    ? code : "IC040_P1B_BLOCKED";
};
const keyOf=n=>[n.tableOrdinal,n.rowOrdinal,n.nodeIdCellOrdinal].join(":");

/** Separate from P1-P6 read-only/reference panels: only original cell ordinals. */
export function OfficeReviewedBuilderPanel({inspectFile,onConfirm,onClose,manualRoleOptions=["resource.generic"]}){
  const [result,setResult]=useState(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const epoch=useRef(0),selectedFile=useRef(null),focus=useRef(null);
  const reset=()=>{
    epoch.current++;selectedFile.current=null;setResult(null);setError("");setBusy(false);
  };
  const close=()=>{reset();onClose();};
  useEffect(()=>{
    focus.current?.focus();
    return()=>{epoch.current++;selectedFile.current=null;};
  },[]);
  useEffect(()=>{
    const onKey=event=>{if(event.key==="Escape")close();};
    document.addEventListener("keydown",onKey);
    return()=>document.removeEventListener("keydown",onKey);
  },[onClose]);
  const choose=async file=>{
    reset();if(!file)return;
    const request=epoch.current;
    setBusy(true);
    try{
      const value=await inspectFile(file);
      if(epoch.current!==request)return;
      if(!value || !["docx","odt"].includes(value.format) ||
          value.preview?.status!=="REVIEW_REQUIRED" ||
          value.preview?.textIncluded!==false ||
          value.preview?.canActivate!==false ||
          value.preview?.engineVerified!==false ||
          value.preview?.physicalTopologyVerified!==false){
        setError("IC040_P1B_PREVIEW_INVALID");return;
      }
      selectedFile.current=file;setResult(value);
    }catch(cause){
      if(epoch.current===request)setError(errCode(cause));
    }finally{if(epoch.current===request)setBusy(false);}
  };
  return e("div",{className:"network-import-overlay","data-office-p1b-overlay":"true"},
    e("section",{className:"network-import-panel",role:"dialog","aria-modal":"true",
      tabIndex:-1,ref:focus,"aria-label":"Reviewed DOCX/ODT nodes into Builder",
      "data-office-p1b-panel":"REVIEW_REQUIRED"},
      e("div",{className:"network-import-heading"},
        e("div",null,e("h2",null,"Review DOCX/ODT nodes into Builder"),
          e("p",null,"Choose individual original table cells, not whole rows or documents. All modeled resources are unverified.")),
        e("button",{type:"button",onClick:close,"data-office-p1b-top-close":"true"},"Close")),
      e("label",{className:"file-button"},"Choose local .docx or .odt",
        e("input",{type:"file",accept:".docx,.odt",hidden:true,
          "data-office-p1b-file":"true",
          onClick:reset,onCancel:reset,
          onChange:event=>{
            const file=event.currentTarget.files?.[0]??null;
            event.currentTarget.value="";
            void choose(file);
          }})),
      error?e("p",{role:"alert","data-office-p1b-error":"BLOCKED"},error):null,
      result?e(OfficeReviewedNodeChoices,{
        key:result.preview.sourceSha256+":"+epoch.current,
        result,manualRoleOptions,busy,setBusy,setError,
        onConfirm:async decision=>{
          const request=epoch.current,original=selectedFile.current;
          const isCurrent=()=>epoch.current===request&&selectedFile.current===original;
          if(!original || !isCurrent() || typeof onConfirm!=="function"){
            const error=new Error("IC040_P1B_STALE");error.code="IC040_P1B_STALE";throw error;
          }
          return onConfirm(result,decision,original,isCurrent);
        }
      }):e("p",{"data-office-p1b-empty":"true"},"No original selected. Existing Builder and Engine unchanged."),
      e("div",{className:"network-import-actions"},
        e("button",{type:"button","data-office-p1b-cancel":"true",onClick:close},
          "Close without Builder changes"))));
}

/** Metadata-only choices; no original text or source filenames rendered. */
export function OfficeReviewedNodeChoices({
  result,manualRoleOptions=["resource.generic"],busy=false,
  setBusy=()=>{},setError=()=>{},onConfirm,
}){
  const [choice,setChoice]=useState(""),[nodes,setNodes]=useState([]),
        [peerChoice,setPeerChoice]=useState(""),[connections,setConnections]=useState([]),
        [connectionAck,setConnectionAck]=useState(false),
        [modeledAck,setModeledAck]=useState(false),[sending,setSending]=useState(false),
        [localError,setLocalError]=useState("");
  const choices=[];
  for(const table of result.preview.tables.slice(0,4)){
    for(const row of table.rows.slice(1,21)){
      for(const cell of row.cells.slice(0,4)){
        choices.push({tableOrdinal:table.tableOrdinal,rowOrdinal:row.rowOrdinal,
          nodeIdCellOrdinal:cell.cellOrdinal});
      }
    }
  }
  const selectable=new Map(choices.map(n=>[keyOf(n),n]));
  const present=new Set(nodes.map(keyOf));
  const peerKey=v=>[v.fromNodeIndex,v.peerCellOrdinal].join(":");
  const peerOptions=nodes.flatMap((n,fromNodeIndex)=>
    (result.preview.tables[n.tableOrdinal]?.rows[n.rowOrdinal]?.cells??[])
      .slice(0,4).filter(cell=>cell.cellOrdinal!==n.nodeIdCellOrdinal)
      .map(cell=>({fromNodeIndex,peerCellOrdinal:cell.cellOrdinal})));
  const peerAvailable=new Map(peerOptions.map(x=>[peerKey(x),x]));
  const peerPresent=new Set(connections.map(peerKey));
  const canSubmit=nodes.length>=1 && nodes.length<=MAX &&
    nodes.every(n=>n.acknowledgeCell===true)&&modeledAck&&
    connections.every(c=>c.acknowledgePeerCell===true)&&
    (connections.length===0||connectionAck)&&
    !busy&&!sending&&typeof onConfirm==="function";
  const clear=()=>{
    setModeledAck(false);setConnectionAck(false);setLocalError("");setError("");
  };
  const add=()=>{
    const available=selectable.get(choice);
    if(!available || present.has(choice) || nodes.length>=MAX){
      setLocalError("IC040_P1B_NODE_DECISION_INVALID");return;
    }
    setNodes(prev=>[...prev,{...available,role:"resource.generic",acknowledgeCell:false}]);
    setChoice("");clear();
  };
  const edit=(key,patch)=>{
    setNodes(prev=>prev.map(n=>keyOf(n)===key?{...n,...patch}:n));
    clear();
  };
  const remove=key=>{
    setNodes(prev=>prev.filter(n=>keyOf(n)!==key));
    // Link source is a selected node INDEX. Never preserve stale indices after
    // node removal/reordering; require a fresh explicit peer review.
    setConnections([]);setPeerChoice("");clear();
  };
  const addConnection=()=>{
    const selected=peerAvailable.get(peerChoice);
    if(!selected||peerPresent.has(peerChoice)||connections.length>=MAX){
      setLocalError("IC040_P2_LINK_DECISION_INVALID");return;
    }
    setConnections(prev=>[...prev,{...selected,acknowledgePeerCell:false}]);
    setPeerChoice("");clear();
  };
  const editConnection=(key,checked)=>{
    setConnections(prev=>prev.map(x=>peerKey(x)===key
      ?{...x,acknowledgePeerCell:checked}:x));
    clear();
  };
  const removeConnection=key=>{
    setConnections(prev=>prev.filter(x=>peerKey(x)!==key));
    clear();
  };
  const submit=async()=>{
    if(!canSubmit)return;
    setSending(true);setBusy(true);setError("");setLocalError("");
    const decision={format:result.format,sourceSha256:result.preview.sourceSha256,
      nodes:nodes.map(n=>({...n})),acknowledgeModeledResources:modeledAck};
    // Keep the P1a/P1b exact legacy decision shape when no link was selected.
    if(connections.length){
      decision.connections=connections.map(x=>({...x}));
      decision.acknowledgeModeledConnections=connectionAck;
    }
    try{await onConfirm(decision);}
    catch(cause){setLocalError(errCode(cause));}
    finally{setBusy(false);setSending(false);}
  };
  return e("section",{className:"network-import-preview","data-office-p1b-controls":"REVIEW_REQUIRED"},
    e("h3",null,result.format.toUpperCase()+" — original table cell review"),
    e("p",{"data-office-p1b-source-sha":"true"},result.preview.sourceSha256),
    e("p",{"data-office-p1b-counts":"true"},
      "Tables: "+result.preview.tables.length+" · structural cells: "+result.preview.totalCells),
    e("p",{"data-office-p1b-truth-boundary":"true"},
      "Only first four tables, first 20 non-header rows and first four cells per row can be selected. Only individually acknowledged peer cells may become modeled links; no source text, OS, IP, ports, physical cabling, Runtime or Engine PASS is inferred."),
    e("label",null,"Original cell position (never the header)",
      e("select",{value:choice,disabled:busy||sending,
        "data-office-p1b-cell-ordinal":"true",onChange:event=>{
          setChoice(event.currentTarget.value);clear();
        }},
        e("option",{value:""},"Choose an original cell…"),
        ...choices.map(n=>e("option",{key:keyOf(n),value:keyOf(n)},
          "Table "+(n.tableOrdinal+1)+" · row "+(n.rowOrdinal+1)+
          " · cell "+(n.nodeIdCellOrdinal+1))))),
    e("button",{type:"button",disabled:!choice||present.has(choice)||nodes.length>=MAX||busy||sending,
      "data-office-p1b-add":"true",onClick:add},"Add cell for individual consent"),
    e("p",{"data-office-p1b-selected-count":String(nodes.length)},
      "Cells selected: "+nodes.length+" / "+MAX+"; no unselected cell may become a node."),
    e("ol",{className:"validation-list"},...nodes.map(n=>{
      const key=keyOf(n);
      return e("li",{key,"data-office-p1b-selection":key},
        e("span",null,"Table "+(n.tableOrdinal+1)+" · row "+(n.rowOrdinal+1)+" · cell "+(n.nodeIdCellOrdinal+1)+" (not yet verified) "),
        e("label",null,"Operator-assigned modeled role ",
          e("select",{value:n.role,disabled:busy||sending,
            "data-office-p1b-role":key,
            onChange:event=>edit(key,{role:event.currentTarget.value,acknowledgeCell:false})},
            ...manualRoleOptions.map(role=>e("option",{key:role,value:role},role)))),
        e("label",null,e("input",{type:"checkbox",checked:n.acknowledgeCell,
          disabled:busy||sending,"data-office-p1b-cell-ack":key,
          onChange:event=>edit(key,{acknowledgeCell:event.currentTarget.checked})}),
          " I independently authorize use of ONLY this selected original cell as an unverified modeled node ID."),
        e("button",{type:"button",disabled:busy||sending,
          "data-office-p1b-remove":key,onClick:()=>remove(key)},"Remove"));
    })),
    e("h4",{"data-office-p2-title":"REVIEW_REQUIRED"},
      "Optional individually reviewed original peer cells"),
    e("p",{"data-office-p2-boundary":"UNVERIFIED"},
      "Choose a peer cell from an individually selected node's SAME original row. "+
      "It must contain another selected node ID, or import BLOCKS. At most four connections; "+
      "no port, cable, interface, physical verification or network PASS inferred."),
    e("label",null,"Original row's peer cell position",
      e("select",{value:peerChoice,disabled:busy||sending||nodes.length<2,
        "data-office-p2-peer-choice":"true",
        onChange:event=>{setPeerChoice(event.currentTarget.value);clear();}},
        e("option",{value:""},"Choose explicitly documented peer cell…"),
        ...peerOptions.map(x=>e("option",{key:peerKey(x),value:peerKey(x)},
          "Selected node "+(x.fromNodeIndex+1)+" · original peer cell "+(x.peerCellOrdinal+1))))),
    e("button",{type:"button",disabled:!peerChoice||peerPresent.has(peerChoice)||
      connections.length>=MAX||busy||sending,
      "data-office-p2-add":"true",onClick:addConnection},
      "Review this explicitly declared peer cell"),
    e("p",{"data-office-p2-selected-count":String(connections.length)},
      "Reviewed peer cells: "+connections.length+" / "+MAX+"; only exact selected node IDs can be endpoints."),
    e("ol",{className:"validation-list"},...connections.map(link=>{
      const key=peerKey(link);
      return e("li",{key,"data-office-p2-selection":key},
        e("span",null,"Selected node "+(link.fromNodeIndex+1)+
          " · same row, original peer cell "+(link.peerCellOrdinal+1)+" "),
        e("label",null,e("input",{type:"checkbox",checked:link.acknowledgePeerCell,
          disabled:busy||sending,"data-office-p2-peer-ack":key,
          onChange:event=>editConnection(key,event.currentTarget.checked)}),
          " I authorize disclosure of ONLY this original cell to map its exact peer ID."),
        e("button",{type:"button",disabled:busy||sending,
          "data-office-p2-remove":key,onClick:()=>removeConnection(key)},"Remove"));
    })),
    e("label",null,e("input",{type:"checkbox",checked:connectionAck,
      disabled:busy||sending||connections.length===0,
      "data-office-p2-modeled-ack":"true",
      onChange:event=>{setConnectionAck(event.currentTarget.checked);setLocalError("");}}),
      " I explicitly approve ONLY these source-declared peer references as UNVERIFIED modeled Builder connections."),
    e("label",null,e("input",{type:"checkbox",checked:modeledAck,
      disabled:busy||sending||nodes.length===0,"data-office-p1b-modeled-ack":"true",
      onChange:event=>{setModeledAck(event.currentTarget.checked);setLocalError("");}}),
      " I separately acknowledge these are only MODELED Builder resources, not observed machines or proven physical network connectivity."),
    localError?e("p",{role:"alert","data-office-p1b-error":"BLOCKED"},localError):null,
    e("button",{type:"button",disabled:!canSubmit,"data-office-p1b-confirm":"true",
      onClick:()=>{void submit();}},busy||sending?"Rechecking original…":"Validate original and create reviewed Builder draft"));
}
