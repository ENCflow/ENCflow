# test/brink — Free overfall at a pond outlet, and the inertia of the edge right after a bend (check of f_advection_bend)

> English mirror of test/brink/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check that compares the flow dropping over a step from a level pond, in a channel one cell wide,
with the one-dimensional theory of open channels (critical flow at a free overfall and gradually
varied flow profiles). It also checks the upwind value used on the edge right after a bend in the
momentum-conserving advection (`f_advection_bend` of `&list_enc`;
[Advection schemes](../../../docs/en/users_guide/advection.md) §4.4; developer.md §110). When the
channel shifts diagonally by one row just before the overfall, 0 (the default until 2026-11-15)
gives the flow on the apron an energy head 9–29 m above that of the pond it comes from. With 1 and
the default 2 it does not exceed it. In
a channel with a pond below the overfall, the supercritical flow that has dropped turns into a
hydraulic jump inside the pond. When the channel shifts diagonally by one row at the foot of the
overfall, the supercritical reach disappears with 0, while with 1 the jump stands at the same
position as in the straight channel.

Places wider than one cell are checked too. Uniform flow in a channel two cells wide has the Manning
depth with both 0 and 1. At a junction where two streams drop at constant discharge into a pond with
a dead-end bay, the water surface settles to a steady state with 1. With 0 it oscillates in
the pond where the main stream enters straight (combined with `f_advection_lateral = 0` for the lateral
faces, it keeps oscillating at every discharge).

There are two groups of configurations. The old group (17 configurations) states the combination of the old
values, 3, 1, 3, for the other three switches of the advection rules (`f_advection_donor`, `f_advection_lateral`,
`f_dry_head_cap`) and compares 0 and 1 of `f_advection_bend`. The new group (17 configurations) uses the
combination of the four values for deep, slow neighbouring cells (`f_advection_donor = 4`,
`f_advection_lateral = 2`, `f_dry_head_cap = 4`) and compares 0 and 2 of `f_advection_bend` (2 is the rule of 1
plus the acceleration from the arrival speed of the water, charged by an advection term in energy-head form;
[Advection schemes](../../../docs/en/users_guide/advection.md) §4.4). The same items are judged in both groups.

## Rule

The momentum-conserving advection (schemes 2 and 3) takes the velocity $`\bar u`$ on the face
through which the flow enters the control volume of an edge from the edge one step upstream on the
same line. A face whose upstream cell (the donor) is a wall or dry is a face that the flow enters
by turning in from the side (the edge just after a bend). `f_advection_bend = 0` sets
$`\bar u = u_e`$ (the velocity of the control volume itself) on such a face. This treats a wall as
supplying no momentum; it is correct for a bend along which the velocity does not change and
creates no loss at the bend ([test/bendloss](../../bendloss/en/README.md)). But when a bend
coincides with an accelerating or a decelerating reach, that edge does not receive the momentum of
the upstream flow. In a strongly accelerating reach (the outlet of a pond, just before an overfall)
its velocity rises to the balance between the surface slope and friction. In a decelerating reach
(the foot of an overfall) the momentum of the flow that has dropped is lost.

`f_advection_bend = 1` (and the default 2) uses the following value in place of $`u_e`$.

```math
\bar u = u_e + f\left(\sigma\,\frac{f\,Q_\mathrm{in}}{W_e\,\breve h_\mathrm{in}} - u_e\right),\qquad
\breve h_\mathrm{in} = \frac{\sum_l Q_l\,s_l\,h_{e,l}}{\sum_l Q_l\,s_l},\qquad f = \frac{Q_e}{Q_\mathrm{out}}
```

$`l`$ runs over the links that actually carry water into the face cell (excluding this edge),
$`Q_l`$ is their discharge, $`s_l`$ the magnitude of their velocity, $`h_{e,l}`$ their edge depth,
and $`Q_\mathrm{in} = \sum_l Q_l`$. $`W_e`$ is the conveying width of this edge, $`Q_e`$ its
discharge and $`Q_\mathrm{out}`$ the total outflow of the face cell. $`\sigma`$ is +1 when the
positive direction of this edge points out of the face cell and −1 when it points into it. The
first term in the parentheses is "the velocity the part of the inflow that turns into this edge
would have at the width of this edge and at the depth it arrived with".

