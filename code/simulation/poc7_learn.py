"""
CertiHeal-Edge PoC — Vòng 4: thay ORACLE bằng POLICY HỌC THẬT (mắt xích cuối ĐG1').
Học một bộ phân loại cạnh (chỉ ĐẶC TRƯNG CỤC BỘ 1-2 hop) dự đoán "cạnh này nên tăng
conductance" (imitation nhãn = cạnh nằm trên tuyến tối ưu max-flow). Suy luận: đặt
cond = 1 + 19*p_hoc, chạy soft-routing, đo κ. Nếu learned tiến gần oracle và vượt uniform
=> ĐG1' KHẢ THI bằng học máy thật, phi tập trung (đặc trưng cục bộ), không cần oracle.
"""
import numpy as np, networkx as nx, json, os, time
import poc
from poc2_ai import harmonic_w
from poc3_oracle import optimum_flow_edges
from poc5_softroute import soft_route
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(4242)

def live_graph(G,F):
    dead=set(F); Glive=G.subgraph([v for v in G.nodes() if v not in dead]).copy()
    for f in F:
        Glive.add_node(f)
        for w in G.neighbors(f):
            if w in Glive: Glive.add_edge(f,w)
    return Glive

def config_features(G,F,S):
    """Trả (edges, X, y): đặc trưng CỤC BỘ mỗi cạnh + nhãn (trên tuyến tối ưu)."""
    Glive=live_graph(G,F)
    pot=harmonic_w(Glive,set(F),set(S),{})     # trường đều: source=F(1), sink=S(0)
    Sset=set(S); Fset=set(F)
    spare_adj={v for s in S for v in G.neighbors(s)}|Sset
    fail_adj={v for f in F for v in G.neighbors(f)}|Fset
    val,opt_edges=optimum_flow_edges(G,F,S)
    edges=[]; X=[]; y=[]
    for u,w in G.edges():
        if u in Fset and w in Fset: continue     # cạnh giữa 2 node chết
        pu=pot.get(u,1e3); pw=pot.get(w,1e3)
        if pu>=1e3 and pw>=1e3: continue          # cạnh không tới sink
        feat=[
            min(pu,pw), max(pu,pw), abs(pu-pw),          # thế + dòng-proxy
            G.degree(u), G.degree(w),                     # bậc cục bộ
            int(u in spare_adj)+int(w in spare_adj),      # gần spare
            int(u in fail_adj)+int(w in fail_adj),        # gần lỗi
            int(u in Fset)+int(w in Fset),                # là nguồn
            int(u in Sset)+int(w in Sset),                # là spare
        ]
        edges.append(frozenset((u,w))); X.append(feat)
        y.append(1 if frozenset((u,w)) in opt_edges else 0)
    return edges, np.array(X,dtype=float), np.array(y)

def build_dataset(G,S,n,t):
    Xs=[]; ys=[]
    for _ in range(n):
        F=poc.sample_failures(G,S,t,clustered=True)
        _,X,y=config_features(G,F,S)
        if len(X): Xs.append(X); ys.append(y)
    return np.vstack(Xs), np.concatenate(ys)

def eval_policy(G,S,model,mu,sd,t,ncfg):
    """Đo κ: uniform vs learned-conductance vs oracle vs optimum trên ncfg cấu hình mới."""
    cu=cl=co=cop=0
    for _ in range(ncfg):
        F=poc.sample_failures(G,S,t,clustered=True)
        val,opt_edges=optimum_flow_edges(G,F,S); cop+=(val>=t)
        cu+=(soft_route(G,F,S,{})>=t)
        # learned conductance
        edges,X,_=config_features(G,F,S)
        if len(X):
            p=model.predict_proba((X-mu)/sd)[:,1]
            cond={e:1.0+19.0*pi for e,pi in zip(edges,p)}
        else: cond={}
        cl+=(soft_route(G,F,S,cond)>=t)
        co+=(soft_route(G,F,S,{e:20.0 for e in opt_edges})>=t)
    n=ncfg
    return {"kappa_optimum":round(cop/n,3),"kappa_oracle_cond":round(co/n,3),
            "kappa_learned_cond":round(cl/n,3),"kappa_uniform_soft":round(cu/n,3)}

def main():
    t0=time.time(); GX=GY=8; m=10; T=5
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    print("... build train set"); Xtr,ytr=build_dataset(G,S,500,T)
    Xva,yva=build_dataset(G,S,150,T)
    mu=Xtr.mean(0); sd=Xtr.std(0); sd[sd==0]=1
    Xtrn=(Xtr-mu)/sd; Xvan=(Xva-mu)/sd
    out={"n_train_edges":int(len(ytr)),"pos_rate":round(float(ytr.mean()),3)}
    models={}
    for name,clf in [("logreg",LogisticRegression(max_iter=1000,class_weight="balanced")),
                     ("mlp",MLPClassifier(hidden_layer_sizes=(32,16),max_iter=400,random_state=0))]:
        clf.fit(Xtrn,ytr)
        auc=roc_auc_score(yva,clf.predict_proba(Xvan)[:,1])
        out[f"AUC_{name}"]=round(float(auc),3); models[name]=clf
    best=max(models,key=lambda k:out[f"AUC_{k}"])
    out["best_model"]=best
    print(f"... eval policy ({best}, AUC={out['AUC_'+best]})")
    out["kappa"]=eval_policy(G,S,models[best],mu,sd,T,150)
    # % khe hở uniform mà learned khép được
    k=out["kappa"]; gap=k["kappa_optimum"]-k["kappa_uniform_soft"]
    out["gap_closed_by_learned_pct"]=round(100*(k["kappa_learned_cond"]-k["kappa_uniform_soft"])/gap,1) if gap>1e-9 else None
    out["gap_closed_by_oracle_pct"]=round(100*(k["kappa_oracle_cond"]-k["kappa_uniform_soft"])/gap,1) if gap>1e-9 else None
    out["runtime_sec"]=round(time.time()-t0,1)
    json.dump(out,open(os.path.join(OUT,"results_learned.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
