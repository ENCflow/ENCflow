# test/bedmix — Verification of mixed grain sizes (f_bedmix)

> English mirror of test/bedmix/README.md. The Japanese file is the master copy.

[日本語](../README.md)

developer.md §84.19, docs/mixed_sediment_plan.md §6 (both in Japanese). The bed load is split into size
classes and the bed composition is kept in one exchange layer and one substrate (Hirano type); this case
verifies it through limits, theoretical values, recomputation of the formulas and balances.

The channel is a straight channel 5 cells wide (dx = dy = 1 m) and 60 cells long between dry, high banks.
The inflow segment at the west end carries the unit-width discharge of the Manning normal depth times the
width; the east edge is a free outflow (n = 0.03). make_init.py generates the inputs for each type:

| Type | Slope | Normal depth | Soil thickness of the bed | Banks | Last 4 columns downstream |
|---|---|---|---|---|---|
| std | 0.002 | 0.5 m | 1 m | 2 m high, soil thickness 0 | soil thickness 0 (non-erodible bed) |
| deep | 0.001 | 1.0 m | 0.5 m | 2 m high, soil thickness 0 | soil thickness 0 |
| free | 0.002 | 0.5 m | 1 m | 2 m high, soil thickness 0 | mobile bed (to look at the outflow through the open boundary) |
| bank | 0.002 | 0.5 m | 1 m | 1 m high, soil thickness 1 m (mobile banks) | soil thickness 0 |

## Configurations

