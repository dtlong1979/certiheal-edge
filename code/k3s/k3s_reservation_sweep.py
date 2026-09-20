# -*- coding: utf-8 -*-
"""
THI NGHIEM K3s #1 (chay THAT tren cluster heterogeneous): fail-closed reservation tren Kubernetes.
Quet muc ap luc L = so node bi RUT khoi lich (cordon), re-place toan bo workload len (16-L) node,
do Pending. Tinh verdict CA BA arm tu CUNG mot episode vat ly (chung khac nhau o QUY TAC QUYET DINH):
  - certonly    : model uniform-slot certificate (cap = cpu//3 = 10 slot/node) -> feasible?
  - dryrun/reservation : admission THAT theo cpu (sum allocatable >= sum cpu-request that) -> feasible?
False-safe = arm tuyen "feasible" nhung THUC TE co Pending (role treo).
Ky vong: heterogeneous (30x3cpu + 15x9cpu) khien slot-model OVER-PROMISE -> certonly false-safe o
L in {9,10,11}; admission/reservation theo cpu that -> 0 false-safe (fail-closed).

  python k3s_reservation_sweep.py [TRIALS=3]
"""
import subprocess, time, json, os, sys, random
from kubernetes import client, config
NS="certiheal"; DEPLOYS=["roles","roles-big"]; OUT=os.path.dirname(os.path.abspath(__file__))
NOMINAL=3                                   # kich thuoc role "danh nghia" (cpu) ma model gia dinh -> cap slot = alloc//NOMINAL
LEVELS=[6,8,9,10,11,12]                      # so node cordon; boundary: slot<=11, cpu<=8 => false-safe zone {9,10,11}
TRIALS=int(sys.argv[1]) if len(sys.argv)>1 else 3
random.seed(42)

config.load_kube_config(); v1=client.CoreV1Api(); appsv1=client.AppsV1Api()
def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
def is_worker(n):
    lbl=n.metadata.labels or {}
    return "node-role.kubernetes.io/control-plane" not in lbl and not n.metadata.name.endswith("server-0")
def nready(n): return any(c.type=="Ready" and c.status=="True" for c in (n.status.conditions or []))
def alloc_cpu(n):
    a=(n.status.allocatable or {}).get("cpu","0"); return int(a[:-1])/1000 if a.endswith("m") else float(a)
def role_pods(): return [p for p in v1.list_namespaced_pod(NS).items if (p.metadata.labels or {}).get("app")=="role"]
def pod_cpu(p):
    tot=0.0
    for c in p.spec.containers:
        r=(c.resources.requests or {}).get("cpu","0"); tot+= int(r[:-1])/1000 if r.endswith("m") else float(r)
    return tot
def counts():
    ps=role_pods(); run=sum(1 for p in ps if p.status.phase=="Running")
    pend=sum(1 for p in ps if p.status.phase=="Pending" or p.spec.node_name is None)
    return run,pend,len(ps)
def workers(): return [n for n in v1.list_node().items if is_worker(n)]
def uncordon_all():
    for n in workers():
        if n.spec.unschedulable: sh(f"kubectl uncordon {n.metadata.name}")
def restart_and_wait(target, timeout=120):
    for d in DEPLOYS: sh(f"kubectl -n {NS} rollout restart deploy/{d}")
    t0=time.time()
    while time.time()-t0<timeout:
        run,pend,tot=counts()
        if run==target and pend==0: return True
        time.sleep(4)
    return False
def settle(timeout=90):
    """cho pending on dinh (3 lan doc lien tiep bang nhau) roi tra ve."""
    t0=time.time(); hist=[]
    while time.time()-t0<timeout:
        run,pend,tot=counts(); hist.append(pend)
        if len(hist)>=3 and hist[-1]==hist[-2]==hist[-3]: break
        time.sleep(5)
    return counts()

WK=[n.metadata.name for n in workers()]
NW=len(WK)
TOTAL=sum(1 for _ in role_pods())          # 45
REAL_DEMAND=round(sum(pod_cpu(p) for p in role_pods()),1)
print(f"[SWEEP] {NW} worker nodes, {TOTAL} role pods, real demand {REAL_DEMAND} cpu, nominal slot={NOMINAL}cpu, trials={TRIALS}",flush=True)

episodes=[]
for L in LEVELS:
    for tr in range(TRIALS):
        # baseline khoe manh
        uncordon_all()
        if not restart_and_wait(TOTAL): print(f"  [warn] baseline khong day du truoc L={L} tr={tr}",flush=True)
        # cordon L node ngau nhien (theo seed) — node dong nhat 32cpu nen chon nao cung tuong duong
        victims=random.sample(WK, L)
        for n in victims: sh(f"kubectl cordon {n}")
        # re-place toan bo workload len (NW-L) node
        for d in DEPLOYS: sh(f"kubectl -n {NS} rollout restart deploy/{d}")
        run,pend,tot=settle()
        ready_sched=[n for n in workers() if nready(n) and not n.spec.unschedulable]
        real_cap=round(sum(alloc_cpu(n) for n in ready_sched),1)
        slot_cap=sum(int(alloc_cpu(n)//NOMINAL) for n in ready_sched)
        slot_feasible = slot_cap>=tot
        admit_feasible = real_cap>=REAL_DEMAND
        hang = pend>0
        ep=dict(L=L,trial=tr,sched_nodes=len(ready_sched),running=run,pending=pend,total=tot,
                slot_cap=slot_cap,slot_feasible=slot_feasible,real_cap=real_cap,real_demand=REAL_DEMAND,
                admit_feasible=admit_feasible,hang=hang)
        episodes.append(ep)
        print(f"  L={L} tr={tr} sched={len(ready_sched)} run={run} pend={pend} | slot_cap={slot_cap}>= {tot}? {slot_feasible} | real {real_cap}>={REAL_DEMAND}? {admit_feasible} | hang={hang}",flush=True)
uncordon_all(); restart_and_wait(TOTAL)
json.dump(dict(nodes=NW,total_pods=TOTAL,real_demand=REAL_DEMAND,nominal=NOMINAL,levels=LEVELS,trials=TRIALS,episodes=episodes),
          open(os.path.join(OUT,"results_res_sweep.json"),"w"),ensure_ascii=False,indent=1)
print(f"=== SWEEP DONE === {len(episodes)} episodes -> results_res_sweep.json",flush=True)
