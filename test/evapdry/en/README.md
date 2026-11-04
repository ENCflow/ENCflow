# test/evapdry — Reduction of evapotranspiration by the dryness of the soil (evap_hglim)

> English mirror of test/evapdry/README.md. The Japanese file is the master copy.

[日本語](../README.md)

When `evap_hglim` of [evapotranspiration](../../../docs/en/users_guide/forcing.md#evapotranspiration-list_evap)
is given, the evapotranspiration taken from groundwater is reduced to the
fraction hg/evap_hglim while the subsurface storage hg is smaller than
evap_hglim (Ks = min(1, hg/evap_hglim); the same linear reduction as the
water stress coefficient of FAO-56;
[the explanation](../../../docs/en/users_guide/forcing_models.md) §3,
developer.md §27.2). Within a step, dhg/dt = −E·min(1, hg/evap_hglim) is
solved exactly, so hg after the rain should match the analytical solution
(linear at the rate E while above evap_hglim, then exponential decay with the
time constant evap_hglim/E) to rounding. This test checks that.

- **param.txt (compared with the regression reference)**: a flat closed
  domain (10 × 10 cells, dx = 10 m, uniform ground elevation). A bucket-type
  infiltration (capacity 200 mm/h, storage capacity 0.1 m) takes in all of
  one hour of uniform rain at 50 mm/h, and a constant potential
  evapotranspiration PET of 48 mm/day (2 mm/h) evaporates water from the
  subsurface storage. There is neither surface nor subsurface flow, so after
  the rain only evapotranspiration decreases hg. evap_hglim = 0.02 m (smaller
  than the 0.048 m after the rain: linear, then exponential decay). The rain
  carries a tracer at 1 mg/L (the water-quality ledger gives the rain total).
- **param_b.txt**: evap_hglim = 0.1 m (larger than the storage after the
  rain: exponential decay from the start, time constant 50 hours).
- **param_c.txt**: a control without evap_hglim (no reduction: the previous
  "take as much as there is"). hg falls linearly at the rate PET and runs out
  to 0 after about 25 hours.

## Configuration

| Item | param.txt | param_b.txt | param_c.txt |
|---|---|---|---|
| Terrain | flat closed domain (10 × 10 cells, dx = 10 m) | same | same |
| Water | rain 50 mm/h × 1 h (1 mg/L) | same | same |
| Subsurface | bucket (infiltration capacity 200 mm/h, storage capacity 0.1 m; no lateral flow) | same | same |
| Evapotranspiration | constant PET 48 mm/day, evap_hglim = 0.02 m | same PET, evap_hglim = 0.1 m | same PET, no evap_hglim |
| Time | dt = 10 s, 30 h | same | same |

| File | Content |
|---|---|
| `Run.sh` | compares Log.txt and evap.csv of param.txt with the reference (ULP = 0; the Runge column of the Log is excluded) → checks with `Check_evapdry.py` → runs param_b.txt and param_c.txt and checks them |
| `Run_MPI.sh N` | runs param.txt on N ranks, compares with the serial reference at ULP = 0 and checks it |
| `Check_evapdry.py decay\|evbal\|ledger` | subsurface storage after the rain (from 1.5 h; S_grnd of Log.txt) equal to the analytical solution (1e-9 of the value at 1.5 h) / final total storage + evapotranspiration = rain total (relative 1e-6) / closure of the water-quality ledger (evaporation leaves the substance behind) |

## Running

```bash
make
./Run.sh
./Run_MPI.sh 4
```

## Findings

| Configuration | hg at 1.5 h (m) | hg at 30 h (m) | Departure from the analytical solution (relative to the value at 1.5 h) |
|---|---:|---:|---:|
| param.txt (evap_hglim 0.02 m) | 0.048097 | 0.004714 | 3e-13 |
| param_b.txt (evap_hglim 0.1 m) | 0.049697 | 0.028105 | 1e-13 |
| param_c.txt (no reduction) | 0.047694 | 0 | 2e-13 |

- The departures are within the printed digits of Log.txt (14 digits). The
  equation is solved exactly within a step, so the result matches the
  analytical solution regardless of the time step.
- Evapotranspiration also acts during the rain, so hg at 1.5 h is less than
  the rain total (0.0507 m) and differs between the configurations (more
  remains where the reduction is stronger). The check starts the analytical
  solution from the value at 1.5 h.
- Without reduction (param_c.txt) the previous formula is used as is (the
  branch of the reduction is not taken).
