# Supplementary experiments

Two optional mechanisms outside the core certificate guarantee: a local learning head that tunes the field conductances, and remaining-useful-life (RUL) proactive migration. Hyperparameters are in `../config/hyperparameters.md` (supplementary table). Figures are in `../figures/`.

## Local learning policy (method)

An optional shallow GNN with K = 2 to 3 message-passing steps is trained offline on features of each edge and its two endpoints; its message passing coincides with the field relaxation steps (unrolled optimization). Inference runs on a CPU per node; training uses a GPU only.

Data: `../data/simulation/results_learned.json`, `results_ai.json`, `results_oracle.json`, `results_gnn_rgg_n150.json`, `results_gnn_rgg_n200.json`, `results_generalize.json`; trained weights `rl_policy_n200.pt`; RL router runs `results_rl_n64.json`, `results_rl_n200.json`.

## Proactive migration via RUL prediction (Fig. S1 = `figures/fig5_proactive.png`)

RUL and anomaly scores at a node enter the field source term, moving a role off an at-risk node before it stops. RUL is modeled as the true value plus Gaussian noise of standard deviation sigma (an oracle sensitivity analysis over prediction quality). Measured: for sigma <= 1.0 the mechanism keeps 100% of roles (250 of 250), 99.9% at sigma = 1.5; the reactive alternative keeps about 84%; the two break even at sigma ~ 2.4.

Data: `../data/simulation/results_proactive.json`.

## Local learning policy (improvement and limits) (Fig. S2 = `figures/fig7_scale_feasible.png`)

The edge classifier reaches AUC 0.94 to 0.95 and saturates at K = 2 to 3. The routing policy improves little: learned conductance closes 15 to 34% of the gap to optimum, typically 15 to 20% in the feasible region, and this does not grow with size. An oracle configuration (optimal-route edges amplified) closes 33 to 100%, bounding what conductance tuning alone can achieve. Learning the router directly with REINFORCE performed worse than the plain field. The limiting factor is locality: the field already carries a near-optimal follow-the-current bias at the neighborhood level, leaving little residual signal for a K-hop policy.

Data: `../data/simulation/results_scale_feasible.json`, `results_softroute.json`.
