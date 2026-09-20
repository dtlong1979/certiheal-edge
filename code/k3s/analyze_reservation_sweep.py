# -*- coding: utf-8 -*-
"""
Phan tich results_res_sweep.json -> confusion + false-safe cho tung arm (certonly vs reservation/dryrun).
certonly declared feasible = slot_feasible (model uniform-slot).  reservation = admit_feasible (cpu that).
false-safe = declared feasible NHUNG hang (co Pending).
  python analyze_reservation_sweep.py
"""
import json, os
D=os.path.dirname(os.path.abspath(__file__))
d=json.load(open(os.path.join(D,"results_res_sweep.json"),encoding="utf-8"))
eps=d["episodes"]

def decl_of(e, rule):
    if rule=="slot":        return e["slot_feasible"]          # model uniform-slot certificate (sum slot)
    if rule=="cpu":         return e["admit_feasible"]         # admission = sum cpu-request (van la SUM, khong bat fragmentation)
    if rule=="reservation": return e["pending"]==0             # fail-closed: chi tuyen success khi placement THAT nhan het
    return False

def conf(rule):
    TP=FP=TN=FN=0
    for e in eps:
        decl=decl_of(e,rule); hang=e["hang"]
        if decl and not hang: TP+=1
        elif decl and hang:   FP+=1        # FALSE-SAFE
        elif (not decl) and hang: TN+=1
        else: FN+=1
    fs=FP/(TP+FP) if (TP+FP) else 0.0
    return dict(TP=TP,FP=FP,TN=TN,FN=FN,declared_feasible=TP+FP,false_safe_pct=round(100*fs,1))

arms={"certonly (model slot-certificate, sum)":"slot",
      "admission (real cpu, sum)":"cpu",
      "reservation (real acceptance, fail-closed)":"reservation"}
print(f"=== K3s reservation sweep: {len(eps)} episodes, {d['total_pods']} pods, demand {d['real_demand']} cpu ===")
print(f"{'arm':<36} {'declFeas':>8} {'TP':>3} {'FP':>3} {'TN':>3} {'FN':>3} {'false-safe%':>11}")
summary={}
for name,key in arms.items():
    c=conf(key); summary[name]=c
    print(f"{name:<36} {c['declared_feasible']:>8} {c['TP']:>3} {c['FP']:>3} {c['TN']:>3} {c['FN']:>3} {c['false_safe_pct']:>10}%")
# per-L breakdown
print("\nPer-L (sched nodes, mean pending, slot_feas, admit_feas):")
byL={}
for e in eps: byL.setdefault(e["L"],[]).append(e)
for L in sorted(byL):
    g=byL[L]; mp=sum(x["pending"] for x in g)/len(g)
    print(f"  L={L:<2} sched={g[0]['sched_nodes']} mean_pend={mp:.1f} slot_feas={g[0]['slot_feasible']} admit_feas={g[0]['admit_feasible']} hang={sum(1 for x in g if x['hang'])}/{len(g)}")
json.dump(dict(episodes=len(eps),arms=summary,real_demand=d["real_demand"],total_pods=d["total_pods"]),
          open(os.path.join(D,"results_res_sweep_summary.json"),"w"),ensure_ascii=False,indent=1)
print("\n-> results_res_sweep_summary.json")
