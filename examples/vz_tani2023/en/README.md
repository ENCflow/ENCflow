# examples/vz_tani2023 — reproducing the VZ runoff model of Tani (2023) (Tatsunokuchi-yama TY1 and TY2)

> English mirror of examples/vz_tani2023/README.md. The Japanese file is the master copy.

This example recomputes, with the vertical unsaturated flow (VZ) runoff of ENCflow
([fn_vz](../../../docs/en/users_guide/vz.md)) and the same settings, the
computation of the VZ runoff model that Tani (2023)[^tani2023] carried out with
HYDRUS-1D, and compares it with the calculated runoff rates of the paper. The
target is the Tatsunokuchi-yama Experimental Watershed (TY, near Okayama), with its
three catchments (Kitadani KT 17.27 ha, Minamidani MN 22.61 ha, hillslope SL
500 m²), for the Baiu event of July 1987 (TY1) and the typhoon event of September
1976 (TY2). Comparing with the values calculated in the paper checks the 1D
Richards kernel of ENCflow and the read-out of the zones (integrating over the
catchment the drainage at the depth of the soil) against the results of an
independent implementation.

## Handling of the numbers of the paper (no data are shipped)

The rainfall, the observed runoff rates and the calculated runoff rates of the paper
exist only in figures. This example keeps no numbers in the repository: the user
obtains the PDF of the paper from J-STAGE, and `extract_tani2023.py` extracts them
into `data/` from the coordinates of the vector drawing of the figures (rain bars,
observed markers ○ KT, × MN, △ SL, and the curves of the calculated values).

- Target PDF: <https://www.jstage.jst.go.jp/article/jjshwr/36/1/36_36.1741/_pdf/-char/ja>
  (the SHA-256 of the version obtained on 2026-10-26 is recorded in the script; a
  different version produces a warning)
- Check of the reading (compared with Table 1; the script shows it every time):

  | Event | Rain bars | Maximum hourly rainfall (Table 1) | Sum of the bars (total rainfall of Table 1) |
  |---|---|---|---|
  | TY1 (Fig. 14) | 48 bars of 1 hour | 14.50 mm/h (14.5) | 132.46 mm (131.5 mm) |
  | TY2 (Fig. 15) | 112 bars of 1 hour | 14.30 mm/h (14.3) | 376.59 mm (374.9 mm) |

  The heights of the TY1 bars sit on a 0.5 mm grid within ±0.012 mm, so the reading
  error is within the precision of the drawing. The differences of the totals
  (+0.7 % and +0.5 %) are thought to come from, for example, a difference between
  the period summed in Table 1 and the range of the figure (the cause cannot be
  confirmed from the paper).
- The observed runoff rates come from the hydrological observation of the Kansai
  Research Center of the Forestry and Forest Products Research Institute
  (Section III.1 of the paper).

## Settings (description in the paper → ENCflow)

| Item | Paper (Tani 2023) | ENCflow (`param_ty1.txt`, `param_ty2.txt`) |
|---|---|---|
| Reference column | 10 m long, 2.5 cm steps, free drainage at the bottom (free drainage of HYDRUS-1D) (II.2) | `vz_depth = 10`, `vz_dz = 0.025`, `f_vz_bottom = 1` |
| Soil physical properties | Kosugi model, TY: θr 0.230, θs 0.370, ψm −20.0 cm, σ 1.60, Ks 5.0×10⁻³ cm/s (Table 2) | `vz_thetar = 0.230`, `vz_thetas = 0.370`, `vz_psim = -0.200`, `vz_sigma = 1.60`, `vz_ks_mmh = 180` |
| Initial condition | ψ = −400 cm at all depths (based on observations at SL). TY2 is the same as TY1 (IV.2) | `vz_psi0 = -4.0` |
| Distribution of soil depth | linear distribution: classes every 2.5 cm from 0 cm to the maximum occupy equal areas. Maximum SL 100, KT 175, MN 250 cm (values chosen by the author to fit the wet period of TY1) (IV.1, IV.2) | 1 class = 1 cell (1 m²), 1 catchment = a zone of one row (`make_case.py`). The 0 cm class is a cell with soil depth 0 (its rain drains as it is) |
| Column and catchments | read out of the computation of the same soil column for each catchment | the 3 zones (KT, MN, SL) share one column (`vz_zone_col = 1`) |
| Runoff rate | the downward fluxes at each depth integrated over the distribution (Fig. 3) | 10-minute differences of the cumulative drainage vdrain of a zone / area of the zone (`compare_tani2023.py`). Drainage leaves the system (`vz_out_kind = 2`) |
| Baseflow | the baseflow separated from observations is added to the calculated values in the figures (III.1) | not added (the separation line cannot be recovered from the paper). Compare in the range of large runoff rates |
| Rainfall | hourly rainfall (bars of the figures) | the bars of the figures as an hourly step function (`data/precip_TY*.txt`). The assignment in time is estimated below |
| Time | TY1: 1987-07-14 06:00 to 07-21 06:00, TY2: 1976-09-08 12:00 to 09-14 00:00 (time axes of the figures) | `tt` = 7 days and 5.5 days, `dt = dt_vz = 60` s, records every 10 minutes |

All cells are VZ cells, so no surface flow occurs (the grid is a container for
integrating the runoff). As an extension on the ENCflow side, cells with soil depth
0 (the 0 cm class of the linear distribution) are now allowed (developer.md §87.2).

## Running

```bash
cd examples/vz_tani2023
make                          # link to the executables in bin/ and the grid input data/
./Run.sh <PDF of the paper>   # extraction → computation of TY1 and TY2 → comparison (about 20 s and 30 s)
./Run.sh                      # only computation and comparison once extracted
```