- When the depth does not change along the path, $`\bar u = u_e`$, the same as 0 (no loss is
  created at a bend in uniform flow). Where the depth decreases along the path (the flow
  accelerates), it is smaller than $`u_e`$, and the difference is the inertia the acceleration
  needs. Where the depth increases (the flow decelerates), it is larger than $`u_e`$, and the
  momentum from upstream is retained.
- The velocity of the inflow link itself is not used, because the conveying width of a diagonal
  link is 0.707 times that of an axis link, so the velocity is 1.41 times larger even in uniform
  flow. The difference in width is not counted as acceleration or deceleration.
- An edge that carries only part of the outflow of the face cell ($`f \ll 1`$), such as an edge
  spilling sideways from the main stream onto a bank, stays almost the same as with 0.
- When the inflow into the face cell is less than $`\varepsilon`$ times its outflow
  (`p_adv_donor_eps`; default 0.1), the $`f`$ in front of the parentheses is multiplied by
  $`Q_\mathrm{in}/(\varepsilon\,Q_\mathrm{out})`$, which pulls the value toward $`u_e`$. A face cell
  without inflow (a cell fed only by a source, the tip of a receding front) is the same as with 0.
  Inflow from sea cells is not counted in $`Q_\mathrm{in}`$, and the fraction of the inflow that
  does not come from sea cells is applied as a factor in the same way.
- When the line of an inflow continues beyond the face cell (the neighbour on the opposite side of
  inflow link $`l`$ belongs to the same water body as the face cell), the momentum of that inflow is
  carried to the next edge on the same line by the ordinary upwind value. So that the same momentum
  is not added again to this edge, which turns away, the depth of that inflow is counted with a
  lower bound at the depth of this edge, $`h_e = Q_e/(W_e\,|u_e|)`$.

  ```math
  h'_{e,l} = \beta_l\,h_{e,l} + (1-\beta_l)\max(h_{e,l},\,h_e),\qquad
  \beta_l = 1 - \min\!\left(1,\ \frac{h_o}{\varepsilon\,h_c}\right)
  ```

  $`h_o`$ is the depth of the neighbour on the opposite side and $`h_c`$ the depth of the face cell
  (when the opposite side is a wall or dry, $`\beta_l = 1`$ and the inflow is counted as it is). The
  part in which the inflow is shallower than this edge (a decelerating bend, where $`\bar u`$ would
  exceed $`u_e`$) is not counted; the part in which the inflow is deeper than this edge (the inertia
  needed in an accelerating bend) is counted as it is. In a channel one cell wide the line of the
  inflow ends at a wall, so the formula above applies unchanged.
- The same value is used for the part that `f_advection_donor = 3` pulls toward $`u_e`$ for a
  thin-film donor.
- This is ENCflow's own treatment. It changes only the inflow faces in the flow direction (on the
  line $`k`$); the lateral faces are unchanged.

## Set-up

Δx = 50 m, n = 0.02. The banks are dry ground 200 m above the bed, so no water leaves the channel.
`make_brink.py` writes the input.

**Overfall channel** (39 × 12 cells): level pond (bed 20 m, 20 cells) → step of 3 m → level apron
(5 cells) → outflow reach with a slope of 2 % → free outflow on the east side. A source in the two
cells at the upstream end of the pond gives the discharge in three stages, 2,000, 4,000 and
6,000 m³/s (40, 80 and 120 m²/s per unit width); each stage is raised in 10 minutes and held for
30 minutes (the run is 120 minutes). The values at the end of each stage (40, 80 and 120 minutes)
are compared.

**Channel with a pond below the drop** (51 × 12 cells): upper pond (bed 20 m, 12 cells) → step of
3 m → level lower pond (20 cells) → step of 3 m → level apron (5 cells) → outflow reach. The three
discharge stages are the same as in the overfall channel. In the lower pond there is the
supercritical flow that has dropped over the step and the subcritical flow that extends upstream
from the second step, with a hydraulic jump between them. Below, the first cell below the step is
called the "foot cell".

**Staircase channel in uniform flow** (80 × 39 cells): slope 0.005 (along the path), n = 0.03. East
and north-east links alternate. Reach inflow of 200 m³/s at the west end, free outflow on the east
side, 75 minutes.

