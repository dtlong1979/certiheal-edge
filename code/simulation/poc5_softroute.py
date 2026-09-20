"""
CertiHeal-Edge PoC — Vòng 3(a): ĐG1 có PHỤC SINH dưới ROUTING NHẠY-TRỌNG-SỐ không?
Vòng 2 cho thấy descent-argmin-thế trơ với conductance (oracle khép 0%). Ở đây thay bằng
SOFT / CURRENT-PROPORTIONAL routing: mỗi nguồn đi ngẫu nhiên với xác suất tỉ lệ DÒNG ĐIỆN
xuôi dốc  c_uw*max(0,u_u-u_w), khóa nút, thử K lần giữ kết quả tốt nhất. Dòng điện nhạy
conductance -> nếu oracle-conductance giờ khép được khe hở => ĐG1 sống lại dạng "learned soft-routing".
"""
import numpy as np, networkx as nx, json, os, time
import poc
from poc2_ai import harmonic_w
from poc3_oracle import optimum_flow_edges
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(2025)
BIG=1e3

def soft_route(G,F,S,cond,K=12):
    """Routing ngẫu nhiên tỉ lệ dòng điện, K lần thử, trả max số vai-trò đỉnh-rời."""
    dead=set(F); Sset=set(S)
    def hop(f):
        try: return min(nx.shortest_path_length(G,f,s) for s in S)
        except: return 1e9
    order=sorted(F,key=hop)
    best=0
    for _ in range(K):
        locked=set(); used=set(); placed=0
        for f in order:
            avail=set(s for s in S if s not in used)
            if not avail: break
            block=(dead-{f})|locked
            Glive=G.subgraph([v for v in G.nodes() if v not in block]).copy()
            if f not in Glive: continue
            u=harmonic_w(Glive,{f},avail,cond)
            # random walk tỉ lệ dòng xuôi dốc; KHÔNG đi xuyên spare (spare chỉ là điểm cuối)
            cur=f; visited={f}; ok=False
            for _ in range(Glive.number_of_nodes()):
                if cur in avail: ok=True; break
                nbrs=[w for w in Glive.neighbors(cur) if w not in visited
                      and (w in avail or (w not in Sset and w not in locked))]
                if not nbrs: break
                wts=[]
                for w in nbrs:
                    c=cond.get(frozenset((cur,w)),1.0)
                    dv=u.get(cur,BIG)-u.get(w,BIG)          # >0 nếu xuôi dốc về sink
                    wts.append(max(0.0,c*dv))
                s=sum(wts)
                if s<=0: nxt=min(nbrs,key=lambda w:u.get(w,BIG))   # kẹt -> greedy
                else:    nxt=nbrs[rng.choice(len(nbrs),p=np.array(wts)/s)]
                visited.add(nxt)
                if nxt not in avail: locked.add(nxt)
                cur=nxt
            if ok:
                placed+=1; used.add(cur)
        best=max(best,placed)
    return best

def main():
    t0=time.time(); GX=GY=8; m=10; TRIALS=1200
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    out={}
    for t in [5,6]:
        # (1) so κ tổng thể: descent (poc.field) vs soft (đều) vs optimum
        cf=csoft=co=0
        # (2) oracle-test dưới SOFT routing
        gap=0; oracle=0; rnd=0
        for _ in range(TRIALS):
            F=poc.sample_failures(G,S,t,clustered=True)
            val,edges=optimum_flow_edges(G,F,S)
            co+=(val>=t)
            cf+=(poc.field_disjoint(G,F,S)>=t)
            su=soft_route(G,F,S,{})>=t
            csoft+=su
            if val>=t and not su:                 # khe hở của SOFT-uniform
                gap+=1
                cond={e:20.0 for e in edges}
                if soft_route(G,F,S,cond)>=t: oracle+=1
                alled=[frozenset(e) for e in G.edges()]
                ri=rng.choice(len(alled),size=min(len(edges),len(alled)),replace=False)
                if soft_route(G,F,S,{alled[i]:20.0 for i in ri})>=t: rnd+=1
        out[f"t={t}"]={
            "kappa_optimum":round(co/TRIALS,3),
            "kappa_soft_uniform":round(csoft/TRIALS,3),
            "kappa_descent_field":round(cf/TRIALS,3),
            "gap_configs_soft":gap,
            "oracle_conductance_closes":oracle,
            "oracle_close_pct":round(100*oracle/gap,1) if gap else None,
            "random_boost_closes":rnd,
            "random_close_pct":round(100*rnd/gap,1) if gap else None,
        }
    out["runtime_sec"]=round(time.time()-t0,1)
    json.dump(out,open(os.path.join(OUT,"results_softroute.json"),"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
