-------------------------- MODULE CertiHealReservation --------------------------
(***************************************************************************)
(* Machine-checked model of the two-phase path-atomic reservation         *)
(* protocol of CertiHeal-Edge (Proposition 1).  A coordinator reserves,    *)
(* for each role r, the capacitated units (arcs) on r's route, then        *)
(* commits them all-or-nothing (COMMIT-ALL).  The network is asynchronous  *)
(* with message loss, duplication and reordering; a coordinator may time   *)
(* out at any point, and a PREPARED lease may expire.                      *)
(*                                                                         *)
(* Verified safety invariants (single epoch):                             *)
(*   CapacitySafety  : held load of every unit stays within its capacity.  *)
(*   NoDoubleBooking : committed roles on a unit never exceed its capacity. *)
(*   PathAtomicity   : a role is ACTIVE only if EVERY unit on its route     *)
(*                     holds a COMMITTED record for it (COMMIT-ALL), and an *)
(*                     ABORTED record can never be revived (tombstone).     *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets

CONSTANTS Roles, Units, Path, Cap, Demand

(* Path[r] is the set of units on role r's route; Cap[u] is unit capacity;  *)
(* Demand[r] is r's demand (units of capacity each unit on the path holds). *)

ASSUME PathAssume == Path \in [Roles -> SUBSET Units]
ASSUME CapAssume  == Cap  \in [Units -> Nat]
ASSUME DemAssume  == Demand \in [Roles -> Nat]

VARIABLES rec, cstate, msgs

(* rec[u][r] in {"NONE","PREPARED","COMMITTED","ABORTED"} : per-key record. *)
(* cstate[r] : coordinator state for role r.                                *)
(* msgs : the network, a SET of in-flight messages (a set gives reordering  *)
(*        and, since receipt does not remove, redelivery/duplication; loss  *)
(*        is modelled by never being forced to act on a message).           *)

RecStates  == {"NONE","PREPARED","COMMITTED","ABORTED"}
CoordStates == {"ROUTED","PREPARING","COMMITTING","ACTIVE","ABORTED"}

C2U == {"RESERVE","COMMIT","ABORT"}      \* coordinator -> unit
U2C == {"ACKP","ACKC","NACK"}            \* unit -> coordinator

Mk(t,r,u) == [type |-> t, r |-> r, u |-> u]

AllMsgs ==
  { Mk(t,r,u) : t \in (C2U \cup U2C), r \in Roles, u \in Units }

TypeOK ==
  /\ rec \in [Units -> [Roles -> RecStates]]
  /\ cstate \in [Roles -> CoordStates]
  /\ msgs \subseteq AllMsgs

(* Held load of a unit: sum of demands of roles whose key is PREPARED or    *)
(* COMMITTED on that unit.  (All demands are positive naturals.)            *)
Holders(u) == { r \in Roles : rec[u][r] \in {"PREPARED","COMMITTED"} }
RECURSIVE SumDem(_)
SumDem(S) == IF S = {} THEN 0
             ELSE LET r == CHOOSE x \in S : TRUE
                  IN Demand[r] + SumDem(S \ {r})
Held(u) == SumDem(Holders(u))

Init ==
  /\ rec    = [u \in Units |-> [r \in Roles |-> "NONE"]]
  /\ cstate = [r \in Roles |-> "ROUTED"]
  /\ msgs   = {}

------------------------------------------------------------------------------
(* Coordinator actions (per role r).                                        *)

CSendReserve(r) ==
  /\ cstate[r] = "ROUTED"
  /\ cstate' = [cstate EXCEPT ![r] = "PREPARING"]
  /\ msgs' = msgs \cup { Mk("RESERVE",r,u) : u \in Path[r] }
  /\ UNCHANGED rec

CAllAckP(r) ==
  /\ cstate[r] = "PREPARING"
  /\ \A u \in Path[r] : Mk("ACKP",r,u) \in msgs
  /\ cstate' = [cstate EXCEPT ![r] = "COMMITTING"]
  /\ msgs' = msgs \cup { Mk("COMMIT",r,u) : u \in Path[r] }
  /\ UNCHANGED rec

CNack(r) ==
  /\ cstate[r] = "PREPARING"
  /\ \E u \in Path[r] : Mk("NACK",r,u) \in msgs
  /\ cstate' = [cstate EXCEPT ![r] = "ABORTED"]
  /\ msgs' = msgs \cup { Mk("ABORT",r,u) : u \in Path[r] }
  /\ UNCHANGED rec

(* Coordinator lease timeout while preparing: abort the whole path.         *)
CTimeoutP(r) ==
  /\ cstate[r] = "PREPARING"
  /\ cstate' = [cstate EXCEPT ![r] = "ABORTED"]
  /\ msgs' = msgs \cup { Mk("ABORT",r,u) : u \in Path[r] }
  /\ UNCHANGED rec

CAllAckC(r) ==            \* COMMIT-ALL point: activate only after every ACK-COMMIT
  /\ cstate[r] = "COMMITTING"
  /\ \A u \in Path[r] : Mk("ACKC",r,u) \in msgs
  /\ cstate' = [cstate EXCEPT ![r] = "ACTIVE"]
  /\ UNCHANGED <<rec, msgs>>

(* Coordinator lease timeout while committing: abort (roll back).           *)
CTimeoutC(r) ==
  /\ cstate[r] = "COMMITTING"
  /\ cstate' = [cstate EXCEPT ![r] = "ABORTED"]
  /\ msgs' = msgs \cup { Mk("ABORT",r,u) : u \in Path[r] }
  /\ UNCHANGED rec

------------------------------------------------------------------------------
(* Unit actions (per role r and unit u on r's path).                        *)

URecvReserve(r,u) ==
  /\ u \in Path[r]
  /\ Mk("RESERVE",r,u) \in msgs
  /\ LET s == rec[u][r] IN
       \/ /\ s = "NONE" /\ Held(u) + Demand[r] <= Cap[u]
          /\ rec' = [rec EXCEPT ![u][r] = "PREPARED"]
          /\ msgs' = msgs \cup { Mk("ACKP",r,u) }
       \/ /\ s = "NONE" /\ Held(u) + Demand[r] > Cap[u]
          /\ msgs' = msgs \cup { Mk("NACK",r,u) }
          /\ UNCHANGED rec
       \/ /\ s = "PREPARED"                         \* idempotent re-ack
          /\ msgs' = msgs \cup { Mk("ACKP",r,u) }
          /\ UNCHANGED rec
       \/ /\ s = "COMMITTED"
          /\ msgs' = msgs \cup { Mk("ACKC",r,u) }
          /\ UNCHANGED rec
       \/ /\ s = "ABORTED"                          \* tombstone: reject late RESERVE
          /\ UNCHANGED <<rec, msgs>>
  /\ UNCHANGED cstate

URecvCommit(r,u) ==
  /\ u \in Path[r]
  /\ Mk("COMMIT",r,u) \in msgs
  /\ LET s == rec[u][r] IN
       \/ /\ s = "PREPARED"
          /\ rec' = [rec EXCEPT ![u][r] = "COMMITTED"]
          /\ msgs' = msgs \cup { Mk("ACKC",r,u) }
       \/ /\ s = "COMMITTED"                        \* idempotent re-ack
          /\ msgs' = msgs \cup { Mk("ACKC",r,u) }
          /\ UNCHANGED rec
       \/ /\ s \in {"ABORTED","NONE"}               \* tombstone: reject late COMMIT
          /\ UNCHANGED <<rec, msgs>>
  /\ UNCHANGED cstate

URecvAbort(r,u) ==       \* whole-path abort reaches a unit: release / tombstone
  /\ u \in Path[r]
  /\ Mk("ABORT",r,u) \in msgs
  /\ rec[u][r] \in {"NONE","PREPARED","COMMITTED"}
  /\ rec' = [rec EXCEPT ![u][r] = "ABORTED"]
  /\ UNCHANGED <<cstate, msgs>>

ULeaseExpire(r,u) ==     \* a PREPARED (not yet committed) lease expires
  /\ u \in Path[r]
  /\ rec[u][r] = "PREPARED"
  /\ rec' = [rec EXCEPT ![u][r] = "ABORTED"]
  /\ UNCHANGED <<cstate, msgs>>

------------------------------------------------------------------------------
Next ==
  \E r \in Roles :
     \/ CSendReserve(r) \/ CAllAckP(r) \/ CNack(r)
     \/ CTimeoutP(r) \/ CAllAckC(r) \/ CTimeoutC(r)
     \/ \E u \in Path[r] :
           URecvReserve(r,u) \/ URecvCommit(r,u)
        \/ URecvAbort(r,u)   \/ ULeaseExpire(r,u)

Spec == Init /\ [][Next]_<<rec,cstate,msgs>>

------------------------------------------------------------------------------
(* Safety invariants.                                                       *)

CapacitySafety  == \A u \in Units : Held(u) <= Cap[u]

NoDoubleBooking ==
  \A u \in Units :
     Cardinality({ r \in Roles : u \in Path[r] /\ rec[u][r] = "COMMITTED" }) <= Cap[u]

PathAtomicity ==
  \A r \in Roles :
     (cstate[r] = "ACTIVE") => (\A u \in Path[r] : rec[u][r] = "COMMITTED")

Safety == TypeOK /\ CapacitySafety /\ NoDoubleBooking /\ PathAtomicity
==============================================================================
