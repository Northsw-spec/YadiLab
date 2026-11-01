#!/usr/bin/env python3
"""IC-040 P1b exact compiled Chromium, individual original Office cell Builder decisions."""
import argparse
import io
import json
import os
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
from run_docx_p2_real_browser import make_bytes as docx_bytes, CANARY as DOCX_CANARY, WORD, OPC_REL, OPC_TYPES, OFFICE_REL, MAIN_TYPE
from run_odt_p2_real_browser import make_odt as odt_bytes, CANARY as ODT_CANARY, MIME, OFFICE, TABLE, TEXT, MANIFEST
from run_ic010_p2_shared_xml_real_browser import setup, exported_source, require, menu

def make_changed(original,filename):
    candidates=[]
    for number in "23456789":
        target=("node0"+number).encode()
        out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original),"r") as src, zipfile.ZipFile(out,"w") as dest:
            for item in src.infolist():
                body=src.read(item.filename)
                if item.filename==filename:
                    require(b"node01" in body,"Valid original must contain selected node01")
                    body=body.replace(b"node01",target)
                item.extra=b""
                dest.writestr(item,body)
        changed=out.getvalue()
        if len(changed)==len(original) and changed!=original:
            return changed
        candidates.append(len(changed))
    raise AssertionError("Could not produce independent valid same-byte-length Office ZIP "+str(candidates))

def opening(page):
    menu(page).locator('[data-review-office-builder="REVIEW_REQUIRED"]').click()
    expect(page.locator('[data-office-p1b-panel="REVIEW_REQUIRED"]')).to_be_visible(timeout=18000)

def choose(page,ext,data):
    page.locator('[data-office-p1b-file="true"]').set_input_files({
      "name":"reviewed."+ext,"mimeType":"application/octet-stream","buffer":data})
    expect(page.locator('[data-office-p1b-controls="REVIEW_REQUIRED"]')).to_be_visible(timeout=26000)
    require(page.locator('[data-office-p1b-selected-count="0"]').count()==1,
            "Any default node selection must be forbidden")
    require(page.locator('[data-office-p1b-confirm]').is_disabled(),
            "Unconsented Office import enabled")
    for text in [DOCX_CANARY,ODT_CANARY,"node01","Host","Address","<w:t>IP</w:t>"]:
        require(text not in page.locator('[data-office-p1b-panel]').inner_html(),
                "Raw private/original Office cell content leaked into DOM: "+text)

def choose_one(page):
    page.locator('[data-office-p1b-cell-ordinal]').select_option("0:1:0")
    page.locator('[data-office-p1b-add]').click()
    require(page.locator('[data-office-p1b-confirm]').is_disabled(),"Per-cell or global consent absent")
    role=page.locator('[data-office-p1b-role="0:1:0"]')
    role.select_option("network.router")
    require(page.locator('[data-office-p1b-confirm]').is_disabled(),"Role selection implicitly approved cell")
    page.locator('[data-office-p1b-cell-ack="0:1:0"]').check()
    require(page.locator('[data-office-p1b-confirm]').is_disabled(),"Separate modeled acknowledgment absent")
    page.locator('[data-office-p1b-modeled-ack]').check()
    require(page.locator('[data-office-p1b-confirm]').is_enabled(),"Fully consented original node blocked")

def patch_file_reads(page,ext,changed,mode):
    page.evaluate("""({name,changed,mode})=>{
       const original=File.prototype.arrayBuffer;
       const bytes=new Uint8Array(changed);
       window.__ic040_p1b_reads=0;
       window.__ic040_p1b_interrupted=0;
       File.prototype.arrayBuffer=function(){
         if(this.name===name){
           window.__ic040_p1b_reads++;
           if(window.__ic040_p1b_reads>=3 && mode==="swap")
             return Promise.resolve(bytes.buffer.slice(0));
           if(window.__ic040_p1b_reads===3 && mode==="workspace"){
             const button=Array.from(document.querySelectorAll("button"))
               .find(b=>b.textContent?.trim()==="Öppna enterprise i byggläget");
             if(!button || button.disabled) throw new Error("IC040_P1B_WORKSPACE_TRIGGER_MISSING");
             button.click();window.__ic040_p1b_interrupted++;
           }
         }
         return original.call(this);
       };
    }""",{"name":"reviewed."+ext,"changed":list(changed),"mode":mode})

