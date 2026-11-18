# The cap on the edge depth toward higher ground (f_dry_head_cap)

> English mirror of docs/users_guide/dry_head_cap.md. The Japanese file is the master copy.

[Advection schemes](advection.md) | [Shallow water chapter](swflow.md) | [User's guide index](../users_guide.md)

This page explains the rule that caps, by the energy head, the depth on edges
toward ground above the water surface (banks, the land behind them, valley
walls). It describes what `f_dry_head_cap` of `&list_enc` (default 3)
prevents, how options 1, 2 and 3 differ, their limits, and what to set to
reproduce earlier results. How the edge depth is defined in the first place
is in [ENC grid and time integration](encgrid.md), the advection schemes are
in [Advection schemes](advection.md), and the records of the design and the
numerical experiments (for developers) are in docs/developer.md §68.16 (1),
§108 (2), and §110.24, §110.30 and §110.32 (3) (in Japanese).

**Key points**

- The pressure term stops water from climbing onto ground above the water
  surface, but where the advection term wins, water can leak over at bore
  fronts and in incised channels. Capping the edge depth toward high ground by
  the energy head prevents it.
- The default 3 caps climbing edges (edges where the bed of the receiver is
  above the bed of the sender), whether the receiver is dry or wet. The
  velocity head also counts the flow entering the sending cell. The time and
  amount at which channel water starts to spill onto a bank do not depend on
  the time step.
- 1 (the default until 2026-11-13) caps only while the receiver is dry, and 2
  (the default until 2026-11-16) also caps a wet receiver as long as its bed
  is above the water level of the sender. Both take the velocity head from the
  velocity of the edge itself, so the onset of spilling depends on the time
  step.
- To reproduce cases computed or calibrated while each was the default, set
  that value explicitly (§6).

## 1. What the rule prevents

The pressure term stops water from climbing onto ground above the water
surface, but where the advection term wins, water can leak over at bore
fronts and in incised channels. `f_dry_head_cap` caps the edge depth toward
high ground by the energy head and prevents it.

1, 2 and 3 are all ENCflow's own rules built on the Bernoulli relation "water
does not climb onto ground above its energy head". $`\sigma`$ of 3 (§3) is the
same quantity as the flow depth between cells taken as "the higher water level
minus the higher bed level" in flood inundation models[^bates10]. Taking the
velocity head from the entering flow, its limit, and the harmonic-mean floor
are ENCflow's own.

## 2. Options

| Value | Edges that are capped | Where the velocity head comes from | Default until |
|---|---|---|---|
| 0 | none | — | 2026-10-03 |
| 1 | edges whose receiving cell is dry | the velocity of the edge itself, $`u_n^2/2g`$ | 2026-11-13 |
| 2 | as 1, and also edges whose receiver is wet but has its bed above the water level of the sender (with a transition at the threshold) | the same | 2026-11-16 |
| 3 | climbing edges (the bed of the receiver above the bed of the sender), whether the receiver is dry or wet | the larger of the velocity of the edge itself and the flow entering the sending cell (for a supercritical flow, up to the specific energy of the critical flow of the same discharge) | current default |

1 prevents the leaks and the blow-up at bore fronts and in incised channels.
It does not act at ordinary wet/dry fronts, where it is the same as 0.

## 3. The default 3: formula and idea

3 caps the edge depth on climbing edges (edges where the bed of the receiver
is above the bed of the sender), whether the receiver is dry or wet, by

```math
h_e \le \max(w\,h_\mathrm{harm},\ \sigma + v_h,\ 0)
```

with the following symbols.

- $`\sigma`$: the water level of the sender minus the bed of the receiver (the
  thickness of the water that goes over).
- $`v_h = \max(u_n^2/2g,\ v_a)`$: the velocity head. $`u_n`$ is the velocity of
  this edge.
- $`v_a`$: the part of the flow entering the sending cell along the same line.
  When its speed $`u_a`$, i.e. the unit-width discharge of the next edge
  upstream divided by the depth of the sender $`h_s`$, is subcritical
  ($`u_a^2 \le g h_s`$), it is the velocity head $`u_a^2/2g`$, and when it is
  supercritical, it is the specific energy of the critical flow of the same
  discharge minus the depth of the sender, $`\tfrac{3}{2}h_c - h_s`$, where
  $`h_c = (u_a^2 h_s^2/g)^{1/3}`$ is the critical depth.
- $`h_\mathrm{harm}`$: the harmonic mean of the depths on both sides.
- $`w = \min(\max(\sigma/h_r, 0), 1)`$ ($`h_r`$ is the depth of the receiver).

**Why the velocity head of the entering flow.** 1 and 2 take the velocity head
from the velocity of the edge itself, but the velocity of an edge closed by
the cap is reset to 0 every step, so whether the edge opens depends on the
time step, and water enters all at once at the moment it opens (the steps of
examples 1 and 2 in §5.2). 3 uses the velocity head of the entering flow, which has
a value even while the edge is closed, so water starts to enter thinly when
the energy head of the sender reaches the bed of the receiver and increases
continuously with the water level. There is no transition (§5.2). For a bank
pocket directly ahead of the flow, the difference in the water level at the
onset of spilling between time steps of 6 s and 1.5 s is 0.001 m against
0.14 m with 2, and the rise of the depth in the minute of opening is 0.08 m
against 0.5–0.9 m ([test/bankspill](../../../test/bankspill/en/README.md)).

**The first term is a floor for submerged steps.** It is the harmonic mean
when the water level of the receiver is not above that of the sender. It is
nearly the mean of both sides for a gentle step, and close to 0 when the
receiver holds only a thin film. Without the floor a wave travelling up a
gentle slope becomes slower.

**Flow parallel to the bank.** There is no velocity head toward the bank, so,
as with 2, water does not climb onto a bank above the water level
([test/bankcap](../../../test/bankcap/en/README.md)).

## 4. Limits of 3

- **The rise of the water surface at the outer bank of a bend.** How much the
  water surface rises at the outer bank of a bend cannot be resolved by a
  one-cell-wide channel; what is satisfied is only that the level in the
  pocket does not exceed the energy head upstream.
- **Where a supercritical flow meets a high cell head-on.** Where a
  supercritical flow (a Froude number above 1) meets a high cell head-on, for
  example at a bend just below a drop, the entering flow is counted not by its
  velocity head itself but by the specific energy of the critical flow of the
  same discharge (which is determined by the discharge alone and is smaller
  than the actual specific energy; the height to which a supercritical flow
  runs up a bank directly ahead is counted on the low side). The velocity head
  is not counted as it is because the "speed of the entering flow" is taken as
  the discharge divided by the depth of the sender. For the same discharge,
  the gradient of the specific energy $`h + q^2/2gh^2`$ with respect to depth
  is $`1 - Fr^2`$, which is negative in a supercritical flow, so a slight
  change in depth changes the velocity head greatly in the opposite direction.
  If it is counted as it is, where a flow that has fallen over a drop meets a
  hillslope cell 8 m above the water level, the edge opens and closes and the
  discharge in the pool just downstream oscillates
  ([test/chutepool](../../../test/chutepool/en/README.md)). Even when it is
  counted by the specific energy of the critical flow, where a supercritical
  flow meets a bank, water climbs onto bank cells above the water level of the
  channel (in a run on the 100 m grid of the Chichibu basin, there are 3
  places where about 1 m of water sits on a cell 3–9 m above the maximum water
  level of the adjacent channel).
- **Runs where a movable bed reaches a free-outflow boundary.** With 3,
  erosion from the downstream end advances more easily than with 2 (with 2,
  the flow that crosses the sill of sediment deposited at the downstream end
  with the mean depth of both sides keeps the sill). Make the last few columns
  at the downstream end a non-erodible bed (a distribution with soil thickness
  0; `f_sdtype = 1` and `fn_sd`;
  [test/sedfeed](../../../test/sedfeed/en/README.md)).
- **Differences from 2.** Compared with 2, the results with 3 change; for
  example, the downstream peak falls by the amount that the step at the onset
  of spilling had added (how to reproduce earlier results is in §6).

## 5. 1 and 2 (the earlier defaults)

### 5.1 1: caps only while the receiver is dry

1 caps only while the receiving cell is dry. Once the cells of a bank or of
the land behind it are thinly wet (rain, the film left after the water has
receded), the cap is lifted, and channel water whose level is below the bank
can climb onto the wet bank (in a flowing incised channel, the bank row with a
2 cm film rises to 7–15 cm;
[test/bankcap](../../../test/bankcap/en/README.md)).

### 5.2 2: also applied to a wet receiver

2 applies the same cap also when the receiver is wet, as long as its bed is
above the water level of the sender, and stops this (it is not applied to a
submerged step, that is, where the bed of the receiver is below the water
level of the sender; in runs with the debris-flow model `f_debris`, the
surface of the flow = bed + water depth + solid thickness is used in place of
the water level of the sender).

**The transition at the threshold.** While the water level of the sender is
just below the bed of the receiver, the cap is joined to "no cap" by a
transition (with a slope such that the water level does not overshoot the
threshold in one step; without it, when the water level sits at the height of
the bed of the receiver, the cap flips on and off every few steps. The width
of the transition is proportional to the normal velocity and to the time step,
and within it a small amount flows while the water level is still below the
bed of the receiver. The formula is in
[test/bankcap](../../../test/bankcap/en/README.md)).

**The width of the transition and the step at the onset of spilling.** In a
deep, fast channel solved with a large time step the transition becomes wide
(on the 200 m grid of Chichibu with a time step of 6 s and a channel 7 m deep,
0.2 m per 1 m/s of normal velocity; with a 50 m wide sub-grid channel on the
same grid and a time step of 4 s, 0.7 m). Once the inflow onto a higher cell
starts, the normal velocity rises and the transition widens, so the water
levels at which the inflow starts and stops differ, and the discharge can
change like a step within one or two minutes when it starts or stops. Examples
(both computed on the 200 m grid of the catchment of the
[chichibu tutorial](../../../tutorials/chichibu/en/README.md), with the
depression-filled elevation (`Chichibu_200m_filled`) and a channel roughness
of 0.02, with 2 combined with `f_advection_lateral = 0`, the defaults until
2026-11-16):

1. The inflow onto the high cell on the outer side of a channel bend starts
   with the channel level 0.2 m below the bed of the receiver and continues
   for 18 minutes until it is 0.5 m below, and the discharge at a transect
   600 m upstream rises by 4 % in two minutes (time step 6 s; with a time step
   of 3 s it does not start, and the peak at that transect is 4 % lower).
2. With a 50 m wide sub-grid channel, water starts to enter a bank cell while
   the channel level is still 1.1 m below the bed of the bank, and the step in
   which the downstream discharge drops by a fifth in one minute comes
   17 minutes earlier than in a run with a time step of 1 s (time step 4 s;
   the peaks agree within 1 %).

These steps do not appear with the default 3.

### 5.3 A limit of 2 (steep stepped channels)

Where a supercritical flow runs up onto a low bank directly ahead or on the
inside of a bend (a cell 10–15 m above the bed) and returns to the channel,
the head of the flow can exceed the water level upstream (the velocity becomes
too large). In a run on a reach cut out of the 50 m grid of Chichibu, where
the bed descends from 354 m to 268 m, with a discharge of up to 8,000 m³/s
given at the upstream end, with 2 and dry banks the bed elevation plus the
velocity head exceeds the water level at the upstream end by 45 m (maximum
velocity 49 m/s). When the banks are wet from rain, the brake of the water
film under `f_advection_lateral = 0` acts and there is no excess (24 m/s), but
`f_advection_lateral = 1` does not count the water film, so the head exceeds
it by 22 m even with rain (44 m/s; §4.4 of
[Advection schemes](advection.md)). With 3 the excess is within 5 m whether
the banks are dry or wet and whatever `f_advection_lateral` is, about the same
as on a terrain where the bank cells are turned into walls (6 m)
([test/cascade](../../../test/cascade/en/README.md)). It appears when the
run-up onto banks is counted by the edge's own velocity alone (a strong
restriction), but why it does so has not been identified
(developer.md §110.29).

