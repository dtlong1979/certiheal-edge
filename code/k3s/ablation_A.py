# -*- coding: utf-8 -*-
"""
ABLATION LADDER + CONFUSION-MATRIX, tu dong nhieu SEED, chay overnight (A-side = bo nao + log).
Ladder 4 cau hinh: k8s -> +fence -> +reassign -> +full (fence+reassign+respread).
Moi (config, seed) chay 1 run dai `dur` giay; giua cac run co `gap`. A & B dong bo bang
base_start + i*(dur+gap), cung thu tu (config-major) nen moi may tu biet config/seed cua run i.
  python ablation_A.py <base_start_epoch> <dur> <gap> <seed1,seed2,...>
  vd: python ablation_A.py 1785999999 480 60 101,102,103,104,105,106
"""
import sys, time, json, os, subprocess
os.environ["MSYS_NO_PATHCONV"]="1"
NS="certiheal"; DEP="roles"; OUT=os.path.dirname(os.path.abspath(__file__)); CAP=6; TTL=10; TICK=3
NODES=["k3d-a-agent2-0","k3d-certiheal-agent-0","k3d-certiheal-agent-1",
       "edge-b","edge-b-1","edge-b-2","edge-b-3","edge-b-4","edge-b-5",
       "edge-b-6","edge-b-7","edge-b-8","edge-b-9","edge-b-10","edge-b-11","edge-b-12"]
CLUSTERS=[[0,1,2],[3,4,5],[6,7,8],[9,10,11,12],[13,14,15]]
A_NODES={0,1,2}; A_CLUSTERS={0}; SRV="172.20.0.3"; LB="172.20.0.6"; IPT="/bin/aux/iptables"
# (name, FENCE, REASSIGN, RESPREAD)
CONFIGS=[("k8s",0,0,0),("fence",1,0,0),("reassign",1,1,0),("full",1,1,1)]

def nxt(s): return (1103515245*s+12345)&0x7FFFFFFF
def schedule(seed,dur):
    s=seed; t=0; ev=[]
    while True:
        s=nxt(s); gap=20+(s%41); t+=gap
        if t>=dur: break
        s=nxt(s); isc=(s%10)<3
        s=nxt(s); size=5 if isc else 16
        s=nxt(s); tgt=s%size
        s=nxt(s); d=(45+s%46) if isc else (30+s%31)
        ev.append(dict(t=t,scope="cluster" if isc else "node",target=tgt,dur=d))
    return ev
def a_owns(e): return (e["scope"]=="node" and e["target"] in A_NODES) or (e["scope"]=="cluster" and e["target"] in A_CLUSTERS)
def nodes_of(e): return [NODES[i] for i in (CLUSTERS[e["target"]] if e["scope"]=="cluster" else [e["target"]])]
def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
def isolate(n):
    for ip in (SRV,LB): sh(f'docker exec {n} {IPT} -I OUTPUT -d {ip} -j DROP'); sh(f'docker exec {n} {IPT} -I INPUT -s {ip} -j DROP')
def deisolate(n):
    for ip in (SRV,LB): sh(f'docker exec {n} {IPT} -D OUTPUT -d {ip} -j DROP'); sh(f'docker exec {n} {IPT} -D INPUT -s {ip} -j DROP')
def pause(n): sh(f'docker pause {n}')
def unpause(n): sh(f'docker unpause {n}')

from kubernetes import client, config as kconfig
kconfig.load_kube_config(); v1=client.CoreV1Api(); apps=client.AppsV1Api()
def node_status(): return {n.metadata.name: any(c.type=="Ready" and c.status=="True" for c in (n.status.conditions or [])) for n in v1.list_node().items}
def role_pods(): return [p for p in v1.list_namespaced_pod(NS).items if (p.metadata.labels or {}).get("app")=="role"]
def load_map(pods):
    m={}
    for p in pods:
        if p.spec.node_name and p.status.phase=="Running": m[p.spec.node_name]=m.get(p.spec.node_name,0)+1
    return m
def avail(): return apps.read_namespaced_deployment_status(DEP,NS).status.available_replicas or 0

base_start=float(sys.argv[1]); dur=int(sys.argv[2]); gap=int(sys.argv[3])
seeds=[101,102,103,104,105,106]        # HARDCODE — phai giong het ablation_B.ps1
S=len(seeds); N=len(CONFIGS)*S
tot_h=round(N*(dur+gap)/3600,2)
fin=time.strftime('%H:%M', time.localtime(base_start+N*(dur+gap)))
assert base_start>time.time(), "base_start phai o TUONG LAI"
print(f"[ABL-A] {N} runs (4 cfg x {S} seed), dur={dur}s gap={gap}s, TONG ~{tot_h}h, xong ~{fin}. base_start in {base_start-time.time():.0f}s",flush=True)
def cordon(n): sh(f"kubectl cordon {n}")
def uncordon(n): sh(f"kubectl uncordon {n}")

