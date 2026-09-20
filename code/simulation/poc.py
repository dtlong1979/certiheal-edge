"""
CertiHeal-Edge — Proof-of-Concept nhỏ (CPU-only)
Làm rõ định lượng NOVELTY của Đ4: tái ánh xạ vai-trò khi nhiều node hỏng đồng thời
trên một mesh edge/IoT, so 3 chiến lược tìm tuyến khôi phục ĐỈNH-RỜI (vertex-disjoint):

  (G) Greedy nearest-spare  — baseline rời rạc: mỗi vai-trò mồ côi lấy đường NGẮN NHẤT
      tới spare rảnh gần nhất, khóa nút đã dùng (myopic -> gây chồng tuyến).
  (F) Trường điều hòa (harmonic/diffusion) — ĐÚNG thuật toán luận án 2014: giải Laplace
      (spare = 0, node-hỏng = nguồn 1), route theo GRADIENT thế giảm, khóa nút; giải lại
      trường sau mỗi lần khóa (mô phỏng dòng tái phân bố).
  (O) Optimum = max luồng đỉnh-rời F->S (định lý Menger). min-cut = O = CHỨNG CHỈ khả-sửa
      (cận dưới số vai-trò chắc chắn sửa được).

Đo: corrective capability  kappa(t) = tỉ lệ cấu hình mà chiến lược sửa ĐƯỢC TẤT CẢ t lỗi.
Kỳ vọng novelty:  G  <  F  ~<=  O , khoảng cách nới rộng khi lỗi CỤM (clustered);
và chứng chỉ min-cut TĂNG theo số spare m.
"""
import numpy as np, networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import json, os, time

OUT = os.path.dirname(os.path.abspath(__file__))
SEED = 12345
rng = np.random.default_rng(SEED)

# ----------------------------- model -----------------------------
def build_grid(gx, gy):
    G = nx.grid_2d_graph(gx, gy)          # 2D lattice, node = (i,j)
    return G

def place_spares(G, m, mode="spread"):
    nodes = list(G.nodes())
    if mode == "spread":
        # phân bố đều: chọn m nút cách quãng theo thứ tự ô lưới
        idx = np.linspace(0, len(nodes)-1, m).round().astype(int)
        return set(nodes[i] for i in idx)
    ix = rng.choice(len(nodes), size=m, replace=False)
    return set(nodes[i] for i in ix)

def sample_failures(G, spares, t, clustered=False):
    working = [v for v in G.nodes() if v not in spares]
    if not clustered:
        ix = rng.choice(len(working), size=t, replace=False)
        return set(working[i] for i in ix)
    # lỗi CỤM: chọn tâm, lấy t nút gần tâm nhất (tương quan không gian)
    c = working[rng.integers(len(working))]
    working.sort(key=lambda v: (v[0]-c[0])**2 + (v[1]-c[1])**2
                               + 0.01*rng.random())
    return set(working[:t])

# ----------------- (O) optimum: max vertex-disjoint flow -----------------
def optimum_disjoint(G, F, S):
    """Max luồng đỉnh-rời F->S (mỗi node nội bộ & spare dùng 1 lần). Trả (value, mincut)."""
    D = nx.DiGraph(); src="__s__"; snk="__t__"
    live_interior = [v for v in G.nodes() if v not in F and v not in S]
    for v in live_interior:                      # node-splitting, cap 1
        D.add_edge((v,"i"), (v,"o"), capacity=1)
    for s in S:                                  # spare: cửa vào -> sink, 1 lần
        D.add_edge((s,"i"), snk, capacity=1)
    for f in F:                                  # node hỏng: nguồn phát tại 'o'
        D.add_edge(src, (f,"o"), capacity=1)
    def has_out(v): return v in F or v in live_interior
    def has_in(v):  return v in S or v in live_interior
    for u, w in G.edges():
        if has_out(u) and has_in(w): D.add_edge((u,"o"), (w,"i"), capacity=1)
        if has_out(w) and has_in(u): D.add_edge((w,"o"), (u,"i"), capacity=1)
    val, _ = nx.maximum_flow(D, src, snk)
    return int(val)

