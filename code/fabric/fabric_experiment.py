# -*- coding: utf-8 -*-
"""
THI NGHIEM cap bai bao: phan manh control-plane + quet so node chet CAT QUA ranh gioi kha-thi.
Topology: s0 (3 node co-located, KHONG phan manh, control) + s1 (M=12 node edge, cap b=4, R=36 role ~75% tai).
Moi run: cat toan bo s1 khoi ctrlnet (phan manh uplink edge) roi giet k node edge.
  Certificate (min-cut suy bien = kiem capacity): KHA-THI <=> (M-k)*b >= R  <=>  k <= 3.
  baseline : field OFF -> chi central (bi phan manh chan) -> role mat nam chet.
  certiheal: field ON tren edge song -> coordinator cuc bo cuu qua peernet toi khi het cap (fail-closed).
Mot fabric dung chung; /field toggle theo dieu kien; reset chong trung. Xuat fabric_results.json.
  python fabric_experiment.py [SEEDS=8]
"""
import subprocess, json, time, os, sys, urllib.request

HERE=os.path.dirname(os.path.abspath(__file__)); HERES=HERE.replace("\\","/")
CFGPATH=os.path.join(HERE,"fabric_cfg.json").replace("\\","/")
IMG="python:3.11-slim"
S0=[0,1,2]; M=12; EDGE=list(range(3,3+M)); N=3+M
B=4; R_S1=36; R_S0=6
AGENT_SITE={**{i:"s0" for i in S0}, **{i:"s1" for i in EDGE}}
ROLE_SITE={**{r:"s0" for r in range(R_S0)}, **{r:"s1" for r in range(R_S0,R_S0+R_S1)}}
NROLE=R_S0+R_S1
AGENTS=[f"fa-{i}" for i in range(N)]
KSWEEP=[1,2,3,4,5,6]
HP=lambda i:9000+i

def sh(c,t=45):
    try: return subprocess.run(c,shell=True,capture_output=True,text=True,timeout=t)
    except subprocess.TimeoutExpired:
        class R: returncode=124; stdout=""; stderr="timeout"
        return R()
def get(u,t=1.2):
    try:
        with urllib.request.urlopen(u,timeout=t) as r: return json.loads(r.read().decode())
    except Exception: return None
