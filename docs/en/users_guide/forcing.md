# Rainfall and Meteorology (&list_precip / intercept / meteo / evap / snow)

> English mirror of docs/users_guide/forcing.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

This chapter covers the five features that drive the hydrologic
computation. Each can be enabled independently; combined, they act in
the following sequence.

```
Precipitation (fn_precip)
  -> reduced by canopy interception (fn_intercept)
  -> rain/snow partitioning by air temperature (fn_snow; temperature from fn_meteo)
      snow is stored as snowpack and released to the surface by snowmelt
  -> surface water
Surface water is lost to evapotranspiration (fn_evap)
```

The roles are split as follows: **precipitation (fn_precip) is the mass
input to the water budget**, while **the meteorological forcing field
(fn_meteo) provides background fields such as air temperature**. A
rain-only run does not need fn_meteo.

## Putting all meteorological input in one file (recommended layout)

Each fn_\* may point to the same file name, so the meteorological
inputs can be kept in a single file.

```
&list_sysparam
  ...
  fn_precip = "forcing.txt"
  fn_meteo  = "forcing.txt"
  fn_snow   = "forcing.txt"
/
```

```
! ---- forcing.txt ----
&list_precip
  prtype = 1
  prval(:,1) = 0, 10        ! (time (min), rainfall intensity (mm/h))
  prval(:,2) = 1440, 10
/
&list_meteo
  temp0 = 2.0               ! uniform air temperature (deg C)
/
&list_snow
  snow_ddf = 3.0            ! degree-day factor (mm/degC/day)
/
```

## Precipitation (&list_precip)

Select how rainfall is given with `prtype`.

| prtype | How rainfall is given | Parameters used |
|---|---|---|
| 0 (default) | No precipitation (temporarily disabled) | - |
| 1 | Uniform time series | prval |
| 2 | Fixed distribution x time-series multiplier | fn_prmap, prval (multiplier) |
| 3 | Series of distribution files (e.g. radar rainfall) | fn_maplist, dt_maplist |

| Parameter | Default | Meaning |
|---|---|---|
| prval | - | Time-series pairs `(time (min), value)`. The value is rainfall intensity (mm/h) for prtype=1 and a multiplier for prtype=2. After the last time, the last value persists |
| dt_prupdate | 1 | Rainfall update interval (min) (prtype=1, 2) |
| fn_prmap | "" | Precipitation distribution file (prtype=2) |
| fn_maplist | "" | List of distribution file names (one file per line; prtype=3). **Paths inside the list are also relative to dir_data** (not relative to the list file) |
| dt_maplist(_c) | 60 | Time interval of the distribution files (min) (prtype=3) |
| dt_mapunit(_c) | 0 | Specifies over how many minutes the values in the distribution files are accumulated rainfall (mm). With 0 (default), prtype=2 assumes one day (= mm/day) and prtype=3 assumes the file interval (accumulated mm between dt_maplist frames; with a 1-hour interval this equals mm/h) |
| runoff_rate | 1.0 | Runoff coefficient multiplied onto precipitation (a shortcut to subtract infiltration in coarse runoff analyses; keep 1.0 when the groundwater computation is used) |

```
&list_precip                ! example: uniform 15 mm/h from minute 10 for 24 hours
  prtype = 1
  prval(:,1) =    0,  0
  prval(:,2) =   10, 15
  prval(:,3) = 1440, 15
  prval(:,4) = 1450,  0
/
```

Worked examples of the format for all four types are in
[examples/List_samples/list_precip.txt](../../../examples/List_samples/en/list_precip.txt).
The rainfall intensity distribution can be output as `Pr0001` with
`f_out_pre = 1`.

## Rainfall interception (&list_intercept)

Gives rainfall losses due to the canopy etc. as a reduction before the
rain reaches the ground surface.

| Parameter | Default | Meaning |
|---|---|---|
| f_icmodel | 0 | 0: none (temporarily disabled), 1: fixed interception ratio, 2: initial loss (storage type) |

