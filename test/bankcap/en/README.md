# test/bankcap — Channel water below the bank does not climb onto a thinly wet bank (check of f_dry_head_cap = 2)

> English mirror of test/bankcap/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the energy-head cap on the edge depth (`f_dry_head_cap` of `&list_enc`;
[Advection schemes](../../../docs/en/users_guide/advection.md) §5; developer.md §68.16 and §108).
`f_dry_head_cap = 2` applies the cap also when the receiving cell is wet, as long as its bed is
above the water level of the sending cell. It is checked with a flowing incised channel and a
thinly wet bank.

## Rule

The edge depth $`h_e`$ that can be carried to the cell the flow heads for (the receiver) is
limited to the part of the energy head of the sender that exceeds the bed of the receiver.

```math
h_e \leftarrow \min\!\left(h_e,\ \max\!\left(\eta_s + \frac{u_n^2}{2g} - z_r,\ 0\right)\right)
```

$`\eta_s = z_s + h_s`$ is the water level of the sender, $`u_n`$ the normal velocity on the edge
and $`z_r`$ the bed of the receiver. An edge whose depth becomes 0 also gets zero velocity. It is
ENCflow's own rule built on the Bernoulli relation "water does not climb onto ground above its
energy head".

| f_dry_head_cap | When the cap is applied |
|---|---|
| 0 | never |
| 1 (default) | the receiver is dry ($`h_r < d_d`$) |
| 2 | as 1, and also when the receiver is wet but its bed is above the water level of the sender ($`z_r > \eta_s`$) |

With 1, the cap is lifted as soon as a bank cell is thinly wet, and the edge depth of the
continuity equation returns to the mean of the two cells (the mean of a deep channel and a thin
film). On the diagonal edges of the 8-neighbour stencil, the mean of the velocities of the channel
cell and the bank cell gives a normal velocity, so channel water whose level is below the bank
climbs onto the bank. 2 is not applied to a submerged step ($`z_r < \eta_s`$): ordinary flow up a
wet slope is the same as with 1.

## Set-up

Length 400 m, Δx = 5 m, slope 0.002. An incised channel 4 cells (20 m) wide with n = 0.03 carries
137.3 m³/s (uniform depth 2.50 m, velocity 2.75 m/s, velocity head 0.38 m). The floodplain to the
north (8 rows, n = 0.05) is 3.5 m above the channel bed, so the channel water level is 1.0 m below
the bank. To the south is a terrace (channel bed + 7 m). Reach inflow at the west end, free outflow
at the east edge; the initial velocity is that of the uniform flow, and the run lasts 15 minutes.
The inputs are written by `make_bankcap.py`.

| Configuration | File | Initial floodplain | f_dry_head_cap | What is checked |
|---|---|---|---:|---|
| 1 | `param_wet2.txt` | 2 cm film | 2 | channel water does not climb onto the bank |
| 2 | `param_wet1.txt` | 2 cm film | 1 | it climbs (the check of configuration 1 tells the difference) |
| 3 | `param_dry2.txt` | dry | 2 | the bank stays dry and the channel is in uniform flow; byte-identical to configuration 4 |
| 4 | `param_dry1.txt` | dry | 1 | as above |

## Checks (Check_bankcap.py and Run.sh)

1. Configuration 1: the maximum depth over the run in the bank row (the floodplain row next to
   the channel) does not exceed the initial film of 2 cm.
2. Configuration 1: the depth of the bank row at the end is below 1 cm (the film drains into the
   channel).
3. Configuration 1: the water volume on the floodplain decreases at every output.
4. Configuration 2: the maximum depth over the run in the bank row exceeds 4 cm.
5. Configurations 3 and 4: the floodplain stays dry.
6. Configurations 3 and 4: the channel depth at the end (mean over x = 100–300 m) is within ±1 %
   of the uniform depth.
7. The depth and velocity outputs and Log.txt of configurations 3 and 4 are byte-identical (with
   a dry receiver, 1 and 2 are the same).

## Results

| Item | Value | Verdict |
|---|---|---|
| 1 maximum depth over the run in the bank row, configuration 1 | 0.0200 m (the initial film) | PASS |
| 2 depth of the bank row at the end, configuration 1 | 0.0042 m | PASS |
| 3 water volume on the floodplain, configuration 1 | 320.0 → 237.8 → 204.0 → 178.4 m³ | PASS |
| 4 depth of the bank row, configuration 2 | maximum over the run 0.153 m, 0.071 m at the end | PASS |
| 5 and 6 configurations 3 and 4 | maximum floodplain depth over the run 0; channel depth 2.5006 m (1.0002 times the uniform depth) | PASS |
| 7 configurations 3 and 4 | the 12 files of H and V outputs and Log.txt are byte-identical | PASS |

## Usage

```bash
make
./Run.sh            # serial (4 runs, about 10 seconds)
./Run_MPI.sh 2      # MPI (the boundary between the bank row and the channel is a band boundary)
```

## Findings and limits of accuracy

- The water that climbs onto the bank in configuration 2 raises the depth of the bank row from
  2 cm to at most 15 cm and then keeps it at 7 cm. The channel water level is 1.0 m below the
  bank and does not reach it even with the velocity head of 0.38 m added, so physically this
  water cannot climb.
- A channel next to a wet bank comes out deeper than the uniform depth whichever cap is chosen
  (2.61 m as the mean over x = 100–300 m; 2.50 m with a dry bank). This is a property of the
  advection term on the 8-neighbour stencil (developer.md §50.9) and outside the scope of this
  check. `f_dry_head_cap = 2` does not change it.
- `f_dry_head_cap = 2` is not the default. In runs where thin flow runs over steep terrain the
  results can change ([test/chichibu](../../chichibu/en/README.md) and others; developer.md
  §108), and the default 1 keeps the previous results.

## Related documents

- [docs/en/users_guide/advection.md](../../../docs/en/users_guide/advection.md) §5 — switches around the advection term
- [docs/en/users_guide/swflow.md](../../../docs/en/users_guide/swflow.md) — parameter list of `&list_enc`
- developer.md §68.16 (cap toward dry receivers), §108 (extension to wet receivers), §50.9 (how it was found with the example bridge_wood_jam)
- [examples/bridge_wood_jam](../../../examples/bridge_wood_jam/en/README.md) — backwater and bypass flooding from driftwood jammed at a bridge
