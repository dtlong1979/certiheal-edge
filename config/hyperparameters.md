# Configuration tables

Machine-readable configuration is in `roles.yaml`, `roles_hetero.yaml`, and `fabric_cfg.json` in this folder; the tables below list the numeric settings.

## Main experiments

| Component | Hyperparameter | Value |
|---|---|---|
| Laplace field (Jacobi) | convergence tolerance / max rounds; edge conductance | 1e-3 / 5000; c0: live edge = 1, dead edge = 0 |
| Min-cut certificate | grid size / number of spares | 6x6 / 4 to 16 |
| Fabric partition | nodes (co-located + edge) / roles / capacity b / seeds | 15 (3 + 12) / 42 / 4 / 5 |
| K3s prototype | nodes on two WAN machines / roles / per-node cap; detection | 16 / 64 / 6; grace-period ~40 s |
| K3s admission sweep | pods (small 3 CPU + big 9 CPU) / node CPU (A + B) / cordon L / episodes | 45 (30 + 15), 225 CPU / 3 at 20 + 13 at 32 / L = 6 to 12 / 18 |

## Supplementary experiments

| Component | Hyperparameter | Value |
|---|---|---|
| Proactive migration (RUL) | grid / spares / cluster size / threshold tau / noise sigma / runs | 8x8 / 10 / 6 / 2.0 / {0 to 3} / 250 |
| GNN (learned policy) | input-hidden / K / optimizer, lr / epochs / train-test graphs | 3-32 / K in {1 to 4}, saturating 2 to 3 / Adam, 3e-3 / 25-40 / 600-120 (RGG, n = 400) |
| RL router (REINFORCE) | hidden / K steps / lr / episodes | 48 / K / 2e-3 / 3000 |