Model-specific settings go in dedicated groups within the same file.

**Fixed interception ratio (f_icmodel = 1, &list_intercept_fixed)** -
intercepts a constant fraction alpha of rainfall and delivers the
effective rainfall (1-alpha)P to the surface. Use `ic_alpha` (uniform
value; default 0.15) or `fn_icalpha` (distribution; ic_alpha is ignored
when given).

**Initial loss (f_icmodel = 2, &list_intercept_initloss)** - stores
the first part of the rainfall up to a maximum storage, then passes
everything through once the storage is full. Use `ic_smax_mm` (uniform
value, mm; default 1.5) or `fn_icsmax` (distribution).

When the uniform value is unspecified the default is adopted and
printed with "(default)" (the minimal input is f_icmodel and an empty
model group; rationale in developer.md §66). Guide values by
vegetation (review of Crockford & Richardson 2000; calibration
quantities):

| Type | ic_alpha (interception ratio) | ic_smax_mm (canopy storage, mm) |
|---|---|---|
| Dense conifer forest | 0.25-0.4 | 1.5-3 |
| Broadleaf / mixed forest (default) | 0.1-0.2 | 0.8-1.5 |
| Leafless deciduous forest | 0.05-0.1 | 0.3-0.8 |
| Grassland / cropland | 0.05-0.1 | 0.3-0.5 |
| Urban (initial loss as depression storage) | - | 1-2.5 (depression storage of impervious surfaces; SWMM convention) |

## Meteorological forcing field (&list_meteo)

Manages air temperature in one place and provides it to
evapotranspiration, snowmelt, water quality, and so on. The input is
**exactly one of three forms**.

| Parameter | Default | Meaning |
|---|---|---|
| temp0 | - | Uniform constant (deg C) |
| tempval | - | Uniform time series `(elapsed days, deg C)`. Times are elapsed **days** from t=0 |
| fn_tempmap | "" | List of temperature distribution files (one file per line, applied sequentially at dt_tempmap_c intervals; the last frame persists) |
| dt_tempmap_c | "1 day" | Time interval of the distribution files |
| f_temp_lapse | 0 | 1: enable the temperature lapse rate with elevation (uniform inputs only) |
| temp_lapse | 0.65 | Lapse rate (degC/100 m) |
| temp_zref | lowest elevation in the domain | Reference elevation (m). T(z) = T - lapse rate x (z - temp_zref) |

With the temperature lapse rate, even a uniform temperature input
gives mountain temperatures that decrease with elevation, and in the
snowmelt computation **a snow line emerges automatically**.

Two further options target long-term runs
([glaciers](glacier.md), long-term landform change).

| Parameter | Default | Meaning |
|---|---|---|
| tempofs | - | Long-period air temperature offset series `(elapsed days, dT degC)`, added to the temperature input (uniform and distributed alike). It is interpolated on the real time axis, which is not folded by the cyclic forcing t_cycle, so **a cooling/warming trend or a glacial cycle can be superimposed on a repeated representative year** |
| f_prec_lapse | 0 | 1: enable the precipitation gradient with elevation. Precipitation is multiplied by max(0, 1 + rate x (z - prec_zref)) (a simple representation of orographic precipitation and the elevation dependence of glacier accumulation; prefer distributed precipitation input when available) |
| prec_lapse | 0.0 | Precipitation increase rate (%/100 m) |
| prec_zref | lowest elevation in the domain | Reference elevation of the precipitation gradient (m) |

## Evapotranspiration (&list_evap)

Select how potential evapotranspiration (PET) is given with `f_evmodel`.

| f_evmodel | Method | Requirements |
|---|---|---|
| 0 (default) | None (temporarily disabled) | - |
| 1 | Constant rate evap0 (mm/day) | - |
| 2 | Monthly climatology evap_monthly (mm/day x 12) | Calendar (date0_c) |
| 3 | Hamon formula (estimated from temperature and daylight hours) | Calendar, temperature (fn_meteo), latitude lat |
| 4 | Thornthwaite formula | As 3, plus monthly normal temperatures temp_normal (x 12) |

