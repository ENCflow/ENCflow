# test/wave_river — Testing the river-mouth rule wave_vmax (separating wave-driven longshore transport from river flow)

[日本語正本](../README.md)

> English mirror of `test/wave_river/README.md`. The Japanese version is authoritative.

The longshore-transport model (`fn_wave`; developer.md §84.15) treats any wet
cell deeper than the surf zone as a wave source. A river channel whose flow
depth exceeds the breaking depth h_b/γ can therefore become a source, while
shallower channel sections (bars and riffles) are classified as surf zone and
experience longshore transport. This was the mechanism behind divergence in
`examples/delta`. The river-mouth rule `wave_vmax` excludes cells whose speed
|V| exceeds a threshold from both the sources and the surf zone (exposure 0,
i.e. shadow). This test is a minimal reproduction.

## Setup

The domain is 300 m × 200 m (Δx = 2.5 m). A channel 10 m wide, with bed
elevation −1.2 m, crosses the non-erodible land (+1.5 m) in the west and
enters the sea to the east (beach slope 0.02; offshore water depth 2 m).
A riffle at x = 40–60 m has bed elevation −0.5 m and water depth about
0.6 m < h_b/γ = 0.86 m. Inflow is 10 m³/s (channel speed 0.76–1.0 m/s),
and the eastern boundary uses long-wave radiation.

Offshore waves have H₀ = 0.5 m, T = 5 s, and propagation direction 150°
(the same oblique incidence as `examples/delta`). Bedload is supplied at
transport capacity; the sediment layer in the channel is 1 m thick.
With morfac = 10, 30 minutes of hydrodynamic time represents 5 hours of
morphological time (`make_init.py`).

| Configuration | Settings | Role |
|---|---|---|
| nowave | No fn_wave | Baseline channel-bed evolution; river flow alone erodes the riffle by 0.7 m |
| novmax | Waves enabled, no rule | Reproduces the problem: pools become sources, and waves change the bed by 1 m from the riffle through the channel |
| vmax | Waves enabled, wave_vmax = 0.5 m/s | The channel is essentially unchanged relative to nowave (difference ≤ 0.014 m, due to hydrodynamic feedback from changes in the river-mouth bar), while waves still act on the sea side |

## Checks (Check_wave_river.py)

1. vmax: in the channel at least 15 m upstream of the mouth,
   |Z − Z_nowave| is below 0.05 m and below 0.05 times the novmax difference.
2. novmax: the difference in the same reach is at least 0.5 m, confirming
   that waves enter the channel without the rule.
3. vmax: on the sea side, Σ|Z − Z_nowave| dA is at least 10 m³, confirming
   that the rule does not stop longshore transport there.
4. MPI: `state.dat` is byte-identical to the serial result (`cmp` in
   `Run_MPI.sh`). The Japanese source reports that bit identity with the
   rule disabled (`wave_vmax` unspecified) was checked by comparing the
   `low` case in `test/wave_shore` before and after adding the rule.

## Running the test

For every language, work directly in `test/wave_river`, not in `en/`.
The shared `Run.sh` and `Run_MPI.sh` use the authoritative inputs.
The `en/param_*.txt` files translate the comments; they do not replace the
official test inputs. To run one directly, remain in the case directory and
use, for example, `./encflow en/param_vmax.txt`. The output paths are the same
as in the originals, so consecutive runs in the same working copy may
overwrite results.

```bash
make
./Run.sh          # Generate inputs → nowave / novmax / vmax → checks (3 runs; about 1 minute)
./Run_MPI.sh 4
```
