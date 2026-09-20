"""
CertiHeal-Edge PoC — Vòng 4(c): TỔNG QUÁT HOÁ + kiểm P1 (độc-lập-kích-thước).
Rời lưới đều sang RANDOM GEOMETRIC GRAPH (mô hình triển khai IoT/edge không gian:
node nối nhau nếu trong tầm sóng). Kiểm: (soft-field ≈ optimum ≫ naive) có GIỮ khi
đổi topo và TĂNG kích thước n không, và Jacobi cục bộ vẫn ~O(đường kính) (P1).
"""
import numpy as np, networkx as nx, json, os, time
import poc
from poc import jacobi_iters  # đo hội tụ cục bộ
from poc5_softroute import soft_route
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(77)

def make_rgg(n):
    r=1.7*np.sqrt(np.log(max(n,2))/ (np.pi*n))   # bán kính đủ để liên thông (whp)
    G=nx.random_geometric_graph(n, r, seed=int(rng.integers(1e9)))
    # đảm bảo liên thông: lấy thành phần lớn nhất
    if not nx.is_connected(G):
        cc=max(nx.connected_components(G),key=len); G=G.subgraph(cc).copy()
    pos=nx.get_node_attributes(G,"pos")
    return G,pos

def spares_geo(G,m):
    nodes=list(G.nodes()); ix=rng.choice(len(nodes),size=m,replace=False)
    return set(nodes[i] for i in ix)

def fails_geo(G,pos,S,t):
    """Lỗi CỤM không gian: chọn tâm, lấy t node sống gần nhất theo Euclid."""
    work=[v for v in G.nodes() if v not in S]
    c=work[rng.integers(len(work))]; cp=pos[c]
    work.sort(key=lambda v:(pos[v][0]-cp[0])**2+(pos[v][1]-cp[1])**2+0.001*rng.random())
    return set(work[:t])

def live_geo(G,F):
    Glive=G.subgraph([v for v in G.nodes() if v not in F]).copy()
    for f in F:
        Glive.add_node(f)
        for w in G.neighbors(f):
            if w in Glive: Glive.add_edge(f,w)
    return Glive

def main():
    t0=time.time()
    rows=[]
    for n in [64,150,300]:
        FRAC_SP=0.15; t=max(3,int(round(0.06*n)))   # ~6% lỗi, ~15% spare, theo TỈ LỆ (kiểm P1)
        TR=80; cn=cf=cg=co=0; its=[]; diam=[]
        m=max(4,int(round(FRAC_SP*n)))
        for _ in range(TR):
            G,pos=make_rgg(n); S=spares_geo(G,m); F=fails_geo(G,pos,S,t)
            co+=(poc.optimum_disjoint(G,F,S)>=t)
            cf+=(soft_route(G,F,S,{})>=t)
            cg+=(poc.greedy_disjoint(G,F,S)>=t)
            cn+=(poc.discrete_naive(G,F,S)>=t)
            Glive=live_geo(G,F)
            its.append(jacobi_iters(Glive,set(F),set(S)))
            try: diam.append(nx.diameter(G))
            except: diam.append(np.nan)
        rows.append({"n":n,"t":t,"spares":m,
            "kappa_naive":round(cn/TR,3),"kappa_soft_field":round(cf/TR,3),
            "kappa_greedy":round(cg/TR,3),"kappa_optimum":round(co/TR,3),
            "field_over_naive_x": round((cf/TR)/max(cn/TR,1e-3),1),
            "field_to_opt_ratio": round((cf/TR)/max(co/TR,1e-3),3),
            "jacobi_iters_mean":round(float(np.mean(its)),1),
            "diameter_mean":round(float(np.nanmean(diam)),1),
            "jacobi_over_diam":round(float(np.mean(its))/max(np.nanmean(diam),1),2)})
    out={"rows":rows,"runtime_sec":round(time.time()-t0,1),
         "note":"P1: neu field_to_opt_ratio va jacobi_over_diam ON DINH theo n => doc-lap-kich-thuoc"}
    json.dump(out,open(os.path.join(OUT,"results_generalize.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