def post(u,o,t=1.2):
    try:
        rq=urllib.request.Request(u,data=json.dumps(o).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(rq,timeout=t) as r: return json.loads(r.read().decode())
    except Exception: return None
def nxt(s): return (1103515245*s+12345)&0x7FFFFFFF
def fail_set(seed,k):
    s=seed; picked=[]; pool=list(EDGE)
    while len(picked)<k and pool:
        s=nxt(s); picked.append(pool.pop(s%len(pool)))
    return sorted(picked)

def cleanup():
    ids=sh('docker ps -aq --filter "name=fa-"').stdout.split()
    if ids: sh("docker rm -f "+" ".join(ids))
def ensure_net(n):
    if sh(f'docker network inspect {n}').returncode!=0: sh(f"docker network create {n}")
def write_cfg():
    json.dump(dict(cap=B,agents=AGENTS,agent_site={str(k):v for k,v in AGENT_SITE.items()},
                   role_site={str(k):v for k,v in ROLE_SITE.items()}),open(CFGPATH,"w"))
def wait_health(ids,to=45):
    for _ in range(to):
        if all(get(f"http://localhost:{HP(i)}/health") for i in ids): return True
        time.sleep(1)
    return False
def start_fabric():
    cleanup(); ensure_net("ctrlnet"); ensure_net("peernet")
    vol=f'-v "{HERES}":/app'
    for i in range(N):
        sh(f'docker run -d --name fa-{i} --network peernet -p {HP(i)}:8080 {vol} {IMG} python /app/fabric_real.py agent --id {i} --field 0')
        sh(f'docker network connect ctrlnet fa-{i}')
    # KHONG chay container central: control-plane bi phan manh khoi vung edge = khong voi toi duoc,
    # nen su hien dien cua no khong quan sat duoc o vung phan manh (chi gay leak DNS docker). Baseline =
    # khong recovery nao toi duoc vung edge; CertiHeal = field agent cuc bo tu cuu qua peernet.
    wait_health(range(N))
def hosted_sum():
    t=0
    for i in range(N):
        d=get(f"http://localhost:{HP(i)}/roles")
        if d is not None: t+=len(d["hosted"])
    return t
def coverage(t=2.0,exclude=()):
    cov=set()
    for i in range(N):
        if i in exclude: continue                            # node da kill: khong dem (docker-proxy co the con tra stale)
        d=get(f"http://localhost:{HP(i)}/roles",t)
        if d is not None: cov|=set(d["hosted"])
    return len(cov)
def coverage_clean(exclude=()):
    r=sorted(coverage(2.5,exclude) for _ in range(3)); return r[1]   # median-of-3: chong outlier hai chieu
def dup_count(exclude=()):
    """So role dang cai tren >1 agent SONG (double-booking): =0 neu ton trong invariant no-double-booking."""
    cnt={}
    for i in range(N):
        if i in exclude: continue
        d=get(f"http://localhost:{HP(i)}/roles",2.0)
        if d is not None:
            for r in d["hosted"]: cnt[r]=cnt.get(r,0)+1
    return sum(1 for r,c in cnt.items() if c>1)
def _exited(i):
    return sh(f'docker inspect -f "{{{{.State.Running}}}}" fa-{i}').stdout.strip()=="false"
def wait_dead(F,to=16):
    for _ in range(to):                              # xac nhan container da EXITED (chac hon health HTTP)
        if all(_exited(i) for i in F): time.sleep(1); return
        time.sleep(0.5)
def all_live(exclude):
    return all(get(f"http://localhost:{HP(i)}/health",1.5) is not None for i in range(N) if i not in exclude)
def place_initial():
    for site,ids in (("s0",S0),("s1",EDGE)):
        roles=[r for r in range(NROLE) if ROLE_SITE[r]==site]
        for k,r in enumerate(roles): post(f"http://localhost:{HP(ids[k%len(ids)])}/host",{"role":r})
def reset():
    for i in range(N):
        post(f"http://localhost:{HP(i)}/field",{"on":False})     # tat field truoc khi dat role
        sh(f"docker network connect ctrlnet fa-{i}")
    dead=[i for i in range(N) if get(f"http://localhost:{HP(i)}/health") is None]
    for i in dead: sh(f"docker start fa-{i}")
    if dead: wait_health(range(N))
    for _ in range(4):                                            # clear robust (khong trung)
        for i in range(N): post(f"http://localhost:{HP(i)}/clear",{})
        if hosted_sum()==0: break
        time.sleep(0.4)
    place_initial()
    for _ in range(6):
        if hosted_sum()==NROLE and coverage()==NROLE: return True
        time.sleep(0.4)
    return hosted_sum()==NROLE

def run_one(cond,seed,k):
    ok=reset()
    if not ok or coverage()!=NROLE: return None
    F=fail_set(seed,k); surv=[i for i in EDGE if i not in F]
    for i in EDGE: sh(f"docker network disconnect ctrlnet fa-{i}")   # phan manh uplink s1
    for i in F: sh(f"docker kill fa-{i}")
    wait_dead(F)                                                     # chac node bi kill da chet han
    dead=set(F); rec=0.0; killed_coord=None
    if cond in ("certiheal","peer","ckill"):
        coord=(cond!="peer")                                                # peer = uncoordinated; certiheal/ckill = coordinator + reservation
        for i in surv: post(f"http://localhost:{HP(i)}/field",{"on":True,"coord":coord})   # bat field tren edge song
        t0=time.time(); tl=[]
        while time.time()-t0<30:                                            # cua so field CO DINH du dai cho k lon (khong break som)
            time.sleep(2)
            if cond=="ckill" and killed_coord is None and time.time()-t0>=8:  # GIET coordinator dang hoat dong giua recovery
                live_s1=sorted(i for i in surv if i not in dead)
                if live_s1:
                    killed_coord=live_s1[0]                                   # coordinator = agent aid nho nhat con song
                    sh(f"docker kill fa-{killed_coord}"); dead.add(killed_coord); wait_dead([killed_coord])
            tl.append((round(time.time()-t0,1),coverage(2.0,dead)))
        for i in surv:
            if i not in dead: post(f"http://localhost:{HP(i)}/field",{"on":False})  # TAT field truoc khi do sach
        time.sleep(2)
        if tl:                                                              # rec = luc dat coverage cao nhat trong cua so
            mx=max(c for _,c in tl); rec=next((t for t,c in tl if c>=mx),tl[-1][0])
    else:
        time.sleep(2.5)                                                      # cho node bi kill chet han truoc khi do
    fin=coverage_clean(dead)                                                 # do sach, bo node da kill khoi phep dem
    dup=dup_count(dead)                                                      # double-booking: role tren >1 agent song
    if not all_live(dead): return None                                       # co agent (khong bi kill) treo -> redo
    kk=k+(1 if killed_coord is not None else 0)                              # ckill: +1 node chet giua chung
    feas=(M-kk)*B>=R_S1
    return dict(cond=cond,seed=seed,k=k,fail=sorted(dead),cov_final=fin,cov_pct=round(100*fin/NROLE,1),
                recov_s=rec,dup=dup,killed_coord=killed_coord,cert_feasible=feas,surv_cap=(M-kk)*B,demand=R_S1,nrole=NROLE)

if __name__=="__main__":
    # Usage: fabric_experiment.py [SEEDS=8]              -> chay baseline+certiheal (ghi de)
    #        fabric_experiment.py <cond> [NSEEDS=5]      -> chay 1 dieu kien (baseline|certiheal|peer), NOI vao file co san
    RESF=os.path.join(HERE,"fabric_results.json")
    a1=sys.argv[1] if len(sys.argv)>1 else None
    if a1 in ("baseline","certiheal","peer","ckill"):
        CONDS=[a1]; NS=int(sys.argv[2]) if len(sys.argv)>2 else 5
        results=[r for r in json.load(open(RESF))] if os.path.exists(RESF) else []
        results=[r for r in results if r.get("cond")!=a1]     # bo run cu cua dieu kien nay (chay lai sach)
        APPEND=True
    else:
        CONDS=["baseline","certiheal"]; NS=int(a1) if a1 else 8; results=[]; APPEND=False
    SEEDS=list(range(101,101+NS))
    write_cfg()
    if sh(f"docker image inspect {IMG}").returncode!=0: sh(f"docker pull {IMG}",t=300)
    for cond in CONDS:
        ksweep=[1,2] if cond=="ckill" else KSWEEP                          # ckill: chi muc con feasible sau khi coordinator chet
        for seed in SEEDS:
            print(f"  [build fabric] {cond} seed={seed} ...",flush=True)
            start_fabric()                                    # rebuild fabric moi seed cho tuoi (tranh xuong cap)
            for k in ksweep:
                r=run_one(cond,seed,k)
                if r is None:                                    # reset loi -> rebuild fabric roi thu lai 1 lan
                    print(f"  [rebuild fabric] {cond} seed={seed} k={k}",flush=True); start_fabric(); r=run_one(cond,seed,k)
                if r is None: print(f"  [SKIP] {cond} seed={seed} k={k}",flush=True); continue
                results.append(r)
                print(f"  {cond} seed={seed} k={k} feas={r['cert_feasible']} cov={r['cov_final']}/{NROLE} ({r['cov_pct']}%) dup={r.get('dup')} recov={r['recov_s']}s",flush=True)
        json.dump(results,open(RESF,"w"),indent=1)
    cleanup()
    print(f"DONE {len(results)} runs total -> fabric_results.json (append={APPEND})",flush=True)
