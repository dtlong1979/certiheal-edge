"""
CertiHeal-Edge PoC — Bước A: kiểm ĐG1.
Câu hỏi: điều chỉnh DẪN SUẤT (conductance) — đòn bẩy mà lớp AI sẽ học — có thu hẹp
khe hở giữa trường phi-tập-trung và optimum (Menger) dưới LỖI CỤM không?

Phương pháp (không huấn luyện, để cô lập đòn bẩy):
  field_adaptive = trường điều hòa CÓ TRỌNG SỐ + phản hồi tắc nghẽn:
    lặp R vòng: giải trường theo conductance hiện tại -> đo "cầu" đi qua từng nút
    (đường descent chưa khóa của mọi nguồn) -> GIẢM conductance quanh nút tắc
    -> trường vòng sau tự lái tuyến TÁCH RA -> nhiều tuyến đỉnh-rời hơn.
Nếu κ(adaptive) > κ(field) và tiến sát κ(opt) => đòn bẩy conductance CÓ giá trị => ĐG1 khả thi.
"""
import numpy as np, networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import json, os, time
from collections import Counter
import poc   # tái dùng build_grid, optimum_disjoint, greedy_disjoint, field_disjoint, sample_failures, place_spares

OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(2024)
BIG = 1e3

def harmonic_w(Glive, sources, sinks, cond):
    """Trường điều hòa CÓ TRỌNG SỐ: u_v = sum_w c_vw u_w / sum_w c_vw (Laplacian trọng số)."""
    bnd={**{s:1.0 for s in sources}, **{k:0.0 for k in sinks}}
    reach=set()
    for k in sinks:
        if k in Glive: reach|=nx.node_connected_component(Glive,k)
    interior=[v for v in Glive.nodes() if v not in bnd and v in reach]
    out=dict(bnd)
    for v in Glive.nodes():
        if v not in bnd and v not in reach: out[v]=BIG
    if not interior: return out
    idx={v:i for i,v in enumerate(interior)}; n=len(interior)
    A=sp.lil_matrix((n,n)); b=np.zeros(n)
    for v in interior:
        i=idx[v]; s=0.0
        for w in Glive.neighbors(v):
            c=cond.get(frozenset((v,w)),1.0); s+=c
            if w in idx: A[i,idx[w]]-=c
            elif w in bnd: b[i]+=c*bnd[w]
        A[i,i]=s if s>0 else 1.0
    u=spsolve(A.tocsr(),b)
    for v,i in idx.items(): out[v]=float(u[i])
    return out

def descend(Glive, start, u, sinks, locked, avoid_locked=True):
    """Đi theo thế giảm (có trọng số ngầm qua u) tới một sink; trả path hoặc None."""
    cur=start; path=[start]; visited={start}
    for _ in range(Glive.number_of_nodes()):
        if cur in sinks: return path
        nbrs=[w for w in Glive.neighbors(cur) if w not in visited
              and (w in sinks or not (avoid_locked and w in locked))]
        if not nbrs: return None
        cur=min(nbrs, key=lambda w: u.get(w,BIG)); visited.add(cur); path.append(cur)
    return None

