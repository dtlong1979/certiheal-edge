"""
CertiHeal-Edge — Hướng B: RL-ROUTER (học THẲNG luật routing) để bắt oracle headroom.
Thay vì học conductance cho soft-router cố định (Vòng 4-5, chỉ khép ~15%), ở đây policy
GNN CHỌN TRỰC TIẾP hop kế tiếp khi định tuyến từng vai-trò mồ côi tới spare, huấn luyện
bằng REINFORCE với reward = có tới spare không (tuyến đỉnh-rời, khóa nút).
Phép thử: κ RL-router có tiến gần ORACLE (và > learned-conductance) không?
"""
import argparse, json, os, time, numpy as np, networkx as nx, torch, torch.nn as nn
import poc
from poc3_oracle import optimum_flow_edges
from poc5_softroute import soft_route
from gnn_certiheal import sample_config
OUT=os.path.dirname(os.path.abspath(__file__)); DEV="cuda" if torch.cuda.is_available() else "cpu"

def tensors(G,F,S):
    nodes=list(G.nodes()); idx={v:i for i,v in enumerate(nodes)}; n=len(nodes)
    Fset,Sset=set(F),set(S); md=max(dict(G.degree()).values()) or 1
    x=np.zeros((n,3),np.float32)
    for v in nodes: x[idx[v]]=[1.0 if v in Fset else 0,1.0 if v in Sset else 0,G.degree(v)/md]
    ei=[]
    for u,w in G.edges(): ei+=[[idx[u],idx[w]],[idx[w],idx[u]]]
    return torch.tensor(x),torch.tensor(ei,dtype=torch.long).t().contiguous(),idx,nodes

class Policy(nn.Module):
    def __init__(self,in_dim=3,hid=48,K=3):
        super().__init__(); self.K=K
        self.sl=nn.ModuleList([nn.Linear(in_dim if k==0 else hid,hid) for k in range(K)])
        self.nl=nn.ModuleList([nn.Linear(in_dim if k==0 else hid,hid) for k in range(K)])
        self.hop=nn.Sequential(nn.Linear(2*hid,hid),nn.ReLU(),nn.Linear(hid,1))
    def embed(self,x,ei):
        src,dst=ei; h=x
        for k in range(self.K):
            agg=torch.zeros(h.size(0),h.size(1),device=h.device); deg=torch.zeros(h.size(0),1,device=h.device)
            agg.index_add_(0,dst,h[src]); deg.index_add_(0,dst,torch.ones(src.size(0),1,device=h.device))
            h=torch.relu(self.sl[k](h)+self.nl[k](agg/deg.clamp(min=1)))
        return h
    def score(self,h,cur_i,cand_i):
        hu=h[cur_i].expand(len(cand_i),-1); hc=h[cand_i]
        return self.hop(torch.cat([hu,hc],1)).squeeze(-1)

def episode(pol,G,F,S,idx,h,train=True,stochastic=False,max_steps=None):
    dead,Sset=set(F),set(S); locked=set(); used=set(); placed=0; logps=[]; rews=[]
    # 1 lần: khoảng cách tới spare gần nhất cho MỌI nút (multi-source BFS tự viết) -> ordering rẻ
    from collections import deque
    d2s={s:0 for s in S}; q=deque(S)
    while q:
        u=q.popleft()
        for w in G.neighbors(u):
            if w not in d2s: d2s[w]=d2s[u]+1; q.append(w)
    order=sorted(F,key=lambda f:d2s.get(f,1e9))
    ms=max_steps or G.number_of_nodes()          # bỏ nx.diameter (đắt); cap = n
    for f in order:
        avail=set(s for s in S if s not in used)
        if not avail: break
        cur=f; visited={f}; tlog=[]; ok=False
        for _ in range(ms):
            if cur in avail: ok=True; break
            cands=[w for w in G.neighbors(cur) if w not in visited and w not in dead|locked
                   and (w in avail or w not in Sset)]
            if not cands: break
            ci=torch.tensor([idx[c] for c in cands],device=h.device)
            logit=pol.score(h,idx[cur],ci); prob=torch.softmax(logit,0)
            if train:
                d=torch.distributions.Categorical(prob); a=d.sample(); tlog.append(d.log_prob(a)); a=a.item()
            elif stochastic:
                a=int(torch.distributions.Categorical(prob).sample().item())
            else: a=int(torch.argmax(prob).item())
            cur=cands[a]; visited.add(cur)
        if ok:
            placed+=1; used.add(cur)
            for v in visited-{f,cur}:
                if v not in Sset: locked.add(v)
            r=1.0
        else: r=0.0
        if train and tlog: logps.append(torch.stack(tlog).sum()); rews.append(r)
    return placed/len(F), logps, rews

