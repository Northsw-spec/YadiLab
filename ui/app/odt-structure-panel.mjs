import React, { useEffect, useRef, useState } from "react";
const e=React.createElement;
const MAX_VISIBLE_TABLES=20,MAX_VISIBLE_ROWS=30,MAX_VISIBLE_CELLS=16;

export function OdtStructureDetails({ result }) {
  if(!result)return e("p",{"data-odt-empty":"true"},
    "Choose a local .odt file. Only supported table structure is inspected; no document cell text is displayed.");
  const {filename,preview}=result;
  const items=[];
  for(const table of preview.tables.slice(0,MAX_VISIBLE_TABLES)){
    const rows=[];
    for(const row of table.rows.slice(0,MAX_VISIBLE_ROWS)){
      const cells=row.cells.slice(0,MAX_VISIBLE_CELLS).map(cell=>
        e("li",{key:cell.cellOrdinal,
          "data-odt-cell":[table.tableOrdinal,row.rowOrdinal,cell.cellOrdinal].join(":")},
          "Cell "+(cell.cellOrdinal+1)+": "+cell.textCodeUnits+
          " text code units · source table "+(cell.locator.tableOrdinal+1)+
          ", row "+(cell.locator.rowOrdinal+1)+", cell "+(cell.locator.cellOrdinal+1)));
      rows.push(e("li",{key:row.rowOrdinal,
          "data-odt-row":[table.tableOrdinal,row.rowOrdinal].join(":")},
        "Row "+(row.rowOrdinal+1)+": "+row.cells.length+" cells",
        e("ul",{className:"validation-list"},...cells),
        row.cells.length>MAX_VISIBLE_CELLS?e("p",null,"Further cells not displayed."):null));
    }
    if(table.rows.length>MAX_VISIBLE_ROWS)rows.push(
      e("li",{key:"limit"},"Showing first "+MAX_VISIBLE_ROWS+" of "+table.rows.length+" rows."));
    items.push(e("li",{key:table.tableOrdinal,
        "data-odt-table":String(table.tableOrdinal)},
      e("strong",null,"Table "+(table.tableOrdinal+1)+": "+table.rows.length+" rows"),
      e("ol",{className:"validation-list"},...rows)));
  }
  return e("section",{"data-odt-preview":"CONFIG_DOCUMENTED",className:"network-import-preview"},
    e("h3",null,"ODT table structure — ",filename),
    e("p",{"data-odt-summary":"true"},
      "Declared tables: "+preview.tables.length+" · structural cells: "+preview.totalCells),
    e("p",{"data-odt-source-hash":"true"},"Original SHA-256: "+preview.sourceSha256),
    e("p",{"data-odt-truth-boundary":"true",className:"helper-note"},
      "CONFIG_DOCUMENTED, REVIEW_REQUIRED. Table shapes only. No original cell values, source secrets, verified devices, physical links, Builder edits or Engine PASS."),
    e("ol",{"data-odt-tables":"true",className:"validation-list"},...items),
    e("p",{"data-odt-activation-status":"BLOCKED"},
      "Read-only source inspection. Complex ODT tables may be rejected. No network mapping, import, or simulation activation."));
}

export function OdtStructurePanel({ inspectFile,onClose }) {
  const [result,setResult]=useState(null),[error,setError]=useState(""),
        [busy,setBusy]=useState(false);
  const generation=useRef(0),focus=useRef(null);
  useEffect(()=>{focus.current?.focus();return()=>{generation.current++;};},[]);
  useEffect(()=>{
    const escape=event=>{
      if(event.key==="Escape"&&!busy){generation.current++;onClose();}
    };
    document.addEventListener("keydown",escape);
    return()=>document.removeEventListener("keydown",escape);
  },[busy,onClose]);
  const inspect=async file=>{
    if(!file)return;
    const current=++generation.current;
    setResult(null);setError("");setBusy(true);
    try{
      const next=await inspectFile(file);
      if(current===generation.current)setResult(next);
    }catch(cause){
      if(current===generation.current){
        const code=typeof cause?.code==="string" &&
          /^(ODT_|IMPORT_ARCHIVE_|IMPORT_WORKBOOK_ARCHIVE_|IMPORT_XML_)[A-Z_]+$/.test(cause.code)
          ?cause.code:"ODT_INSPECTION_BLOCKED";
        setError(code);
      }
    }finally{
      if(current===generation.current)setBusy(false);
    }
  };
  return e("div",{className:"network-import-overlay","data-odt-overlay":"true"},
    e("section",{className:"network-import-panel",role:"dialog","aria-modal":"true",
        "aria-label":"OpenDocument ODT table structure inspection",ref:focus,tabIndex:-1,
        "data-odt-panel":"CONFIG_DOCUMENTED"},
      e("div",{className:"network-import-heading"},
        e("div",null,
          e("h2",null,"Inspect OpenDocument ODT — structure only"),
          e("p",null,"Local, read-only; source cell values are never displayed or imported.")),
        e("button",{type:"button",disabled:busy,
          "aria-label":"Close ODT inspection",onClick:()=>{
            generation.current++;onClose();
          }},"Close")),
      e("label",{className:"file-button"},busy?"Reading ODT structure…":"Choose .odt file",
        e("input",{type:"file",accept:".odt",hidden:true,disabled:busy,
          "data-odt-file":"true",onChange:event=>{
            const file=event.currentTarget.files?.[0];
            event.currentTarget.value="";
            if(file)void inspect(file);
          }})),
      error?e("p",{role:"alert",className:"helper-status blocked",
        "data-odt-error":"BLOCKED"},error):null,
      e(OdtStructureDetails,{result}),
      e("div",{className:"network-import-actions"},
        e("button",{type:"button",disabled:busy,"data-odt-close":"true",
          onClick:()=>{generation.current++;onClose();}},"Close without changes"))));
}
