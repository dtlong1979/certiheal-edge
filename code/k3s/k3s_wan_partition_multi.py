"""
Do LAP LAI phan vung WAN that de lay mean +/- CI cua thoi gian khoi phuc (sau phat hien).
Script tu dong theo doi edge-b tren may A; NGUOI DUNG chi can bat/tat Tailscale tren MAY B
theo nhip tu chon: down -> cho ~1 phut -> up -> cho ~30s -> lap lai. Script tu bat moi chu ky.
"""
import subprocess, time, json, os, statistics as st
from kubernetes import client, config
try: from scipy import stats as sps
except: sps=None
NS="certiheal"; DEP="roles"; VIC="edge-b"; OUT=os.path.dirname(os.path.abspath(__file__))
TARGET=4; TIMEOUT=900
config.load_kube_config(); v1=client.CoreV1Api(); appsv1=client.AppsV1Api()
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
def avail(): return appsv1.read_namespaced_deployment_status(DEP,NS).status.available_replicas or 0
def ready(n):
    try: return any(c.type=="Ready" and c.status=="True" for c in v1.read_node(n).status.conditions)
    except: return False
def pods_on(n):
    return [p.metadata.name for p in v1.list_namespaced_pod(NS).items
            if p.spec.node_name==n and (p.metadata.labels or {}).get("app")=="role"]
def ci95(x):
    if len(x)<2: return 0.0
    if sps: return float(sps.t.ppf(0.975,len(x)-1)*st.stdev(x)/len(x)**0.5)
    return 1.96*st.stdev(x)/len(x)**0.5
def respread():
    sh(f"kubectl -n {NS} rollout restart deploy/{DEP}"); sh(f"kubectl -n {NS} rollout status deploy/{DEP} --timeout=120s")

recs=[]; t0=time.time()
print(f"[MULTI] Muc tieu {TARGET} chu ky. Tren MAY B lap lai: tailscale down -> cho ~1' -> tailscale up -> cho ~30s.", flush=True)
while len(recs)<TARGET and time.time()-t0<TIMEOUT:
    # State READY: dam bao edge-b Ready + co pod
    sh(f"kubectl uncordon {VIC}")
    while not ready(VIC) and time.time()-t0<TIMEOUT: time.sleep(2)
    if not pods_on(VIC):
        respread();
        w=time.time()
        while not pods_on(VIC) and time.time()-w<60: time.sleep(2)
    print(f"[SAN SANG chu ky {len(recs)+1}] edge-b Ready, {len(pods_on(VIC))} pod. -> Chay 'tailscale down' tren B.", flush=True)
    # Arm: cho NotReady
    while ready(VIC) and time.time()-t0<TIMEOUT: time.sleep(2)
    if ready(VIC): break
    t_nr=time.time()
    print(f"[PARTITION #{len(recs)+1}] edge-b NotReady. Remap...", flush=True)
    sh(f"kubectl cordon {VIC}")
    for p in pods_on(VIC): sh(f"kubectl -n {NS} delete pod {p} --grace-period=0 --force")
    lat=None; w=time.time()
    while time.time()-w<120:
        if avail()>=12: lat=time.time()-t_nr; break
        time.sleep(1)
    if lat: recs.append(round(lat,1)); print(f"   -> khoi phuc {lat:.1f}s. (Da co {len(recs)}/{TARGET}) -> Chay 'tailscale up' tren B.", flush=True)
    # Cho reconnect
    while not ready(VIC) and time.time()-t0<TIMEOUT: time.sleep(2)
    time.sleep(3)

res={"config":"WAN real partition (Tailscale, 2 host)","recoveries_s":recs}
if recs: res.update(mean=round(st.mean(recs),1), ci95=round(ci95(recs),1), std=round(st.pstdev(recs),1), n=len(recs))
json.dump(res, open(os.path.join(OUT,"results_k3s_wan_multi.json"),"w"), ensure_ascii=False, indent=2)
print("=== DONE ===", json.dumps(res, ensure_ascii=False), flush=True)
