# test/dbrock — Checks of rock erosion by debris flows

> English mirror of test/dbrock/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification case for the erosion of rock by the flowing mixture in debris-flow
event runs (`f_debris = 1`). It covers the debris-flow term (`rock_kdb`) of bedrock
incision `f_rockinc`
([chapter on landform change in the users guide](../../../docs/en/users_guide/geomorph.md#rock-erosion-by-debris-flows-rock_kdb),
equations in the
[supplement](../../../docs/en/users_guide/sediment.md#bedrock-incision-by-flowing-water-f_rockinc);
docs/mountain_stream_plan.md §12 and developer.md §88.18, in Japanese). The lowering
rate of bare rock is the excess form of the quasi-static driving stress

  E_d0 = f_r k_d max(τ_d/τ_cd − 1, 0)^m_d,  τ_d = ρ(1 + sC) g_e h_t tanθ.

Only cells with a dense mixture (C ≥ db_cmin) that is moving (|V| ≥ db_vstop)
erode. The product enters the mobile layer sd 1:1 (z unchanged) and covers the rock
by the exposure exp(−sd/H*). There is no reference; the case is judged by the
analytical solution, conservation, bit identity and the messages of the stops.

## Configurations

The channel of db1 and db3: a straight channel one cell wide between dry high
ground (+2 m) (3 × 60 cells, Δx = 1 m, slope 0.2 to the south, n = 0.05). Clear
water of 0.5 m³/s and sediment with concentration h_s/h = 0.5 (C = 1/3) enter at
the north end, and the south edge is a free outflow. The mixture without exchange
(`f_dbed = 0`) and with Manning resistance becomes steady in about 60 s, so the
first landform update is placed at t = 100 s and all updates see the same steady
hydraulics. k_d = 1e-3 m/s, τ_cd = 300 Pa (the steady τ_d ≈ 660 Pa), m_d = 1.5,
H* = 0.05 m. The initial cover (repeating 0, 0.02, 0.04 and 0.06 m) and the
erodibility multiplier (0 to 2, shifting with a period of 9 rows) vary by row.

| Configuration | File | Contents | Judgement |
|---|---|---|---|
| DB1 analytical solution | `param_db1.txt` | No exchange, so the product stays in place and neither z nor the flow changes. 6 updates in 600 s | In each cell of rows 11 to 50, e^{H/H*} − e^{H0/H*} = E_d0 T/H* within relative 1e-9. Rows with multiplier 0 have Ri = 0 and sd unchanged. z of the channel unchanged |
| DB1 update interval | `param_db1_dtg.txt` | Update interval doubled (3 updates, every 200 s) | sd within relative 1e-12 of db1 |
| DB3 concentration gate | `param_db3_cmin.txt` | db_cmin = 0.5 > C | Ri = 0 and sd unchanged in every cell |
| DB3 velocity gate | `param_db3_vstop.txt` | db_vstop = 10 m/s > \|V\| | Ri = 0 and sd unchanged in every cell |
| DB2 conservation | `param_db2.txt` | A 10 × 40 box with walls on all sides: a slope of 0.4 (y < 25 m) and a flat. 0.5 m of the soil in the northern band is mobilized at t = 1 s and runs down over a 2 cm cover (Takahashi-type E-D, Coulomb + Manning, φ = 30°, low-velocity settling). 20 s | Total solids Σh_s A + (1 − λ)Σ(z − z0)A zero within 1e-10 m³. Mobile-layer solids Σh_s A + (1 − λ)Σ(sd − sd0)A within relative 1e-7 of (1 − λ) × the ledger (bulk volume of rock eroded by debris flows). (sd − sd0) − (z − z0) = Ri within 1e-12 m. Ledger > 1e-3 m³ |
| DB7 input errors | `param_db7_kp.txt` and 4 others | Fluvial plucking in a debris-flow run / no threshold / db_cmin = 0 / rock_kdb without f_debris / no process that erodes the rock | Each stops at the initialization with its message |

| File | Contents |
|---|---|
| `make_init.py` | Generates the terrain, initial cover and erodibility multiplier of the channel of db1 and db3, and the terrain, soil depth and release depth of the box of db2 (constants kept in pairs with `param*.txt` and `Check_dbrock.py`) |
| `Check_dbrock.py db1 / db3 / db2 LOG` | The judgements above (h, h_s, z and sd are read in double precision from state.dat of the saves and Ri from geomorph_rockinc.dat; the ledger of DB2 from the end-of-run line in the Screen log) |
| `Run.sh` / `Run_MPI.sh N` | Runs and checks all configurations. MPI compares state.dat and geomorph_rockinc.dat byte by byte with the serial saves (`save_*_serial`) |

## Running

```bash
make
python3 make_init.py   # regenerate the inputs (bundled; only when changed)
./Run.sh            # serial (about 1 minute)
./Run_MPI.sh 4      # MPI (after Run.sh; byte comparison with save_*_serial)
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1, default -Ofast build)

- DB1: the largest relative difference to the analytical solution is 1.4e-15
  (tolerance 1e-9). τ_d = 660.1 to 660.2 Pa, C = 1/3. The largest relative
  difference of sd to the configuration with the doubled update interval is
  2.3e-16. The 5 rows with multiplier 0 have Ri = 0. z of the channel changes by
  3.6e-15 m.
- DB3: outside the concentration and velocity gates, Ri and the change of sd are
  both 0.
- DB2: total solids 5.1e-14 m³. The relative difference between the mobile-layer
  solids and (1 − λ) × the ledger is 4.9e-10 (the ledger is printed with 9
  digits). The largest (sd − sd0) − (z − z0) − Ri is 1.9e-14 m. Rock eroded by
  debris flows: 0.74 m³ (largest Ri 6.0 mm).
- DB7: all 5 configurations stop at the initialization.
- MPI (DB4): no run-time errors with -fcheck=all at np = 2. With the -O2 build,
  the state.dat and geomorph_rockinc.dat of np = 1, 2 and 4 are byte-identical to
  the serial run. With the default -Ofast, Run_MPI.sh 2 and 4 are also
  byte-identical to the serial run for all configurations.
