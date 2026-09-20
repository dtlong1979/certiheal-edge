# -*- coding: utf-8 -*-
"""
Phan tich fabric_results.json -> bang + figure cap bai bao.
(a) Role coverage vs k (so node edge chet), baseline vs CertiHeal, vung 'certificate: feasible' (k<=3).
(b) Confusion cua certificate (feasible <-> CertiHeal phuc hoi 100%) + false-safe rate (fail-closed).
    kem thoi gian phuc hoi vs k.
  python fabric_analyze.py
"""
import json, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
D=os.path.dirname(os.path.abspath(__file__))
R=json.load(open(os.path.join(D,"fabric_results.json")))
NROLE=R[0]["nrole"]; KS=sorted({r["k"] for r in R})

def agg(cond):
    out={}
    for k in KS:
        rr=[r for r in R if r["cond"]==cond and r["k"]==k]
        if not rr: continue
        cov=[r["cov_final"] for r in rr]; rec=[r["recov_s"] for r in rr]; dup=[r.get("dup",0) for r in rr]
        out[k]=dict(n=len(rr),cov_mean=float(np.mean(cov)),cov_min=int(np.min(cov)),cov_max=int(np.max(cov)),
                    pct=round(100*np.mean(cov)/NROLE,1),rec_mean=round(float(np.mean(rec)),1),rec_sd=round(float(np.std(rec)),1),
                    dup_mean=round(float(np.mean(dup)),2),dup_max=int(np.max(dup)),dup_total=int(np.sum(dup)),
                    feasible=rr[0]["cert_feasible"])
    return out
B=agg("baseline"); C=agg("certiheal"); P=agg("peer"); CK=agg("ckill")
has_peer=bool(P); has_ck=bool(CK)
# ckill: coordinator bi giet giua recovery -> kiem recovery van hoan tat + khong double-booking
ck_runs=[r for r in R if r["cond"]=="ckill"]
ck_summary=dict(n=len(ck_runs),
                full_recovery=sum(1 for r in ck_runs if r["cov_final"]==NROLE),
                dup_total=sum(r.get("dup",0) for r in ck_runs),
                feasible_full=sum(1 for r in ck_runs if r["cert_feasible"] and r["cov_final"]==NROLE),
                feasible_n=sum(1 for r in ck_runs if r["cert_feasible"]),
                by_k={k:dict(pct=CK[k]["pct"],dup_total=CK[k]["dup_total"],n=CK[k]["n"]) for k in CK}) if ck_runs else None

# confusion: certificate feasible <-> CertiHeal phuc hoi day du (cov==NROLE)
conf={"TP":0,"FP":0,"TN":0,"FN":0}
for r in R:
    if r["cond"]!="certiheal": continue
    feas=r["cert_feasible"]; full=(r["cov_final"]==NROLE)
    if feas and full: conf["TP"]+=1
    elif feas and not full: conf["FP"]+=1     # FALSE-SAFE: cert hua kha-thi nhung KHONG phuc hoi day du
    elif (not feas) and (not full): conf["TN"]+=1
    else: conf["FN"]+=1
fsr=conf["FP"]/max(1,conf["TP"]+conf["FP"])

dup_tot=lambda cond: sum(r.get("dup",0) for r in R if r["cond"]==cond)
res=dict(nrole=NROLE,baseline=B,certiheal=C,peer=P,confusion=conf,false_safe_rate=round(fsr,4),
         dup_total={"certiheal":dup_tot("certiheal"),"peer":dup_tot("peer"),"ckill":dup_tot("ckill")},
         cov_tie=all(abs(P[k]["pct"]-C[k]["pct"])<1e-9 for k in KS if k in P and k in C) if has_peer else None,
         coordinator_kill=ck_summary,
         seeds=sorted({r["seed"] for r in R}))
json.dump(res,open(os.path.join(D,"results_fabric.json"),"w"),indent=1)
print(json.dumps(res,indent=1))

# ---------- figure ----------
fig,ax=plt.subplots(1,2,figsize=(11.5,4.3))
ks=list(KS)
bpct=[B[k]["pct"] for k in ks]; cpct=[C[k]["pct"] for k in ks]
# vung feasible (k<=3): certificate bao phuc hoi kha-thi
kmax_feas=max([k for k in ks if C[k]["feasible"]],default=0)
ax[0].axvspan(min(ks)-0.5,kmax_feas+0.5,color="#2e6fb0",alpha=.08)
ax[0].text((min(ks)-0.5+kmax_feas+0.5)/2,50.5,"certificate: recoverable",ha="center",va="bottom",fontsize=8,color="#2e6fb0")
ax[0].text((kmax_feas+0.5+max(ks)+0.4)/2,50.5,"certificate: not recoverable",ha="center",va="bottom",fontsize=8,color="#8a3b38")
if has_peer:                                    # duong peer-heuristic (cuu cuc bo, khong certificate); whisker = min..max (khong tat dinh)
    ppct=[P[k]["pct"] for k in ks]
    plo=[100*(P[k]["cov_mean"]-P[k]["cov_min"])/NROLE for k in ks]; phi=[100*(P[k]["cov_max"]-P[k]["cov_mean"])/NROLE for k in ks]
    ax[0].errorbar(ks,ppct,yerr=[plo,phi],fmt="--^",color="#4a8a4a",capsize=3,label="Peer heuristic (local, no certificate)",zorder=2)
ax[0].plot(ks,cpct,"-o",color="#2e6fb0",label="CertiHeal (local field recovery)",zorder=3)
ax[0].plot(ks,bpct,"-s",color="#b0413e",label="Baseline (central control plane only)")
ax[0].axhline(100,ls=":",color="gray",lw=.8)
ax[0].set_xlabel("Edge nodes lost during control-plane partition (k)")
ax[0].set_ylabel("Role coverage (%)"); ax[0].set_ylim(50,105)
ax[0].set_title("(a) Coverage under control-plane partition"); ax[0].legend(fontsize=8,loc="upper right"); ax[0].grid(alpha=.3)
# panel b: double-booking (no-double-booking invariant) peer vs CertiHeal
import numpy as _np
xb=_np.arange(len(ks)); w=0.38
pdup=[P[k]["dup_total"] for k in ks] if has_peer else [0]*len(ks)
cdup=[C[k]["dup_total"] for k in ks]
ax[1].bar(xb-w/2,pdup,w,color="#4a8a4a",label=f"Peer heuristic (total {sum(pdup)})")
ax[1].bar(xb+w/2,cdup,w,color="#2e6fb0",label=f"CertiHeal (total {sum(cdup)})")
ax[1].set_xticks(xb); ax[1].set_xticklabels(ks)
ax[1].set_xlabel("Edge nodes lost (k)"); ax[1].set_ylabel("Double-booked roles (5 seeds)")
ax[1].set_title(f"(b) Double-booking; certificate false-safe = {100*fsr:.1f}%")
ax[1].legend(fontsize=8); ax[1].grid(alpha=.3,axis="y")
fig.tight_layout(); out=os.path.join(D,"fig_fabric.png"); fig.savefig(out,dpi=140,bbox_inches="tight")
print("wrote",out)