**Straight channel two cells wide** (80 × 8 cells): slope 0.005, n = 0.03. Reach inflow of 400 m³/s
into the two cells at the west end (200 m³/s per cell), free outflow on the east side, 75 minutes.
In a channel two or more cells wide the upwind side of the diagonal links along the banks is a wall,
so the path value of 1 is used even inside uniform flow.

**Junction pond** (18 × 13 cells, Δx = 100 m, n = 0.02, banks at the pond bed + 300 m): the level
pond has three cells A, B and C in one row from the west, and D to the south of B. A is the head of
a dead-end bay. The shallow, fast flow of the west channel (slope 0.2; depth 0.12–0.29 m, velocity
5–9 m/s) drops over a step of 15 m into A. The main channel (slope 0.1) drops over a step of 36 m
into D. The outlet of the pond bends diagonally twice, from C to E on its north-east and to F on
the south-east of E, and drops over a step of 26 m east of F. Sources at the upstream ends of the
west channel and of the main channel give the discharge in three stages (west 60, 130 and 250 m³/s;
main 150, 450 and 450 m³/s; each raised over 10 minutes and held for 30 minutes), and the mean and
the range (maximum − minimum) of the depth in the four pond cells (A–D) over the last 10 minutes of
each stage are compared. The main channel enters in two ways.

```
jpond (main stream enters diagonally from the south-west)   jtee (main stream enters straight from the south)
            E                                                          E
 W → A  B  C     F → step → outflow reach                   W → A  B  C     F → step → outflow reach
     S  D                                                             D
     M  N                                                             M
  M                                                                   M
  M                                                                   M
```

W is the west channel and M the main channel. jpond has a shelf S, 9 m above the pond, south of A
and west of D, and a shelf N, 6 m above the pond, south of D; part of the main stream passes over
them and drops into the pond. In jtee the main stream runs from D into B to its north, where it
meets the bank and turns east.

| Configuration | File | Channel | f_advection_bend | What is checked |
|---|---|---|---:|---|
| st0 | `param_st0.txt` | straight overfall | 0 | the pond profile and the apron depth agree with the theory |
| st1 | `param_st1.txt` | straight overfall | 1 | same result as st0 |
| dg0 | `param_dg0.txt` | shifts diagonally by one row just before the overfall | 0 | the energy head on the apron far exceeds that of the pond (record of the behaviour with 0) |
| dg1 | `param_dg1.txt` | same | 1 | the energy head on the apron does not exceed that of the pond; pond depth within ±6 % of the theory |
| sr0 | `param_sr0.txt` | staircase channel in uniform flow | 0 | — |
| sr1 | `param_sr1.txt` | same | 1 | same depth as sr0 |
| ps1 | `param_ps1.txt` | pond below the drop; straight | 1 | the position of the jump and the depth downstream of it agree with the theory |
| pf0 | `param_pf0.txt` | same; shifts diagonally by one row just after the foot cell | 0 | the supercritical reach disappears (record of the behaviour with 0) |
| pf1 | `param_pf1.txt` | same | 1 | same profile as the straight channel (ps1) |
| pb0 | `param_pb0.txt` | same; shifts diagonally by one row just before the first step | 0 | the jump is swept downstream (record of the behaviour with 0) |
| pb1 | `param_pb1.txt` | same | 1 | the energy head in the lower pond does not exceed that of the upper pond, and the jump is not farther downstream than in the straight channel |
| wd0 | `param_wd0.txt` | uniform flow in a straight channel two cells wide | 0 | the Manning normal depth |
| wd1 | `param_wd1.txt` | same | 1 | same depth as wd0 |
| jp0 | `param_jp0.txt` | junction pond; main stream enters diagonally (jpond) | 0 | the water surface settles to a steady state |
| jp1 | `param_jp1.txt` | same | 1 | same result as jp0 (steady) |
| jt0 | `param_jt0.txt` | junction pond; main stream enters straight (jtee) | 0 (`f_advection_lateral = 0` is also set) | the water surface keeps oscillating (record of the combination of 0 with 0 for the lateral faces) |
| jt1 | `param_jt1.txt` | same | 1 | the water surface settles to a steady state |

