# test/icevap — Equivalence check of the defaults for rainfall interception and evapotranspiration

> English mirror of test/icevap/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This case verifies the policy of giving defaults to the physical parameters
of rainfall interception (`fn_intercept`) and evapotranspiration (`fn_evap`)
(developer.md §66). In three configurations it checks that the save and
Log.txt of a minimal input (defaults omitted) and of an input with the
defaults written explicitly are byte-identical, and that "(default)" is
displayed on 3 lines of the screen output. Same style as
[test/gwdefault](../../gwdefault/en/README.md); there are no figures.

## Configuration

Common: a closed-domain slope of 40 × 20 cells (`z.txt`), dt = 0.2 s, 900 s.

| Configuration | Enabled | Omitted → value displayed as default |
|---|---|---|
| e | Fixed interception ratio (`f_icmodel = 1`), rainfall 36 mm/h | ic_alpha = 0.15 |
| f | Initial loss (`f_icmodel = 2`), rainfall 36 mm/h | ic_smax_mm = 1.5 mm |
| g | Constant evapotranspiration (`f_evmodel = 1`), initial water 0.05 m | evap0 = 3.0 mm/day |

| File | Contents |
|---|---|
| `param_e.txt` / `param_ex.txt`, `param_f.txt` / `param_fx.txt`, `param_g.txt` / `param_gx.txt` | Minimal input / defaults written explicitly |
| `Run.sh` | Runs the 3 pairs and checks `diff -r save_<tag> save_<tag>x`, `cmp Log.txt` and the number of "(default)" lines = 3 |
| `Run_MPI.sh N` | Runs the same pairs with N ranks |

## Running

```bash
make
./Run.sh          # 6 runs (tens of seconds). PASS when all are byte-identical
./Run_MPI.sh 4
```

## Findings

| Configuration | Byte identity of save / Log | "(default)" line |
|---|---|---|
| e Fixed interception ratio | Identical | `intercept: ic_alpha = 0.1500 (default)` |
| f Initial loss | Identical | `intercept: ic_smax_mm = 1.5000 mm (default)` |
| g Constant evapotranspiration | Identical | `evap: evap0 = 3.0000 mm/day (default)` |

- The basis of the defaults (interception ratio 0.15, initial loss 1.5 mm,
  evapotranspiration 3 mm/day) is in the table of developer.md §66. When
  changing a default, update the table and `param_*x.txt` as a pair.
- How to use interception and evapotranspiration is taught in Step 5
  (rainfall interception and infiltration) of
  [tutorials/chichibu](../../../tutorials/chichibu/en/README.md).

## Related documents

- [docs/users_guide/forcing.md](../../../docs/en/users_guide/forcing.md) — settings for rainfall interception and evapotranspiration
- developer.md §62 (policy on defaults), §66 (defaults and verification of intercept, evap and lavaflow) (in Japanese)
