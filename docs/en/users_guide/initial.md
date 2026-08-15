# Initial conditions (&list_initial)

> English mirror of docs/users_guide/initial.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Gives the water depth, water level, and velocity at the start of the
computation (t = t0). Enabled via `fn_initial`. If not specified, the
whole domain starts dry (h = 0) -- for computations where water enters
through rainfall runoff or river inflow, that is often sufficient.

```
&list_initial
  h0 = 1.0                       ! still water with an initial depth of 1 m
/
```

## How depth / water level is given (f_htype)

| f_htype | How it is given | Parameters used |
|---|---|---|
| 0 (default) | fixed water depth | h0 |
| 1 | water depth distribution file | fn_hinit |
| 2 | fixed water level (h = max(e0 - z, 0)) | e0 |
| 3 | water level distribution file | fn_hinit |

| Parameter | Default | Meaning |
|---|---|---|
| h0 | 0 | initial water depth (m) |
| e0 | 0 | initial water level (m; same elevation datum as z) |
| fn_hinit | "" | distribution file of the initial depth/water level (f_htype=1, 3) |
| h0_rw | 0 | additional initial depth on channel mask cells (m) (pre-wet the channel at normal flow) |
| u0 / v0 | 0 | initial velocity (m/s) (f_uvtype=0: uniform value only) |
| f_fill_depres | 0 | depression filling. 0: none, 1: fill all depressions with water, 2: fill channel cells only, 3: fill channel cells only, then convert that water into ground elevation (fill with terrain) |
| f_user_routine | "" | user routine that modifies the initial field (for idealized experiments) |

- The "water level" specification (f_htype=2, 3) gives a water surface
  elevation relative to the terrain, and suits the initialization of
  lakes, reservoirs, and the sea surface. Ground higher than the water
  surface stays dry. The reference water level of the long-wave
  radiation edge boundary (type 2) matches automatically if the initial
  condition is a constant water level ([boundary conditions
  chapter](boundary.md)).
- `f_fill_depres` fills terrain depressions (hollows without an outlet)
  before the computation starts. 1 fills all depressions with water,
  skipping the warm-up phase in runoff computations where "runoff does
  not start until the depressions are full". 2 fills only channel
  cells with water, removing spurious depressions (pits) that remain in
  the channel long-profile of coarse terrain data. 3 performs the
  filling of 2 and then replaces the water with ground elevation,
  raising the river bed itself to erase the depressions (when you do
  not want the initial water volume in the water budget). 2 and 3
  require the channel mask fn_rw. None of them fill depressions that
  can drain to the sea.

## Using a warmed-up field as the initial condition

When you want to start from a realistic "flowing field" beyond what the
parameters can express, a saved state from a warm-up run can be read as
the initial condition (`f_state_restore = 2`). A typical use is to run
normal flow through the channel first and then start the flood
scenario. See the [suspending and restarting chapter](restart.md).

## Examples

- Annotated list of all parameters: [examples/List_samples/list_initial.txt](../../../examples/List_samples/en/list_initial.txt)
- Still water + a water-level mound from a user routine: [tutorials/wave](../../../tutorials/wave/en/README.md)
- Starting from dry ground + rainfall/inflow: the real-terrain examples ([examples/](../../../examples/))
