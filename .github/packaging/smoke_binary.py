"""Compiled standalone Linux binary integration smoke, exact main."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

PROGRAM = pathlib.Path("dist/NetworkLab").resolve()
PROJECT = {"schemaVersion":"1.4","name":"Compiled application smoke","zones":[],"nodes":[],"links":[]}

def request(port, path, body=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type":"application/json"} if data is not None else {})
    with urllib.request.urlopen(req, timeout=2) as res:
        return res.status, res.read()

def start(port, data_dir):
    p = subprocess.Popen([str(PROGRAM), "--no-browser","--port",str(port),"--data-dir",str(data_dir)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for _ in range(80):
        if p.poll() is not None:
            stdout,stderr=p.communicate()
            raise RuntimeError(f"binary exited {p.returncode}: {stdout!r} / {stderr!r}")
        try:
            status, payload=request(port,"/api/health")
            if status==200:
                info=json.loads(payload)
                assert info["version"]=="0.1.0",info
                assert info["storage"]=="local",info
                return p
        except (OSError,urllib.error.URLError,TimeoutError):
            pass
        time.sleep(0.25)
    p.terminate()
    raise RuntimeError("binary did not start serving /api/health")

def stop(p):
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
    if p.stdout: p.stdout.close()
    if p.stderr: p.stderr.close()

assert PROGRAM.is_file(), PROGRAM
with tempfile.TemporaryDirectory() as tmp:
    store=pathlib.Path(tmp)/"projects"
    a=start(18765,store)
    try:
        status,html=request(18765,"/")
        assert status==200 and b"Network Lab" in html and b"CANONICAL NETWORK LAB" in html
        status,js=request(18765,"/app.js")
        assert status==200 and len(js)>20000
        status,mod=request(18765,"/features/projects/import-review.js")
        assert status==200 and b"countCandidateVlans" in mod
        status,css=request(18765,"/styles.css")
        assert status==200 and len(css)>500
        status,raw=request(18765,"/api/validate",PROJECT)
        normalized=json.loads(raw)["project"]
        assert normalized==PROJECT,normalized
        status,raw=request(18765,"/api/save",{"filename":"compiled-smoke","project":PROJECT,"expectedSha256":None})
        saved=json.loads(raw)
        assert status==200
        fn=store/"compiled-smoke.yadilab"
        assert fn.is_file()
        data=fn.read_bytes()
        assert saved["sha256"]==hashlib.sha256(data).hexdigest()
    finally:
        stop(a)
    b=start(18766,store)
    try:
        status,raw=request(18766,"/api/projects/compiled-smoke")
        reopened=json.loads(raw)
        assert status==200 and reopened["project"]==PROJECT
        assert reopened["sha256"]==saved["sha256"]
        assert fn.read_bytes()==data
    finally:
        stop(b)
print("PASS frozen Linux ELF: HTTP, static frontend, canonical validation, SHA256 Save/Open after full process restart")
