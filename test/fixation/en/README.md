# test/fixation — checks of fixation (f_fixation)

> English mirror of test/fixation/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the process in which fixation advances on bars exposed at low flow
and resists re-erosion during floods (developer.md §84.6, docs/meander_plan.md §3.4).

## Setup

The southern 3 rows of a straight channel 10 cells wide (Δx = 1 m, slope 0.002,
dry banks of +2 m on both sides) are made a bar of +0.1 m (make_init.py). The
segment inflow at the west end is Q = 0.1 m³/s from 0 to 10 min (low flow; the
bar is dry) and 1.7 m³/s from 11 min (flood; the bar is submerged and swept by
bedload). The east side is free outflow. The soil thickness is 0 (non-erodible)
at both ends and connected by ramps, and the checks look only at the central
segment (columns 26–49). d50 = 2 mm, T_fix = 0.1 h = 360 s, morfac = 1.

| Configuration | Settings | Role |
|---|---|---|
| off | f_fixation = 0 | Baseline (the bar is eroded by the flood) |
| on | c_τ = 100, dz_reset = 0.1 m | The fixed bar is not eroded even by the flood |
| weak | c_τ = 0.5, dz_reset = 0.002 m | It is eroded and the fixation is reset |
| rough | on + c_n = 2 | The roughness triples on the fixed bar and the velocity drops |
| decay | on + T_dec = 0.1 h | The fixation of a bar submerged by the flood decays as exp(−t/T_dec) (§84.13) |
| susp_off | Suspended sediment 0.2 mm, fed at concentration 0.002 during the flood, no fixation | Baseline for comparison |
| susp_on / susp_on2 | Suspended sediment + fixation (f_esform = 1 / 2) | Fines accumulate on the fixed bar |
| rt1 → rt2 | rough split at 600 s and restored from save_rt | Restart round trip (including the rebuild of the dynamic roughness) |

## Checks (Check_fixation.py)

1. Growth law: for the bar and bank cells that stay dry throughout the low-flow
   period, a(600 s) = 1 − exp(−600/360) (to 1e-9 in the saved value
   geomorph_fixation.dat of rt1; to the print precision 1e-4 in the text output Fx).
2. a is exactly 0 in the channel cells that are always wet.
3. Effect: the bar of on has Δz ≥ 0 in every cell during the flood (zero outflow
   from fixed cells); the bar of off has 10 or more cells with Δz < −5 mm.
4. Reset: in the bar of weak at least 1 cell returns to a = 0, and
   zref − z ≤ dz_reset in every cell at the end (the invariant of the reset).
5. 0 ≤ a ≤ 1.
6. No trace when disabled (no Fx output in result_off, no private file in save_off).
7. Roughness: during the flood (1800 s) the velocity on the fixed bar in rough is
   less than 0.7 times that of on (measured 0.50), and the cross-sectional discharge
   Σ V h dy is within ±3 % of Q_in in both configurations.
8. Suspended sediment: with fixation the bar shows net deposition in every cell
   during the flood (Δz > 0), and the mean Δz is at least 2 cm larger than without
   fixation (for both f_esform = 1 and 2; measured +3.1 / +4.2 cm versus −1.0 cm).
9. Submergence decay: in the bar of decay, a(1800) = a_on·exp(−(1800 − t_w)/360)
   (a_on is the saved value of on = the value frozen at the submergence time t_w;
   relative 1e-3 between saved values), a of the banks that stay dry is identical
   to on (the decay acts only on wet cells), and a of the channel cells is 0.

Run.sh further confirms that state.dat and geomorph_fixation.dat of the restart
split continuation (rt1 → rt2) are bit-identical to the straight-through run
(rough). Run_MPI.sh performs the same checks under MPI and looks for bit identity
with save_*_serial (the serial and MPI builds are made with the strict flags
-O2 -ffp-contract=off and compared; with -Ofast the last digit fluctuates. §28.3).

## Usage

```
make
./Run.sh            # serial (9 runs, about 3 minutes)
./Run_MPI.sh 2      # MPI (2 ranks)
```
