# test/bankhalo — the effective plan-area ratio af read by the overshoot cap of levee overflow at band boundaries (MPI)

> English mirror of test/bankhalo/README.md. The Japanese file is the master copy.

This case checks a real bug in which the overshoot cap of levee overflow (`cap_overshoot`; developer.md §68.29 (C'))
read a stale effective plan-area ratio `s%af` at MPI band boundaries (developer.md §120). It is a check-type case
without a reference; the result is decided by the exit codes of `Run.sh` and `Run_MPI.sh`.

## What it checks

The effective plan-area ratio af = gv × wfrac × v(h)/h (void ratio of buildings × plan-area fraction of the channel
width × wetted fraction of the σ cross-section) is updated every step when any of channel width, σ cross-section or
a changing void ratio is active. The overshoot cap of levee overflow converts the response of the water level with the
af of the cells on both sides of a levee edge, so that the discharge of deeply submerged overflow does not overshoot
the level difference in one step. At a band boundary the neighbouring cell is in a halo row, so if the af in the halo
does not match the owner's value, runs with two or more ranks do not match one rank.

## Configuration

| Item | Value |
|---|---|
| Domain and grid | a closed box of 20 × 16 cells (Δx = Δy = 10 m). Four rows per rank even with np = 4 |
| Channel | column i = 10 runs north–south (bed −1 m, sub-grid width 4 m = plan-area fraction 0.4, roughness 0.03). The ground on both banks is 0 m |
| Levee | crest of the channel cells 0.5 m (landside ground + 0.5 m) |
| Initial water level | west bank 1.50 m, east bank 1.45 m, channel 1.475 m (the levees are deeply submerged) |
| Time | dt = 0.5 s, 10 minutes |

| Settings | Contents |
|---|---|
| `param.txt` | channel width only (af = gv × 0.4) |
| `param_sect.txt` | channel width + channel cross-section shape σ(h) = (h/D)^0.5 (D = crest − bed = 1.5 m) |

The band boundary crosses the channel, so the neighbouring cell of a diagonal levee edge falls in a halo row.

| File | Contents |
|---|---|
| `Run.sh` | runs the two configurations serially and checks them with `Check_bankhalo.py` |
| `Run_MPI.sh [N]` | runs with N ranks (default 2; N ≤ 8) and with one rank (the same executable) and compares Log.txt, water level E0001 and depth H0001 byte by byte; also `Check_bankhalo.py` |
| `Check_bankhalo.py` | the water volume S of the closed box is kept (first and last agree to a relative 10⁻¹²), the level difference between the banks shrinks from 0.05 m to less than half, and the east bank rises by 5 mm or more |
| `make_bankhalo.py` | makes the inputs (ground, channel mask, channel width, initial water level) |

## Results (2026-11-24; gfortran 13.3, -Ofast)

| Executable | np = 2, 4 against one rank |
|---|---|
| before the fix | does not match in either configuration (water level differs by up to 1×10⁻⁴ m, maximum speed 0.044 m/s against 0.058 m/s; the water volume S agrees) |
| after the fix | byte-identical in both configurations |

With -Og -fcheck=all the checks also pass and np = 2 is bit-identical with the serial run. The level difference
between the banks shrinks from 0.05 m to 0.000 m (4 digits of the output) in 10 minutes.

## What this case does not check

- The halo exchange of af changed by the feedback of building destruction on the void ratio (`m_bldgdebris`; the same
  kind of fix, without a check).
- The accuracy of the overshoot cap itself (checked under §68.29).
