"""
CertiHeal-Edge PoC — Bước A' (quyết định): ORACLE-CONDUCTANCE TEST cho ĐG1.
Câu hỏi: trên các cấu hình mà trường-dẫn-suất-đều THẤT BẠI nhưng optimum THÀNH CÔNG
(khe hở), liệu CÓ TỒN TẠI một bộ dẫn suất khiến trường phi-tập-trung đạt optimum?
-> Lấy dẫn suất "oracle" từ chính lời giải max-flow (boost cạnh nằm trên tuyến tối ưu),
   rồi chạy lại trường descent. Nếu trường-oracle giải được phần lớn khe hở => đòn bẩy
   conductance ĐỦ MẠNH => ĐG1 (học conductance) chính đáng.
"""
import numpy as np, networkx as nx, json, os, time
import poc
from poc2_ai import harmonic_w, descend
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(7)

def optimum_flow_edges(G,F,S):
    """Trả (value, set cạnh vô hướng G mang dòng trong 1 lời giải max-flow đỉnh-rời)."""
    D=nx.DiGraph(); src="__s__"; snk="__t__"
    interior=[v for v in G.nodes() if v not in F and v not in S]
    for v in interior: D.add_edge((v,"i"),(v,"o"),capacity=1)
    for s in S: D.add_edge((s,"i"),snk,capacity=1)
    for f in F: D.add_edge(src,(f,"o"),capacity=1)
    def ho(v): return v in F or v in interior
    def hi(v): return v in S or v in interior
    for u,w in G.edges():
        if ho(u) and hi(w): D.add_edge((u,"o"),(w,"i"),capacity=1)
        if ho(w) and hi(u): D.add_edge((w,"o"),(u,"i"),capacity=1)
    val,flow=nx.maximum_flow(D,src,snk)
    edges=set()
    for a,nbrs in flow.items():
        for b,f in nbrs.items():
            if f>0 and isinstance(a,tuple) and isinstance(b,tuple) and a[1]=="o" and b[1]=="i":
                edges.add(frozenset((a[0],b[0])))
    return int(val), edges

def field_route(G,F,S,cond):
    """Trường descent có khóa nút (đỉnh-rời) với conductance cho trước; trả số vai-trò sửa được."""
    dead=set(F)
    def hop(f):
        try: return min(nx.shortest_path_length(G,f,s) for s in S)
        except: return 1e9
    order=sorted(F,key=hop); locked=set(); used=set(); placed=0
    for f in order:
        avail=[s for s in S if s not in used]
        if not avail: break
        block=(dead-{f})|locked
        Glive=G.subgraph([v for v in G.nodes() if v not in block]).copy()
        if f not in Glive: continue
        u=harmonic_w(Glive,{f},set(avail),cond)
        p=descend(Glive,f,u,set(avail),locked)
        if p:
            placed+=1; used.add(p[-1])
            for v in p[1:-1]:
                if v not in S: locked.add(v)
    return placed

def main():
    t0=time.time(); GX=GY=8; m=10; TRIALS=400
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    summary={}
    for t in [4,5]:
        gap=0; oracle_solved=0; field_solved=0; boost_solved=0
        for _ in range(TRIALS):
            F=poc.sample_failures(G,S,t,clustered=True)
            val,edges=optimum_flow_edges(G,F,S)
            if val<t: continue                    # optimum cũng không sửa được -> bỏ
            fld=poc.field_disjoint(G,F,S)>=t
            if fld:                               # trường đều đã giải -> không phải khe hở
                field_solved+=1; continue
            gap+=1                                 # cấu hình KHE HỞ (opt ok, field fail)
            # oracle conductance: boost mạnh cạnh trên tuyến tối ưu
            cond={e:20.0 for e in edges}
            if field_route(G,F,S,cond)>=t: oracle_solved+=1
            # đối chứng: boost NGẪU NHIÊN cùng số cạnh (loại giả thuyết "boost gì cũng được")
            alledges=[frozenset(e) for e in G.edges()]
            ridx=rng.choice(len(alledges),size=min(len(edges),len(alledges)),replace=False)
            rcond={alledges[i]:20.0 for i in ridx}
            if field_route(G,F,S,rcond)>=t: boost_solved+=1
        summary[f"t={t}"]={
            "khe_ho_configs":gap,
            "oracle_conductance_giai_duoc":oracle_solved,
            "oracle_ty_le_khep_gap_%":round(100*oracle_solved/gap,1) if gap else None,
            "boost_ngau_nhien_giai_duoc":boost_solved,
            "boost_ngau_nhien_%":round(100*boost_solved/gap,1) if gap else None,
        }
    summary["runtime_sec"]=round(time.time()-t0,1)
    json.dump(summary,open(os.path.join(OUT,"results_oracle.json"),"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