# ----------------- harmonic field solver (eq 2.1/2.2 luận án) -----------------
BIG = 1e3   # thế "không tới được sink" -> routing tránh
def harmonic(Glive, sources, sinks):
    """u=1 trên sources (node-hỏng seed), u=0 trên sinks (spare); nội bộ điều hòa u=avg(nbr).
    Sửa suy biến: chỉ giải trên nút CÓ đường tới ít nhất 1 sink; nút không tới được -> u=BIG."""
    bnd = {**{s:1.0 for s in sources}, **{k:0.0 for k in sinks}}
    # tập nút tới được 1 sink trong Glive (loại thành phần cô lập gây singular)
    reach=set()
    for k in sinks:
        if k in Glive:
            reach |= nx.node_connected_component(Glive, k)
    interior = [v for v in Glive.nodes() if v not in bnd and v in reach]
    out = dict(bnd)
    for v in Glive.nodes():
        if v not in bnd and v not in reach: out[v]=BIG      # không tới sink
    if not interior: return out
    idx = {v:i for i,v in enumerate(interior)}; n=len(interior)
    A = sp.lil_matrix((n,n)); b = np.zeros(n)
    for v in interior:
        i = idx[v]; deg = 0
        for w in Glive.neighbors(v):
            deg += 1
            if w in idx: A[i, idx[w]] -= 1
            elif w in bnd: b[i] += bnd[w]     # sink(0) hoặc source(1)
        A[i,i] = deg if deg>0 else 1.0
    u = spsolve(A.tocsr(), b)
    for v,i in idx.items(): out[v] = float(u[i])
    return out

# ----------------- (F) field routing: steepest-descent + lock + re-solve -----
def field_disjoint(G, F, S, resolve=True):
    """Route từng node-hỏng theo gradient thế giảm tới spare; khóa nút -> đỉnh-rời."""
    dead = set(F)                       # node hỏng = chướng ngại (trừ điểm xuất phát)
    Sset = set(S)                       # spare chỉ là điểm cuối, KHÔNG đi xuyên
    locked = set()                      # nút nội bộ đã dùng
    used_spare = set()
    order = list(F)
    # xử lý node-hỏng theo thứ tự "gần spare trước" để ổn định (ước lượng bằng field 1 lần)
    base_live = G.subgraph([v for v in G.nodes() if v not in dead or True]).copy()
    placed = 0
    remaining = list(F)
    # thứ tự: gần spare nhất trước (dùng hop-distance thô)
    def hopdist(f):
        try: return min(nx.shortest_path_length(G, f, s) for s in S)
        except: return 1e9
    remaining.sort(key=hopdist)
    for f in remaining:
        avail_spares = [s for s in S if s not in used_spare]
        if not avail_spares: break
        # đồ thị sống: bỏ node hỏng khác + nút đã khóa (giữ f để xuất phát)
        block = (dead - {f}) | locked
        Glive = G.subgraph([v for v in G.nodes() if v not in block]).copy()
        if f not in Glive: continue
        seeds = [f]
        u = harmonic(Glive, seeds, set(avail_spares))
        # steepest descent từ f
        path=[f]; cur=f; ok=False; visited={f}
        for _ in range(G.number_of_nodes()):
            if cur in avail_spares: ok=True; break
            nbrs=[w for w in Glive.neighbors(cur) if w not in visited
                  and (w in avail_spares or (w not in Sset and w not in locked))]
            if not nbrs: break
            cur = min(nbrs, key=lambda w: u.get(w, 1.0))   # đi về thế thấp (về spare)
            visited.add(cur); path.append(cur)
        if ok:
            placed += 1
            used_spare.add(cur)
            for v in path[1:-1]:            # khóa nút nội bộ -> đỉnh-rời
                if v not in S: locked.add(v)
    return placed