The extraction needs the Python package pdfminer.six (`pip install pdfminer.six`).
If matplotlib is available, `result_ty1/fig_ty1.png` and `result_ty2/fig_ty2.png`
show the rainfall and the runoff rates calculated in the paper, by ENCflow and
observed (log axis). They contain numbers of the paper, so the figures are not kept
in the repository either.

## Results (2026-10-26; gfortran 13.3, default numerical settings)

Output of `compare_tani2023.py`. The log10 ratio is log10(ENCflow / value calculated
in the paper), and p90 is the 90 % value of its absolute value (0.1 corresponds to a
ratio of about 26 %, 0.03 to about 7 %). The peak time is the median of the time
differences between the main maxima of the calculated values of the paper and the
maxima of ENCflow.

| Event | Catchment | ≥ 0.1 mm/h: median / p90 | ≥ 0.5 mm/h: median / p90 | Peak paper / ENCflow | Peak time difference |
|---|---|---|---|---|---|
| TY1 | KT | −0.042 / 0.113 | −0.020 / 0.065 | 4.29 / 4.13 mm/h (−3.9 %) | −0.10 h |
| TY1 | MN | −0.036 / 0.246 | −0.029 / 0.097 | 2.79 / 2.90 mm/h (+4.0 %) | −0.18 h |
| TY1 | SL | −0.010 / 0.149 | −0.008 / 0.060 | 7.42 / 7.15 mm/h (−3.7 %) | −0.11 h |
| TY2 | KT | −0.005 / 0.026 | −0.005 / 0.021 | 8.65 / 8.68 mm/h (+0.4 %) | −0.09 h |
| TY2 | MN | −0.003 / 0.089 | −0.003 / 0.029 | 6.31 / 6.46 mm/h (+2.3 %) | +0.07 h |

- **TY2** almost overlaps the values calculated in the paper (above 0.5 mm/h, 90 % of
  the points are within 7 %). This is an agreement between results of the same
  equations and settings solved independently, so the kernel and the read-out of
  ENCflow reproduce the computation of the paper.
- **TY1** is also within 15–25 % for 90 % of the points in the range of large runoff
  rates, with peaks within 4 %. In the low-flow periods around 0.1 mm/h (the rainless
  periods in the first half of the event) ENCflow is lower by about 0.01–0.03 mm/h,
  which corresponds to the size of the baseflow added to the values calculated in
  the paper (not added in ENCflow).
- A peak time difference of about −0.1 h is of the size caused by, for example,
  ENCflow obtaining the runoff rate as 10-minute averages.
- The comparison with observations (discussion in IV.2 of the paper: in the first
  half of TY1 the computation exceeds the observations and they come to agree as the
  catchment becomes wet) can be checked in the figures. As in the paper, this example
  makes no adjustment to fit the observations.

## Assignment of the rainfall in time (estimated)

The rain bars of the figures are drawn over the hour centred on the full hour, and
the figures do not tell whether the rain belongs to the hour before or after the
full hour. The computation was run with the bars as drawn and shifted by ±0.5 h and
±1.0 h, and the assignment minimising p90 for the values of the paper of 0.5 mm/h or
more was taken (`RAIN_SHIFT_H` of `extract_tani2023.py`).

| Event | −1.0 h | −0.5 h | bars as drawn | +0.5 h | +1.0 h |
|---|---|---|---|---|---|
| TY1 (KT / SL / MN) | — | 0.207 / 0.306 / 0.382 | 0.171 / 0.238 / 0.276 | **0.065 / 0.060 / 0.097** | 0.096 / 0.106 / 0.183 |
| TY2 (KT / MN) | 0.100 / 0.121 | **0.020 / 0.028** | 0.067 / 0.094 | 0.157 / 0.200 | — |

TY1 corresponds to the hour starting at the full hour and TY2 to the hour ending at
the full hour. Why the direction differs between the events cannot be told from the
paper (a difference in how the figures were made or in how the original data were
time-stamped is suspected, but not confirmed).

## What this example does not cover yet

- Kiryu (KI1, KI2), Mettman Ridge (MREX, MR1) and the sprinkling experiment on a
  small hillslope in Kiryu (KIEX). For KI the paper treats half of the drainage as
  deep percolation, and for MR it subtracts 0.3 mm/h from the drainage (and for
  MREX it also removes 20 % of the rain as evapotranspiration), outside the model;
  the comparison script of the example can do the same. KIEX can be set up with the
  hydrostatic initial condition (`vz_wt0`) and a fixed bottom pressure.
- The "investigated distribution" of soil depth (frequency distributions of KI and
  MR) has no numbers in the paper, so only the linear distribution can be handled
  (the paper also reports that the difference between them is small).
- Comparison with the observed pressure heads (Fig. 14 (d) to (i)).

## References

[^tani2023]: Tani, M. (2023): Reevaluating the runoff mechanisms of small mountainous catchments by applying a new storm-runoff model based on the vertical unsaturated flow (in Japanese with English abstract). *Journal of Japan Society of Hydrology and Water Resources*, 36(1), 20–51. doi:10.3178/jjshwr.36.1741

- Kosugi, K. (1996): Lognormal distribution model for unsaturated soil hydraulic properties. *Water Resources Research*, 32(9), 2697–2703.
- Šimůnek, J., Šejna, M., Saito, H., Sakai, M. and van Genuchten, M. Th. (2013): The Hydrus-1D software package for simulating the movement of water, heat, and multiple solutes in variably saturated media, Version 4.17. HYDRUS Software Series 3, Department of Environmental Sciences, University of California Riverside, 344 pp. (software used for the computation in the paper)
