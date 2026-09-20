# -*- coding: utf-8 -*-
"""
Danh gia CHUNG CHI TIEN NGHIEM (robust) C_rob(G,S) bang VET CAN (tra loi #1):
  C_rob = max{t : voi MOI F, |F|<=t, maxflow(F,S) = |F|}  (don vi dung luong).
Tim kich thuoc loi NHO NHAT lam mat kha nang khoi phuc -> C_rob = size_that_bai - 1.
So sanh C_rob voi C(F,S) trung binh (ngau nhien theo cum) tai t=C_rob+1.
  python poc_crob.py
"""
import itertools, os, json
import numpy as np
import poc
OUT=os.path.dirname(os.path.abspath(__file__))

def crob(G, S, maxt=6):
    working=[v for v in G.nodes() if v not in S]
    for t in range(1, maxt+1):
        for F in itertools.combinations(working, t):
            Fs=set(F)
            if poc.optimum_disjoint(G, Fs, S) < t:      # co to hop t loi khong khoi phuc du
                return t-1, Fs
    return maxt, None

def nested_order(G):
    """Thu tu farthest-point (spread) de tao chuoi spare LONG NHAU S_m ⊆ S_{m+1}."""
    nodes=list(G.nodes()); order=[nodes[0]]
    while len(order)<len(nodes):
        best=None; bd=-1
        for v in nodes:
            if v in order: continue
            d=min((v[0]-u[0])**2+(v[1]-u[1])**2 for u in order)
            if d>bd: bd=d; best=v
        order.append(best)
    return order

def eval_seq(G, spare_of):
    ms=[4,6,8,10,12,16]
    out={"m":[], "Crob":[], "mean_C_at_t":[], "min_C_at_t":[], "max_C_at_t":[], "t_probe":[]}
    for m in ms:
        S=spare_of(m)
        cr,_=crob(G, S, maxt=6); t2=cr+1
        cs=[poc.optimum_disjoint(G, poc.sample_failures(G,S,t2,clustered=True), S) for _ in range(400)]
        out["m"].append(m); out["Crob"].append(int(cr)); out["t_probe"].append(int(t2))
        out["mean_C_at_t"].append(round(float(np.mean(cs)),2))
        out["min_C_at_t"].append(int(np.min(cs))); out["max_C_at_t"].append(int(np.max(cs)))
    return out

def main():
    GX=GY=6; G=poc.build_grid(GX,GY)
    # (A) khong long nhau: moi m dat lai spread rieng
    nonnested=eval_seq(G, lambda m: poc.place_spares(G,m,mode="spread"))
    # (B) LONG NHAU: S_m = m dau cua thu tu farthest-point
    order=nested_order(G)
    nested=eval_seq(G, lambda m: set(order[:m]))
    res={"grid":f"{GX}x{GY}","nonnested":nonnested,"nested":nested}
    json.dump(res, open(os.path.join(OUT,"results_crob.json"),"w"), indent=1)
    print(json.dumps(res, indent=1))

if __name__=="__main__":
    main()
