# -*- coding: utf-8 -*-
"""
Thi nghiem CHUNG CHI CO KIEM SOAT: han che kha nang -> chung chi nho, gay dung k loi
(k = chung chi va k = chung chi+1), xac nhan du bao dung ranh gioi (Pending hay khong).
Dieu khien tu A: victim la 3 nut A (k3d-*). Cac nut khac cordon de capacity that su rang buoc.
"""
import subprocess, time, json, os, math
from kubernetes import client, config
NS="certiheal"; DEP="roles"; OUT=os.path.dirname(os.path.abspath(__file__))
A=["k3d-certiheal-agent-0","k3d-certiheal-agent-1","k3d-a-agent2-0"]
config.load_kube_config(); v1=client.CoreV1Api(); apps=client.AppsV1Api()
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
def nready(n):
    try: return any(c.type=="Ready" and c.status=="True" for c in v1.read_node(n).status.conditions)
    except: return False
def wait_ready(n,to=150):
    t0=time.time()
    while time.time()-t0<to:
        if nready(n): return
        time.sleep(2)
def cap(n):
    a=(v1.read_node(n).status.allocatable or {}).get("cpu","0"); c=int(a[:-1])/1000 if a.endswith("m") else float(a); return int(c//3)
def pending():
    return sum(1 for p in v1.list_namespaced_pod(NS).items
               if (p.metadata.labels or {}).get("app")=="role" and (p.status.phase=="Pending" or p.spec.node_name is None))
def live_cert(R):
    caps=sorted([cap(n) for n in A if nready(n) and not v1.read_node(n).spec.unschedulable], reverse=True)
    c=0
    for k in range(len(caps)+1):
        if sum(caps[:len(caps)-k])>=R: c=k
        else: break
    return c
def respread():
    sh(f"kubectl -n {NS} rollout restart deploy/{DEP}"); sh(f"kubectl -n {NS} rollout status deploy/{DEP} --timeout=120s"); time.sleep(3)

# Han che schedulable ve 3 nut A
sh("kubectl get nodes --no-headers -o custom-columns=N:.metadata.name | findstr /V server > NUL")  # noop
allw=[n.metadata.name for n in v1.list_node().items if not n.metadata.name.endswith("server-0")]
for n in allw:
    if n in A: sh(f"kubectl uncordon {n}")
    else: sh(f"kubectl cordon {n}")

res=[]
for R in [12, 6]:   # R=12 -> cert1 ; R=6 -> cert2 (3 nut cap 6)
    sh(f"kubectl -n {NS} scale deploy/{DEP} --replicas={R}"); respread()
    cert=live_cert(R)
    print(f"\n### R={R}  chung chi(live)={cert}  (cap moi nut={cap(A[0])}) ###", flush=True)
    for k in [cert, cert+1]:
        if k>len(A): continue
        vics=A[:k]
        for v in vics: sh(f"docker stop {v}"); sh(f"kubectl cordon {v}")
        # cho + remap pod mo coi
        time.sleep(3)
        for v in vics:
            for p in [pp.metadata.name for pp in v1.list_namespaced_pod(NS).items if pp.spec.node_name==v and (pp.metadata.labels or {}).get("app")=="role"]:
                sh(f"kubectl -n {NS} delete pod {p} --grace-period=0 --force")
        time.sleep(8)
        pend=pending()
        verdict = ("DUNG: khong Pending (k<=cert)" if k<=cert and pend==0 else
                   ("DUNG: co Pending (k>cert)" if k>cert and pend>0 else "LECH"))
        print(f"  giet k={k} nut -> Pending={pend}  [{verdict}]", flush=True)
        res.append(dict(R=R,cert=cert,k=k,pending=pend,within=(k<=cert),verdict=verdict))
        for v in vics: sh(f"kubectl uncordon {v}"); sh(f"docker start {v}"); wait_ready(v,150)
        respread()

# khoi phuc
for n in allw: sh(f"kubectl uncordon {n}")
sh(f"kubectl -n {NS} scale deploy/{DEP} --replicas=64"); respread()
json.dump(res, open(os.path.join(OUT,"results_cert_boundary.json"),"w"), ensure_ascii=False, indent=1)
print("\n=== CERT BOUNDARY ==="); print(json.dumps(res, ensure_ascii=False))
