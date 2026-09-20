# -*- coding: utf-8 -*-
"""
Hai kiem chung SIM bo sung (khong can testbed):
 (1) SHADOW: chay hai nhanh (danh dinh f0 vs hoc-khong-hoan-hao f_theta), lay f_out=max.
     Xac nhan f_out>=f0 100%, do ti le nhanh danh dinh CUU nhanh hoc (f0>f_theta), va khe toi C.
 (2) CAPACITY: max-flow node-split CO DUNG LUONG voi dung luong nut/cau/lien ket KHONG dong deu,
     cho thay chung chi phan anh dung rang buoc rang buoc (nut vs lien ket vs cau), khong chi nhan capacity.
Ket qua -> results_sim_checks.json
"""
import numpy as np, networkx as nx, json, os
import poc
from poc2_ai import harmonic_w, descend
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(3)

def route(G, F, S, cond):
    dead=set(F); locked=set(); used=set(); placed=0
    def hop(f):
        try: return min(nx.shortest_path_length(G,f,s) for s in S)
        except: return 1e9
    for f in sorted(F, key=hop):
        avail=[s for s in S if s not in used]
        if not avail: break
        block=(dead-{f})|locked
        Glive=G.subgraph([v for v in G.nodes() if v not in block]).copy()
        if f not in Glive: continue
        u=harmonic_w(Glive, {f}, set(avail), cond)
        p=descend(Glive, f, u, set(avail), locked)
        if p:
            placed+=1; used.add(p[-1])
            for v in p[1:-1]:
                if v not in S: locked.add(v)
    return placed

def shadow_check(trials=500):
    G=poc.build_grid(8,8); S=poc.place_spares(G,10)
    n=0; foutge=fthg=f0g=0; gaps=[]
    for _ in range(trials):
        F=poc.sample_failures(G,S,5,clustered=True)
        f0=route(G,F,S,{})                                        # nhanh danh dinh (uniform)
        cond={frozenset((u,w)): float(np.exp(rng.normal(0,1.0)))  # nhanh hoc khong hoan hao
              for u,w in G.edges()}
        ft=route(G,F,S,cond)
        C=poc.optimum_disjoint(G,F,S); fout=max(ft,f0)
        n+=1; foutge+=(fout>=f0); fthg+=(ft>f0); f0g+=(f0>ft); gaps.append(C-fout)
    return {"trials":n,
            "fout_ge_f0_pct":round(100*foutge/n,1),
            "learned_helps_pct":round(100*fthg/n,1),
            "nominal_saves_pct":round(100*f0g/n,1),      # f0>f_theta: shadow-max CUU nhanh hoc
            "mean_gap_fout_to_C":round(float(np.mean(gaps)),3),
            "note":"chay 2 nhanh = 2 lan giai truong; f_out>=f0 dung theo cau truc"}

def cap_maxflow(G,F,S,bnode,dsrc,elink):
    D=nx.DiGraph(); src="__s__"; snk="__t__"
    interior=[v for v in G.nodes() if v not in F and v not in S]
    for v in interior: D.add_edge((v,"i"),(v,"o"),capacity=bnode[v])
    for s in S: D.add_edge((s,"i"),snk,capacity=bnode.get(s,1))
    for f in F: D.add_edge(src,(f,"o"),capacity=dsrc[f])
    ho=lambda v: v in F or v in interior; hi=lambda v: v in S or v in interior
    for u,w in G.edges():
        e=elink[frozenset((u,w))]
        if ho(u) and hi(w): D.add_edge((u,"o"),(w,"i"),capacity=e)
        if ho(w) and hi(u): D.add_edge((w,"o"),(u,"i"),capacity=e)
    val,_=nx.maximum_flow(D,src,snk); return int(val)

def capacity_check(trials=300):
    G=poc.build_grid(8,8); S=poc.place_spares(G,10); BIG=10
    acc={"uniform":[],"nonuniform_node":[],"nonuniform_demand":[],"link_bottleneck":[]}
    for _ in range(trials):
        F=poc.sample_failures(G,S,5,clustered=True); nodes=list(G.nodes())
        bn1={v:1 for v in nodes}; ds1={f:1 for f in F}
        elBIG={frozenset((u,w)):BIG for u,w in G.edges()}
        bn2={v:int(rng.integers(1,4)) for v in nodes}        # dung luong nut {1,2,3}
        ds2={f:int(rng.integers(1,3)) for f in F}            # cau {1,2}
        elBN={frozenset((u,w)):(1 if rng.random()<0.3 else BIG) for u,w in G.edges()}
        acc["uniform"].append(cap_maxflow(G,F,S,bn1,ds1,elBIG))
        acc["nonuniform_node"].append(cap_maxflow(G,F,S,bn2,ds1,elBIG))
        acc["nonuniform_demand"].append(cap_maxflow(G,F,S,bn2,ds2,elBIG))
        acc["link_bottleneck"].append(cap_maxflow(G,F,S,bn2,ds1,elBN))
    return {k:round(float(np.mean(v)),2) for k,v in acc.items()}

def bridge_example():
    """Vi du KIEM SOAT: 6 nguon -> R1 -> R2 -> 6 giep. Chung chi = min(cau, bind cap).
    Cho thay min-cut bam dung rang buoc bind du la LIEN KET hay NUT."""
    k=6; G=nx.Graph()
    srcs=[("L",i) for i in range(k)]; sinks=[("S",i) for i in range(k)]; R1=("R",1); R2=("R",2)
    for s in srcs: G.add_edge(s,R1)
    G.add_edge(R1,R2)
    for t in sinks: G.add_edge(R2,t)
    F=set(srcs); S=set(sinks); ds={f:1 for f in F}; base={v:100 for v in G.nodes()}
    out={"k_demand":k, "link_bottleneck":{}, "node_bottleneck":{}}
    for lc in [2,4,6,8]:
        el={frozenset((u,w)):100 for u,w in G.edges()}; el[frozenset((R1,R2))]=lc
        out["link_bottleneck"][lc]=cap_maxflow(G,F,S,base,ds,el)     # = min(6, lc)
    for nc in [2,4,6,8]:
        bnode=dict(base); bnode[R1]=nc; el={frozenset((u,w)):100 for u,w in G.edges()}
        out["node_bottleneck"][nc]=cap_maxflow(G,F,S,bnode,ds,el)    # = min(6, nc)
    return out

def main():
    res={"shadow":shadow_check(), "capacity_grid":capacity_check(), "capacity_bridge":bridge_example()}
    json.dump(res, open(os.path.join(OUT,"results_sim_checks.json"),"w"), indent=1)
    print(json.dumps(res, indent=1))

if __name__=="__main__":
    main()
