# test/uniflow — Uniform flow in a straight channel between dry ground

> English mirror of test/uniflow/README.md. The Japanese file is the master copy.

[日本語](../README.md)

In a "raster incised channel" that uses neither the channel mask (fn_rw) nor
the channel-width mode, the conveyance of the rows adjacent to the walls is
compared with Manning uniform flow (developer.md §84.7).

## Setup

Length 1000 m, Δx = 1 m, slope 0.002, n = 0.03. Channels of width W = 1 and
5 cells with dry ground at bed +2 m on both sides. Segment inflow Q = q·W at
the west end (q = 0.4695 m²/s corresponds to a uniform-flow depth of 0.5 m);
free outflow at the east edge. Measurements are taken at x = 400–700 m to
avoid the drawdown backwater at the downstream end (about 250 m). Two
settings of `f_opening_dynamic`: 0 (no reassignment) and 2 (all edges).

Supercritical segment inflow (configuration w1_sc): the same q flows into a
channel one cell wide with slope 0.05 (reassignment 2; Manning uniform-flow
depth 0.190 m, Fr = 1.8). If the depth floor of the inflow face exceeds the
depth of the flow, the inflow cell flows slower than the uniform flow
(developer.md §89.25, in Japanese).

## Checks (Check_uniflow.py)

1. Steady uniform flow: the water-surface slope agrees with the bed slope
   within ±2 % (4 configurations).
2. Mass balance: the sum of V·h over the rows agrees with Q within 1e-3
   (4 configurations).
3. `f_opening_dynamic = 2` matches Manning: h/h_n and V/V_n are 1 ± 0.5 % in
   all rows.
4. Known properties without reassignment are recorded: at width 1,
   h/h_n = 1.30 (the conveyance is 64 % of Manning); at width 5, the velocity
   of the bank rows is 0.80 of the interior rows (h/h_n = 1.04). This is
   because the diagonal links to dry cells carry no flux and their passage
   width is lost (the same motivation as §68.14).
5. Supercritical segment inflow (w1_sc; checks 1 and 2 are also applied): the
   depth and velocity of the inflow cell agree with the mean of the uniform
   reach within ±1 %. After the change of 2026-10-28 (the depth floor of the
   inflow face no deeper than the uniform-flow depth) both are 1.0000 times
   (equal to the four digits printed); with the executable before the change,
   the velocity was 0.71 times and the depth 0.96 times (the floor of the
   inflow face was the critical depth).

## Usage

```
make
./Run.sh            # serial (5 runs, about 4 minutes)
./Run_MPI.sh 2      # MPI
```
