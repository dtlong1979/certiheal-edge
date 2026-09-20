# -*- coding: utf-8 -*-
"""
CHAOS + FENCE + REBALANCE, 30 phut, dong bo A/B qua LCG chung + START epoch.
A-side = bo nao: sinh lich, thuc thi fault cho nut/cum cua A (co lap iptables),
tu-fence sau TTL, phuc hoi khi het han; DONG THOI dieu khien toan cum:
  - reassign vai tro mo coi tren nut NotReady (CertiHeal),
  - uncordon nut da hoi phuc,
  - RESPREAD tra viec ve nut vua hoi (rebalance-back).
Ghi timeseries -> chaos_fence_A.json.
  python chaos_fence_A.py <SEED> <START_epoch> [DURATION=1800]
  python chaos_fence_A.py verify <SEED>            # in 12 su kien dau de doi chieu voi B
"""
import sys, time, json, os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); NS="certiheal"; DEP="roles"
os.environ["MSYS_NO_PATHCONV"]="1"
NODES=["k3d-a-agent2-0","k3d-certiheal-agent-0","k3d-certiheal-agent-1",
       "edge-b","edge-b-1","edge-b-2","edge-b-3","edge-b-4","edge-b-5",
       "edge-b-6","edge-b-7","edge-b-8","edge-b-9","edge-b-10","edge-b-11","edge-b-12"]
CLUSTERS=[[0,1,2],[3,4,5],[6,7,8],[9,10,11,12],[13,14,15]]
A_NODES={0,1,2}; A_CLUSTERS={0}
SRV="172.20.0.3"; LB="172.20.0.6"; IPT="/bin/aux/iptables"
TTL=10

def nxt(s): return (1103515245*s + 12345) & 0x7FFFFFFF
def schedule(seed, duration):
    s=seed; t=0; ev=[]
    while True:
        s=nxt(s); gap=20+(s%41); t+=gap
        if t>=duration: break
        s=nxt(s); is_cluster=(s%10)<3
        s=nxt(s); size=5 if is_cluster else 16
        s=nxt(s); tgt=s%size
        s=nxt(s); dur=(45+s%46) if is_cluster else (30+s%31)
        ev.append(dict(t=t, scope="cluster" if is_cluster else "node", target=tgt, dur=dur))
    return ev
def a_owns(e):
    return (e["scope"]=="node" and e["target"] in A_NODES) or (e["scope"]=="cluster" and e["target"] in A_CLUSTERS)
def nodes_of(e): return [NODES[i] for i in (CLUSTERS[e["target"]] if e["scope"]=="cluster" else [e["target"]])]

def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
def isolate(n):
    for ip in (SRV,LB):
        sh(f'docker exec {n} {IPT} -I OUTPUT -d {ip} -j DROP'); sh(f'docker exec {n} {IPT} -I INPUT -s {ip} -j DROP')
def deisolate(n):
    for ip in (SRV,LB):
        sh(f'docker exec {n} {IPT} -D OUTPUT -d {ip} -j DROP'); sh(f'docker exec {n} {IPT} -D INPUT -s {ip} -j DROP')
def pause(n): sh(f'docker pause {n}')
def unpause(n): sh(f'docker unpause {n}')

if len(sys.argv)>=3 and sys.argv[1]=="verify":
    for e in schedule(int(sys.argv[2]),1800)[:12]:
        tg = ("cum "+["cA","cB1","cB2","cB3","cB4"][e["target"]]) if e["scope"]=="cluster" else NODES[e["target"]]
        print(f"t={e['t']:4d} {e['scope']:7s} {tg:14s} dur={e['dur']}")
    sys.exit(0)

from kubernetes import client, config
config.load_kube_config(); v1=client.CoreV1Api(); apps=client.AppsV1Api()
def node_status():
    return {n.metadata.name: any(c.type=="Ready" and c.status=="True" for c in (n.status.conditions or [])) for n in v1.list_node().items}
def role_pods():
    return [p for p in v1.list_namespaced_pod(NS).items if (p.metadata.labels or {}).get("app")=="role"]
def load_map(pods):
    m={}
    for p in pods:
        if p.spec.node_name and p.status.phase=="Running": m[p.spec.node_name]=m.get(p.spec.node_name,0)+1
    return m
def avail(): return apps.read_namespaced_deployment_status(DEP,NS).status.available_replicas or 0

SEED=int(sys.argv[1]); START=float(sys.argv[2]); DURATION=int(sys.argv[3]) if len(sys.argv)>3 else 1800
BASELINE = "--baseline" in sys.argv    # baseline = K8s thuan: khong reassign chu dong/uncordon/respread
TAG = "baseline" if BASELINE else "certiheal"
EV=schedule(SEED, DURATION); MINE=[e for e in EV if a_owns(e)]
for e in MINE: e["nodes"]=nodes_of(e); e["fenced"]=False; e["started"]=False; e["done"]=False
print(f"[FENCE-A] {len(EV)} su kien tong, {len(MINE)} thuoc A. START in {START-time.time():.0f}s. DURATION={DURATION}", flush=True)
while time.time()<START: time.sleep(0.5)

