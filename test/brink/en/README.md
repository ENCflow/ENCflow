# test/brink — Free overfall at a pond outlet, and the inertia of the edge right after a bend (check of f_advection_bend)

> English mirror of test/brink/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check that compares the flow dropping over a step from a level pond, in a channel one cell wide,
with the one-dimensional theory of open channels (critical flow at a free overfall and gradually
varied flow profiles). It also checks the upwind value used on the edge right after a bend in the
momentum-conserving advection (`f_advection_bend` of `&list_enc`;
[Advection schemes](../../../docs/en/users_guide/advection.md) §4.4; developer.md §110). When the
channel shifts diagonally by one row just before the overfall, the default 0 gives the flow on the
apron an energy head 9–29 m above that of the pond it comes from. With 1 it does not exceed it.

## Rule

The momentum-conserving advection (schemes 2 and 3) takes the velocity $`\bar u`$ on the face
through which the flow enters the control volume of an edge from the edge one step upstream on the
same line. When the cell upstream of it (the donor) is a wall or dry, the default (0) sets
$`\bar u = u_e`$ (the velocity of the control volume itself). This treats a wall as supplying no
momentum; it is correct for a bend along which the velocity does not change and creates no loss at
the bend ([test/bendloss](../../bendloss/en/README.md)). But when a bend coincides with a strongly
accelerating reach, that edge carries no inertia brought from upstream, and its velocity rises to
the balance between the surface slope and friction.

`f_advection_bend = 1` uses the following value in place of $`u_e`$.

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

**Staircase channel in uniform flow** (80 × 39 cells): slope 0.005 (along the path), n = 0.03. East
and north-east links alternate. Reach inflow of 200 m³/s at the west end, free outflow on the east
side, 75 minutes.

| Configuration | File | Channel | f_advection_bend | What is checked |
|---|---|---|---:|---|
| st0 | `param_st0.txt` | straight overfall | 0 | the pond profile and the apron depth agree with the theory |
| st1 | `param_st1.txt` | straight overfall | 1 | same result as st0 |
| dg0 | `param_dg0.txt` | shifts diagonally by one row just before the overfall | 0 | the energy head on the apron far exceeds that of the pond (record of the default behaviour) |
| dg1 | `param_dg1.txt` | same | 1 | the energy head on the apron does not exceed that of the pond; pond depth within ±6 % of the theory |
| sr0 | `param_sr0.txt` | staircase channel in uniform flow | 0 | — |
| sr1 | `param_sr1.txt` | same | 1 | same depth as sr0 |

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
| 9 dg0 first apron cell − pond energy head | +8.6, +19.5, +29.5 m | PASS (record of the default behaviour) |
| 10 sr1 ÷ sr0 mean depth − 1 | −0.31 % (1.5191 m and 1.5238 m) | PASS |
| 11 sr1 depth range ÷ mean | 2.3 % (2.9 % for sr0) | PASS |

Side by side for a unit-width discharge of 80 m²/s (the second stage; critical depth 8.67 m; the
theory is for the straight channel):

| | Pond depth (225 m upstream) | Depth and velocity in the first apron cell | First apron cell − pond energy head |
|---|---|---|---|
| Theory | 10.14 m | 5.67 m, 14.1 m/s | −0.8 m (the friction in between) |
| st0 (straight) | 10.24 m | 6.01 m, 13.3 m/s | −1.6 m |
| dg1 (diagonal, 1) | 9.86 m | 6.64 m, 12.0 m/s | −2.5 m |
| dg0 (diagonal, 0 = default) | 9.63 m | 3.15 m, 25.4 m/s | **+19.5 m** |

## How to read it, and limits

- **The straight channel agrees with the theory.** The pond profile is within 1.2 % from 125 m
  (2.5 cells) upstream. The cell just before the overfall is inside the drawdown and its depth is
  0.63–0.70 times the critical depth (not compared). On the apron the depth comes out 4–10 % larger
  than the loss-free theory (0.6–0.9 m of head is lost at the overfall).
- **The default (0) creates energy head in the diagonal channel.** The diagonal edge and the
  overfall edge after it have a wall on their upstream side, so their advection term is 0 and their
  velocity is set by the balance between the surface slope and friction. On the apron the depth
  becomes 2.1–4.0 m and the velocity 19–30 m/s, and the energy head is 9–29 m above that of the
  pond. The pond depth (225 m upstream of the overfall) is 4–7 % smaller than the theory.
- **With 1 the energy head on the apron does not exceed that of the pond.** The apron is 0.4–1.1 m
  deeper than in the straight channel and its energy head is 0.4–1.4 m lower (the loss due to the
  bend). The pond depth is 0.2–4.2 % smaller than the theory. There is no coefficient for tuning
  the bend loss.
- 1 changes only the inflow faces in the flow direction. The treatment of the lateral faces, in
  which slow flow on a wet bank is counted as a brake on the main stream entering from the side
  ([One-cell-wide channels and the upwind donors of the advection term](../../../docs/en/users_guide/advection_donor.md) §7),
  is unchanged.
- The check covers channels one cell wide only. In two-dimensional flow along a wall, 1 also acts
  on faces whose upwind side is a wall and which receive inflow.

## Usage

```
make
./Run.sh            # serial (about 20 s for the six runs)
./Run_MPI.sh 2      # MPI
```

## Related documents

- [Advection schemes](../../../docs/en/users_guide/advection.md) §4.4 — treatment of walls and dry cells, and `f_advection_bend`
- [test/bendloss](../../bendloss/en/README.md) — loss at bends in uniform flow (K = 0.00 with the default 0)
- developer.md §110 — background (the regime switch on the 50 m grid of Chichibu), the forms tried, verification