| Parameter | Default | Meaning |
|---|---|---|
| evap0 | 3.0 | Mode 1: PET (mm/day). When unspecified the default is adopted and printed with "(default)" |
| evap_monthly | - | Mode 2: monthly PET (mm/day). 12 months |
| evap_kc | 1.0 | Conversion coefficient (pan coefficient / calibration; common to all modes) |
| lat | - | Representative latitude (deg). Required for modes 3, 4 |
| temp_normal | - | Monthly normal mean temperatures (deg C). Required for mode 4 |

Evapotranspiration is subtracted from surface water (supply-limited),
and the totals are output to `evap.csv` in the result directory. A
configuration missing its requirements (e.g. mode 2 without a
calendar) stops at initialization with a message stating what is
missing. The mode-1 default of 3 mm/day is the lower side of the
warm-season reference evapotranspiration of a humid temperate climate
(FAO-56 ET0 of 3-5 mm/day): larger than the annual mean of Japan
(2-2.5 mm/day) and smaller than summer (4-5). Use modes 2-4 for runs
spanning seasons (monthly values, latitude and normal temperatures are
given data and have no default).

## Snowpack and snowmelt (&list_snow)

Degree-day snowpack and snowmelt. **Air temperature (fn_meteo) is
required.**

| Parameter | Default | Meaning |
|---|---|---|
| f_snow | 1 | 0 temporarily disables while keeping the file |
| snow_t_snow | 0.0 | Temperature threshold below which all precipitation is snow (deg C) |
| snow_t_rain | 2.0 | Temperature threshold above which all precipitation is rain (deg C). In between, rain and snow mix linearly |
| snow_t_melt | 0.0 | Temperature threshold for snowmelt (deg C) |
| snow_ddf | 4.0 | Degree-day factor (mm/degC/day). When unspecified the default is adopted and printed with "(default)" (rationale in developer.md §65) |
| snow_swe0 / fn_snow_swe0 | - / "" | Initial snow water equivalent (mm) (uniform value / distribution; mutually exclusive; omit both to start without snow) |

Snowfall is stored as snow water equivalent (SWE) and melts into
surface water by the degree-days above snow_t_melt. Combined with the
temperature lapse rate (&list_meteo), snowpack and snowmelt are
represented per elevation band.

The minimal input to "just try it" is **an empty &list_snow in
fn_snow** (plus the air temperature of fn_meteo). Guide values of the
degree-day factor (compilation of Hock 2003; a calibration quantity):

| Type | snow_ddf (mm/degC/day) | Notes |
|---|---|---|
| Forest (under a conifer canopy) | 2-3 | Small because radiation is shaded |
| Open land / sparse forest (default) | 3.5-5 | The observed range of snowmelt floods in Japanese mountain basins |
| Late melt season, open high elevation | 5-7 | Larger with dirty snow and stronger radiation (no seasonal variation is implemented, so give a period average) |
| Snow on a glacier | 3-5 | The ice surface uses gl_ddfi ([Glaciers](glacier.md)) |

## Summary of combination requirements

| Feature | Other features required |
|---|---|
| Precipitation | None (works on its own) |
| Interception | Precipitation |
| Meteorological forcing field | None (used together with a consuming feature) |
| Evapotranspiration (mode 1) | None |
| Evapotranspiration (modes 2-4) | Calendar date0_c (3, 4 also need the meteorological forcing field and latitude) |
| Snowpack / snowmelt | Precipitation + meteorological forcing field |
| Glaciers ([dedicated chapter](glacier.md)) | Precipitation + meteorological forcing field + snowpack/snowmelt |

For worked examples of the settings, see list_precip / list_intercept /
list_meteo / list_evap / list_snow in
[examples/List_samples/](../../../examples/List_samples/en/).
