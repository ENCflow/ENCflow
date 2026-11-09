# meander — deformation of a sinusoidal channel (outer-bank retreat, inner-bank bars and fixation)

> English mirror of examples/meander/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This example follows how a sinusoidal channel placed in a floodplain changes its shape under
bedload bed evolution, corrections of the bedload direction (transverse bed slope and secondary
flow), bank collapse and fixation of the inner-bank bars. No processing that rebuilds the
channel centreline or the grid is used: the shape of the channel is represented only by the
terrain on a fixed grid and the wet/dry judgement. Ten configurations compare the nature of
the banks (non-cohesive, cohesive, slump blocks), the way the discharge is given (constant, or
alternating floods and low flows) together with fixation, and the sediment supply from upstream
(no feed, capacity feed, equilibrium-concentration feed of suspended sediment, the ledger of
fines in the bed). The values are schematic values chosen to make the phenomena easy to see; the
example does not reproduce a particular river. Cutoffs of meander loops are treated in
[meander_cutoff](../../meander_cutoff/en/README.md).

The coefficients of the bedload-direction corrections (μs, μk, N*) are literature values.
Fixation (`f_fixation`) is **ENCflow's own simplification** that replaces the treatment of Asahi
et al. (2013), in which cells that stay dry long enough are added to the floodplain, with a
continuous rise of the critical Shields stress according to a degree of fixation a; there are no
standard values in the literature for the fixation time T_fix or the increment ratio c_τ. The
ledger of fines in the bed (`f_bedfines`) is also a minimal two-component ledger without grain
size classes assembled in ENCflow (developer.md §84.6, §84.10).

## What happens in real meandering rivers

- **Secondary flow and the cross-section of a bend**: in a bend a secondary (helical) flow
  arises in which the flow near the surface goes towards the outer bank and the flow near the
  bed towards the inner bank; a pool forms at the outer bank and a bar (point bar) at the inner
  bank. The transverse bed slope is set by the balance between the bedload carried inward by
  the secondary flow and the bedload going down the transverse slope by gravity (Engelund
  1974, Hasegawa 1989).
- **Retreat of the outer bank**: when scour in the pool erodes the toe of the bank, the bank
  collapses and retreats. A sandy bank collapses by the part that exceeds the angle of repose; a
  cohesive bank is eroded little by little by the flow and also fails as a block when its
  height exceeds a limit. The fallen blocks cover the toe and stop bank erosion until the flow
  carries them away (Parker et al. 2011, Asahi et al. 2013).
- **Advance of the inner bank and vegetation**: the inner-bank bar grows during floods; once
  vegetation is established on a bar exposed during low flow, the bar is hard to erode in the
  next flood and joins the floodplain. When the retreat of the outer bank and the advance of
  the inner bank balance, the channel moves sideways while keeping its width. In laboratory
  flumes, the ratio of the time for vegetation to establish to the time for the channel to
  migrate decides whether a single meandering channel persists or the river becomes braided
  (Tal and Paola 2007).
- **Sediment supply**: the conditions under which a meander that migrates sideways and repeats
  cutoffs was sustained at constant discharge in a flume were banks stronger than the bed
  (vegetation) and suspended fine sediment that fills the hollows behind the bars (Braudrick et
  al. 2009). Without sediment coming from upstream, the bed lowers as a whole (degradation).

## Mechanisms needed to reproduce it

![Schematic of the mechanisms](figs/mechanism.png)

Schematic. (a) Plan view of the bends: the flow near the bed (secondary flow) turns inward, and
the pool at the outer bank lies slightly downstream of the apex. The outer bank retreats (dashed)
and a bar grows at the inner bank. (b) Cross-section at a bend apex: bedload goes inward by the
secondary flow and down the transverse slope by gravity, and their balance sets the transverse
slope. The outer bank retreats in three ways of collapse, and the bar top rises only up to the
water level. (c) Alternating floods and low flows, and fixation: the degree of fixation a of a
bar cell exposed during low flow and the factor 1 + c_τ a on the critical Shields stress of the
bedload leaving that cell (schematic; the bar is assumed to be dry below 5 m³/s).

The mechanisms at work in this example and the settings that carry them:

