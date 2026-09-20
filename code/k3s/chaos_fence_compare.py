# -*- coding: utf-8 -*-
"""So sanh CertiHeal vs Baseline (K8s-tuned) tren cung lich chaos 1800s.
Doc chaos_fence_A_certiheal.json + chaos_fence_A_baseline.json -> fig_chaos_compare.png"""
import json, os, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import statistics as st
D=os.path.dirname(os.path.abspath(__file__))
def load(tag):
    d=json.load(open(os.path.join(D,f"chaos_fence_A_{tag}.json")))
    return d["timeseries"], d.get("events",[])
C,evC=load("certiheal"); B,evB=load("baseline")
DESIRED=max(max(p["avail"] for p in C), max(p["avail"] for p in B))
col={"certiheal":"#2e7d46","baseline":"#b0413e"}
fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True)
# (a) availability
for tag,ts in [("baseline",B),("certiheal",C)]:
    t=[p["t"]/60 for p in ts]; a=[p["avail"] for p in ts]
    ax[0].plot(t,a,color=col[tag],lw=1.3,label=f"{tag}")
ax[0].axhline(DESIRED,color="gray",ls=":",lw=1)
ax[0].set_ylabel(f"Roles available (/{DESIRED})"); ax[0].set_ylim(0,DESIRED+2)
ax[0].set_title("(a) Availability under the same chaos schedule (46 node+cluster faults, 30 min)")
ax[0].legend(); ax[0].grid(alpha=.3)
# (b) phan bo availability theo dai (ro rang hon load_std bi nhieu boi collapse)
bands=[(0,20),(20,30),(30,40),(40,DESIRED),(DESIRED,DESIRED+1)]
blab=["<20","20-29","30-39",f"40-{DESIRED-1}","full"]
def frac(ts):
    a=[p["avail"] for p in ts]; n=len(a)
    return [100*sum(lo<=x<hi for x in a)/n for (lo,hi) in bands]
import numpy as np
x=np.arange(len(blab)); w=0.38
fc=frac(C); fb=frac(B)
ax[1].bar(x-w/2,fb,w,color=col["baseline"],label="baseline")
ax[1].bar(x+w/2,fc,w,color=col["certiheal"],label="certiheal")
ax[1].set_xticks(x); ax[1].set_xticklabels(blab); ax[1].set_xlabel("Availability band (roles)")
ax[1].set_ylabel("% of time")
respC=sum(p.get("respread",0) for p in C); respB=sum(p.get("respread",0) for p in B)
ax[1].set_title(f"(b) Availability distribution: CertiHeal never below 30; baseline ~17% of time below 20 (rebalance-back {respC} vs {respB})")
ax[1].legend(); ax[1].grid(alpha=.3,axis="y")
fig.tight_layout(); out=os.path.join(D,"..","certiheal_poc","fig_chaos_compare.png")
fig.savefig(out,dpi=140,bbox_inches="tight"); print("wrote",out)
has_ls=lambda ts: ts and ("load_std" in ts[0])
def summ(ts,tag):
    a=[p["avail"] for p in ts]
    r=dict(mode=tag,avail_mean=round(st.mean(a),1),avail_min=min(a),
           avail_pct_full=round(100*sum(1 for x in a if x>=DESIRED-1)/len(a),1),
           respread=sum(p.get("respread",0) for p in ts))
    if has_ls(ts):
        ls=[p["load_std"] for p in ts]; r["load_std_mean"]=round(st.mean(ls),2); r["load_std_max"]=max(ls)
    return r
res={"certiheal":summ(C,"certiheal"),"baseline":summ(B,"baseline"),"roles":DESIRED}
print(json.dumps(res,indent=1)); json.dump(res,open(os.path.join(D,"results_chaos_compare.json"),"w"),indent=1)
