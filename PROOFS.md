# CertiHeal-Edge: Proofs

This document states and proves Theorem 1, Proposition 1, Theorem 2, Lemma 1, and Lemma 2. All
notation is defined in Section 0. Standard results are cited without proof.

Contents

- 0. Setting and notation
- 1. Theorem 1 (certificate: exact value, Menger reduction, monotonicity, weak duality)
- 2. Proposition 1 (reservation safety of the two-phase COMMIT-ALL protocol; $f_{\mathrm{field}}\le C(F,S)$)
- 3. Theorem 2 (fallback branch: Dirichlet solution, greedy witness, per-scenario guarantee)
- 4. Lemma 1 (synchronous field convergence)
- 5. Lemma 2 (partially asynchronous field convergence)

---

## 0. Setting and notation

### 0.1 Service graph, failures, spares, demand

Let $G=(V,E)$ be a finite undirected graph. Let $F\subseteq V$ be the failed-node set and
$S\subseteq V\setminus F$ the spare set. Define

$$

G_F=G[V\setminus F].

$$

For $v\in V$, let $N(v)$ denote its neighbor set in $G$.

For $v\in F$, let $d_v\in\mathbb{Z}_{\ge 0}$ be the orphaned demand at $v$, and set

$$

d(F)=\sum_{v\in F} d_v.

$$

Let $R(F)$ be the set of orphaned roles. Each $r\in R(F)$ has origin $v(r)\in F$ and demand
$q_r\in\mathbb{Z}_{\ge 1}$, with

$$

d_v=\sum_{r:\,v(r)=v} q_r.

$$

Theorem 1 uses unit roles, $q_r=1$. Proposition 1 permits arbitrary $q_r$.

Each live node $v\in V\setminus F$ has capacity $b_v\in\mathbb{Z}_{\ge 0}$. For $s\in S$, $b_s$ is
the residual spare capacity. Each live edge $\{v,w\}\in E(G_F)$ has capacity

$$

b_{vw}=b_{wv}\in\mathbb{Z}_{\ge 0}\cup\{+\infty\}.

$$

Define

$$

B_v=N(v)\setminus F,
\qquad
B_F=\left(\bigcup_{v\in F}B_v\right)\setminus S.

$$

Then

$$

B_F\cap S=\varnothing,
\qquad
\partial=B_F\cup S,
\qquad
I=(V\setminus F)\setminus\partial.

$$

### 0.2 The capacity graph $G_F^{\mathrm{cap}}$ (node-split construction)

$G_F^{\mathrm{cap}}$ is the directed capacitated graph with the following vertices and arcs.

- Vertices: a super-source $\sigma_F$; one per-node source $\sigma_v$ for each $v\in F$; for each live node $v\in V\setminus F$ an in-out pair $(v_{\mathrm{in}},v_{\mathrm{out}})$; and a super-sink $\tau$.
- Source arcs: $(\sigma_F,\sigma_v)$ with capacity $d_v$ for each $v\in F$; and $(\sigma_v,w_{\mathrm{in}})$ with capacity $+\infty$ for each $v\in F$ and each $w\in B_v=N(v)\setminus F$. There are no other arcs leaving $\sigma_F$ or any $\sigma_v$, and no arcs enter them.
- Node arcs: $(v_{\mathrm{in}},v_{\mathrm{out}})$ with capacity $b_v$ for each live $v$.
- Link arcs: $(v_{\mathrm{out}},w_{\mathrm{in}})$ and $(w_{\mathrm{out}},v_{\mathrm{in}})$, each with capacity $b_{vw}$, for each live link $\{v,w\}\in E(G_F)$.
- Sink arcs: $(s_{\mathrm{out}},\tau)$ with capacity $+\infty$ for each spare $s\in S$.

All finite capacities are integers. Write $c(a)$ for the capacity of arc $a$.

A flow is a function $x$ on arcs with $0\le x(a)\le c(a)$ and flow conservation at every vertex
other than $\sigma_F$ and $\tau$. Its value $|x|$ is the net flow out of $\sigma_F$. A
$\sigma_F$-$\tau$ cut is a vertex set $X$ with $\sigma_F\in X$, $\tau\notin X$; its capacity is
$c(X)=\sum_{a=(p,q):\,p\in X,\,q\notin X}c(a)$. Because the sink arcs are uncapacitated, every
finite-capacity cut $X$ contains no $s_{\mathrm{out}}$, $s\in S$; such a cut separates $\sigma_F$
from every spare and is called a capacitated $\sigma_F$-$S$ cut. The certificate is

$$

C(F,S)=\max\{|x| : x \text{ a flow in } G_F^{\mathrm{cap}}\}.

$$

A recovery configuration is a set $R'\subseteq R(F)$ of unit roles together with, for each $r\in R'$, a simple path $\pi_r$ in $G_F$ from a node of $B_{v(r)}$ to a spare, such that for every live
node $v$ the number of paths using $v$ (as an interior vertex or as an endpoint) is at most $b_v$,
and for every live link $\{v,w\}$ the number of paths traversing it is at most $b_{vw}$. Its size is
$|R'|$, the number of role units served at once.

### 0.3 The field graph $G_F^{\mathrm{field}}$ and the Jacobi iteration

$G_F^{\mathrm{field}}$ is the undirected graph $G_F$ with a symmetric conductance
$c_{vw}=c_{wv}\in[c_{\min},c_{\max}]$, $0<c_{\min}\le c_{\max}<\infty$, on every live link. The
weighted degree of a live node is $d_v^c=\sum_{w\in N_F(v)}c_{vw}$ where $N_F(v)$ is the neighbor
set in $G_F$. $A_c$ is the weighted adjacency matrix, $D_c=\operatorname{diag}(d_v^c)$, and $L_c=D_c-A_c$
is the weighted Laplacian.

The Dirichlet data are

$$

g_v=
\begin{cases}
1, & v\in B_F,\\
0, & v\in S.
\end{cases}

$$

With the ordering $(I,\partial)$,

$$

u_\partial=g,
\qquad
(L_cu)_I=0,

$$

or equivalently

$$

L_{II}u_I=-L_{I\partial}g. \tag{0.1}