| Real phenomenon | Mechanism in the model | Settings |
|---|---|---|
| Erosion and deposition of the bed | the transport formula of [bedload](../../../docs/en/users_guide/geomorph.md#bedload-f_fluvial) (Ashida–Michiue, d50 = 1 mm) and the Exner equation | `f_fluvial = 1`, `f_qbform = 1`, `fluv_d50 = 0.001` |
| Bedload going down a transverse slope | bed-slope term $`\vec q = q_b(\hat t - \gamma\nabla z)`$, $`\gamma = \sqrt{\tau_{*c}/(\mu_s\mu_k\tau_*)}`$ (Hasegawa type) | `fluv_slope = 1`, `fluv_mus = 1.0`, `fluv_muk = 0.45` |
| Bedload carried inward by the secondary flow | equilibrium secondary-flow term (ratio of the near-bed transverse velocity $`r = N_* h\kappa`$; κ is the streamline curvature) | `f_secflow = 1`, `sec_nstar = 7` |
| Collapse of sandy banks | angle-of-repose avalanching (the part of the slope to a neighbouring cell beyond tanφ is moved to the lower side) | `f_repose = 1`, `repose_phi = 32` (35 in the cohesive configurations) |
| Erosion of cohesive banks by the flow | bank-erosion law $`E_b = K_b(\tau_*/\tau_{*c,b} - 1)^m`$ (evaluated with τ* of the toe cell next to the bank; the eroded soil is moved to the toe) | `f_berode = 1`, `berode_kb = 3e-5`, `berode_tausc = 0.5` |
| Block failure and protection of the toe by the blocks | bank mode of [rockfall and talus](../../../docs/en/users_guide/geomorph.md#rockfall-and-talus-f_rockfall) (the part of a bank face above the critical height H_c fails and becomes talus at the toe) and shielding of bank erosion by the talus thickness | `f_rockfall = 1`, `rf_bank = 1`, `rf_hc = 1.5`, `berode_hcover = 0.2` |
| Bars do not grow above the flood water level | bedload is not carried into a neighbouring cell higher than the water surface (a bank face) | behaviour of `f_fluvial = 1` |
| Vegetation establishing on exposed bars | degree of fixation a (grows towards 1 as 1 − exp(−t/T_fix) while dry). The critical Shields stress of the bedload leaving the cell, and of bank erosion with the cell as the bank, rises to τ*c (1 + c_τ a). Reset to 0 when scoured 0.1 m below the fixed surface | `f_fixation = 1`, `fix_tfix = 10`, `fix_ctau = 10`, `fix_dzreset = 0.1` |
| Vegetation slows the flow and traps fines | roughness of fixed cells raised to n (1 + c_n a) | `fix_cn = 2` |
| Transport and deposition of fines in floods | advection, entrainment and settling of [suspended sediment](../../../docs/en/users_guide/geomorph.md#suspended-sediment-f_suspend) (0.2 mm) | `f_suspend = 1`, `inflow_cs` or `inflow_cs_eq` |
| Sediment supply from upstream | capacity feed (supply through the inflow face = net outflow of the inflow cells; the bed at the inlet is held fixed) | `fluv_bcfeed = 1` |
| Distinguishing coarse sand and fines in the bed | [ledger of fines in the bed](../../../docs/en/users_guide/geomorph.md#ledger-of-fines-in-the-bed-f_bedfines) (thickness of fines sf; entrainment within the stock, and fines also move with the bedload) | `f_bedfines = 1`, `fines_frac0 = 0`, `fines_la = 0.05` |
| Landform change over a long time | only the landform change is accelerated by the factor morfac (4 h of hydraulics = 200 h of landform time) | `dt_geomorph = 1`, `morfac = 50` |

The transport formula is Ashida and Michiue (1972). The bed-slope term has the same form as
equation (6) of Hasegawa (1989), and μs = 1.0, μk = 0.45 are the values used by equation (22)
of Asahi et al. (2013) after Hasegawa (1984). The secondary-flow coefficient N* = 7 is the value
equation (18) of Asahi et al. (2013) takes from Engelund (1974) (check of the equations and
coefficients: developer.md §84.12, and the
[explanation](../../../docs/en/users_guide/sediment.md#3-bedload-f_fluvial)). The bank-erosion law
is a power of the excess Shields stress, with the simplification that the toe cell's value
stands for the stress acting on the bank face. K_b is a calibration value with no standard
value. Slump blocks place the slump blocks of Asahi et al. (2013) and Parker et al. (2011) (the
fallen blocks cover the toe and stop bank erosion until they are carried away) on the grid
within the rockfall-and-talus framework (the shielding factor (1 − ht/h_cover)⁺ is the grid
version of equations (27)–(28) of Asahi et al.). The fixation values T_fix and c_τ are
schematic. Asahi et al. (2013) showed that meanders develop when the ratio T_Land/T_return of
the dry time needed to become land to the return period of floods is 0.025–0.5; in this example
T_fix / flood period = 10 h / 35 h ≈ 0.29 lies in that range.

## Geometry and settings

![Settings](figs/setup.png)

Top: the initial terrain (blue = channel; the floodplain is bed + 1 m and dry). The red ticks
are the bend apexes and the red arrow the range of the metrics. Bottom left: longitudinal section
along the channel (base of the soil: solid = sd.txt, dashed = sd_feed.txt of the feed
configurations). Bottom middle: initial cross-section at the apex x = 350 m. Bottom right:
inflow (the first three cycles). The runs last 240 min of hydraulics = 200 h of landform time
with output every 30 min (25 h); in the varying-discharge configurations the 100 h and 200 h
outputs fall in low flow and 150 h in a flood.

800 m × 240 m, Δx = 2 m (400 × 120 cells). A channel 20 m (10 cells) wide is placed in a dry
floodplain (bed + 1 m). The inputs are made by `make_init.py` (`make`).

- **Channel**: the centreline is straight for x = 0–100 m and a sine wave of wavelength 200 m
  from x = 100 m. The amplitude rises from 0 to 10 m over x = 100–300 m and is 10 m over
  x = 300–700 m (bend apexes at x = 350, 450, 550, 650 m). From x = 700 m the amplitude starts
  to decrease; one bend of amplitude 7.5 m remains before the east edge, and the channel reaches
  the east edge at an angle of about 9°.
- **Bed and banks**: the bed slopes 0.001 in x (the sinuosity is 1.02, so the slope along the
  channel is about 0.00098); initial depth 0.8 m. The bank step 1 m / 2 m = 26.6° is gentler
  than the 32° angle of repose and does not collapse initially.
- **Soil**: the erodible soil is 5 m. The 30 m at the downstream end are 0 (non-erodible). In
  the no-feed configurations (sd.txt) the 30 m at the upstream end are also 0 and the next
  300 m (x = 30–330 m) are a ramp 0 → 5 m, so that bedrock stops the degradation at the
  upstream end from becoming a deep hole. The feed configurations (sd_feed.txt) have 5 m up to
  the upstream end (capacity feed holds the bed at the inlet, so no ramp is needed).
- **Inflow**: a segment inflow into the 10 channel cells at the west edge. Either a constant
  15 m³/s (uniform flow of depth ≈ 0.8 m), or alternating floods of 15 m³/s (20 min) and low
  flows of 1.5 m³/s (18 min) joined by 2-min transitions, with a period of 42 min (35 h of
  landform time). The east edge is a free outflow.
- **Time**: dt = 0.2 s (0.1 s in the two configurations with suspended sediment), the
  landform is updated every 1 s, the landform change is accelerated by morfac = 50, and 4 h of
  hydraulics is 200 h of landform time. Roughness n = 0.03.
- **Numerical settings of the flow**: the advection is the default momentum-conservative form
  (scheme 3), dynamic reassignment of blocked openings at its default `f_opening_dynamic = 3`,
  and `f_inflow_edge = 2` for the edges touching the outer cells of the segment inflow (see the
  notes).

| Case | Parameter file | Inflow | Banks, fixation, feed | Run time (guide) |
|---|---|---|---|---|
| Non-cohesive | param.txt | constant 15 m³/s | angle-of-repose avalanching (32°) | about 20 min |
| Cohesive | param_cohesive.txt | constant | bank-erosion law (K_b = 3×10⁻⁵ m/s, τ*c,b = 0.5) + avalanching (35°) | about 20 min |
| Cohesive + slump blocks | param_cohesive_slump.txt | constant | cohesive + slump blocks (H_c = 1.5 m, talus 35°) + shielding by the blocks (h_cover = 0.2 m) | about 20 min |
| Non-cohesive + capacity feed | param_feed.txt | constant | non-cohesive + capacity feed (sd_feed.txt) | about 20 min |
| Varying discharge only | param_varq.txt | alternating floods and low flows | non-cohesive (no fixation; for comparison) | about 20 min |
| Varying discharge + fixation | param_fix.txt | same | non-cohesive + fixation (T_fix = 10 h, c_τ = 10) | about 20 min |
| Same, gentle recession | param_fixrec.txt | raised to 15 m³/s in 2 min, held 10 min, lowered to 1.5 m³/s over 20 min, low flow 10 min (period 42 min) | same as varying discharge + fixation | about 20 min |
| Varying discharge + fixation + suspended sediment | param_fixsusp.txt | floods and low flows; fines (0.2 mm) fed at a volume concentration of 0.004 during floods | fixation + suspended sediment + roughness of fixed cells (c_n = 2) | about 1 h 15 min |
| Varying discharge + fixation + capacity feed | param_fixfeed.txt | floods and low flows | fixation + capacity feed | about 25 min |
| Varying discharge + fixation + suspended sediment + feed + ledger of fines | param_fixsuspfines.txt | floods and low flows; fines (0.2 mm) fed at 0.5 × the equilibrium concentration of the inflow cells | fixation + suspended sediment + roughness + capacity feed + ledger of fines in the bed (the initial bed is coarse sand only) | about 1 h 5 min |

The run times are for gfortran 13.3 (-Ofast -march=native) on 1 thread of an Intel Xeon (2.3 GHz)
with other cases running at the same time (one core per case).

**Metrics** (plot_results.py; measured over the columns x = 150–650 m): the **channel width** is
the column mean of the width of the wet cells (depth > 0.1 m), the **maximum shift of the centre**
is the largest shift of the column centroid of the wet cells from the initial one, the **maximum
amplitude of the wet belt** is the largest distance of a wet cell from the valley axis y = 120 m
(19 m initially), and the **deepest scour** is the minimum of z − z0. **Fixed cells** are cells
in the initial channel with fixation degree a > 0.5. In the varying-flow configurations the
outputs at 100 h and 200 h fall in a low-flow period, so their width is measured at the low-flow
water edge.

## How to run

```
cd examples/meander
make                     # link to the executable and inputs (make_init.py makes z.txt, h.txt, sd.txt, sd_feed.txt)
make run                 # the 4 constant-discharge configurations (non-cohesive, cohesive, cohesive + slump blocks, capacity feed)
make varq                # the 4 flood/low-flow configurations (varying discharge only, fixation, gentle recession, fixation + suspended sediment)
make feed                # the 2 feed + fixation configurations (capacity feed; equilibrium feed of suspended sediment + ledger of fines)
python3 plot_setup.py    # figs/mechanism.png, setup.png (does not use the results)
python3 plot_results.py  # figs/planform.png, fixation.png, sections.png, metrics.png, feed.png and the tables
```

With the argument `en` the figures are drawn with English labels into en/figs/
(`python3 plot_setup.py en`, `python3 plot_results.py en`). plot_results.py reads the ledgers of collapse, erosion and feed from the screen output
(Screen.log, Screen_<configuration>.log, kept by the `make` targets with `2>&1 | tee`). Plotting
needs Python 3, NumPy and matplotlib.

## Results

The tables and figures are values computed for all configurations with gfortran 13.3 (-Ofast
-march=native, 1 thread). The tables are excerpts from the output of plot_results.py.

### Constant discharge: outer-bank retreat and widening

![Planform](figs/planform.png)

The initial channel (top) and the bed change z − z0 after 200 h of landform time in 7
configurations (blue = scour, red = deposition). Black lines = initial banks, coloured lines =
final water edge (depth 0.05 m). The varying-flow configurations end in a low-flow period, so
their water edge lies inside by the width of the exposed bars.

![Cross-sections](figs/sections.png)

Time evolution of the cross-sections 70 m downstream of the bend apexes in the non-cohesive,
constant-discharge run (left: a bend bulging north, outer bank on the north; right: a bend
bulging south, outer bank on the south). The dashed line is the final water surface.

![Metrics](figs/metrics.png)

Time evolution of the channel width, the maximum shift of the centre and the maximum amplitude
of the wet belt over x = 150–650 m (all configurations; dashed = the three varying Q + fixation
configurations with the gentle recession, the capacity feed, and fines + feed + ledger of fines;
non-cohesive + capacity feed is solid).

Width / maximum shift of the centre / maximum amplitude of the wet belt (m; initially 20 / 0 /
19), deepest scour and fixed cells:

| Case | 100 h | 150 h (flood period) | 200 h | Deepest scour (m, 200 h) | Fixed bar cells (inside the initial channel, 200 h) |
|---|---|---|---|---|---|
| Non-cohesive (constant Q) | 28.1 / 10.0 / 29 | 32.3 / 16.0 / 35 | 35.1 / 23.7 / 43 | −2.31 | – |
| Cohesive (constant Q) | 24.6 / 6.0 / 21 | 26.6 / 9.0 / 23 | 28.7 / 12.0 / 25 | −2.26 | – |
| Cohesive + slump blocks | 26.9 / 9.0 / 25 | 30.6 / 14.0 / 33 | 33.1 / 18.0 / 35 | −2.28 | – |
| Non-cohesive + capacity feed | 30.5 / 12.0 / 31 | 36.1 / 22.5 / 43 | 39.2 / 25.9 / 45 | −2.18 | – |
| Varying Q only | 21.7 / 6.0 / 21 | 24.5 / 6.0 / 23 | 25.4 / 13.0 / 27 | −1.97 | – |
| Varying Q + fixation | 20.8 / 10.0 / 21 | 23.1 / 10.0 / 29 | 23.8 / 17.0 / 33 | −2.24 | 483 (1,932 m²) |
| Same, gentle recession | 21.0 / 6.0 / 19 | 21.7 / 7.0 / 21 | 22.6 / 9.9 / 25 | −2.06 | 191 (764 m²) |
| Varying Q + fixation + suspended fines | 15.0 / 8.0 / 21 | 19.1 / 8.8 / 29 | 23.2 / 26.1 / 51 | −2.77 | 1,040 (4,160 m²) |
| Varying Q + fixation + capacity feed | 20.4 / 11.9 / 23 | 24.1 / 13.0 / 33 | 25.9 / 24.6 / 41 | −2.08 | 851 (3,404 m²) |
| Varying Q + fixation + fines + feed + ledger of fines | 17.4 / 14.0 / 29 | 28.8 / 25.3 / 89 | 93.1 / 41.1 / 119 | −2.00 | 1,340 (5,360 m²) |

(150 h is just an intermediate output for the constant-discharge configurations and a
flood-period output for the varying-flow configurations. For the configuration with the ledger of
fines, the values at 150 h and 200 h include the water spilled onto the floodplain.)

- **The chain of outer-bank retreat works**: the equilibrium secondary-flow term carries sediment
  towards the inner bank and the bed-slope term eases the transverse slope, forming pools on the
  outer banks and bars on the inner banks. As a pool deepens the outer bank face collapses, and
  the toe flow carries the collapsed sediment away so that the retreat continues (cross-section
  figure: the outer bank retreats by 18 m (x = 420 m) and 28 m (x = 520 m) in 200 h, and the inner
  bar rises 0.4–0.6 m above the initial bed but stays below the water surface). The retreat is
  largest not at the apex of a bend but 70–90 m downstream of it (where the main flow crosses the
  bend and strikes the outer bank), and it grows towards the downstream bends (22, 30, 40 and 46 m
  in the bends with apexes at x = 350, 450, 550 and 650 m; table 4 of plot_results.py).
- **Under a constant discharge lateral migration becomes widening and loop extension**: the inner
  bars do not build above the water surface and do not become land, so outer-bank retreat turns
  directly into widening (non-cohesive: width 20 → 35.1 m, amplitude of the wet belt 19 → 43 m,
  angle-of-repose avalanching 3,958 m³). The upstream bends move little because the bed
  degradation without feed (−0.93 m at x = 50–150 m) leaves their banks relatively high.
- **Cohesive banks retreat more slowly**: with the bank-erosion law (423 m³) and collapse at a
  repose angle of 35° (1,507 m³), the width at 200 h is 28.7 m and the amplitude 25 m (35.1 m and
  43 m non-cohesive). Adding slump blocks, banks taller than the critical height H_c = 1.5 m
  collapse in blocks (1,279 m³), giving a slightly larger width of 33.1 m and amplitude of 35 m;
  the contribution of the bank-erosion law does not decrease (423 → 458 m³: the shielding by the
  blocks has little effect).
- **Capacity feed stops the bed degradation** (non-cohesive + capacity feed): the bed change of
  the channel is −0.04 to −0.12 m (−0.48 to −0.93 m without feed), the upstream bends move too,
  and the channel spreads the most of the constant-discharge configurations, to a width of 39.2 m
  and an amplitude of 45 m at 200 h (capacity feed 5,884 m³).

### Varying discharge and fixation: the inner bank becomes land

![Fixation degree](figs/fixation.png)

Fixation degree a after 200 h (top) and the final depth at low flow (bottom) for varying Q +
fixation (param_fix.txt). The floodplain stays dry, so a = 1 there.

Fixed cells, bar height, bed change of the channel (mean over wet cells) and floodplain
deposition at 200 h:

| Case | Fixed cells (inside the initial channel) | of which z − z0 > 1.0 m | Maximum z − z0 of fixed bars (m) | Bed change x = 50–150 / 150–300 / 300–500 m | Floodplain deposition > 0.1 m (cells) |
|---|---|---|---|---|---|
| Non-cohesive (constant Q) | – | – | – | −0.93 / −0.72 / −0.48 | 0 |
| Non-cohesive + capacity feed | – | – | – | −0.04 / −0.04 / −0.12 | 0 |
| Varying Q only | – | – | – | −0.87 / −0.57 / −0.37 | 0 |
| Varying Q + fixation | 483 | 0 | 0.87 | −0.85 / −0.56 / −0.51 | 0 |
| Same, gentle recession | 191 | 0 | 0.77 | −0.82 / −0.54 / −0.39 | 0 |
| Varying Q + fixation + suspended fines | 1,040 | 115 | 1.17 | −0.35 / −0.57 / −0.69 | 196 |
| Varying Q + fixation + capacity feed | 851 | 72 | 1.07 | −0.14 / −0.08 / −0.39 | 0 |
| Varying Q + fixation + fines + feed + ledger of fines | 1,340 | 550 | 1.64 | −0.00 / −0.00 / −0.04 | 694 |

(The floodplain is at the initial bed + 1.0 m. The two cohesive configurations have almost the
same bed change as the non-cohesive one and are left out of the table. In the configuration with the
ledger of fines, water remains on the floodplain at 200 h, and the bed change is a mean that includes
those wet cells (with almost no change).)

- **Varying discharge alone does not turn the inner bank into land**: bars exposed at low flow are
  eroded by the next flood (width 25.4 m and amplitude 27 m at 200 h; the flood lasts about half
  of the period, so the change is smaller than under a constant discharge).
- **With fixation the inner bank stays as land**: bars exposed at low flow become fixed (483 cells
  = 1,932 m² with a > 0.5 inside the initial channel at 200 h) and survive the next flood. The
  outer banks keep retreating (amplitude 33 m), and at low flow the water gathers in the pools
  along the outer banks. In the flood period (150 h) 99 of 324 fixed cells are submerged; the top
  of the fixed bars (at most +0.87 m) stops at the flood water surface and does not reach
  floodplain level.
- **A gentle recession gives less fixation** (param_fixrec.txt): 191 fixed cells (483 with the
  rectangular wave), bar top 0.77 m, width 22.6 m. Bed-load deposition is capped by the water
  surface of the supplying cell, so the highest deposition happens during the peak; a longer
  recession shortens the peak and slows everything down.
- **Suspended fines fill the initial channel with bars, and the flow cuts new bends**
  (param_fixsusp.txt): feeding fines during the floods lets the fines settle on and around the
  fixed bars, which grow: the fixed cells increase to 1,040, of which 115 rise above floodplain
  level (bar top 1.17 m), and the low-flow channel narrows to 15.0 m at 100 h. Once the initial
  channel is filled, from about 150 h the flow cuts new bends into the floodplain that cross the
  initial channel (x ≈ 180–470 m; wavelength 70–90 m, less than half the initial one), and the
  amplitude of the wet belt grows to 51 m at 200 h. Fines settle on the floodplain near the inlet
  (196 cells). This configuration is sensitive to the numerical settings of the flow: with the
  opening treatment f_opening_dynamic = 2, the bar top stops at about 0.8 m and the outer banks
  almost stop retreating.

### Sediment feed: stopping degradation and raising bars to floodplain level

![Configurations with sediment feed](figs/feed.png)

Bed change at 100 h and 200 h (both low-flow periods) of the two varying Q + fixation
configurations with sediment feed. Black = initial banks, green = water edge, brown = fixed bars
(a > 0.5) inside the initial channel.

- **With capacity feed the fixed bars begin to reach floodplain level** (param_fixfeed.txt): the
  degradation of the channel eases to −0.08 to −0.39 m (−0.51 to −0.85 m without feed), and of
  the 851 fixed cells at 200 h (483 without feed) 72 rise above floodplain level (+1.0 m; bar
  top 1.07 m; capacity feed 3,557 m³).
- **With the ledger of fines in the bed, bars grow above floodplain level at a feed factor of 0.5,
  and the floods spill onto the floodplain** (param_fixsuspfines.txt): with an initial bed of
  coarse sand only (`fines_frac0 = 0`), only fines that have been deposited are re-entrained, so
  the channel does not degrade and the initial channel fills with bars (bed change inside the
  initial channel at 200 h +0.95 / +0.64 / +0.49 m at x = 50–150 / 150–300 / 300–500 m). Of the
  1,340 fixed cells at 200 h, 550 rise above floodplain level (bar top 1.64 m). The intended
  sequence (deposition during floods → exposure at low flow → fixation → floodplain level)
  appears without tuning the feed concentration and goes on above floodplain level. Where the bars
  fill the channel, the flow swings out onto the floodplain and cuts new bends from the inlet to
  x ≈ 220 m and at x ≈ 350–480 m. From about 125 h the floods spill onto the floodplain, the water
  does not drain away even at low flow, and at 200 h shallow water is left across the whole width
  of the floodplain at x ≈ 0–450 m (green lines in the figure; 26,359 wet cells). Floodplain
  deposition covers 694 cells, capacity feed is 4,151 m³, and the fines carried along with the
  bed load by the ledger add up to 7.9 × 10⁵ m³.

### Ledgers

| Case | Angle-of-repose avalanching | Bank-erosion law | Slump blocks | Capacity feed | Fines carried with bed load | Firings of fluv_dzmax (edges) |
|---|---|---|---|---|---|---|
| Non-cohesive (constant Q) | 3,958 | – | – | – | – | 41,274 |
| Cohesive (constant Q) | 1,507 | 423 | – | – | – | 7,406 |
| Cohesive + slump blocks | 1,197 | 458 | 1,279 | – | – | 22,669 |
| Non-cohesive + capacity feed | 4,306 | – | – | 5,884 | – | 126,155 |
| Varying Q only | 1,792 | – | – | – | – | 852 |
| Varying Q + fixation | 3,190 | – | – | – | – | 406 |
| Same, gentle recession | 2,181 | – | – | – | – | 144 |
| Varying Q + fixation + suspended fines | 15,216 | – | – | – | – | 292,347 |
| Varying Q + fixation + capacity feed | 5,626 | – | – | 3,557 | – | 10,102 |
| Varying Q + fixation + fines + feed + ledger of fines | 8,623 | – | – | 4,151 | 790,965 | 48,947 |

(m³. Collapse and erosion are bulk volumes, feed and fines are solid volumes. plot_results.py
reads them from the ledgers in the screen output.)

## What this model cannot represent (differences from the real phenomena)

- **The channel is terrain on a grid**: the banks are 2 m steps and bank retreat proceeds one
  cell at a time. Where the flow hits a convex corner of a step, a locally deep hole forms
  (inherent in the raster representation; limiting the deviation angle of the secondary flow
  with `sec_rmax` makes it shallower).
- **Under constant discharge the inner bank does not become land**: bedload does not deposit
  above the water level of the supplying cell, so the bars stay under water and the retreat of
  the outer bank becomes an increase of the width as it is. The advance of the inner bank needs
  exposure in low flow with fixation, or deposition of fines.
- **Fixation is schematic**: species, growth and dieback of vegetation are not distinguished;
  only the degree of fixation a represents it. There are no standard values of T_fix and c_τ in
  the literature, and the values of this example (10 h, 10) are schematic. Dieback under water
  (`fix_tdec`) is not used.
- **The secondary flow is of the equilibrium type**: the secondary flow responds instantly to
  the streamline curvature, without the lag with which it develops after entering a bend (the
  non-equilibrium adaptation length; in the form of Struiksma et al. 1985, about 10–20 times the
  depth for a Chézy coefficient C = 50 m^1/2/s).
- **Two grain components in the bed**: bedload and suspended sediment have one grain size each,
  with no mixed-size exchange layer and no vertical stratigraphy (the ledger of fines treats
  buried fines as available for entrainment too).
- **The speed of meander development is not compared with real rivers**: in 200 h the amplitude of
  the wet belt grows from 19 m to 25–51 m (except the configuration with the ledger of fines,
  where water remains on the floodplain) and the mechanisms of outer-bank retreat, inner-bank
  advance and lateral migration of the channel are in place, but under a constant discharge the
  change is mainly widening and loop extension, and the stage at which the growth of the loops or
  the speed of migration could be compared with real rivers is not reached.

## Notes

- **Edges at the rim of the inflow section**: all configurations set `f_inflow_edge = 2` (zero
  advection term on the edges into the inflow section, with their speed capped by the energy
  head). With the default 0, the capacity-feed configurations stop through a positive feedback
  between scour beside the inlet and the jet (developer.md §68.40). Results near the inlet depend
  on this rule.
- **Dynamic reassignment of blocked openings**: all configurations write out the default
  `f_opening_dynamic = 3`. An incised channel without a channel mask needs 2 or more to keep the
  conveyance of the rows next to the banks (1 has no effect there; developer.md §84.7,
  test/uniflow).
- **Time step**: dt = 0.2 s, and 0.1 s for the two configurations with suspended sediment (the
  configuration with suspended sediment and fixation exceeds the CFL limit at 0.2 s).
- **Limit of the bed change per update**: `fluv_dzmax` (0.05 m) fires on 144–292,347 edges (ledger
  table), more often in the varying Q + fixation + suspended fines configuration and the
  non-cohesive + capacity feed configuration. morfac = 50 is large; lowering it reduces this.
- **Reproducibility**: the same executable gives bit-identical results for any number of threads,
  but a different compiler, optimisation or CPU (this README uses gfortran 13.3 with -Ofast
  -march=native, which uses the instructions of the CPU it is built on) changes the rounding, which
  the feedback between bank collapse and flow amplifies into different numbers.
  When comparing, look at the direction and size of the differences between configurations rather
  than at matching values of width or amplitude.

## Starting points for sensitivity experiments

- `fix_tfix`, `fix_ctau`: speed and strength of fixation. Choose them by the ratio
  T_fix/T_return to the flood period (in Asahi et al. 2013 meanders develop at 0.025–0.5 and do
  not at 1).
- `fix_tdec`, `fix_ctau_bank`: decay of fixation under water and the increment ratio applied to
  bank erosion (developer.md §84.13). The remedy when fixed bars stay submerged without being
  eroded.
- `berode_kb`, `rf_hc`, `berode_hcover`: speed of retreat of cohesive banks. In the slump-block
  configuration the critical height H_c (a value exceeded by the initial bank height + the scour
  depth of the pool) decides when the retreat starts.
- `inflow_cs_fac`, `fines_la`: the factor of the equilibrium-concentration feed of suspended
  sediment and the thickness of the exchange layer for fines in the bed.
- `sec_rmax`, `repose_phi`: depth of the pools at the outer banks and how easily the banks
  collapse.
- `fluv_bcfeed_fac`: factor of the capacity feed (0 = no feed, 1 = the bed at the inlet held
  fixed).

## References

- Ashida, K. and Michiue, M. (1972): Study on hydraulic resistance and bed-load transport rate in
  alluvial streams. *Proc. JSCE*, 206, 59–69 (in Japanese).
- Asahi, K., Shimizu, Y., Nelson, J. and Parker, G. (2013): Numerical simulation of river
  meandering with self-evolving banks. *J. Geophys. Res. Earth Surf.*, 118(4), 2208–2229.
- Braudrick, C. A., Dietrich, W. E., Leverich, G. T. and Sklar, L. S. (2009): Experimental
  evidence for the conditions necessary to sustain meandering in coarse-bedded rivers.
  *Proc. Natl. Acad. Sci. USA*, 106(40), 16936–16941. doi:10.1073/pnas.0909417106 (checked
  against the abstract)
- Engelund, F. (1974): Flow and bed topography in channel bends. *J. Hydraul. Div. ASCE*,
  100(HY11), 1631–1648. (Cited by Asahi et al. (2013) as the source of N* = 7; the text itself
  has not been checked)
- Hasegawa, K. (1989): Universal bank erosion coefficient for meandering rivers. *J. Hydraul.
  Eng.*, 115(6), 744–765.
- Parker, G., Shimizu, Y., Wilkerson, G. V., Eke, E. C., Abad, J. D., Lauer, J. W., Paola, C.,
  Dietrich, W. E. and Voller, V. R. (2011): A new framework for modeling the migration of
  meandering rivers. *Earth Surf. Process. Landforms*, 36(1), 70–86. (checked against the
  abstract)
- Struiksma, N., Olesen, K. W., Flokstra, C. and de Vriend, H. J. (1985): Bed deformation in
  curved alluvial channels. *J. Hydraul. Res.*, 23(1), 57–79. doi:10.1080/00221688509499377
- Tal, M. and Paola, C. (2007): Dynamic single-thread channels maintained by the interaction of
  flow and vegetation. *Geology*, 35(4), 347–350. doi:10.1130/G23260A.1 (checked against the
  abstract)

## Related documents

- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — settings of the
  bedload-direction corrections, bank erosion, angle-of-repose avalanching, slump blocks,
  fixation, suspended sediment and the ledger of fines
- docs/meander_plan.md (master design document), developer.md §84 (record of implementation and
  verification)
- Verification: [test/bendsed](../../../test/bendsed/) (cross-section of a bend),
  [test/berode](../../../test/berode/) (bank erosion and slump blocks),
  [test/repose](../../../test/repose/) (angle-of-repose avalanching),
  [test/fixation](../../../test/fixation/) (fixation), [test/uniflow](../../../test/uniflow/)
  (conveyance of rows next to the banks)
- [examples/meander_cutoff](../../meander_cutoff/en/README.md) — cutoff of meander loops by the
  same mechanisms
