# source_area — growth and shrinkage of the runoff source area of a mountain catchment

> English mirror of examples/source_area/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Most of the rain that falls on a forested mountain catchment does not run over the ground: it
infiltrates into the soil. The infiltrated water flows downslope inside the soil layer, gathers
in the valleys, and comes out at the surface where the soil has filled up (the saturated area)
to become streamflow. Only part of the catchment produces runoff; that part spreads from the
valleys onto the slopes during rain and shrinks after the rain stops (the variable source
area). This example puts the same storm twice on a 35 km² headwater catchment cut out of the
real terrain of Chichibu and looks at two things.

1. **Process run**: infiltration → lateral flow in the soil → saturated area → channel routing
   are linked in a single run, to see the growth and shrinkage of the saturated area, the
   hydrograph at the catchment outlet, and the difference between rain on dry soil and rain on
   wet soil.
2. **Can surface flow alone stand in for it?**: the same rain is computed with "no infiltration
   (all rain runs over the surface)" and with "vertical infiltration only (no lateral flow in
   the soil)" and compared with the process run, to examine whether a larger slope roughness
   (an equivalent roughness) can represent the delay of runoff caused by the passage through
   the soil.

The terrain is a real catchment, but the soil layer, the conductivities and the rain are
schematic uniform values; this is not a reproduction of the runoff of this catchment (nothing is
compared with observations).

## What happens in real mountain catchments

- **Rain infiltrates and flows inside the soil**: forest soils have a high infiltration
  capacity, and rain of ordinary intensity does not run over the ground. From the records of
  small forested catchments in the eastern United States, Hewlett & Hibbert (1967) argued that
  subsurface flow predominates even in storm runoff and that separating a hydrograph into
  overland flow, interflow and base flow has little meaning for small catchments. Hillslope
  soils contain large pores and pipes, so the effective downslope conductivity is one to two
  orders of magnitude larger than that of the soil matrix (Mosley 1979; Beven & Germann 1982).
- **The source area grows and shrinks**: only part of a catchment produces runoff, and that
  part changes during a storm and with the season (the variable source area). In a small
  catchment in Vermont, Dunne & Black (1970) observed that storm runoff came mainly from
  overland flow on the saturated area, which occupied a small share of the catchment (including
  rain falling directly on it), and that this area expanded and contracted with the season and
  during storms.
- **Places where water gathers saturate first**: the soil fills more easily where the upslope
  contributing area is large and the slope is gentle. TOPMODEL (Beven & Kirkby 1979) expresses
  this relation with a topographic index and computes the extent of the source area from it.
  Thin soil fills with less rain, so the distribution of soil depth also sets the order of
  saturation (Tani 1997).
- **Nothing comes out until the wet patches connect**: subsurface flow from a hillslope often
  rises abruptly once the storm total exceeds a certain amount. On a hillslope at Panola,
  Georgia, Tromp-van Meerveld & McDonnell (2006) showed that the flow increased by orders of
  magnitude beyond 55 mm of rain, when the depressions of the bedrock surface had filled and
  the saturated patches connected down to the foot of the slope (fill and spill).
- **Engineering runoff calculations often treat hillslope flow as overland flow**: the
  kinematic wave method (also called the equivalent roughness method in Japan) solves the flow
  of rainwater on slopes as Manning-type overland flow and gives the roughness a value larger
  than that of the real ground surface (the equivalent roughness), so that it also covers the
  delay caused by the passage through the soil. The amount of rain that becomes runoff (the
  effective rainfall) is determined separately. According to documents of the Ministry of
  Land, Infrastructure, Transport and Tourism that quote the table of the Technical Criteria
  for River Works (survey volume), the standard value of the equivalent roughness is 0.4–0.8
  m⁻¹ᐟ³ s for mountain catchments with good forest cover, and one application uses 0.6 for
  mountains (both confirmed from search excerpts; the originals were not checked). Manning's
  roughness of the thin sheet flow that actually runs over the ground is tabulated as
  0.15–0.41 for grass and 0.4–0.8 for woods (Table 3-1 of USDA 1986, compiled from Engman
  1986; values confirmed from a search excerpt, the table itself was not checked).
- **A yardstick for the speed of storm runoff**: an empirical formula for the flood
  concentration time of small and medium rivers (the time for rain on the most distant part
  of the catchment to reach the outlet) is tp = C A^0.22 re^-0.35 of Kadoya & Fukushima (1976)
  (tp in minutes, A the catchment area in km², re the effective rainfall intensity in mm/h;
  C = 290 for forested hills and mountains). For the catchment (35 km²) and the rain
  (10 mm/h) of this example it gives 4.7 hours (the formula and the coefficient were confirmed
  from a search excerpt of a paper that quotes them; the original was not checked).

## Mechanisms needed to reproduce it

![Differences between the three runs](figs/mechanism.png)

Schematic cross-sections of a hillslope (not computed results). (a) Process run. Rain
infiltrates into the soil and flows downslope in the saturated zone that forms on the base of
the soil (the bedrock surface). Where the saturated zone reaches the ground surface is the
saturated area: rain falling there cannot infiltrate and runs over the surface, and groundwater
coming from upslope seeps out. (b) No infiltration. All rain runs over the surface, and only
the slope roughness delays the runoff. (c) Vertical infiltration only. Rain is stored in the
soil column of each cell and does not move sideways; nothing runs off until the soil is full.

| Real phenomenon | Representation in ENCflow | Settings |
|---|---|---|
| Rain infiltrates into the soil | Green-Ampt infiltration (constant capacity 200 mm/h). The soil stores up to 0.5 m × effective porosity 0.2 = 100 mm | `f_gwvertical = 2`, `gw_ksv_mmh`, `sd0`, `sy0` |
| Soil water flows downslope and gathers in the valleys | Lateral flow in the soil (Darcy flow in the saturated zone; nonlinear Boussinesq, 8 neighbours) | `f_gwlateral = 1`, `gw_ksh_mmh` |
| Where the soil is full, rain cannot infiltrate and groundwater seeps out | Infiltration is limited to the remaining capacity of the soil. Water that exceeds the capacity through lateral flow is handed to the surface water in the same step (return flow) | Works when the two above are enabled |
| Surface water flows down the valleys and channels | Shallow-water flow (dynamic wave). Different roughness for slopes and channel cells | `rn0`, `rn0_rw`, channel mask `fn_rw` |
| Water running over the surface infiltrates into soil that is not yet full | Infiltration acts every step on every cell that has surface water (rain and water arriving from upstream are not distinguished) | Same as above |
| Water leaves the catchment at the outlet | The single cell at the downstream end of the valley is kept empty with a prescribed stage (a complete drain) | `&list_bound_stage` |

The three runs to be compared share the terrain, the channels, the rain, the outlet and the
time step; only the treatment of the soil differs.

