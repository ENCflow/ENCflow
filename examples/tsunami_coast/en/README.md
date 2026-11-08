# tsunami_coast — coastal subsidence and uplift versus the offshore fault tsunami, with their time lag (fn_bedmotion)

> English mirror of examples/tsunami_coast/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The ground deformation of a fault reaches not only the offshore seabed but also
the coast and the land. In the Tohoku-oki earthquake the coast subsided by
0.5–1 m, and in the Kanto earthquake the Sagami Bay coast was uplifted by 1–2 m.
[fn_bedmotion](../../../docs/en/users_guide/bedmotion.md) moves the bed
elevation z as a time history without distinguishing land from sea (the water
column h is unchanged and the water surface moves together with the bed), so
**the positive wave heading into the subsided area, the wave spreading from the
uplifted area and the flooding of the subsided plain** are computed in the same
run as the tsunami from the offshore fault. This example compares three cases
on an idealised coast with a bay. No code changes (settings only).

## Setup

- Domain 120 km × 80 km, Δx = Δy = 500 m. Land to the west (coastline at
  x = 20 km); at y = 30–50 km a bay 12 km deep (head at x = 8 km; depth
  2 → 25 m). A shelf (25 → 200 m, x = 20–40 km) and a slope (→ 1000 m at
  x = 80 km). The land is a coastal plain of 0.5 m/km for 5 km from the
  waterline (with 0.6 m of subsidence, 1.2 km goes below sea level). East,
  north and south are long-wave radiation boundaries; the "solved sea"
  configuration (f_htype=2, still-water level 0).

![Setup](figs/setup.png)

(a) Plan (north up). On the terrain, the surface projections of the three
fault planes (rectangles; the thick line is the top edge and the triangles
point down-dip) and probes 1–7. The west is a wall; east, north and south are
radiation boundaries. (b) Section along the bay axis (y = 40 km). Top: the
terrain (depths beyond 10 m compressed logarithmically); bottom: the fault
planes (vertical and horizontal scales nearly equal; the splay fault 3 is the
section at y = 15 km overlaid). All are reverse faults, with the hanging wall
(west side) moving up-dip. Drawn from the input files (z.txt and
fault2disp_all.txt); not computed results.

- Faults ([fault2disp_all.txt](../fault2disp_all.txt) → bm/; strike N–S, dipping west):

| Segment | Position and geometry | Slip | Time | Effect |
|---|---|---|---|---|
| 1 deep (beneath the coast) | upper edge x = 60 km, depth 8 km; width 40 km; dip 20° | 5 m | t = 0, 20 s | coast to bay subsides 0.4–0.6 m; the outer shelf and slope (x ≈ 40–65 km) are uplifted 0.9–2.2 m (with the subsidence from the offshore fault, the final displacement is 0.7–1.4 m at x ≈ 40–61 km and turns into subsidence seaward of 64 km) |
| 2 shallow (offshore) | upper edge x = 100 km, depth 5 km; width 30 km; dip 15° | 8 m | t = 30 s, 20 s | main tsunami (3.4 m uplift offshore, −1.4 m subsidence) |
| 3 splay fault (south of the bay mouth) | upper edge x = 22 km, y = 15 km, depth 1 km; width 8 km; dip 60° | 2 m | t = 0, 10 s | the cape and the surrounding shelf are uplifted by up to 1.0 m (with the subsidence from the deep segment, the final displacement is up to 0.6 m) |

![Ground displacement](figs/deformation.png)

(a) Final ground displacement of the three faults together (red = uplift,
blue = subsidence). (b) Displacement along the bay axis by source: the coastal
faults 1 and 3 (the difference between bm/ and bm_off/) and the offshore fault
2 (bm_off/). The deep fault 1 lowers the coast and bay by 0.4–0.6 m and raises
the outer shelf and slope by up to 2.2 m, but that area overlaps the
subsidence of the offshore fault 2, and the final displacement there is 1.4 m.
Drawn from the fault2disp output bm/ and bm_off/; not computed results.