# ----------------- (G) greedy nearest-spare -----------------
def greedy_disjoint(G, F, S):
    dead=set(F); Sset=set(S); locked=set(); used_spare=set(); placed=0
    def hopdist(f):
        try: return min(nx.shortest_path_length(G, f, s) for s in S)
        except: return 1e9
    for f in sorted(F, key=hopdist):
        best=None; bestlen=1e9
        for s in S:
            if s in used_spare: continue
            # đường tới s KHÔNG đi xuyên spare khác (spare chỉ là điểm cuối)
            block=(dead-{f})|locked|(Sset-{s})
            Glive=G.subgraph([v for v in G.nodes() if v not in block]).copy()
            if f not in Glive or s not in Glive: continue
            try:
                p=nx.shortest_path(Glive, f, s)   # đường NGẮN NHẤT (myopic)
                if len(p)<bestlen: bestlen=len(p); best=p
            except nx.NetworkXNoPath: pass
        if best is not None:
            placed+=1; used_spare.add(best[-1])
            for v in best[1:-1]:
                if v not in S: locked.add(v)
    return placed

# ----------------- (N) discrete-naive: đối thủ luận án tuyên bố thắng -----------------
def discrete_naive(G, F, S):
    """Mỗi node-hỏng ĐỘC LẬP nhắm spare gần NHẤT tuyệt đối (shortest path), KHÔNG phối hợp.
    Va chạm (chung nút nội bộ HOẶC cùng spare) -> các vai-trò đụng nhau đều KHÔNG sửa được.
    Mô phỏng thuật toán rời rạc 'đạt-tới-gần-nhất' mà luận án 2014 chỉ ra là hay xung đột."""
    dead=set(F); Glive=G.subgraph([v for v in G.nodes() if v not in dead]).copy()
    for f in F: Glive.add_node(f)                     # giữ điểm xuất phát
    for f in F:                                        # nối f vào hàng xóm sống
        for w in G.neighbors(f):
            if w in Glive and w not in dead or (w in G and w not in F):
                if w in Glive: Glive.add_edge(f,w)
    paths={}; Sset=set(S)
    for f in F:
        best=None; bl=1e9
        for s in S:
            if s not in Glive: continue
            # đường tới s không đi xuyên spare khác
            Gs=Glive.subgraph([v for v in Glive.nodes() if v not in (Sset-{s})]).copy()
            if f not in Gs or s not in Gs: continue
            try:
                p=nx.shortest_path(Gs,f,s)
                if len(p)<bl: bl=len(p); best=p
            except nx.NetworkXNoPath: pass
        paths[f]=best
    # đếm va chạm: nút nội bộ hoặc spare bị >1 route dùng
    from collections import Counter
    use=Counter()
    for f,p in paths.items():
        if p is None: continue
        for v in p[1:]:      # gồm cả spare cuối
            use[v]+=1
    repaired=0
    for f,p in paths.items():
        if p is None: continue
        if all(use[v]==1 for v in p[1:]):   # không đụng ai
            repaired+=1
    return repaired

# ----------------- locality: trường = điểm bất động của Jacobi cục bộ -----------------
def jacobi_iters(Glive, sources, sinks, tol=1e-3, maxit=5000):
    """Đếm số vòng lặp Jacobi (chỉ trung bình hàng xóm 1-hop) để hội tụ tới trường điều hòa.
    Chứng minh P1/P2: trường KHÔNG cần giải tập trung, đạt được bằng trao đổi 1-hop."""
    bnd={**{s:1.0 for s in sources}, **{k:0.0 for k in sinks}}
    reach=set()
    for k in sinks:
        if k in Glive: reach|=nx.node_connected_component(Glive,k)
    interior=[v for v in Glive.nodes() if v not in bnd and v in reach]
    if not interior: return 0
    u={v:0.0 for v in interior}
    for it in range(1,maxit+1):
        mx=0.0; nu={}
        for v in interior:
            vals=[]
            for w in Glive.neighbors(v):
                vals.append(bnd[w] if w in bnd else u.get(w,0.0))
            nv=sum(vals)/len(vals) if vals else 0.0
            nu[v]=nv; mx=max(mx,abs(nv-u[v]))
        u=nu
        if mx<tol: return it
    return maxit

