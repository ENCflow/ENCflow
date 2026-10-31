# test/wave_shore — Verification of wave-driven longshore transport (fn_wave)

> English mirror of test/wave_shore/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The mechanism that drives longshore transport from the shoreline orientation
in the surf zone, with the offshore waves as given input (developer.md §84.15;
docs/wave_plan.md option A; both in Japanese), is verified against the linear
theory for a straight shoreline (Ashton & Murray 2006).

## Setup

800 m × 240 m (Δx = 2.5 m); a beach with a dry shore to the north that
deepens southward at a uniform slope of 0.02 (shoreline at y = 20 m, water
level 0; since the shoreline lies inside the domain, the result does not
depend on the treatment of the domain edges). A sinusoidal perturbation
η = a sin(2πx/L) (a = 6 m, L = 200 m) is placed on the shoreline
(`make_init.py`). The offshore waves are H₀ = 0.5 m, T = 5 s (breaking depth
h_b/γ = 0.86 m = a band 43 m from the shoreline). The shoreline orientation
is smoothed by the multi-pass kernel of physical length wave_lsm = 5 m
(= 2Δx) plus the local slope term wave_bslp = 5 (§84.15 stage 3 (a)). Bed
load f_fluvial = 1 is a prerequisite of the pathway (the water is still, so
the bed load itself does not move). morfac = 5; 1 h of hydraulics = 5 h of
morphology.

| Configuration | Wave direction | Role |
|---|---|---|
| low | 110° (α = 20° from the onshore normal, which points north) | Low angle: the perturbation decays by diffusion |
| high | 150° (α = 60°) | High angle: the perturbation grows by anti-diffusion at the growth rate of the linear theory |
| high0 | As above, wave_lsm = 0 | The former cell-radius kernel. A record that the irregularities grow at the grid scale |
| bar | 110°, straight shoreline + non-erodible submerged bar (x = 350–450 m, crest 0.2 m), f_wave_shadow = 1 | Stage 3 (b) partial shadowing: the lee of the bar rests, deposition at the updrift edge, erosion downdrift |
| bar0 | As above, f_wave_shadow = 0 | Control without shadowing |
| off | fn_wave given, f_wave_longshore = 0 | Zero addition when disabled (state.dat byte-identical to nowave) |
| nowave | No fn_wave | Reference for off |

## Checks (Check_wave_shore.py)

1. Low angle (α = 20°): the amplitude a(t) of the h = 0.5 m depth contour over
   the central 2 wavelengths (x = 200–600 m) decays as exp(−D k² t), and the
   decay rate agrees within ±35 % with D k² of the linear theory,
   D = Q_s'(α)/h_b, Q_s'(α) = K₂ H₀^{12/5} T^{1/5} cos^{1/5}α (cos²α − 1.2 sin²α)
   (measured: amplitude 6.0 → 3.10 → 1.52 m, ratio 1.02).
2. High angle (α = 60°): the same amplitude grows as exp(+|D| k² t), and the
   growth rate is 0.5–1.5 times the theoretical value (measured
   6.0 → 10.3 → 13.1 m, ratio 0.76). In addition, in the spectrum of the
   irregularities of the depth contour on the offshore side of the surf zone
   (h = 0.8 m), the power at wavelengths below 10 m is under 15 % (measured
   4 %; no grid-scale bars).
   2b. high0 (the former cell-radius kernel): the same power is 20 % or more
   (measured 28 %).
3. Volume conservation (closed domain; rounding at the printed precision is
   tolerated).
4. The state.dat of off and nowave are byte-identical (cmp in Run.sh).
5. Submerged detached breakwater (bar / bar0): with shadowing, the bed change
   Σ|Δz| at the centre of the lee (x = 360–440 m, 25 m from the shoreline) is
   at most 0.5 times that without shadowing (measured 16 versus 70 m³ = 0.23),
   the deposition at the updrift edge of the lee (x = 440–500 m) is at least
   1.5 times (measured 227 versus 101 m³), and the erosion over 100 m downdrift
   is at least 1.5 times (measured 267 versus 103 m³). Since there is no
   diffraction, the sand accumulates not at the centre of the lee but at its
   updrift edge (the same pattern as a detached breakwater in a one-line
   model).

## Running

```bash
make
./Run.sh          # generate inputs → low / high / high0 / bar / bar0 / off / nowave → Check (7 runs; about 20 minutes)
./Run_MPI.sh 4    # MPI. The rule is that state.dat is byte-identical to the serial run
```
