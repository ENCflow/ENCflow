# test/gwlateral — analytical verification of lateral groundwater flow (f_gwlateral)

> English mirror of test/gwlateral/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of lateral groundwater flow (`f_gwlateral = 1` in `&list_gwflow`;
the nonlinear Boussinesq equation, developer.md §16.1). On a flat base with
a small undulation of the subsurface storage, the lateral flow follows the
linearised Boussinesq equation

∂η/∂t = D ∇²η, D = K_sh h̄ / s_y

(η: undulation of the subsurface storage, h̄: saturated thickness). The
check script `Check_gwlateral.py` compares two configurations with this
solution. There is no reference; the check decides pass or fail.

## Configuration

| Item | Configuration 1 (param.txt → result) | Configuration 2 (param_strip.txt → result_strip) |
|---|---|---|
| Domain and grid | 121 × 121 cells (Δx = 1 m), flat, no flux on all four sides | 3 × 40 cells (a north-south strip), otherwise the same |
| Initial subsurface storage | hg = 0.2 m + 4 mm · exp(−r²/(2σ²)), σ = 4 m (a mound in the centre) | hg = 0.2 m + 4 mm · cos(π s/L), L = 40 m (s is the distance from the north edge) |
| Groundwater | sy0 = 0.2 (saturated thickness h̄ = 1 m), sd0 = 2 m, `gw_ksh_mmh = 36000` (K_sh = 0.01 m/s) → D = 0.05 m²/s | The same |
| Time | dt = 0.5 s, 1800 s. Distributions (bil) every 300 s | dt = 0.25 s, 3600 s. Distributions every 600 s |

The initial subsurface storage is made from an initial depth of the same
shape (written by `make_init.py`), which a Green-Ampt model with a very large
infiltration capacity (`gw_ksv_mmh = 3.6e6`, `gw_psif = 0`) moves entirely
into the ground in the first step. The distributions are written as bil
(float32) and read without display rounding.

- **Configuration 1 (interior diffusion)**: the second moment of the mound
  grows at d⟨r²⟩/dt = 4D whatever its initial shape. The discrete operator
  that combines the eight-direction shares gives the same value in the
  interior, whatever `gw_diagratio` is. In 30 minutes the mound spreads to
  σ ≈ 14 m but does not reach the edges 60 m from the centre, so the
  comparison covers the interior free of edge effects.
- **Configuration 2 (conductance along walls)**: on an interior grid the
  decay rate of the undulation would be λ = D k² (k = π/L). The east and west
  edge columns, however, have no outward diagonal links, so their north-south
  conductance is 1 − d/2 = 0.707 times the interior value (d is the default
  `gw_diagratio` 2/(2+√2)). The mean over the three columns is
  (2 × 0.707 + 1)/3 = 0.805 times, and the check confirms that the decay rate
  matches this discrete prediction. The shallow water solver has a
  correction that moves the blocked diagonal shares (f_opening_dynamic); the
  lateral groundwater flow does not (how to handle this is under discussion;
  developer.md §16.6). The strip runs north-south so that the MPI band
  decomposition (in the j direction) cuts across the undulation.

| File | Content |
|---|---|
| `make_init.py` | Writes the initial depth distributions (data_gwlateral/h_gauss.txt, h_strip.txt); Run.sh and Run_MPI.sh call it first |
| `Run.sh` | Runs both configurations serially and checks them with `Check_gwlateral.py` |
| `Run_MPI.sh N` | Runs the same checks on N ranks and compares the distribution outputs (Hg*.bil) and Log.txt (without the Runge column) byte by byte with np = 1 of the same binary. Configuration 2 has 40 rows, so N ≤ 20 |
| `Check_gwlateral.py` | Analytical checks: `gauss` checks the ratio of d⟨r²⟩/dt over 300–1800 s to 4D (tolerance 0.5 %) and the linearity; `strip` checks the ratio of the decay rate to the discrete prediction with the walls (tolerance 0.5 %) and the uniformity of the exponential decay. Both confirm with all digits of the Log that S_grnd stays at the initial amount of water and that no surface water remains |

## Running

```bash
make
./Run.sh
./Run_MPI.sh 4
```

## Findings

| Quantity | Computed | Theory |
|---|---|---|
| Configuration 1: d⟨r²⟩/dt (300–1800 s) | 0.200014 m²/s | 4D = 0.2 m²/s (ratio 1.00007) |
| Configuration 2: decay rate | 2.4806e-4 1/s | Discrete prediction with the walls 2.4820e-4 (ratio 0.99945) / interior theory D k² = 3.0843e-4 (ratio 0.804) |

- The remaining difference in configuration 1 (7e-5) is of the size of the
  nonlinearity (the interface saturated thickness changes with the
  undulation) and the float32 rounding of the distribution outputs. The total
  subsurface storage (S_grnd in the Log) is unchanged in all digits at all
  times.
- The decay in configuration 2 is 20 % slower than the interior theory
  because of the reduced conductance along the walls. Preliminary runs with
  other strip widths also followed the prediction: 0.414 times for a strip
  one column wide and 0.985 times for one 40 columns wide (developer.md §16.6).
- With MPI, np = 1, 2 and 4 all give distribution outputs and Logs identical
  byte for byte to the serial run (2026-10-30).

## Related documents

- [docs/en/users_guide/gwflow.md](../../../docs/en/users_guide/gwflow.md) — `f_gwlateral`, `gw_ksh_mmh`, `gw_diagratio`
- [docs/en/users_guide/gwflow_models.md](../../../docs/en/users_guide/gwflow_models.md) §4 — the lateral flow equations and the conductance along walls
- developer.md §16.1 (design of the lateral flow), §16.6 (record of this check and of the conductance along walls)
