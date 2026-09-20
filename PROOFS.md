# CertiHeal-Edge: Full Proofs

This document restates the formal results of the CertiHeal-Edge paper (Theorem 1, Theorem 2, Lemma 1, Lemma 2 of Appendix A, and the reservation-safety argument of Section III-B, stated here as Proposition 1) and gives complete proofs. It is self-contained: every object used is defined in Section 0. Standard results (the max-flow min-cut theorem, the integrality of maximum flows under integer capacities, flow decomposition, Menger's theorem, the Perron-Frobenius theorem, and the partially asynchronous iteration model of Bertsekas and Tsitsiklis) are invoked by name only.

Contents

- 0. Setting and notation
- 1. Theorem 1 (certificate: tight value, Menger reduction, monotonicity, weak duality)
- 2. Proposition 1 (reservation safety of the two-phase COMMIT-ALL protocol; $f_{field}\le C(F,S)$)
- 3. Theorem 2 (fallback branch: Dirichlet solution, greedy witness, per-scenario guarantee)
- 4. Lemma 1 (synchronous field convergence)
- 5. Lemma 2 (partially asynchronous field convergence)

---

## 0. Setting and notation

### 0.1 Service graph, failures, spares, demand

Let $G=(V,E)$ be a finite undirected graph (the service graph); vertices are edge nodes. Let $F\subseteq V$ be the set of fail-stopped nodes and $S\subseteq V\setminus F$ the set of spares. The live graph is the induced subgraph $G_F=G[V\setminus F]$. For $v\in V$, $N(v)$ is the neighbor set of $v$ in $G$.

Each failed node $v\in F$ carries $d_v\in\mathbb{Z}_{\ge 0}$ orphaned role units; $d(F)=\sum_{v\in F}d_v$. The orphaned roles are $R(F)$; role $r$ originates at the failed node $v(r)\in F$ and has demand $q_r\in\mathbb{Z}_{\ge 1}$, so $d_v=\sum_{r:\,v(r)=v}q_r$. Roles are interchangeable, so in Theorem 1 only the counts $d_v$ matter and roles are taken unit-sized ($q_r=1$); Proposition 1 allows general $q_r$.

Every live node $v\in V\setminus F$ has an integer capacity $b_v\ge 0$: for a non-spare, the number of role units it can host or relay; for a spare $s\in S$, its residual capacity, the number of additional role units it accepts. Every live link $\{v,w\}\in E(G_F)$ has an integer capacity $b_{vw}=b_{wv}\ge 0$ (a dead link is simply absent; an uncapacitated link has $b_{vw}=+\infty$).

The surviving boundary of a failed node $v$ is $B_v=N(v)\setminus F$. The source boundary of the field is
$$B_F=\Big(\bigcup_{v\in F}B_v\Big)\setminus S,$$
which excludes spares, so $B_F\cap S=\emptyset$. The Dirichlet set is $\partial=B_F\cup S$ and the interior is $I=(V\setminus F)\setminus\partial$.

### 0.2 The capacity graph $G_F^{cap}$ (node-split construction)

$G_F^{cap}$ is the directed capacitated graph with the following vertices and arcs.

- Vertices: a super-source $\sigma_F$; one per-node source $\sigma_v$ for each $v\in F$; for each live node $v\in V\setminus F$ an in-out pair $(v_{in},v_{out})$; and a super-sink $\tau$.
- Source arcs: $(\sigma_F,\sigma_v)$ with capacity $d_v$ for each $v\in F$; and $(\sigma_v,w_{in})$ with capacity $+\infty$ for each $v\in F$ and each $w\in B_v=N(v)\setminus F$. There are no other arcs leaving $\sigma_F$ or any $\sigma_v$, and no arcs enter them.
- Node arcs: $(v_{in},v_{out})$ with capacity $b_v$ for each live $v$.
- Link arcs: $(v_{out},w_{in})$ and $(w_{out},v_{in})$, each with capacity $b_{vw}$, for each live link $\{v,w\}\in E(G_F)$.
- Sink arcs: $(s_{out},\tau)$ with capacity $+\infty$ for each spare $s\in S$.

All finite capacities are integers. Write $c(a)$ for the capacity of arc $a$.

A flow is a function $x$ on arcs with $0\le x(a)\le c(a)$ and flow conservation at every vertex other than $\sigma_F$ and $\tau$. Its value $|x|$ is the net flow out of $\sigma_F$. A $\sigma_F$-$\tau$ cut is a vertex set $X$ with $\sigma_F\in X$, $\tau\notin X$; its capacity is $c(X)=\sum_{a=(p,q):\,p\in X,\,q\notin X}c(a)$. Because the sink arcs are uncapacitated, every finite-capacity cut $X$ contains no $s_{out}$, $s\in S$; such a cut separates $\sigma_F$ from every spare and is called a capacitated $\sigma_F$-$S$ cut. The certificate is
$$C(F,S)=\max\{|x| : x \text{ a flow in } G_F^{cap}\}.$$

A recovery configuration is a set $R'\subseteq R(F)$ of unit roles together with, for each $r\in R'$, a simple path $\pi_r$ in $G_F$ from a node of $B_{v(r)}$ to a spare, such that for every live node $v$ the number of paths using $v$ (as an interior vertex or as an endpoint) is at most $b_v$, and for every live link $\{v,w\}$ the number of paths traversing it is at most $b_{vw}$. Its size is $|R'|$, the number of role units served at once.

### 0.3 The field graph $G_F^{field}$ and the Jacobi iteration

$G_F^{field}$ is the undirected graph $G_F$ with a symmetric conductance $c_{vw}=c_{wv}\in[c_{min},c_{max}]$, $0<c_{min}\le c_{max}<\infty$, on every live link. The weighted degree of a live node is $d^c_v=\sum_{w\in N_F(v)}c_{vw}$ where $N_F(v)$ is the neighbor set in $G_F$. $A_c$ is the weighted adjacency matrix, $D_c=\mathrm{diag}(d^c_v)$, and $L_c=D_c-A_c$ is the weighted Laplacian.

The Dirichlet data are $g_v=1$ for $v\in B_F$ and $g_v=0$ for $v\in S$. Ordering live nodes as (interior $I$, boundary $\partial$), the Dirichlet problem is: find $u$ with $u_\partial=g$ and $(L_cu)_v=0$ for all $v\in I$, that is,
$$L_{II}\,u_I=-L_{I\partial}\,g. \tag{0.1}$$

The CERTIFIED branch (hard boundary, nominal conductance $c=c^0$, $\lambda=0$) iterates, for $v\in I$,
$$u_v^{k+1}=\frac{1}{d^c_v}\sum_{w\in N_F(v)}c_{vw}u_w^{k},\qquad u_w^{k}=g_w \text{ for } w\in\partial. \tag{0.2}$$
In matrix form $u_I^{k+1}=J\,u_I^{k}+h$ with
$$J=\big(D_c^{-1}A_c\big)_{II},\qquad h=\big(D_c^{-1}A_c\big)_{I\partial}\,g .$$
$J$ is the (interior) iteration matrix; $\rho=\rho(J)$ is its spectral radius.

The HEURISTIC branch (penalty weight $M>0$, forcing $\lambda\ge 0$, RUL score $\eta_v$) iterates over all live nodes $v$, with selector $p_v=1$ for $v\in\partial$ and $p_v=0$ otherwise,
$$u_v^{k+1}=\frac{\sum_{w\in N_F(v)}c_{vw}u_w^{k}+M p_v g_v+\lambda(1-p_v)\eta_v}{d^c_v+Mp_v}. \tag{0.3}$$
Its iteration matrix is $J_M=(D_c+MP)^{-1}A_c$ with $P=\mathrm{diag}(p_v)$.

Standing assumption (used in Theorem 2, Lemma 1, Lemma 2): every connected component of $G_F^{field}$ that contains an interior node also contains a node of $\partial$. A component with no node of $\partial$ contains no surviving neighbor of any failed node and no spare; it receives no demand and no route, and its potentials are irrelevant; such components are excluded from all statements below.

### 0.4 Norms

For a positive vector $w$, the weighted sup-norm is $\|x\|_w=\max_i|x_i|/w_i$ and the induced matrix norm of a nonnegative matrix is $\|J\|_w=\max_i\frac{1}{w_i}\sum_jJ_{ij}w_j$. For a positive diagonal $D$, $\|x\|_D=(x^{\top}Dx)^{1/2}$.

---

## 1. Theorem 1 (certificate)

**Theorem 1 (certificate: tight value, monotonicity, cheap lower bound).** In $G_F^{cap}$ with integer capacities:

(a) The maximum size of a recovery configuration equals the maximum flow value $C(F,S)$, and a maximum flow can be taken integral.

(b) $C(F,S)$ equals the minimum capacity of a $\sigma_F$-$\tau$ cut, which is the minimum capacity of a capacitated $\sigma_F$-$S$ cut.

(c) (Menger reduction.) If $d_v=1$ for all $v\in F$, $b_v=1$ for all live $v$, and links are uncapacitated, then $C(F,S)$ is the maximum number of pairwise vertex-disjoint paths in $G_F$ that start at distinct sets $B_v$ (one path per failed node, starting in its own $B_v$) and end in $S$, and equals the minimum number of live vertices whose removal, together with the loss of their source arcs, separates every $\sigma_v$ from $S$ in $G_F^{cap}$.

(d) (Monotonicity.) If $S\subseteq S'$ and the capacities of arcs common to $G_F^{cap}(S)$ and $G_F^{cap}(S')$ are not decreased, then $C(F,S)\le C(F,S')$.

(e) (Weak duality.) Every feasible flow $x$ in $G_F^{cap}$ satisfies $|x|\le C(F,S)$; in particular any flow committed by the local rounds is a lower bound on $C(F,S)$.

**Proof.**

*Step 1: from a recovery configuration to an integral flow.* Let $(R',\{\pi_r\})$ be a recovery configuration. For each $r\in R'$ with $\pi_r=(w_0,w_1,\dots,w_m)$, $w_0\in B_{v(r)}$, $w_m\in S$, define the directed path in $G_F^{cap}$
$$\hat\pi_r=\big(\sigma_F,\sigma_{v(r)},\,w_{0,in},w_{0,out},\,w_{1,in},w_{1,out},\dots,w_{m,in},w_{m,out},\,\tau\big).$$
Every consecutive pair is an arc of $G_F^{cap}$: $(\sigma_F,\sigma_{v(r)})$ is a source arc; $(\sigma_{v(r)},w_{0,in})$ exists because $w_0\in B_{v(r)}$; $(w_{i,in},w_{i,out})$ is a node arc; $(w_{i,out},w_{i+1,in})$ is a link arc because $\{w_i,w_{i+1}\}\in E(G_F)$; $(w_{m,out},\tau)$ is a sink arc because $w_m\in S$. Let $x=\sum_{r\in R'}\mathbf{1}_{\hat\pi_r}$ (unit flow along each path). $x$ is integral and conserves flow at every vertex other than $\sigma_F,\tau$ because each $\hat\pi_r$ does. Capacities: $x(\sigma_F,\sigma_v)=|\{r\in R':v(r)=v\}|\le d_v$ since at most $d_v$ unit roles originate at $v$; $x(v_{in},v_{out})$ is the number of paths using $v$, which is $\le b_v$ (each $\pi_r$ is simple, so it uses $v_{in},v_{out}$ at most once); $x(v_{out},w_{in})+x(w_{out},v_{in})$ is the number of paths traversing $\{v,w\}$, which is $\le b_{vw}$ in each direction separately; the remaining arcs are uncapacitated. Hence $x$ is a feasible flow with $|x|=|R'|$, and so $C(F,S)\ge$ maximum configuration size.

*Step 2: from an integral flow to a recovery configuration.* Let $x$ be an integral feasible flow. By flow decomposition, $x$ is the sum of unit flows along $|x|$ directed $\sigma_F$-$\tau$ paths plus unit flows along directed cycles; dropping the cycles yields a feasible integral flow $x'$ with $|x'|=|x|$ and $x'\le x$ arcwise. Each path $\hat\pi$ leaves $\sigma_F$ through exactly one arc $(\sigma_F,\sigma_v)$ and then through one arc $(\sigma_v,w_{in})$ with $w\in B_v$; since no arc enters any $\sigma_{v'}$ or $\sigma_F$, the path never returns to a source vertex. Thereafter it alternates node arcs and link arcs, since the only arc out of $v_{in}$ is $(v_{in},v_{out})$ and the arcs out of $v_{out}$ are link arcs or, if $v\in S$, the sink arc. It ends with $(s_{out},\tau)$ for some $s\in S$. Because a decomposition path is simple in $G_F^{cap}$, it uses each node arc at most once, so its projection $\pi=(w_0,\dots,w_m)$ to $G_F$ is a simple path from $w_0\in B_v$ to $w_m=s\in S$. Assign to failed node $v$ the $x'(\sigma_F,\sigma_v)\le d_v$ paths that pass through $\sigma_v$, one per distinct unit role originating at $v$. The node constraint holds because the number of paths through $v$ equals $x'(v_{in},v_{out})\le b_v$; the link constraint holds because the number of paths traversing $\{v,w\}$ is $x'(v_{out},w_{in})+x'(w_{out},v_{in})\le 2b_{vw}$ in total and at most $b_{vw}$ per direction, and in a recovery configuration the link capacity is counted per direction of traversal exactly as in $G_F^{cap}$. The result is a recovery configuration of size $|x|$.

*Step 3: integrality and (a).* All capacities of $G_F^{cap}$ are integers or $+\infty$; the infinite ones may be replaced by the finite integer $d(F)$ without changing any flow of value at most $d(F)$, and no flow exceeds $d(F)$ because the cut $X=\{\sigma_F\}$ has capacity $d(F)$. By the integrality theorem for maximum flows (the augmenting-path algorithm started at zero maintains integrality), there is an integral maximum flow. Steps 1 and 2 then give equality between the maximum configuration size and $C(F,S)$.

*Step 4: (b), the max-flow min-cut equivalence.* By the max-flow min-cut theorem, $C(F,S)=\min\{c(X):X \text{ a } \sigma_F\text{-}\tau \text{ cut}\}$. The minimum is finite (at most $d(F)$), so a minimizing $X$ contains no $s_{out}$ with $s\in S$, otherwise the uncapacitated sink arc $(s_{out},\tau)$ would cross it. Conversely every cut containing no $s_{out}$ is a $\sigma_F$-$\tau$ cut. Hence the minimum over $\sigma_F$-$\tau$ cuts equals the minimum over capacitated $\sigma_F$-$S$ cuts.

For completeness, here is the direction of max-flow min-cut needed for (e), which also identifies the cut. For any flow $x$ and any $\sigma_F$-$\tau$ cut $X$, summing conservation over the vertices of $X\setminus\{\sigma_F\}$ gives
$$|x|=\sum_{a \text{ leaving } X}x(a)-\sum_{a \text{ entering } X}x(a)\le\sum_{a \text{ leaving } X}c(a)=c(X). \tag{1.1}$$
If $x$ is a maximum flow, the residual graph has no augmenting $\sigma_F$-$\tau$ path; let $X$ be the set of vertices reachable from $\sigma_F$ in the residual graph. Then every arc leaving $X$ is saturated and every arc entering $X$ carries zero flow, so (1.1) holds with equality, giving $|x|=c(X)$ and hence max-flow $=$ min-cut.

*Step 5: (c), the unit-capacity case.* With $b_v=1$ for all live $v$, a unit flow uses each node arc at most once, so the paths of the decomposition in Step 2 project to pairwise vertex-disjoint simple paths in $G_F$; with $d_v=1$ at most one path leaves each $\sigma_v$, so each failed node is served by at most one path, starting in its own $B_v$. Conversely such a family of vertex-disjoint paths gives a flow by Step 1. Thus $C(F,S)$ is the maximum number of vertex-disjoint paths described in (c).

For the cut side, let $X$ be a $\sigma_F$-$\tau$ cut of finite capacity. Link arcs, the arcs $(\sigma_v,w_{in})$, and the sink arcs are uncapacitated, so none of them leaves $X$. The arcs leaving $X$ are therefore source arcs $(\sigma_F,\sigma_v)$ and node arcs $(v_{in},v_{out})$, each of capacity 1, so $c(X)=|F_0|+|U|$ with $F_0=\{v\in F:\sigma_v\notin X\}$ and $U=\{v \text{ live}: v_{in}\in X,\ v_{out}\notin X\}$. Closure of $X$ under uncapacitated arcs gives: for $v\in F\setminus F_0$, $w_{in}\in X$ for all $w\in B_v$; for every live $v$ with $v_{out}\in X$, $w_{in}\in X$ for all live neighbors $w$; and $s_{out}\notin X$ for all $s\in S$. Hence every path in $G_F-U$ that starts in $B_v$, $v\in F\setminus F_0$, has all its vertices $w$ with $w_{in}\in X$ and $w_{out}\in X$ (the latter because $w\notin U$), so it never reaches a spare. Thus $(F_0,U)$ is a separator: deleting the live vertices $U$ and disregarding the sources in $F_0$ leaves no path from any $B_v$, $v\in F\setminus F_0$, to $S$.

Conversely, let $(F_0,U)$ be any such separator and let $W$ be the set of live vertices reachable in $G_F-U$ from $\bigcup_{v\in F\setminus F_0}B_v$; then $W\cap S=\emptyset$. Put $X=\{\sigma_F\}\cup\{\sigma_v:v\in F\setminus F_0\}\cup\{w_{in},w_{out}:w\in W\}\cup\{u_{in}:u\in U,\ u \text{ adjacent to } W \text{ or } u\in B_v \text{ for some } v\in F\setminus F_0\}$. No uncapacitated arc leaves $X$, and the arcs leaving $X$ are $(\sigma_F,\sigma_v)$ for $v\in F_0$ and $(u_{in},u_{out})$ for those $u\in U$ included, so $c(X)\le|F_0|+|U|$. Therefore the minimum cut capacity equals the minimum size $|F_0|+|U|$ of a separator, which is the statement of (c). Regarding each $\sigma_v$ as an ordinary unit-capacity vertex adjacent to $B_v$, this is the vertex form of Menger's theorem between $\{\sigma_v\}_{v\in F}$ and $S$; the node-split construction is the standard reduction of vertex-disjoint paths to arc-capacitated flow.

*Step 6: (d), monotonicity.* Let $S\subseteq S'$. The vertex set of $G_F^{cap}(S')$ equals that of $G_F^{cap}(S)$ (spares are live nodes in both). Every arc of $G_F^{cap}(S)$ is an arc of $G_F^{cap}(S')$: source, node, and link arcs are defined from $F$, $G_F$, and the capacities alone, and $B_F$ plays no role in $G_F^{cap}$; the sink arcs $(s_{out},\tau)$, $s\in S$, are among those of $S'$. By hypothesis no common arc lost capacity. Hence every feasible flow of $G_F^{cap}(S)$ is a feasible flow of $G_F^{cap}(S')$ with the same value, and $C(F,S)\le C(F,S')$.

*Step 7: (e), weak duality.* This is inequality (1.1) applied to any feasible flow $x$ and a minimum cut $X^*$: $|x|\le c(X^*)=C(F,S)$. Proposition 1 shows that the routes committed by the local rounds form a feasible flow, so its value $f_{field}$ satisfies $f_{field}\le C(F,S)$. $\blacksquare$

*Remark 1.1 (indivisible multi-unit roles).* If a role $r$ with $q_r>1$ must be routed on a single path, the maximum served demand is an unsplittable-flow value, which is at most $C(F,S)$ because every unsplittable routing is a feasible flow. The certificate remains an upper bound, which is all that the witness inequality uses.

---

## 2. Proposition 1 (reservation safety and the witness bound)

### 2.1 Protocol model

A resource unit is any capacitated arc of $G_F^{cap}$: the source arc $(\sigma_F,\sigma_v)$ (capacity $d_v$), a node arc $(v_{in},v_{out})$ (capacity $b_v$; for a spare this is its slot capacity), or a link arc (capacity $b_{vw}$). Write $\mathcal U$ for the set of units and $\mathrm{cap}(u)$ for the capacity of unit $u$. Uncapacitated arcs are not units.

An episode has an identifier $e$; identifiers are strictly increasing across epochs and never reused. Within episode $e$, a coordinator computes for each role $r\in R(F)$ a candidate route: a simple path $\pi_r$ in $G_F$ from a node of $B_{v(r)}$ to a spare (Phase B), or the direct route $\sigma_{v(r)}\to s$ for an adjacent spare $s$ (Phase 0). The unit set of the route, $\mathcal U(r)\subseteq\mathcal U$, is the set of capacitated arcs of the lifted path $\hat\pi_r$ of Section 1, Step 1: the source arc of $v(r)$, the node arcs of every vertex of $\pi_r$, and the link arcs of every edge of $\pi_r$ in the direction of traversal.

Each unit $u$ keeps, for each key $(e,r,u)$ it has ever seen, a record with state in $\{\mathrm{PREPARED},\mathrm{COMMITTED},\mathrm{ABORTED}\}$ and the demand $q_r$; a key with no record is FREE. Define the held load
$$\mathrm{held}_u=\sum\{q_r:\ (e,r,u) \text{ in state PREPARED or COMMITTED}\}.$$
The coordinator keeps, for each role, a state in $\{\mathrm{ROUTED},\mathrm{PREPARING},\mathrm{COMMITTING},\mathrm{ACTIVE},\mathrm{ABORTED}\}$.

The events are message deliveries and local timeouts; each event is processed atomically at one site. The rules are:

- (U1) On $\mathrm{RESERVE}(e,r,u)$: if a record for $(e,r,u)$ exists, do nothing except re-send the acknowledgement matching its state (idempotence). Otherwise, if $\mathrm{held}_u+q_r\le\mathrm{cap}(u)$, create the record in state PREPARED and send $\mathrm{ACK\text{-}PREPARE}(e,r,u)$; else send $\mathrm{NACK}(e,r,u)$ and create no record.
- (U2) On $\mathrm{COMMIT}(e,r,u)$: if the record is PREPARED, move it to COMMITTED and send $\mathrm{ACK\text{-}COMMIT}(e,r,u)$; if COMMITTED, re-send the acknowledgement; if ABORTED or absent, ignore.
- (U3) On $\mathrm{ABORT}(e,r,u)$, or on expiry of the lease of a PREPARED record: if the record is PREPARED or COMMITTED, move it to ABORTED; if absent, create it in state ABORTED; if ABORTED, do nothing. Records in state ABORTED contribute nothing to $\mathrm{held}_u$ and reject every later RESERVE or COMMIT under the same key.
- (C1) Coordinator, role $r$ in ROUTED: send $\mathrm{RESERVE}(e,r,u)$ to all $u\in\mathcal U(r)$; go to PREPARING.
- (C2) Coordinator, role $r$ in PREPARING: on receipt of ACK-PREPARE from every $u\in\mathcal U(r)$, send $\mathrm{COMMIT}(e,r,u)$ to all $u\in\mathcal U(r)$ and go to COMMITTING. On any NACK, or on the coordinator's own lease timeout, send $\mathrm{ABORT}(e,r,u)$ to all $u\in\mathcal U(r)$ and go to ABORTED.
- (C3) Coordinator, role $r$ in COMMITTING: on receipt of ACK-COMMIT from every $u\in\mathcal U(r)$, activate $r$ and go to ACTIVE (this is the COMMIT-ALL point). On lease timeout before that, send ABORT to all $u\in\mathcal U(r)$ and go to ABORTED.
- (C4) A role in ACTIVE or ABORTED never changes state within episode $e$, and the coordinator sends no further message for it except re-sends of COMMIT to units of an ACTIVE role. A role counts toward $f_{field}$ if and only if it is ACTIVE.
- (C5) Epoch change: when a new coordinator opens episode $e+1$, it reads the records of every unit; every role of episode $e$ that is ACTIVE stays ACTIVE with its COMMITTED records; every other role of episode $e$ is treated as ABORTED, and $\mathrm{ABORT}(e,r,u)$ is sent to all units of its route. Routing in episode $e+1$ uses the residual capacities $\mathrm{cap}(u)-\mathrm{held}_u$.

Records are garbage-collected only after a retention period longer than the maximum message lifetime, so a delivered message always finds the record it refers to if one was ever created; together with the monotonicity of $e$ this makes (U1) to (U3) well defined for late messages. The claims below concern an arbitrary finite prefix of a run, that is, any interleaving of events consistent with the rules; message loss, duplication, and reordering are allowed.

### 2.2 Statement and proof

**Proposition 1 (reservation safety).** In every reachable global state of the protocol of Section 2.1:

(i) (Capacity safety.) For every unit $u$, $\mathrm{held}_u\le\mathrm{cap}(u)$.

(ii) (No double-booking.) For every unit $u$ and every $(e,r)$ there is at most one record, and the loads of distinct keys are disjoint parts of $\mathrm{held}_u$; a record enters PREPARED only from FREE, enters COMMITTED only from PREPARED and only on a COMMIT message carrying its own key, and once ABORTED never leaves ABORTED.

(iii) (Path atomicity.) If role $r$ is ACTIVE, then every $u\in\mathcal U(r)$ holds a COMMITTED record for $(e,r,u)$; and a role is ACTIVE only after the coordinator has received ACK-COMMIT from every unit of its route. If the coordinator has issued ABORT for $(e,r,\cdot)$, or a lease of one of $r$'s PREPARED records has expired, then $r$ is never ACTIVE in episode $e$ and no later message can activate it.

Consequently, at any time, let $A$ be the set of ACTIVE roles across all episodes and let $f_{field}=\sum_{r\in A}q_r$. Then $x=\sum_{r\in A}q_r\,\mathbf{1}_{\hat\pi_r}$ is a feasible flow in $G_F^{cap}$ for the current failed set $F$, and hence $f_{field}\le C(F,S)$.

**Proof.** We prove (i) to (iii) by induction over the sequence of events. All three hold in the initial state (no records, all roles ROUTED, $\mathrm{held}_u=0$). Assume they hold before an event; we check each rule.

*(U1).* A RESERVE with an existing record changes no state. A RESERVE with no record creates a PREPARED record only when $\mathrm{held}_u+q_r\le\mathrm{cap}(u)$, after which $\mathrm{held}_u$ increases by exactly $q_r$ and (i) holds. The record for $(e,r,u)$ is created exactly once (a second RESERVE finds it), so there is at most one record per key, and $\mathrm{held}_u$ is the sum over distinct keys, giving (ii). The event does not change any role state, so (iii) is unaffected.

*(U2).* A COMMIT changes state only from PREPARED to COMMITTED, under its own key, and leaves $\mathrm{held}_u$ unchanged (both states are counted). Hence (i) and (ii) are preserved. For (iii): the transition can only help the first clause; the second clause concerns the coordinator; for the third clause, if an ABORT was issued for $(e,r,\cdot)$ before this COMMIT reaches $u$ then either the ABORT already arrived at $u$ (the record is ABORTED and the COMMIT is ignored) or it has not yet arrived (the record becomes COMMITTED transiently and will become ABORTED by (U3) when the ABORT arrives); in both cases the coordinator is in ABORTED for $r$ and by (C4) never activates $r$.

*(U3).* An ABORT or lease expiry moves the record to ABORTED or creates it ABORTED; $\mathrm{held}_u$ does not increase, so (i) holds. The ABORTED state is absorbing, so (ii) holds. For (iii), we must check that no ACTIVE role loses a COMMITTED record. A lease expiry acts only on PREPARED records, and an ACTIVE role has all its records COMMITTED by the induction hypothesis, so expiry cannot touch it. An ABORT message for $(e,r,u)$ is sent only by (C2), (C3), or (C5), all from a coordinator state in which $r$ is not ACTIVE and, by (C4), never becomes ACTIVE in episode $e$; the first clause of (iii) therefore concerns no such $r$. The third clause holds because the record is now ABORTED and (U1), (U2) ignore any later RESERVE or COMMIT for the key, so the coordinator can never collect a full set of ACK-COMMIT for $r$.

*(C1), (C2).* These send messages and move the role among ROUTED, PREPARING, COMMITTING, ABORTED; no unit state changes, so (i), (ii) hold. A role enters COMMITTING only after ACK-PREPARE from every unit of its route, and ACK-PREPARE is sent by (U1) only with a PREPARED record. The move to ABORTED in (C2) makes $r$ permanently non-ACTIVE by (C4), which is what the third clause of (iii) requires.

*(C3).* A role becomes ACTIVE only after ACK-COMMIT from every $u\in\mathcal U(r)$; by (U2) each such acknowledgement was sent with the record for $(e,r,u)$ in state COMMITTED. Between the sending of that acknowledgement and the present event, the record could have left COMMITTED only through (U3), that is, through an ABORT for $(e,r,u)$; but the coordinator is in COMMITTING, so by (C2) to (C4) it has issued no ABORT for $r$, and by (C5) no other coordinator has, since the episode has not changed. Hence every record of $r$ is COMMITTED at the moment of activation, and the first two clauses of (iii) hold; the third is unaffected because $r$ is activated only if no ABORT was issued and no lease of its PREPARED records expired (an expired lease produces an ABORTED record, which never acknowledges COMMIT).

*(C5).* The new coordinator keeps ACTIVE roles ACTIVE and their COMMITTED records untouched; it issues ABORT only for non-ACTIVE roles of episode $e$, which by (C4) can never become ACTIVE. The ABORTED records fence late messages of episode $e$ exactly as in (U3). Since $e+1>e$ and identifiers are never reused, no key of episode $e+1$ collides with a key of episode $e$. Hence (i) to (iii) are preserved.

This completes the induction.

*Feasibility of the committed flow.* Fix a reachable state and let $A$ be the set of ACTIVE roles. For $r\in A$ its route $\pi_r$ was computed by Phase 0 or Phase B for the failed set of its episode, which is contained in the current failed set $F$ (failed sets only grow across epochs, and a role activated in an earlier episode with a route through a node that failed later is orphaned again and re-enters $R(F)$ as a new role; it is then no longer ACTIVE). Hence $\pi_r$ is a simple path in the current $G_F$ from a node of $B_{v(r)}$ to a spare, and its lift $\hat\pi_r$ is a directed $\sigma_F$-$\tau$ path in the current $G_F^{cap}$ (Section 1, Step 1): in particular the first arcs are $(\sigma_F,\sigma_{v(r)})$ and $(\sigma_{v(r)},w_{in})$ with $w\in B_{v(r)}$, and the latter is an arc of $G_F^{cap}$ precisely because the route starts at $B_{v(r)}$ and not at the boundary of a different failed node. Let $x=\sum_{r\in A}q_r\mathbf{1}_{\hat\pi_r}$. Conservation holds at every vertex other than $\sigma_F,\tau$ because each summand is a path flow. For a capacitated arc $u$,
$$x(u)=\sum_{r\in A:\,u\in\mathcal U(r)}q_r\le\mathrm{held}_u\le\mathrm{cap}(u),$$
where the first inequality holds because by (iii) every ACTIVE role using $u$ holds a COMMITTED record at $u$, by (ii) these records are distinct keys whose demands are disjoint parts of $\mathrm{held}_u$, and the second inequality is (i). Uncapacitated arcs impose no constraint. Thus $x$ is a feasible flow of value $|x|=\sum_{r\in A}q_r=f_{field}$, and Theorem 1(e) gives $f_{field}\le C(F,S)$. $\blacksquare$

*Remark 2.1 (two branches, solver fallback).* In Algorithm 1 the CERTIFIED and HEURISTIC branches route on separate virtual copies of the residual capacities and only the selected branch's routes enter (C1); the exact solver of step 8 also outputs routes of the form above and commits them through the same rules. Proposition 1 therefore applies to whichever assignment is committed. Roles whose route is in PREPARING or COMMITTING contribute nothing to $f_{field}$, and their held capacity is released on abort, so partial states cost nothing in the bound and nothing permanently in capacity.

---

## 3. Theorem 2 (fallback branch)

**Theorem 2 (fallback branch: per-scenario guarantee, not optimal).** Let $c^0$ be a fixed symmetric nominal conductance on $G_F^{field}$ with $c^0_{vw}\in[c_{min},c_{max}]$, $c_{min}>0$, and impose the Dirichlet boundary $u=1$ on $B_F$, $u=0$ on $S$. Then:

(a) The interior potentials are determined by the partitioned Laplace system $L_{II}u_I=-L_{I\partial}g$, which has a unique solution on every connected component of $G_F^{field}$ that contains a node of $\partial=B_F\cup S$. The solution satisfies $0\le u_v\le 1$ for all $v$.

(b) Let $f_0(F,S)$ be the number of demand units that the current-tracing and capacity-reservation procedure (Phase 0, Phase B with $c=c^0$, and Phase C) serves from the nominal solution for the scenario $(F,S)$. The routes it produces form a recovery configuration, so $f_0(F,S)\le C(F,S)$.

(c) The procedure is greedy and $f_0(F,S)<C(F,S)$ is possible (self-stranding).

(d) Because Phase C selects $f_{out}=\max(f_\theta,f_0)$ and the nominal branch does not depend on the learned weights $\theta$, the output satisfies $f_{out}(F,S)\ge f_0(F,S)$ for every scenario $(F,S)$ and every learned policy. This is a per-scenario guarantee, not a statement about an average over scenarios.

**Proof.**

*(a) Existence and uniqueness.* Fix a connected component $K$ of $G_F^{field}$ containing a node of $\partial$, let $I_K=I\cap K$, and let $L_{II}^{K}$ be the principal submatrix of $L_{c^0}$ on $I_K$ (the system (0.1) decouples over components because $L_c$ has no entries between different components). For $x\in\mathbb{R}^{I_K}$ extend $x$ by zero on $\partial$ and write $\tilde x$; then
$$x^{\top}L^{K}_{II}x=\sum_{\{v,w\}\in E(K),\ v\in I_K \text{ or } w\in I_K}c^0_{vw}(\tilde x_v-\tilde x_w)^2
=\sum_{\{v,w\}\subseteq I_K}c^0_{vw}(x_v-x_w)^2+\sum_{v\in I_K}\Big(\sum_{w\in\partial\cap N_F(v)}c^0_{vw}\Big)x_v^2 .\tag{3.1}$$
Both sums are nonnegative, so $L^K_{II}$ is positive semidefinite. Suppose $x^{\top}L^K_{II}x=0$. Then $x$ is constant on every connected component of the interior subgraph $G_F^{field}[I_K]$, and $x_v=0$ at every interior node adjacent to $\partial$. Each connected component $Q$ of $G_F^{field}[I_K]$ has such a node: $K$ is connected and contains a node of $\partial$, so there is a path in $K$ from $Q$ to $\partial$, and the last vertex of this path before its first vertex in $\partial$ lies in $Q$ (because $Q$ is a maximal connected subset of $I_K$) and is adjacent to $\partial$. Hence the constant is $0$ on every $Q$, so $x=0$. Thus $L^K_{II}$ is positive definite, in particular nonsingular, and (0.1) has exactly one solution $u_{I_K}$ on $K$. Since this holds for each component, the interior potential is unique on each component.

*Maximum principle.* Write the solution as the fixed point of (0.2): $u_I=Ju_I+h$ with $J\ge 0$ and $h=(D_c^{-1}A_c)_{I\partial}g\ge 0$. By Lemma 1 below (whose proof does not use Theorem 2) $\rho(J)<1$, so $(I-J)^{-1}=\sum_{k\ge 0}J^k\ge 0$ and $u_I=(I-J)^{-1}h\ge 0$. For the upper bound, the row sums of $D_c^{-1}A_c$ equal one, so $\mathbf 1=J\mathbf 1+(D_c^{-1}A_c)_{I\partial}\mathbf 1\ge J\mathbf 1+h$ because $g\le\mathbf 1$; hence $(I-J)(\mathbf 1-u_I)\ge 0$ and $\mathbf 1-u_I=(I-J)^{-1}(I-J)(\mathbf 1-u_I)\ge 0$. So $0\le u\le 1$ everywhere, with $u=1$ on $B_F$ and $u=0$ on $S$.

*(b) Validity of the routes and $f_0\le C$.* Consider Phase B for role $r$ with $c=c^0$. The trace starts at a node $w_0\in B_{v(r)}$, where $u_{w_0}=1$, and at each step moves along an edge $\{w_i,w_{i+1}\}$ of $G_F$ with $u_{w_{i+1}}<u_{w_i}$ whose residual capacity (node arc of $w_{i+1}$, link arc in the direction $w_i\to w_{i+1}$, on the branch's virtual copy) admits $q_r$. Because the potential strictly decreases along the trace, no vertex repeats, so the trace is a simple path and terminates after at most $|V\setminus F|$ steps. It terminates either at a spare (potential $0$, the minimum, so no decreasing edge exists) or at a non-spare vertex with no admissible decreasing edge; in the second case $r$ is not served in this branch and nothing is reserved. If it terminates at a spare $s$ with residual slot capacity at least $q_r$, the procedure reserves $q_r$ on the source arc of $v(r)$, on every node arc and link arc along the path, and on the slot of $s$, on the virtual copy, refusing the route if any reservation fails. Phase 0 routes $\sigma_{v(r)}\to s$ for an adjacent spare $s$ are prepared the same way on the virtual copy. Hence, after Phase B, the set of prepared routes of the nominal branch is a family of simple paths from $B_{v(r)}$ to $S$ whose per-unit demands respect every capacity of $G_F^{cap}$ on the virtual copy, that is, a recovery configuration (with demands $q_r$; a configuration in the sense of Section 0.2 when $q_r=1$). By Theorem 1, Step 1, its lift is a feasible flow of value $f_0(F,S)$, and Theorem 1(e) gives $f_0(F,S)\le C(F,S)$. If the nominal branch is the one committed in Phase C, Proposition 1 gives the same bound for the committed value.

*(c) Self-stranding.* Take $F=\{v_1,v_2\}$ with $d_{v_1}=d_{v_2}=1$ (roles $r_1$ from $v_1$, $r_2$ from $v_2$, in role-id order), live non-spare nodes $a,b$ with $b_a=b_b=1$, spares $s_1,s_2$ with residual capacity $1$, and edges $\{v_1,a\},\{v_1,b\},\{v_2,a\},\{a,s_1\},\{b,s_2\}$; all links uncapacitated and $c^0\equiv 1$. Then $B_{v_1}=\{a,b\}$, $B_{v_2}=\{a\}$, $B_F=\{a,b\}$, $S=\{s_1,s_2\}$, and there is no interior node: $u_a=u_b=1$, $u_{s_1}=u_{s_2}=0$. The routes $r_1:b\to s_2$ and $r_2:a\to s_1$ are vertex-disjoint, so $C(F,S)=2$ by Theorem 1. Phase 0 does not apply (no failed node is adjacent to a spare). Phase B processes $r_1$ first; it starts at a node of $B_{v_1}=\{a,b\}$ and, if the tie between $a$ and $b$ is broken in favor of $a$ (equal latency, lower peer id), routes $r_1:a\to s_1$, consuming the node capacity $b_a=1$. Then $r_2$ must start at $B_{v_2}=\{a\}$, whose node arc has no residual capacity, and is not served. Hence $f_0(F,S)=1<2=C(F,S)$. The gap is closed only by rerouting $r_1$ through $b$, which is an augmenting-path operation and not a greedy trace; this is why the exact solver of step 8 is allowed to reroute prepared paths.

*(d) Per-scenario guarantee.* The nominal branch runs with the fixed conductance $c^0$, the hard Dirichlet boundary, and $\lambda=0$; its input is the tuple $(G_F,c^0,F,S,b,\{q_r\},\text{role order},\text{tie rule})$, none of which involves the learned weights $\theta$. Hence $f_0(F,S)$ is a deterministic function of the scenario alone. Phase C computes $f_{out}=\max(f_\theta,f_0)$ and, when it commits the field assignment, commits the routes of the branch attaining the maximum. Therefore $f_{out}(F,S)\ge f_0(F,S)$ holds for every scenario and every value of $\theta$, including a learned conductance $c_\theta$ whose branch serves nothing. Since $f_0\le C(F,S)$ by (b) and, for the learned branch, the same argument as in (b) gives $f_\theta\le C(F,S)$ (its routes are also a recovery configuration on its own virtual copy), $f_{out}\le C(F,S)$ as well. The statement is per scenario: it holds for each fixed $(F,S)$, not merely on average over a failure distribution. $\blacksquare$

---

## 4. Lemma 1 (synchronous field convergence)

**Lemma 1 (field convergence, independent of the value of the learned weights).** Consider $G_F^{field}$ with symmetric conductances $c_{vw}\in[c_{min},c_{max}]$, $c_{min}>0$, under the standing assumption of Section 0.3. Let $J=(D_c^{-1}A_c)_{II}$ be the interior Jacobi matrix of (0.2) and $\rho=\rho(J)$.

(a) $J$ is nonnegative and sub-stochastic: every row sum is at most $1$; the row of an interior node adjacent to $\partial$ sums to strictly less than $1$ (a deficient row), and the row of an interior node with no neighbor in $\partial$ sums to exactly $1$.

(b) $\rho<1$. More precisely, $J$ is block diagonal over the connected components $Q$ of $G_F^{field}[I]$, each block $J_Q$ is irreducible with $\rho(J_Q)<1$, and $\rho=\max_Q\rho(J_Q)$.

(c) The iteration $u_I^{k+1}=Ju_I^k+h$ converges from every initial vector to the unique solution $u_I^*$ of (0.1). The error $e^k=u_I^k-u_I^*$ satisfies $\|e^k\|_{D_c}\le\rho^k\|e^0\|_{D_c}$, and the asymptotic rate is exactly $\rho$: $\lim_{k\to\infty}\|J^k\|^{1/k}=\rho$ in every matrix norm, and $\|J^ke^0\|=\rho^k\|e^0\|$ for a suitable $e^0\ne 0$. If the initial potentials lie in $[0,1]$, then $\|e^k\|_\infty\le\varepsilon$ as soon as
$$k\ \ge\ \frac{\log(1/\varepsilon)+\tfrac12\log\!\big(|I|\,\deg_{max}\,c_{max}/c_{min}\big)}{1-\rho},$$
which is $O(\log(1/\varepsilon)/(1-\rho))$ rounds.

(d) (Uniform bound through the conductance ratio and the boundary geometry.) Let $\ell$ be the maximum over interior nodes of the graph distance in $G_F^{field}$ to $\partial$, and suppose a family of shortest paths from each interior node to $\partial$ can be chosen so that no edge lies on more than $\kappa$ of them. Then
$$1-\rho\ \ge\ \frac{c_{min}}{c_{max}}\cdot\frac{1}{\deg_{max}\,\ell\,\kappa},$$
independently of which conductances in $[c_{min},c_{max}]$ the learned head $g_\theta$ produces. On a two-dimensional grid of side $D$ whose Dirichlet set meets every row (for instance when it contains a full side of the grid, or when every row segment of $G_F$ ends at a surviving neighbor of a failed node or at a spare), one can take $\ell\le D$ and $\kappa\le D$, so $1-\rho\ge c_{min}/(4c_{max}D^2)$ and the round count is $O(D^2\log(1/\varepsilon))$; this order is attained, since for the grid with the whole outer frame as Dirichlet set and unit conductance, $1-\rho=1-\cos\frac{\pi}{D+1}=\Theta(1/D^2)$.

(e) The penalized iteration matrix $J_M=(D_c+MP)^{-1}A_c$ of the HEURISTIC branch (0.3), $M>0$, is likewise nonnegative and sub-stochastic with its boundary rows deficient, and $\rho(J_M)<1$; the iteration (0.3) converges geometrically to the unique solution of $(L_c+MP)u=MPg+\lambda(I-P)\eta$ with the same conclusions as (c).

**Proof.**

*(a).* The entries of $J$ are $J_{vw}=c_{vw}/d^c_v\ge 0$ for $v,w\in I$ adjacent, and $0$ otherwise. The row sum is
$$\sum_{w\in I}J_{vw}=\frac{\sum_{w\in I\cap N_F(v)}c_{vw}}{\sum_{w\in N_F(v)}c_{vw}}=1-\frac{\sum_{w\in\partial\cap N_F(v)}c_{vw}}{d^c_v}.$$
The subtracted term is positive exactly when $v$ has a neighbor in $\partial$, because all conductances are positive. This proves (a).

*(b).* The pattern of $J$ is the adjacency pattern of $G_F^{field}[I]$, which is symmetric; after ordering the interior nodes by the connected components $Q$ of $G_F^{field}[I]$, $J$ is block diagonal with one block $J_Q$ per component, and $J_Q$ is irreducible because $Q$ is connected. The spectrum of $J$ is the union of the spectra of the blocks, so $\rho=\max_Q\rho(J_Q)$.

Fix $Q$. As shown in the proof of Theorem 2(a), $Q$ contains a node adjacent to $\partial$, so $J_Q$ has a deficient row. By the Perron-Frobenius theorem for irreducible nonnegative matrices, $\rho(J_Q)$ is an eigenvalue with an eigenvector $x>0$. Let $m=\max_ix_i$ and $T=\{i:x_i=m\}$. For $i\in T$,
$$\rho(J_Q)\,m=\sum_jJ_{ij}x_j\le m\sum_jJ_{ij}\le m,$$
so $\rho(J_Q)\le 1$. If $\rho(J_Q)=1$, both inequalities are equalities for every $i\in T$: the row sum of $i$ is $1$ and $x_j=m$ for every $j$ with $J_{ij}>0$, so every neighbor of $i$ in $Q$ lies in $T$. Since $Q$ is connected, $T$ is all of $Q$, and then every row of $J_Q$ sums to $1$, contradicting the existence of a deficient row. Hence $\rho(J_Q)<1$ for every $Q$ and $\rho<1$.

*(c).* Since $\rho<1$, $I-J$ is nonsingular, so the fixed point $u_I^*=(I-J)^{-1}h$ exists and is unique; it solves (0.1) because (0.2) is (0.1) divided row by row by $d^c_v$. Subtracting the fixed-point equation from the iteration gives $e^{k+1}=Je^k$, so $e^k=J^ke^0$.

Geometric bound in $\|\cdot\|_{D_c}$: put $\hat J=D_{c}^{1/2}JD_c^{-1/2}$, where $D_c$ is restricted to $I$. Then $\hat J=D_c^{-1/2}(A_c)_{II}D_c^{-1/2}$ is symmetric (because $A_c$ is symmetric), so it is diagonalizable with real eigenvalues, its spectrum coincides with that of $J$ (similarity), and $\|\hat J^k\|_2=\rho^k$. Hence
$$\|e^k\|_{D_c}=\|D_c^{1/2}J^ke^0\|_2=\|\hat J^kD_c^{1/2}e^0\|_2\le\rho^k\|D_c^{1/2}e^0\|_2=\rho^k\|e^0\|_{D_c}.$$
Convergence from every initial vector follows since $\rho<1$.

Asymptotic rate: Gelfand's formula gives $\lim_k\|J^k\|^{1/k}=\rho$ for every matrix norm. The rate is attained: $\rho$ is an eigenvalue of $J$ (it is the Perron root of the block $Q$ achieving the maximum) with a nonnegative eigenvector $x_\rho$ supported on that block, and $J^kx_\rho=\rho^kx_\rho$. Thus no faster geometric rate holds uniformly over initial errors.

Round bound: $\|e^k\|_\infty\le(\min_vd^c_v)^{-1/2}\|e^k\|_{D_c}$ and $\|e^0\|_{D_c}\le(\sum_{v\in I}d^c_v)^{1/2}\|e^0\|_\infty$. With $d^c_v\in[c_{min},\deg_{max}c_{max}]$,
$$\|e^k\|_\infty\le\rho^k\Big(\frac{|I|\deg_{max}c_{max}}{c_{min}}\Big)^{1/2}\|e^0\|_\infty.$$
If the initial potentials lie in $[0,1]$, then $\|e^0\|_\infty\le 1$ because $u_I^*\in[0,1]$ by the maximum principle of Theorem 2(a). Requiring the right-hand side to be at most $\varepsilon$ and using $\log(1/\rho)\ge1-\rho$ gives the stated $k$, which is $O(\log(1/\varepsilon)/(1-\rho))$ as $\varepsilon\to 0$ with the graph fixed.

*(d).* Because $\hat J$ is symmetric and $\rho$ is its largest eigenvalue (the Perron root is the largest eigenvalue in absolute value and is itself an eigenvalue, so the largest eigenvalue equals $\rho$),
$$1-\rho=\lambda_{min}(I-\hat J)=\min_{x\ne 0}\frac{x^{\top}L_{II}x}{x^{\top}D_cx},$$
using $I-\hat J=D_c^{-1/2}L_{II}D_c^{-1/2}$. Substituting (3.1) with the general conductance $c$ and bounding each conductance by $c_{min}$ from below in the numerator and $d^c_v\le\deg_{max}c_{max}$ in the denominator,
$$1-\rho\ \ge\ \frac{c_{min}}{\deg_{max}c_{max}}\ \min_{x\ne 0}\frac{\sum_{\{v,w\}}(\tilde x_v-\tilde x_w)^2}{\sum_{v\in I}x_v^2},$$
where the sum runs over edges of $G_F^{field}$ with at least one interior endpoint and $\tilde x$ is $x$ extended by $0$ on $\partial$. For an interior node $v$ let $\pi_v=(v=y_0,y_1,\dots,y_{\ell_v})$ be its chosen shortest path to $\partial$, $\ell_v\le\ell$, so $\tilde x_{y_{\ell_v}}=0$. By the Cauchy-Schwarz inequality,
$$x_v^2=\Big(\sum_{i=0}^{\ell_v-1}(\tilde x_{y_i}-\tilde x_{y_{i+1}})\Big)^2\le\ell_v\sum_{i=0}^{\ell_v-1}(\tilde x_{y_i}-\tilde x_{y_{i+1}})^2 .$$
Summing over $v\in I$ and using that each edge appears on at most $\kappa$ paths,
$$\sum_{v\in I}x_v^2\le\ell\,\kappa\sum_{\{v,w\}}(\tilde x_v-\tilde x_w)^2,$$
which gives the bound. On a grid of side $D$ whose Dirichlet set meets every row, route each interior node along its row toward the nearest Dirichlet node of that row; the path length is at most $D$ and a horizontal edge is used by at most $D$ nodes of its row, so $\ell,\kappa\le D$ and $\deg_{max}=4$. For the matching upper bound, take the $D\times D$ interior grid with the outer frame as Dirichlet set and unit conductance; every interior node has degree $4$, so $J=\tfrac14(A_{P_D}\otimes I+I\otimes A_{P_D})$ where $A_{P_D}$ is the adjacency matrix of the path on $D$ vertices, whose eigenvalues are $2\cos(j\pi/(D+1))$, $j=1,\dots,D$. The eigenvalues of $J$ are $\tfrac12(\cos\frac{i\pi}{D+1}+\cos\frac{j\pi}{D+1})$, so $\rho=\cos\frac{\pi}{D+1}$ and $1-\rho=2\sin^2\frac{\pi}{2(D+1)}=\Theta(1/D^2)$.

*(e).* The row of $J_M$ for a live node $v$ has entries $c_{vw}/(d^c_v+Mp_v)\ge 0$ and row sum $d^c_v/(d^c_v+Mp_v)$, which is $1$ for $v\in I$ and $d^c_v/(d^c_v+M)<1$ for $v\in\partial$. Thus $J_M$ is nonnegative and sub-stochastic with exactly the boundary rows deficient. Its pattern is the adjacency pattern of $G_F^{field}$ restricted to the live nodes being updated, so $J_M$ is block diagonal over the connected components of $G_F^{field}$, each block irreducible, and each block contains a node of $\partial$ by the standing assumption, hence a deficient row. The argument of (b) applies verbatim and gives $\rho(J_M)<1$. Writing (0.3) as $u^{k+1}=J_Mu^k+h_M$ with $h_M=(D_c+MP)^{-1}(MPg+\lambda(I-P)\eta)$, the fixed point is unique, equals the solution of $(D_c+MP-A_c)u=MPg+\lambda(I-P)\eta$, that is, $(L_c+MP)u=MPg+\lambda(I-P)\eta$, and the error obeys $e^{k+1}=J_Me^k$. Since $\hat J_M=(D_c+MP)^{1/2}J_M(D_c+MP)^{-1/2}=(D_c+MP)^{-1/2}A_c(D_c+MP)^{-1/2}$ is symmetric, the bound $\|e^k\|_{D_c+MP}\le\rho(J_M)^k\|e^0\|_{D_c+MP}$ and the round count $O(\log(1/\varepsilon)/(1-\rho(J_M)))$ follow exactly as in (c). No property of the learned conductance beyond $c_{vw}\in[c_{min},c_{max}]$ was used. $\blacksquare$

*Remark 4.1.* Part (d) is a lower bound on $1-\rho$; sparser Dirichlet sets in two dimensions can force $\kappa$ larger than $D$ and hence a smaller $1-\rho$ (for a single Dirichlet vertex on a $D\times D$ grid the smallest Dirichlet eigenvalue carries an additional logarithmic factor). The $\Theta(1/D^2)$ statement therefore refers to Dirichlet sets that admit a path system with $\ell,\kappa=O(D)$, which is the situation of the row-meeting condition above; the empirical near-linear round counts reported for the grids in the paper are consistent with (c) and (d) and are not implied by them.

---

## 5. Lemma 2 (partially asynchronous field convergence)

### 5.1 Asynchronous model

Time is discrete, $t=0,1,2,\dots$. Each interior node $i$ has a set $T^i\subseteq\mathbb{N}$ of update times. At $t\in T^i$ node $i$ computes
$$u_i(t+1)=\sum_{j\in I}J_{ij}\,u_j(\tau^i_j(t))+h_i,\qquad t-\Delta\le\tau^i_j(t)\le t, \tag{5.1}$$
and at $t\notin T^i$ it keeps $u_i(t+1)=u_i(t)$. Here $\tau^i_j(t)$ is the time stamp of the value of $u_j$ that $i$ uses; the values at negative times are the initial values, $u_j(t)=u_j(0)$ for $t<0$. The three schedule assumptions are:

- (S1) every node is updated infinitely often: $T^i$ is infinite for each $i$;
- (S2) bounded update gap: every window $\{t,t+1,\dots,t+B-1\}$ of $B$ consecutive times contains an element of $T^i$ for every $i$;
- (S3) bounded staleness: $t-\tau^i_j(t)\le\Delta$ for all $i,j,t$.

(S2) implies (S1); (S1) is listed because the qualitative convergence statement needs only it together with (S3). This is the partially asynchronous model of Bertsekas and Tsitsiklis. The fixed point is $u_I^*=Ju_I^*+h$, unique by Lemma 1.

### 5.2 Statement and proof

**Lemma 2 (asynchronous convergence).** Let $J$ be the Dirichlet Jacobi matrix of Lemma 1 with $\rho=\rho(J)<1$.

(a) In general $\|J\|_\infty=1$, so $J$ is not a contraction in the plain infinity norm; this happens whenever some interior node has no neighbor in $\partial$.

(b) There is a positive vector $w$ with $Jw\le\rho\,w$ componentwise; consequently $\|J\|_w=\rho<1$, that is, $J$ is a contraction in the weighted sup-norm $\|\cdot\|_w$ with factor $\rho$.

(c) Under (S1) and (S3), the asynchronous iteration (5.1) converges to $u_I^*$ from every initial vector. Under (S2) and (S3), with $E_0=\|u_I(0)-u_I^*\|_w$,
$$\|u_I(t)-u_I^*\|_w\le\rho^{m}E_0\qquad\text{for all } t\ge m(B+\Delta),\ m=0,1,2,\dots,$$
so $\|u_I(t)-u_I^*\|_w\le\varepsilon$ for all $t\ge(B+\Delta)\big\lceil\log(E_0/\varepsilon)/\log(1/\rho)\big\rceil$, which is $O\big((B+\Delta)\log(1/\varepsilon)/(1-\rho)\big)$. The same holds for $J_M$ and the HEURISTIC iteration (0.3) with $\rho(J_M)$ in place of $\rho$.

**Proof.**

*(a).* $\|J\|_\infty$ is the maximum row sum of $|J|=J$, which by Lemma 1(a) equals $1$ if some interior node has no neighbor in $\partial$ and is less than $1$ only when every interior node touches the boundary. For instance, on a path $s,x_1,x_2,x_3,b$ with $s\in S$, $b\in B_F$, and unit conductance, the row of $x_2$ sums to $1$, so $\|J\|_\infty=1$ although $\rho=\cos(\pi/4)<1$. Hence a single synchronous step need not reduce the plain sup-norm of the error, and the standard contraction argument in $\|\cdot\|_\infty$ is unavailable.

*(b).* By Lemma 1(b), $J$ is block diagonal over the components $Q$ of $G_F^{field}[I]$ with irreducible blocks $J_Q$ and $\rho(J_Q)\le\rho$. For each block, the Perron-Frobenius theorem provides $w_Q>0$ with $J_Qw_Q=\rho(J_Q)w_Q\le\rho\,w_Q$. Let $w$ be the concatenation of the $w_Q$; then $w>0$ and $Jw\le\rho w$. For a nonnegative matrix, $\|J\|_w=\max_i\frac{1}{w_i}\sum_jJ_{ij}w_j=\max_i\frac{(Jw)_i}{w_i}\le\rho$; and $\|J\|_w\ge\rho(J)=\rho$ for every induced norm, so $\|J\|_w=\rho$. Explicitly, for any $x$, $|(Jx)_i|\le\sum_jJ_{ij}w_j\,\frac{|x_j|}{w_j}\le\|x\|_w(Jw)_i\le\rho\|x\|_w\,w_i$, that is,
$$\|Jx\|_w\le\rho\|x\|_w. \tag{5.2}$$

*(c).* Let $e_i(t)=u_i(t)-u^*_i$. Subtracting the fixed-point equation from (5.1), an update at $t\in T^i$ gives
$$e_i(t+1)=\sum_jJ_{ij}\,e_j(\tau^i_j(t)), \tag{5.3}$$
and $e_i(t+1)=e_i(t)$ otherwise. Define $T_m=m(B+\Delta)$ and the claim
$$P(m):\qquad |e_i(t)|\le\rho^mE_0\,w_i\quad\text{for all } i\in I \text{ and all } t\ge T_m .$$

*Base case $P(0)$.* We show $|e_i(t)|\le E_0w_i$ for all $t\ge 0$ (and, by the convention on negative times, for all $t<0$) by induction on $t$. It holds at $t=0$ by definition of $E_0$. If $t\notin T^i$ the value is unchanged. If $t\in T^i$, then by (5.3), the induction hypothesis applied at the times $\tau^i_j(t)\le t$, and (5.2) applied to the vector $(e_j(\tau^i_j(t)))_j$ whose $\|\cdot\|_w$-norm is at most $E_0$,
$$|e_i(t+1)|\le\sum_jJ_{ij}\,E_0w_j\le\rho E_0w_i\le E_0w_i .$$

*Inductive step.* Assume $P(m)$. Fix $i\in I$. By (S2) there is an update time $t_i\in T^i$ with $T_m+\Delta\le t_i\le T_m+\Delta+B-1$. At this update, by (S3), every value read has stamp $\tau^i_j(t_i)\ge t_i-\Delta\ge T_m$, so $P(m)$ gives $|e_j(\tau^i_j(t_i))|\le\rho^mE_0w_j$, and by (5.3) and (5.2)
$$|e_i(t_i+1)|\le\sum_jJ_{ij}\rho^mE_0w_j\le\rho^{m+1}E_0w_i .$$
Every later update of $i$ at a time $t'\ge t_i$ reads stamps $\tau^i_j(t')\ge t'-\Delta\ge T_m$ and therefore also produces $|e_i(t'+1)|\le\rho^{m+1}E_0w_i$; between updates $e_i$ is constant. Hence $|e_i(t)|\le\rho^{m+1}E_0w_i$ for all $t\ge t_i+1$, and since $t_i+1\le T_m+\Delta+B=T_{m+1}$, in particular for all $t\ge T_{m+1}$. As $i$ was arbitrary, $P(m+1)$ holds.

