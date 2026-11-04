# test/gwsect — Water exchanged between the surface and the subsurface or water sources on cells with a section shape σ

> English mirror of test/gwsect/README.md. The Japanese file is the master copy.

[日本語](../README.md)

On cells with a [cross-section shape (sigma law)](../../../docs/en/users_guide/channel.md#cross-section-shape-sigma-law)
(p_sect_m), the surface water depth h is the depth of the water level, and the
volume is proportional to the rectangular-equivalent depth v(h) (below D, the
volume grows with depth at the rate of the water-surface width σ(h) = (h/D)^m).
Modules outside the shallow-water computation add water to the surface and take
it in v, not in the depth (h' = v⁻¹(v(h) + Δv); developer.md §26.2). Adding to
the depth itself would increase the volume by only σ(h) times the amount, so
seeping water and melting snow would vanish, and infiltration would hand the
ground only 1/(m+1) of the volume removed. This test checks that.

- **param.txt (compared with the regression reference)**: the same closed
  valley as [test/gwwidth](../../gwwidth/en/README.md) (12 × 8 cells,
  dx = 10 m; column 10 is a subgrid channel 2 m wide, wfrac = 0.2), with the
  section shape σ(h) = (h/D)^0.5 (transition depth D = excavation depth 0.5 m)
  on the channel. One hour of uniform rain at 50 mm/h infiltrates
  (Green-Ampt), collects in the valley through lateral groundwater flow and
  seeps into the σ channel on the valley floor. The rain carries a tracer at
  1 mg/L.
- **param_nowidth.txt**: without the channel width; σ applies to the section
  over the full cell width.
- **param_gwc.txt**: an impervious surface; one hour of uniform rain at
  20 mm/h flows through the inlets in every cell into the conduit layer. When
  the conduits are full, water spouts back to the surface; the lowest channel
  cell of the valley floor has a land-side outfall. The rain and the spouted
  and outfall water have a concentration of 1 mg/L.
- **param_snow.txt**: an impervious surface (no groundwater); an initial snow
  cover of 20 mm on every cell melts at an air temperature of 10 ℃ with a
  degree-day factor of 20 mm/℃/day (gone in 2.4 hours).

## Configuration

| Item | param.txt | param_nowidth.txt | param_gwc.txt | param_snow.txt |
|---|---|---|---|---|
| Terrain | closed valley (`data_gwsect/z.txt`, channel mask `rw.txt`, excavation 0.5 m) | same | same | same |
| Section shape | σ(h) = (h/D)^0.5, D = 0.5 m | same | same | same |
| Channel width | 2 m (`width.txt`) | none | 2 m | 2 m |
| Water | rain 50 mm/h × 1 h (1 mg/L) | same | rain 20 mm/h × 1 h (1 mg/L) | initial snow 20 mm |
| Subsurface | Green-Ampt + lateral flow (layer 1) | same | conduit layer only (inlets, outfall) | none |
| Time | dt = 0.5 s, 6 h | same | 4 h | 6 h |

| File | Content |
|---|---|
| `Run.sh` | compares Log.txt and wq.csv of param.txt with the reference (ULP = 0; the Runge column of the Log is excluded) → checks with `Check_gwsect.py` → runs the other three configurations and checks them |
| `Run_MPI.sh N` | runs param.txt on N ranks, compares with the serial reference at ULP = 0 and checks it |
| `Check_gwsect.py conserve\|rain\|conc\|ledger` | total storage S_total constant (after the rain; from the start for the snowmelt; relative 1e-10) / final total storage equal to the rain total (relative 1e-6) / concentration 1 ± 1e-3 mg/L in every cell deeper than 1 mm / closure of the water-quality ledger |

## Running

```bash
make
./Run.sh
./Run_MPI.sh 4
```

## Findings

| Quantity | After the fix | Before the fix (executable of main on 2026-11-04) |
|---|---|---|
| Final total storage of param.txt (m; domain mean) | 0.0508264 (equal to the rain total) | 0.0496 (2.5 % lost) |
| Final total storage of param_nowidth.txt (m) | 0.0508264 | 0.0413 (19 % lost) |
| Final total storage of param_gwc.txt (m) | 0.0203306 (equal to the rain total) | 0.0210 (3.5 % created by the inflow into the conduits) |
| Total storage of param_snow.txt (m; surface + snow) | 0.0200000 (constant) | 0.0198 (1 % of the melt water lost) |
| Concentration on the valley floor (mg/L) | 0.99986–0.99993 (conduits 1.00044–1.00049) | 1.02–1.03 (without width 1.31, conduits 1.0004–1.0037) |

- The concentration exceeded 1 before the fix because the fraction of the
  proportional transfer of infiltration on σ cells was taken from the water
  level: the infiltrating water took away too little substance, and the water
  left on the surface looked concentrated. After the fix, both the record of
  infiltration and the fraction use the volume (rectangular-equivalent depth).
- The small departure of the concentration from 1 (about 1e-4) is the existing
  offset from evaluating the proportional transfer of infiltration and inflow
  with the depth at the end of the step (the same as test/gwwidth; the
  tolerance ±1e-3 of the check allows for it).
- The amount of infiltration itself (the drop of the water level =
  infiltration over the wetted width) is unchanged. The equalization limit of
  the exchange with the conduit layer is an approximation linearized with the
  water-surface width σ(h) at the current depth (water is conserved).
- Pore water of landform change, lava, the VZ outlet, glacier melt water and
  the change of the void ratio use the same function (`sect_add_vh`); this test
  does not run those configurations.
