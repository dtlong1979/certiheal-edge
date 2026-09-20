# -*- coding: utf-8 -*-
"""
Baseline THUAT TOAN manh (tra loi 2.9 + 2.3 + 2.5), tren CUNG mo hinh do thi voi poc.py.
  (1) Augmenting-path (Edmonds-Karp) tren do thi node-split -> dat max luong roi dinh = OPTIMUM.
      Do: (a) khoang cach field toi optimum = ti le field TU-KET (greedy self-stranding),
          (b) chi phi phoi hop toan cuc (so lan tang luong + so canh tham) vs field cuc bo.
  (2) Optimum CO DUNG LUONG (node-split cap=c): chung chi khi moi nut chua nhieu vai tro (khop testbed cap=6).
Ket qua -> results_baselines.json + fig_baselines.png
"""
import numpy as np, networkx as nx, json, os, time
from collections import deque
import poc
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(7)

def build_split(G, F, S, cap=1):
    """Do thi node-split huong: moi nut noi bo/spare tach in->out cap=cap; F phat, S thu."""
    D=nx.DiGraph(); src="__s__"; snk="__t__"
    interior=[v for v in G.nodes() if v not in F and v not in S]
    for v in interior: D.add_edge((v,"i"),(v,"o"),capacity=cap)
    for s in S: D.add_edge((s,"i"),snk,capacity=cap)      # spare chua toi 'cap' vai tro
    for f in F: D.add_edge(src,(f,"o"),capacity=cap)       # nut hong phat toi 'cap' vai tro mo coi
    hasout=lambda v: v in F or v in interior
    hasin =lambda v: v in S or v in interior
    for u,w in G.edges():
        if hasout(u) and hasin(w): D.add_edge((u,"o"),(w,"i"),capacity=cap)
        if hasout(w) and hasin(u): D.add_edge((w,"o"),(u,"i"),capacity=cap)
    return D,src,snk

def edmonds_karp(D,src,snk):
    """Ford-Fulkerson BFS. Tra (max_flow, so_lan_tang_luong, so_canh_tham) — do chi phi phoi hop TOAN CUC."""
    res={}
    for u,v,d in D.edges(data=True):
        res[(u,v)]=res.get((u,v),0)+d["capacity"]; res.setdefault((v,u),0)
    adj={}
    for (u,v) in res: adj.setdefault(u,set()).add(v)
    flow=0; augs=0; visits=0
    while True:
        par={src:None}; q=deque([src]); found=False
        while q:
            u=q.popleft()
            for v in adj.get(u,()):
                visits+=1
                if v not in par and res[(u,v)]>0:
                    par[v]=u
                    if v==snk: found=True; q.clear(); break
                    q.append(v)
        if not found: break
        # tang luong doc duong
        b=1e9; v=snk
        while par[v] is not None: b=min(b,res[(par[v],v)]); v=par[v]
        v=snk
        while par[v] is not None: res[(par[v],v)]-=b; res[(v,par[v])]+=b; v=par[v]
        flow+=b; augs+=1
    return int(flow),augs,visits

def main():
    t0=time.time(); GX=GY=8; m=10; TRIALS=200
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    # === (1) field self-stranding vs augmenting-path (=optimum), + chi phi phoi hop ===
    ts=list(range(1,9)); res1={"t":ts,"field":[],"optimum":[],"greedy":[],
        "field_strand_pct":[],"aug_visits":[],"field_local_rounds":[]}
    for t in ts:
        cf=co=cg=0; strand=0; visits=[]; rounds=[]
        for _ in range(TRIALS):
            F=poc.sample_failures(G,S,t,clustered=True)
            D,sr,sk=build_split(G,F,S,cap=1)
            opt,augs,vis=edmonds_karp(D,sr,sk)
            fld=poc.field_disjoint(G,F,S); grd=poc.greedy_disjoint(G,F,S)
            cf+=(fld>=t); co+=(opt>=t); cg+=(grd>=t)
            if fld<opt: strand+=1               # field tu-ket: dat it hon max luong toan cuc
            visits.append(vis)
            # so vong cuc bo cua field (trao doi 1-hop) tren cung cau hinh
            Glive=G.subgraph([v for v in G.nodes() if v not in F]).copy()
            for f in F:
                Glive.add_node(f)
                for w in G.neighbors(f):
                    if w in Glive: Glive.add_edge(f,w)
            rounds.append(poc.jacobi_iters(Glive,set(F),set(S)))
        res1["field"].append(round(cf/TRIALS,3)); res1["optimum"].append(round(co/TRIALS,3))
        res1["greedy"].append(round(cg/TRIALS,3))
        res1["field_strand_pct"].append(round(100*strand/TRIALS,1))
        res1["aug_visits"].append(int(np.mean(visits)))
        res1["field_local_rounds"].append(round(float(np.mean(rounds)),1))
    # === (2) chung chi CO DUNG LUONG: min-cut node-split khi cap tang (khop testbed cap=6) ===
    caps=[1,2,3,4,6]; t_fix=6; res2={"cap":caps,"cert_mean":[]}
    for cap in caps:
        vals=[]
        for _ in range(120):
            F=poc.sample_failures(G,S,t_fix,clustered=True)
            D,sr,sk=build_split(G,F,S,cap=cap)
            val,_,_=edmonds_karp(D,sr,sk)
            vals.append(val)
        res2["cert_mean"].append(round(float(np.mean(vals)),2))
    res={"self_strand_and_cost":res1,"capacitated_cert":res2,
         "note":"augmenting-path dat optimum; field cuc bo bam sat nhung thi thoang tu-ket; "
                "chi phi phoi hop augmenting (visits toan cuc) >> so vong cuc bo cua field",
         "runtime_sec":round(time.time()-t0,1)}
    json.dump(res,open(os.path.join(OUT,"results_baselines.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    # figure
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,3,figsize=(15,4.2))
    ax[0].plot(ts,res1["optimum"],"k-o",label="Augmenting-path (=optimum)")
    ax[0].plot(ts,res1["field"],"b-s",label="Field (local)")
    ax[0].plot(ts,res1["greedy"],"r-^",label="Greedy")
    ax[0].set_xlabel("Simultaneous failures t"); ax[0].set_ylabel("Corrective capability κ(t)"); ax[0].set_ylim(-0.02,1.02)
    ax[0].set_title("(a) Field tracks the augmenting-path optimum"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
    ax[1].plot(ts,res1["field_strand_pct"],"m-d")
    ax[1].set_xlabel("Simultaneous failures t"); ax[1].set_ylabel("% configurations field self-strands")
    ax[1].set_title("(b) Field self-stranding rate"); ax[1].grid(alpha=.3)
    ax[2].plot(caps,res2["cert_mean"],"g-o")
    ax[2].axhline(t_fix,color="gray",ls=":",lw=1)
    ax[2].set_xlabel("Per-node capacity (pods/node)"); ax[2].set_ylabel(f"Min-cut certificate (t={t_fix})")
    ax[2].set_title("(c) Certificate grows with node capacity"); ax[2].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT,"fig_baselines.png"),dpi=140,bbox_inches="tight")
    print(json.dumps(res,ensure_ascii=False,indent=2))
    print("wrote fig_baselines.png")

if __name__=="__main__":
    main()