for i in range(N):
    name,FENCE,REASSIGN,RESPREAD=CONFIGS[i//S]; seed=seeds[i%S]
    run_start=base_start + i*(dur+gap)
    while time.time()<run_start-45: time.sleep(0.5)      # reset deploy TRONG gap, truoc run_start
    sh(f"kubectl -n {NS} rollout restart deploy/{DEP}"); sh(f"kubectl -n {NS} rollout status deploy/{DEP} --timeout=40s")
    while time.time()<run_start: time.sleep(0.3)         # cho dung run_start de dong bo voi B
    print(f"[ABL-A] RUN {i+1}/{N}: config={name} seed={seed}",flush=True)
    EV=schedule(seed,dur); MINE=[e for e in EV if a_owns(e)]
    for e in MINE: e.update(nodes=nodes_of(e),started=False,fenced=False,done=False,iso_at=0.0)
    cordoned=set(); last_respread=0; ts=[]; t0=run_start
    while time.time()-t0<dur:
        rel=time.time()-t0
        for e in MINE:
            if not e["started"] and rel>=e["t"]:
                e["started"]=True; e["iso_at"]=rel
                for n in e["nodes"]: isolate(n)
            if FENCE and e["started"] and not e["fenced"] and not e["done"] and rel>=e["iso_at"]+TTL:
                e["fenced"]=True
                for n in e["nodes"]: pause(n)
            if e["started"] and not e["done"] and rel>=e["t"]+e["dur"]:
                e["done"]=True
                for n in e["nodes"]:
                    if e["fenced"]: unpause(n)
                    deisolate(n)
        st=node_status(); pods=role_pods()
        nr=[n for n,ok in st.items() if not ok and n!="k3d-certiheal-server-0"]
        orphans=0; respread=0
        if REASSIGN:
            for n in nr:
                if n not in cordoned: cordon(n); cordoned.add(n)
            for p in pods:
                if p.spec.node_name in nr and p.status.phase!="Pending":
                    sh(f"kubectl -n {NS} delete pod {p.metadata.name} --grace-period=0 --force"); orphans+=1
            for n in list(cordoned):
                if st.get(n): uncordon(n); cordoned.discard(n)
        ready_workers=[n for n,ok in st.items() if ok and n!="k3d-certiheal-server-0" and n not in cordoned]
        if RESPREAD and rel-last_respread>25 and not any(p.status.phase=="Pending" for p in pods) and len(ready_workers)>=2:
            lm=load_map(pods); mean=sum(lm.get(n,0) for n in ready_workers)/max(1,len(ready_workers))
            light=[n for n in ready_workers if lm.get(n,0)<=max(0,mean-2)]
            heavy=sorted(ready_workers,key=lambda n:lm.get(n,0),reverse=True)
            if light and heavy and lm.get(heavy[0],0)>=mean+1:
                for hn in heavy[:2]:
                    for p in [p for p in pods if p.spec.node_name==hn and p.status.phase=="Running"][:2]:
                        sh(f"kubectl -n {NS} delete pod {p.metadata.name}"); respread+=1
                last_respread=rel
        lm2=load_map(pods)
        spare_cap=sum(max(0,CAP-lm2.get(n,0)) for n in ready_workers)
        a=avail(); pend=sum(1 for p in pods if p.status.phase=="Pending" or p.spec.node_name is None)
        ndown=len(nr); active=[e for e in MINE if e["started"] and not e["done"]]
        # cau (orphaned) uoc luong = so pod tren nut NotReady (dang mat)
        orph_now=sum(1 for p in pods if p.spec.node_name in nr)
        ts.append(dict(t=round(rel),avail=a,pending=pend,ready=sum(1 for v in st.values() if v)-1,
                       notready=ndown,spare_cap=spare_cap,orphaned=orph_now,respread=respread,
                       nfail=sum(len(e["nodes"]) for e in active)))
        time.sleep(TICK)
    for e in MINE:
        for n in e["nodes"]: unpause(n); deisolate(n)
    for n in list(cordoned): uncordon(n);
    cordoned.clear()
    json.dump(dict(config=name,seed=seed,fence=FENCE,reassign=REASSIGN,respread=RESPREAD,dur=dur,timeseries=ts),
              open(os.path.join(OUT,f"ablation_A_{name}_{seed}.json"),"w"))
    am=round(sum(p["avail"] for p in ts)/len(ts),1) if ts else 0
    print(f"[ABL-A] done {name} seed={seed}: avail_mean={am} min={min((p['avail'] for p in ts),default=0)}",flush=True)
print("=== ABL-A ALL DONE ===",flush=True)
