# Suspend and Restart

> English mirror of docs/users_guide/restart.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Running a long computation in segments, or branching multiple
scenarios from an intermediate state -- that is what the state save
(save) and restore (restore) features are for. They are controlled by
two flags in `&list_sysparam`.

| Parameter | Default | Meaning |
|---|---|---|
| f_state_save | 0 | 1: save the state to dir_save (default `save/`) at the end of the computation |
| f_state_restore | 0 | 1: **restart** from the saved state (time continues) / 2: **use the saved state as an initial condition** (new time axis) |
| dir_save | "save" | directory used for saving and restoring |

What is saved is the state of the fields such as depth and
topography, the internal state of the dynamics (edge velocities and
discharges), and the private state of modules that hold internal
state. The files are written with zero-suppressing lossless
compression, so even wide-area computations stay at a realistic size.

## Restarting (f_state_restore = 1)

Runs the continuation of a suspended run. **The time axis continues**,
and the times, step numbers, and even the sequential numbers of
output files are identical to a run without interruption.

Usage is just "add `f_state_restore = 1` to the original parameter
file". To extend the computation, also increase `tt`.

```
  f_state_save = 1          ! saving-side run: save to save/ at the end
```
```
  f_state_restore = 1       ! restarting-side run: continue from save/
  tt = 172800.0             ! (extend the end time if prolonging)
```

- **The results match a run without interruption bit for bit**
  (ENCflow's restart is not "roughly the same" but exactly the same).
- Since the save destination equals the load source, a **restart
  chain** of save -> restart -> save -> ... runs without editing
  parameters (for long-term runs advanced one cycle at a time).
- `t0` and `dt` must match the values at save time (a mismatch stops
  the run; restarting with a changed dt is not possible).
- On restore, the version, grid counts, and real-number precision are
  checked, and a non-matching file stops with an explicit error
  (accidentally reading the save of a different case cannot happen).

**What does not continue across a restart**: the maximum-value
statistics (the H9999 family) and the cumulative discharge are not
saved; they are re-accumulated from zero within the restart run
(becoming statistics of the restarted interval only). If you need
through-run statistics, post-process the distributed outputs.

## Using as an initial condition (f_state_restore = 2)

Carries over **only the fields** from the saved state, and starts a
new time axis (new `t0`, new calendar `date0_c`, and **dt may also be
changed**) from the first step. The typical use is **spin-up
(warm-up)**:

1. Run for a while with, e.g., normal river discharge to let the
   fields settle, and save
2. Using those fields as the initial condition, run multiple flood
   scenarios with a new reference date and time

Unlike mode 1, there is no contract of "exact agreement with a run
without interruption" (since the purpose is generating initial
conditions). Also, **time-series forcings** such as tide, boundary
inflow, and rainfall **are read from the beginning of the new time
axis**, so making the forcing values at the start of a scenario
consistent with the saved state is the user's responsibility (if they
disagree, disturbances caused by the step change run through the
early computation).

## Restrictions

- State save and restart apply to computations on the ENC grid (the
  default). The legacy STG scheme kept for comparison cannot restart
  (it stops with an explicit error).
- The execution environment (number of threads, number of MPI ranks)
  may differ from save time (the results do not change -- see
  [Parallel Execution](parallel.md)).
