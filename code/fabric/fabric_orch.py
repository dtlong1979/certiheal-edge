# -*- coding: utf-8 -*-
"""
Orchestrator (chay tren HOST): dung fabric docker THAT, tiem loi + phan manh, do coverage.
Smoke: 6 agent / 2 site (s0 co-located voi central, s1 edge se bi phan manh), 24 role.
Kich ban: cat site s1 khoi ctrlnet (phan manh THAT) roi giet 1 node edge -> so sanh:
  baseline (field off): chi central cuu -> khong voi toi s1 -> role chet nam chet.
  certiheal(field on) : agent s1 tu cuu qua peernet.
Do coverage bang cach poll cong publish tren host (thay het, doc lap phan manh).
  python fabric_orch.py
"""
import subprocess, json, time, os, urllib.request

HERE=os.path.dirname(os.path.abspath(__file__))
HERES=HERE.replace("\\","/")
CFGPATH=os.path.join(HERE,"fabric_cfg.json").replace("\\","/")
IMG="python:3.11-slim"
N=6; NROLE=24; CAP=6
# site: 0,1,2 -> s0 (an toan) ; 3,4,5 -> s1 (edge, phan manh)
AGENT_SITE={i:("s0" if i<3 else "s1") for i in range(N)}
ROLE_SITE={r:("s0" if r<12 else "s1") for r in range(NROLE)}
AGENTS=[f"fa-{i}" for i in range(N)]
HOSTPORT=lambda i:9000+i

def sh(c,**k): return subprocess.run(c,shell=True,capture_output=True,text=True,**k)
def dq():
    r=sh('docker ps -aq --filter "name=fa-"'); return r.stdout.split()
def cleanup():
    ids=dq()
    if ids: sh("docker rm -f "+" ".join(ids))
def ensure_net(n):
    if not sh(f'docker network inspect {n}').returncode==0: sh(f"docker network create {n}")
def get(url,t=1.5):
    try:
        with urllib.request.urlopen(url,timeout=t) as r: return json.loads(r.read().decode())
    except Exception: return None
def post(url,o,t=1.5):
    try:
        req=urllib.request.Request(url,data=json.dumps(o).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=t) as r: return json.loads(r.read().decode())
    except Exception: return None

def write_cfg():
    json.dump(dict(cap=CAP,agents=AGENTS,
                   agent_site={str(k):v for k,v in AGENT_SITE.items()},
                   role_site={str(k):v for k,v in ROLE_SITE.items()}),
              open(CFGPATH,"w"))

def start_fabric(field):
    cleanup()
    ensure_net("ctrlnet"); ensure_net("peernet")
    vol=f'-v "{HERES}":/app'
    for i in range(N):
        sh(f'docker run -d --name fa-{i} --network peernet -p {HOSTPORT(i)}:8080 {vol} {IMG} python /app/fabric_real.py agent --id {i} --field {1 if field else 0}')
        sh(f'docker network connect ctrlnet fa-{i}')
    sh(f'docker run -d --name fa-central --network ctrlnet {vol} {IMG} python /app/fabric_real.py central')
    # cho agent len
    for _ in range(30):
        if all(get(f"http://localhost:{HOSTPORT(i)}/health") for i in range(N)): break
        time.sleep(1)

def place_initial():
    # round-robin trong tung site
    for site,ids in (("s0",[0,1,2]),("s1",[3,4,5])):
        roles=[r for r in range(NROLE) if ROLE_SITE[r]==site]
        for k,r in enumerate(roles):
            i=ids[k%len(ids)]; post(f"http://localhost:{HOSTPORT(i)}/host",{"role":r})

def coverage():
    covered=set()
    for i in range(N):
        d=get(f"http://localhost:{HOSTPORT(i)}/roles")
        if d is not None: covered|=set(d["hosted"])
    return len(covered)

def run(field, label):
    print(f"=== {label} (field={'on' if field else 'off'}) ===")
    start_fabric(field); place_initial(); time.sleep(3)
    tl=[]; c0=coverage(); print(f"  t0 coverage={c0}/{NROLE}")
    # PHAN MANH: cat site s1 (fa-3,4,5) khoi ctrlnet
    for i in [3,4,5]: sh(f"docker network disconnect ctrlnet fa-{i}")
    print("  >> phan manh: s1 (fa-3,4,5) mat ctrlnet (van con peernet)")
    # LOI: giet 1 node edge (fa-3)
    sh("docker kill fa-3")
    print("  >> giet fa-3 (node edge chet han)")
    t0=time.time()
    while time.time()-t0<24:
        c=coverage(); rel=round(time.time()-t0)
        tl.append(dict(t=rel,cov=c)); print(f"    t={rel}s coverage={c}/{NROLE}")
        time.sleep(3)
    return tl

if __name__=="__main__":
    write_cfg()
    print("kéo image (neu can)..."); sh(f"docker pull {IMG}")
    tb=run(False,"BASELINE")
    tc=run(True ,"CERTIHEAL")
    print("=== KET QUA ===")
    print(f"  baseline  coverage cuoi: {tb[-1]['cov']}/{NROLE} ({100*tb[-1]['cov']//NROLE}%)")
    print(f"  certiheal coverage cuoi: {tc[-1]['cov']}/{NROLE} ({100*tc[-1]['cov']//NROLE}%)")
    json.dump(dict(baseline=tb,certiheal=tc,nrole=NROLE),open(os.path.join(HERE,"fabric_real_smoke.json"),"w"),indent=1)
    cleanup()
    print("done -> fabric_real_smoke.json")