Thus $\|e(t)\|_w\le\rho^mE_0$ for $t\ge m(B+\Delta)$. Given $\varepsilon>0$, choose $m=\lceil\log(E_0/\varepsilon)/\log(1/\rho)\rceil$; then $\|e(t)\|_w\le\varepsilon$ for all $t\ge m(B+\Delta)$, and using $\log(1/\rho)\ge1-\rho$,
$$m(B+\Delta)\le(B+\Delta)\Big(1+\frac{\log(E_0/\varepsilon)}{1-\rho}\Big)=O\Big(\frac{(B+\Delta)\log(1/\varepsilon)}{1-\rho}\Big).$$
Because $\|\cdot\|_w$ and $\|\cdot\|_\infty$ are equivalent norms ($\min_iw_i\,\|x\|_w\le\|x\|_\infty\le\max_iw_i\,\|x\|_w$), the same order of bound holds for the plain sup-norm error, with the ratio $\max_iw_i/\min_iw_i$ entering only through an additive term in the logarithm.

For convergence under (S1) and (S3) alone, replace the fixed window $B$ by the following: since each $T^i$ is infinite, for every $m$ there is a finite time $\theta_{m+1}$ by which every node has been updated at least once after $\theta_m+\Delta$; the inductive step above shows $\|e(t)\|_w\le\rho^{m}E_0$ for $t\ge\theta_m$, so $e(t)\to 0$, although without a rate.

Finally, the limit is the same fixed point $u_I^*$ for every schedule satisfying the assumptions, because the argument bounds the distance to that specific vector; and the proof used only $J\ge 0$, $Jw\le\rho w$ with $w>0$, and the update rule, all of which hold for $J_M$ and (0.3) by Lemma 1(e) with the Perron vectors of the blocks of $J_M$. $\blacksquare$

*Remark 5.1.* The proof is a direct instance of the convergence theorem for partially asynchronous iterations of contractions in a weighted sup-norm: the contraction property (5.2) is exactly what makes stale reads harmless, and the rate depends on $B$ and $\Delta$ through the length $B+\Delta$ of one "synchronous-equivalent" phase, not on $\Delta$ alone. If $B=1$ and $\Delta=0$ the bound reduces to the synchronous count of Lemma 1(c) up to the norm-equivalence constant.

