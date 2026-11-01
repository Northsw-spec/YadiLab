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
from run_docx_p2_real_browser import make_bytes as docx_bytes, CANARY as DOCX_CANARY
from run_odt_p2_real_browser import make_odt as odt_bytes, CANARY as ODT_CANARY
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
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("FAIL IC-040 P1b real compiled Chromium: "+str(exc),file=sys.stderr)
        raise
