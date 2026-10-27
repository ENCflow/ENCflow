# test/prmap — Time units of rainfall maps (prtype = 2, 3)

> English mirror of test/prmap/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of how ENCflow interprets the accumulation time of the values in rainfall
map files (`dt_mapunit(_c)`) and the time interval of the map files
(`dt_maplist(_c)`) ([the chapter of the User's Guide](../../../docs/en/users_guide/forcing.md),
developer.md §88). `Check_prmap.py` confirms the specification: numbers are in
minutes, strings `_c` with a unit are read in that unit (a number without a unit
is in minutes), `_c` takes precedence when both are given, and without either,
prtype = 2 assumes accumulation over 24 hours (mm/day) and prtype = 3 the file
interval (no reference comparison).

## Set-up

Uniform rain is given for 1.5 h (dt = 10 s) to a flat closed domain of 4 × 8 cells
(Δx = Δy = 10 m; 2 rows per rank even with np = 4). Surface water does not move,
so S in the Log (the domain-mean depth, with all significant digits by
`f_disp_debug = 1`) equals the accumulated rainfall. The prtype = 2 map
`prmap.txt` is 24 mm in all cells (the multiplier is constant at 1), and the
prtype = 3 list is `f1.txt`–`f3.txt` (6, 12 and 0 mm in all cells).

| Configuration | Specification | Interpretation | Rain in 1.5 h |
|---|---|---|---|
| `param_p2_def.txt` | prtype = 2, nothing given | accumulation over 24 hours (mm/day) = 1 mm/h | 1.5 mm |
| `param_p2_min.txt` | `dt_mapunit = 60` | accumulation over 60 minutes = 24 mm/h | 36 mm |
| `param_p2_c1h.txt` | `dt_mapunit_c = "1h"` | same as p2_min (the Log is bit-identical) | 36 mm |
| `param_p2_c60.txt` | `dt_mapunit_c = "60"` | a number without a unit is in minutes; same as p2_min | 36 mm |
| `param_p2_prio.txt` | `dt_mapunit = 60` and `dt_mapunit_c = "1d"` | `_c` takes precedence; same as p2_def | 1.5 mm |
| `param_p3_def.txt` | prtype = 3, `dt_maplist = 30` | switched every 30 minutes, values accumulated over 30 minutes | 17.97 mm |
| `param_p3_c30.txt` | `dt_maplist_c = "30"` | a number without a unit is in minutes; same as p3_def | 17.97 mm |
| `param_p3_unit.txt` | `dt_maplist_c = "0.5h"`, `dt_mapunit = 60` | switched every 30 minutes, values accumulated over 60 minutes (mm/h) | 8.98 mm |

The prtype = 3 frames are switched by the time at the end of a step (step it uses
the frame that contains the time it·dt). The first frame is therefore one step
shorter (1790 s), and the rain of p3_def falls slightly short of 6 + 12 = 18 mm.

## Checks (Check_prmap.py)

- **Accumulated S**: S in the Log agrees within a relative 1e-9 with the
  rainfall intensity of each step accumulated by the rule above (rounding to the
  14 digits shown in the Log is at most 3e-11 even for the smallest S; a mix-up of
  units gives a factor of 24 or 60).
- **Agreement of other forms**: the Log.txt of the configurations that give the
  same time as a number in minutes, as a string with a unit or as a string
  without a unit, and of the configuration where `_c` takes precedence, is
  bit-identical to that of the corresponding configuration.
- **Display of the adopted value**: the screen shows the adopted value, such as
  `precip: dt_mapunit = 1440.00000 min (default)`.

## Running

```bash
make
./Run.sh          # 8 serial configurations + checks (a few seconds)
./Run_MPI.sh 4    # MPI (np ≤ 4); besides the checks, the Log.txt of all configurations is byte-identical to the serial run
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1, Ubuntu 24.04)

With the code before the fix (dt_mapunit used as seconds, dt_mapunit_c
overwritten by the default, dt_maplist_c without effect on the frame interval),
p2_min gave 2160 mm (60 times), p2_c1h and p2_c60 1.5 mm, p2_prio 2160 mm,
p3_c30 24.03 mm and p3_unit 721 mm, and 21 items including the display failed.
After the fix all items pass, and the largest relative difference of S is 2e-11
(rounding of the digits shown). The Log of the configurations without a
specification (p2_def, p3_def) is bit-identical to that before the fix. With MPI
np = 1, 2 and 4, the Log.txt of all configurations is byte-identical to the serial
run.
