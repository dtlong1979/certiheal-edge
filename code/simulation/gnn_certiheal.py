"""
CertiHeal-Edge — Vòng 5: POLICY GNN (thay MLP 1-hop bằng GNN K-hop).
- Train: có thể chạy A100 (tu dong nhan cuda). Infer: GNN NÔNG K-hop -> chạy CPU/node biên (P1).
- Trục thí nghiệm hạng nhất: K (bán kính thu nhận = số vòng truyền thông) vs hiệu năng.
  => cho thấy "model nho-cuc-bo la du" (locality is enough) — luan diem edge-AI.
- Đầu ra: AUC + corrective-capability downstream (qua soft_route) so uniform/GNN/oracle/optimum.

Chạy nhanh (CPU smoke):   python gnn_certiheal.py --smoke
Chạy đầy đủ (A100):        python gnn_certiheal.py --topo rgg --n 400 --Ks 1 2 3 4 --train_graphs 600 --epochs 40 --eval_graphs 120
"""
import argparse, json, os, time, numpy as np, networkx as nx
import torch, torch.nn as nn
from sklearn.metrics import roc_auc_score
import poc
from poc2_ai import harmonic_w
from poc3_oracle import optimum_flow_edges
from poc5_softroute import soft_route
from poc8_generalize import make_rgg, spares_geo, fails_geo
OUT=os.path.dirname(os.path.abspath(__file__))
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# ----------------- sinh cấu hình + tensor hoá -----------------
def sample_config(topo, n, t_frac, sp_frac, rng):
    if topo=="grid":
        g=int(round(n**0.5)); G=poc.build_grid(g,g)
        m=max(4,int(round(sp_frac*G.number_of_nodes())))
        S=poc.place_spares(G,m); t=max(2,int(round(t_frac*G.number_of_nodes())))
        F=poc.sample_failures(G,S,t,clustered=True); pos=None
    else:
        G,pos=make_rgg(n); m=max(4,int(round(sp_frac*G.number_of_nodes())))
        S=spares_geo(G,m); t=max(2,int(round(t_frac*G.number_of_nodes())))
        F=fails_geo(G,pos,S,t)
    return G,F,S

def to_tensors(G,F,S):
    nodes=list(G.nodes()); idx={v:i for i,v in enumerate(nodes)}; n=len(nodes)
    Fset=set(F); Sset=set(S); maxdeg=max(dict(G.degree()).values()) or 1
    x=np.zeros((n,3),dtype=np.float32)
    for v in nodes:
        i=idx[v]; x[i]=[1.0 if v in Fset else 0.0, 1.0 if v in Sset else 0.0, G.degree(v)/maxdeg]
    # edge_index vô hướng (2 chiều) cho message passing
    ei=[]
    for u,w in G.edges(): ei+= [[idx[u],idx[w]],[idx[w],idx[u]]]
    edge_index=torch.tensor(ei,dtype=torch.long).t().contiguous()
    # cạnh cần chấm điểm + nhãn (trên tuyến tối ưu)
    _,opt=optimum_flow_edges(G,F,S)
    pairs=[]; e_uv=[]; y=[]
    for u,w in G.edges():
        if u in Fset and w in Fset: continue
        pairs.append(frozenset((u,w))); e_uv.append([idx[u],idx[w]])
        y.append(1.0 if frozenset((u,w)) in opt else 0.0)
    return (torch.tensor(x), edge_index, torch.tensor(e_uv,dtype=torch.long),
            torch.tensor(y,dtype=torch.float32), pairs, nodes)

# ----------------- GNN K-hop (thuần torch, không cần torch_geometric) -----------------
class GNN(nn.Module):
    def __init__(self, in_dim=3, hid=32, K=2):
        super().__init__(); self.K=K
        self.self_lin=nn.ModuleList([nn.Linear(in_dim if k==0 else hid,hid) for k in range(K)])
        self.nbr_lin =nn.ModuleList([nn.Linear(in_dim if k==0 else hid,hid) for k in range(K)])
        self.edge=nn.Sequential(nn.Linear(2*hid,hid),nn.ReLU(),nn.Linear(hid,1))
    def forward(self,x,edge_index,e_uv):
        src,dst=edge_index
        h=x
        for k in range(self.K):                      # K vòng: bán kính thu nhận = K hop
            agg=torch.zeros(h.size(0),h.size(1),device=h.device)
            deg=torch.zeros(h.size(0),1,device=h.device)
            agg.index_add_(0,dst,h[src]); deg.index_add_(0,dst,torch.ones(src.size(0),1,device=h.device))
            agg=agg/deg.clamp(min=1)
            h=torch.relu(self.self_lin[k](h)+self.nbr_lin[k](agg))
        hu=h[e_uv[:,0]]; hv=h[e_uv[:,1]]
        # đối xưng hoá (cạnh vô hướng)
        return self.edge(torch.cat([hu+hv, (hu-hv).abs()],1)).squeeze(-1)