The table above is the old group. The configurations of the new group are named with an n appended to the
configurations of 0 (`st0n`, `dg0n`, `sr0n`, `pf0n`, `pb0n`, `wd0n`, `jp0n`, `jt0n`) and with the 1 of the
configurations of 1 replaced by 2 (`st2`, `dg2`, `sr2`, `ps2`, `pf2`, `pb2`, `wd2`, `jp2`, `jt2`;
`f_advection_bend = 2`). Every configuration states all four switches of the advection rules (none depends on the
defaults).

## Theory (one-dimensional, steady; wide rectangular section, Manning)

A flow of discharge $`q`$ per unit width passes through the critical depth
$`h_c = (q^2/g)^{1/3}`$ at the overfall. The pond (level bed) is, going upstream from the overfall,
the drawdown curve (H2) of

```math
\frac{dh}{dx} = \frac{-S_f}{1 - \mathrm{Fr}^2},\qquad S_f = \frac{n^2 q^2}{h^{10/3}},\qquad \mathrm{Fr}^2 = \frac{q^2}{g h^3}
```

($`x`$ points downstream). On the apron the flow starts just below the overfall as a supercritical
flow whose specific energy above the bed is $`1.5\,h_c + \Delta z`$ ($`\Delta z`$ is the step; no
loss at the overfall) and decelerates by friction following the same equation (H3). The energy head
is $`E = z + h + (q/h)^2/2g`$. These are standard relations of open-channel hydraulics (for example
Chow 1959, *Open-Channel Hydraulics*; the original text has not been checked). `make_brink.py`
integrates them numerically.

In the channel with a pond below the drop, a hydraulic jump stands between the supercritical flow
from the foot (H3) and the subcritical flow that extends upstream from the second step (H2). The
jump is where the momentum function (specific force per unit width)

```math
M = \frac{q^2}{g h} + \frac{h^2}{2}
```

is equal on both sides (momentum is conserved across the jump; also a standard relation). With the
settings of this check it is 154, 306 and 458 m from the foot (in the order of the three discharge
stages). The position of the jump in the model is measured as the point where the Froude number,
interpolated linearly between the cell centres of the lower pond, becomes 1.

## Check items (Check_brink.py)

1. st0: the transect discharge is within ±1.5 % of the source discharge.
2. st0: the pond depth is within ±2 % of the H2 theory 125 m or more upstream of the overfall, and
   within ±4 % at 75 m upstream.
3. st0: the depth in the 1st to 4th apron cells is 0.95–1.12 times the H3 theory.
4. st0: the 1st to 4th apron cells are supercritical (Froude number > 1.2).
5. st1: the depths of all probes at all times are the same as st0 (difference of 1e-9 m or less).
6. dg1: the energy head in the 1st to 4th apron cells does not exceed the energy head of the pond
   (475 m upstream of the overfall) by more than 0.2 m.
7. dg1: the pond depth is within ±6 % of the H2 theory 125 m or more upstream.
8. dg1: the depth in the 1st to 4th apron cells is 1.00–1.30 times the H3 theory, and the flow is
   supercritical (Froude number > 1.1).
9. dg0: the energy head in the first apron cell exceeds that of the pond by more than 5 m
   (confirmation that item 6 distinguishes this difference).
10. sr0 and sr1: the mean depth over 40–80 % of the path agrees between 0 and 1 within ±1 %.
11. sr1: the range of the depth (maximum − minimum) ÷ mean over the same reach is 4 % or less.
12. ps1: the position of the jump is between 150 m upstream and 25 m downstream of the theoretical
    position.
13. ps1: the subcritical depth downstream of the jump is within ±2 % of the H2 theory (from 3 cells
    downstream of the cell containing the jump to 125 m upstream of the second step).
14. ps1: the foot cell is supercritical and its depth is 0.95–1.18 times the H3 theory.
15. pf1: same profile as the straight channel (ps1). The position of the jump differs by 50 m or
    less, the depth of the foot cell agrees within ±5 %, the depth downstream of the jump within
    ±1.5 %, and the depth of the upper pond within ±1 %.
16. pf0: the foot cell is subcritical and its depth is more than 1.5 times that of the foot cell of
    the straight channel (confirmation that item 15 distinguishes this difference).
