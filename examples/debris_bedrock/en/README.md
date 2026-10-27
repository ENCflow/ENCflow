# examples/debris_bedrock — Rock erosion by debris flows: how far one debris flow erodes the rock of a stream

> English mirror of examples/debris_bedrock/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A debris flow is released once from the head of a stream whose slope eases in steps, and we
look at where and how much the flowing mixture erodes the rock. The comparison covers two
resistance laws with their erosion-deposition equations, a bed of bare rock or of a deposit, the
erosion threshold, and a clear-water flood with the same discharge. The features used are debris
flows `f_debris` and the debris-flow term `rock_kdb` of bedrock incision `f_rockinc`
([chapter on landform change in the users guide](../../../docs/en/users_guide/geomorph.md#rock-erosion-by-debris-flows-rock_kdb),
equations and sources in the
[supplement](../../../docs/en/users_guide/sediment.md#bedrock-incision-by-flowing-water-f_rockinc)).
The example recomputes the single-event comparison of docs/mountain_stream_plan.md §12 (§12.4,
in Japanese) with the implemented law. The checks are in [test/dbrock](../../../test/dbrock/).
The values are illustrative and are not calibrated for any particular stream.

## Settings

| Item | Value |
|---|---|
| Stream | 10 m wide (5 cells, Δx = 2 m, walls on both banks), 400 m long. The slope from the head is 0.35 (0–120 m) → 0.20 (to 220 m) → 0.10 (to 300 m) → 0.04 (to 360 m) → 0.01 (to 400 m). Free outflow at the south end, n = 0.05 |
| Debris flow | A triangular hydrograph of the mixture from the 5 cells at the head (peak 40 m³/s at 10 s, ending at 70 s). Concentration C = 0.35 (26 m³/s of water and 14 m³/s of solids; 490 m³ of solids in total) |
| Resistance and erosion-deposition | Takahashi–Nakagawa (`f_dbres = 3`, `f_dbed = 3`; d_L = 0.1 m, δe = 1e-4, δd = 0.5) and Coulomb + Manning (`f_dbres = 1`, `f_dbed = 1`; δe = 7e-4, δd = 0.05). Common: φ = 35°, λ = 0.4, low-velocity settling `f_dbstop = 1` (`db_vstop` = `db_wstop` = 0.05 m/s), slope correction `f_gravity_correction = 1` |
| Bed | Bare rock (sd = 0) and a deposit 0.3 m thick |
| Rock erosion | k_d = 1.8e-4 m/s, τ_cd = 1 kPa, m_d = 1, H* = 0.05 m. k_d was chosen in §12.4 so that the mean over the stream (0–360 m) for Takahashi–Nakagawa on bare rock is 1 cm per event |
| Time | 300 s with dt = 0.02 s. The landform is updated every step (`dt_geomorph = 0`, `morfac = 1`). Output every 10 s |

| Configuration | Contents |
|---|---|
| `param_T_b.txt` | Takahashi–Nakagawa, bare rock |
| `param_T_c.txt` | Takahashi–Nakagawa, 0.3 m deposit |
| `param_C_b.txt` | Coulomb + Manning, bare rock |
| `param_C_c.txt` | Coulomb + Manning, 0.3 m deposit |
| `param_T_b05.txt`, `param_T_b20.txt` | T_b with the threshold τ_cd at 0.5 kPa and 2 kPa |
| `param_W.txt` | A clear-water flood with the same discharge (bare rock; the 40 m³/s of the mixture as clear water). Bed load `f_fluvial` and fluvial plucking (`rock_kp`) with the same coefficient, threshold and exponent |

| File | Contents |
|---|---|
| `make_init.py` | Writes the terrain, soil depth and `param_*.txt` (constants kept in pairs with `plot_results.py`) |
| `plot_results.py` | Figures `figs/*.png` (`en/figs/` with `en`) and tables (standard output: erosion per reach, ledgers, share of rock-derived sediment, mobile layer at the end) |

## Running

```bash
make                                   # links to the executables in ../../bin/
python3 make_init.py                   # writes the inputs and param_*.txt (same as the bundled ones)
for c in T_b T_c C_b C_c T_b05 T_b20 W; do
  ./encflow param_$c.txt > Screen_$c.log   # about 30 s each
done
python3 plot_results.py | tee analysis.txt    # figures and tables (python3 plot_results.py en for the English figures)
```

## Results

### Rock erosion by one debris flow

![Longitudinal distribution of rock erosion and the mobile layer at the end](figs/erosion.png)

Rock erosion per event in each reach (cm; mean of the cells of the reach) and the bulk volume of
eroded rock (the end-of-run line "rock erosion by debris flows: eroded"; for W, "rock incision:
plucked").

| Configuration | Slope 0.35 | 0.20 | 0.10 | 0.04 | 0.01 | Ledger (m³) |
|---|---|---|---|---|---|---|
| T_b Takahashi–Nakagawa, bare rock | 1.94 | 0.90 | 0.015 | 0 | 0 | 32.4 |
| C_b Coulomb + Manning, bare rock | 1.08 | 0.38 | 0 | 0 | 0 | 16.8 |
| T_c Takahashi–Nakagawa, deposit | 0.51 | 0.003 | 0 | 0 | 0 | 6.1 |
| C_c Coulomb + Manning, deposit | 0.33 | 0.001 | 0 | 0 | 0 | 3.9 |
| T_b05 threshold 0.5 kPa | 5.79 | 2.91 | 0.28 | 0.002 | 0 | 100.7 |
| T_b20 threshold 2 kPa | 0.39 | 0.067 | 0 | 0 | 0 | 5.4 |
| W clear water, same discharge (fluvial plucking) | 0.56 | 0.10 | 0 | 0 | 0 | 7.7 |

- **The erosion is concentrated in the steep reaches.** The driving stress
  τ_d = ρ(1 + sC) g_e h_t tanθ exceeds the threshold of 1 kPa only in the thick flow of the
  reaches with slopes of 0.2 or more. At slopes of 0.10 or less even bare rock hardly erodes.
- **Difference between the resistance laws**: in the reach with slope 0.35, Coulomb + Manning
  erodes 0.56 times as much as Takahashi–Nakagawa. Its flow is thinner and faster in the steep
  reach (largest flow depth 0.87 m against 1.26 m in the comparison of §12.4), so τ_d, which is
  proportional to the depth, is smaller.
- **Peak upstream of a slope break**: the deposit in the reach with slope 0.10 backs the flow up,
  and the mixture becomes thick and slow at the end of the reach with slope 0.20. In the cell of
  C_b 205 m from the head, h_t ≈ 1.3 m and |V| ≈ 0.5 m/s from 70 to 120 s, which gave the
  largest erosion of that reach (1.55 cm). Split with output every 1 s, 55 % of the erosion of C_b
  in the reach with slope 0.20 (12 % of the whole of C_b) came from flow with |V| < 1 m/s (1 % in
  the same reach for Takahashi–Nakagawa). The quasi-static driving stress does not depend on the
  velocity, so as long as the flow moves above the gate (|V| ≥ `db_vstop` = 0.05 m/s), a slow and
  thick flow erodes until the cover becomes thick. This is a property of the adopted law (§12.5),
  not a behaviour confirmed by observations.
- **Mobile layer at the end**: the steep reach is almost swept clean (0 for T_b), and the
  sediment deposits at the slope breaks (1.4 m for T_b and 1.1 m for C_b at 220 m from the head).
  The eroded rock enters the mobile layer 1:1, and the erosion-deposition equation decides whether
  the flow takes it up or leaves it as cover.
- **Rock-derived sediment**: the solids of the eroded rock are 19.4 m³ for T_b (4.0 % of the
  490 m³ of solids that entered), 2.1 % for C_b, 0.7 % for T_c and 0.5 % for C_c. Almost all of
  the sediment of one debris flow comes from the head.

### Comparison with a clear-water flood

The clear-water flood with the same discharge (W) eroded 0.56 cm in the reach with slope 0.35 and
0.10 cm in the reach with slope 0.20 (29 % and 12 % of T_b; 24 % in the ledgers). The stress of W,
however, is that of the fluvial plucking law, the Manning closure of the cell velocity
τ_b = ρ g n² V²/h^{1/3}. This closure comes out larger than the balance in steep uniform flow
(developer.md §88.4, item 1; in steady uniform flow with the same width, grid and discharge as the
reach with slope 0.35 of this stream, τ_b / ρ g h tanθ = 1.41 in the central column). Evaluated
with the same quasi-static stress as the debris-flow term, the same flow erodes 0.20 cm and
0.01 cm (7 % of T_b as the mean over the stream; post-processing of §12.4). The definition of the
stress changes the result threefold, but in both cases the debris flow erodes more (4.2 times in
the ledgers, and 14 times as the mean over the stream between quasi-static stresses).

### Effect of the cover

![Mobile layer and rock erosion over time with the deposit](figs/cover.png)

- With a deposit 0.3 m thick, the erosion in the reach with slope 0.35 drops to 26 %
  (Takahashi–Nakagawa) and 30 % (Coulomb + Manning) of that on bare rock, and is almost 0 at
  slopes of 0.20 or less.
- The rock starts to erode only after the flow has stripped the deposit down to a few cm (a few
  times H*). At 21 m from the head with Takahashi–Nakagawa, the deposit is stripped completely from
  40 to 60 s, and 0.80 cm of rock is eroded (1.96 cm on bare rock). At 101 m the deposit only
  thins to 3 cm, and the erosion is 0.23 cm. In the reach with slope 0.20 the deposit is not
  stripped; it remains or thickens.
- The H* = 0.05 m of the exposure exp(−sd/H*) follows the observation that a deposit about 5 cm
  thick protects the bed from impacts (McCoy et al. 2013; references in sediment.md).

### Effect of the threshold

![Rock erosion with different thresholds](figs/threshold.png)

- Halving the threshold (0.5 kPa) makes the erosion in the reach with slope 0.35 3.0 times larger
  (5.79 cm), and the erosion extends into the reach with slope 0.10. Doubling it (2 kPa) gives
  0.20 times (0.39 cm). The threshold sets both the magnitude of the erosion and the range of
  slopes that it reaches.
- With a low threshold, the long tail of the falling limb also erodes. Downstream, where the
  recession is slower, the rock erodes for longer, so with 0.5 kPa the erosion grows downstream
  even within the steep reach (from 5.2 cm at 5 m from the head to 6.6 cm at the end of the reach,
  115 m).

## Linking to long-term runs

One event erodes a few mm to a few cm, so changing the shape of a valley takes many debris flows
and the flood runs between them. Debris-flow event runs and flood runs (`morfac > 1` or the
conversion by an intermittency factor; [examples/mountain_valley](../../mountain_valley/en/README.md))
are chained alternately with `f_state_restore = 2` (a new time axis; dt can change). With
`f_rockinc = 1` in both, the cumulative incision `Ri` continues (procedure in the
[users guide](../../../docs/en/users_guide/geomorph.md#rock-erosion-by-debris-flows-rock_kdb)). The
interval between debris flows (once in how many years) is chosen by the user.

## Notes (scope of this example)

- A single-layer mixture does not resolve the front where boulders gather. Observations show most
  of the erosion during the passage of the coarse front (Illgraben; §12.4, item 6), whereas in the
  comparison of §12.4 the first 5 s of the front contributed 12 %. The effect of the front is
  calibrated into the coefficient k_d of the whole event.
- k_d and τ_cd are calibration values with no standard values in the literature (lowering of mm to
  cm per event has been reported; references in sediment.md).
- The quasi-static driving stress does not depend on the velocity, so slow and thick flows also
  erode ("peak upstream of a slope break" above). The velocity gate is shared with `db_vstop` of
  the low-velocity settling.
- The run covers one event only, without uplift, weathering or repeated debris flows.

## Related documents

- [Users guide: landform change](../../../docs/en/users_guide/geomorph.md#rock-erosion-by-debris-flows-rock_kdb),
  [supplement](../../../docs/en/users_guide/sediment.md#bedrock-incision-by-flowing-water-f_rockinc)
  (equations and sources),
  [debris flows and slope failure](../../../docs/en/users_guide/massflow.md) (resistance laws and
  erosion-deposition equations of the mixture)
- Checks: [test/dbrock](../../../test/dbrock/en/README.md) (analytical solution of self-cover,
  invariance to the update interval, concentration and velocity gates, conservation in a closed
  box, input errors)
- Examples of bedrock incision by flowing water: [examples/bedrock_cover](../../bedrock_cover/en/README.md),
  [examples/mountain_valley](../../mountain_valley/en/README.md)
- Design: docs/mountain_stream_plan.md §12 and docs/developer.md §88.18 onwards (in Japanese)
