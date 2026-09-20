# -*- coding: utf-8 -*-
"""
RANDOM CHAOS - script MAY A. Sinh lich RANDOM tu SEED chung (LCG so nguyen, giong het ban PS o may B),
thuc thi kill cho node CUA A (k3d-*), do time-series toan cluc, dong vai CertiHeal remap.
Chay:  python chaos_A.py <SEED> <START_EPOCH> <DURATION_giay>
"""
import subprocess, time, json, os, sys
from kubernetes import client, config
NS="certiheal"; DEP="roles"; OUT=os.path.dirname(os.path.abspath(__file__))
SEED=int(sys.argv[1]) if len(sys.argv)>1 else 12345
START=float(sys.argv[2]) if len(sys.argv)>2 else 0
DURATION=int(sys.argv[3]) if len(sys.argv)>3 else 7200
KEEP_ALIVE=4; GAP_MIN=45; GAP_MAX=150; HOLD_MIN=30; HOLD_MAX=180

# --- danh sach node DONG BO, THU TU CO DINH (phai giong HET ban PowerShell) ---
NODES=["edge-b","edge-b-1","edge-b-2","edge-b-3","edge-b-4","edge-b-5","edge-b-6","edge-b-7",
       "edge-b-8","edge-b-9","edge-b-10","edge-b-11","edge-b-12",
       "k3d-a-agent2-0","k3d-certiheal-agent-0","k3d-certiheal-agent-1"]
def owns(n): return n.startswith("k3d-")          # A so huu node k3d-*
def container_of(n): return n                     # ten container == ten node (k3d agent)

# --- LCG so nguyen giong het may B ---
_st=SEED & 0x7FFFFFFF
def nxt():
    global _st; _st=(1103515245*_st + 12345) & 0x7FFFFFFF; return _st
def rint(a,b): return a + (nxt() % (b-a+1))

def gen_schedule():
    ev=[]; down={}; alive=set(NODES); t=120
    while t < DURATION-120:
        for n,rt in list(down.items()):
            if rt<=t: alive.add(n); del down[n]
        t += rint(GAP_MIN,GAP_MAX)
        for n,rt in list(down.items()):
            if rt<=t: alive.add(n); del down[n]
        r=nxt()%100; k=1 if r<55 else (2 if r<85 else 3)
        k=min(k, len(alive)-KEEP_ALIVE)
        if k<1: continue
        pool=[n for n in NODES if n in alive]; vics=[]
        for _ in range(k): vics.append(pool.pop(nxt()%len(pool)))
        hold=rint(HOLD_MIN,HOLD_MAX)
        for v in vics:
            ev.append((t,"kill",v)); alive.discard(v); down[v]=t+hold
            ev.append((t+hold,"rejoin",v))
    ev.sort(key=lambda e:(e[0],e[2])); return ev

SCHED=gen_schedule()
kills=sum(1 for e in SCHED if e[1]=="kill")
print(f"[CHAOS-A] SEED={SEED} DURATION={DURATION}s | {len(SCHED)} su kien ({kills} kill). 10 dau (VERIFY):", flush=True)
for e in SCHED[:10]: print(f"   t={e[0]} {e[1]} {e[2]}", flush=True)

config.load_kube_config(); v1=client.CoreV1Api(); appsv1=client.AppsV1Api()
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
def is_worker(n):
    lbl=n.metadata.labels or {}
    return "node-role.kubernetes.io/control-plane" not in lbl and not n.metadata.name.endswith("server-0")
def nready(n): return any(c.type=="Ready" and c.status=="True" for c in (n.status.conditions or []))
def cap_of(n):
    a=(n.status.allocatable or {}).get("cpu","0"); c=int(a[:-1])/1000 if a.endswith("m") else float(a)
    return int(c//3)
def orphan_pods(node):
    return [p.metadata.name for p in v1.list_namespaced_pod(NS).items
            if p.spec.node_name==node and (p.metadata.labels or {}).get("app")=="role"]

if START>0:
    print(f"[CHAOS-A] cho START (con {START-time.time():.0f}s)...", flush=True)
    while time.time()<START: time.sleep(0.3)
t0=time.time(); ts=[]; done=set(); last_respread=time.time()
print("[CHAOS-A] BAT DAU.", flush=True)
while time.time()-t0 < DURATION:
    dt=time.time()-t0
    # thuc thi su kien cua A den han
    for i,(et,act,node) in enumerate(SCHED):
        if i in done or et>dt: continue
        if et<=dt:
            done.add(i)
            if owns(node):
                sh(f"docker {'stop' if act=='kill' else 'start'} {container_of(node)}")
                print(f"  t+{dt:6.0f}s [{act.upper()}] {node} (A thuc thi)", flush=True)
    # do trang thai
    nodes=[n for n in v1.list_node().items if is_worker(n)]
    ready=[n for n in nodes if nready(n)]; notready=[n for n in nodes if not nready(n)]
    caps=sorted([cap_of(n) for n in ready if not n.spec.unschedulable], reverse=True)
    dep=appsv1.read_namespaced_deployment_status(DEP,NS)
    avail=dep.status.available_replicas or 0; desired=dep.spec.replicas
    cert=0
    for k in range(len(caps)+1):
        if sum(caps[:len(caps)-k])>=desired: cert=k
        else: break
    pend=sum(1 for p in v1.list_namespaced_pod(NS).items
             if (p.metadata.labels or {}).get("app")=="role" and (p.status.phase=="Pending" or p.spec.node_name is None))
    ts.append(dict(t=round(dt,1), avail=avail, desired=desired, pending=pend,
                   ready=len(ready), notready=len(notready),
                   ready_b=sum(1 for n in ready if n.metadata.name.startswith("edge-b")), cert=cert))
    # CertiHeal remap: node NotReady con pod mo coi -> cordon + xoa
    for n in notready:
        orph=orphan_pods(n.metadata.name)
        if orph:
            sh(f"kubectl cordon {n.metadata.name}")
            for p in orph: sh(f"kubectl -n {NS} delete pod {p} --grace-period=0 --force")
    # uncordon node Ready lai
    for n in ready:
        if n.spec.unschedulable: sh(f"kubectl uncordon {n.metadata.name}")
    # respread dinh ky khi fabric khoe -> nap lai pod cho node vua rejoin
    healthy = len(notready)==0 and not any(n.spec.unschedulable for n in nodes) and avail==desired and pend==0
    if healthy and time.time()-last_respread>300:
        sh(f"kubectl -n {NS} rollout restart deploy/{DEP}"); last_respread=time.time()
    time.sleep(2)
json.dump(dict(seed=SEED,duration=DURATION,schedule=[list(e) for e in SCHED],timeseries=ts),
          open(os.path.join(OUT,"results_chaos_A.json"),"w"), ensure_ascii=False)
print("=== CHAOS-A DONE ===", len(ts), "diem", flush=True)