| Case | Settings | Meaning |
|---|---|---|
| With time history | param_full.txt (bm/bmlist.txt; 11 snapshots at 5 s intervals) | the intended use of fn_bedmotion |
| Instantaneous displacement | param_inst.txt (the final displacement at t = 0) | the same as the conventional "shift the initial water level and bed to their post-event values" |
| Offshore fault only | param_offshore.txt (bm_off/; segment 2 only) | the case where the coastal ground deformation is ignored |

```
make                        # links, z.txt, bm/ (fault2disp), bm_off/
python3 plot_schematic.py   # explanatory figures figs/setup.png, deformation.png, mechanism.png (can be drawn before the runs)
./encflow param_full.txt    # about 30 s each (gfortran, 4 threads; dt = 1.5 s, 60 min)
./encflow param_inst.txt
./encflow param_offshore.txt
python3 plot_results.py     # result figures figs/probes.png, snapshots.png and tables
```

With the argument `en`, the figures are drawn with English labels into
en/figs/ (`python3 plot_schematic.py en`, `python3 plot_results.py en`).
Plotting needs Python 3, NumPy and matplotlib.

## How it works

![How it works](figs/mechanism.png)

(a) Time history of the ground displacement that fn_bedmotion reads (11
snapshots every 5 s in bm/). Faults 1 and 3 move at t = 0–20 s and the
offshore fault 2 at t = 30–50 s. The crest of the slope uplift (x = 58 km)
rises 2.2 m by 20 s and drops to 1.4 m with the subsidence of fault 2. The
dashed lines are the instantaneous case (the final displacement given at
t = 0). (b) The rule of fn_bedmotion: the ground height z is moved and the
water column h is kept, so the water surface moves with the ground. Seabed
uplift becomes a wave as a raised water surface, subsidence of the bay floor
draws water in from around (a flood wave), and subsidence of the land floods
the plain now below sea level. (c) Travel time along the bay axis to the
coast (bay mouth) at the long-wave speed √(gh), with the final ground
displacement (right axis). It takes 15.9 min from the crest of the slope
uplift and 23.3 min from the crest of the offshore uplift, close to the two
peaks at the bay-mouth probe (15.9 and 23.9 min). Drawn from the inputs and
formulas; not computed results.

## Results

![Probes](figs/probes.png)

Water level (z + h) at the seven probes. ▲ marks the arrival (the time at
which the change in depth exceeds 0.1 m; at the land probe, the start of
flooding). The water surface moving with the ground shows up as a step right
after the ground moves (−0.6 m at the bay head, +0.7 m at the cape). At the
bay mouth, ① is the wave from the coastal deformation (absent in the
offshore-only case) and ② the tsunami from the offshore fault. For the land
at the bay head (7), the line shows the ground height until it floods (in
the time-history case it drops from 0.38 m to −0.18 m).

![Water-level distributions and flooding](figs/snapshots.png)

Water level in the time-history case (t = 2, 5, 10, 20 and 30 min; the black
line is the coastline before the motion) and the maximum flood depth on land
around the bay. At t = 2 min the bay surface has dropped about 0.6 m with the
ground, and the uplift of the outer shelf and slope and the offshore uplift
appear as raised water surfaces.

| Probe | With time history: arrival (min) / max / min (m) | Instantaneous displacement: arrival / max / min | Offshore fault only: arrival / max / min |
|---|---:|---:|---:|
| Bay head x = 9 km (depth 4 m) | 18.2 / 4.29 / -1.17 | 18.1 / 4.19 / -1.14 | 25.1 / 3.63 / -0.99 |
| Bay mouth x = 20 km | 4.0 / 3.78 / -1.96 | 3.8 / 3.05 / -2.11 | 12.0 / 4.12 / -2.01 |
| Coast outside the bay (north) y = 65 km | 2.7 / 2.58 / -1.89 | 2.6 / 2.61 / -1.79 | 10.1 / 2.46 / -1.15 |
| Coast of the southern cape y = 15 km (uplifted area) | 0.5 / 2.68 / -1.98 | 0.5 / 2.73 / -1.89 | 10.1 / 2.51 / -1.17 |
| Shelf x = 40 km | 3.3 / 2.33 / -1.35 | 3.8 / 1.66 / -1.50 | 3.8 / 3.09 / -1.05 |
| Above the offshore fault x = 90 km | 1.4 / 2.14 / -0.94 | 0.8 / 2.13 / -0.88 | 1.5 / 2.07 / -1.53 |
| Land at the bay head x = 7 km (flooded by subsidence) | 27.5 / 2.76 / -0.18 | 27.4 / 2.84 / -0.18 | 38.9 / 2.49 / 0.37 |

