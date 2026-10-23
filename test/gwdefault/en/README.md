# test/gwdefault — equivalence check of the groundwater module defaults

> English mirror of test/gwdefault/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the policy of giving defaults to the physical and calibration
parameters of the groundwater module (the `&list_gwflow` family)
(developer.md §64). For each of four configurations, the **minimal input**
(`param_<tag>.txt`, with the defaults omitted) and `param_<tag>x.txt`, which
**states every default explicitly**, are run, and it is checked that all save
files (state.dat and the private files of each module) and Log.txt are
byte-identical and that "(default)" is printed on screen the expected number
of lines (18). There are no figures (an identity check).

## Configuration

Common: a closed-domain slope of 40 × 20 cells (`z.txt`), initial water 0.05 m, dt = 0.2 s, 900 s.

| Configuration | Enabled | Omitted → values shown as defaults |
|---|---|---|
| a | Bucket (`f_gwvertical = 1`) | gw_infil_mmh = 10 mm/h, gw_capacity = 0.2 m |
| b | Green-Ampt + lateral flow + weathered bedrock layer (`f_gwlayer2 = 1`) | sd0 = 1 m, gw_ksv_mmh = 10, gw_psif = 0, gw_ksh_mmh = 360, gw2_depth = 3 m, gw2_sy = 0.05, gw2_infil_mmh = 1 |
| c | Green-Ampt + frozen ground (`f_gwfrost = 1`, `fn_meteo`) | sd0, gw_ksv_mmh, gw_psif, fro_fifull = 20 ℃·day |
| d | Green-Ampt + conduit continuum layer (`f_gwconduit = 1`, infiltration water `gwc_leak_layer = 1`) | sd0, gw_ksv_mmh, gw_psif, gwc_cap = 0.01 m, gwc_depth = 3 m, gwc_sy = 0.05, gwc_slot_sy = 1e-3, gwc_leak_mmh = 10 |

In configuration d, `gwc_inlet` (inlet density) and `gwc_cnd_m2s` (conveyance
density) are given values (no default is set, because 0 is the explicit
statement of "no lateral flow" / "no exchange").

| File | Contents |
|---|---|
| `Run.sh` | Runs 4 configurations × 2 and checks `diff -r save_<tag> save_<tag>x`, `cmp Log.txt` and the number of "(default)" lines = 18 |
| `Run_MPI.sh N` | Runs the same pairs with N ranks and makes the same comparison (byte-identical at np = 2, 4) |

## Running

```bash
make
./Run.sh          # 8 runs (tens of seconds). All byte-identical, PASS
./Run_MPI.sh 4
```

## Findings

| Configuration | Byte identity of save / Log | "(default)" lines |
|---|---|---|
| a bucket | identical | 2 |
| b Green-Ampt + lateral + layer 2 | identical | 7 |
| c Green-Ampt + frozen ground | identical | 4 |
| d Green-Ampt + conduit layer | identical | 5 |
| Total | PASS | 18 (expected 18) |

- The basis of the defaults (Green-Ampt parameters by soil texture, soil
  thickness of forest soils, frost depth by the Stefan equation, etc.) is
  summarized in the table of developer.md §64. When changing a default,
  update that table and the explicit values in `param_<tag>x.txt` as a pair.
- All existing references specify the values explicitly, so they are
  unchanged by the introduction of defaults.
- Checks of the same type: [test/icevap](../../icevap/en/README.md) (interception and evapotranspiration), [test/lava](../../lava/en/README.md)
  configuration 3, [test/glacier](../../glacier/en/README.md) configuration 3, [test/tide](../../tide/en/README.md) configuration 2,
  configurations 4 / 5 of [test/driftwood](../../driftwood/en/README.md) / [test/bldgdebris](../../bldgdebris/en/README.md).

## Related documents

- [docs/users_guide/gwflow.md](../../../docs/en/users_guide/gwflow.md) — "Just try it (minimal input)" and the defaults of each parameter
- developer.md §62 (default policy), §64 (table and verification of the gwflow defaults)