# ----------------------------- experiments -----------------------------
def sweep_kappa(gx, gy, m, T, trials, clustered):
    G=build_grid(gx,gy); S=place_spares(G,m)
    ts=list(range(1,T+1))
    kap={"naive":[], "greedy":[], "field":[], "opt":[]}; mincut_mean=[]
    for t in ts:
        cn=cg=cf=co=0; mcs=[]
        for _ in range(trials):
            F=sample_failures(G,S,t,clustered)
            o=optimum_disjoint(G,F,S); mcs.append(o)
            cn+= (discrete_naive(G,F,S)>=t)
            cg+= (greedy_disjoint(G,F,S)>=t)
            cf+= (field_disjoint(G,F,S)>=t)
            co+= (o>=t)
        kap["naive"].append(cn/trials); kap["greedy"].append(cg/trials)
        kap["field"].append(cf/trials); kap["opt"].append(co/trials)
        mincut_mean.append(float(np.mean(mcs)))
    return ts, kap, mincut_mean, len(S)

def cert_vs_spares(gx, gy, ms, t, trials, clustered):
    G=build_grid(gx,gy)
    res={"m":[], "opt":[], "field":[], "greedy":[], "naive":[], "mincut":[]}
    PLACEMENTS=4                       # trung bình nhiều cách đặt spare -> mượt nhiễu
    for m in ms:
        cn=cg=cf=co=0; mcs=[]; tot=0
        for _ in range(PLACEMENTS):
            S=place_spares(G,m,mode="random")
            for _ in range(trials):
                F=sample_failures(G,S,t,clustered)
                o=optimum_disjoint(G,F,S); mcs.append(o)
                cn+=(discrete_naive(G,F,S)>=t)
                cg+=(greedy_disjoint(G,F,S)>=t); cf+=(field_disjoint(G,F,S)>=t); co+=(o>=t)
                tot+=1
        res["m"].append(m); res["opt"].append(co/tot); res["field"].append(cf/tot)
        res["greedy"].append(cg/tot); res["naive"].append(cn/tot)
        res["mincut"].append(float(np.mean(mcs)))
    return res

