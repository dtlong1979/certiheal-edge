# Machine-checked reservation protocol

TLA+ specification and TLC model-check of the two-phase path-atomic reservation protocol (Proposition 1): a coordinator reserves the capacitated units on each role's route and commits them all-or-nothing, over an asynchronous network with message loss, duplication, and reordering, with coordinator timeout and PREPARED-lease expiry.

| File | Contents |
|---|---|
| `CertiHealReservation.tla` | The protocol and the safety invariants. |
| `MCReservation.tla` / `.cfg` | Finite instance for TLC (two roles sharing a capacity-1 unit; one role spanning two units). |
| `tlc_output.txt` | TLC run log. |

Invariants checked: `CapacitySafety` (held load stays within capacity), `NoDoubleBooking` (committed roles on a unit stay within capacity), `PathAtomicity` (a role is ACTIVE only if every unit on its route holds a COMMITTED record, and an ABORTED record is never revived).

Result: all invariants hold across all reachable states (1346 distinct states, depth 17). Removing the prepare-time capacity guard reproduces a `CapacitySafety` violation, confirming the check is effective.

Run: `java -cp tla2tools.jar tlc2.TLC -config MCReservation.cfg MCReservation` (TLA+ tools, Java 11+).
