# CertiHeal-Edge — artifact

Proofs, configuration, code, and measured data for the CertiHeal-Edge paper.

| Resource | Contents |
|---|---|
| `PROOFS.md` | Full proofs of the theorems and lemmas. |
| `supplement/` | Descriptions of the supplementary experiments (learning head, RUL migration). |
| `config/` | Hyperparameter tables (`hyperparameters.md`) and workload/fabric configuration (`roles.yaml`, `roles_hetero.yaml`, `fabric_cfg.json`). |
| `code/` | Scripts that produced the data: `simulation/`, `fabric/`, `k3s/`. |
| `data/` | Measured results, grouped by platform; every file is described in `data/NOTES.md`. |
| `figures/` | Figures generated from the data. |

Environment: Python 3.11 (NumPy, NetworkX, PyTorch); the fabric and K3s scripts additionally require a Docker and a Kubernetes host.
