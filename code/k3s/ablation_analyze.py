# -*- coding: utf-8 -*-
"""
Phan tich ABLATION: doc ablation_A_<config>_<seed>.json -> thong ke moi config qua cac seed
(mean±CI95, median/IQR, min availability, #tick treo) + CONFUSION MATRIX per-tick
(cert=spare_cap>=orphaned du bao khong-treo; thuc te=pending>0) voi FALSE-SAFE rate + bootstrap CI.
  python ablation_analyze.py
"""
import glob, os, json, math
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
D=os.path.dirname(os.path.abspath(__file__))
ORDER=["k8s","fence","reassign","full"]

def boot_ci(x, f=np.mean, n=2000):
    x=np.array(x)
    if len(x)==0: return (0,0,0)
    bs=[f(np.random.choice(x,len(x),replace=True)) for _ in range(n)]
    return (round(float(f(x)),2), round(float(np.percentile(bs,2.5)),2), round(float(np.percentile(bs,97.5)),2))

runs={}
for fn in glob.glob(os.path.join(D,"ablation_A_*.json")):
    d=json.load(open(fn)); runs.setdefault(d["config"],[]).append(d)

res={}; conf_overall={"TP":0,"FP":0,"TN":0,"FN":0}
for cfg in ORDER:
    rr=runs.get(cfg,[])
    if not rr: continue
    means=[np.mean([p["avail"] for p in r["timeseries"]]) for r in rr]
    mins=[min(p["avail"] for p in r["timeseries"]) for r in rr]
    hang_ticks=[sum(1 for p in r["timeseries"] if p["pending"]>0) for r in rr]
    C={"TP":0,"FP":0,"TN":0,"FN":0}
    for r in rr:
        for p in r["timeseries"]:
            if p["notready"]==0: continue                  # chi xet luc co loi
            pred_ok = p["spare_cap"] >= p["orphaned"]       # chung chi noi: khoi phuc du
            hang = p["pending"]>0
            if pred_ok and not hang: C["TP"]+=1
            elif pred_ok and hang:   C["FP"]+=1             # FALSE-SAFE (nguy hiem)
            elif (not pred_ok) and hang: C["TN"]+=1
            else: C["FN"]+=1                                # bao thu
    for k in C: conf_overall[k]+=C[k]
    fs = C["FP"]/max(1,C["TP"]+C["FP"])
    res[cfg]=dict(n_seed=len(rr),
        avail_mean_ci=boot_ci(means), avail_median=round(float(np.median(means)),2),
        avail_iqr=[round(float(np.percentile(means,25)),2),round(float(np.percentile(means,75)),2)],
        avail_min=round(float(np.min(mins)),1),
        hang_ticks_mean=round(float(np.mean(hang_ticks)),1),
        confusion=C, false_safe_rate=round(fs,4))
fs_all=conf_overall["FP"]/max(1,conf_overall["TP"]+conf_overall["FP"])
res["_overall_confusion"]=conf_overall; res["_overall_false_safe_rate"]=round(fs_all,4)
json.dump(res, open(os.path.join(D,"results_ablation.json"),"w"), indent=1)
print(json.dumps(res, indent=1))

# figure: (a) availability ladder ±CI, (b) false-safe rate per config
cfgs=[c for c in ORDER if c in res]
if cfgs:
    fig,ax=plt.subplots(1,2,figsize=(11,4.2))
    mid=[res[c]["avail_mean_ci"][0] for c in cfgs]
    lo=[res[c]["avail_mean_ci"][0]-res[c]["avail_mean_ci"][1] for c in cfgs]
    hi=[res[c]["avail_mean_ci"][2]-res[c]["avail_mean_ci"][0] for c in cfgs]
    ax[0].bar(cfgs,mid,yerr=[lo,hi],capsize=5,color="#2e6fb0",alpha=.85)
    ax[0].set_ylabel("Mean roles available"); ax[0].set_title("(a) Ablation ladder (mean ± 95% CI over seeds)")
    ax[0].grid(alpha=.3,axis="y")
    fsr=[100*res[c]["false_safe_rate"] for c in cfgs]
    ax[1].bar(cfgs,fsr,color="#b0413e",alpha=.85)
    ax[1].set_ylabel("False-safe rate (%)"); ax[1].set_title("(b) P(hang | certificate says OK)")
    ax[1].grid(alpha=.3,axis="y")
    fig.tight_layout(); out=os.path.join(D,"..","certiheal_poc","fig_ablation.png")
    fig.savefig(out,dpi=140,bbox_inches="tight"); print("wrote",out)
