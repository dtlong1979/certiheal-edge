# -*- coding: utf-8 -*-
"""Fig. 4 (English): K3s WAN chaos. (a) availability over one representative schedule;
(b) within-certificate false-safe rate for the five schedules with mean and 95% CI."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "certiheal_poc", "fig_chaos_en.png")

REP = 213                      # representative schedule (peak unplaceable ~31)
FALSE_SAFE = {211: 30.9, 212: 26.0, 213: 26.5, 214: 14.7, 215: 17.2}
MEAN, CI_LO, CI_HI = 23.0, 15.0, 31.0

d = json.load(open(os.path.join(HERE, f"results_chaos_A_{REP}.json")))
ts = d["timeseries"]
des = ts[0]["desired"]
t = [p["t"] / 3600.0 for p in ts]
avail = [100.0 * p["avail"] / des for p in ts]
pending = [p.get("pending", 0) for p in ts]

fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 3.0))

# (a) availability over time, with unplaceable roles on a twin axis
a.plot(t, avail, color="#1f77b4", lw=0.8)
a.axhline(100, color="#2ca02c", lw=0.8, ls=":")
a.set_xlabel("Time (hours)")
a.set_ylabel("Role availability (%)", color="#1f77b4")
a.set_ylim(60, 102)
a.set_xlim(0, 3)
a.tick_params(axis="y", labelcolor="#1f77b4")
a.set_title("(a) Availability under 3-hour chaos")
a2 = a.twinx()
a2.fill_between(t, pending, color="#d62728", alpha=0.30, step=None, lw=0)
a2.set_ylabel("Unplaceable roles", color="#d62728")
a2.set_ylim(0, 40)
a2.tick_params(axis="y", labelcolor="#d62728")

# (b) per-schedule false-safe rate with mean and 95% CI band
seeds = sorted(FALSE_SAFE)
vals = [FALSE_SAFE[s] for s in seeds]
x = range(len(seeds))
b.bar(x, vals, color="#9467bd", width=0.62)
b.axhspan(CI_LO, CI_HI, color="#bbbbbb", alpha=0.35, lw=0)
b.axhline(MEAN, color="black", ls="--", lw=1.0)
b.set_xticks(list(x))
b.set_xticklabels([f"S{i+1}" for i in x])
b.set_xlabel("Schedule")
b.set_ylabel("Within-certificate\nfalse-safe rate (%)")
b.set_ylim(0, 38)
b.set_title("(b) False-safe rate (5 schedules)")
b.text(len(seeds) - 0.5, MEAN + 0.6, "mean 23%", ha="right", va="bottom", fontsize=8)
b.text(len(seeds) - 0.5, CI_HI - 0.4, "95% CI [15, 31]", ha="right", va="top", fontsize=8, color="#555555")

fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print("wrote", os.path.normpath(OUT))
print("rep schedule", REP, "full%", round(100*sum(1 for p in ts if p['avail']==des)/len(ts),1),
      "max pending", max(pending))