Arrival = the time at which the change in depth exceeds 0.1 m (motion together
with the bed does not change the depth, so only the waves and the inflow are
picked up; at the land probe, the start of flooding). The maximum flood depth on
the land at the bay head is 2.94 m with time history, 3.02 m instantaneous and
2.12 m offshore only. The flooded land area is 301 / 299 / 266 km².

- **With the coastal deformation included, the disturbance in the bay and on
  the coast starts 7–8 minutes earlier.** With the offshore fault only, the
  arrival at the coast takes 10 min (bay mouth 12 min, bay head 25 min), but when
  the subsidence beneath the coast and the uplift of the outer shelf occur at
  t = 0, the water level starts moving at 2.7 min on the coast, 4.0 min at the
  bay mouth, 18 min at the bay head and 0.5 min at the cape (uplifted area). In
  the time series at the bay mouth and on the coast outside the bay, the first
  slow positive wave (1.3–1.5 m, 14–16 min) is the inflow into the subsided area
  and the wave from the uplift of the shelf, and the sharp wave at 23–24 min that
  follows is the tsunami from the offshore fault. At the bay head these two
  arrive at 29 and 37 min.
- **Flooding of the subsided plain**: at the bay head the water surface first
  drops with the subsidence (−0.6 m), and its recovery by inflow from the
  surroundings becomes a positive wave as it is. The land at the bay head floods
  from 27.5 min (38.9 min with the offshore fault only), with a maximum flood
  depth of 2.9 m (2.1 m offshore only). The subsided land (ground 0.38 →
  −0.18 m) lies below sea level, and water remains after the tsunami has
  receded (level 0.72 m, depth 0.90 m at 60 min). In the offshore-only case the
  ground stays above sea level (0.37 m), and the depth of 0.63 m (level
  1.00 m) at 60 min is water still draining away.
- **Response inside the bay**: the inflow into the subsided area and the
  offshore tsunami overlap inside the bay, and the maximum level at the bay head
  is 4.3 m (3.6 m offshore only). At the bay mouth the time-history case gives
  3.78 m against 3.05 m for the instantaneous displacement (+24%), and on the
  shelf 2.33 m against 1.66 m (+40%): **even a 30-second lag in the start of
  the motion changes how the waves overlap**. This is because the phase
  difference between the waves of the deep segment (t = 0) and the shallow
  segment (t = 30 s) interferes on the shelf. The instantaneous displacement
  (the conventional method) roughly reproduces the arrival times and the
  maximum levels at the bay head, on the coast and at the cape (within 2%), but
  gives 20–30% lower levels at the bay mouth and on the shelf. Note that the
  maximum levels at the bay mouth and on the shelf are highest in the
  offshore-only case (bay mouth 4.12 m against 3.78 m, shelf 3.09 m against
  2.33 m). Depending on how they overlap with the waves from the coastal
  deformation, the crests of the offshore tsunami become lower in places, so
  including the coastal deformation does not always raise the water level.
- The uplift of the cape (segment 3) emits a local positive wave at 0.5 min,
  which becomes the first wave on the southern coast (a 1.5 m rise after a
  −0.6 m drawdown).

## Notes

- Cells in the sea mask (sw > 0) do not move their bed, so the tsunami
  computation uses the "solved sea" configuration (f_htype=2).
- The inflow into the subsided area appears as a recovery of the water level
  over several minutes rather than as a "wave". It changes greatly with the
  coastal topography (levees, river mouths, slope of the plain) and the grid
  resolution.
- The time history of the displacement model (t_r and the rise of each segment)
  is often poorly known for real earthquakes and is an assumption here.
- The spatial scale of the deformation (tens of km) is much longer than the
  depth, so the hydrostatic approximation suffices. In the near field of short
  displacements (splay faults, submarine landslides) use the non-hydrostatic
  f_nh_bottom.
