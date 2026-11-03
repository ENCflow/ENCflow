# test/gwwidth — Water handed between the subsurface and the surface on cells with a subgrid channel width

> English mirror of test/gwwidth/README.md. The Japanese file is the master copy.

[日本語](../README.md)

On cells with a [subgrid channel width](../../../docs/en/users_guide/channel.md#subgrid-channel-width)
(fn_width), the surface water depth is the depth in the channel part of the
cell (plan-area fraction wfrac). The subsurface storages (layer 1 hg, the
conduit layer hgc, and so on) are amounts on the plane of the whole cell, so
water handed between the two is converted so that the volumes match
(surface → subsurface by af/gv, subsurface → surface by 1/wfrac;
developer.md §26.1). Without this conversion, water seeping out of the
ground reaches the surface only in the channel-width fraction and the rest
is lost, and inflow into the conduit layer instead creates water. This test
checks the conversion.

- **param.txt (compared with the regression reference)**: a closed valley
  (12 × 8 cells, dx = 10 m). Slopes of 5 % on both sides fall to the valley
  floor in column 10, which is a subgrid channel 2 m wide (wfrac = 0.2).
  One hour of uniform rain at 50 mm/h infiltrates completely (Green-Ampt,
  infiltration capacity 200 mm/h, saturated at soil depth 0.5 m × effective
  porosity 0.1 = 0.05 m), collects in the valley through lateral groundwater
  flow (hydraulic conductivity 1e-2 m/s) and seeps out of the saturated
  valley floor. The rain carries a tracer at 1 mg/L.
- **param_nowidth.txt**: the same configuration without the channel width
  (conversion factor 1), as a control.
- **param_gwc.txt**: the same valley with an impervious surface; one hour of
  uniform rain at 20 mm/h flows through the inlets in every cell (1 per
  cell) into the conduit layer (storage capacity 0.01 m, crown at the
  ground, no lateral conveyance). When the conduits are full, the pressure
  head rises and water spouts back to the surface. The lowest channel cell
  of the valley floor has a land-side outfall (Cd·A = 0.05 m²). The rain and
  the spouted and outfall water have a concentration of 1 mg/L.

## Configuration

| Item | param.txt | param_nowidth.txt | param_gwc.txt |
|---|---|---|---|
| Terrain | closed valley (`data_gwwidth/z.txt`, channel mask `rw.txt`) | same | same |
| Channel width | 2 m (`width.txt`; wfrac = 0.2) | none | 2 m |
| Rain | 50 mm/h × 1 h (concentration 1 mg/L) | same | 20 mm/h × 1 h (concentration 1 mg/L) |
| Subsurface | Green-Ampt + lateral flow (layer 1) | same | conduit layer only (inlets, outfall) |
| Time | dt = 0.5 s, 6 h | same | dt = 0.5 s, 4 h |

| File | Content |
|---|---|
| `Run.sh` | compares Log.txt and wq.csv of param.txt with the reference (ULP = 0; the Runge column of the Log is excluded) → checks with `Check_gwwidth.py` → runs param_nowidth.txt and param_gwc.txt and checks them |
| `Check_gwwidth.py conserve\|rain\|match\|conc\|ledger` | total storage constant after the rain (relative 1e-10) / final total storage equal to the rain total (relative 1e-6; with the rain at 1 mg/L the ledger's in_rain_g is the rain volume) / final total storage equal to the control without width / concentration 1 ± 1e-3 mg/L in every cell deeper than 1 mm / closure of the water-quality ledger |

## Running

```bash
make
./Run.sh
./Run_MPI.sh 4
```

## Findings

| Quantity | After the fix | Before the fix (executable of 2026-11-03) |
|---|---|---|
| Final total storage of param.txt (m; domain mean) | 0.0508264 (equal to the rain total and to the control without width) | 0.0241 (53 % lost) |
| Concentration on the valley floor in param.txt (mg/L) | 0.99987–0.99994 | 3.65–6.21 (the seepage water shrinks and looks concentrated) |
| Final total storage of param_gwc.txt (m) | 0.0203306 (equal to the rain total) | 0.0211 (3.6 % created by the inflow) |
| Concentration in param_gwc.txt (mg/L) | 1.00041–1.00050 | 1.00042–1.00047 |

- Before the fix, the concentration in param_gwc.txt was close to 1 because
  the spouted volume and the mass carried with it were counted in the same
  units (the gain or loss of water came from the missing conversion between
  the conduits and the surface, and is detected by the total storage).
- The small departure of the concentration from 1 (about 1e-4) is the same
  before and after the fix; it is an existing offset from evaluating the
  proportional transfer of infiltration and inflow with the water depth at
  the end of the step (the tolerance ±1e-3 of the check allows for it).
- The exchange on cells with a section shape (sigma law) remains an
  approximation and is outside this test (developer.md §26.1,
  [users guide](../../../docs/en/users_guide/channel.md#cross-section-shape-sigma-law)).
