# test/bankcap — Channel water below the bank does not climb onto a thinly wet bank (check of f_dry_head_cap = 2 and 3)

> English mirror of test/bankcap/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the energy-head cap on the edge depth (`f_dry_head_cap` of `&list_enc`;
[Advection schemes](../../../docs/en/users_guide/advection.md) §5; developer.md §68.16 and §108).
`f_dry_head_cap = 2` applies the cap also when the receiving cell is wet, as long as its bed is
above the water level of the sending cell. It is checked with a flowing incised channel and a
thinly wet bank. A further configuration makes the channel water level cross the height of the bank
and checks that the discharge does not flip back and forth at the threshold of the cap
(configuration 5). `f_dry_head_cap = 3` (caps climbing edges by the energy head that also counts the
velocity head of the flow entering the sending cell; developer.md §110.24) is checked to satisfy the
same items in the same set-up (configurations 6–8).

## Rule

The edge depth $`h_e`$ that can be carried to the cell the flow heads for (the receiver) is
limited to the part of the energy head of the sender that exceeds the bed of the receiver.

```math
h_e \leftarrow \min\!\left(h_e,\ \max\!\left(\eta_s + \frac{u_n^2}{2g} - z_r,\ 0\right)\right)
```

$`\eta_s = z_s + h_s`$ is the water level of the sender, $`u_n`$ the normal velocity on the edge
and $`z_r`$ the bed of the receiver. An edge whose depth becomes 0 also gets zero velocity. It is
ENCflow's own rule built on the Bernoulli relation "water does not climb onto ground above its
energy head".

| f_dry_head_cap | When the cap is applied |
|---|---|
| 0 | never |
| 1 | the receiver is dry ($`h_r < d_d`$) |
| 2 (default) | as 1, and also when the receiver is wet but its bed is above the water level of the sender ($`z_r > \eta_s`$) |
| 3 | whether the receiver is dry or wet, when its bed is above the bed of the sender ($`z_r > z_s`$; a climbing edge). The formula is given below |

When 2 is applied to a wet receiver, the cap is relaxed while the water level of the sender is
just below the bed of the receiver. With the bed of the receiver $`d = z_r - \eta_s`$ above the
water level of the sender, the edge depth becomes

```math
h_e \leftarrow \max\!\left(\max\!\left(\frac{u_n^2}{2g} - d,\ 0\right),\ h_e - \frac{\kappa\,d}{|u_n|\,m_s}\right),\qquad \kappa = \frac{1}{4}
```

The first term is the energy-head cap of the formula above. The second term is a transition
between $`d = 0`$ (no cap) and the first term: it reduces the unit-width discharge $`|u_n| h_e`$
by $`\kappa d / m_s`$. $`m_s`$ is the factor that converts the unit-width discharge on this edge
into the change of depth of the sender in one time step (the same
$`l_k \Delta t / (\Delta x \Delta y)`$ as in the continuity equation, divided by the porosity and by
the plan-area fraction of the channel), so the term means "the flow on this edge lowers the water
level of the sender in one step by $`\kappa d`$ less than it would without the cap". Without the
transition, when the water level sits at the height of the bed of the receiver, the cap flips on
(the outflow drops and the level rises) and off (the outflow grows and the level falls) every few
steps. The width of the transition is proportional to the Courant number of the normal velocity
on the edge, so it is narrow, and the rule converges to the first term alone as the time step is
reduced. $`\kappa = 1/4`$ is the value with which the one-step response of the water level does
not overshoot the threshold even when four edges lead to receivers of the same height. The
transition is also ENCflow's own treatment (developer.md §108.9).

With 1, the cap is lifted as soon as a bank cell is thinly wet, and the edge depth of the
continuity equation returns to the mean of the two cells (the mean of a deep channel and a thin
film). On the diagonal edges of the 8-neighbour stencil, the mean of the velocities of the channel
cell and the bank cell gives a normal velocity, so channel water whose level is below the bank
climbs onto the bank. 2 is not applied to a submerged step ($`z_r < \eta_s`$): ordinary flow up a
wet slope is the same as with 1.

3 caps the edge depth on climbing edges by the following value. It has no transition.

```math
h_e \leftarrow \min\!\left(h_e,\ \max\!\left(w\,h_\mathrm{harm},\ \sigma + v_h,\ 0\right)\right),\qquad
v_h = \max\!\left(\frac{u_n^2}{2g},\ \min\!\left(\frac{u_a^2}{2g},\ \frac{h_s}{2}\right)\right)
```

```math
\sigma = \eta_s - z_r,\quad h_\mathrm{harm} = \frac{2 h_s h_r}{h_s + h_r},\quad w = \min\!\left(\max\!\left(\frac{\sigma}{h_r},\ 0\right),\ 1\right)
```

