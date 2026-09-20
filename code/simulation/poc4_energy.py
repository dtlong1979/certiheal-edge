"""
CertiHeal-Edge PoC — Bước B (tái khung ĐG1): learned/energy-aware conductance
KHÔNG để giành corrective capability (đã do chứng chỉ+fallback bảo đảm), mà để tối ưu
NĂNG LƯỢNG/TUỔI THỌ TRONG tập tuyến khả-thi. Kiểm: conductance nhận-biết-năng-lượng có
(a) GIỮ nguyên corrective capability, và (b) chọn tuyến "an toàn năng lượng" hơn không?
"""
import numpy as np, networkx as nx, json, os, time
import poc
from poc2_ai import harmonic_w, descend
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(99)

def route_with_energy(G,F,S,energy,use_energy):
    """Trả (placed, min_energy_dùng, mean_energy_spare). cond edge = f(energy) nếu use_energy."""
    dead=set(F)
    if use_energy:
        cond={frozenset((u,w)): 0.1+min(energy[u],energy[w]) for u,w in G.edges()}
    else:
        cond={}
    def hop(f):
        try: return min(nx.shortest_path_length(G,f,s) for s in S)
        except: return 1e9
    order=sorted(F,key=hop); locked=set(); used=set(); placed=0
    route_min_e=[]; spare_e=[]
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
            interior=[v for v in p[1:-1] if v not in S]
            route_min_e.append(min([energy[v] for v in interior], default=1.0))
            spare_e.append(energy[p[-1]])
            for v in interior: locked.add(v)
    return placed, (np.mean(route_min_e) if route_min_e else np.nan), (np.mean(spare_e) if spare_e else np.nan)

def main():
    t0=time.time(); GX=GY=8; m=10; TRIALS=400; t=4
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    ku=ke=0; du=[]; de=[]; su=[]; se=[]; both=0
    for _ in range(TRIALS):
        F=poc.sample_failures(G,S,t,clustered=True)
        energy={v: float(rng.uniform(0.15,1.0)) for v in G.nodes()}
        pu,mu,spu=route_with_energy(G,F,S,energy,use_energy=False)
        pe,me,spe=route_with_energy(G,F,S,energy,use_energy=True)
        ku+=(pu>=t); ke+=(pe>=t)
        if pu>=t and pe>=t:           # so "chất lượng năng lượng" khi CẢ HAI cùng sửa được
            both+=1; du.append(mu); de.append(me); su.append(spu); se.append(spe)
    res={"t":t,"TRIALS":TRIALS,"m":m,
        "kappa_uniform":round(ku/TRIALS,3), "kappa_energy_aware":round(ke/TRIALS,3),
        "configs_both_solved":both,
        "route_bottleneck_energy_uniform":round(float(np.mean(du)),3),
        "route_bottleneck_energy_aware":round(float(np.mean(de)),3),
        "spare_energy_uniform":round(float(np.mean(su)),3),
        "spare_energy_aware":round(float(np.mean(se)),3),
        "runtime_sec":round(time.time()-t0,1)}
    # ý nghĩa thống kê thô (paired)
    du=np.array(du); de=np.array(de)
    res["route_energy_gain"]=round(float(np.mean(de-du)),3)
    res["route_energy_gain_pct_configs_better"]=round(float(np.mean(de>du))*100,1)
    json.dump(res,open(os.path.join(OUT,"results_energy.json"),"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)
    json.dump({"du":du.tolist(),"de":de.tolist(),
               "su":[float(x) for x in su],"se":[float(x) for x in se]},
              open(os.path.join(OUT,"results_energy_pairs.json"),"w",encoding="utf-8"))
    print(json.dumps(res,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
