------------------------------ MODULE MCReservation ------------------------------
(* Concrete finite instance for TLC.  Two roles share unit u1 (capacity 1), *)
(* which forces the no-double-booking conflict; role r2 also needs u2, which *)
(* exercises COMMIT-ALL / path atomicity across two units.                   *)
EXTENDS CertiHealReservation

MCRoles  == {"r1","r2"}
MCUnits  == {"u1","u2"}
MCPath   == [r \in MCRoles |-> IF r = "r1" THEN {"u1"} ELSE {"u1","u2"}]
MCCap    == [u \in MCUnits |-> 1]
MCDemand == [r \in MCRoles |-> 1]
==================================================================================
