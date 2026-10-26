# examples/vz_tani2023 — reproducing the VZ runoff model of Tani (2023) (7 events)

> English mirror of examples/vz_tani2023/README.md. The Japanese file is the master copy.

This example recomputes, with the vertical unsaturated flow (VZ) runoff of ENCflow
([fn_vz](../../../docs/en/users_guide/vz.md)) and the same settings, the
computations of the VZ runoff model that Tani (2023)[^tani2023] carried out with
HYDRUS-1D, and compares them with the calculated runoff rates of the paper. All
seven events of the paper are covered.

| Event | Target | Figure |
|---|---|---|
| KIEX | sprinkling experiment on the small hillslope Plot 2 (9 m², 50 cm soil layer) of the Kiryu Experimental Watershed (1981; Ohta et al. 1983) | Fig. 12 |
| MREX | sprinkling experiment on the zero-order catchment CB1 (860 m²) of Mettman Ridge (Oregon, USA) (May–June 1992) | Fig. 11 |
| MR1 | natural storm on the same CB1 during which a shallow landslide occurred (November 1996) | Fig. 13 |
| TY1, TY2 | Kitadani KT 17.27 ha, Minamidani MN 22.61 ha and hillslope SL 500 m² of the Tatsunokuchi-yama Experimental Watershed (Okayama) (July 1987, September 1976) | Fig. 14, Fig. 15 |
| KI1, KI2 | Kiryu Experimental Watershed (Shiga; weathered granite, 5.99 ha) (August 1982, July 2006) | Fig. 16, Fig. 17 |

Comparing with the values calculated in the paper checks the 1D Richards kernel of
ENCflow and the read-out of the zones (integrating over the catchment the drainage
at the depth of the soil) against the results of an independent implementation.

## Handling of the numbers of the paper (no data are shipped)

The rainfall, the observed runoff rates and the calculated runoff rates of the paper
exist only in figures. This example keeps no numbers in the repository: the user
obtains the PDF of the paper from J-STAGE, and `extract_tani2023.py` extracts them
into `data/` from the coordinates of the vector drawing of the figures (rain bars,
observed markers or curves, and the curves of the calculated values).

- Target PDF: <https://www.jstage.jst.go.jp/article/jjshwr/36/1/36_36.1741/_pdf/-char/ja>
  (the SHA-256 of the version obtained on 2026-10-26 is recorded in the script; a
  different version produces a warning)