# ----------------- train / eval -----------------
def make_dataset(topo,n,tf,sf,ng,rng):
    data=[]
    for _ in range(ng):
        G,F,S=sample_config(topo,n,tf,sf,rng)
        data.append((G,F,S,to_tensors(G,F,S)))
    return data

def train(model,data,epochs,lr=3e-3):
    opt=torch.optim.Adam(model.parameters(),lr=lr)
    pos=sum(t[3][3].sum().item() for t in data); tot=sum(t[3][3].numel() for t in data)
    pw=torch.tensor([(tot-pos)/max(pos,1)],device=DEV)
    lossf=nn.BCEWithLogitsLoss(pos_weight=pw)
    for ep in range(epochs):
        model.train(); tl=0
        for _,_,_,(x,ei,euv,y,_,_) in data:
            x,ei,euv,y=x.to(DEV),ei.to(DEV),euv.to(DEV),y.to(DEV)
            opt.zero_grad(); logit=model(x,ei,euv); l=lossf(logit,y)
            l.backward(); opt.step(); tl+=l.item()
    return model

@torch.no_grad()
def evaluate(model,data,eval_cc=40):
    model.eval(); ys=[]; ps=[]
    cc={"uniform":0,"gnn":0,"oracle":0,"optimum":0}; ncc=0
    for gi,(G,F,S,(x,ei,euv,y,pairs,_)) in enumerate(data):
        logit=model(x.to(DEV),ei.to(DEV),euv.to(DEV)).cpu()
        p=torch.sigmoid(logit).numpy()
        ys.append(y.numpy()); ps.append(p)
        if gi<eval_cc:                              # corrective capability downstream (đắt) -> giới hạn
            t=len(F)
            val,opt=optimum_flow_edges(G,F,S); cc["optimum"]+=(val>=t)
            cc["uniform"]+=(soft_route(G,F,S,{})>=t)
            cond={e:1.0+19.0*float(pi) for e,pi in zip(pairs,p)}
            cc["gnn"]+=(soft_route(G,F,S,cond)>=t)
            cc["oracle"]+=(soft_route(G,F,S,{e:20.0 for e in opt})>=t)
            ncc+=1
    auc=roc_auc_score(np.concatenate(ys),np.concatenate(ps))
    kk={k:round(v/max(ncc,1),3) for k,v in cc.items()}
    return round(float(auc),3),kk

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--topo",default="rgg"); ap.add_argument("--n",type=int,default=150)
    ap.add_argument("--t_frac",type=float,default=0.06); ap.add_argument("--sp_frac",type=float,default=0.15)
    ap.add_argument("--Ks",type=int,nargs="+",default=[1,2,3])
    ap.add_argument("--hid",type=int,default=32)
    ap.add_argument("--train_graphs",type=int,default=200); ap.add_argument("--eval_graphs",type=int,default=60)
    ap.add_argument("--epochs",type=int,default=25); ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args()
    if a.smoke: a.topo="grid"; a.n=64; a.Ks=[1,2]; a.train_graphs=40; a.eval_graphs=20; a.epochs=8
    rng=np.random.default_rng(0); torch.manual_seed(0)
    t0=time.time()
    print(f"device={DEV} topo={a.topo} n={a.n} Ks={a.Ks}")
    print("... gen data"); tr=make_dataset(a.topo,a.n,a.t_frac,a.sp_frac,a.train_graphs,rng)
    ev=make_dataset(a.topo,a.n,a.t_frac,a.sp_frac,a.eval_graphs,rng)
    rows=[]
    for K in a.Ks:
        m=GNN(3,a.hid,K).to(DEV); train(m,tr,a.epochs)
        auc,kk=evaluate(m,ev,eval_cc=a.eval_graphs)   # κ dùng HẾT eval_graphs (bỏ trần 40) -> giảm nhiễu
        gap=kk["optimum"]-kk["uniform"]
        closed=round(100*(kk["gnn"]-kk["uniform"])/gap,1) if gap>1e-9 else None
        row={"K_hop":K,"AUC":auc,"kappa":kk,"gnn_gap_closed_pct":closed,
             "comm_rounds":K,"params":sum(p.numel() for p in m.parameters())}
        rows.append(row); print(json.dumps(row,ensure_ascii=False))
    out={"device":DEV,"topo":a.topo,"n":a.n,"rows":rows,"runtime_sec":round(time.time()-t0,1)}
    tag="smoke" if a.smoke else f"{a.topo}_n{a.n}"
    json.dump(out,open(os.path.join(OUT,f"results_gnn_{tag}.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print("saved results_gnn_"+tag+".json  runtime",out["runtime_sec"],"s")

if __name__=="__main__":
    main()
