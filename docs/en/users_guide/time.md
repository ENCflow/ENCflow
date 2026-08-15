# Time Management

> English mirror of docs/users_guide/time.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

The time axis of ENCflow is a single one of "elapsed seconds". On top
of it, a "calendar (date and time)" used only by the features that
need it can be overlaid. All time-related parameters are in
`&list_sysparam`.

## Time axis and time step

| Parameter | Default | Meaning |
|---|---|---|
| t0 | 0 | computation start time (s) |
| tt | 0 | computation end time (s). **An absolute time, not a duration** (the end point on the time axis measured from t0) |
| dt | 0 | time step (s). Must be specified |

The total number of steps is (tt - t0)/dt. The in-computation time is
always defined exactly as `t = t0 + dt x (number of steps)` and is
shown in the time column of the screen and log.

The time step dt governs the stability and accuracy of the
computation. The guide is the Cn_max column (Courant number) on the
screen; settings that greatly exceed 1 become unstable. For the actual
relationship between accuracy and computational cost, see
[Tutorial Steps 1-2](../../../tutorials/wave/en/README.md#coarsening-the-time-step).

## Specifying times as strings (`*_c`)

Instead of seconds, times can also be specified as "number + unit"
strings. The corresponding parameter names end in `_c`, and **if both
are written, the `_c` version takes precedence**.

```
  tt_c = "24h"              ! same as tt = 86400.0
  dt_file_c = "10min"       ! same as dt_file = 600.0
```

The unit is exactly one of `d` (`day`), `h` (`hour`), `m` (`min`),
`s` (`sec`), and decimals such as `"1.5d"` can be used (compound
notation such as `"1h30m"` is not allowed). Since this avoids hand
computation of seconds for long runs, `_c` versions exist for all of
`t0/tt/dt/dt_disp/dt_file/dt_recrd/st_file/et_file/st_recrd/et_recrd`.

## Display and output intervals

| Parameter | Default | Meaning |
|---|---|---|
| dt_disp | 60 | interval of screen and log display (s) |
| dt_file | 3600 | interval of distributed file output (s) |
| dt_recrd | 60 | interval of probe / transect (fn_record) output (s) |
| st_file / et_file | 0 / -1 | time window in which distributed file output occurs (s). et = -1 means "until the end" |
| st_recrd / et_recrd | 0 / -1 | time window of probe output (s) |

When you want fine output only during a specific event period in a
long run, combining the st/et windows with split execution via
[the restart feature](restart.md) is practical.

## Calendar (date and time)

For features that depend on the season or the date (monthly
coefficients of evapotranspiration, day-boundary handling of snow
accumulation and snowmelt, temperature correction of water quality,
etc.), the calendar date of simulation time t=0 can be specified.

```
  date0_c = "2019-10-11"          ! or "2019-10-11 09:00"
```

- If a feature that uses the calendar is enabled but date0_c is
  absent, the run stops at initialization with a message to that
  effect. If no feature uses the calendar, it need not be specified.
- The time anchor of time-series inputs such as distributed
  temperature files is the simulation time (elapsed time from t=0).
  date0_c only gives "what calendar time t=0 is" and never shifts the
  interpretation of input series.

## Time on restart

On suspend and restart (save/restore) the time axis itself continues
-- the times and step numbers of the restart run match a run without
interruption exactly, and the results match bit for bit. To extend a
computation, just increase tt and restart. For details see
[Suspend and Restart](restart.md).

## Cyclic forcing (for long-term runs)

Specifying a period in `t_cycle_c` (e.g. `"365d"`) repeats the
time-series forcing cyclically, which can be used for
millennium-scale landform development experiments and the like (for
what it applies to, see the developer document
[developer.md Sec. 32.4](../../developer.md) (in Japanese)). It is not
used in ordinary computations.