17. pb1: the energy head in the 1st to 4th cells of the lower pond does not exceed that of the upper
    pond (325 m upstream of the step) by more than 0.2 m. The jump is inside the lower pond and not
    more than 50 m downstream of its position in the straight channel.
18. pb0: the jump is more than 250 m downstream of its position in the straight channel, or not
    inside the lower pond.
19. wd0, wd1: the depth over 40–80 % of the path is within ±0.2 % of the Manning normal depth with
    both 0 and 1, and 0 and 1 differ by 0.01 % or less.
20. jp0: over the last 10 minutes of each stage, the transect discharge is within ±1.5 % of the sum
    of the sources and the depth range in the four pond cells is 0.05 m or less (steady).
21. jp1: same result as jp0. The depth range in the four pond cells is 0.05 m or less, and the
    depths are within ±0.10 m of jp0.
22. jt0 (the configuration that combines `f_advection_bend = 0` with `f_advection_lateral = 0` for the lateral
    faces): the depth range of A exceeds 0.3 m in all three stages (record of the behaviour of this combination).
23. jt1: the depth range in the four pond cells is 0.10 m or less in all three stages (steady).

The new group (`Check_brink.py new`) judges items 1–23 with the configurations of 0 read as those with an n
appended and the configurations of 1 read as those of 2. The limits are the same, except 0.20 m for item 21 (jp2
is 0.05–0.15 m deeper than jp0n: the acceleration at the outlet of the pond, where two inflows join and leave
faster, charged by the energy-head term of 2; the water surface stays steady. This is an upper bound for
regression with a margin over the present values, not derived from theory).

## Results

| Item | Value (in the order of the three discharge stages) | Verdict |
|---|---|---|
| 1 st0 discharge vs. source | −0.12, +0.04, +0.74 % | PASS |
| 2 st0 pond depth ÷ theory − 1 | 75 m upstream: −0.1, −1.5, −2.8 %; 125–725 m upstream: −0.7 to +1.2 % | PASS |
| 3 st0 apron depth ÷ theory | 1.08–1.10, 1.06, 1.04–1.05 | PASS |
| 4 st0 Froude number on the apron | 1.50–1.90 | PASS |
| 5 st1 − st0 depth difference | 0 | PASS |
| 6 dg1 apron − pond energy head | −2.6 to −3.3, −2.5 to −3.1, −2.5 to −3.0 m | PASS |
| 7 dg1 pond depth ÷ theory − 1 | −2.3 to −0.2, −3.5 to −0.5, −4.2 to −0.6 % | PASS |
| 8 dg1 apron depth ÷ theory; Froude number | 1.21–1.25, 1.17–1.20, 1.16–1.18; 1.27–1.62 | PASS |
| 9 dg0 first apron cell − pond energy head | +8.6, +19.5, +29.5 m | PASS (record of the behaviour with 0) |
| 10 sr1 ÷ sr0 mean depth − 1 | −0.31 % (1.5191 m and 1.5238 m) | PASS |
| 11 sr1 depth range ÷ mean | 2.3 % (2.9 % for sr0) | PASS |
| 12 ps1 position of the jump (theory) | 104 m (154 m), 218 m (307 m), 347 m (459 m) | PASS |
| 13 ps1 depth downstream of the jump ÷ theory − 1 | +0.3 to +1.1, +0.1 to +0.5, −1.2 to +0.3 % | PASS |
| 14 ps1 foot cell depth ÷ theory; Froude number | 1.14, 1.05, 1.04; 1.78, 1.75, 1.65 | PASS |
| 15 pf1 position of the jump (difference from ps1) | 125 m (+21 m), 213 m (−5 m), 328 m (−19 m) | PASS |
| 15 pf1 ÷ ps1 depth − 1 | foot cell +2.9, +2.5, +1.7 %; downstream of the jump within 0.6 %; upper pond within 0.2 % | PASS |
| 16 pf0 foot cell depth (ps1) | 7.84 m (3.73 m), 11.59 m (5.98 m), 14.61 m (8.14 m); subcritical | PASS (record of the behaviour with 0) |
| 17 pb1 lower pond − upper pond energy head | −3.3 to −2.5, −3.3 to −2.5, −3.3 to −2.6 m | PASS |
| 17 pb1 position of the jump (ps1) | 47 m (104 m), 61 m (218 m), 74 m (347 m) | PASS |
| 18 pb0 position of the jump | 636 m, not inside the lower pond, not inside the lower pond | PASS (record of the behaviour with 0) |
| 19 wd0, wd1 depth ÷ normal depth − 1 | +0.003 %, +0.003 % (1.37350 m; normal depth 1.37347 m); difference between 0 and 1: 0 | PASS |
| 20 jp0 discharge difference, depth range | −0.01, 0.00, 0.00 %; 0.00 m (all three stages) | PASS |
| 21 jp1 depth range, depth difference from jp0 | 0.00 m (all three stages); +0.03 to +0.04, +0.03 to +0.06, +0.05 to +0.07 m | PASS |
| 22 jt0 depth range of A | 0.51, 0.73, 1.47 m | PASS (record of the combination of 0 with 0 for the lateral faces) |
| 23 jt1 depth range | 0.01, 0.00, 0.00 m | PASS |