$$

For the CERTIFIED branch, $c=c^0$ and $\lambda=0$. For $v\in I$,

$$

\begin{aligned}
u_v^{k+1}
&=\frac{1}{d_v^c}\sum_{w\in N_F(v)}c_{vw}u_w^k,\\
u_w^k&=g_w,\qquad w\in\partial.
\end{aligned}
\tag{0.2}

$$

Equivalently,

$$

u_I^{k+1}=Ju_I^k+h,

$$

where

$$

J=(D_c^{-1}A_c)_{II},
\qquad
h=(D_c^{-1}A_c)_{I\partial}g.

$$

Let $\rho=\rho(J)$.

For the HEURISTIC branch, let $M>0$, $\lambda\ge 0$, and

$$

p_v=\mathbf{1}_{\{v\in\partial\}}.

$$

Then

$$

u_v^{k+1}
=
\frac{
\displaystyle\sum_{w\in N_F(v)}c_{vw}u_w^k
+Mp_vg_v
+\lambda(1-p_v)\eta_v
}{d_v^c+Mp_v}. \tag{0.3}

$$

Moreover,

$$

J_M=(D_c+MP)^{-1}A_c,
\qquad
P=\operatorname{diag}(p_v).

$$

**Standing assumption.** Every connected component of $G_F^{\mathrm{field}}$ containing a vertex of $I$ intersects $\partial$. Components disjoint from $\partial$ are omitted.

### 0.4 Norms

For $w>0$, define

$$

\|x\|_w=\max_i\frac{|x_i|}{w_i},
\qquad
\|J\|_w=\max_i\frac{1}{w_i}\sum_jJ_{ij}w_j.

$$

For a positive diagonal matrix $D$, define

$$

\|x\|_D=(x^\top Dx)^{1/2}.

$$

---

## 1. Theorem 1 (certificate)

**Theorem 1 (certificate: exact value, Menger reduction, monotonicity, weak duality).** In $G_F^{\mathrm{cap}}$ with integer capacities:

(a) The maximum size of a recovery configuration equals the maximum flow value $C(F,S)$, and a
maximum flow can be taken integral.

(b) $C(F,S)$ equals the minimum capacity of a $\sigma_F$-$\tau$ cut, which is the minimum capacity
of a capacitated $\sigma_F$-$S$ cut.

(c) (Menger reduction.) If $d_v=1$ for all $v\in F$, $b_v=1$ for all live $v$, and links are
uncapacitated, then $C(F,S)$ is the maximum number of pairwise vertex-disjoint paths in $G_F$ that
start at distinct sets $B_v$ (one path per failed node, starting in its own $B_v$) and end in $S$,
and equals the minimum number of live vertices whose removal, together with the loss of their source
arcs, separates every $\sigma_v$ from $S$ in $G_F^{\mathrm{cap}}$.

(d) (Monotonicity.) If $S\subseteq S'$ and the capacities of arcs common to $G_F^{\mathrm{cap}}(S)$
and $G_F^{\mathrm{cap}}(S')$ are not decreased, then $C(F,S)\le C(F,S')$.

(e) (Weak duality.) Every feasible flow $x$ in $G_F^{\mathrm{cap}}$ satisfies $|x|\le C(F,S)$; in
particular any flow committed by the local rounds is a lower bound on $C(F,S)$.

**Proof.**

*Step 1. Recovery configuration to integral flow.* For $r\in R'$, write

$$

\pi_r=(w_0,w_1,\ldots,w_m),
\qquad
w_0\in B_{v(r)},
\quad
w_m\in S,

$$

and define its lift

$$

\widehat\pi_r=
(\sigma_F,\sigma_{v(r)},w_{0,\mathrm{in}},w_{0,\mathrm{out}},\ldots,
w_{m,\mathrm{in}},w_{m,\mathrm{out}},\tau).

$$

Set

$$

