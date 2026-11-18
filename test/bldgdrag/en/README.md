# test/bldgdrag — Uniform flow in a channel with buildings (check of the building drag term)

> English mirror of test/bldgdrag/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Uniform flow in a channel given the building void ratio `fn_gv` and the mean
building size `fn_bb` is compared with the theoretical value of the building
drag term in the momentum equation
([ENC grid and time integration](../../../docs/en/users_guide/encgrid.md) §5;
developer.md §107).

## Theoretical value

In a cell with buildings, the equation for the edge-normal velocity $`u`$ has the
void ratio $`g_v`$ on the pressure term and the bed friction, plus the building drag.

```math
\lambda_m\frac{\partial u}{\partial t}
 = -\,g_v\,g\,\frac{\partial \eta}{\partial s}
   - \left[\,g_v\,\frac{g\,n^2}{h^{4/3}} + \frac{k\,C_D}{2}\,\frac{1 - g_v}{B}\right]|\mathbf{V}|\,u
```

$`B`$ is the mean building size, $`C_D`$ (`cd`) the drag coefficient and $`k`$ (`kk`)
a correction coefficient. The drag on the buildings is proportional to the submerged
frontal area $`B\,h`$, but the velocity equation divides it by the mass of the water
column, so the coefficient does not contain the depth. For uniform flow in a channel
of slope $`S`$, with unit-width discharge $`q = V h`$, the uniform depth $`h_u`$ is the
solution of

```math
g_v\,g\,S = \left[\,g_v\,\frac{g\,n^2}{h^{4/3}} + \frac{k\,C_D}{2}\,\frac{1 - g_v}{B}\right]\frac{q^2}{h^2}
```

(`uniform_depth` in `make_init.py`; bisection). With $`g_v = 1`$ it reduces to
Manning uniform flow.

## Setup

Length 2000 m, Δx = 5 m, slope 0.01, n = 0.03. A channel 4 cells (20 m) wide lies
between dry ground 12 m above the bed, and buildings are placed over the whole
channel. Reach inflow Q = q × 20 m at the west end, free outflow on the east edge.
The run starts from a depth of 1 m and lasts 90 minutes; measurements are taken over
x = 300–900 m, away from the inflow and from the drawdown at the downstream end.

| Configuration | gv | B (m) | cd | kk | q (m²/s) | Uniform depth h_u (m) | Velocity V_u (m/s) | Manning depth without buildings (m) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| shallow | 0.7 | 10 | 1.0 | 0.5 | 0.4 | 0.299 | 1.337 | 0.280 |
| deep | 0.7 | 10 | 1.0 | 0.5 | 8.0 | 2.897 | 2.762 | 1.691 |
| dense | 0.5 | 20 | 2.0 | 0.5 | 8.0 | 4.146 | 1.930 | 1.691 |

In shallow, Manning friction dominates (the building drag is 0.24 times it); in
deep, the building drag dominates (5 times). dense changes the void ratio, the
building size and the drag coefficient to check how the coefficients enter.

## Checks (Check_bldgdrag.py)

1. Steady state: the depths at 45 and 90 minutes differ by no more than 1 mm.
2. Uniform flow: the water-surface slope matches the bed slope within ±2 %.
3. Mass balance: the row-wise sum of V·h matches Q within 1e-3.
4. Agreement with the theoretical uniform flow: h/h_u and V/V_u are 1 ± 0.5 % in every row.
5. The building drag is acting: the uniform depth is deeper than the Manning depth
   without buildings (at least 1.05 times in shallow, at least 1.5 times in deep and dense).

In the measured runs, h/h_u and V/V_u are 1 ± 0.0001 in all three configurations. With
the drag coefficient multiplied by the depth (the error present until 2026-11-12;
developer.md §107), shallow gives 0.955, deep 2.33 and dense 2.99, which item 4 detects.

## Usage

```
make
./Run.sh            # serial (about 1.5 minutes for the 3 runs)
./Run_MPI.sh 2      # MPI
```

## What this does not cover

Only the uniform-flow balance is checked. The validity of the drag coefficients of
building groups themselves (comparison with flows in real urban areas) is out of scope;
`cd` and `kk` are calibration values
([ENC grid and time integration](../../../docs/en/users_guide/encgrid.md) §8).