## 6. Reproducing earlier results

| What to reproduce | Setting | Note |
|---|---|---|
| Cases computed or calibrated with versions until 2026-11-16 | `f_dry_head_cap = 2` (together with `f_advection_lateral = 0`) | the treatment of side faces is in §4.4 of [Advection schemes](advection.md) |
| Cases computed or calibrated with versions until 2026-11-13 | `f_dry_head_cap = 1` | in rain-wetted steep valleys (rainfall runoff on a real DEM) and at run-up fronts the results differ between 1 and 2 (the differences in the Chichibu regression case are in [test/chichibu](../../../test/chichibu/en/README.md)) |
| Cases calibrated with versions before 2026-10-03 | `f_dry_head_cap = 0` (together with `f_advection_scheme = 1` and `f_opening_dynamic = 0`) | the choice of schemes in §5 of [Advection schemes](advection.md) |

## 7. Verification cases

- **[test/bankcap](../../../test/bankcap/en/README.md)** -- a flowing incised
  channel and a thinly wet bank. Channel water below the bank does not climb
  onto it (2 and 3), and the discharge does not flip at the threshold of the
  cap. The formula of the transition of 2.
- **[test/bankspill](../../../test/bankspill/en/README.md)** -- what happens
  when the channel level rises slowly and water starts to spill into a bank
  pocket. The onset of spilling does not depend on the time step (3); the
  limit of 2 is recorded.