Side by side for a unit-width discharge of 80 m²/s (the second stage; critical depth 8.67 m; the
theory is for the straight channel):

| | Pond depth (225 m upstream) | Depth and velocity in the first apron cell | First apron cell − pond energy head |
|---|---|---|---|
| Theory | 10.14 m | 5.67 m, 14.1 m/s | −0.8 m (the friction in between) |
| st0 (straight) | 10.24 m | 6.01 m, 13.3 m/s | −1.6 m |
| dg1 (diagonal, 1) | 9.86 m | 6.64 m, 12.0 m/s | −2.5 m |
| dg0 (diagonal, 0) | 9.63 m | 3.15 m, 25.4 m/s | **+19.5 m** |

The depths in the lower pond for a unit-width discharge of 80 m²/s (the second stage), listed from
the foot cell, are as follows (the theoretical jump is 307 m from the foot, inside the 7th cell).

| | Depth in the 1st to 10th cells (m) | Position of the jump |
|---|---|---|
| Theory | 5.68 5.84 5.99 6.16 6.33 6.50 11.11 11.02 10.94 10.85 | 307 m |
| ps1 (straight) | 5.98 6.19 6.57 7.40 8.94 10.41 11.00 11.05 10.97 10.86 | 218 m |
| pf1 (diagonal just after the foot, 1) | 6.13 6.39 6.68 7.55 9.14 10.53 11.03 11.04 10.97 10.86 | 213 m |
| pf0 (diagonal just after the foot, 0) | 11.59 11.43 11.43 11.35 11.25 11.18 11.15 11.09 10.96 10.83 | at the foot (no supercritical reach) |
| pb1 (diagonal just before the step, 1) | 7.54 9.21 10.72 11.24 11.27 11.22 11.12 11.03 10.96 10.88 | 61 m |
| pb0 (diagonal just before the step, 0) | 3.18 3.31 3.43 3.56 3.69 3.83 3.98 4.14 4.29 4.42 | not inside the lower pond |

Mean depth and its range (in brackets) in the junction pond over the last 10 minutes of each stage
(m):

| Configuration | Stage (west + main, m³/s) | A (head of the bay) | B | C | D |
|---|---|---|---|---|---|
| jp0 | 60 + 150 | 1.42 (0.00) | 1.63 (0.00) | 1.59 (0.00) | 1.30 (0.00) |
| | 130 + 450 | 2.15 (0.00) | 2.59 (0.00) | 2.49 (0.00) | 1.79 (0.00) |
| | 250 + 450 | 2.25 (0.00) | 3.03 (0.00) | 2.92 (0.00) | 2.12 (0.00) |
| jp1 | 60 + 150 | 1.45 (0.00) | 1.67 (0.00) | 1.63 (0.00) | 1.34 (0.00) |
| | 130 + 450 | 2.18 (0.00) | 2.63 (0.00) | 2.55 (0.00) | 1.82 (0.00) |
| | 250 + 450 | 2.32 (0.00) | 3.09 (0.00) | 2.99 (0.00) | 2.17 (0.00) |
| jt0 | 60 + 150 | 1.93 (0.51) | 2.11 (0.29) | 1.86 (0.28) | 1.68 (0.17) |
| | 130 + 450 | 3.42 (0.73) | 3.81 (0.56) | 3.24 (0.40) | 2.95 (0.10) |
| | 250 + 450 | 3.74 (1.47) | 4.40 (1.01) | 3.63 (0.85) | 3.36 (0.28) |
| jt1 | 60 + 150 | 1.90 (0.01) | 2.10 (0.01) | 1.87 (0.01) | 1.66 (0.00) |
| | 130 + 450 | 3.30 (0.00) | 3.77 (0.00) | 3.29 (0.00) | 2.74 (0.00) |
| | 250 + 450 | 3.55 (0.00) | 4.25 (0.00) | 3.68 (0.00) | 3.12 (0.00) |