def evaluate(pol,data,Kroll=12):
    ck={"rl_greedy":0,"rl_bestK":0,"uni":0,"oracle":0,"opt":0}; n=len(data)
    with torch.no_grad():
        for G,F,S in data:
            t=len(F); x,ei,idx,_=tensors(G,F,S); h=pol.embed(x.to(DEV),ei.to(DEV))
            fg,_,_=episode(pol,G,F,S,idx,h,train=False,stochastic=False)  # greedy
            ck["rl_greedy"]+=(round(fg*t)>=t)
            best=max(round(episode(pol,G,F,S,idx,h,train=False,stochastic=True)[0]*t)
                     for _ in range(Kroll))                                # best-of-K (công bằng soft_route)
            ck["rl_bestK"]+=(best>=t)
            val,opt=optimum_flow_edges(G,F,S); ck["opt"]+=(val>=t)
            ck["uni"]+=(soft_route(G,F,S,{})>=t)
            ck["oracle"]+=(soft_route(G,F,S,{e:20.0 for e in opt})>=t)
    return {k:round(v/n,3) for k,v in ck.items()}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n",type=int,default=120); ap.add_argument("--K",type=int,default=3)
    ap.add_argument("--episodes",type=int,default=3000); ap.add_argument("--eval_graphs",type=int,default=80)
    ap.add_argument("--t_frac",type=float,default=0.06); ap.add_argument("--sp_frac",type=float,default=0.15)
    ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args()
    if a.smoke: a.n=64; a.episodes=300; a.eval_graphs=20
    rng=np.random.default_rng(0); torch.manual_seed(0)
    pol=Policy(3,48,a.K).to(DEV); optim=torch.optim.Adam(pol.parameters(),lr=2e-3)
    base=0.0; t0=time.time(); hist=[]
    print(f"device={DEV} n={a.n} K={a.K} episodes={a.episodes}")
    for ep in range(1,a.episodes+1):
        G,F,S=sample_config("rgg",a.n,a.t_frac,a.sp_frac,rng)
        x,ei,idx,_=tensors(G,F,S); h=pol.embed(x.to(DEV),ei.to(DEV))
        frac,logps,rews=episode(pol,G,F,S,idx,h,train=True)
        if logps:
            R=torch.tensor(rews,device=DEV); adv=R-base
            loss=-(adv*torch.stack(logps)).mean()
            optim.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(pol.parameters(),2.0); optim.step()
            base=0.98*base+0.02*float(R.mean())
        if ep%500==0:
            print(f"  ep{ep} base={base:.3f} elapsed={time.time()-t0:.0f}s",flush=True)
    # eval
    evd=[sample_config("rgg",a.n,a.t_frac,a.sp_frac,rng)[:3] for _ in range(a.eval_graphs)]
    evd=[(G,F,S) for (G,F,S) in evd]
    torch.save(pol.state_dict(), os.path.join(OUT,f"rl_policy_n{a.n}.pt"))
    kk=evaluate(pol,evd)
    gap=kk["opt"]-kk["uni"]
    out={"n":a.n,"K":a.K,"episodes":a.episodes,"kappa":kk,
         "rl_bestK_gap_closed_pct":round(100*(kk["rl_bestK"]-kk["uni"])/gap,1) if gap>1e-9 else None,
         "rl_greedy_gap_closed_pct":round(100*(kk["rl_greedy"]-kk["uni"])/gap,1) if gap>1e-9 else None,
         "oracle_gap_closed_pct":round(100*(kk["oracle"]-kk["uni"])/gap,1) if gap>1e-9 else None,
         "runtime_sec":round(time.time()-t0,1)}
    json.dump(out,open(os.path.join(OUT,f"results_rl_n{a.n}.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
