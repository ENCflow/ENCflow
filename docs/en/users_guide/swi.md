# Soil Water Index (fn_swi)

> English mirror of docs/users_guide/swi.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Computes the **Soil Water Index** (SWI) — the operational indicator
used for sediment-disaster (landslide/debris-flow) early warning in
Japan — for every cell. It implements the serial three-tank model of
Ishihara and Kobatake (1979) with the **nationally uniform standard
constants used by the Japan Meteorological Agency, unchanged** (they
cannot be modified). Rain fills the tanks and drains through lateral
outlets and bottom percolation; the index (mm) is a measure of
antecedent soil moisture, and its value is what gets compared with
warning criteria (CL lines).

## Enabling and settings

Specify `fn_swi` in `&list_sysparam`. There is almost nothing to
configure (the tank constants are fixed to preserve the official
definition):

```
&list_swi
  f_swi = 1                 ! 0 to disable temporarily
  swi0 = 0.0, 0.0, 0.0      ! initial tank storages (mm) (antecedent rain)
/
```

## Contract (dedicated runs)

To keep the index faithful to its official definition (input = ground
rainfall itself), **SWI is computed in a dedicated run**:

- The only module that may be combined is **fixed-rate interception**
  (f_icmodel=1 in &list_intercept). Enabling any other process module
  (groundwater, evapotranspiration, snow, glacier, landform change,
  water quality, ...) stops the run — they would rewrite the rainfall
  or invite confusion between the index and physical states.
- `dt` must be **600 s or less** (the JMA computation interval of
  10 minutes); larger values stop the run.
- Any grid is valid (the index does not depend on cell area), but if
  `dx,dy` is not 1 km a warning notes that the conditions differ from
  the official 1-km product. Feeding 1-km analyzed rainfall to a 1-km
  grid reproduces the official setting.

To compare with physical model states (e.g., groundwater saturation),
run a separate case with the same rainfall.

## Output

Written automatically when enabled (no switches):

| File | Contents |
|---|---|
| Swi0001... | Soil Water Index (mm) distribution (every dt_file) |
| Swi9999 | **period maximum of SWI** (the statistic used for warning; hazard map) |
| Swit9999 | time of the maximum (min) |

On suspend/restart the tank states are saved to `swi.dat`, so the
index continues exactly even when a long rainfall event is split
across runs.

## Notes

- The rainfall time series table (prtype=1) is **linearly
  interpolated**. To give a rectangular rainfall pulse, repeat the end
  point (e.g., `(0,30),(180,30),(181,0)`).
- References: Ishihara and Kobatake (1979); Okada et al. (2001,
  Sokkō-Jihō 68); the JMA explanation of the Soil Water Index. See
  developer.md §49 for the implementation record.