New group (combination of the four values; all pass):

- **The straight channel (st2) has exactly the same depths as st0n** (item 5; difference 0). A cell where the
  discharge is given by a source is treated like a stage-prescribed cell: the acceleration from rest is not
  counted (developer.md §113.9 (9)).
- The energy head on the apron of the channel shifted diagonally just before the overfall (dg2) is 2.8–3.5 m
  below the pond (item 6), while dg0n with 0 exceeds it by +8.6, +19.5 and +29.5 m (item 9). The hydraulic jump in
  the pond below the drop stands at 104, 218 and 347 m in the straight channel (ps2), at 125, 213 and 328 m with
  a diagonal link just after the foot (pf2), and at 39–47 m with a diagonal link just before the drop (pb2), as in
  the old group (items 12, 15 and 17). The depths in the uniform flow in the stepped channel (sr2) and in the
  channel two cells wide (wd2) are the same as with 0 (items 10 and 19).
- In the junction ponds, the pond where the main stream enters diagonally (jp2) is 0.05–0.15 m deeper than jp0n
  (item 21), and the pond where it enters straight (jt2) is steady (range at most 0.005 m; cell A at 120 minutes is
  3.08 m, 0.47 m shallower than the 3.55 m of jt1 in the old group). jt0n, with 0 and lateral 0, keeps
  oscillating as in the old group (range in cell A 0.45, 0.78 and 1.31 m).

## How to read it, and limits

- **The straight channel agrees with the theory.** The pond profile is within 1.2 % from 125 m
  (2.5 cells) upstream. The cell just before the overfall is inside the drawdown and its depth is
  0.63–0.70 times the critical depth (not compared). On the apron the depth comes out 4–10 % larger
  than the loss-free theory (0.6–0.9 m of head is lost at the overfall).
- **0 creates energy head in the diagonal channel.** The diagonal edge and the
  overfall edge after it have a wall on their upstream side, so their advection term is 0 and their
  velocity is set by the balance between the surface slope and friction. On the apron the depth
  becomes 2.1–4.0 m and the velocity 19–30 m/s, and the energy head is 9–29 m above that of the
  pond. The pond depth (225 m upstream of the overfall) is 4–7 % smaller than the theory.
- **With 1 the energy head on the apron does not exceed that of the pond.** The apron is 0.4–1.1 m
  deeper than in the straight channel and its energy head is 0.4–1.4 m lower (the loss due to the
  bend). The pond depth is 0.2–4.2 % smaller than the theory. There is no coefficient for tuning
  the bend loss.
- **In the straight channel with a pond below the drop, the jump is 50–112 m (1–2 cells) upstream
  of the theory.** Because of the head lost at the overfall the supercritical flow at the foot is
  4–14 % deeper (slower) than the theory, and the numerical jump is 3–4 cells wide. The depth
  downstream of the jump is within ±1.2 % of the theory.
- **Even when the channel shifts diagonally just after the foot, 1 gives the same profile as the
  straight channel.** The position of the jump differs by 21 m or less, and the foot cell is
  1.7–2.9 % deeper. With 0, the edge right after the bend at the foot does not receive the momentum
  of the flow that has dropped. The foot cell becomes subcritical and piles up 0.06–0.20 m above the
  cell downstream of it, and the supercritical reach disappears. The first step is also drowned, and
  the depth of the cell just before the step becomes 5.1, 8.7 and 11.8 m (3.5, 5.9 and 8.0 m in the
  straight channel).
