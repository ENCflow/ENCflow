# source_area — growth and shrinkage of the runoff source area of a mountain catchment

> English mirror of examples/source_area/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Most of the rain that falls on a forested mountain catchment does not run over the ground: it
infiltrates into the soil. The infiltrated water flows downslope inside the soil layer, gathers
in the valleys, and comes out at the surface where the soil has filled up (the saturated area)
to become streamflow. Only part of the catchment produces runoff; that part spreads from the
valleys onto the slopes during rain and shrinks after the rain stops (the variable source
area). This example puts the same storm twice on a 38 km² headwater catchment cut out of the
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
  C = 290 for forested hills and mountains). For the catchment (38 km²) and the rain
  (10 mm/h) of this example it gives 4.8 hours (the formula and the coefficient were confirmed
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
| Water leaves the catchment at the outlet | The single cell at the east end of the valley is kept empty with a prescribed stage (a complete drain) | `&list_bound_stage` |

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
  cells). Just upstream of the confluence of two tributaries, one cell in the valley of the
  southern (right-bank) tributary (cell (344, 302) of the source grid) is taken as the outlet,
  and the 15,261 cells (38.15 km²) upstream of it are cut out (a window of 192 × 143 cells).
  Elevation is 734–2127 m and the median steepest slope is 0.76 (37°; 80 % of the cells lie
  between 0.39 and 1.03). The extraction is done by `make` (`make_catchment.py`), and the
  elevations are those of the source data, unchanged.