| Run | Infiltration | Lateral flow in the soil | Parameter file | Change from the process run |
|---|---|---|---|---|
| Process run | yes | yes | `param.txt` | — |
| Vertical infiltration only | yes | no | `param_vertical.txt` | `f_gwlateral = 0` |
| No infiltration | no | — | `param_surface.txt` | no `fn_gwflow` line (groundwater is not enabled) |

The equations and settings of each mechanism are in the user guide:
[Groundwater](../../../docs/en/users_guide/gwflow.md) and
[Groundwater models](../../../docs/en/users_guide/gwflow_models.md) (Green-Ampt in §3, lateral
flow in §4), [Shallow-water flow](../../../docs/en/users_guide/swflow.md) and
[Boundary conditions](../../../docs/en/users_guide/boundary.md).

## Geometry and settings

![Setup](figs/setup.png)

(a) Location within the Chichibu basin (the 50 m grid of test/chichibu). (b) Terrain and channel
cells of the extracted catchment. (c) Rainfall.

- **Catchment**: a headwater catchment at the western end of the Chichibu basin (the upper
  Arakawa River; the 50 m grid of [test/chichibu](../../../test/chichibu/en/README.md), 1120 × 600
  cells). The outlet is one cell in the valley of the southern (right-bank) tributary (cell
  (307, 308) of the source grid), 2.3 km upstream of the confluence of two tributaries, and
  the 13,896 cells (34.74 km²) upstream of it are cut out (a window of 172 × 143 cells). The
  outlet lies just upstream of two small tributaries that enter from the right and the left
  bank. The reach from there down to the confluence is left out of the catchment, because
  water ponds on a 1.5 km flat reach produced by the depression filling
  ([Starting points for sensitivity experiments](#starting-points-for-sensitivity-experiments)).
  Elevation is 757–2127 m and the median steepest slope is 0.76 (37°; 80 % of the cells lie
  between 0.40 and 1.01). The extraction is done by `make` (`make_catchment.py`), and the
  elevations are those of the source data, unchanged.
- **Flow tree and channel cells**: each cell drains to the steepest of its 8 neighbours (D8;
  O'Callaghan & Mark 1984); on the flats left by the depression filling the receiver follows
  the order of Priority-Flood (Barnes et al. 2014). The channel cells are the 730 cells of the
  source river mask (made from the rivers of the National Land Numerical Information) plus the
  16 cells passed when the flow tree is followed from each of them down to the outlet: 746
  cells (5.4 %) in all (the line of the river mask is offset by one cell from the valley line
  of the elevations in places and is interrupted there; see [Notes](#notes)).
- **Outlet and how the discharge is measured**: the outlet cell (153, 39) is a drain kept empty
  with a prescribed stage (a stage below the bed). The catchment consists of "the cells
  upstream of the valley cell (152, 39) just west of the outlet cell" and the outlet cell, so
  all water leaving the catchment enters the outlet cell from column i = 152. The discharge
  across a transect along this column is taken as the runoff from the catchment (every 10
  minutes).
- **Soil**: depth 0.5 m, effective porosity 0.2 (it can store 100 mm), infiltration capacity
  (vertical saturated conductivity) 200 mm/h, lateral saturated conductivity 3600 mm/h
  (1e-3 m/s). All are uniform, and both the soil and the channels are empty at the start. The
  soil depth and the lateral conductivity are schematic values chosen within the ranges the
  user guide suggests for forested catchments (soil 0.5–1.5 m, lateral 1000–10000 mm/h).
- **Roughness**: slopes 0.3, channel cells 0.05 (both schematic: the slope value is taken from
  the middle of the literature values for thin sheet flow given above, 0.15–0.41 for grass and
  0.4–0.8 for woods; the channel value is that of a mountain stream with cobbles and boulders).
- **Rain**: 10 mm/h × 12 hours = 120 mm, twice, at 0–12 h and 48–60 h (uniform over the
  catchment). The first storm falls on dry soil, the second on soil that still holds water
  from the first.
- **Computation**: dynamic wave at the surface, dt = 3 s, 96 hours. The limit depth `dd` and
  the lower bound of the depth in the friction term `dv` are 0.1 mm (so that thin flow on the
  slopes is not stopped; the default is 1 mm). Fields are written every hour.

| Case | Parameter file | Contents |
|---|---|---|
| Process run | `param.txt` | Infiltration + lateral flow in the soil. Slope roughness 0.3 |
| Vertical infiltration only | `param_vertical.txt` | No lateral flow. Slope roughness 0.3 |
| No infiltration | `param_surface.txt` | No groundwater. Slope roughness 0.3 |
| Sweep (15 cases) | `param_sweep_<case>.txt` (made by `sweep.py` from the three above) | No infiltration with slope roughness 1, 3, 5, 10, 30; no infiltration as a diffusion wave with roughness 0.3, 3, 10; vertical infiltration only with roughness 3; the process run with slope roughness 1, as a diffusion wave, with lateral conductivity 10000, 36000 and 100000 mm/h, and with soil depth 1 m |

## How to run

```
cd examples/source_area
make                      # links and inputs (make_catchment.py; a few seconds)
make run                  # the three basic cases, one after another
make sweep                # the 15 sweep cases, one after another
python3 plot_results.py   # figs/*.png and tables (argument en writes English figures to en/figs/)
```

Rough run times (gfortran -Ofast, a 4-core machine): the process run takes seven and a half
minutes with 3 threads. With 1 thread and four cases side by side, the process run takes
10–16 minutes, vertical infiltration only 23–30 minutes and no infiltration 25–33 minutes (no
infiltration, and vertical infiltration only once the soil is full, are heavy because water
lies on every cell). To run cases side by side, use `make -j 4 run OMP_NUM_THREADS=1` and
`make -j 4 sweep OMP_NUM_THREADS=1` (about 2 hours for the 18 cases). The results do not
depend on the number of threads (the process run
with 1 thread and with 3 threads gives byte-identical transect discharge, Log and groundwater
storage field at 12 h). `mechanism.png` and `setup.png` do not use computed results, so they
can be drawn after `make`, before any run. If the sweep is not finished, the figures and tables
are made from the cases that are.

## Results

### Process run: growth and shrinkage of the saturated area

![Distribution of the saturated area](figs/source_area.png)

Soil saturation (shade of grey) and the saturated area (blue) in the process run. Top row:
during and at the end of the first storm. Bottom row: 12 hours after the rain, just before the
second storm, and at the end of the second storm.

![Time series of the process run](figs/series.png)

(a) Rain (grey) and runoff from the catchment (black). Blue is the rain that fell on the
saturated area (rain × saturated fraction); the rest of the runoff is water that passed through
the soil. (b) Fraction of the saturated area. (c) Catchment-mean storage (the dashed line is the
soil capacity). (d) Cumulative rain and runoff. (e) Soil water versus the saturated fraction
(circles mark times; the axes run to the soil capacity of 100 mm and to the whole catchment,
100 %; the dotted line is the upper bound, where all soil water is in saturated cells). (f)
Fraction of saturated cells by class of upslope area on the flow tree.

| Storm | Soil water before the rain (mm) | Saturated area before the rain (%) | Time when runoff exceeds 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Max. saturated area (%) | Runoff in 48 h (mm) | Ratio to rain (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0 | 0.0 | 7.5 | 8.72 | 12.2 | 42.5 | 99.0 | 82 |
| 2 | 18.1 | 11.5 | 2.5 | 8.79 | 12.2 | 42.7 | 119.9 | 100 |

Times are measured from the start of each storm. The fraction of saturated cells by class of
upslope area (on the flow tree, counting the cell itself) is as follows.

| Class | Share of cells (%) | 5 h | 7 h | 12 h | 24 h | 48 h | 60 h |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 cell (ridge) | 39 | 0 | 1 | 6 | 1 | 0 | 6 |
| 2–9 cells | 44 | 1 | 19 | 54 | 10 | 2 | 54 |
| 10–99 cells | 11 | 20 | 90 | 100 | 89 | 45 | 100 |
| ≥ 100 cells (valley) | 5 | 64 | 100 | 100 | 100 | 100 | 100 |

- **Nothing saturates in the first 4 hours**: all rain infiltrates, and the catchment-mean soil
  water rises at the rain rate of 10 mm/h (40.0 mm at 4 h). There is no water on the surface and
  no runoff.
- **The saturated area spreads from the valleys onto the slopes**: in the fifth hour the valley
  cells, where groundwater from upslope gathers, fill first (64 % of the valley cells with an
  upslope area of 100 cells or more; 6 % of the whole catchment). The saturated area spreads
  onto the slopes while joining the valley lines into a dendritic pattern: 24 % at 7 h and
  42.5 % at 12 h, the end of the rain. At 12 h almost every cell with an upslope area of 10
  cells or more is saturated, while only 6 % of the ridge cells are. The catchment-mean soil
  water rises only to
  72 mm (72 % of the capacity of 100 mm), because the ridges and upper slopes never fill: the
  water that infiltrates there flows away downslope.
- **After the rain it shrinks from the upper slopes**: the saturated area shrinks to 20 % 12
  hours after the rain and to 11.5 % after 36 hours (just before the second storm). The valleys
  (100 cells or more) stay saturated, while the slopes with 2–9 cells return from 54 % to 2 %.
- **The same storage gives different saturated areas during growth and shrinkage**: when the
  catchment-mean soil water is 55–57 mm, the saturated area is 16 % during the first storm
  (6 h) and 29 % after the rain (16 h) (the path in (e) forms a loop). During the rain, water
  enters uniformly over the slopes; after the rain it has moved toward the valleys (the closer
  to the dotted line in (e), the more of the soil water sits in the saturated area: the
  saturated cells hold 28 % of the soil water at 6 h, 53 % at 16 h and 64 % just before the
  second storm). The catchment-mean storage alone does not determine the extent of the
  saturated area.
- **Outlet runoff rises once the saturated area has connected along the valleys**: in the
  first storm the runoff is practically zero until 6.5 h, then grows to 0.5 mm/h at 7 h,
  3.0 mm/h at 8 h and 6.1 mm/h at 9 h, and reaches 8.7 mm/h (87 % of the rain) at the end of
  the rain. For the two and a half hours between 5 h, when the saturated area starts to form,
  and 7.5 h, when the runoff exceeds 1 mm/h, the water leaving the saturated area infiltrates
  into downstream cells that are not yet full and travels down while filling the valleys and
  channels (the catchment-mean surface water is 8.0 mm at 7 h and 18.3 mm at 12 h; see
  [What this model does not represent](#what-this-model-does-not-represent-differences-from-the-real-phenomenon)).
- **Three quarters of the runoff is water that passed through the soil**: the rain that fell on
  the saturated area is 21 mm in the first storm and 30 mm in the second, 21 % and 25 % of the
  runoff in 48 hours. The rest infiltrated, flowed through the soil and seeped out in the
  saturated area. When the rain stops, the part supplied by rain on the saturated area
  disappears and the runoff halves in a little under four hours (4.1 mm/h at 16 h); after that
  it declines slowly with the drainage of the soil (1.9 mm/h at 24 h, 0.4 mm/h at 48 h).
- **In the second storm, on wet soil, runoff rises from the start of the rain**: before the
  second storm the saturated area is still 11.5 % and the soil holds 18 mm. Rain on the
  saturated area becomes runoff at once, and the runoff exceeds 1 mm/h after 2.5 hours (7.5
  hours in the first storm). The peak is almost the same as in the first storm, 8.8 mm/h, and
  the runoff in 48 hours equals the rain, 120 mm (99.0 mm in the first storm; the difference of
  21 mm is the water that first filled the dry soil and channels).

Where the water in the catchment is (catchment-mean depth in mm; 54 h and 56 h are the sixth
and the eighth hour of the second storm):

| Time (h) | Runoff (mm/h) | Soil water | of which in saturated cells | Surface water | of which on channel cells | Total |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0.00 | 40.0 | 0.1 | 0.0 | 0.0 | 40.0 |
| 6 | 0.01 | 56.7 | 16.2 | 3.3 | 1.7 | 60.0 |
| 8 | 3.01 | 65.4 | 29.9 | 13.0 | 8.5 | 78.5 |
| 12 | 8.70 | 72.1 | 42.5 | 18.3 | 12.0 | 90.4 |
| 24 | 1.94 | 36.3 | 20.0 | 7.2 | 5.5 | 43.5 |
| 48 | 0.43 | 18.0 | 11.5 | 3.1 | 2.6 | 21.1 |
| 54 | 3.94 | 59.1 | 22.8 | 11.6 | 8.2 | 70.7 |
| 56 | 5.89 | 66.1 | 31.7 | 14.8 | 10.0 | 80.9 |
| 60 | 8.78 | 72.2 | 42.7 | 18.4 | 12.1 | 90.6 |

- **With water running in the channels, the catchment holds 21 mm**: just before the second
  storm (36 hours after the rain) the outlet carries 0.43 mm/h (4.1 m³/s) and the catchment
  holds 21.1 mm of water: 18.0 mm in the soil (11.5 mm of it in the saturated cells of the
  valleys) and 3.1 mm on the surface (2.6 mm of it on channel cells). The difference in runoff
  between the first and the second storm (21 mm) is the water that first built up this
  storage. The amount is not constant: after the rain it decreases together with the runoff
  (43.5 mm and 1.94 mm/h 12 hours after the rain).
- **With the same water in the soil, a dry catchment does not yet deliver it to the outlet**:
  at 6 h of the first storm the soil holds 56.7 mm, but the surface holds only 3.3 mm and the
  runoff is 0.01 mm/h. In the sixth hour of the second storm (54 h) the soil water is almost
  the same, 59.1 mm, the surface holds 11.6 mm and the runoff is 3.9 mm/h. In the first storm
  the water has not yet spread through the dry valleys and channels.

Changing one setting of the process run at a time gives the following (`process_*` of
`make sweep`).

| Changed setting | Storm | Time above 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Runoff 12 h after the rain (mm/h) | Runoff in 48 h (mm) | Max. saturated area (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 1 | 7.5 | 8.72 | 12.2 | 1.94 | 99.0 | 42.5 |
| base | 2 | 2.5 | 8.79 | 12.2 | 1.94 | 119.9 | 42.7 |
| slope roughness 0.3 → 1 | 1 | 7.8 | 8.28 | 12.2 | 2.09 | 98.2 | 42.2 |
| slope roughness 0.3 → 1 | 2 | 2.8 | 8.42 | 12.2 | 2.09 | 119.9 | 42.5 |
| surface flow as a diffusion wave | 1 | 7.5 | 8.72 | 12.2 | 1.94 | 99.0 | 42.5 |
| surface flow as a diffusion wave | 2 | 2.5 | 8.79 | 12.2 | 1.94 | 119.9 | 42.7 |
| lateral conductivity 3600 → 10000 mm/h | 1 | 5.5 | 9.77 | 12.0 | 1.20 | 109.5 | 26.8 |
| lateral conductivity 3600 → 10000 mm/h | 2 | 3.0 | 9.78 | 12.0 | 1.20 | 119.9 | 26.8 |
| lateral conductivity 3600 → 36000 mm/h | 1 | 3.8 | 9.99 | 12.0 | 0.57 | 114.9 | 15.3 |
| lateral conductivity 3600 → 36000 mm/h | 2 | 2.8 | 9.99 | 12.0 | 0.57 | 119.9 | 15.3 |
| lateral conductivity 3600 → 100000 mm/h | 1 | 2.8 | 9.99 | 10.7 | 0.35 | 116.8 | 10.0 |
| lateral conductivity 3600 → 100000 mm/h | 2 | 2.5 | 9.99 | 10.7 | 0.35 | 119.7 | 10.0 |
| soil depth 0.5 → 1 m | 1 | 10.3 | 5.68 | 12.7 | 2.41 | 83.1 | 22.1 |
| soil depth 0.5 → 1 m | 2 | 2.0 | 6.77 | 12.3 | 2.45 | 119.8 | 23.2 |

- **The surface roughness and the flow equation hardly change the runoff of the process run**:
  raising the slope roughness from 0.3 to 1 lowers the peak by 5 % and delays the time of
  exceeding 1 mm/h by 0.3 hours. The run with the surface flow as a diffusion wave is the same
  as the base run to the precision of the table. The soil sets the delay of the runoff; the
  surface roughness matters only while the water flows over the saturated area and the valleys.
- **The conductivity and the depth of the soil change the runoff a great deal**: with a lateral
  conductivity about three times larger, groundwater reaches the valleys sooner, the rise
  advances from 7.5 to 5.5 hours and the peak rises to 9.8 mm/h (98 % of the rain). Because
  the slopes drain well, the maximum saturated area decreases from 43 % to 27 %. With 10 and
  about 28 times the conductivity (36000 and 100000 mm/h) the rise comes at 3.8 and 2.8
  hours, the runoff balances the rain during the storm (10 mm/h), and the saturated area
  stays on the valley floors, 15 % and 10 %. With a soil depth of 1 m, twice as much water
  is needed to fill the soil, the rise is delayed to 10.3 hours, and in a 12-hour storm the
  runoff does not rise fully: the peak is 5.7 mm/h (maximum saturated area 22 %).

### Comparison with no infiltration and vertical infiltration only

![Comparison of hydrographs](figs/compare.png)

(a) No infiltration, with the slope roughness n varied. (b) Vertical infiltration only. (c)
Runs with the surface flow as a diffusion wave (dashed). Black is the process run, grey the
rain.

![Roughness and indices](figs/roughness.png)

Slope roughness of the no-infiltration runs against the peak runoff (top), the time when the
runoff exceeds 1 mm/h (middle) and the fit to the process run (bottom: the coefficient of Nash &
Sutcliffe 1970 over the 48 hours of each storm; 1 is a perfect match, 0 is as good as using the
mean of the process run). The black horizontal line is the process run, green is vertical
infiltration only.

| Case | Slope roughness | Storm | Time above 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Runoff 12 h after the rain (mm/h) | Runoff in 48 h (mm) | Fit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| process run | 0.3 | 1 | 7.5 | 8.72 | 12.2 | 1.94 | 99.0 | — |
| process run | 0.3 | 2 | 2.5 | 8.79 | 12.2 | 1.94 | 119.9 | — |
| no infiltration | 0.3 | 1 | 1.8 | 10.00 | 5.7 | 0.12 | 119.7 | -1.57 |
| no infiltration | 0.3 | 2 | 1.8 | 10.00 | 5.7 | 0.12 | 120.0 | -0.41 |
| no infiltration | 1 | 1 | 2.7 | 10.00 | 10.3 | 0.29 | 119.2 | -0.94 |
| no infiltration | 1 | 2 | 2.5 | 10.00 | 10.3 | 0.29 | 120.0 | 0.08 |
| no infiltration | 3 | 1 | 3.8 | 10.00 | 12.0 | 0.80 | 117.1 | 0.15 |
| no infiltration | 3 | 2 | 3.3 | 10.00 | 12.0 | 0.79 | 120.0 | 0.68 |
| no infiltration | 5 | 1 | 4.7 | 9.84 | 12.0 | 1.31 | 114.4 | 0.68 |
| no infiltration | 5 | 2 | 3.8 | 9.87 | 12.0 | 1.31 | 120.0 | 0.86 |
| no infiltration | 10 | 1 | 6.0 | 7.12 | 14.2 | 2.49 | 105.7 | 0.73 |
| no infiltration | 10 | 2 | 4.0 | 7.79 | 12.8 | 2.49 | 119.9 | 0.72 |
| no infiltration | 30 | 1 | 17.8 | 1.85 | 30.0 | 1.62 | 56.4 | -0.26 |
| no infiltration | 30 | 2 | 0.2 | 3.73 | 20.5 | 3.56 | 118.2 | 0.12 |
| no infiltration (diffusion wave) | 0.3 | 1 | 1.8 | 10.00 | 5.5 | 0.12 | 119.7 | -1.58 |
| no infiltration (diffusion wave) | 0.3 | 2 | 1.8 | 10.00 | 5.7 | 0.12 | 120.0 | -0.42 |
| no infiltration (diffusion wave) | 3 | 1 | 3.8 | 10.00 | 12.0 | 0.79 | 117.1 | 0.13 |
| no infiltration (diffusion wave) | 3 | 2 | 3.3 | 10.00 | 12.0 | 0.79 | 120.0 | 0.67 |
| no infiltration (diffusion wave) | 10 | 1 | 6.0 | 7.12 | 14.0 | 2.48 | 105.7 | 0.74 |
| no infiltration (diffusion wave) | 10 | 2 | 3.8 | 7.79 | 12.8 | 2.48 | 119.9 | 0.73 |
| vertical infiltration only | 0.3 | 1 | 11.8 | 7.66 | 12.8 | 0.12 | 19.7 | -0.18 |
| vertical infiltration only | 0.3 | 2 | 1.8 | 10.00 | 5.7 | 0.12 | 120.0 | -0.41 |
| vertical infiltration only | 3 | 1 | 14.8 | 1.37 | 17.5 | 0.71 | 17.1 | -0.50 |
| vertical infiltration only | 3 | 2 | 3.3 | 10.00 | 12.0 | 0.79 | 120.0 | 0.68 |

Times are measured from the start of each storm. In the cases whose peak equals the rain,
10 mm/h, the runoff has levelled off in balance with the rain, and the "time of peak" is the
time when it levelled off. For roughness 30 the time of exceeding 1 mm/h in the second storm is
0.2 hours because the water of the first storm is still running off at a little over 1 mm/h.

The amount of water lying on the surface is as follows (the maximum catchment-mean storage, and
the depth on the cells other than channel cells at the end of each storm).

| Case | Slope roughness | Max. surface water (mm) | Mean depth at 12 h (mm) | Max. depth at 12 h (m) | Mean depth at 60 h (mm) |
|---|---:|---:|---:|---:|---:|
| process run | 0.3 | 18.4 | 6.7 | 0.79 | 6.7 |
| process run | 1 | 24.7 | 13.5 | 1.16 | 13.6 |
| process run (diffusion wave) | 0.3 | 18.3 | 6.6 | 0.79 | 6.7 |
| process run (lateral 10000 mm/h) | 0.3 | 18.2 | 5.8 | 0.82 | 5.8 |
| process run (lateral 36000 mm/h) | 0.3 | 17.0 | 4.5 | 0.82 | 4.5 |
| process run (lateral 100000 mm/h) | 0.3 | 16.1 | 3.5 | 0.82 | 3.5 |
| process run (soil 1 m) | 0.3 | 14.9 | 4.2 | 0.67 | 4.6 |
| no infiltration | 0.3 | 23.0 | 10.6 | 0.82 | 10.6 |
| no infiltration | 1 | 34.0 | 22.1 | 1.21 | 22.1 |
| no infiltration | 3 | 55.0 | 44.2 | 1.92 | 44.2 |
| no infiltration | 5 | 71.4 | 61.6 | 2.40 | 61.6 |
| no infiltration | 10 | 101.6 | 93.2 | 2.92 | 95.2 |
| no infiltration | 30 | 160.8 | 117.8 | 0.60 | 162.5 |
| no infiltration (diffusion wave) | 0.3 | 22.8 | 10.6 | 0.82 | 10.6 |
| no infiltration (diffusion wave) | 3 | 54.6 | 44.2 | 1.92 | 44.2 |
| no infiltration (diffusion wave) | 10 | 101.3 | 93.2 | 2.92 | 95.2 |
| vertical infiltration only | 0.3 | 23.0 | 10.5 | 0.81 | 10.6 |
| vertical infiltration only | 3 | 55.0 | 19.2 | 0.10 | 44.2 |

- **No infiltration with roughness 0.3 rises early and recedes early**: the runoff exceeds
  1 mm/h after 1.8 hours and in a little over 3 hours it has reached the rain rate of 10 mm/h
  and levelled off (the process run exceeds 1 mm/h after 7.5 hours and peaks at 8.7 mm/h).
  When the rain stops it recedes within a few hours: 0.1 mm/h after 12 hours (1.9 mm/h in the
  process run). The
  responses to the first and the second storm are the same. Because the water does not pass
  through the soil, there is neither the time needed to fill the dry soil nor the long recession
  fed by the drainage of the soil.
- **A larger roughness brings the delay and the recession closer to the process run**: the
  larger the slope roughness, the later the rise, the lower the peak and the gentler the
  recession. Of the six values tried, the closest to the process run is roughness 10 for the
  first storm (dry soil; fit 0.73) and roughness 5 for the second storm (wet soil; 0.86).
  Roughness 30 overshoots (the first peak is 1.9 mm/h, 18 hours after the end of the rain).
- **The roughness needed is 5–10, an order of magnitude above the equivalent roughness used in
  practice**: a roughness of 5–10 is 17–33 times the slope roughness 0.3 of the process run,
  an order of magnitude away from both the roughness of thin sheet flow (0.4–0.8 for woods)
  and the equivalent roughness used in practice for mountains (about 0.4–0.8). At the end of
  the rain the slope cells then carry 6–9 cm of water on average, and the catchment-mean
  surface water reaches 71–102 mm. This is about the same as the sum of the soil water (72 mm)
  and the surface water (18 mm) of the process run at the end of the rain, 90 mm. A large
  roughness delays the runoff by storing, as a thick layer of water on the surface, the water
  that the soil was storing.
- **The roughness needed is set by the amount of water the soil stores**: in the
  no-infiltration runs the depth on the slopes at the end of the rain grows with nearly the
  0.6th power of the roughness (table below; the normal depth of Manning flow,
  h = (n q / √I)^0.6, with q the discharge per unit width and I the slope). At the end of the
  rain the process run holds 77 mm on the slopes (cells other than channel cells), soil and
  surface together, and the roughness that holds this on the surface alone is
  0.3 × (77 / 10.6)^(5/3) = 8.2. The
  fitted roughness of 5–10 is what this relation gives. Storing twice the water takes 3.2
  times the roughness, so the roughness needed rises steeply with the water the soil stores.

| Slope roughness | 0.3 | 1 | 3 | 5 | 10 | 30 |
|---|---:|---:|---:|---:|---:|---:|
| Time to reach 50 % of the rain (h) | 2.5 | 3.3 | 5.5 | 7.2 | 10.8 | — |
| Time to reach 90 % of the rain (h) | 2.8 | 4.3 | 7.5 | 10.0 | — | — |
| Mean depth on the slopes at 12 h (mm) | 10.6 | 22.1 | 44.2 | 61.6 | 93.2 | 117.8 |
| Depth for roughness 0.3 × (n / 0.3)^0.6 (mm) | 10.6 | 21.8 | 42.2 | 57.3 | 86.9 | 167.9 |

Values for the first storm of the no-infiltration runs (— = not reached during the rain). The
depth is 5–7 % above the 0.6-power relation for roughness 3–10; for roughness 30 the runoff
has not yet balanced the rain at the end of the storm, so the depth is below it.

- **The shape still does not match**: roughness 5 nearly matches the time of the peak (12.0 h,
  against 12.2 h in the process run), but the peak is 13 % too high, the rise is too early
  (3.3 mm/h at 6 h, against 0.01 mm/h) and the recession is too fast (1.3 mm/h 12 hours after
  the rain, against 1.9 mm/h). Roughness 10 rises early (above 1 mm/h after 6.0 hours, against
  7.5 hours) and yet too gently (3.1 mm/h at 9 h, against 6.1 mm/h); the peak is 18 % too low
  and 2.0 hours late, and the recession is now too slow (2.5 mm/h). The runoff of the process
  run has the shape "practically zero for 6.5 hours → a rise to 6 mm/h in two and a half hours
  → halving in a little under 4 hours when the rain stops → a long recession", and these come
  from different mechanisms: the
  connection of the saturated area along the valleys, the end of the rain on the saturated
  area, and the drainage of the soil. Slowing the surface flow uniformly with one roughness
  does not produce this shape.
- **Dry soil and wet soil need different roughness values**: the no-infiltration run has no
  memory of the soil, and its responses to the two storms differ only by the water left on the
  surface (with roughness 10, 14 mm of catchment-mean water is left at 48 h and the time of
  exceeding 1 mm/h advances from 6.0 to 4.0 hours; with roughness 5, 6 mm is left and it
  advances from 4.7 to 3.8 hours). The difference in the process run (from 7.5 to 2.5 hours) is
  larger: roughness 10, which fits the first storm, is too slow for the second, and roughness
  5, which fits the second, is too fast for the first.
- **The fitting roughness changes with the soil**: the fitted roughness is not a property of
  the ground surface. It stands in for the conductivity and depth of the soil and its wetness
  before the rain, and has to be refitted when these change
  ([next section](#soil-conductivity-and-the-equivalent-roughness)).
- **Vertical infiltration only gives nothing until the soil is full, then runoff from the
  whole catchment, and the water that went in never returns**: without lateral flow in the
  soil, the soil of every cell fills at the same rate, and all cells saturate at the same time,
  at 10 h, when the cumulative rain reaches the capacity of 100 mm (the saturated area jumps
  from 0 to 100 %). Only the 20 mm of rain after that runs over the surface; the outlet runoff
  exceeds 1 mm/h at 11.8 h and peaks at 7.7 mm/h at 12.8 h, after the rain has stopped (the
  runoff in 48 hours is 20 mm, against 99.0 mm in the process run). The 100 mm that entered the
  soil does not move downslope and never comes out. In the second storm the soil is still
  full, so the response is the same as that of no infiltration with roughness 0.3 (above
  1 mm/h after 1.8 hours, levelling off at 10 mm/h). The runoff in 96 hours is 140 mm, 79 mm
  less than the 219 mm of the process run. With a slope roughness of 3 the first peak falls to
  1.4 mm/h and is nearly 5 hours later, but the amount of water that comes out hardly changes
  (17 mm in 48 hours). It is the lateral flow in the soil that gathers water in the valleys to
  form
  the saturated area and keeps the runoff going after the rain.
- **The surface flow equation (dynamic wave versus diffusion wave) makes little difference**: when the
  no-infiltration runs with roughness 0.3, 3 and 10 are computed as a diffusion wave, the time
  of exceeding 1 mm/h, the peak and the runoff in 48 hours are the same as, or almost the same
  as, those of the dynamic wave at the precision of the table (the peak for roughness 10 is
  7.12 mm/h in both; in the second storm it exceeds 1 mm/h after 3.8 against 4.0 hours). The
  fits differ by 0.02 at most. The same holds for the process run (table above). At the rain
  intensity (10 mm/h)
  and the discharges of this example, the treatment of the soil and the roughness matter far
  more than whether the advection term is included.

### Soil conductivity and the equivalent roughness

![Comparison for each lateral conductivity](figs/equivalent.png)

The process run (black) with a lateral saturated conductivity of (a) 3600 mm/h (base), (b)
10000, (c) 36000 and (d) 100000 mm/h, each overlaid with the closest no-infiltration runs
(orange). Grey is the rain.

| Lateral conductivity (mm/h) | Max. saturated area (%) | Water on the slopes at the end of the rain (mm) | Roughness that stores the same water on the surface | Time when runoff reaches 90 % of the rain (h) | Closest roughness (fit): storm 1 | storm 2 |
|---:|---:|---:|---:|---:|---:|---:|
| 3600 (base) | 42.7 | 77.2 | 8.2 | — / — | 10 (0.73) | 5 (0.86) |
| 10000 | 26.8 | 52.7 | 4.3 | 9.0 / 8.8 | 5 (0.94) | 3 (0.98) |
| 36000 | 15.3 | 29.0 | 1.6 | 5.5 / 5.3 | 3 (0.93) | 1 (0.97) |
| 100000 | 10.0 | 18.0 | 0.7 | 4.0 / 4.0 | 1 (0.99) | 1 (0.99) |

"Water on the slopes at the end of the rain" is the sum of the soil water and the surface water
on the cells other than channel cells at 12 h; the "roughness that stores the same water on the
surface" converts it to a roughness with the 0.6-power relation above. The times are for the
first / second storm, and — means not reached during the rain. The fit of the no-infiltration
run of each roughness to each variant of the process run (first / second storm) is as follows.

| Process-run variant | n = 0.3 | n = 1 | n = 3 | n = 5 | n = 10 | n = 30 |
|---|---:|---:|---:|---:|---:|---:|
| base (soil 0.5 m, lateral 3600 mm/h, slope roughness 0.3) | -1.57 / -0.41 | -0.94 / 0.08 | 0.15 / 0.68 | 0.68 / 0.86 | 0.73 / 0.72 | -0.26 / 0.12 |
| slope roughness 1 | -2.22 / -0.86 | -1.48 / -0.26 | -0.21 / 0.52 | 0.51 / 0.82 | 0.84 / 0.83 | -0.26 / 0.18 |
| lateral 10000 mm/h | 0.08 / 0.40 | 0.45 / 0.71 | 0.92 / 0.98 | 0.94 / 0.95 | 0.51 / 0.62 | -0.28 / 0.04 |
| lateral 36000 mm/h | 0.71 / 0.81 | 0.92 / 0.97 | 0.93 / 0.93 | 0.72 / 0.75 | 0.20 / 0.35 | -0.29 / -0.05 |
| lateral 100000 mm/h | 0.90 / 0.94 | 0.99 / 0.99 | 0.79 / 0.81 | 0.55 / 0.61 | 0.06 / 0.22 | -0.30 / -0.08 |
| soil 1 m | -7.70 / -2.58 | -6.30 / -1.67 | -3.73 / -0.41 | -1.92 / 0.21 | 0.40 / 0.69 | -0.12 / 0.27 |

- **The better the soil conducts water, the smaller the fitting roughness and the better the
  shape matches**: a larger lateral conductivity reduces the water stored in the soil and the
  saturated area, and the runoff comes earlier. The closest roughness falls from 10 and 5
  (first and second storm) at 3600 mm/h to 5 and 3 at 10000, 3 and 1 at 36000 and 1 and 1 at
  100000, and the fit rises from 0.73 and 0.86 to 0.99 and 0.99. In every case the closest
  roughness is near the "roughness that stores the same water on the surface" (8.2, 4.3, 1.6,
  0.7). In the process run with 100000 mm/h only the valley floors saturate (10 %); the soil
  water moves quickly down the slopes and seeps out in the valleys, and the hydrograph almost
  coincides with that of no infiltration with roughness 1. The effect of the wetness before
  the rain also becomes small (the runoff exceeds 1 mm/h after 2.8 hours in the first storm
  and 2.5 hours in the second).
- **The equivalent roughness used in practice corresponds to a soil that conducts water
  fast**: in the no-infiltration runs the runoff reaches 90 % of the rain after 2.8 hours
  with roughness 0.3 and 4.3 hours with roughness 1. The equivalent roughness used in practice
  for mountains (about 0.4–0.8) lies in between, and the value of the empirical flood
  concentration time for this catchment (4.7 hours) is close to that of roughness 1. The
  process run is this fast when the lateral conductivity is 36000–100000 mm/h (5.5 and 4.0
  hours); the base value of
  3600 mm/h does not reach 90 % during the 12 hours of rain. The equivalent roughness came
  out as large as 5–10 because the soil of the base setting releases water more slowly than
  this yardstick of real storm runoff. 36000–100000 mm/h (0.01–0.03 m/s) is beyond the range
  the user guide suggests (1000–10000 mm/h); it is not flow in the soil matrix but an
  effective value that lumps fast paths such as pipes. The equivalent roughness used in
  practice is tied to how the slope length is taken, and the definition of the flood
  concentration time is not the same as "the time to reach 90 % of the rain", so this
  correspondence is only a guide.
- **Soil depth and the wetness before the rain are hard to replace with a roughness**: the
  first storm of the process run with 1 m of soil (10 hours without runoff) is matched no
  better than a fit of 0.40 by any roughness. The rain that does not run off until the soil
  has filled is what practice handles with the effective rainfall (losses); the roughness
  covers the delay of the water that does become runoff.

## What this model does not represent (differences from the real phenomenon)

- **The soil is a uniform schematic layer**: the soil depth of 0.5 m, the effective porosity of
  0.2 and the conductivities are the same everywhere. Real soil depth varies from place to
  place, and thin soil fills first and sets the timing of the runoff (Tani 1997). A
  distribution of soil depth can be given with `fn_sd`. The results depend strongly on the
  soil values (soil 1 m and the runs with other lateral conductivities above). The runoff of
  the base setting (lateral 3600 mm/h) is on the slow side of the empirical flood
  concentration time
  ([Soil conductivity and the equivalent roughness](#soil-conductivity-and-the-equivalent-roughness)).
- **The unsaturated zone is not solved**: infiltrated water joins the saturated zone at the
  base of the soil in the same step. The wetness of the soil before the rain, the time needed
  to pass through the unsaturated zone, and the water retained in the soil after the rain are
  not represented (soil water keeps decreasing until it has drained to the valleys by lateral
  flow). The amount of rain needed before runoff appears in the first storm on dry soil
  (around 70 mm in this example) is set by the initial groundwater storage of zero and by
  this treatment. The feature that solves vertical unsaturated flow
  ([VZ runoff](../../../docs/en/users_guide/vz.md)) cannot be combined with groundwater
  (`fn_gwflow`).
- **Bedrock, evapotranspiration and interception are not included**: infiltration into the
  weathered bedrock below the soil and the baseflow from it (layer 2), evapotranspiration and
  canopy interception are not enabled. Between storms the soil water decreases only by
  drainage to the valleys.
- **Slopes are represented on a 50 m grid**: a slope from ridge to valley (a few hundred
  metres) is represented by a few cells. The saturated area is resolved in units of one cell
  (50 m), coarser than the real wet strips along streams (a few metres to a few tens of metres
  wide) and small hollows. How the saturated fraction changes with the grid size has not been
  examined.
- **Channels are 50 m wide cells, and water ponds on flat reaches**: a channel cell is as wide
  as the grid, 50 m, so the flow is wider and shallower than in real mountain streams (a few
  metres to a little over ten metres). In addition, the depression-filled elevations keep
  flat reaches as steps (40 % of the 9.4 km of main stem that runs on channel cells and 13 %
  of the 42.9 km channel network; the longest reach is 0.7 km), where water flows only by the
  slope of the water surface and therefore ponds. Of the 18 mm of surface water at the end of
  the rain, 12 mm is on channel cells, and 70 % of that (8.4 mm) lies on the channel cells of
  the flat steps (the 144 channel cells that have a neighbouring channel cell at the same
  elevation), 0.8 m deep on average (1.9 m at most). The two and a half hours between the
  formation of the saturated area and the moment the outlet runoff exceeds 1 mm/h are the
  time the small runoff from a still narrow saturated area needs to supply the water that the
  flow in the valleys and channels, these ponds included, requires. Real streams probably
  route the water faster. Narrow channels can be represented with the subgrid channel width
  (`fn_width` in [Channels](../../../docs/en/users_guide/channel.md)), which this example does
  not use. Valleys without the channel mask (upslope area up to 1.3 km²) flow with the slope
  roughness.
- **The rain is a uniform block of a single intensity**: neither a variation of intensity in
  time nor a distribution of rain within the catchment is given, and the intensity is always
  10 mm/h. The normal depth of surface flow grows with the 0.6th power of (rain intensity ×
  roughness) and the thickness of the saturated zone in the soil in proportion to the rain
  intensity, so the fitting roughness should also change with the rain intensity; this has not
  been examined.
- **Nothing is compared with observations**: the values are schematic, and whether the timing
  of the rise, the peak and the recession match a real catchment has not been checked. What
  this example shows is how the mechanisms are linked and in which direction the response
  moves when a setting is changed.

## Notes

- **Dry soil and empty channels at the start**: the response to the first storm (6.5 hours
  without runoff) belongs to this initial condition. A real catchment has baseflow before the
  rain and is wet along the valleys, so the condition closer to a real flood is the second
  storm.
- **Definition of the saturated area**: a cell is counted as saturated when its groundwater
  storage is within 0.1 mm of the soil capacity (100 mm) (cells on the edge of the saturated
  area hover just below the capacity, because the rain of each step replaces the water that
  flows out). Fields are written every hour, so the saturated fraction is also resolved to one
  hour. The "rain on the saturated area" is the integral of rain × saturated fraction; it is a
  guide that ignores the time this water needs to travel to the outlet.
- **Measuring the runoff, and the water balance**: the runoff integrated by the trapezoidal
  rule from the transect discharge (instantaneous values every 10 minutes), the storage in the
  Log (S_total) and the cumulative rain balance within 0.05 mm over the 96 hours of the
  process run (the storage in the Log is printed in steps of 0.1 mm). The transect measures
  the flow on the surface. Water that moves inside the soil into the outlet cell does not
  cross it, so in the runs with a larger lateral conductivity the runoff comes out smaller by
  that amount (over 96 hours: 0.05 mm for 10000 mm/h, 0.1 mm for 36000 mm/h and 0.5 mm for
  100000 mm/h).
- **Why the channel mask is connected along the flow tree**: the line of the source river mask
  is offset by one cell from the valley line of the elevations in places and is interrupted
  there. Those cells get the slope roughness, so in the runs with a large slope roughness the
  slope-type cells on the valley line dam the flow and deep water ponds upstream.
  `make_catchment.py` follows the flow tree from each cell of the river mask down to the outlet
  and adds the cells it passes to the channels.
- **Time step**: with dt = 3 s, Cn_max stays at or below 0.43 in all cases.

## Starting points for sensitivity experiments

- `gw_ksh_mmh` (lateral conductivity) and `sd0` (soil depth): they set the timing of the rise,
  the peak and the extent of the saturated area (table above). `sy0` (effective porosity)
  changes both the capacity of the soil and the speed at which groundwater moves downslope.
- `fn_sd` (distribution of soil depth): thinning the soil along the valleys or on the ridges
  changes the order of saturation ([test/gwtani](../../../test/gwtani/en/README.md) checks this
  on a single slope).
- `prval` in `param_common.txt` (intensity and duration of the rain, and the interval between
  the two storms): a longer interval lets the saturated area shrink further before the second
  storm, and the second response approaches the first.
- `CASES` in `sweep.py`: one line adds a case, such as another roughness (between 10 and 30, for
  instance) or another setting of the process run. To show it in the figures and tables, add
  it to `CASES` in `plot_results.py` as well.
- `make_catchment.py --outlet I J` (the outlet cell, numbered on the source grid): cuts out
  another catchment. Adjust the grid size, the stage cell, the transect and the probe in the
  parameter files to the `nx`, `ny`, `outlet_ij` and `gauge_ij` it prints. `--outlet 344 302`
  puts the outlet 2.3 km downstream, just upstream of the confluence of the two tributaries
  (38.2 km²; `nx = 192`, stage cell (190, 33), probe (189, 33), transect (189, 34)–(189, 30)).
  A flat reach 1.5 km long then lies just upstream of the outlet and holds water 1.3–2.4 m
  deep at the end of the rain, so the runoff exceeds 1 mm/h after 8.3 instead of 7.5 hours in
  the first storm and after 3.5 instead of 2.5 hours in the second, and it rises abruptly
  shortly after 8 h (the maximum surface water increases from 18 to 25 mm; the saturated
  fraction and the closest roughness do not change, and the peak is almost the same,
  8.6 mm/h).
- Adding the weathered bedrock layer (`f_gwlayer2`), evapotranspiration (`fn_evap`) and
  interception (`fn_intercept`) brings in baseflow and the drying between storms.

## References

The bibliographic details of Mosley (1979), Beven & Germann (1982) and Tani (1997) are those of
[Groundwater models](../../../docs/en/users_guide/gwflow_models.md); the others were confirmed by
search (for Kadoya & Fukushima (1976) only the formula and the coefficient were confirmed, from
a search excerpt of a paper that quotes them; its bibliographic details were not checked). The
texts were not checked; the summaries of their contents rely on abstracts and secondary sources.

- Barnes, R., Lehman, C. and Mulla, D. (2014): Priority-flood: An optimal depression-filling
  and watershed-labeling algorithm for digital elevation models. Computers & Geosciences, 62,
  117–127.
- Beven, K. and Germann, P. (1982): Macropores and water flow in soils. Water Resources
  Research, 18, 1311–1325.
- Beven, K. J. and Kirkby, M. J. (1979): A physically based, variable contributing area model of
  basin hydrology. Hydrological Sciences Bulletin, 24(1), 43–69.
- Dunne, T. and Black, R. D. (1970): Partial area contributions to storm runoff in a small New
  England watershed. Water Resources Research, 6(5), 1296–1311.
- Engman, E. T. (1986): Roughness coefficients for routing surface runoff. Journal of
  Irrigation and Drainage Engineering, 112(1), 39–53.
- Hewlett, J. D. and Hibbert, A. R. (1967): Factors affecting the response of small watersheds
  to precipitation in humid areas. In: Sopper, W. E. and Lull, H. W. (eds.), Forest Hydrology,
  Pergamon Press, 275–290.
- Mosley, M. P. (1979): Streamflow generation in a forested watershed, New Zealand. Water
  Resources Research, 15, 795–806.
- Nash, J. E. and Sutcliffe, J. V. (1970): River flow forecasting through conceptual models
  part I — A discussion of principles. Journal of Hydrology, 10(3), 282–290.
- O'Callaghan, J. F. and Mark, D. M. (1984): The extraction of drainage networks from digital
  elevation data. Computer Vision, Graphics, and Image Processing, 28(3), 323–344.
- Tani, M. (1997): Runoff generation processes estimated from hydrological observations on a
  steep forested hillslope with a thin soil layer. Journal of Hydrology, 200, 84–109.
- Tromp-van Meerveld, H. J. and McDonnell, J. J. (2006): Threshold relations in subsurface
  stormflow: 2. The fill and spill hypothesis. Water Resources Research, 42, W02411.
- USDA Soil Conservation Service (1986): Urban hydrology for small watersheds. Technical
  Release 55 (TR-55), 2nd ed.
- Kadoya, M. and Fukushima, A. (1976): Chūshō kasen no kōzui tōtatsu jikan [Flood
  concentration time of small and medium rivers]. Annuals of the Disaster Prevention Research
  Institute, Kyoto University, 19(B-2), 143–152 (in Japanese).
- A document of the river basin committee of the Wakayama Office of River and National
  Highway, Kinki Regional Development Bureau, Ministry of Land, Infrastructure, Transport and
  Tourism (it quotes the table of equivalent roughness from the Technical Criteria for River
  Works (draft) and uses N = 0.6 for present mountain land; in Japanese):
  https://www-2.kkr.mlit.go.jp/wakayama/ryuiki_iinkai/ryuiki/comm08/pdf/data1/refe-data1_2.pdf
- A document of the Hokkaido Regional Development Bureau, Ministry of Land, Infrastructure,
  Transport and Tourism (it quotes the table of standard values of the equivalent roughness
  from the Technical Criteria for River Works, survey volume (June 2012 edition): 0.4–0.8 for
  mountain catchments with good forest cover; in Japanese):
  https://www.hkd.mlit.go.jp/ky/kn/kawa_kei/splaat0000017ws4-att/splaat0000017wum.pdf
