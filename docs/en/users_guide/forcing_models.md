# Rainfall and meteorology models explained (supplement to the rainfall and meteorology chapter)

> English mirror of docs/users_guide/forcing_models.md. The Japanese file is the master copy.

[Back to the rainfall and meteorology chapter](forcing.md) | [Back to the user's guide index](../users_guide.md)

This page gives the equations and the basis of the default values for the
models of the [rainfall and meteorology chapter](forcing.md): rainfall
interception (fixed ratio and initial loss), the elevation corrections of
temperature and precipitation, potential evapotranspiration (Hamon and
Thornthwaite) and degree-day snowpack and snowmelt. The implementation is
in `src/m_intercept*.f90`, `src/m_meteo.f90`, `src/m_evap.f90` and
`src/m_snow.f90`; the history of the defaults is in developer.md §65 and
§66 (in Japanese).

## 1. Rainfall interception

**Fixed interception ratio (f_icmodel = 1).** A constant fraction
$`\alpha`$ of the precipitation $`P`$ is removed as a loss and the
remainder passes to the rain/snow partition. There is no canopy storage.

```math
P_{out} = (1 - \alpha)\,P
```

**Initial loss (f_icmodel = 2).** The first part of the rainfall is stored
up to a maximum storage $`S_{\max}`$; once full, everything passes through.
Each step stores water up to the spare capacity and passes the excess.

```math
\Delta S = \min\!\left(P\,\Delta t,\ S_{\max} - S\right),
\qquad
P_{out} = P - \frac{\Delta S}{\Delta t}
```

This is the simplest form of the storage-type interception models of the
Rutter and Gash family[^crockford00] with a canopy storage $`S_{\max}`$;
drainage and evaporation in time are left to the evapotranspiration module
(evapotranspiration through `fn_evap` reduces the canopy water and restores
capacity; without it the spare capacity does not recover).

**Basis of the defaults.** $`\alpha`$ = 0.15 and $`S_{\max}`$ = 1.5 mm are
the broadleaf/mixed-forest values of the review of Crockford &
Richardson[^crockford00] (interception loss 20–40 % for conifers, 10–25 %
for broadleaf forests, 5–10 % for grassland; canopy storage 0.3–3 mm), and
are comparable with the depression storage of impervious urban surfaces
(SWMM customary values 1.3–2.5 mm[^rossman15]). Guide values by vegetation
are in the table of the chapter.

## 2. Elevation corrections of temperature and precipitation

With a uniform temperature input and `f_temp_lapse = 1`, the temperature at
elevation $`z`$ (m) is

```math
T = T_{\mathrm{input}} + \Delta T - \gamma\,(z - z_{T,\mathrm{ref}}),
\qquad
\gamma = \frac{\mathtt{temp\_lapse}}{100}
```

where $`z_{T,\mathrm{ref}}`$ is `temp_zref` and $`\Delta T`$ the value of
`tempofs` (zero if omitted). A lapse rate of 0.65 °C/100 m over 1000 m
lowers the temperature by 6.5 °C. Combining the lapse rate with temperature
maps (`fn_tempmap`) is rejected at initialisation (the offset `tempofs`
also applies to maps). The default 0.65 °C/100 m is that of the standard
atmosphere (empirical).

The precipitation correction (`f_prec_lapse = 1`) converts `prec_lapse`
from %/100 m to 1/m and applies the following factor when precipitation is
updated, before interception:

```math
F_P = \max\!\left(0,\ 1 + \beta\,(z - z_{P,\mathrm{ref}})\right),
\qquad
\beta = \frac{\mathtt{prec\_lapse}}{10000}
```

with $`z_{P,\mathrm{ref}}`$ = `prec_zref`. A gradient of 10 %/100 m over
500 m gives a factor of 1.5; negative factors are clamped to 0. The
precipitation correction and the snow temperature use the ice-surface
elevation $`z + h_i`$ when a glacier is active; evapotranspiration uses
the ground elevation $`z`$.

## 3. Potential evapotranspiration (Hamon and Thornthwaite)

Modes 3 and 4 estimate the PET (mm/day) from the daylight hours $`N`$
(hours; solar declination by Cooper's approximation) and the daily mean
temperature $`T`$ (°C):

```math
PET_{\text{Hamon}} = 0.1651\,\frac{N}{12}\,\frac{216.7\,e_s}{T + 273.3},
\qquad
e_s = 6.108\,\exp\!\left(\frac{17.27\,T}{T + 237.3}\right)\ [\mathrm{hPa}]
```

```math
PET_{\text{Thornthwaite}} = \frac{16}{30}\left(\frac{10\,\max(T, 0)}{I}\right)^{a}\frac{N}{12},
\qquad
I = \sum_{m=1}^{12}\left(\frac{\max(T_m, 0)}{5}\right)^{1.514},
\quad
a = 6.75\times10^{-7}I^3 - 7.71\times10^{-5}I^2 + 1.792\times10^{-2}I + 0.49239
```

The Hamon formula[^hamon61] is a temperature method using only the
saturation vapour density (Tetens formula) and the daylight hours; the
Thornthwaite formula[^thornthwaite48] is a climatological one whose heat
index $`I`$ comes from the monthly normal temperatures, the monthly value
being divided by 30 for a daily rate. Neither uses radiation, wind or
humidity; calibrate with `evap_kc`. Modes 3 and 4 evaluate the PET of a day
from the temperature at the start of that calendar day and keep it
constant within the day (a daily-mean temperature series is recommended).

**Order of withdrawal.** The PET is multiplied by `evap_kc`, converted from
mm/day to m/s, and each step withdraws the depth $`PET\,\Delta t`$ in the
order **canopy water (storage-type interception only) → surface water
$`h`$ → storage $`h_{rs}`$ (ponds and dam/lake capture cells) → groundwater
$`h_g`$**. Each withdrawal is capped by the available water and only the
remaining demand passes to the next store. There is no dry-soil
suppression beyond this supply limit and no sublimation from SWE. It acts
on the state after the surface-flow and groundwater updates.

**Basis of the default.** The mode-1 default of 3 mm/day is the lower side
of the warm-season reference evapotranspiration of a humid temperate
climate (FAO-56[^allen98] $`ET_0`$ of 3–5 mm/day): larger than the annual
mean of Japan (2–2.5 mm/day) and smaller than summer (4–5). Use modes 2–4
for runs spanning seasons (monthly values, latitude and normal temperatures
are given data and have no default).

## 4. Degree-day snowpack and snowmelt

Post-interception precipitation is partitioned into rain and snow and the
snow accumulates as snow water equivalent SWE. At $`T \le`$ `snow_t_snow` it
is all snow, at $`T \ge`$ `snow_t_rain` all rain, with a linear mixture
between (require `snow_t_rain ≥ snow_t_snow`; if equal, that temperature
and below give all snow). Only the liquid part reaches the surface as
rainfall.

After adding the snowfall, the melt of a step (mm; $`\Delta t`$ in seconds)
is capped by the available SWE:

```math
\Delta W_{\mathrm{melt}} = \min\left(\mathrm{SWE},\
\mathtt{snow\_ddf}\,\max(T - \mathtt{snow\_t\_melt},\,0)\,
\frac{\Delta t}{86400}\right)
```

The degree-day method[^hock03] estimates melt from air temperature alone,
folding radiation, wind and rain melt into the degree-day factor. The melt
is converted to metres and added directly to the surface water $`h`$ with
the area conversion for void fraction and active channel width (it is not
included in the rainfall intensity `pre`). For example, `snow_ddf` = 4, a
temperature 3 °C above the melt threshold and $`\Delta t`$ = 3600 s give a
melt demand of 0.5 mm; if only 0.2 mm of SWE is available, 0.2 mm melts.
Refreezing, rain retention within the snow and sublimation are not
represented.

**Basis of the defaults.** `snow_ddf` = 4 mm/°C/day is the middle of
Hock's compilation[^hock03] (mostly 2.5–6 for snow; smaller under forest,
larger in the open) and of the customary 3–5 of snowmelt floods in Japanese
mountain basins. The rain/snow thresholds 0–2 °C are customary values after
the observation that the transition occurs around a wet-bulb temperature of
1 °C. Guide values by type are in the table of the chapter.

## 5. Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| ic_alpha | 0.15 | fixed interception ratio $`\alpha`$ | **literature value** interception loss 10–25 % of broadleaf and mixed forests[^crockford00] |
| ic_smax_mm | 1.5 mm | maximum storage $`S_{\max}`$ of the initial loss | **literature value** canopy storage 0.3–3 mm[^crockford00]; comparable with the urban depression storage 1.3–2.5 mm[^rossman15] |
| temp_lapse | 0.65 °C/100 m | temperature lapse rate | **customary value** lapse rate of the standard atmosphere |
| prec_lapse | 0 | precipitation gradient | **given** no correction by default |
| evap0 | 3 mm/day | constant PET | **literature value** lower side of the warm-season $`ET_0`$ 3–5 of a humid temperate climate[^allen98] |
| evap_kc | 1 | PET conversion coefficient | **calibration** plays the role of a pan or crop coefficient |
| snow_t_snow / snow_t_rain | 0 / 2 °C | rain/snow thresholds | **customary value** range based on the observed transition around a wet-bulb temperature of 1 °C |
| snow_t_melt | 0 °C | melt threshold | **customary value** standard of the degree-day method |
| snow_ddf | 4 mm/°C/day | degree-day factor | **literature value** middle of 2.5–6 for snow[^hock03]; middle of the customary 3–5 of Japanese mountain basins |

**Where to look when revising the defaults**

- Interception ratio and canopy storage vary with the forest type
  (conifer / broadleaf / leafless season); the review by Crockford &
  Richardson[^crockford00] gives ranges by type.
- The lapse rate can be taken directly from two nearby weather stations
  at different elevations (0.5–0.7 °C/100 m depending on season).
- Set the constant PET from FAO-56[^allen98] Penman–Monteith evaluated with
  monthly climate; when using Hamon or Thornthwaite (§3), adjust evap_kc to
  close the water balance (annual runoff).
- The degree-day factor is usually calibrated against snow-depth gauges or
  the satellite-derived snow-covered area; Hock's review[^hock03] compiles
  values by region.

## 6. Verification cases

- [test/icevap](../../../test/icevap/): equivalence of minimal input and explicitly specified defaults for fixed-rate interception, initial loss and constant evapotranspiration.
- [test/frost](../../../test/frost/): comparison with analytical values for the freezing index and infiltration suppression under constant air temperature.
- [test/chichibu](../../../test/chichibu/): regression case of uniform rainfall on a real-terrain catchment.

## References

[^crockford00]: Crockford, R. H. and Richardson, D. P. (2000): Partitioning of rainfall into throughfall, stemflow and interception: effect of forest type, ground cover and climate. *Hydrol. Process.*, 14, 2903–2920.
[^rossman15]: Rossman, L. A. (2015): Storm Water Management Model User's Manual Version 5.1. US EPA, EPA/600/R-14/413b. (customary depression storage)
[^hamon61]: Hamon, W. R. (1961): Estimating potential evapotranspiration. *J. Hydraul. Div. ASCE*, 87(HY3), 107–120.
[^thornthwaite48]: Thornthwaite, C. W. (1948): An approach toward a rational classification of climate. *Geogr. Rev.*, 38, 55–94.
[^allen98]: Allen, R. G., Pereira, L. S., Raes, D. and Smith, M. (1998): Crop Evapotranspiration: Guidelines for Computing Crop Water Requirements. *FAO Irrigation and Drainage Paper*, 56.
[^hock03]: Hock, R. (2003): Temperature index melt modelling in mountain areas. *J. Hydrol.*, 282, 104–115.