| Configuration | Settings | Check |
|---|---|---|
| single | std, single size 3 mm, capacity feed | reference for equal |
| equal | std, 3 classes all of 3 mm (fractions 0.2, 0.3, 0.5), exchange layer 5 m thick (thicker than the soil layer = the exchange layer is the whole column), capacity feed | the bed agrees with single (maximum difference < 1e-10 m), the composition stays at its initial value (< 1e-12), the total net outflow through the open boundary agrees with single (relative 1e-8). The equal-mobility limit |
| single_te → equal_te | single and equal with the effective shear of Ashida and Michiue added (`f_taupart = 2`; developer.md §121) | the beds agree with each other (< 1e-10 m) and the net outflows through the open boundaries agree (relative 1e-8) and are smaller than without the effective shear (the factor (u*e/u*)³ obtained with the d_m of the classes acts the same as the single-size factor) |
| single_tp → equal_tp | single with the steep-gravel roughness partition added (`f_taupart = 1`, `fluv_d84` = 3 mm), and equal with the partition added and no `fluv_d84` (the D84 is computed from the exchange-layer composition of each cell; developer.md §122) | the beds agree with each other (< 1e-10 m) and the net outflows through the open boundaries agree (relative 1e-8) and are at least 0.1 % smaller than without the partition (with 3 mm and a depth of about 0.1 m the factor is φ ≈ 0.985) |
| tpmix1 → tpfix1, tpmix → tpfix | hide1 (0.5, 2 and 8 mm) with the roughness partition (`f_taupart = 1`) added, with the D84 from the composition (tpmix) and with the D84 of the initial composition (3.8193664156 mm by the interpolation in the logarithm of the size; 17 digits) fixed by `fluv_d84` (tpfix). One step (0.1 s) and 100 s | after one step the beds agree (< 1e-10 m; the composition is still the initial one) and `fluv_d84` equals the value of the formula in the check; after 100 s the beds differ (> 1e-6 m) and the outflow with the D84 from the composition is smaller (coarsening makes the D84 larger) |
| single_su → equal_su | bed load and suspended load (`f_suspend = 1`) of a single size of 0.5 mm, and mixed sizes with 3 classes all of 0.5 mm and the composition 1, 0, 0 plus suspended load (class 1 is the suspended load; developer.md §122). std, capacity feed | the beds and the suspended load hs agree with each other (< 1e-10 m) and the composition stays at class 1 only (< 1e-12). The single-size limit of the link to the suspended load |
| susp | free, 0.3, 2 and 8 mm (0.3, 0.4, 0.3), class 1 is the suspended load, no feed (clear-water inflow), 2 probes (record_susp.txt) | the residuals of the bed balance of each class (class 1 including what went to the suspended load) and of the suspended balance (stock, exchange, inflow and outflow through the open boundaries) < 1e-10 m³; the exchange counted on the bed side and on the suspended side agree (relative 1e-10); the composition is within 0 to 1 and sums to 1; the last probe column is Dm (mm), and its first and last records are within 1e-5 mm of the values from the composition |
| suw | susp with the middle row of the channel given a subgrid channel width of 0.6 m (rw_suw.txt, width_suw.txt) | with the weight of the channel area fraction, the balance of each class and the suspended balance still close (< 1e-10 m³) and the two sides of the exchange agree |
| sueq | susp with the capacity feed of bed load and the equilibrium-concentration feed of suspended sediment (inflow_cs_eq) | the equilibrium concentration is multiplied by the class-1 fraction of the exchange layer of the inflow cell, so in 160 s the class-1 fraction of the inflow cells changes by less than 0.02 and the bed by less than 1 mm (what remains is the entrainment until the suspended load fills the flow at the start; developer.md §123.7); the balances close |
| armor | deep, 1 mm and 20 mm at 0.5 each, no hiding, no feed (the coarse class is below its threshold and does not move) | the lowering of the column at the upstream end agrees with the static-armouring value L_a F_0 / (1 − f_sub) (< 1e-6 m) and the fines there are depleted (< 1e-6); the fine fraction decreases monotonically; its decay rate is within 3 % of the rate of the one-cell formula dF/dt = −(1 − f_sub) Q F / L_a evaluated from the output hydraulics |
| hide1 → hide2 | free, 0.5, 2 and 8 mm (0.3, 0.4, 0.3), modified Egiazaroff (default). Saved at 100 s and continued to 160 s | the volume of each class that left through the downstream open boundary in 100–160 s (ledger) is within 0.5 % of the value from Ashida and Michiue (1972) eqs. (31) and (32) with the depth, velocity and composition of the downstream cells |
| bcfeed | std, 3 classes, capacity feed | the bed and composition of the inflow cells do not change (< 1e-12); the bed downstream moves |
| bclim | bcfeed with a 2 mm exchange layer, landform updates every 10 s and morfac 10, so that the per-class supply limiter fires in the inflow cells | the feed is built from the net outflow after the limiter, so the bed and composition of the inflow cells do not change (< 1e-12; developer.md §123.7); the bed downstream moves |
| bank | bank, 3 classes, bank erosion and repose collapse, total feed 1e-3 m³/s with a constant composition 0.2, 0.5, 0.3 | the residual of the balance of each class (initial and final stock, feed, net outflow through the open boundary) < 1e-10 m³; the feed equals total × composition × time (relative 1e-9); the compositions of the exchange layer and substrate are within 0 to 1 and sum to 1 (< 1e-12); the banks move |
| qbmix | std, a feed series per class (qbmix.txt) | the feed in the ledger is within 0.2 % of the integral of the (piecewise-linear) series; the balance closes (< 1e-10 m³) |
| rfs1 → rfs3 | rockfall and talus on a mesa (as in test/rockfall: a plateau 20 m wide and 10 m high on a 41 × 41 m plain), with only the soil layer collapsing (soil thickness 20 m). A single size of 3 mm and a 0.5, 2 and 8 mm mixture (exchange layer 0.3, 0.4, 0.3; substrate 0.1, 0.3, 0.6) (developer.md §123) | the ground elevation, soil thickness and talus thickness agree (< 1e-10 m; a collapse does not select grain sizes), the balance of each class closes (< 1e-10 m³), and the mean fraction of the coarse class (8 mm) in the talus exceeds 0.5 (not capped by the exchange-layer thickness; the deep part of the column, the substrate composition, is carried) |
| rfb1 → rfb3 | only the top 1 m of the plateau is soil, bedrock below. Bedrock collapse (`rf_bedrock = 1`). The mixture gives the composition of the debris from bedrock `rf_frac` = 0.05, 0.15, 0.8 | the ground elevation, soil thickness and talus thickness agree, the balance closes including the production from bedrock, the total production equals the lowering of the bedrock (relative 1e-9) and the class ratios are `rf_frac` |
| rfsea1 → rfsea3 | rfb with the west side (x < 10 m) made sea cells (the west wall of the plateau faces the sea) | the ground elevation, soil thickness and talus thickness agree, the balance closes including the outflow into sea cells |
| cr1 → cr3 | depth-dependent creep at the edge of the mesa (`creep_hstar` = 0.5 m, soil thickness 20 m). The mixture uses an exchange layer 5 cm thick | the ground elevation and soil thickness agree, the balance closes, and the exchange-layer supply limiter does not act |
| ls1 → ls3 | wave-driven longshore transport (a sinusoidal shoreline, test/wave_shore reduced to 200 × 100 m). The mixture is 0.25, 0.5 and 1 mm with an exchange layer 0.1 m thick | the ground elevation and soil thickness agree (the CERC formula does not depend on grain size), the balance closes, and the exchange-layer supply limiter does not act |
| rt1 → rt2 | bank split at 150 s | state.dat and geomorph_bedmix.dat bit-identical to bank |
| surt1 → surt2 | susp split at 80 s | state.dat and geomorph_bedmix.dat bit-identical to susp |
| rfrt1 → rfrt2 | rfb3 split at 30 s | state.dat, geomorph_bedmix.dat and geomorph_rockfall.dat (talus) bit-identical to rfb3 |
| nofrac | only a total feed, without a composition | stops at initialization (the feed composition is given data, so there is no default) |
| su_d50 | susp with `susp_d50` = 1 mm (different from the 0.3 mm of class 1) | stops at initialization |
| su_wash | susp with hillslope erosion `f_wash = 1` | stops at initialization (how hillslope erosion carries the composition is not decided) |
| rfstop_bank | rfs3 with the bank mode of rockfall `rf_bank = 1` | stops at initialization (the talus removed by bed load is not tracked in the mixed-size application) |
| rfstop_frac | rfb3 without `rf_frac` | stops at initialization (the composition of the debris from bedrock is given data) |