def main():
    t0=time.time()
    GX=GY=8; TRIALS=250
    summary={}

    # --- Fig 1 & 2: kappa(t), uniform vs clustered ---
    fig,axes=plt.subplots(1,2,figsize=(12,4.6))
    for ax,clu,title in [(axes[0],False,"Lỗi phân bố ĐỀU (uniform)"),
                         (axes[1],True ,"Lỗi CỤM (clustered)")]:
        ts,kap,mc,ns=sweep_kappa(GX,GY,10,8,TRIALS,clu)
        ax.plot(ts,kap["opt"],"k-o",label="Optimum (Menger / tran)")
        ax.plot(ts,kap["field"],"b-s",label="Field")
        ax.plot(ts,kap["greedy"],"r-^",label="Greedy phoi hop")
        ax.plot(ts,kap["naive"],"m-v",label="Discrete-naive")
        ax.set_title(f"{title}\n8x8 mesh, {ns} spares, {TRIALS} trials/t")
        ax.set_xlabel("Số lỗi đồng thời t"); ax.set_ylabel("Corrective capability κ(t)")
        ax.set_ylim(-0.02,1.02); ax.grid(alpha=.3); ax.legend()
        summary["uniform" if not clu else "clustered"]={"t":ts,**kap,"mincut_mean":mc}
    fig.tight_layout(); fig.savefig(os.path.join(OUT,"fig1_kappa.png"),dpi=130)

    # --- Fig 3: chứng chỉ min-cut & κ tăng theo #spare (lỗi cụm, t=5) ---
    ms=[4,6,8,10,12,14,16]; T_FIX=5
    cv=cert_vs_spares(GX,GY,ms,T_FIX,120,clustered=True)
    fig2,ax1=plt.subplots(figsize=(7,4.8))
    ax1.plot(cv["m"],cv["opt"],"k-o",label="κ optimum")
    ax1.plot(cv["m"],cv["field"],"b-s",label="κ trường")
    ax1.plot(cv["m"],cv["greedy"],"r-^",label="κ greedy")
    ax1.set_xlabel("Số spare m"); ax1.set_ylabel(f"κ (t={T_FIX})"); ax1.set_ylim(-0.02,1.02)
    ax1.grid(alpha=.3)
    ax2=ax1.twinx()
    ax2.plot(cv["m"],cv["mincut"],"g--d",label="Chứng chỉ min-cut TB")
    ax2.set_ylabel("min-cut trung bình (# chắc chắn sửa được)",color="g")
    ax2.axhline(T_FIX,color="gray",ls=":",lw=1)
    ax1.set_title(f"Chứng chỉ khả-sửa & κ TĂNG theo số spare (lỗi cụm, t={T_FIX})")
    l1,la1=ax1.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
    ax1.legend(l1+l2,la1+la2,loc="lower right",fontsize=9)
    fig2.tight_layout(); fig2.savefig(os.path.join(OUT,"fig3_certificate.png"),dpi=130)
    summary["cert_vs_spares"]={"t":T_FIX, **cv}

    # --- số liệu tóm tắt: mức giảm "fatal combination" của field so với greedy ---
    # đếm trực tiếp trên lỗi cụm, t=5
    G=build_grid(GX,GY); S=place_spares(G,10)
    only_field=0; both_fail=0; N=600
    for _ in range(N):
        F=sample_failures(G,S,5,clustered=True)
        g=greedy_disjoint(G,F,S)>=5; f=field_disjoint(G,F,S)>=5; o=optimum_disjoint(G,F,S)>=5
        if f and not g: only_field+=1
        if not f and not g: both_fail+=1
    summary["fatal_reduction"]={"N":N,"m":10,"t":5,
        "field_saves_over_greedy":only_field,
        "field_saves_pct":round(100*only_field/N,1),
        "both_fail":both_fail}

    # --- locality: Jacobi cục bộ hội tụ trong ~O(đường kính) ---
    Gd=build_grid(GX,GY); Sd=place_spares(Gd,10); diam=nx.diameter(Gd)
    its=[]
    for _ in range(120):
        F=sample_failures(Gd,Sd,5,clustered=True)
        Glive=Gd.subgraph([v for v in Gd.nodes() if v not in F]).copy()
        for f in F: Glive.add_node(f)
        for f in F:
            for w in Gd.neighbors(f):
                if w in Glive: Glive.add_edge(f,w)
        its.append(jacobi_iters(Glive, set(F), set(Sd)))
    summary["locality"]={"grid":f"{GX}x{GY}","diameter":diam,
        "jacobi_iters_mean":round(float(np.mean(its)),1),
        "jacobi_iters_p95":int(np.percentile(its,95)),
        "note":"truong dat duoc bang trao doi 1-hop; comm ~ O(duong kinh), khong can BFS/flow toan cuc"}

    summary["runtime_sec"]=round(time.time()-t0,1)
    with open(os.path.join(OUT,"results.json"),"w",encoding="utf-8") as fp:
        json.dump(summary,fp,ensure_ascii=False,indent=2,default=lambda x:list(x) if isinstance(x,set) else x)

    # in tóm tắt (ASCII an toàn cho cp1252)
    def row(name,xs): print(f"{name:8s}:",[round(x,3) for x in xs])
    print("=== KAPPA(t) uniform ===  (t=",summary["uniform"]["t"],")")
    for k in ("naive","greedy","field","opt"): row(k, summary["uniform"][k])
    print("=== KAPPA(t) clustered ===")
    for k in ("naive","greedy","field","opt"): row(k, summary["clustered"][k])
    print("=== CERT vs #spares (clustered, t=5) ===")
    print("m       :",cv["m"]); print("mincutAvg:",[round(x,2) for x in cv["mincut"]])
    for k in ("naive","greedy","field","opt"):
        if k in cv: row("k_"+k, cv[k])
    print("=== FATAL REDUCTION (clustered,t=5,m=10,N=600) ===")
    print(summary["fatal_reduction"])
    print("=== LOCALITY (Jacobi cuc bo) ===")
    print(summary["locality"])
    print("runtime",summary["runtime_sec"],"s -> figs + results.json in",OUT)

if __name__=="__main__":
    main()