- **Flow tree and channel cells**: each cell drains to the steepest of its 8 neighbours (D8;
  O'Callaghan & Mark 1984); on the flats left by the depression filling the receiver follows
  the order of Priority-Flood (Barnes et al. 2014). The channel cells are the 828 cells of the
  source river mask (made from the rivers of the National Land Numerical Information) plus the
  24 cells passed when the flow tree is followed from each of them down to the outlet: 852
  cells (5.6 %) in all (the line of the river mask is offset by one cell from the valley line
  of the elevations in places and is interrupted there; see [Notes](#notes)).
- **Outlet and how the discharge is measured**: the outlet cell (190, 33) is a drain kept empty
  with a prescribed stage (a stage below the bed). The catchment consists of "the cells
  upstream of the valley cell (189, 33) just west of the outlet cell" and the outlet cell, so
  all water leaving the catchment enters the outlet cell from column i = 189. The discharge
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

Rough run times (gfortran -Ofast, a 4-core machine): the process run takes nine and a half
minutes with 3 threads. With 1 thread, the process run takes 20–30 minutes, vertical
infiltration only 20–40 minutes and no infiltration 40–60 minutes (no infiltration, and
vertical infiltration only once the soil is full, are heavy because water lies on every cell;
the larger the roughness, the longer the water stays and the longer the run). To run cases side
by side, use `make -j 4 run OMP_NUM_THREADS=1` and `make -j 4 sweep OMP_NUM_THREADS=1` (a
little over 3 hours for the 18 cases). The results do not depend on the number of threads (the process run
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
| 1 | 0.0 | 0.0 | 8.3 | 8.60 | 12.3 | 42.6 | 97.5 | 81 |
| 2 | 18.2 | 11.5 | 3.5 | 8.70 | 12.3 | 42.8 | 119.9 | 100 |

Times are measured from the start of each storm. The fraction of saturated cells by class of
upslope area (on the flow tree, counting the cell itself) is as follows.

| Class | Share of cells (%) | 5 h | 7 h | 12 h | 24 h | 48 h | 60 h |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 cell (ridge) | 39 | 0 | 1 | 6 | 1 | 0 | 6 |
| 2–9 cells | 44 | 1 | 19 | 54 | 10 | 2 | 54 |
| 10–99 cells | 11 | 20 | 90 | 100 | 88 | 44 | 100 |
| ≥ 100 cells (valley) | 5 | 63 | 100 | 100 | 100 | 100 | 100 |

- **Nothing saturates in the first 4 hours**: all rain infiltrates, and the catchment-mean soil
  water rises at the rain rate of 10 mm/h (40.0 mm at 4 h). There is no water on the surface and
  no runoff.
- **The saturated area spreads from the valleys onto the slopes**: in the fifth hour the valley
  cells, where groundwater from upslope gathers, fill first (63 % of the valley cells with an
  upslope area of 100 cells or more; 6 % of the whole catchment). The saturated area spreads
  onto the slopes while joining the valley lines into a dendritic pattern: 24 % at 7 h and 43 %
  at 12 h, the end of the rain. At 12 h every cell with an upslope area of 10 cells or more is
  saturated, while only 6 % of the ridge cells are. The catchment-mean soil water rises only to
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
- **Outlet runoff rises abruptly once the saturated area has connected along the valleys**: in
  the first storm the runoff is practically zero until 8 h (0.05 mm/h at 8 h), then reaches
  4.3 mm/h in one hour and 8.6 mm/h (86 % of the rain) in four hours. For a little over three
  hours after the saturated area starts to form at 5 h, the water leaving it infiltrates into
  downstream cells that are not yet full and travels down while filling the valleys and
  channels (the catchment-mean surface water is 14.5 mm at 8 h and 24.6 mm at 12 h; see
  [What this model does not represent](#what-this-model-does-not-represent-differences-from-the-real-phenomenon)).
- **Three quarters of the runoff is water that passed through the soil**: the rain that fell on
  the saturated area is 21 mm in the first storm and 30 mm in the second, 22 % and 25 % of the
  runoff in 48 hours. The rest infiltrated, flowed through the soil and seeped out in the
  saturated area. When the rain stops, the part supplied by rain on the saturated area
  disappears and the runoff halves in four hours (4.4 mm/h at 16 h); after that it declines
  slowly with the drainage of the soil (2.1 mm/h at 24 h, 0.5 mm/h at 48 h).
- **In the second storm, on wet soil, runoff rises from the start of the rain**: before the
  second storm the saturated area is still 11.5 % and the soil holds 18 mm. Rain on the
  saturated area becomes runoff at once, and the runoff exceeds 1 mm/h after 3.5 hours (8.3
  hours in the first storm). The peak is almost the same as in the first storm, 8.7 mm/h, and
  the runoff in 48 hours equals the rain, 120 mm (97.5 mm in the first storm; the difference of
  22 mm is the water that first filled the dry soil and channels).

Where the water in the catchment is (catchment-mean depth in mm; 52 h and 56 h are the fourth
and the eighth hour of the second storm):

| Time (h) | Runoff (mm/h) | Soil water | of which in saturated cells | Surface water | of which on channel cells | Total |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0.00 | 40.0 | 0.1 | 0.0 | 0.0 | 40.0 |
| 8 | 0.05 | 65.5 | 30.3 | 14.5 | 9.9 | 80.0 |
| 12 | 8.51 | 72.0 | 42.6 | 24.6 | 17.6 | 96.6 |
| 24 | 2.05 | 36.3 | 20.1 | 10.2 | 8.2 | 46.5 |
| 48 | 0.46 | 18.1 | 11.5 | 4.5 | 3.9 | 22.6 |
| 52 | 1.54 | 48.2 | 16.9 | 11.5 | 9.0 | 59.7 |
| 56 | 5.41 | 66.2 | 32.1 | 19.8 | 14.4 | 85.9 |
| 60 | 8.62 | 72.1 | 42.8 | 24.8 | 17.7 | 96.9 |

- **With water running in the channels, the catchment holds 23 mm**: just before the second
  storm (36 hours after the rain) the outlet carries 0.46 mm/h (4.9 m³/s) and the catchment
  holds 22.6 mm of water: 18.1 mm in the soil (11.5 mm of it in the saturated cells of the
  valleys) and 4.5 mm on the surface (3.9 mm of it on channel cells). The difference in runoff
  between the first and the second storm (22 mm) is the water that first built up this
  storage. The amount is not constant: after the rain it decreases together with the runoff
  (46.5 mm and 2.05 mm/h 12 hours after the rain).
- **With the same water in the soil, a dry catchment does not yet deliver it to the outlet**:
  at 8 h of the first storm the soil holds 65.5 mm and the surface 14.5 mm, but the runoff is
  0.05 mm/h. In the eighth hour of the second storm (56 h) the soil water is almost the same,
  66.2 mm, the surface water is 19.8 mm, and the runoff is 5.4 mm/h. In the first storm the
  dry valleys and channels are still being filled (9.9 mm of the 14.5 mm on the surface is on
  channel cells).

Changing one setting of the process run at a time gives the following (`process_*` of
`make sweep`).

| Changed setting | Storm | Time above 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Runoff 12 h after the rain (mm/h) | Runoff in 48 h (mm) | Max. saturated area (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 1 | 8.3 | 8.60 | 12.3 | 2.05 | 97.5 | 42.6 |
| base | 2 | 3.5 | 8.70 | 12.3 | 2.05 | 119.9 | 42.8 |
| slope roughness 0.3 → 1 | 1 | 8.8 | 8.14 | 12.5 | 2.21 | 96.7 | 42.3 |
| slope roughness 0.3 → 1 | 2 | 3.7 | 8.31 | 12.5 | 2.21 | 119.9 | 42.6 |
| surface flow as a diffusion wave | 1 | 8.3 | 8.63 | 12.3 | 2.04 | 97.5 | 42.6 |
| surface flow as a diffusion wave | 2 | 3.3 | 8.71 | 12.3 | 2.04 | 119.9 | 42.8 |
| lateral conductivity 3600 → 10000 mm/h | 1 | 6.5 | 9.80 | 12.3 | 1.35 | 108.4 | 27.0 |
| lateral conductivity 3600 → 10000 mm/h | 2 | 4.0 | 9.80 | 12.3 | 1.35 | 119.9 | 27.0 |
| lateral conductivity 3600 → 36000 mm/h | 1 | 4.7 | 10.00 | 12.0 | 0.69 | 114.1 | 15.5 |
| lateral conductivity 3600 → 36000 mm/h | 2 | 3.7 | 10.00 | 12.0 | 0.69 | 120.0 | 15.5 |
| lateral conductivity 3600 → 100000 mm/h | 1 | 3.7 | 10.00 | 11.2 | 0.44 | 116.3 | 10.0 |
| lateral conductivity 3600 → 100000 mm/h | 2 | 3.2 | 10.00 | 11.2 | 0.44 | 119.9 | 10.0 |
| soil depth 0.5 → 1 m | 1 | 11.3 | 5.47 | 13.3 | 2.52 | 81.1 | 22.3 |
| soil depth 0.5 → 1 m | 2 | 2.8 | 6.64 | 12.7 | 2.56 | 119.8 | 23.4 |

- **The surface roughness and the flow equation hardly change the runoff of the process run**:
  raising the slope roughness from 0.3 to 1 lowers the peak by 5 % and delays it by 0.2 hours.
  The run with the surface flow as a diffusion wave coincides with the base run, with a
  difference of 0.3 % in the peak. The soil sets the delay of the runoff; the surface
  roughness matters only while the water flows over the saturated area and the valleys.
- **The conductivity and the depth of the soil change the runoff a great deal**: with a lateral
  conductivity about three times larger, groundwater reaches the valleys sooner, the rise
  advances from 8.3 to 6.5 hours and the peak rises to 9.8 mm/h (98 % of the rain). Because
  the slopes drain well, the maximum saturated area decreases from 43 % to 27 %. With 10 and
  about 28 times the conductivity (36000 and 100000 mm/h) the rise comes at 4.7 and 3.7
  hours, the runoff balances the rain during the storm (10 mm/h), and the saturated area
  stays on the valley floors, 15.5 % and 10 %. With a soil depth of 1 m, twice as much water
  is needed to fill the soil, the rise is delayed to 11.3 hours, and in a 12-hour storm the
  runoff does not rise fully: the peak is 5.5 mm/h (maximum saturated area 22 %).

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
| process run | 0.3 | 1 | 8.3 | 8.60 | 12.3 | 2.05 | 97.5 | — |
| process run | 0.3 | 2 | 3.5 | 8.70 | 12.3 | 2.05 | 119.9 | — |
| no infiltration | 0.3 | 1 | 2.7 | 10.00 | 7.8 | 0.20 | 119.4 | -1.62 |
| no infiltration | 0.3 | 2 | 2.5 | 10.00 | 7.8 | 0.20 | 120.0 | -0.37 |
| no infiltration | 1 | 1 | 3.5 | 10.00 | 10.3 | 0.40 | 118.7 | -1.02 |
| no infiltration | 1 | 2 | 3.3 | 10.00 | 10.3 | 0.40 | 120.0 | 0.10 |
| no infiltration | 3 | 1 | 4.7 | 9.99 | 12.0 | 0.96 | 116.4 | 0.06 |
| no infiltration | 3 | 2 | 4.2 | 9.99 | 12.0 | 0.96 | 120.0 | 0.69 |
| no infiltration | 5 | 1 | 5.5 | 9.75 | 12.3 | 1.50 | 113.6 | 0.64 |
| no infiltration | 5 | 2 | 4.7 | 9.80 | 12.2 | 1.49 | 120.0 | 0.86 |
| no infiltration | 10 | 1 | 7.2 | 7.06 | 14.5 | 2.68 | 104.5 | 0.75 |
| no infiltration | 10 | 2 | 4.8 | 7.73 | 13.5 | 2.68 | 119.9 | 0.73 |
| no infiltration | 30 | 1 | 18.3 | 1.83 | 30.5 | 1.56 | 54.7 | -0.24 |
| no infiltration | 30 | 2 | 0.2 | 3.71 | 20.8 | 3.58 | 118.0 | 0.13 |
| no infiltration (diffusion wave) | 0.3 | 1 | 2.7 | 10.00 | 6.8 | 0.20 | 119.4 | -1.68 |
| no infiltration (diffusion wave) | 0.3 | 2 | 2.5 | 10.00 | 6.8 | 0.20 | 120.0 | -0.42 |
| no infiltration (diffusion wave) | 3 | 1 | 4.7 | 9.99 | 12.0 | 0.95 | 116.4 | 0.01 |
| no infiltration (diffusion wave) | 3 | 2 | 4.2 | 9.99 | 12.0 | 0.94 | 120.0 | 0.67 |
| no infiltration (diffusion wave) | 10 | 1 | 7.2 | 7.07 | 14.3 | 2.64 | 104.5 | 0.77 |
| no infiltration (diffusion wave) | 10 | 2 | 4.8 | 7.74 | 13.2 | 2.64 | 119.9 | 0.76 |
| vertical infiltration only | 0.3 | 1 | 12.7 | 5.80 | 13.5 | 0.20 | 19.4 | -0.20 |
| vertical infiltration only | 0.3 | 2 | 2.5 | 10.00 | 7.8 | 0.20 | 120.0 | -0.37 |
| vertical infiltration only | 3 | 1 | 16.5 | 1.32 | 18.7 | 0.82 | 16.5 | -0.53 |
| vertical infiltration only | 3 | 2 | 4.2 | 9.99 | 12.0 | 0.96 | 119.9 | 0.69 |

Times are measured from the start of each storm. In the cases whose peak equals the rain,
10 mm/h, the runoff has levelled off in balance with the rain, and the "time of peak" is the
time when it levelled off. For roughness 30 the time of exceeding 1 mm/h in the second storm is
0.2 hours because the water of the first storm is still running off at a little over 1 mm/h.

The amount of water lying on the surface is as follows (the maximum catchment-mean storage, and
the depth on the cells other than channel cells at the end of each storm).

| Case | Slope roughness | Max. surface water (mm) | Mean depth at 12 h (mm) | Max. depth at 12 h (m) | Mean depth at 60 h (mm) |
|---|---:|---:|---:|---:|---:|
| process run | 0.3 | 24.8 | 7.5 | 2.39 | 7.5 |
| process run | 1 | 30.8 | 14.2 | 2.37 | 14.3 |
| process run (diffusion wave) | 0.3 | 24.2 | 7.4 | 2.23 | 7.4 |
| process run (lateral 10000 mm/h) | 0.3 | 24.9 | 6.7 | 2.54 | 6.7 |
| process run (lateral 36000 mm/h) | 0.3 | 23.8 | 5.4 | 2.56 | 5.4 |
| process run (lateral 100000 mm/h) | 0.3 | 22.9 | 4.4 | 2.54 | 4.4 |
| process run (soil 1 m) | 0.3 | 20.2 | 4.6 | 1.70 | 5.2 |
| no infiltration | 0.3 | 30.0 | 11.6 | 2.60 | 11.6 |
| no infiltration | 1 | 40.9 | 23.0 | 2.68 | 23.0 |
| no infiltration | 3 | 61.7 | 44.9 | 2.73 | 44.9 |
| no infiltration | 5 | 77.9 | 62.0 | 2.73 | 62.1 |
| no infiltration | 10 | 106.6 | 93.0 | 2.92 | 95.1 |
| no infiltration | 30 | 163.5 | 117.6 | 0.60 | 162.2 |
| no infiltration (diffusion wave) | 0.3 | 29.1 | 11.4 | 2.39 | 11.4 |
| no infiltration (diffusion wave) | 3 | 60.6 | 44.7 | 2.45 | 44.7 |
| no infiltration (diffusion wave) | 10 | 105.8 | 93.0 | 2.92 | 95.1 |
| vertical infiltration only | 0.3 | 30.0 | 10.5 | 0.81 | 11.6 |
| vertical infiltration only | 3 | 61.7 | 19.2 | 0.10 | 44.9 |

- **No infiltration with roughness 0.3 rises early and recedes early**: the runoff exceeds
  1 mm/h after 2.7 hours and by 5 h it has reached the rain rate of 10 mm/h and levelled off
  (the process run exceeds 1 mm/h after 8.3 hours and peaks at 8.6 mm/h). When the rain stops
  it recedes within a few hours: 0.2 mm/h after 12 hours (2.1 mm/h in the process run). The
  responses to the first and the second storm are the same. Because the water does not pass
  through the soil, there is neither the time needed to fill the dry soil nor the long recession
  fed by the drainage of the soil.
- **A larger roughness brings the delay and the recession closer to the process run**: the
  larger the slope roughness, the later the rise, the lower the peak and the gentler the
  recession. Of the six values tried, the closest to the process run is roughness 10 for the
  first storm (dry soil; fit 0.75) and roughness 5 for the second storm (wet soil; 0.86).
  Roughness 30 overshoots (the first peak is 1.8 mm/h, 18 hours after the end of the rain).
- **The roughness needed is 5–10, an order of magnitude above the equivalent roughness used in
  practice**: a roughness of 5–10 is 17–33 times the slope roughness 0.3 of the process run,
  an order of magnitude away from both the roughness of thin sheet flow (0.4–0.8 for woods)
  and the equivalent roughness used in practice for mountains (about 0.4–0.8). At the end of
  the rain the slope cells then carry 6–9 cm of water on average, and the catchment-mean
  surface water reaches 78–107 mm. This is about the same as the sum of the soil water (72 mm)
  and the surface water (25 mm) of the process run at the end of the rain, 97 mm. A large
  roughness delays the runoff by storing, as a thick layer of water on the surface, the water
  that the soil was storing.
- **The roughness needed is set by the amount of water the soil stores**: in the
  no-infiltration runs the depth on the slopes at the end of the rain grows with the 0.6th
  power of the roughness (table below; the normal depth of Manning flow, h = (n q / √I)^0.6,
  with q the discharge per unit width and I the slope). At the end of the rain the process run
  holds 78 mm on the slopes (cells other than channel cells), soil and surface together, and
  the roughness that holds this on the surface alone is 0.3 × (78 / 11.6)^(5/3) = 7.2. The
  fitted roughness of 5–10 is what this relation gives. Storing twice the water takes 3.2
  times the roughness, so the roughness needed rises steeply with the water the soil stores.

| Slope roughness | 0.3 | 1 | 3 | 5 | 10 | 30 |
|---|---:|---:|---:|---:|---:|---:|
| Time to reach 50 % of the rain (h) | 3.0 | 4.0 | 6.0 | 7.7 | 11.3 | — |
| Time to reach 90 % of the rain (h) | 3.7 | 5.0 | 8.2 | 10.5 | — | — |
| Mean depth on the slopes at 12 h (mm) | 11.6 | 23.0 | 44.9 | 62.0 | 93.0 | 117.6 |
| Depth for roughness 0.3 × (n / 0.3)^0.6 (mm) | 11.6 | 23.8 | 46.0 | 62.5 | 94.8 | 183.3 |

Values for the first storm of the no-infiltration runs (— = not reached during the rain). For
roughness 10 and 30 the runoff has not yet balanced the rain at the end of the storm, so the
depth is below the 0.6-power relation.

- **The shape still does not match**: roughness 5 matches the time of the peak (12.3 h), but
  the peak is 13 % too high, the rise is too early (5.8 mm/h at 8 h, against 0.05 mm/h in the
  process run) and the recession is too fast (1.5 mm/h 12 hours after the rain, against
  2.1 mm/h). Roughness 10 comes closer in the time of exceeding 1 mm/h (7.2 hours), but the
  increase is too gentle (2.6 mm/h at 9 h, against 4.3 mm/h), the peak is 18 % too low and 2.2
  hours late, and the recession is now too slow (2.7 mm/h). The runoff of the process run has
  the shape "practically zero for 8 hours → a steep rise of 4 mm/h in one hour → halving in 4
  hours when the rain stops → a long recession", and these come from different mechanisms: the
  connection of the saturated area along the valleys, the end of the rain on the saturated
  area, and the drainage of the soil. Slowing the surface flow uniformly with one roughness
  does not produce this shape.
- **Dry soil and wet soil need different roughness values**: the no-infiltration run has no
  memory of the soil, and its responses to the two storms differ only by the water left on the
  surface (with roughness 10, 16 mm of catchment-mean water is left at 48 h and the time of
  exceeding 1 mm/h advances from 7.2 to 4.8 hours; with roughness 5, 7 mm is left and it
  advances from 5.5 to 4.7 hours). The difference in the process run (from 8.3 to 3.5 hours) is
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
  exceeds 1 mm/h at 12.7 h, after the rain has stopped, and peaks at 5.8 mm/h at 13.5 h (the
  runoff in 48 hours is 19 mm, against 97.5 mm in the process run). The 100 mm that entered the
  soil does not move downslope and never comes out. In the second storm the soil is still
  full, so the response is the same as that of no infiltration with roughness 0.3 (above
  1 mm/h after 2.5 hours, levelling off at 10 mm/h). The runoff in 96 hours is 139 mm, 78 mm
  less than the 217 mm of the process run. With a slope roughness of 3 the first peak falls to
  1.3 mm/h and is 5 hours later, but the amount of water that comes out hardly changes (17 mm
  in 48 hours). It is the lateral flow in the soil that gathers water in the valleys to form
  the saturated area and keeps the runoff going after the rain.
- **The surface flow equation (dynamic wave versus diffusion wave) makes little difference**: when the
  no-infiltration runs with roughness 0.3, 3 and 10 are computed as a diffusion wave, the time
  of exceeding 1 mm/h, the peak and the runoff in 48 hours are the same as, or almost the same
  as, those of the dynamic wave at the precision of the table (the peak for roughness 10 is
  7.07 against 7.06 mm/h). A difference is visible at the end of the rise for roughness 0.3:
  the diffusion wave reaches the balance with the rain one hour earlier (6.8 against 7.8
  hours). The same holds for the process run (table above). At the rain intensity (10 mm/h)
  and the discharges of this example, the treatment of the soil and the roughness matter far
  more than whether the advection term is included.

### Soil conductivity and the equivalent roughness

![Comparison for each lateral conductivity](figs/equivalent.png)

The process run (black) with a lateral saturated conductivity of (a) 3600 mm/h (base), (b)
10000, (c) 36000 and (d) 100000 mm/h, each overlaid with the closest no-infiltration runs
(orange). Grey is the rain.

| Lateral conductivity (mm/h) | Max. saturated area (%) | Water on the slopes at the end of the rain (mm) | Roughness that stores the same water on the surface | Time when runoff reaches 90 % of the rain (h) | Closest roughness (fit): storm 1 | storm 2 |
|---:|---:|---:|---:|---:|---:|---:|
| 3600 (base) | 42.8 | 77.9 | 7.2 | — / — | 10 (0.75) | 5 (0.86) |
| 10000 | 27.0 | 53.5 | 3.9 | 9.3 / 9.3 | 5 (0.95) | 3 (0.98) |
| 36000 | 15.5 | 29.9 | 1.5 | 6.0 / 6.0 | 3 (0.93) | 1 (0.97) |
| 100000 | 10.0 | 18.9 | 0.7 | 4.8 / 4.7 | 1 (0.99) | 1 (0.99) |

"Water on the slopes at the end of the rain" is the sum of the soil water and the surface water
on the cells other than channel cells at 12 h; the "roughness that stores the same water on the
surface" converts it to a roughness with the 0.6-power relation above. The times are for the
first / second storm, and — means not reached during the rain. The fit of the no-infiltration
run of each roughness to each variant of the process run (first / second storm) is as follows.

| Process-run variant | n = 0.3 | n = 1 | n = 3 | n = 5 | n = 10 | n = 30 |
|---|---:|---:|---:|---:|---:|---:|
| base (soil 0.5 m, lateral 3600 mm/h, slope roughness 0.3) | -1.62 / -0.37 | -1.02 / 0.10 | 0.06 / 0.69 | 0.64 / 0.86 | 0.75 / 0.73 | -0.24 / 0.13 |
| slope roughness 1 | -2.26 / -0.81 | -1.55 / -0.24 | -0.31 / 0.53 | 0.45 / 0.82 | 0.85 / 0.84 | -0.23 / 0.19 |
| lateral 10000 mm/h | 0.06 / 0.42 | 0.41 / 0.71 | 0.90 / 0.98 | 0.95 / 0.95 | 0.52 / 0.62 | -0.28 / 0.05 |
| lateral 36000 mm/h | 0.70 / 0.82 | 0.91 / 0.97 | 0.93 / 0.92 | 0.72 / 0.75 | 0.19 / 0.36 | -0.31 / -0.04 |
| lateral 100000 mm/h | 0.89 / 0.94 | 0.99 / 0.99 | 0.79 / 0.80 | 0.54 / 0.61 | 0.04 / 0.23 | -0.32 / -0.07 |
| soil 1 m | -7.89 / -2.51 | -6.55 / -1.64 | -4.04 / -0.40 | -2.22 / 0.22 | 0.31 / 0.71 | -0.07 / 0.29 |

- **The better the soil conducts water, the smaller the fitting roughness and the better the
  shape matches**: a larger lateral conductivity reduces the water stored in the soil and the
  saturated area, and the runoff comes earlier. The closest roughness falls from 10 and 5
  (first and second storm) at 3600 mm/h to 5 and 3 at 10000, 3 and 1 at 36000 and 1 and 1 at
  100000, and the fit rises from 0.75 and 0.86 to 0.99 and 0.99. In every case the closest
  roughness is near the "roughness that stores the same water on the surface" (7.2, 3.9, 1.5,
  0.7). In the process run with 100000 mm/h only the valley floors saturate (10 %); the soil
  water moves quickly down the slopes and seeps out in the valleys, and the hydrograph almost
  coincides with that of no infiltration with roughness 1. The effect of the wetness before
  the rain also becomes small (the runoff exceeds 1 mm/h after 3.7 hours in the first storm
  and 3.2 hours in the second).
- **The equivalent roughness used in practice corresponds to a soil that conducts water
  fast**: in the no-infiltration runs the runoff reaches 90 % of the rain after 3.7 hours
  with roughness 0.3 and 5.0 hours with roughness 1. The equivalent roughness used in practice
  for mountains (about 0.4–0.8) lies in between, and agrees with the value of the empirical
  flood concentration time for this catchment (4.8 hours). The process run is this fast when
  the lateral conductivity is 36000–100000 mm/h (6.0 and 4.8 hours); the base value of
  3600 mm/h does not reach 90 % during the 12 hours of rain. The equivalent roughness came
  out as large as 5–10 because the soil of the base setting releases water more slowly than
  this yardstick of real storm runoff. 36000–100000 mm/h (0.01–0.03 m/s) is beyond the range
  the user guide suggests (1000–10000 mm/h); it is not flow in the soil matrix but an
  effective value that lumps fast paths such as pipes. The equivalent roughness used in
  practice is tied to how the slope length is taken, and the definition of the flood
  concentration time is not the same as "the time to reach 90 % of the rain", so this
  correspondence is only a guide.
- **Soil depth and the wetness before the rain are hard to replace with a roughness**: the
  first storm of the process run with 1 m of soil (11 hours without runoff) is matched no
  better than a fit of 0.31 by any roughness. The rain that does not run off until the soil
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
  flow). The amount of rain needed before runoff appears in the first storm on dry soil (a
  little over 80 mm in this example) is set by the initial groundwater storage of zero and by
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
  flat reaches (48 % of the 11.7 km of main stem that runs on channel cells and 17 % of the
  49 km channel network, including the 1.5 km just upstream of the outlet), where water flows
  only by the slope of the water surface and therefore ponds. The catchment-mean surface water
  reaches 25 mm (18 mm of it on channel cells), and the little over three hours between the
  formation of the saturated area and the rise of the outlet runoff are mostly the time needed
  to fill this storage. Real streams probably route the water faster. Narrow channels can be
  represented with the subgrid channel width (`fn_width` in
  [Channels](../../../docs/en/users_guide/channel.md)), which this example does not use.
  Valleys without the channel mask (upslope area up to 1.3 km²) flow with the slope roughness.
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

- **Dry soil and empty channels at the start**: the response to the first storm (8 hours
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
  Log (S_total) and the cumulative rain balance within 0.11 mm over the 96 hours of the
  process run (the storage in the Log is printed in steps of 0.1 mm).
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
  parameter files to the `nx`, `ny`, `outlet_ij` and `gauge_ij` it prints.
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
