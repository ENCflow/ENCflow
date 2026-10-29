# test/prmap — Time units of rainfall maps and the runoff rate

> English mirror of test/prmap/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of how ENCflow interprets the accumulation time of the values in rainfall
map files (`dt_mapunit(_c)`) and the time interval of the map files
(`dt_maplist(_c)`) ([the chapter of the User's Guide](../../../docs/en/users_guide/forcing.md),
developer.md §88). `Check_prmap.py` confirms the specification: numbers are in
minutes, strings `_c` with a unit are read in that unit (a number without a unit
is in minutes), `_c` takes precedence when both are given, and without either,
prtype = 2 assumes accumulation over 24 hours (mm/day) and prtype = 3 the file
interval. It also confirms that dt_prupdate has no effect with prtype = 3, and
that saving in the middle of a frame and restarting agrees with the continuous
run (no reference comparison). It also confirms that the runoff rate
`runoff_rate` scales both the water balance (S) and the output Pr in every
prtype, and that the output Pr is in mm/h (with prtype = 3 too, it is the
converted value, not the file value itself; developer.md §88.5).

## Set-up

Uniform rain is given for 1.5 h (dt = 10 s) to a flat closed domain of 4 × 8 cells
(Δx = Δy = 10 m; 2 rows per rank even with np = 4). Surface water does not move,
so S in the Log (the domain-mean depth, with all significant digits by
`f_disp_debug = 1`) equals the accumulated rainfall. The prtype = 2 map
`prmap.txt` is 24 mm in all cells (the multiplier is constant at 1), the
prtype = 3 list is `f1.txt`–`f3.txt` (6, 12 and 0 mm in all cells), and the
prtype = 1 series is constant at 4 mm/h. The runoff-rate configurations (`*_rr`)
write the rainfall intensity field Pr every 15 minutes (`f_out_pre = 1`,
`dt_file = 900`).

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
| `param_p3_prupdate.txt` | p3_def with `dt_prupdate = 7` | not used with prtype = 3; same as p3_def | 17.97 mm |
| `param_p3_save.txt` / `param_p3_restart.txt` | p3_prupdate saved at 45 minutes and restarted | the Log after the restart is the same as p3_prupdate | 17.97 mm |
| `param_p1_rr.txt` | prtype = 1 (4 mm/h), `runoff_rate = 0.75` | both the water balance and Pr are 0.75 times (Pr = 3 mm/h) | 4.5 mm |
| `param_p2_rr.txt` | p2_def with `runoff_rate = 0.75` | likewise (Pr = 0.75 mm/h) | 1.125 mm |
| `param_p3_rr.txt` | p3_def with `runoff_rate = 0.75` | likewise; Pr is converted to mm/h (12 mm/h × 0.75 = 9, 18, 0 mm/h) | 13.48 mm |

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
  without a unit, of the configuration where `_c` takes precedence, and of the
  prtype = 3 configuration with dt_prupdate written, is bit-identical to that of
  the corresponding configuration.
- **Restart**: after saving in the middle of the second frame (45 minutes) and
  restarting, the rows of the Log after the restart are bit-identical to the
  continuous run (the current frame is read again right after the restart;
  developer.md §7).
- **Runoff rate and output Pr**: in the configurations with a runoff rate, S
  agrees with the accumulated rainfall × runoff rate (relative 1e-9), and every
  cell of Pr0000–Pr0006 (every 15 minutes) agrees, within the rounding of the
  display (f12.4), with the rainfall intensity × runoff rate at that time in mm/h.
- **Display of the adopted value**: the screen shows the adopted value, such as
  `precip: dt_mapunit = 1440.00000 min (default)` (and, when the runoff rate is
  not 1, `precip: runoff_rate = .75000 (applied to the rainfall and Pr)`).

## Running

```bash
make
./Run.sh          # 12 serial configurations and save/restart + checks (a few seconds)
./Run_MPI.sh 4    # MPI (np ≤ 4); besides the checks, the Log.txt of all configurations is byte-identical to the serial run
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1, Ubuntu 24.04)

With the code before the fix of the time units (developer.md §88.2; dt_mapunit
used as seconds, dt_mapunit_c overwritten by the default, dt_maplist_c without
effect on the frame interval), p2_min gave 2160 mm (60 times), p2_c1h and p2_c60
1.5 mm, p2_prio 2160 mm, p3_c30 24.03 mm and p3_unit 721 mm, and 26 items failed,
including the display of the adopted values and the items below. With the code
where only the units were fixed, the defect where dt_prupdate thins out the frame
switching (developer.md §88.4) left the second and later frames of p3_prupdate
unread (S at 1:00 was 12.0 mm instead of 17.97 mm), and 3 items failed: S and the
agreement of the Log of p3_prupdate, and the restart.

After both fixes all items pass, and the largest relative difference of S is
2e-11 (rounding of the digits shown). The Log of the configurations without a
specification (p2_def, p3_def) is bit-identical to that before the fixes, and the
Log of p3_def, p3_c30 and p3_unit is bit-identical before and after the fix of
§88.4. With MPI np = 1, 2 and 4, the Log.txt of all configurations is
byte-identical to the serial run (also with an -Og -fcheck=all build, the serial
run and np = 2 agree without out-of-bounds accesses).

**Runoff rate and output Pr (2026-10-29; developer.md §88.5)**: with the code before the
change, S of p1_rr and p2_rr was 6.0 mm and 1.5 mm without the runoff rate (the runoff
rate scaled only the output Pr, not the water balance), and Pr of p3_rr was the file
value itself (6, 12 = mm/30 min), and 6 items failed, including the 3 displays of the
runoff rate. After the change all items pass, and the Log of the 9 configurations without
a runoff rate and of the restart is bit-identical before and after the change. With MPI
np = 1, 2 and 4 all items pass as well, the Log.txt of all configurations is
byte-identical to the serial run, and the Pr output of the runoff-rate configurations is
byte-identical between np = 4 and the serial run (also with an -Og -fcheck=all build, the
serial run and np = 2 agree without out-of-bounds accesses).