- **When the channel shifts diagonally just before the step, even 1 does not give the same result as
  the straight channel.** The loss due to the bend weakens the supercritical flow, and the jump
  stands 47–74 m from the foot (57–273 m upstream of its position in the straight channel). With 0,
  the supercritical flow that has gained energy head at the bend just before the step sweeps the
  jump away (the jump is at 636 m, or outside the lower pond).
- 1 changes only the inflow faces in the flow direction. The lateral faces (the treatment in which
  slow flow on a wet bank is counted as a brake on the main stream entering from the side, and the
  loss at a junction) are handled by `f_advection_lateral`
  ([One-cell-wide channels and the upwind donors of the advection term](../../../docs/en/users_guide/advection_donor.md) §7,
  [test/tjunction](../../tjunction/en/README.md)).
- **Uniform flow in a channel two cells wide has the Manning depth with both 0 and 1.** The path
  value equals $`u_e`$ whenever inflow and outflow balance and the depth is uniform, so it creates
  no loss on the diagonal links along the banks either.
- **The junction pond settles to a steady state with 1.** The shallow, fast inflow that drops into
  the head of the bay A continues through A to B on the same line. Its momentum is carried to the
  edge A–B by the ordinary upwind value. Because the path value of 1 bounds the depth of an inflow
  whose line continues from below by the depth of the edge, it does not add the same momentum again
  to the edge that leaves A diagonally towards D (whose upwind side is a wall). jp1 is steady in all
  three stages, and the pond is only 0.03–0.07 m deeper than with 0. Without this treatment the
  same pond keeps oscillating with a range of 0.6 m (period 100–130 s), or the depth at the head of
  the bay becomes 0.7 m lower than with 0 (the fast velocity matched to the shallow inflow depth is
  applied to all of the deep, slow pond water and pushes the water of the bay out).
- **Depending on the shape of the pond, 0 does not settle to a steady state.** In the pond where the
  main stream enters straight and turns where it meets the bank, jt0, which combines 0 with
  `f_advection_lateral = 0` for the lateral faces, keeps oscillating in all three stages with a range
  of 0.51–1.47 m (period 80–115 s). The inflow is constant, so this oscillation is produced by the
  computation. Even with 1 for the lateral faces, with 0 the first and third stages
  oscillate (ranges of 0.30 and 0.81 m; 0.00 m in the second stage). With 1 the same pond is steady
  (an oscillation of 0.01 m remains at the end of the first stage; 0.00 m in the second and third).
- There is no theory to compare the depths of the junction pond with. What is checked is whether
  the water surface settles to a steady state under steady inflow, and the difference between 0 and
  1. Even with 0 the head of the bay is 0.21–0.78 m lower than B (the momentum of the dropping flow
  turns into a rise of the water surface from the head of the bay towards the pond).
- **The depth of the pond also changes with the rule for the lateral faces.** With the default
  `f_advection_lateral = 1`, jt1, the pond that the main stream enters straight, is 0.04–0.38 m
  shallower than with 0 (in the second stage A goes from 3.58 to 3.30 m and D from 3.07 to 2.74 m;
  the oscillation at the end of the first stage goes from 0.04 to 0.01 m). In the pond that the main
  stream enters diagonally (jp0, jp1) the difference is −0.01 to +0.04 m. This check has no theory
  that tells which is right (the rule for the lateral faces is checked in
  [test/tjunction](../../tjunction/en/README.md) and [test/wetbank](../../wetbank/en/README.md)).
- The check covers channels one cell wide, the two pond shapes above and uniform flow two cells
  wide only. In two-dimensional flow along a wall, 1 acts on faces whose upwind side is a wall and
  which receive inflow. The depth and the oscillation of a pond whose banks are wet with a thin film
  (developer.md §110.15) are not part of this check.

## Usage

```
make
./Run.sh            # serial (about 40 s for the thirty-four runs)
./Run_MPI.sh 2      # MPI
```

## Related documents

- [Advection schemes](../../../docs/en/users_guide/advection.md) §4.4 — treatment of walls and dry cells, and `f_advection_bend`
- [test/bendloss](../../bendloss/en/README.md) — loss at bends in uniform flow (K = 0.00 with both 0 and 1)
- developer.md §110 — background (the regime switch on the 50 m grid of Chichibu), the forms tried, verification, the oscillation of junction ponds
