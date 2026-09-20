"""
CertiHeal-Edge — Quét QUY MÔ song song (đa tiến trình CPU).
Mục tiêu: đường cong "GNN khép khe hở TĂNG theo quy mô n" + "locality (K) đủ".
- Train GNN (rẻ, tuần tự) cho mỗi (n,K); EVAL corrective-capability chạy SONG SONG trên mọi nhân.
- CHECKPOINT results_scale_sweep.json sau mỗi (n,K) -> gián đoạn vẫn giữ kết quả.
Chạy nền, để 24h cũng ok:  python gnn_scale_sweep.py
"""
import os, json, time, numpy as np, torch
from multiprocessing import Pool, cpu_count
import poc
from poc3_oracle import optimum_flow_edges
from poc5_softroute import soft_route
from gnn_certiheal import GNN, sample_config, to_tensors, make_dataset, train, DEV
OUT=os.path.dirname(os.path.abspath(__file__))
RESULT=os.path.join(OUT,"results_scale_sweep.json")

# ---- worker: đánh giá 1 cấu hình (chạy trong tiến trình con) ----
def eval_one(args):
    G,F,S,cond_gnn = args
    t=len(F)
    val,opt = optimum_flow_edges(G,F,S)
    o_ok  = val>=t
    u_ok  = soft_route(G,F,S,{})>=t
    g_ok  = soft_route(G,F,S,cond_gnn)>=t
    or_ok = soft_route(G,F,S,{e:20.0 for e in opt})>=t
    return (o_ok,u_ok,g_ok,or_ok)

def gnn_conds(model, ev):
    """Tính cond do GNN dự đoán cho từng đồ thị eval (ở tiến trình chính, torch)."""
    model.eval(); conds=[]
    with torch.no_grad():
        for _,_,_,(x,ei,euv,y,pairs,_) in ev:
            p=torch.sigmoid(model(x.to(DEV),ei.to(DEV),euv.to(DEV))).cpu().numpy()
            conds.append({e:1.0+19.0*float(pi) for e,pi in zip(pairs,p)})
    return conds

def main():
    import argparse
    global RESULT
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    ap.add_argument("--t_frac",type=float,default=0.06)
    ap.add_argument("--sp_frac",type=float,default=0.15)
    ap.add_argument("--ns",type=int,nargs="+",default=[100,150,200,300,400,600,800])
    ap.add_argument("--tag",default="")
    a=ap.parse_args()
    SMOKE=a.smoke
    NS=a.ns; KS=[2,3]; TOPO="rgg"; T_FRAC=a.t_frac; SP_FRAC=a.sp_frac
    TRAIN_G=300; EVAL_G=250; EPOCHS=30
    if a.tag: RESULT=os.path.join(OUT,f"results_scale_{a.tag}.json")
    if SMOKE:
        NS=[64]; KS=[2]; TRAIN_G=20; EVAL_G=16; EPOCHS=5
        RESULT=os.path.join(OUT,"results_scale_smoke.json")
    W=max(1,cpu_count()-1)
    print(f"t_frac={T_FRAC} sp_frac={SP_FRAC} tag={a.tag} -> {os.path.basename(RESULT)}")
    print(f"device={DEV} workers={W} NS={NS} KS={KS} eval_graphs={EVAL_G}")
    rng=np.random.default_rng(0); torch.manual_seed(0)
    results=[]
    if os.path.exists(RESULT):
        try: results=json.load(open(RESULT,encoding="utf-8")).get("rows",[])
        except: results=[]
    done={(r["n"],r["K"]) for r in results}
    t0=time.time()
    with Pool(W) as pool:
        for n in NS:
            # sinh eval 1 lần/n, dùng chung cho các K (công bằng)
            print(f"[n={n}] gen data ...", flush=True)
            tr=make_dataset(TOPO,n,T_FRAC,SP_FRAC,TRAIN_G,rng)
            ev=make_dataset(TOPO,n,T_FRAC,SP_FRAC,EVAL_G,rng)
            base=[(G,F,S) for (G,F,S,_) in ev]
            for K in KS:
                if (n,K) in done:
                    print(f"[n={n} K={K}] skalready done", flush=True); continue
                tk=time.time()
                m=GNN(3,32,K).to(DEV); train(m,tr,EPOCHS)
                conds=gnn_conds(m,ev)
                args=[(base[i][0],base[i][1],base[i][2],conds[i]) for i in range(len(ev))]
                res=pool.map(eval_one, args)                 # SONG SONG
                arr=np.array(res,dtype=float)                # cols: opt,uni,gnn,oracle
                ko,ku,kg,kor=arr.mean(0)
                gap=ko-ku
                row={"n":n,"K":K,"eval_graphs":len(ev),
                     "kappa_optimum":round(ko,3),"kappa_uniform":round(ku,3),
                     "kappa_gnn":round(kg,3),"kappa_oracle":round(kor,3),
                     "gnn_gap_closed_pct": round(100*(kg-ku)/gap,1) if gap>1e-9 else None,
                     "oracle_gap_closed_pct": round(100*(kor-ku)/gap,1) if gap>1e-9 else None,
                     "params":sum(p.numel() for p in m.parameters()),
                     "sec":round(time.time()-tk,1)}
                results.append(row)
                json.dump({"meta":{"topo":TOPO,"t_frac":T_FRAC,"sp_frac":SP_FRAC,
                           "train_graphs":TRAIN_G,"eval_graphs":EVAL_G,"epochs":EPOCHS,
                           "workers":W,"elapsed_sec":round(time.time()-t0,1)},
                           "rows":results}, open(RESULT,"w",encoding="utf-8"),
                          ensure_ascii=False,indent=2)
                print(f"[n={n} K={K}] {json.dumps(row,ensure_ascii=False)}", flush=True)
    print("DONE total", round(time.time()-t0,1),"s ->", RESULT)

if __name__=="__main__":
    main()