- **[test/chutepool](../../../test/chutepool/en/README.md)** -- a supercritical
  flow that has fallen over a drop turns and plunges into a deep pool. The
  discharge in the pool does not oscillate (the reason for counting the
  entering flow by the specific energy of the critical flow; §4).
- **[test/cascade](../../../test/cascade/en/README.md)** -- a steep channel
  where drops and flat reaches alternate. The head of the flow does not exceed
  the water level at the upstream end (3); the limit of 2 is recorded (§5.3).
- **[test/sedfeed](../../../test/sedfeed/en/README.md)** -- a run where a
  movable bed reaches a free-outflow boundary (§4).
- **[test/chichibu](../../../test/chichibu/en/README.md)** -- the regression
  case on real terrain. The difference between 1 and the later options.

## Related pages

- [Advection schemes](advection.md) -- the neighbouring switches that interact
  with the advection term (§5), the treatment of side faces
  `f_advection_lateral` (§4.4)
- [ENC grid and time integration](encgrid.md) -- the edge depth and the
  continuity equation
- [Shallow water flow computation](swflow.md) -- the list of the parameters of
  `&list_enc` and their defaults
- docs/developer.md §68.16, §108, §110.24, §110.30 and §110.32 (records of
  the design, prototypes and verification; in Japanese)

## References

[^bates10]: Bates, P. D., Horritt, M. S. and Fewtrell, T. J. (2010): A simple inertial formulation of the shallow water equations for efficient two-dimensional flood inundation modelling. *J. Hydrol.*, 387, 33–45. (the flow depth between cells taken as the higher water level minus the higher bed level; the original has not been checked)
