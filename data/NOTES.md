# Data notes

One line per file: what the measurement is and the paper location it backs. JSON unless noted.

## simulation/  (single-machine simulation; Sections IV-A, IV-E, and Supplement)

- `results.json` — main simulation: success rate kappa(t) under uniform and clustered failures, mean min-cut C(F,S) vs number of spares (random placement), fatal-failure reduction, locality, runtime.
- `results_crob.json` — brute-force robust certificate C_rob vs spares on the 6x6 grid, nested and non-nested placements, with mean/min/max C(F,S) at probe level t.
- `results_sim_checks.json` — shadow-guarantee check (f_out >= f_0) and capacitated-model checks (grid, bridge).
- `results_baselines.json` — coverage vs baselines: discrete-naive, centralized greedy, optimal.
- `results_scale_sweep.json` — scalability: rounds-to-convergence vs graph size and diameter.
- `results_scale_feasible.json` — gap-to-optimum in the feasible region vs size (field, GNN, oracle).
- `results_ai.json` — learned-conductance lever: fraction of the gap-to-optimum closed by the GNN head.
- `results_oracle.json` — oracle configuration (optimal-route edges amplified): upper bound on conductance tuning.
- `results_learned.json` — learned GNN policy: edge-classifier AUC and routing improvement.
- `results_softroute.json` — soft-boundary (penalty) routing vs the hard Dirichlet solution.
- `results_proactive.json` — RUL-based proactive migration vs the reactive alternative, over prediction noise sigma.
- `results_generalize.json` — generalization of the learned policy across graph families.
- `results_gnn_rgg_n150.json`, `results_gnn_rgg_n200.json` — GNN policy on random geometric graphs at n = 150 and 200.
- `results_rl_n64.json`, `results_rl_n200.json` — REINFORCE router policy at n = 64 and 200.
- `rl_policy_n200.pt` — trained REINFORCE router weights (PyTorch state dict, n = 200); binary.
- `results_energy.json` — energy-aware conductance vs uniform: kappa and route/spare energy.
- `results_energy_pairs.json` — paired energy runs (demand/energy, uniform vs energy-aware).

## fabric/  (decentralized container fabric under a real control-plane partition; Section IV-C, Table II, Fig. 3)

- `results_fabric.json` — role coverage by number of dead edge nodes k for baseline, peer-heuristic, and CertiHeal; double-booking counts; coordinator-kill recovery times; certificate false-safe.

## k3s/  (16-node k3d/K3s testbed over two WAN machines; Section IV-D)

- `results_chaos_A_211.json` .. `results_chaos_A_215.json` — five independent 3-hour chaos schedules (about 180 node kills each), one per seed; per-episode within-certificate false-safe (basis of the mean and bootstrap interval).
- `results_chaos_summary.json` — aggregate of the detailed single chaos run: availability, recovery times, distribution by k.
- `results_res_sweep.json` — heterogeneous-workload admission sweep, cordon L = 6..12: three decision rules (slot certificate, CPU-sum, reservation-pod) against the ground-truth hang.
- `results_res_sweep_summary.json` — confusion-matrix summary of the admission sweep (per-rule false-safe rate).
- `results_reservation_summary.json` — reservation-arm confusion summary at the hang sample threshold.
- `results_res_pods.json` — pre-placement reservation-pod probe (placeholder pods with real requests) on the full 16 nodes.
- `results_cert_boundary.json` — certificate-boundary experiment across cordon levels.
- `results_ablation.json` — layer ablation (k8s / fence / reassign / full) with overall confusion and false-safe rate.
- `results_fence.json` — lease-fencing: concurrent-execution window, baseline vs fenced.
- `results_chaos_fence.json` — chaos run with fencing on: availability, fence events, recovery events.
- `results_comm_16node.json` — centralized control cost: cluster state-read bytes (nodes, pods, total KB).
- `results_compare_16node.json` — recovery comparison on 16 nodes: fabric, k8s-default, k8s-tuned, CertiHeal.
- `results_energy.json` — measured per-node energy over runs on the testbed.
- `results_toctou.json` — competing-workload TOCTOU experiment for the operational admission certificate: per competitor size C, the real roles hung by the non-atomic probe (release-then-commit) versus competitors that breach a held reservation (should be 0). Produced by `code/k3s/k3s_toctou.py`.
