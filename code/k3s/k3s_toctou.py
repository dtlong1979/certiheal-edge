# -*- coding: utf-8 -*-
"""
Competing-workload TOCTOU experiment for the operational admission certificate
(reservation-pod probe). On a cleanly-packable slice (12 edge-b nodes at 32 CPU;
machine-A agents cordoned), the real workload of N_REAL pods at POD_CPU exactly
fills the slice, so the probe declares FEASIBLE.

Two conditions per competitor size C:
  NONATOMIC : probe places placeholders, confirms feasible, RELEASES them; a
              competing workload of C pods enters the freed capacity; the real
              workload is then committed. We measure how many real pods hang
              (Pending) -> the TOCTOU gap of the plain probe.
  HELD      : the placeholders are HELD as the reservation while the same C
              competitors are submitted. We measure how many competitors acquire
              the reserved capacity (LEAKED, should be 0) -> holding the
              reservation is fail-closed against concurrency.

Output results_toctou.json.
"""
import subprocess, time, json, os, sys, random
from kubernetes import client, config

NS="certiheal"; OUT=os.path.dirname(os.path.abspath(__file__))
POD_CPU=8; N_REAL=48                      # 48*8 = 384 CPU = 12 edge-b nodes at 32
SETTLE=45                                 # seconds to let the scheduler settle
CVALS=[int(x) for x in (sys.argv[1].split(",") if len(sys.argv)>1 else ["0","4","8","12"])]
TRIALS=int(sys.argv[2]) if len(sys.argv)>2 else 2
random.seed(11)
config.load_kube_config(); v1=client.CoreV1Api()

def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
def alloc(n):
    a=(n.status.allocatable or {}).get("cpu","0"); return int(a[:-1])/1000 if a.endswith("m") else float(a)
def workers():
    out=[]
    for n in v1.list_node().items:
        nm=n.metadata.name; lbl=n.metadata.labels or {}
        if "control-plane" in str(lbl) or nm.endswith("server-0"): continue
        taints=[t.key for t in (n.spec.taints or [])]
        if "node.kubernetes.io/unreachable" in taints: continue
        if any(c.type=="Ready" and c.status=="True" for c in (n.status.conditions or [])): out.append(n)
    return out
def edge_workers():   # the 12 machine-B nodes at 32 CPU (clean packing)
    return [n for n in workers() if n.metadata.name.startswith("edge-b") and abs(alloc(n)-32.0)<0.5]
def agent_workers():  # machine-A agents (cordon these)
    return [n for n in workers() if "agent" in n.metadata.name]

def make(label, k, cpu):
    body={"apiVersion":"v1","kind":"Pod","metadata":{"name":f"{label}-{k}","namespace":NS,"labels":{"app":label}},
          "spec":{"terminationGracePeriodSeconds":0,"restartPolicy":"Never",
            "containers":[{"name":"p","image":"busybox:1.36","command":["sh","-c","sleep 100000"],
                           "resources":{"requests":{"cpu":str(cpu),"memory":"16Mi"}}}]}}
    try: v1.create_namespaced_pod(NS,body)
    except Exception: pass
def spawn(label,n,cpu):
    for k in range(n): make(label,k,cpu)
def wipe(label):
    sh(f"kubectl -n {NS} delete pod -l app={label} --grace-period=0 --force >/dev/null 2>&1")
def wipe_all():
    for l in ("resvprobe","realwl","compete"): wipe(l)
def counts(label):
    ps=[p for p in v1.list_namespaced_pod(NS).items if (p.metadata.labels or {}).get("app")==label]
    run=sum(1 for p in ps if p.status.phase=="Running")
    pend=sum(1 for p in ps if p.status.phase=="Pending" or p.spec.node_name is None)
    return run,pend,len(ps)
def wait_until(label,target_run,timeout):
    t0=time.time(); last=None
    while time.time()-t0<timeout:
        run,pend,tot=counts(label)
        if run>=target_run and pend==0: return True,run,pend
        last=(run,pend); time.sleep(3)
    run,pend,_=counts(label); return False,run,pend