def field_adaptive(G, F, S, R=5, gamma=0.35, count_only=True):
    """Trường thích nghi conductance theo tắc nghẽn. Trả số vai-trò sửa được (đỉnh-rời)."""
    dead=set(F)
    cond={}   # frozenset(edge)->conductance
    best=0
    def hop(f):
        try: return min(nx.shortest_path_length(G,f,s) for s in S)
        except: return 1e9
    order=sorted(F,key=hop)
    for r in range(R):
        # 1) trường toàn cục với mọi nguồn=1, sink=0, conductance hiện tại (dùng để đo cầu)
        Glive0=G.subgraph([v for v in G.nodes() if v not in dead]).copy()
        for f in F:
            Glive0.add_node(f)
            for w in G.neighbors(f):
                if w in Glive0: Glive0.add_edge(f,w)
        u0=harmonic_w(Glive0, set(F), set(S), cond)
        # 2) cầu: đường descent CHƯA KHÓA của mỗi nguồn -> đếm nút bị nhiều tuyến muốn qua
        use=Counter()
        for f in F:
            p=descend(Glive0, f, u0, set(S), locked=set(), avoid_locked=False)
            if p:
                for v in p[1:-1]: use[v]+=1
        # 3) giảm conductance quanh nút tắc (để vòng sau lái tuyến tách ra)
        for v,c in use.items():
            if c>=2:
                for w in G.neighbors(v):
                    e=frozenset((v,w)); cond[e]=cond.get(e,1.0)*gamma
        # 4) route THẬT (khóa nút -> đỉnh-rời) với conductance hiện tại, đếm
        locked=set(); used_spare=set(); placed=0
        for f in order:
            avail=[s for s in S if s not in used_spare]
            if not avail: break
            block=(dead-{f})|locked
            Glive=G.subgraph([v for v in G.nodes() if v not in block]).copy()
            if f not in Glive: continue
            u=harmonic_w(Glive, {f}, set(avail), cond)
            p=descend(Glive, f, u, set(avail), locked)
            if p:
                placed+=1; used_spare.add(p[-1])
                for v in p[1:-1]:
                    if v not in S: locked.add(v)
        best=max(best,placed)
    return best

def main():
    t0=time.time()
    GX=GY=8; TRIALS=150; m=10
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    ts=[3,4,5,6]
    res={"t":ts,"field":[],"adaptive":[],"greedy":[],"opt":[]}
    gapclose=[]
    for t in ts:
        cf=ca=cg=co=0
        for _ in range(TRIALS):
            F=poc.sample_failures(G,S,t,clustered=True)
            o=poc.optimum_disjoint(G,F,S)
            cf+=(poc.field_disjoint(G,F,S)>=t)
            ca+=(field_adaptive(G,F,S)>=t)
            cg+=(poc.greedy_disjoint(G,F,S)>=t)
            co+=(o>=t)
        res["field"].append(cf/TRIALS); res["adaptive"].append(ca/TRIALS)
        res["greedy"].append(cg/TRIALS); res["opt"].append(co/TRIALS)
    # % khe hở (opt - field) mà adaptive khép được
    for i in range(len(ts)):
        gap=res["opt"][i]-res["field"][i]
        closed=res["adaptive"][i]-res["field"][i]
        gapclose.append(round(100*closed/gap,1) if gap>1e-9 else None)
    res["gap_closed_pct"]=gapclose
    res["runtime_sec"]=round(time.time()-t0,1)

    with open(os.path.join(OUT,"results_ai.json"),"w",encoding="utf-8") as fp:
        json.dump(res,fp,ensure_ascii=False,indent=2)

    fig,ax=plt.subplots(figsize=(7.2,4.8))
    ax.plot(ts,res["opt"],"k-o",label="Optimum (Menger)")
    ax.plot(ts,res["adaptive"],"g-D",label="Truong thich nghi conductance (dai dien AI)")
    ax.plot(ts,res["field"],"b-s",label="Truong dan suat deu (baseline)")
    ax.plot(ts,res["greedy"],"r-^",label="Greedy phoi hop")
    ax.set_xlabel("So loi dong thoi t (loi CUM)"); ax.set_ylabel("Corrective capability k(t)")
    ax.set_ylim(-0.02,1.02); ax.grid(alpha=.3); ax.set_title(
        f"DG1: dieu chinh conductance co thu hep khe ho toi optimum? (8x8, {m} spares, {TRIALS} trials)")
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(OUT,"fig4_ai_lever.png"),dpi=130)

    def row(n,xs): print(f"{n:10s}:",[round(x,3) for x in xs])
    print("t         :",ts)
    for k in ("opt","adaptive","field","greedy"): row(k,res[k])
    print("gap_closed% :",gapclose)
    print("runtime",res["runtime_sec"],"s")

if __name__=="__main__":
    main()