cordoned=set(); last_respread=0; ts=[]; fence_events=[]
def uncordon(n): sh(f"kubectl uncordon {n}"); cordoned.discard(n)
def cordon(n): sh(f"kubectl cordon {n}"); cordoned.add(n)
tick=3
while time.time()-START < DURATION+30:
    rel=time.time()-START
    # --- thuc thi fault cua A ---
    for e in MINE:
        if not e["started"] and rel>=e["t"]:
            e["started"]=True; e["iso_at"]=rel
            for n in e["nodes"]: isolate(n)
            fence_events.append(dict(t=round(rel),act="isolate",scope=e["scope"],nodes=e["nodes"]))
            print(f"  t+{rel:5.0f} ISOLATE {e['scope']} {e['nodes']}", flush=True)
        if e["started"] and not e["fenced"] and rel>=e.get("iso_at",0)+TTL and not e["done"] and not BASELINE:
            e["fenced"]=True
            for n in e["nodes"]: pause(n)          # tu-fence: ngung phuc vu truoc khi bi reassign
            fence_events.append(dict(t=round(rel),act="fence",scope=e["scope"],nodes=e["nodes"]))
            print(f"  t+{rel:5.0f} FENCE   {e['scope']} {e['nodes']}", flush=True)
        if e["started"] and not e["done"] and rel>=e["t"]+e["dur"]:
            e["done"]=True
            for n in e["nodes"]:
                if e["fenced"]: unpause(n)
                deisolate(n)
            fence_events.append(dict(t=round(rel),act="recover",scope=e["scope"],nodes=e["nodes"]))
            print(f"  t+{rel:5.0f} RECOVER {e['scope']} {e['nodes']}", flush=True)
    # --- controller: reassign + uncordon + respread (TAT o baseline: de K8s tu xu ly) ---
    st=node_status(); pods=role_pods()
    notready=[n for n,ok in st.items() if not ok and n!="k3d-certiheal-server-0"]
    orphans=0; respread=0
    if not BASELINE:
        for n in notready:
            if n not in cordoned: cordon(n)
        for p in pods:
            if p.spec.node_name in notready and p.status.phase!="Pending":
                sh(f"kubectl -n {NS} delete pod {p.metadata.name} --grace-period=0 --force"); orphans+=1
        for n in list(cordoned):
            if st.get(n): uncordon(n)     # nut da Ready lai -> cho nhan viec
        # respread tra viec ve: khi lanh manh, dinh ky xoa vai pod tren nut nang nhat -> roi ve nut nhe/moi hoi
        ready_workers=[n for n,ok in st.items() if ok and n!="k3d-certiheal-server-0" and n not in cordoned]
        if rel-last_respread>25 and not any(p.status.phase=="Pending" for p in pods) and len(ready_workers)>=2:
            lm=load_map(pods)
            if lm:
                mean=sum(lm.get(n,0) for n in ready_workers)/len(ready_workers)
                light=[n for n in ready_workers if lm.get(n,0)<=max(0,mean-2)]
                heavy=sorted(ready_workers,key=lambda n:lm.get(n,0),reverse=True)
                if light and heavy and lm.get(heavy[0],0)>=mean+1:
                    for hn in heavy[:2]:
                        hp=[p for p in pods if p.spec.node_name==hn and p.status.phase=="Running"][:2]
                        for p in hp: sh(f"kubectl -n {NS} delete pod {p.metadata.name}"); respread+=1
                    last_respread=rel
                    if respread: print(f"  t+{rel:5.0f} RESPREAD {respread} pod -> nut nhe {light[:4]}", flush=True)
    # do can-bang tai: do lech chuan so vai tro tren cac nut Ready (ca hai che do)
    ready_all=[n for n,ok in st.items() if ok and n!="k3d-certiheal-server-0"]
    lm2=load_map(pods); loads=[lm2.get(n,0) for n in ready_all]
    if loads:
        mu=sum(loads)/len(loads); load_std=round((sum((x-mu)**2 for x in loads)/len(loads))**0.5,2)
    else: load_std=0.0
    a=avail()
    fenced_now=sum(len(e["nodes"]) for e in MINE if e["fenced"] and not e["done"])
    active=[e for e in MINE if e["started"] and not e["done"]]
    ts.append(dict(t=round(rel), avail=a, ready=sum(1 for v in st.values() if v)-1, notready=len(notready),
                   fenced=fenced_now, orphans=orphans, respread=respread, load_std=load_std,
                   active_node=sum(1 for e in active if e["scope"]=="node"),
                   active_cluster=sum(1 for e in active if e["scope"]=="cluster")))
    if int(rel)%30<tick: print(f"  t+{rel:5.0f} avail={a}/64 ready={ts[-1]['ready']} notready={len(notready)} fenced={fenced_now}", flush=True)
    time.sleep(tick)

# don dep: go moi iptables/pause con sot
for e in MINE:
    for n in e["nodes"]:
        unpause(n); deisolate(n)
for n in list(cordoned): uncordon(n)
fn=f"chaos_fence_A_{TAG}.json"
json.dump(dict(seed=SEED,duration=DURATION,mode=TAG,events=EV,mine=len(MINE),
               fence_events=fence_events,timeseries=ts),
          open(os.path.join(OUT,fn),"w"), indent=1)
print(f"=== FENCE-A ({TAG}) DONE -> {fn} ===", flush=True)