Typical numbers: the difference between the beds of equal and single 5e-15 m, between equal_te and single_te 4e-15 m (the outflow is 0.19 times that without the effective shear), between equal_tp and single_tp
9e-15 m (the outflow is 0.998 times that without the partition), between tpmix1 and tpfix1 0 (one step), between
tpmix and tpfix 4.5e-5 m, between equal_su and single_su 1e-14 m for the
bed and 3e-17 m for the suspended load, the residuals in susp 7e-14 m³ per class and 1e-14 m³ for the suspended
load (0.513 m³ went from class 1 to the suspended load), the difference of the probe Dm 2e-6 mm, the lowering in
armor 0.02197 m (equal to the theoretical value), decay rates 0.04934 and 0.04946 /s, the outflow ratio in hide2
1.0002, the residual in bank 1e-13 m³, for rockfall a difference of 8e-15 m in the ground elevation and 1.5e-14 m in
the talus thickness (landform change 4.6 m), a coarse fraction of 0.598 in the talus and a production from bedrock of
147.311176 m³ (= the lowering of the bedrock), for creep a difference of 4e-16 m in the ground elevation (landform
change 1.8 m), and for longshore transport 1.3e-15 m (landform change 0.38 m).

## Running

```
make
./Run.sh            # serial. Check_bedmix.py + configurations that stop at initialization (nofrac, su_d50, su_wash, rfstop_bank, rfstop_frac) + cmp of the restarts
./Run_MPI.sh 2      # MPI (np=2). Also checks bit identity with the serial save
```

The inputs zinit_*.txt / hinit_*.txt / sdinit_*.txt / qbmix.txt / rw_suw.txt / width_suw.txt / sw_mesa_sea.txt
are generated by make_init.py (not tracked).
There is no reference; pass or fail is decided by the analytic checks in Check_bedmix.py and by the bit
identity of serial, MPI and restart runs.
