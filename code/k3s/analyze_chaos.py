# -*- coding: utf-8 -*-
import json, os, statistics as st
D=os.path.dirname(os.path.abspath(__file__))
d=json.load(open(os.path.join(D,"results_chaos_A.json"),encoding="utf-8"))
ts=d["timeseries"]; sched=d["schedule"]; DUR=d["duration"]
kills=[e for e in sched if e[1]=="kill"]
desired=ts[0]["desired"]
# 1) availability
full=[p for p in ts if p["avail"]==p["desired"]]
mean_av=st.mean(p["avail"] for p in ts); min_av=min(p["avail"] for p in ts)
# 2) node dynamics
max_nr=max(p["notready"] for p in ts)
nr_dist={}
for p in ts: nr_dist[p["notready"]]=nr_dist.get(p["notready"],0)+1
# 3) recovery episodes: doan lien tiep avail<desired
episodes=[]; i=0
while i<len(ts):
    if ts[i]["avail"]<ts[i]["desired"]:
        j=i; peak_nr=0; peak_pend=0
        while j<len(ts) and ts[j]["avail"]<ts[j]["desired"]:
            peak_nr=max(peak_nr,ts[j]["notready"]); peak_pend=max(peak_pend,ts[j]["pending"]); j+=1
        dur=ts[j-1]["t"]-ts[i]["t"] if j-1>i else 2.0
        episodes.append(dict(dur=round(dur,1),peak_nr=peak_nr,peak_pend=peak_pend))
        i=j
    else: i+=1
rec_times=[e["dur"] for e in episodes if e["peak_pend"]==0]  # phuc hoi hoan toan (khong Pending)
# recovery theo so node hong dong thoi
by_k={}
for e in episodes:
    by_k.setdefault(e["peak_nr"],[]).append(e["dur"])
# 4) pending
max_pend=max(p["pending"] for p in ts); pend_time=sum(1 for p in ts if p["pending"]>0)/len(ts)
# 5) chung chi dung? khi notready<=cert thi pending nen =0
ok=viol=0
for p in ts:
    if p["notready"]<=p["cert"]:
        if p["pending"]==0: ok+=1
        else: viol+=1
cert_acc=ok/(ok+viol) if (ok+viol) else 1.0

print("=== CHAOS 3h — TOM TAT ===")
print(f"Thoi luong: {DUR}s (~{DUR/3600:.1f}h) | {len(ts)} diem do | {len(kills)} lan kill")
print(f"Availability: trung binh {mean_av:.1f}/{desired} | min {min_av} | thoi gian day-du {100*len(full)/len(ts):.1f}%")
print(f"Node NotReady dong thoi: max {max_nr} | phan bo {dict(sorted(nr_dist.items()))}")
print(f"So doan gian doan (avail<{desired}): {len(episodes)}")
if rec_times:
    print(f"Thoi gian phuc hoi (phuc hoi hoan toan, n={len(rec_times)}): trung binh {st.mean(rec_times):.1f}s, trung vi {st.median(rec_times):.1f}s, max {max(rec_times):.1f}s")
print("Recovery theo so node hong dong thoi (peak_nr -> mean dur s):")
for k in sorted(by_k): print(f"   {k} node: n={len(by_k[k])}, mean={st.mean(by_k[k]):.1f}s, max={max(by_k[k]):.1f}s")
print(f"Pending: max {max_pend} | thoi gian co Pending {100*pend_time:.1f}%")
print(f"Do chinh xac chung chi (notready<=cert => khong Pending): {100*cert_acc:.1f}% ({ok} dung / {viol} vi pham)")
json.dump(dict(duration=DUR,points=len(ts),kills=len(kills),mean_avail=round(mean_av,2),min_avail=min_av,
    full_pct=round(100*len(full)/len(ts),1),max_notready=max_nr,nr_dist=nr_dist,episodes=len(episodes),
    recovery_mean=round(st.mean(rec_times),1) if rec_times else None,recovery_median=round(st.median(rec_times),1) if rec_times else None,
    by_k={str(k):[round(st.mean(v),1),len(v)] for k,v in by_k.items()},max_pending=max_pend,
    pending_time_pct=round(100*pend_time,1),cert_accuracy_pct=round(100*cert_acc,1)),
    open(os.path.join(D,"results_chaos_summary.json"),"w"),ensure_ascii=False,indent=1)