$`v_h`$ is the velocity head: $`u_n`$ is the normal velocity on this edge and $`u_a`$ is the speed of the
flow entering the sending cell along the same line (the unit-width discharge of the next edge upstream
divided by the depth of the sender). The velocity head of the entering flow is counted up to half the
depth of the sender (the velocity head of critical flow). The second term is the same energy-head cap as
in 1 and 2, with the velocity head taken also from the entering flow, which has a value even while the
edge is closed. The
first term is a floor for submerged steps (the harmonic mean of the depths on both sides when the
water level of the receiver is not above that of the sender). In the set-up of this check the
channel flow is parallel to the bank and there is no velocity head toward the bank, so 3, like 2,
does not let water climb onto the bank. The difference at a bank directly ahead of the flow is
examined by [test/bankspill](../../bankspill/en/README.md). It is ENCflow's own rule.

## Set-up

Length 400 m, Δx = 5 m, slope 0.002. An incised channel 4 cells (20 m) wide with n = 0.03 carries
137.3 m³/s (uniform depth 2.50 m, velocity 2.75 m/s, velocity head 0.38 m). The floodplain to the
north (8 rows, n = 0.05) is 3.5 m above the channel bed, so the channel water level is 1.0 m below
the bank. To the south is a terrace (channel bed + 7 m). Reach inflow at the west end, free outflow
at the east edge; the initial velocity is that of the uniform flow, and the run lasts 15 minutes.
The inputs are written by `make_bankcap.py`.

| Configuration | File | Initial floodplain | f_dry_head_cap | What is checked |
|---|---|---|---:|---|
| 1 | `param_wet2.txt` | 2 cm film | 2 | channel water does not climb onto the bank |
| 2 | `param_wet1.txt` | 2 cm film | 1 | it climbs (the check of configuration 1 tells the difference) |
| 3 | `param_dry2.txt` | dry | 2 | the bank stays dry and the channel is in uniform flow; byte-identical to configuration 4 |
| 4 | `param_dry1.txt` | dry | 1 | as above |
| 5 | `param_cross.txt` | 2 cm film | 2 | the discharge is raised and lowered as 137.3 → 330 → 137.3 m³/s over 10 minutes each (the run lasts 30 minutes), so that the channel water level crosses the height of the bank; the discharge across the bank line is recorded every step to see that it does not flip back and forth |
| 6 | `param_wet3.txt` | 2 cm film | 3 | as configuration 1 |
| 7 | `param_dry3.txt` | dry | 3 | as configuration 3; byte-identical to configuration 3 |
| 8 | `param_cross3.txt` | 2 cm film | 3 | as configuration 5 |

## Checks (Check_bankcap.py and Run.sh)

1. Configuration 1: the maximum depth over the run in the bank row (the floodplain row next to
   the channel) does not exceed the initial film of 2 cm.
2. Configuration 1: the depth of the bank row at the end is below 1 cm (the film drains into the
   channel).
3. Configuration 1: the water volume on the floodplain decreases at every output.
4. Configuration 2: the maximum depth over the run in the bank row exceeds 4 cm.
5. Configurations 3 and 4: the floodplain stays dry.
6. Configurations 3 and 4: the channel depth at the end (mean over x = 100–300 m) is within ±1 %
   of the uniform depth.
7. The depth and velocity outputs and Log.txt of configurations 3 and 4 are byte-identical (with
   a dry receiver, 1 and 2 are the same).
8. Configuration 5: the maximum second difference, from step to step, of the discharge across the
   bank line (between the channel and the floodplain, x = 100–300 m) is below 2.0 m³/s (the first
   60 seconds are excluded). With a rule without the transition, the discharge jumps by
   17–36 m³/s from step to step while the water level is at the height of the bank.
9. Configuration 5: while the channel water level is above the bed of the bank, the mean discharge
   onto the floodplain exceeds 3 m³/s (the water does go over when it should).
10. Configuration 5: on the rising limb, until the channel water level comes within 0.3 m below
    the bed of the bank, the depth of the bank row does not exceed the initial film (the
    transition is narrower than 0.3 m).
11. Configuration 6 (`f_dry_head_cap = 3`): the same as items 1–3.
12. Configuration 7: the same as items 5 and 6. The depth and velocity outputs and Log.txt are
    byte-identical to configuration 3 (in a flow parallel to a dry bank, 3 is the same as 2).
13. Configuration 8: the same as items 8–10 (3 has no transition, but the value of the cap rises
    continuously from 0, so the discharge does not flip back and forth).

## Results