def clean(errors,external):
    require(not errors,"Uncaught actual Chromium errors: "+repr(errors))
    require(not external,"Unexpected outbound browser network request: "+repr(external))

def case_cancel(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        before=exported_source(page)
        opening(page);choose(page,ext,original);choose_one(page)
        page.locator('[data-office-p1b-cancel]').click()
        expect(page.locator('[data-office-p1b-panel]')).to_have_count(0,timeout=12000)
        require(exported_source(page)==before,"Cancel changed current Builder")
        clean(errors,external)
        return {"format":ext,"case":"cancel_without_workspace_changes","status":"PASS"}
    finally:page.close()

def case_success(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        patch_file_reads(page,ext,original,"count")
        opening(page);choose(page,ext,original);choose_one(page)
        page.locator('[data-office-p1b-confirm]').click()
        expect(page.locator('[data-office-p1b-panel]')).to_have_count(0,timeout=45000)
        require(page.evaluate("window.__ic040_p1b_reads")>=3,
                "Final original re-read must occur after actual compiler and layout")
        src=exported_source(page)
        require(src["scenarioId"]=="office_reviewed","Wrong canonical Builder scenario identity")
        require(len(src["resources"])==1 and src["resources"][0]["id"]=="node01" and
                src["resources"][0]["type"]=="network.router",
                "Only consented original cell and manual role should enter Builder")
        require(src["connections"]==[],"Invented physical links from Office cell")
        require(src["tests"]==[],"Invented Engine probes from Office cell")
        require(src["completion"]["path"]=="office_manual_verification",
                "Unfulfilled independent verification objective missing")
        require(page.locator(".app-frame").get_attribute("data-runtime-scenario-hash")=="builder",
                "Office import unexpectedly activated Runtime")
        require(DOCX_CANARY not in json.dumps(src) and ODT_CANARY not in json.dumps(src),
                "Non-selected private Office cell copied into Builder")
        clean(errors,external)
        return {"format":ext,"case":"one_consented_original_node_only_builder","status":"PASS","reread":True}
    finally:page.close()

def case_swap(browser,url,ext,original,changed):
    page,errors,external=setup(browser,url)
    try:
        before=exported_source(page)
        patch_file_reads(page,ext,changed,"swap")
        opening(page);choose(page,ext,original);choose_one(page)
        page.locator('[data-office-p1b-confirm]').click()
        expect(page.locator('[data-office-p1b-error="BLOCKED"]')).to_contain_text(
            "IC040_P1B_SOURCE_CHANGED",timeout=45000)
        require(page.evaluate("window.__ic040_p1b_reads")>=3,
                "Same-size independent original ZIP mutation was not actually re-read")
        page.locator('[data-office-p1b-cancel]').click()
        require(exported_source(page)==before,"Swapped Office ZIP overwrote Builder")
        clean(errors,external)
        return {"format":ext,"case":"valid_same_size_modified_original_rejected","status":"PASS"}
    finally:page.close()

def case_workspace(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        before=exported_source(page)
        patch_file_reads(page,ext,original,"workspace")
        opening(page);choose(page,ext,original);choose_one(page)
        page.locator('[data-office-p1b-confirm]').click()
        expect(page.locator('[data-office-p1b-error="BLOCKED"]')).to_contain_text(
            "IC040_P1B_WORKSPACE_CHANGED",timeout=45000)
        require(page.evaluate("window.__ic040_p1b_interrupted")==1,
                "No real competing Builder action triggered during final source read")
        page.locator('[data-office-p1b-cancel]').click()
        src=exported_source(page)
        require(src!=before and src["scenarioId"]!="office_reviewed",
                "Competing latest Builder was replaced by stale Office import")
        clean(errors,external)
        return {"format":ext,"case":"real_competing_builder_change_blocks_old_file","status":"PASS"}
    finally:page.close()

def case_invalid(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        before=exported_source(page)
        opening(page);choose(page,ext,original);choose_one(page)
        page.locator('[data-office-p1b-file="true"]').set_input_files({
            "name":"invalid."+ext,"mimeType":"application/octet-stream","buffer":b"not a zip!"})
        expect(page.locator('[data-office-p1b-error="BLOCKED"]')).to_be_visible(timeout=20000)
        require(page.locator('[data-office-p1b-controls]').count()==0,
                "Old individual consents survived invalid file replacement")
        page.locator('[data-office-p1b-cancel]').click()
        require(exported_source(page)==before,"Invalid Office source changed Builder")
        clean(errors,external)
        return {"format":ext,"case":"invalid_new_zip_clears_old_consents","status":"PASS"}
    finally:page.close()


# P2 uses the same actual compiled Chromium and original-source reread chain.
# An explicitly selected original peer cell is NOT proof of physical cabling.
def make_reviewed_peers(original,part,ext,missing=False,reciprocal=False):
    require(not (missing and reciprocal),"Mutually exclusive source fixture variants")
    second_peer=b"fw01" if reciprocal else b"rt01"
    target=b"ghost" if missing else b"sw01"
    if ext=="docx":
        def xmlcell(value):
            return b"<w:tc><w:tcPr/><w:p><w:r><w:t>"+value+b"</w:t></w:r></w:p></w:tc>"
        additions=b"".join(b"<w:tr>"+xmlcell(a)+xmlcell(b)+b"</w:tr>" for a,b in
                           [(b"sw01",second_peer),(b"rt01",b"")])
        closing=b"</w:tbl>"
        canary=DOCX_CANARY.encode()
    else:
        def xmlcell(value):
            return b'<table:table-cell office:value-type="string"><text:p>'+value+b"</text:p></table:table-cell>"
        additions=b"".join(b"<table:table-row>"+xmlcell(a)+xmlcell(b)+b"</table:table-row>" for a,b in
                           [(b"sw01",second_peer),(b"rt01",b"")])
        closing=b"</table:table>"
        canary=ODT_CANARY.encode()
    out=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original),"r") as src,zipfile.ZipFile(out,"w") as dest:
        for item in src.infolist():
            data=src.read(item.filename)
            if item.filename==part:
                require(b"node01" in data and canary in data and closing in data,
                        "P2 original document must contain exact source rows")
                data=data.replace(b"node01",b"fw01").replace(canary,target)
                data=data.replace(closing,additions+closing,1)
            item.extra=b""
            dest.writestr(item,data)
    return out.getvalue()

def choose_reviewed_peers(page):
    for offset,role in enumerate(["network.firewall","network.switch","network.router"]):
        key="0:"+str(offset+1)+":0"
        page.locator('[data-office-p1b-cell-ordinal="true"]').select_option(key)
        page.locator('[data-office-p1b-add="true"]').click()
        page.locator('[data-office-p1b-role="'+key+'"]').select_option(role)
        page.locator('[data-office-p1b-cell-ack="'+key+'"]').check()
    expect(page.locator('[data-office-p1b-selected-count="3"]')).to_be_visible(timeout=10000)
    for key in ["0:1","1:1"]:
        page.locator('[data-office-p2-peer-choice="true"]').select_option(key)
        page.locator('[data-office-p2-add="true"]').click()
        page.locator('[data-office-p2-peer-ack="'+key+'"]').check()
    expect(page.locator('[data-office-p2-selected-count="2"]')).to_be_visible()
    require(page.locator('[data-office-p1b-confirm]').is_disabled(),
            "P2 enabled commit before both independent modeled acknowledgments")
    page.locator('[data-office-p2-modeled-ack="true"]').check()
    page.locator('[data-office-p1b-modeled-ack="true"]').check()
    expect(page.locator('[data-office-p1b-confirm="true"]')).to_be_enabled()

def case_p2_real_links(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        opening(page);choose(page,ext,original);choose_reviewed_peers(page)
        page.locator('[data-office-p1b-confirm="true"]').click()
        expect(page.locator('[data-office-p1b-panel]')).to_have_count(0,timeout=45000)
        source=exported_source(page)
        require(source["scenarioId"]=="office_reviewed","Wrong Office Builder scenario")
        types={x["id"]:x["type"] for x in source["resources"]}
        require(types=={"fw01":"network.firewall","sw01":"network.switch","rt01":"network.router"},
                "P2 wrong or missing original node IDs/roles")
        pairs={(x["from"]["resource"],x["to"]["resource"]) for x in source["connections"]}
        require(pairs=={("fw01","sw01"),("sw01","rt01")} and len(source["connections"])==2,
                "P2 wrong/extra/silent missing original documented peer link")
        require(all(not x["from"].get("port") and not x["to"].get("port")
                    for x in source["connections"]),"P2 invented source-absent ports")
        require(source["tests"]==[] and source["completion"]["path"]=="office_manual_verification",
                "P2 self-certified Engine PASS from documented peer text")
        panel=page.locator(".topology-panel")
        expect(panel).to_have_attribute("data-topology-edge-count","2",timeout=30000)
        nodes=panel.locator('.react-flow__node[data-id]')
        expect(nodes).to_have_count(3,timeout=30000)
        seen={}
        for i in range(nodes.count()):
            node=nodes.nth(i)
            key=node.get_attribute("data-id")
            shape=node.locator(".resource-node[data-device-family]")
            require(shape.count()==1 and key not in seen,"P2 duplicate or missing drawn node")
            seen[key]=shape.get_attribute("data-device-family")
        require(seen=={"fw01":"firewall","sw01":"switch","rt01":"router"},
                "P2 actual drawn device identities/families wrong")
        edges=panel.locator('.react-flow__edge[data-id]')
        expect(edges).to_have_count(2,timeout=30000)
        actual=set()
        for i in range(edges.count()):
            path=edges.nth(i).locator("path.react-flow__edge-path.semantic-edge")
            require(path.count()==1,"P2 missing drawn SVG edge path")
            require(path.get_attribute("data-connection-kind")=="network","P2 wrong drawn edge kind")
            actual.add((path.get_attribute("data-connection-source"),
                        path.get_attribute("data-connection-target")))
        require(actual==pairs,"P2 visible ReactFlow link endpoints differ from document")
        require(page.locator(".app-frame").get_attribute("data-runtime-scenario-hash")=="builder",
                "P2 unexpectedly entered Engine Runtime")
        clean(errors,external)
        return {"format":ext,"case":"actual_drawn_three_nodes_two_source_peer_edges","status":"PASS"}
    finally:page.close()

def case_p2_unknown_peer(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        before=exported_source(page)
        opening(page);choose(page,ext,original);choose_reviewed_peers(page)
        page.locator('[data-office-p1b-confirm="true"]').click()
        expect(page.locator('[data-office-p1b-error="BLOCKED"]')).to_contain_text(
            "IC040_P2_LINK_ENDPOINT_UNKNOWN",timeout=45000)
        page.locator('[data-office-p1b-cancel]').click()
        require(exported_source(page)==before,"P2 unknown document peer replaced existing Builder")
        clean(errors,external)
        return {"format":ext,"case":"unknown_peer_blocked_workspace_unchanged","status":"PASS"}
    finally:page.close()

def case_p2_reciprocal_peer(browser,url,ext,original):
    page,errors,external=setup(browser,url)
    try:
        before=exported_source(page)
        opening(page);choose(page,ext,original);choose_reviewed_peers(page)
        page.locator('[data-office-p1b-confirm="true"]').click()
        expect(page.locator('[data-office-p1b-error="BLOCKED"]')).to_contain_text(
            "IC040_P2_DUPLICATE_CONNECTION",timeout=45000)
        # A rejected modal deliberately remains open and intercepts pointer
        # events; dismiss it before opening the underlying export menu.
        page.locator('[data-office-p1b-cancel]').click()
        expect(page.locator('[data-office-p1b-panel]')).to_have_count(0,timeout=12000)
        require(exported_source(page)==before,
                "Reciprocal document declaration silently created two parallel cables")
        clean(errors,external)
        return {"format":ext,"case":"reciprocal_peer_pair_blocked_without_phantom_cable","status":"PASS"}
    finally:page.close()

P3_PRIVATE_CANARY="PRIVATE_PORTS_ORIGINAL_NOT_DISCLOSED_3001"
P3_ROWS=[
    ["Device","Peer","Local Port","Remote Port","Private"],
    ["fw01","sw01","eth0","eth1",P3_PRIVATE_CANARY],
    ["sw01","rt01","eth2","eth0","SECOND_PRIVATE_PORTS_3002"],
    ["rt01","","","","THIRD_PRIVATE_PORTS_3003"],
]

def make_p3_office(ext,rows=None):
    rows=rows or P3_ROWS
    if ext=="docx":
        cell=lambda s:'<w:tc><w:tcPr/><w:p><w:r><w:t>'+s+'</w:t></w:r></w:p></w:tc>'
        body=('<w:document xmlns:w="'+WORD+'"><w:body><w:tbl><w:tblPr/><w:tblGrid/>'+
             ''.join('<w:tr>'+''.join(cell(value) for value in row)+'</w:tr>' for row in rows)+
             '</w:tbl></w:body></w:document>')
        types=('<Types xmlns="'+OPC_TYPES+'"><Override PartName="/word/document.xml" ContentType="'+
               MAIN_TYPE+'"/></Types>')
        rels=('<Relationships xmlns="'+OPC_REL+'"><Relationship Id="rId1" Type="'+
              OFFICE_REL+'" Target="word/document.xml"/></Relationships>')
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as package:
            for name,data in [("[Content_Types].xml",types),
                              ("_rels/.rels",rels),("word/document.xml",body)]:
                package.writestr(name,data)
        return out.getvalue()
    cell=lambda s:'<table:table-cell office:value-type="string"><text:p>'+s+'</text:p></table:table-cell>'
    table=('<table:table table:name="Inventory"><table:table-column/>'+
           ''.join('<table:table-row>'+''.join(cell(value) for value in row)+
                   '</table:table-row>' for row in rows)+'</table:table>')
    body=('<office:document-content xmlns:office="'+OFFICE+
          '" xmlns:table="'+TABLE+'" xmlns:text="'+TEXT+
          '" office:version="1.3"><office:body><office:text>'+
          table+'</office:text></office:body></office:document-content>')
    manifest=('<manifest:manifest xmlns:manifest="'+MANIFEST+'" manifest:version="1.3">'+
              '<manifest:file-entry manifest:full-path="/" manifest:media-type="'+MIME+'"/>'+
              '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'+
              '</manifest:manifest>')
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as package:
        info=zipfile.ZipInfo("mimetype",(1980,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_STORED
        info.extra=b""
        package.writestr(info,MIME.encode("ascii"))
        package.writestr("content.xml",body.encode(),compress_type=zipfile.ZIP_DEFLATED)
        package.writestr("META-INF/manifest.xml",manifest.encode(),compress_type=zipfile.ZIP_DEFLATED)
    return out.getvalue()

def choose_p3_ports(page):
    choose_reviewed_peers(page)
    for index in range(2):
        index_text=str(index)
        page.locator('[data-office-p3-link-choice="true"]').select_option(index_text)
        page.locator('[data-office-p3-source-choice="true"]').select_option("2")
        page.locator('[data-office-p3-peer-choice="true"]').select_option("3")
        page.locator('[data-office-p3-add="true"]').click()
        require(page.locator('[data-office-p1b-confirm]').is_disabled(),
                "P3 allowed import before explicit separate port-cell consent")
        page.locator('[data-office-p3-source-ack="'+index_text+'"]').check()
        page.locator('[data-office-p3-peer-ack="'+index_text+'"]').check()
    require(page.locator('[data-office-p3-selected-count="2"]').count()==1,
            "P3 did not review exactly two port pairs")
    require(page.locator('[data-office-p1b-confirm]').is_disabled(),
            "P3 missing modeled-port acknowledgment enabled import")
    page.locator('[data-office-p2-modeled-ack="true"]').check()
    page.locator('[data-office-p1b-modeled-ack="true"]').check()
    page.locator('[data-office-p3-modeled-ack="true"]').check()
    expect(page.locator('[data-office-p1b-confirm="true"]')).to_be_enabled()

def case_p3_real_ports(browser,url,ext):
    page,errors,external=setup(browser,url)
    try:
        original=make_p3_office(ext)
        opening(page);choose(page,ext,original);choose_p3_ports(page)
        require(P3_PRIVATE_CANARY not in page.locator('[data-office-p1b-panel]').inner_html(),
                "Unselected original port-document private cell was exposed")
        page.locator('[data-office-p1b-confirm="true"]').click()
        expect(page.locator('[data-office-p1b-panel]')).to_have_count(0,timeout=45000)
        source=exported_source(page)
        require({x["id"]:x["type"] for x in source["resources"]}==
                {"fw01":"network.firewall","sw01":"network.switch","rt01":"network.router"},
                "P3 source IDs/roles not source and review accurate")
        ifaces={x["id"]:sorted(i["id"] for i in x.get("interfaces",[]))
                for x in source["resources"]}
        require(ifaces=={"fw01":["eth0"],"sw01":["eth1","eth2"],"rt01":["eth0"]},
                "P3 invented, lost or reassigned port interface IDs")
        actual={c["id"]:(c["from"]["resource"],c["from"].get("port"),
                        c["to"]["resource"],c["to"].get("port"))
                for c in source["connections"]}
        require(len(actual)==2 and set(actual.values())==
                {("fw01","eth0","sw01","eth1"),("sw01","eth2","rt01","eth0")},
                "P3 real Builder source endpoint ports differ from original Office cells")
        require(source["completion"]["path"]=="office_manual_verification" and source["tests"]==[],
                "P3 falsely certified Engine completion or probes")
        require(all(secret not in json.dumps(source) for secret in
                [P3_PRIVATE_CANARY,"SECOND_PRIVATE_PORTS_3002","THIRD_PRIVATE_PORTS_3003"]),
                "P3 copied unreviewed private Office original cell")
        panel=page.locator(".topology-panel")
        expect(panel.locator('.react-flow__node[data-id]')).to_have_count(3,timeout=30000)
        expect(panel.locator('.react-flow__edge[data-id]')).to_have_count(2,timeout=30000)
        seen={}
        for edge in panel.locator('.react-flow__edge[data-id]').all():
            path=edge.locator("path.react-flow__edge-path.semantic-edge")
            require(path.count()==1,"P3 missing actual rendered semantic edge")
            geom=path.get_attribute("d")
            require(bool(geom and geom.strip()) and "NaN" not in geom,
                    "P3 invalid drawn SVG edge geometry")
            seen[edge.get_attribute("data-id")]=(
                path.get_attribute("data-connection-source"),
                path.get_attribute("data-connection-source-port"),
                path.get_attribute("data-connection-target"),
                path.get_attribute("data-connection-target-port"))
        require(seen==actual,"P3 actual ReactFlow SVG port/endpoint identities differ from source")
        handles={(node.get_attribute("data-id"),
                   handle.get_attribute("data-interface-id"))
                 for node in panel.locator('.react-flow__node[data-id]').all()
                 for handle in node.locator('[data-interface-id]').all()}
        require(all((node,port) in handles for node,ports in ifaces.items() for port in ports),
                "P3 actual visible resource node missing original interface handle")
        require(page.locator(".app-frame").get_attribute("data-runtime-scenario-hash")=="builder",
                "P3 silently activated Engine/Runtime")
        clean(errors,external)
        return {"format":ext,"case":"original_four_ports_two_exact_drawn_endpoints","status":"PASS"}
    finally:page.close()

def case_p3_bad_port(browser,url,ext,mode):
    page,errors,external=setup(browser,url)
    try:
        rows=[list(row) for row in P3_ROWS]
        if mode=="reused":
            rows[2][2]="eth1"
            expected="IC040_P3_PORT_REUSED"
        elif mode=="invalid":
            rows[1][2]="Gi1/0/1"
            expected="IC040_P3_PORT_INVALID"
        elif mode=="sensitive":
            rows[1][2]="PASSWORD=canary"
            expected="DOCX_CELL_SENSITIVE_BLOCKED" if ext=="docx" else "ODT_CELL_SENSITIVE_BLOCKED"
        else:raise AssertionError("Unknown P3 fixture "+mode)
        before=exported_source(page)
        opening(page);choose(page,ext,make_p3_office(ext,rows));choose_p3_ports(page)
        page.locator('[data-office-p1b-confirm="true"]').click()
        expect(page.locator('[data-office-p1b-error="BLOCKED"]')).to_contain_text(expected,timeout=45000)
        page.locator('[data-office-p1b-cancel]').click()
        require(exported_source(page)==before,"P3 blocked port decision replaced workspace")
        clean(errors,external)
        return {"format":ext,"case":mode+"_original_port_denied","status":"PASS"}
    finally:page.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    ap.add_argument("--evidence-dir",type=Path,required=True)
    args=ap.parse_args()
    u=urlsplit(args.url)
    require(u.scheme=="http" and u.hostname=="127.0.0.1" and
            u.port is not None and u.path=="/" and not u.query and
            not u.fragment and not u.username and not u.password,
            "Only real loopback compiled YadiLab permitted")
    args.evidence_dir.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        flags=["--disable-background-networking","--disable-dev-shm-usage"]
        if hasattr(os,"geteuid") and os.geteuid()==0:flags.append("--no-sandbox")
        browser=pw.chromium.launch(headless=True,args=flags)
        try:
            cases=[]
            for ext,raw,part in [
                ("docx",docx_bytes(),"word/document.xml"),
                ("odt",odt_bytes(),"content.xml"),
            ]:
                changed=make_changed(raw,part)
                # P2 must use independently valid original ZIPs and real SVG endpoint proof.
                peers=make_reviewed_peers(raw,part,ext)
                unknown=make_reviewed_peers(raw,part,ext,missing=True)
                reciprocal=make_reviewed_peers(raw,part,ext,reciprocal=True)
                cases.append(case_p2_real_links(browser,args.url,ext,peers))
                cases.append(case_p2_unknown_peer(browser,args.url,ext,unknown))
                cases.append(case_p3_real_ports(browser,args.url,ext))
                for mode in ["reused","invalid","sensitive"]:
                    cases.append(case_p3_bad_port(browser,args.url,ext,mode))
                cases.append(case_p2_reciprocal_peer(browser,args.url,ext,reciprocal))
                for run in [
                    lambda:case_cancel(browser,args.url,ext,raw),
                    lambda:case_success(browser,args.url,ext,raw),
                    lambda:case_swap(browser,args.url,ext,raw,changed),
                    lambda:case_workspace(browser,args.url,ext,raw),
                    lambda:case_invalid(browser,args.url,ext,raw),
                ]:
                    cases.append(run())
        finally:browser.close()
    report={"status":"PASS","kind":"IC-040 P1b actual compiled Chromium reviewed Office nodes",
      "platform":"GitHub Actions Ubuntu; Parrot and physical network NOT_RUN",
      "cases":cases,"runtimeActivated":False,"physicalTopologyVerified":False}
    (args.evidence_dir/"ic040-p1b-office-builder-real-chromium.json").write_text(json.dumps(report,indent=2)+"\n")
    print("PASS IC-040 P1b actual compiled Chromium DOCX/ODT original-cell consent, final reread and live Builder race denial")
    print("PASS IC-040 P2 actual compiled Chromium DOCX/ODT exact SVG peer links, unknown and reciprocal peer duplicates blocked")
    print("PASS IC-040 P3 actual DOCX/ODT Chromium source, port handles, exact drawn endpoint port identities and negative denial")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("FAIL IC-040 P1b real compiled Chromium: "+str(exc),file=sys.stderr)
        raise
