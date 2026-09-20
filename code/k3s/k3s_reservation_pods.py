# -*- coding: utf-8 -*-
"""
PROOF-OF-MECHANISM: PRE-PLACEMENT reservation bang RESERVATION PODS (placeholder giu cho) tren K3s that.
Khac voi "observe actual placement" (post-admission witness, tautological): o day ta trien khai POD GIU CHO
mang dung resource request, xem scheduler co dat HET khong -> QUYET DINH TRUOC khi commit workload that,
roi xoa (rollback). Fail-closed: neu khong dat het -> reject (khong hua). So voi model slot-certificate.

Chay khi so node kha dung it (may B unreachable): sweep cordon L trong {0..M-1} tren M node reachable.
  python k3s_reservation_pods.py [TRIALS=3]
Xuat results_res_pods.json.
"""
import subprocess, time, json, os, sys, random
from kubernetes import client, config
NS="certiheal"; OUT=os.path.dirname(os.path.abspath(__file__)); NOMINAL=3
TRIALS=int(sys.argv[1]) if len(sys.argv)>1 else 3
random.seed(7)
config.load_kube_config(); v1=client.CoreV1Api()
def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
def alloc_cpu(n):
    a=(n.status.allocatable or {}).get("cpu","0"); return int(a[:-1])/1000 if a.endswith("m") else float(a)
def reachable_workers():
    out=[]
    for n in v1.list_node().items:
        lbl=n.metadata.labels or {}
        if "node-role.kubernetes.io/control-plane" in lbl or n.metadata.name.endswith("server-0"): continue
        taints=[t.key for t in (n.spec.taints or [])]
        if "node.kubernetes.io/unreachable" in taints: continue
        if any(c.type=="Ready" and c.status=="True" for c in (n.status.conditions or [])): out.append(n)
    return out

WK=[n.metadata.name for n in reachable_workers()]
M=len(WK); CAP=int(alloc_cpu(reachable_workers()[0]))    # cpu/node (dong nhat 32)
print(f"[RES-PODS] {M} reachable nodes, {CAP} cpu/node = {M*CAP} cpu, {M*(CAP//NOMINAL)} slots",flush=True)

slot_per = CAP//NOMINAL
if M >= 10:
    # 16-node full scale: heterogeneous 30x3 + 15x9 = 225 cpu, 45 pods; sweep cordon L=6..12 (nhu admission sweep)
    SMALL, BIG = 30, 15
    LEVELS = [6, 8, 9, 10, 11, 12]
else:
    # cluster nho (vd 3 node): kich thuoc DONG de slot-model over-count o cordon-1
    target = M*CAP - (CAP//NOMINAL)
    BIG = target//9; SMALL = (target-9*BIG)//3
    while (BIG+SMALL) > (M-1)*slot_per and SMALL>0: SMALL-=1
    LEVELS = list(range(0, M))
REAL_DEMAND = SMALL*3 + BIG*9
NPOD = SMALL+BIG
print(f"[RES-PODS] probe workload: {SMALL}x3cpu + {BIG}x9cpu = {REAL_DEMAND} cpu, {NPOD} pods",flush=True)

def make_probe(k, cpu):
    """tao 1 reservation pod giu cho (pause: busybox sleep), request cpu, khong lam gi."""
    body={"apiVersion":"v1","kind":"Pod","metadata":{"name":f"resv-{cpu}-{k}","namespace":NS,
            "labels":{"app":"resvprobe"}},
          "spec":{"terminationGracePeriodSeconds":0,"restartPolicy":"Never",
            "containers":[{"name":"pause","image":"busybox:1.36","command":["sh","-c","sleep 100000"],
                           "resources":{"requests":{"cpu":str(cpu),"memory":"16Mi"}}}]}}
    try: v1.create_namespaced_pod(NS,body)
    except Exception as e: pass
def clear_probes():
    sh(f"kubectl -n {NS} delete pod -l app=resvprobe --grace-period=0 --force")
def probe_counts():
    ps=[p for p in v1.list_namespaced_pod(NS).items if (p.metadata.labels or {}).get("app")=="resvprobe"]
    run=sum(1 for p in ps if p.status.phase=="Running")
    pend=sum(1 for p in ps if p.status.phase=="Pending" or p.spec.node_name is None)
    return run,pend,len(ps)
def uncordon_all():
    for n in v1.list_node().items:
        if n.spec.unschedulable: sh(f"kubectl uncordon {n.metadata.name}")

episodes=[]
for L in LEVELS:
    for tr in range(TRIALS):
        clear_probes(); uncordon_all(); time.sleep(2)
        vic=random.sample(WK, L)
        for n in vic: sh(f"kubectl cordon {n}")
        # PRE-COMMIT reservation probe: dat pod giu cho, xem co dat HET khong
        for k in range(SMALL): make_probe(k,3)
        for k in range(BIG): make_probe(k,9)
        t0=time.time()
        while time.time()-t0<50:              # cho scheduler on dinh
            run,pend,tot=probe_counts()
            if tot==NPOD and pend==0: break
            time.sleep(3)
        run,pend,tot=probe_counts()
        reserve_feasible = (pend==0 and run==NPOD)     # PRE-COMMIT: reservation nhan HET -> feasible
        # capacity tu node THUC (khong dong nhat: 20 vs 32 cpu) sau khi cordon
        sn=[n for n in reachable_workers() if not n.spec.unschedulable]
        sched=len(sn); real_cap=sum(alloc_cpu(n) for n in sn); slot_cap=sum(int(alloc_cpu(n))//NOMINAL for n in sn)
        slot_feasible = slot_cap >= NPOD               # model slot-certificate (sum slot)
        cpu_feasible  = real_cap >= REAL_DEMAND        # cpu-sum admission
        hang = (pend>0)                                # ground truth: co pod giu cho khong dat duoc
        clear_probes()
        ep=dict(L=L,trial=tr,sched_nodes=sched,run=run,pend=pend,npod=NPOD,
                reserve_feasible=reserve_feasible,slot_feasible=slot_feasible,cpu_feasible=cpu_feasible,hang=hang)
        episodes.append(ep)
        print(f"  L={L} tr={tr} sched={sched} run={run} pend={pend} | reserve={reserve_feasible} slot={slot_feasible} cpu={cpu_feasible} hang={hang}",flush=True)
uncordon_all(); clear_probes()
json.dump(dict(M=M,cap=CAP,npod=NPOD,real_demand=REAL_DEMAND,nominal=NOMINAL,levels=LEVELS,trials=TRIALS,episodes=episodes),
          open(os.path.join(OUT,"results_res_pods.json"),"w"),ensure_ascii=False,indent=1)
# confusion cho tung arm
def conf(key):
    TP=FP=TN=FN=0
    for e in episodes:
        d=e[key]; h=e["hang"]
        if d and not h: TP+=1
        elif d and h: FP+=1
        elif (not d) and h: TN+=1
        else: FN+=1
    fs=FP/(TP+FP) if TP+FP else 0.0
    return TP,FP,TN,FN,round(100*fs,1)
print("=== confusion (declared feasible vs hang) ===")
for name,key in [("slot-certificate","slot_feasible"),("cpu-sum","cpu_feasible"),("reservation-pods (pre-commit)","reserve_feasible")]:
    TP,FP,TN,FN,fs=conf(key); print(f"  {name:<30} TP={TP} FP={FP} TN={TN} FN={FN} false-safe={fs}%")
print("DONE -> results_res_pods.json")