def uncordon_all():
    for n in v1.list_node().items:
        if n.spec.unschedulable: sh(f"kubectl uncordon {n.metadata.name} >/dev/null 2>&1")

# ---- setup: cordon machine-A agents, keep the clean edge-b nodes ----
uncordon_all(); wipe_all(); time.sleep(3)
ew=edge_workers(); aw=agent_workers()
for n in aw: sh(f"kubectl cordon {n.metadata.name} >/dev/null 2>&1")
slice_cpu=sum(alloc(n) for n in ew)
# measure the ACTUAL number of POD_CPU pods that fit (allocatable minus system overhead)
spawn("resvprobe", int(slice_cpu//POD_CPU)+4, POD_CPU); time.sleep(SETTLE)
CAP_UNITS,_,_=counts("resvprobe"); wipe_all(); time.sleep(3)
N_REAL=CAP_UNITS                                     # real workload exactly fills the schedulable slice
print(f"[SETUP] edge nodes={len(ew)} slice_cpu={slice_cpu} | measured capacity={CAP_UNITS} pods of {POD_CPU} CPU | N_REAL={N_REAL} | agents cordoned={len(aw)}",flush=True)

episodes=[]
for C in CVALS:
    for tr in range(TRIALS):
        # ---------- NONATOMIC ----------
        wipe_all(); time.sleep(2)
        spawn("resvprobe",N_REAL,POD_CPU)                      # probe
        ok,run,pend=wait_until("resvprobe",N_REAL,SETTLE)
        probe_feasible = ok
        wipe("resvprobe")                                      # RELEASE (the TOCTOU window opens)
        time.sleep(2)
        if C>0: spawn("compete",C,POD_CPU)                     # competitor grabs freed capacity
        time.sleep(2)
        spawn("realwl",N_REAL,POD_CPU)                         # commit real workload
        time.sleep(SETTLE)
        r_run,r_pend,_=counts("realwl"); c_run,c_pend,_=counts("compete")
        hang_nonatomic=r_pend
        wipe_all(); time.sleep(3)
        # ---------- HELD (atomic proxy: reservation not released) ----------
        spawn("resvprobe",N_REAL,POD_CPU)
        ok2,run2,pend2=wait_until("resvprobe",N_REAL,SETTLE)
        if C>0: spawn("compete",C,POD_CPU)                     # competitor while reservation HELD
        time.sleep(SETTLE)
        c_run_h,c_pend_h,_=counts("compete")
        leaked=c_run_h                                         # competitors that breached the held reservation
        wipe_all(); time.sleep(3)
        ep=dict(C=C,trial=tr,probe_feasible=bool(probe_feasible),
                nonatomic_real_running=r_run,nonatomic_real_hang=hang_nonatomic,nonatomic_compete_running=c_run,
                held_reservation_ok=bool(ok2),held_compete_leaked=leaked,held_compete_pending=c_pend_h)
        episodes.append(ep)
        print(f"  C={C:2d} tr={tr} | probe_feasible={probe_feasible} | NONATOMIC real_hang={hang_nonatomic} compete_run={c_run} | HELD leaked={leaked}",flush=True)

uncordon_all(); wipe_all()
res=dict(pod_cpu=POD_CPU,n_real=N_REAL,slice_cpu=slice_cpu,edge_nodes=len(ew),settle=SETTLE,cvals=CVALS,trials=TRIALS,episodes=episodes)
json.dump(res,open(os.path.join(OUT,"results_toctou.json"),"w"),ensure_ascii=False,indent=1)
# summary
print("\n=== summary (mean over trials) ===")
import statistics as st
for C in CVALS:
    es=[e for e in episodes if e["C"]==C]
    hang=st.mean(e["nonatomic_real_hang"] for e in es); leak=st.mean(e["held_compete_leaked"] for e in es)
    print(f"  C={C:2d}: non-atomic real pods hung = {hang:.1f} | held-reservation competitors leaked = {leak:.1f}")
print("DONE -> results_toctou.json")