x=\sum_{r\in R'}\mathbf{1}_{\widehat\pi_r}.

$$

Then $x$ is integral and satisfies flow conservation. Moreover,

$$

\begin{aligned}
x(\sigma_F,\sigma_v)
&=|\{r\in R':v(r)=v\}|\le d_v,\\
x(v_{\mathrm{in}},v_{\mathrm{out}})
&\le b_v,\\
x(v_{\mathrm{out}},w_{\mathrm{in}})
&\le b_{vw}.
\end{aligned}

$$

Thus $x$ is feasible and $|x|=|R'|$. Hence

$$

C(F,S)\ge \max\{|R'|:R'\text{ is a recovery configuration}\}.

$$

*Step 2. Integral flow to recovery configuration.* Let $x$ be an integral feasible flow. If both link arcs associated with a live edge $\{v,w\}$ carry positive flow, cancel the maximal common integer amount on the directed cycle

$$

v_{\mathrm{out}}\to w_{\mathrm{in}}\to w_{\mathrm{out}}
\to v_{\mathrm{in}}\to v_{\mathrm{out}}.

$$

Cycle cancellation preserves feasibility and $|x|$. Repeating this operation yields a flow with at most one positive direction on each live edge.

Apply integral flow decomposition and discard directed cycles. The resulting flow is a sum of $|x|$ unit $\sigma_F$--$\tau$ paths. Each such path has the form

$$

\sigma_F\to\sigma_v\to w_{0,\mathrm{in}}\to w_{0,\mathrm{out}}
\to\cdots\to w_{m,\mathrm{out}}\to\tau,

$$

with $w_0\in B_v$ and $w_m\in S$. Its projection to $G_F$ is a simple path from $B_v$ to $S$.

The source, node, and link capacities give, respectively,

$$

\#\{\text{paths assigned to }v\}\le d_v,
\qquad
\#\{\text{paths using }v\}\le b_v,
\qquad
\#\{\text{paths using }\{v,w\}\}\le b_{vw}.

$$

Hence these projected paths form a recovery configuration of size $|x|$. Therefore

$$

C(F,S)\le \max\{|R'|:R'\text{ is a recovery configuration}\}

$$

for every integral maximum flow.

*Step 3. Part (a).* Since every flow has value at most

$$

d(F)=\sum_{v\in F}d_v,

$$

each infinite capacity may be replaced by $d(F)$ without changing the maximum value. The resulting network has integer capacities. By the integrality theorem for maximum flows, it admits an integral maximum flow. Steps 1--2 prove (a).

*Step 4. Part (b).* The max-flow min-cut theorem gives

$$

C(F,S)=\min_X c(X),

$$

where $X$ ranges over $\sigma_F$--$\tau$ cuts. A minimum cut is finite. Hence it contains no $s_{\mathrm{out}}$, $s\in S$, because $(s_{\mathrm{out}},\tau)$ has infinite capacity. Thus the finite $\sigma_F$--$\tau$ cuts are exactly the capacitated $\sigma_F$--$S$ cuts relevant to the minimum.

For every feasible flow $x$ and every such cut $X$,

$$

\begin{aligned}
|x|
&=\sum_{a\in\delta^+(X)}x(a)-\sum_{a\in\delta^-(X)}x(a)\\
&\le \sum_{a\in\delta^+(X)}c(a)\\
&=c(X).
\end{aligned}
\tag{1.1}

$$

For a maximum flow, let $X$ be the vertices reachable from $\sigma_F$ in the residual graph. Then every arc in $\delta^+(X)$ is saturated and every arc in $\delta^-(X)$ carries zero flow. Equality holds in (1.1), proving (b).

*Step 5. Part (c).* Under $d_v=b_v=1$ and infinite link capacities, the decomposition in Step 2 gives pairwise vertex-disjoint paths, with at most one path associated with each failed node. Conversely, every such path family defines a feasible unit flow by Step 1.

For a finite cut $X$, only source arcs and node arcs can leave $X$. Define

$$

F_0=\{v\in F:\sigma_v\notin X\},
\qquad
U=\{v\in V\setminus F:v_{\mathrm{in}}\in X,
\ v_{\mathrm{out}}\notin X\}.

$$

Then

$$

c(X)=|F_0|+|U|.

$$

Closure of $X$ under infinite-capacity arcs implies that $G_F-U$ contains no path from $B_v$ to $S$ for $v\in F\setminus F_0$. Hence $(F_0,U)$ is a separator.

Conversely, for such a separator $(F_0,U)$, let $W$ be the set of vertices reachable in $G_F-U$ from

$$

\bigcup_{v\in F\setminus F_0}B_v.

$$

Then $W\cap S=\varnothing$. Taking $X$ to contain $\sigma_F$, the vertices $\sigma_v$ for $v\notin F_0$, the split copies of $W$, and the necessary $u_{\mathrm{in}}$ for $u\in U$, gives

$$

c(X)\le |F_0|+|U|.

$$

Thus the minimum cut equals the minimum separator size. This is the vertex form of Menger's theorem under node splitting.

*Step 6. Part (d).* If $S\subseteq S'$, every arc of $G_F^{\mathrm{cap}}(S)$ is present in $G_F^{\mathrm{cap}}(S')$, and no common capacity decreases. Hence every feasible flow for $S$ is feasible for $S'$ with the same value. Therefore

$$

C(F,S)\le C(F,S').

$$

*Step 7. Part (e).* From (1.1), for every feasible flow $x$ and every minimum cut $X^*$,

$$

|x|\le c(X^*)=C(F,S).

$$

In particular, Proposition 1 gives

$$

f_{\mathrm{field}}\le C(F,S).

$$

$\blacksquare$

*Remark 1.1 (indivisible multi-unit roles).* If $q_r>1$ must be routed unsplittably on one path, every feasible unsplittable routing induces a feasible flow. Hence its served demand is at most $C(F,S)$.

---

## 2. Proposition 1 (reservation safety and the witness bound)

### 2.1 Protocol model

A resource unit is any capacitated arc of $G_F^{\mathrm{cap}}$: the source arc
$(\sigma_F,\sigma_v)$ (capacity $d_v$), a node arc $(v_{\mathrm{in}},v_{\mathrm{out}})$ (capacity
$b_v$; for a spare this is its slot capacity), or a link arc (capacity $b_{vw}$). Write $\mathcal U$
for the set of units and $\operatorname{cap}(u)$ for the capacity of unit $u$. Uncapacitated arcs are not
units.

An episode has an identifier $e$; identifiers are strictly increasing across epochs and never
reused. Within episode $e$, a coordinator computes for each role $r\in R(F)$ a candidate route: a
simple path $\pi_r$ in $G_F$ from a node of $B_{v(r)}$ to a spare (Phase B), or the direct route
$\sigma_{v(r)}\to s$ for an adjacent spare $s$ (Phase 0). The unit set of the route, $\mathcal U(r)\subseteq\mathcal U$, is the set of capacitated arcs of the lifted path $\widehat\pi_r$ of Section
1, Step 1: the source arc of $v(r)$, the node arcs of every vertex of $\pi_r$, and the link arcs of
every edge of $\pi_r$ in the direction of traversal.

Each unit $u$ keeps, for each key $(e,r,u)$ it has ever seen, a record with state in
$\{\mathrm{PREPARED},\mathrm{COMMITTED},\mathrm{ABORTED}\}$ and the demand $q_r$; a key with no
record is FREE. Define the held load

$$

\mathrm{held}_u=\sum\{q_r:\ (e,r,u) \text{ in state PREPARED or COMMITTED}\}.

$$

The coordinator keeps, for each role, a state in
$\{\mathrm{ROUTED},\mathrm{PREPARING},\mathrm{COMMITTING},\mathrm{ACTIVE},\mathrm{ABORTED}\}$.

Events are message deliveries or local timeouts. Each event is atomic. The transition rules are:

- (U1) On $\mathrm{RESERVE}(e,r,u)$: if a record for $(e,r,u)$ exists, do nothing except re-send the acknowledgement matching its state (idempotence). Otherwise, if $\mathrm{held}_u+q_r\le\operatorname{cap}(u)$, create the record in state PREPARED and send $\mathrm{ACK\text{-}PREPARE}(e,r,u)$; else send $\mathrm{NACK}(e,r,u)$ and create no record.
- (U2) On $\mathrm{COMMIT}(e,r,u)$: if the record is PREPARED, move it to COMMITTED and send $\mathrm{ACK\text{-}COMMIT}(e,r,u)$; if COMMITTED, re-send the acknowledgement; if ABORTED or absent, ignore.
- (U3) On $\mathrm{ABORT}(e,r,u)$, or on expiry of the lease of a PREPARED record: if the record is PREPARED or COMMITTED, move it to ABORTED; if absent, create it in state ABORTED; if ABORTED, do nothing. Records in state ABORTED contribute nothing to $\mathrm{held}_u$ and reject every later RESERVE or COMMIT under the same key.
- (C1) Coordinator, role $r$ in ROUTED: send $\mathrm{RESERVE}(e,r,u)$ to all $u\in\mathcal U(r)$; go to PREPARING.
- (C2) Coordinator, role $r$ in PREPARING: on receipt of ACK-PREPARE from every $u\in\mathcal U(r)$, send $\mathrm{COMMIT}(e,r,u)$ to all $u\in\mathcal U(r)$ and go to COMMITTING. On any NACK, or on the coordinator's own lease timeout, send $\mathrm{ABORT}(e,r,u)$ to all $u\in\mathcal U(r)$ and go to ABORTED.
- (C3) Coordinator, role $r$ in COMMITTING: on receipt of ACK-COMMIT from every $u\in\mathcal U(r)$, activate $r$ and go to ACTIVE (this is the COMMIT-ALL point). On lease timeout before that, send ABORT to all $u\in\mathcal U(r)$ and go to ABORTED.
- (C4) A role in ACTIVE or ABORTED never changes state within episode $e$, and the coordinator sends no further message for it except re-sends of COMMIT to units of an ACTIVE role. A role counts toward $f_{\mathrm{field}}$ if and only if it is ACTIVE.
- (C5) Epoch change: when a new coordinator opens episode $e+1$, it reads the records of every unit; every role of episode $e$ that is ACTIVE stays ACTIVE with its COMMITTED records; every other role of episode $e$ is treated as ABORTED, and $\mathrm{ABORT}(e,r,u)$ is sent to all units of its route. Routing in episode $e+1$ uses the residual capacities $\operatorname{cap}(u)-\mathrm{held}_u$.

A record is retained longer than the maximum message lifetime. Episode identifiers are strictly
increasing and are never reused. Hence late messages remain well defined. The statements below hold
for every finite execution prefix consistent with (U1)--(U3) and (C1)--(C5), allowing loss,
duplication, and reordering.

### 2.2 Statement and proof

**Proposition 1 (reservation safety).** In every reachable global state of the protocol of Section 2.1:

(i) (Capacity safety.) For every unit $u$, $\mathrm{held}_u\le\operatorname{cap}(u)$.

(ii) (No double-booking.) For every unit $u$ and every $(e,r)$ there is at most one record, and the
loads of distinct keys are disjoint parts of $\mathrm{held}_u$; a record enters PREPARED only from
FREE, enters COMMITTED only from PREPARED and only on a COMMIT message carrying its own key, and
once ABORTED never leaves ABORTED.

(iii) (Path atomicity.) If role $r$ is ACTIVE, then every $u\in\mathcal U(r)$ holds a COMMITTED
record for $(e,r,u)$; and a role is ACTIVE only after the coordinator has received ACK-COMMIT from
every unit of its route. If the coordinator has issued ABORT for $(e,r,\cdot)$, or a lease of one of
$r$'s PREPARED records has expired, then $r$ is never ACTIVE in episode $e$ and no later message can
activate it.

Consequently, at any time, let $A$ be the set of ACTIVE roles across all episodes and let
$f_{\mathrm{field}}=\sum_{r\in A}q_r$. Then $x=\sum_{r\in A}q_r\,\mathbf{1}_{\widehat\pi_r}$ is a
feasible flow in $G_F^{\mathrm{cap}}$ for the current failed set $F$, and hence
$f_{\mathrm{field}}\le C(F,S)$.

**Proof.** Induct on the event sequence. Initially, $\mathrm{held}_u=0$ and no record exists.

*(U1).* An existing key is unchanged. A new PREPARED record is created only if

$$

\mathrm{held}_u+q_r\le \operatorname{cap}(u).

$$

Thus capacity safety is preserved and each key is created at most once.

*(U2).* PREPARED changes to COMMITTED without changing $\mathrm{held}_u$. If ABORT has already been issued, the coordinator is ABORTED by (C4); a delayed COMMIT therefore cannot activate the role. At the unit, either COMMIT is ignored after ABORT or the later ABORT changes the transient COMMITTED record to ABORTED.

*(U3).* ABORT and PREPARED-lease expiry do not increase $\mathrm{held}_u$, and ABORTED is absorbing. A lease expiry cannot change an ACTIVE role, because every record of an ACTIVE role is COMMITTED. An ABORT is issued only for a non-ACTIVE role; by (C4) that role cannot later become ACTIVE.

*(C1), (C2).* These rules do not change unit records. A transition to COMMITTING occurs only after ACK-PREPARE from every unit, and a transition to ABORTED is permanent within the episode.

*(C3).* A role becomes ACTIVE only after ACK-COMMIT from every $u\in\mathcal U(r)$. By (U2), each acknowledgement corresponds to a COMMITTED record. No ABORT for that role has been issued before activation. Hence all route records are COMMITTED at activation.

*(C5).* ACTIVE roles and their COMMITTED records are preserved. All other roles of the previous episode are aborted. Since episode identifiers are strictly increasing, keys from different episodes are distinct.

Thus (i)--(iii) hold in every reachable state.

Let $A$ be the set of ACTIVE roles. Under the epoch model, an ACTIVE role whose route is invalidated by a later node failure is re-orphaned and is no longer ACTIVE. Hence every $r\in A$ has a route in the current $G_F$. Let $\widehat\pi_r$ be its lifted route and define

$$

x=\sum_{r\in A}q_r\mathbf{1}_{\widehat\pi_r}.

$$

By (iii), every ACTIVE role using a capacitated arc $u$ has a distinct COMMITTED record at $u$. Hence, by (i)--(ii),

$$

\begin{aligned}
x(u)
&=\sum_{\substack{r\in A\\u\in\mathcal U(r)}}q_r\\
&\le \mathrm{held}_u\\
&\le \operatorname{cap}(u).
\end{aligned}

$$

Each $\widehat\pi_r$ is a current $\sigma_F$--$\tau$ path; therefore $x$ is feasible. Its value is

$$

|x|=\sum_{r\in A}q_r=f_{\mathrm{field}}.

$$

Theorem 1(e) gives

$$

f_{\mathrm{field}}\le C(F,S).

$$

$\blacksquare$

*Remark 2.1.* The CERTIFIED, HEURISTIC, and exact-solver routes are committed through the same protocol. Proposition 1 therefore applies to the selected assignment. PREPARING and COMMITTING roles do not contribute to $f_{\mathrm{field}}$.

---

## 3. Theorem 2 (fallback branch)

**Theorem 2 (fallback branch: per-scenario guarantee).** Let $c^0$ be a fixed symmetric nominal conductance on $G_F^{\mathrm{field}}$ with $c^0_{vw}\in[c_{\min},c_{\max}]$, $c_{\min}>0$, and impose the Dirichlet boundary $u=1$ on $B_F$, $u=0$ on $S$. Then:

(a) The interior potentials are determined by the partitioned Laplace system
$L_{II}u_I=-L_{I\partial}g$, which has a unique solution on every connected component of
$G_F^{\mathrm{field}}$ that contains a node of $\partial=B_F\cup S$. The solution satisfies $0\le u_v\le 1$ for all $v$.

(b) Let $f_0(F,S)$ be the number of demand units that the current-tracing and capacity-reservation
procedure (Phase 0, Phase B with $c=c^0$, and Phase C) serves from the nominal solution for the
scenario $(F,S)$. The routes it produces form a recovery configuration, so $f_0(F,S)\le C(F,S)$.

(c) The procedure is greedy and $f_0(F,S)<C(F,S)$ is possible (self-stranding).

(d) Because Phase C selects $f_{\mathrm{out}}=\max(f_\theta,f_0)$ and the nominal branch does not
depend on the learned weights $\theta$, the output satisfies $f_{\mathrm{out}}(F,S)\ge f_0(F,S)$
for every scenario $(F,S)$ and every learned policy; equivalently, the inequality holds pointwise in $(F,S)$.

**Proof.**

*(a).* Fix a connected component $K$ intersecting $\partial$, and let $I_K=I\cap K$. For $x\in\mathbb{R}^{I_K}$, extend $x$ by zero on $\partial$ and denote the extension by $\widetilde x$. Then

$$

\begin{aligned}
x^\top L_{II}^Kx
&=\sum_{\substack{\{v,w\}\in E(K)\\v\in I_K\ \mathrm{or}\ w\in I_K}}
 c_{vw}^0(\widetilde x_v-\widetilde x_w)^2\\
&=\sum_{\{v,w\}\subseteq I_K}c_{vw}^0(x_v-x_w)^2
 +\sum_{v\in I_K}
 \left(\sum_{w\in\partial\cap N_F(v)}c_{vw}^0\right)x_v^2.
\end{aligned}
\tag{3.1}

$$

The right-hand side is nonnegative. If it is zero, $x$ is constant on each connected component of $G_F^{\mathrm{field}}[I_K]$ and vanishes at every interior vertex adjacent to $\partial$. Each such component contains such a vertex by the standing assumption. Hence $x=0$. Thus $L_{II}^K$ is positive definite, so (0.1) has a unique solution.

For the maximum principle, suppose the maximum value is $M>1$ and is attained at an interior vertex $v$. Harmonicity gives

$$

u_v=\frac{1}{d_v^c}\sum_{w\in N_F(v)}c_{vw}u_w.

$$

Since $u_w\le M$ for every neighbor $w$, the equality forces $u_w=M$ for every $w\in N_F(v)$. Propagation along the connected component reaches $\partial$, where $g\in\{0,1\}$, a contradiction. Applying the same argument to a minimum below $0$ gives

$$

0\le u_v\le 1.

$$

*(b).* Along a Phase-B trace,

$$

u_{w_{i+1}}<u_{w_i}.

$$

Hence no vertex repeats, and the trace is simple. A successful trace ends at a spare and reserves all source, node, link, and spare resources on its virtual-capacity copy. Phase 0 satisfies the same capacity conditions. Therefore the accepted nominal routes form a recovery configuration, and Theorem 1 yields

$$

f_0(F,S)\le C(F,S).

$$

If the nominal branch is committed, Proposition 1 gives the same bound for the committed flow.

*(c).* Let

$$

F=\{v_1,v_2\},
\qquad
d_{v_1}=d_{v_2}=1,

$$

with live non-spares $a,b$, spares $s_1,s_2$, unit node/spare capacities, infinite link capacities, and

$$

E=\{\{v_1,a\},\{v_1,b\},\{v_2,a\},\{a,s_1\},\{b,s_2\}\}.

$$

Take $c^0\equiv 1$. Then

$$

B_{v_1}=\{a,b\},
\qquad
B_{v_2}=\{a\},
\qquad
u_a=u_b=1,
\qquad
u_{s_1}=u_{s_2}=0.

$$

The routes

$$

r_1:b\to s_2,
\qquad
r_2:a\to s_1

$$

are vertex-disjoint, so $C(F,S)=2$. If the tie for $r_1$ is resolved in favor of $a$, the greedy procedure uses $a\to s_1$ for $r_1$ and leaves no capacity at $a$ for $r_2$. Hence

$$

f_0(F,S)=1<2=C(F,S).

$$

*(d).* The nominal branch is independent of $\theta$, and Phase C uses

$$

f_{\mathrm{out}}=\max\{f_\theta,f_0\}.

$$

Therefore, for every fixed $(F,S)$,

$$

f_{\mathrm{out}}(F,S)\ge f_0(F,S).

$$

Both branch assignments are recovery configurations on their respective virtual-capacity copies. Hence

$$

f_0(F,S)\le C(F,S),
\qquad
f_\theta(F,S)\le C(F,S),

$$

and consequently

$$

f_0(F,S)\le f_{\mathrm{out}}(F,S)\le C(F,S).

$$

$\blacksquare$

---

## 4. Lemma 1 (synchronous field convergence)

**Lemma 1 (field convergence, independent of the value of the learned weights).** Consider $G_F^{\mathrm{field}}$ with symmetric conductances $c_{vw}\in[c_{\min},c_{\max}]$, $c_{\min}>0$, under the standing assumption of Section 0.3. Let $J=(D_c^{-1}A_c)_{II}$ be the interior Jacobi matrix of (0.2) and $\rho=\rho(J)$.

(a) $J$ is nonnegative and substochastic: every row sum is at most $1$; the row of an interior node
adjacent to $\partial$ sums to strictly less than $1$ (a deficient row), and the row of an interior
node with no neighbor in $\partial$ sums to exactly $1$.

(b) $\rho<1$. More precisely, $J$ is block diagonal over the connected components $Q$ of
$G_F^{\mathrm{field}}[I]$, each block $J_Q$ is irreducible with $\rho(J_Q)<1$, and
$\rho=\max_Q\rho(J_Q)$.

(c) The iteration $u_I^{k+1}=Ju_I^k+h$ converges from every initial vector to the unique solution
$u_I^*$ of (0.1). The error $e^k=u_I^k-u_I^*$ satisfies $\|e^k\|_{D_c}\le\rho^k\|e^0\|_{D_c}$, and
the asymptotic rate is exactly $\rho$: $\lim_{k\to\infty}\|J^k\|^{1/k}=\rho$ in every matrix norm,
and $\|J^ke^0\|=\rho^k\|e^0\|$ for a suitable $e^0\ne 0$. If the initial potentials lie in $[0,1]$,
then $\|e^k\|_\infty\le\varepsilon$ as soon as

$$

k\ \ge\
\frac{\log(1/\varepsilon)+\tfrac12\log\!\big(|I|\,\deg_{\max}\,c_{\max}/c_{\min}\big)}{1-\rho},

$$

which is $O(\log(1/\varepsilon)/(1-\rho))$ rounds.

(d) (Uniform bound through the conductance ratio and the boundary geometry.) Let $\ell$ be the
maximum over interior nodes of the graph distance in $G_F^{\mathrm{field}}$ to $\partial$, and
suppose a family of shortest paths from each interior node to $\partial$ can be chosen so that no
edge lies on more than $\kappa$ of them. Then

$$

1-\rho\ \ge\ \frac{c_{\min}}{c_{\max}}\cdot\frac{1}{\deg_{\max}\,\ell\,\kappa},

$$

independently of which conductances in $[c_{\min},c_{\max}]$ the learned head $g_\theta$ produces.
On a two-dimensional grid of side $D$ whose Dirichlet set meets every row (for instance when it
contains a full side of the grid, or when every row segment of $G_F$ ends at a surviving neighbor of
a failed node or at a spare), one can take $\ell\le D$ and $\kappa\le D$, so $1-\rho\ge c_{\min}/(4c_{\max}D^2)$ and the round count is $O(D^2\log(1/\varepsilon))$; this order is
attained, since for the grid with the whole outer frame as Dirichlet set and unit conductance,
$1-\rho=1-\cos\frac{\pi}{D+1}=\Theta(1/D^2)$.

(e) The penalized iteration matrix $J_M=(D_c+MP)^{-1}A_c$ of the HEURISTIC branch (0.3), $M>0$, is
likewise nonnegative and substochastic with its boundary rows deficient, and $\rho(J_M)<1$; the
iteration (0.3) converges geometrically to the unique solution of $(L_c+MP)u=MPg+\lambda(I-P)\eta$
with the same conclusions as (c).

**Proof.**

*(a).* For adjacent $v,w\in I$,

$$

J_{vw}=\frac{c_{vw}}{d_v^c}\ge 0.

$$

Moreover,

$$

\begin{aligned}
\sum_{w\in I}J_{vw}
&=\frac{\sum_{w\in I\cap N_F(v)}c_{vw}}
        {\sum_{w\in N_F(v)}c_{vw}}\\
&=1-\frac{\sum_{w\in\partial\cap N_F(v)}c_{vw}}{d_v^c}.
\end{aligned}

$$

Hence the row sum is at most $1$, and it is strictly less than $1$ exactly when $N_F(v)\cap\partial\ne\varnothing$.

*(b).* Order $I$ by the connected components $Q$ of $G_F^{\mathrm{field}}[I]$. Then

$$

J=\operatorname{diag}(J_Q)_Q,
\qquad
\rho(J)=\max_Q\rho(J_Q),

$$

and every $J_Q$ is irreducible.

Fix $Q$. By the standing assumption, $Q$ contains a vertex adjacent to $\partial$; hence $J_Q$ has a deficient row. Let

$$

J_Qx=\rho(J_Q)x,
\qquad
x>0,

$$

and set

$$

m=\max_i x_i,
\qquad
T=\{i:x_i=m\}.

$$

For $i\in T$,

$$

\rho(J_Q)m
=\sum_jJ_{ij}x_j
\le m\sum_jJ_{ij}
\le m.

$$

Thus $\rho(J_Q)\le 1$. If $\rho(J_Q)=1$, equality forces every neighbor in $Q$ of every $i\in T$ to lie in $T$, and the corresponding row sum to equal $1$. Irreducibility gives $T=Q$, contradicting the existence of a deficient row. Therefore

$$

\rho(J_Q)<1

$$

for every $Q$, and hence $\rho<1$.

*(c).* Since $\rho<1$,

$$

u_I^*=(I-J)^{-1}h

$$

is the unique fixed point. For

$$

e^k=u_I^k-u_I^*,

$$

we have

$$

e^{k+1}=Je^k,
\qquad
e^k=J^ke^0.

$$

Let $D_c$ denote the restriction of the degree matrix to $I$, and define

$$

\widehat J=D_c^{1/2}JD_c^{-1/2}
=D_c^{-1/2}(A_c)_{II}D_c^{-1/2}.

$$

The matrix $\widehat J$ is symmetric and similar to $J$. Hence

$$

\|\widehat J^{\,k}\|_2=\rho^k.

$$

Therefore

$$

\begin{aligned}
\|e^k\|_{D_c}
&=\|D_c^{1/2}J^ke^0\|_2\\
&=\|\widehat J^{\,k}D_c^{1/2}e^0\|_2\\
&\le \rho^k\|D_c^{1/2}e^0\|_2\\
&=\rho^k\|e^0\|_{D_c}.
\end{aligned}

$$

Thus $u_I^k\to u_I^*$.

Gelfand's formula gives, for every matrix norm,

$$

\lim_{k\to\infty}\|J^k\|^{1/k}=\rho.

$$

Since $\rho$ is a Perron eigenvalue of a block attaining the maximum spectral radius, there exists $e^0\ne0$ such that

$$

J^ke^0=\rho^ke^0.

$$

If $u_I^0,u_I^*\in[0,1]^{I}$, then $\|e^0\|_\infty\le1$. Also,

$$

\begin{aligned}
\|e^k\|_\infty
&\le (\min_{v\in I}d_v^c)^{-1/2}\|e^k\|_{D_c}\\
&\le \rho^k
\left(\frac{\sum_{v\in I}d_v^c}{\min_{v\in I}d_v^c}\right)^{1/2}
\|e^0\|_\infty\\
&\le \rho^k
\left(\frac{|I|\deg_{\max}c_{\max}}{c_{\min}}\right)^{1/2}.
\end{aligned}

$$

Thus $\|e^k\|_\infty\le\varepsilon$ whenever

$$

k\ge
\frac{
\log(1/\varepsilon)
+\tfrac12\log\!\left(|I|\deg_{\max}c_{\max}/c_{\min}\right)
}{1-\rho},

$$

using $\log(1/\rho)\ge1-\rho$.

*(d).* Since $\widehat J$ is symmetric and $\lambda_{\max}(\widehat J)=\rho$,

$$

\begin{aligned}
1-\rho
&=\lambda_{\min}(I-\widehat J)\\
&=\min_{x\ne0}\frac{x^\top L_{II}x}{x^\top D_cx}.
\end{aligned}

$$

Extending $x$ by zero on $\partial$ gives

$$

1-\rho
\ge
\frac{c_{\min}}{\deg_{\max}c_{\max}}
\min_{x\ne0}
\frac{
\sum_{\{v,w\}}(\widetilde x_v-\widetilde x_w)^2
}{
\sum_{v\in I}x_v^2
},

$$

where the edge sum is over edges with at least one endpoint in $I$.

For each $v\in I$, choose a shortest path

$$

\pi_v=(v=y_0,y_1,\ldots,y_{\ell_v}),
\qquad
y_{\ell_v}\in\partial,
\qquad
\ell_v\le\ell.

$$

Then

$$

\begin{aligned}
x_v^2
&=\left(\sum_{i=0}^{\ell_v-1}
(\widetilde x_{y_i}-\widetilde x_{y_{i+1}})\right)^2\\
&\le \ell_v\sum_{i=0}^{\ell_v-1}
(\widetilde x_{y_i}-\widetilde x_{y_{i+1}})^2.
\end{aligned}

$$

If every edge belongs to at most $\kappa$ selected paths, then

$$

\sum_{v\in I}x_v^2
\le
\ell\kappa
\sum_{\{v,w\}}(\widetilde x_v-\widetilde x_w)^2.

$$

Hence

$$

1-\rho
\ge
\frac{c_{\min}}{c_{\max}}
\frac{1}{\deg_{\max}\ell\kappa}.

$$

For the stated two-dimensional grid geometry,

$$

\ell\le D,
\qquad
\kappa\le D,
\qquad
\deg_{\max}=4,

$$

so

$$

1-\rho\ge\frac{c_{\min}}{4c_{\max}D^2}.

$$

For the $D\times D$ interior grid with unit conductance and the outer frame Dirichlet,

$$

J=\frac14(A_{P_D}\otimes I+I\otimes A_{P_D}),

$$

and

$$

\lambda_{ij}(J)
=\frac12\left(
\cos\frac{i\pi}{D+1}
+\cos\frac{j\pi}{D+1}
\right).

$$

Therefore

$$

\rho=\cos\frac{\pi}{D+1},
\qquad
1-\rho
=2\sin^2\frac{\pi}{2(D+1)}
=\Theta(D^{-2}).

$$

*(e).* For $J_M=(D_c+MP)^{-1}A_c$,

$$

\sum_w(J_M)_{vw}
=\frac{d_v^c}{d_v^c+Mp_v}.

$$

Thus $J_M$ is nonnegative and substochastic, with deficient boundary rows. The block argument of part (b) gives

$$

\rho(J_M)<1.

$$

The fixed point satisfies

$$

(L_c+MP)u=MPg+\lambda(I-P)\eta.

$$

With

$$

\widehat J_M
=(D_c+MP)^{-1/2}A_c(D_c+MP)^{-1/2},

$$

which is symmetric,

$$

\|e^k\|_{D_c+MP}
\le
\rho(J_M)^k\|e^0\|_{D_c+MP}.

$$

The corresponding iteration count is

$$

O\!\left(\frac{\log(1/\varepsilon)}{1-\rho(J_M)}\right).

$$

Only $c_{vw}\in[c_{\min},c_{\max}]$ is used.
$\blacksquare$

*Remark 4.1.* The estimate in part (d) depends on the path-congestion parameter $\kappa$. The conclusion $1-\rho=\Theta(D^{-2})$ applies to Dirichlet geometries with $\ell,\kappa=O(D)$; it need not hold for substantially sparser Dirichlet sets.

---

## 5. Lemma 2 (partially asynchronous field convergence)

### 5.1 Asynchronous model

Let $t\in\mathbb{Z}_{\ge0}$. For each $i\in I$, let $T^i\subseteq\mathbb{Z}_{\ge0}$ be its update times. If $t\in T^i$,

$$

\begin{aligned}
u_i(t+1)
&=\sum_{j\in I}J_{ij}u_j(\tau_j^i(t))+h_i,\\
t-\Delta
&\le \tau_j^i(t)\le t.
\end{aligned}
\tag{5.1}

$$

If $t\notin T^i$, then $u_i(t+1)=u_i(t)$. For $t<0$, set $u_i(t)=u_i(0)$.

Assume:

- (S1) $T^i$ is infinite for every $i$;
- (S2) every interval $\{t,t+1,\ldots,t+B-1\}$ contains an element of $T^i$ for every $i$;
- (S3) $t-\tau_j^i(t)\le\Delta$.

Condition (S2) implies (S1). The fixed point is $u_I^*=Ju_I^*+h$.

### 5.2 Statement and proof

**Lemma 2 (asynchronous convergence).** Let $J$ be the Dirichlet Jacobi matrix of Lemma 1 with $\rho=\rho(J)<1$.

(a) In general $\|J\|_\infty=1$, so $J$ is not a contraction in the unweighted sup-norm; this
happens whenever some interior node has no neighbor in $\partial$.

(b) There is a positive vector $w$ with $Jw\le\rho\,w$ componentwise; consequently $\|J\|_w=\rho<1$,
that is, $J$ is a contraction in the weighted sup-norm $\|\cdot\|_w$ with factor $\rho$.

(c) Under (S1) and (S3), (5.1) converges to $u_I^*$ from every initial vector. Under (S2) and (S3), if

$$

E_0=\|u_I(0)-u_I^*\|_w,

$$

then

$$

\|u_I(t)-u_I^*\|_w\le\rho^mE_0,
\qquad
t\ge m(B+\Delta),
\quad m\in\mathbb{Z}_{\ge0}.

$$

Consequently,

$$

t\ge
(B+\Delta)
\left\lceil
\frac{\log(E_0/\varepsilon)}{\log(1/\rho)}
\right\rceil

$$

implies $\|u_I(t)-u_I^*\|_w\le\varepsilon$. The iteration count is

$$

O\!\left(
\frac{(B+\Delta)\log(1/\varepsilon)}{1-\rho}
\right).

$$

The same statements hold for $J_M$ with $\rho(J_M)$ in place of $\rho$.

**Proof.**

*(a).* Since $J\ge0$,

$$

\|J\|_\infty=\max_i\sum_jJ_{ij}.

$$

By Lemma 1(a), a row corresponding to an interior vertex with no boundary neighbor sums to $1$. Hence $\|J\|_\infty=1$ whenever such a vertex exists. For the unit-conductance path

$$

s-x_1-x_2-x_3-b,
\qquad
s\in S,
\quad
b\in B_F,

$$

the row of $x_2$ sums to $1$, whereas $\rho=\cos(\pi/4)<1$.

*(b).* Write

$$

J=\operatorname{diag}(J_Q)_Q

$$

over the interior components. For each $Q$, Perron--Frobenius gives $w_Q>0$ such that

$$

J_Qw_Q=\rho(J_Q)w_Q\le\rho w_Q.

$$

Let $w$ be the concatenation of the $w_Q$. Then

$$

Jw\le\rho w.

$$

Therefore

$$

\|J\|_w
=\max_i\frac{(Jw)_i}{w_i}
\le\rho.

$$

Since every induced norm dominates the spectral radius,

$$

\|J\|_w=\rho.

$$

Equivalently,

$$

\|Jx\|_w\le\rho\|x\|_w. \tag{5.2}

$$

*(c).* Let

$$

e_i(t)=u_i(t)-u_i^*.

$$

At an update time $t\in T^i$,

$$

e_i(t+1)=\sum_jJ_{ij}e_j(\tau_j^i(t)). \tag{5.3}

$$

Otherwise $e_i(t+1)=e_i(t)$.

Set

$$

T_m=m(B+\Delta),

$$

and define

$$

P(m):\quad
|e_i(t)|\le\rho^mE_0w_i
\quad
(i\in I,\ t\ge T_m).

$$

For $m=0$, the bound follows by induction on $t$. At an update,

$$

\begin{aligned}
|e_i(t+1)|
&\le\sum_jJ_{ij}E_0w_j\\
&\le\rho E_0w_i\\
&\le E_0w_i.
\end{aligned}

$$

Assume $P(m)$. By (S2), for each $i$ there exists

$$

t_i\in T^i,
\qquad
T_m+\Delta\le t_i\le T_m+\Delta+B-1.

$$

By (S3),

$$

\tau_j^i(t_i)\ge t_i-\Delta\ge T_m.

$$

Hence

$$

\begin{aligned}
|e_i(t_i+1)|
&\le\sum_jJ_{ij}\rho^mE_0w_j\\
&\le\rho^{m+1}E_0w_i.
\end{aligned}

$$

The same estimate holds at every later update of $i$, and $e_i$ is constant between updates. Since

$$

t_i+1\le T_m+\Delta+B=T_{m+1},

$$

$P(m+1)$ follows. Thus

$$

\|e(t)\|_w\le\rho^mE_0,
\qquad
t\ge m(B+\Delta).

$$

For $\varepsilon>0$, take

$$

m=
\left\lceil
\frac{\log(E_0/\varepsilon)}{\log(1/\rho)}
\right\rceil.

$$

Using $\log(1/\rho)\ge1-\rho$ gives

$$

\begin{aligned}
m(B+\Delta)
&\le
(B+\Delta)
\left(
1+\frac{\log(E_0/\varepsilon)}{1-\rho}
\right)\\
&=O\!\left(
\frac{(B+\Delta)\log(1/\varepsilon)}{1-\rho}
\right).
\end{aligned}

$$

Under (S1) and (S3), define recursively a finite $\theta_{m+1}$ by requiring every node to update at least once after $\theta_m+\Delta$. The preceding induction then gives

$$

\|e(t)\|_w\le\rho^mE_0,
\qquad
t\ge\theta_m,

$$

so $e(t)\to0$.

The proof uses only nonnegativity and a vector $w>0$ satisfying $Jw\le\rho w$. Lemma 1(e) gives the same properties for $J_M$.
$\blacksquare$

*Remark 5.1.* For $B=1$ and $\Delta=0$, the estimate reduces to the synchronous bound, up to equivalence of norms.