- The time axes are calibrated from the ticks of the figures (for date axes, the
  major ticks at 0 o'clock; the date labels are at the middle of the days), and the
  vertical axes from the major ticks. The reading is checked against Table 1 (the
  script shows it every time):

  | Event | Rain bars of the figure | Check (Table 1) |
  |---|---|---|
  | KIEX | 3 steps (53.4, 26.4, 79.8 mm/h, 0 to 2.83 h) | maximum 79.76 mm/h (79.8), total 164.13 mm (164.0) |
  | MREX | bars averaged over about 12 hours (day–night variation), 1.34 to 1.95 mm/h | total 270.95 mm (276.6; −2.0 %) |
  | MR1 | 80 bars of 1 hour (16 to 19 November) | no check (the figure does not include the start of the event, 292.2 mm in 112 h) |
  | TY1 | 48 bars of 1 hour | maximum 14.50 mm/h (14.5), total 132.35 mm (131.5; +0.6 %) |
  | TY2 | 112 bars of 1 hour | maximum 14.30 mm/h (14.3), total 376.56 mm (374.9; +0.4 %) |
  | KI1 | 29 bars of 1 hour | maximum 30.00 mm/h (30.0). The figure is part of the event (348.9 mm, 58 h) |
  | KI2 | 91 bars of 1 hour | total 340.66 mm (341.3; −0.2 %) |

- Sources of the observations (according to the paper): TY from the hydrological
  observation of the Kansai Research Center of the Forestry and Forest Products
  Research Institute, KI from the hydrological observation of Kyoto University,
  MREX from data provided by Dr. Anderson, MR1 from the figures of Montgomery et al.
  (2009), KIEX from the figure of Ohta et al. (1983).

## Settings (description in the paper → ENCflow)

Common: a soil column 10 m long with 2.5 cm steps and free drainage at the bottom
(Section II.2 of the paper; except KIEX), and the Kosugi model (Table 2). The soil
depth follows the "linear distribution" (classes every 2.5 cm from 0 cm to the
maximum occupy equal areas), with 1 class = 1 cell (1 m²) and 1 catchment = a zone of
one row (`make_case.py`). The 0 cm class is a cell with soil depth 0 (its rain
drains as it is). All cells are VZ cells, so no surface flow occurs, and the drainage
leaves the system (`vz_out_kind = 2`). The runoff rate is the time difference of the
cumulative drainage vdrain of a zone divided by its area, and the post-processing
that the paper did outside the model is applied in the same way
(`compare_tani2023.py`).

| Event | Soil | Soil depth | Initial condition | Post-processing of the paper (applied when comparing) | Time 0 and period |
|---|---|---|---|---|---|
| KIEX | KI | a 50 cm column, seepage with ψ fixed to 0 at the bottom (`f_vz_bottom = 2`) | hydrostatic: ψ = 0 at the bottom, ψ = −50 cm at the surface (`vz_wt0 = 0.5`) | none (drainage at the bottom = runoff rate) | start of the rain, 7 h |
| MREX | MR | 0 to 200 cm (81 classes) | ψ = −100 cm | 20 % of the rain removed as evapotranspiration (input × 0.8). Deep percolation of 0.3 mm/h subtracted from the drainage, half each to the upper and lower weirs | 1992-05-27 00:00, 9 days |
| MR1 | MR | 0 to 200 cm | ψ = −100 cm | 0.3 mm/h subtracted from the drainage, half to the upper weir (L/s with × 860 m²) | 1996-11-16 00:00, 4 days |
| TY1 | TY | KT 0 to 175, MN 0 to 250, SL 0 to 100 cm (3 zones share the column) | ψ = −400 cm | none | 1987-07-14 06:00, 7 days |
| TY2 | TY | same | ψ = −400 cm | none | 1976-09-08 12:00, 5.5 days |
| KI1 | KI | 0 to 130 cm (53 classes; the mean 65 cm is the median) | ψ = −100 cm | half of the drainage treated as deep percolation, the rest as runoff | 1982-08-01 00:00, 1.5 days |
| KI2 | KI | 0 to 130 cm | ψ = −100 cm | same | 2006-07-14 10:00, 8.6 days |

| Soil (Table 2) | θr | θs | ψm | σ | Ks | ENCflow |
|---|---|---|---|---|---|---|
| TY (Tatsunokuchi-yama) | 0.230 | 0.370 | −20.0 cm | 1.60 | 5.0×10⁻³ cm/s | `vz_ks_mmh = 180`, `vz_psim = -0.200` |
| KI (Kiryu) | 0.212 | 0.507 | −9.4 cm | 1.34 | 1.9×10⁻¹ cm/s | `vz_ks_mmh = 6840`, `vz_psim = -0.094` |
| MR (Mettman Ridge) | 0.180 | 0.500 | −25.0 cm | 0.80 | 3.4×10⁻² cm/s | `vz_ks_mmh = 1224`, `vz_psim = -0.250` |

The calculated values of the paper for TY and KI include the baseflow separated from
the observations (Section III.1 of the paper). The separation line cannot be
recovered from the paper, so it is not added to the ENCflow values (an approximate
comparison is added only for KI2; see the results). As extensions on the ENCflow
side, cells with soil depth 0 and the hydrostatic initial condition `vz_wt0` were
added (developer.md §87.2).

## Running

```bash
cd examples/vz_tani2023
make                          # link to the executables in bin/ and the grid input data/grid_*/
./Run.sh <PDF of the paper>   # extraction → computation of the 7 events → comparison (0 to 40 s per event)
./Run.sh                      # only computation and comparison once extracted
```

The extraction needs the Python package pdfminer.six (`pip install pdfminer.six`).
If matplotlib is available, `result_<event>/fig_<event>.png` shows the rainfall and
the runoff rates calculated in the paper, by ENCflow and observed. They contain
numbers of the paper, so the figures are not kept in the repository either.

## Results (2026-10-26; gfortran 13.3, default numerical settings)

Output of `compare_tani2023.py`. The log10 ratio is log10(ENCflow / value calculated
in the paper), and p90 is the 90 % value of its absolute value (0.1 corresponds to a
ratio of about 26 %, 0.03 to about 7 %). Limits 1 and 2 are the lower limits of the
calculated values of the paper at the compared points (KIEX 1 and 10 mm/h, MREX 0.1
and 0.3 mm/h, MR1 0.1 and 0.3 L/s, TY and KI 0.1 and 0.5 mm/h). The peak time is the
median of the time differences between the main maxima of the values calculated in
the paper and the nearest maxima of ENCflow. The comparison uses the values
calculated with the linear distribution (QcC for MREX, MR1 and KI).

| Event | Compared quantity | Limit 1: median / p90 | Limit 2: median / p90 | Peak paper / ENCflow | Peak time difference |
|---|---|---|---|---|---|
| KIEX | runoff rate | −0.031 / 0.085 | −0.010 / 0.085 | 79.8 / 79.8 mm/h (−0.0 %) | +0.15 h |
| MREX | runoff rate of each weir QcC | +0.001 / 0.040 | +0.002 / 0.025 | 0.525 / 0.536 mm/h (+2.2 %) | +0.49 h |
| MR1 | discharge of the upper weir QcC | −0.008 / 0.059 | −0.005 / 0.031 | 1.49 / 1.47 L/s (−1.8 %) | −0.10 h |
| TY1 KT | runoff rate | −0.042 / 0.113 | −0.020 / 0.065 | 4.29 / 4.13 mm/h (−3.9 %) | −0.10 h |
| TY1 MN | runoff rate | −0.036 / 0.246 | −0.029 / 0.097 | 2.79 / 2.90 mm/h (+4.0 %) | −0.18 h |
| TY1 SL | runoff rate | −0.010 / 0.149 | −0.008 / 0.060 | 7.42 / 7.15 mm/h (−3.7 %) | −0.11 h |
| TY2 KT | runoff rate | −0.005 / 0.026 | −0.005 / 0.021 | 8.65 / 8.68 mm/h (+0.4 %) | −0.09 h |
| TY2 MN | runoff rate | −0.003 / 0.089 | −0.003 / 0.029 | 6.31 / 6.46 mm/h (+2.3 %) | +0.07 h |
| KI1 | runoff rate QcC | −0.021 / 0.114 | −0.016 / 0.093 | 14.6 / 14.5 mm/h (−0.4 %) | +0.15 h |
| KI2 | runoff rate QcC | −0.149 / 0.400 | −0.144 / 0.420 | 4.21 / 3.91 mm/h (−7.2 %) | −0.05 h |
| KI2 + straight baseflow | same | +0.002 / 0.105 | +0.001 / 0.080 | 4.21 / 4.31 mm/h (+2.4 %) | −0.05 h |

- **KIEX, MREX, MR1 and TY2** almost overlap the values calculated in the paper
  (at limit 2, 90 % of the points within 5 to 22 %, peaks within 2.3 %). This is an
  agreement between results of the same equations and settings solved
  independently, so the kernel and the read-out of ENCflow reproduce the computation
  of the paper. The check includes the short column with a fixed bottom pressure and
  the hydrostatic initial condition for KIEX, the subtraction of deep percolation
  and the split between the weirs for MREX and MR1, and the sharing of one column by
  three catchments for TY.
- **TY1 and KI1** are also within 15 to 25 % for 90 % of the points in the range of
  large runoff rates, with peaks within 4 %. ENCflow is lower in the low-flow parts
  of the recessions by the baseflow added to the values calculated in the paper.
- For **KI2**, the ENCflow values are about 30 % lower in the median. The difference
  (paper − ENCflow) grows almost in proportion to time from 0.1 to 0.6 mm/h, which
  has the shape of the separated baseflow of the paper (a straight line joining the
  start and the end of the storm runoff; Section III.1 of the paper). Kiryu, on
  weathered granite, has a large baseflow, whose contribution is conspicuous in KI2
  with its small runoff. As an approximation, adding to ENCflow "a straight line from
  the first observed value (0.11 mm/h) to the last (0.63 mm/h)" gives a median of
  +0.001 and p90 0.080 (this line is not the separation line of the paper itself but
  an approximation for checking).
- For **MR1**, the paper does not state when its computation started, and the figure
  starts in the middle of the event (16 November), so the computation starts at the
  left end of the figure with the initial condition ψ = −100 cm. ENCflow is slightly
  lower for the small runoff in the first half, and agrees well after the heavy rain.
- The rainfall in the figure of **MREX** is averaged over about 12 hours, coarser
  than the rainfall used in the paper (records of artificial rain varying between day
  and night), so the diurnal variation cannot be reproduced. The mean runoff rate,
  the rise and the recession agree.
- Peak time differences of about ±0.2 h are of the size caused by, for example,
  ENCflow obtaining the runoff rate as averages over the recording interval and the
  points of the curves of the paper being hourly (the +0.49 h of MREX compares the
  diurnal maxima driven by the 12-hour averaged rainfall).
- The comparison with observations (discussion in Sections IV and V of the paper)
  can be checked in the figures. As in the paper, this example makes no adjustment to
  fit the observations.

## Assignment of the rainfall in time (estimated)

The 1-hour rain bars of the figures are drawn centred on the full hour, and the
figures do not tell whether the rain belongs to the hour before or after the full
hour. The computation was run with the bars as drawn and shifted by ±0.5 h and
±1.0 h, and the assignment minimising p90 for the values of the paper at limit 2 or
more was taken (`RAIN_SHIFT_H` of `extract_tani2023.py`; for KI2 the comparison with
the straight baseflow added).

| Event | −1.0 h | −0.5 h | bars as drawn | +0.5 h | +1.0 h |
|---|---|---|---|---|---|
| TY1 KT | — | 0.207 | 0.171 | **0.065** | 0.096 |
| TY2 KT | 0.100 | **0.020** | 0.067 | 0.157 | — |
| KI1 | 0.188 | **0.093** | 0.142 | 0.304 | 0.444 |
| KI2 | 0.184 | **0.080** | 0.118 | 0.271 | 0.354 |
| MR1 | 0.059 | **0.031** | 0.047 | 0.089 | 0.114 |

Only TY1 corresponds to the hour starting at the full hour; the others correspond to
the hour ending at the full hour. Why only TY1 differs cannot be told from the paper
(TY1 is an event also used by Tani et al. (2020), so a difference in how the figure
was made is suspected, but not confirmed). KIEX (bars from the start of the rain at
0 h) and MREX (bars averaged over about 12 hours) are not shifted.

## What this example does not cover yet

- The "investigated distribution" of soil depth (frequency distributions of KI and
  MR) has no numbers in the paper, so only the linear distribution can be handled
  (the paper also reports that the difference between them is small). For the same
  reason the calculated value of the lower weir of MR1 (three times the investigated
  distribution) is not compared.
- The baseflow added to the values calculated in the paper itself (the separation
  line cannot be recovered from the paper).
- Comparison with the observed and calculated pressure heads (hydraulic heads)
  (Fig. 11 (c)(d), Fig. 12 (b), Fig. 13 (c), Fig. 14 (d) to (i), Fig. 16 (c),
  Fig. 17 (c)).

## References

[^tani2023]: Tani, M. (2023): Reevaluating the runoff mechanisms of small mountainous catchments by applying a new storm-runoff model based on the vertical unsaturated flow (in Japanese with English abstract). *Journal of Japan Society of Hydrology and Water Resources*, 36(1), 20–51. doi:10.3178/jjshwr.36.1741

- Kosugi, K. (1996): Lognormal distribution model for unsaturated soil hydraulic properties. *Water Resources Research*, 32(9), 2697–2703.
- Šimůnek, J., Šejna, M., Saito, H., Sakai, M. and van Genuchten, M. Th. (2013): The Hydrus-1D software package for simulating the movement of water, heat, and multiple solutes in variably saturated media, Version 4.17. HYDRUS Software Series 3, Department of Environmental Sciences, University of California Riverside, 344 pp. (software used for the computation in the paper)
