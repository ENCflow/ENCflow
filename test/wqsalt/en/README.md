# test/wqsalt — Water-quality additions for salinity, and the time-series input of potential evapotranspiration

> English mirror of test/wqsalt/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of the features that let [water quality](../../../docs/en/users_guide/wq.md) handle
substances concentrated by evaporation (salt and the like), and of the time-series input of
[evapotranspiration](../../../docs/en/users_guide/forcing.md#evapotranspiration-list_evap)
(developer.md §139). Every case is built so that the water does not move, or its motion does not
affect the result, and is compared with analytical solutions and conservation laws. There is no
reference.

| Case (param_<name>.txt) | Feature | Setup | Criterion |
|---|---|---|---|
| mix | Horizontal mixing `wq_diff` | Substance injected for 10 s at the centre of flat, closed still water (81 × 81 cells). D = 0.5 m²/s | Between 200 s and 600 s the variance of the distribution grows by 2·D·Δt = 400 m² in both x and y and the covariance does not grow (exact to rounding with the 8-neighbour discretization). The mass does not change |
| mixflow | Same | Sloshing started by a step in the depth of a closed box. Uniform initial concentration 100 mg/L | The concentration stays uniform |
| mixwall | Same | A dry ridge in the middle of the box. Substance injected on the west side only | The concentration east of the ridge is exactly 0, and the west approaches a uniform value |
| mixgv | Same | The building porosity of the east half of a still-water box is 0.5. Substance injected on the west side | The mass does not change, and the concentration ends uniform whatever the porosity (= injected amount ÷ water volume) |
| mixwd | Same | A still-water box divided into west and east by a column of subgrid channel cells 2 m wide (plan-area fraction 0.2; 0.1 in the two end cells). Substance injected on the west side | The mass does not change, and the concentration becomes uniform across the channel column |
| sat | Solubility `wq_csat` (precipitation) | Still water 0.5 m deep at 100 g/L evaporated at 0.1 m/h. Solubility 300 g/L | Substance of the water column = min(initial amount, solubility × depth before the evaporation); the rest is precipitate. Once dried up, all of it is precipitate |
| dis | Same (instantaneous dissolution) | Precipitate (west 100, east 30 kg/m²) on the bed of fresh water 0.2 m deep | West: concentration 300 g/L with 40 kg/m² of precipitate left; east: 150 g/L with the precipitate used up |
| disk | Dissolution rate `wq_kdis` | dis with k = 8.64 m/day (1e-4 m/s) | The concentration at the probe agrees with C = Csat (1 − exp(−k t / h)) (difference 1e-9 or less). The east stops at 150 g/L |
| inf | Dissolution by infiltrating water, and the cap on the concentration that moves with groundwater | 36.5 mm of rain on precipitate on dry ground. Bucket-type infiltration. Then a well pumps half of the groundwater (retardation factor R = 2) | Substance entering the ground = min(precipitate, solubility × infiltration). Substance carried out by the well = min(concentration, solubility)/R × pumped water |
| sea | Concentration of water entering from the sea `wq_sea_conc` | The west end is the sea. The tide level moves 0 → 2 m → 1.3 m and floods dry land | The concentration of the water on land and of the sea cells is 35 g/L. Amount entered from the sea − amount that left to the sea = mass on the surface |
| c0map | Map of the initial concentration `fn_wq_c0` | Still water at 100 mg/L west and 300 mg/L east of a dry ridge | The concentrations at the start and at the end stay as given |
| evts | Time series of potential evapotranspiration `f_evmodel = 5` | A triangular series 0 → 96 mm/day → 0 repeated twice by a cyclic forcing of 12 hours | Cumulative evaporation 24 mm per cycle and 48 mm per day (the sum over the steps matches the integral) |

| File | Content |
|---|---|
| `Run.sh` | Runs the 12 cases serially and judges them with `Check_cases.sh` (about 15 seconds) |
| `Run_MPI.sh N` | Runs the 12 cases on N ranks and judges them; for the 7 cases with transport across the band boundaries (mix, mixflow, mixwall, mixgv, mixwd, sea, c0map) it also compares Log.txt, wq.csv and the last concentration field byte by byte with the 1-rank run |
| `Check_cases.sh` | Judges all cases (calls `Check_wqsalt.py` with the arguments of each case) |
| `Check_wqsalt.py` | The checks themselves (Python standard library only) |
| `make_data.py` | Regenerates the inputs in `data_wqsalt/` (maps of depth, ground elevation, precipitate, initial concentration, sea mask, building porosity, channel mask and channel width) |

## How to run

```bash
make
./Run.sh
./Run_MPI.sh 2
```

## Findings

- The variance increment of horizontal mixing agrees with the theoretical 400 m² to a relative
  3e-9. Whatever the share of the diagonal links, the variance grows by 2·D·t in each direction.
- In cells with a building porosity or a subgrid channel width, the area of the link is multiplied
  by the smaller of the "fractions of the cell area that hold water" of the two sides. The flux is
  counted with the same value from both sides of the link, so even with fractions from 0.1 to 1
  the mass is conserved to rounding and the final concentration is uniform (mixgv, mixwd; the
  water volume is taken from the field A0000 that the run outputs).
- Evapotranspiration acts after the water-quality step, so precipitation is decided by the depth
  of one step earlier (the formula of the check includes this). The output concentration can
  exceed the solubility by the evaporation of one step.
- Dissolution with a rate solves the exponential formula exactly within the step, so it agrees
  with the analytical solution whatever the time step.
- The total rain of inf is 36.5 mm, including the part while the rain series is lowered to 0 in
  the minute after the first hour. The check uses the infiltration read from the subsurface
  storage of a cell without a well.