| Item | Value | Verdict |
|---|---|---|
| 1 maximum depth over the run in the bank row, configuration 1 | 0.0200 m (the initial film) | PASS |
| 2 depth of the bank row at the end, configuration 1 | 0.0042 m | PASS |
| 3 water volume on the floodplain, configuration 1 | 320.0 → 237.8 → 204.0 → 178.4 m³ | PASS |
| 4 depth of the bank row, configuration 2 | maximum over the run 0.153 m, 0.071 m at the end | PASS |
| 5 and 6 configurations 3 and 4 | maximum floodplain depth over the run 0; channel depth 2.5006 m (1.0002 times the uniform depth) | PASS |
| 7 configurations 3 and 4 | the 12 files of H and V outputs and Log.txt are byte-identical | PASS |
| 8 second difference of the step-by-step discharge, configuration 5 | maximum 0.49 m³/s (at 310 s) | PASS |
| 9 discharge onto the floodplain, configuration 5 | mean 7.54 m³/s over 364–1,045 s, while the water level is above the bank | PASS |
| 10 depth of the bank row on the rising limb, configuration 5 | 0.0200 m (the initial film) until 239 s, when the water level comes within 0.3 m below the bank | PASS |
| 11 configuration 6 | maximum depth over the run in the bank row 0.0200 m, 0.0042 m at the end; water volume on the floodplain 320.0 → 237.8 → 204.1 → 178.4 m³ | PASS |
| 12 configuration 7 | maximum floodplain depth over the run 0; channel depth 2.5006 m; the 12 files are byte-identical to configuration 3 | PASS |
| 13 configuration 8 | maximum second difference of the step-by-step discharge 0.003 m³/s (at 1,079 s); mean 8.68 m³/s over 368–1,013 s, while the water level is above the bank; 0.0200 m until 240 s, when the water level comes within 0.3 m below the bank | PASS |

## Usage

```bash
make
./Run.sh            # serial (8 runs, about 40 seconds)
./Run_MPI.sh 2      # MPI (the boundary between the bank row and the channel is a band boundary)
```

## Findings and limits of accuracy

- The water that climbs onto the bank in configuration 2 raises the depth of the bank row from
  2 cm to at most 15 cm and then keeps it at 7 cm. The channel water level is 1.0 m below the
  bank and does not reach it even with the velocity head of 0.38 m added, so physically this
  water cannot climb.
- A channel next to a wet bank comes out deeper than the uniform depth whichever cap is chosen
  (2.61 m as the mean over x = 100–300 m; 2.50 m with a dry bank). This is a property of the
  advection term on the 8-neighbour stencil (developer.md §50.9) and outside the scope of this
  check. `f_dry_head_cap = 2` does not change it.
- In configuration 5 the channel depth reaches 3.93 m (0.43 m above the bank) and the depth of the
  bank row reaches 0.62 m. Within the width of the transition, water starts to go onto the bank
  while the water level is still below it, but in this set-up the width is about 2 cm (the
  "bed of the bank − channel water level" at the time the depth of the bank row has risen by 1 cm
  is 0.04 m without the transition and 0.06 m with it). The width is proportional to the normal
  velocity and to the time step, so it widens where the flow toward the bank is fast or the time
  step is large (several tens of centimetres in deep channels on real terrain, and more than 1 m in
  one case with a narrow channel given by its width;
  [the advection page](../../../docs/en/users_guide/advection.md) §5; the amount that goes over never
  exceeds that of 1).
- In configuration 8 (3), without a transition at the threshold, the second difference of the
  step-by-step discharge falls from 0.49 m³/s in configuration 5 to 0.003 m³/s. The value of the cap
  rises continuously from 0 where the water level of the sender reaches the bed of the bank.
- The default is `f_dry_head_cap = 2` (it was 1 until 2026-11-13). In rain-wetted steep valleys
  and at run-up fronts the results differ between 1 and 2
  ([test/chichibu](../../chichibu/en/README.md) and others; developer.md §108). Set 1
  explicitly to reproduce results of the versions up to then.

## Related documents

- [docs/en/users_guide/advection.md](../../../docs/en/users_guide/advection.md) §5 — switches around the advection term
- [docs/en/users_guide/swflow.md](../../../docs/en/users_guide/swflow.md) — parameter list of `&list_enc`
- developer.md §68.16 (cap toward dry receivers), §108 (extension to wet receivers), §110.24 (cap 3 on climbing edges), §50.9 (how it was found with the example bridge_wood_jam)
- [test/bankspill](../../bankspill/en/README.md) — onset of spilling into a bank pocket directly ahead of the flow (the difference between 2 and 3)
- [examples/bridge_wood_jam](../../../examples/bridge_wood_jam/en/README.md) — backwater and bypass flooding from driftwood jammed at a bridge
