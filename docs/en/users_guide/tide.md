# Tide Level and Sea Surface (&list_tide)

> English mirror of docs/users_guide/tide.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Gives a time series of tide level (sea surface elevation) to sea
cells, to compute coastal flooding by storm surge or rising tide, and
drainage toward low tide. Enable it with `fn_tide`.

**Prerequisite**: the sea area must be specified by the sea mask
`fn_sw` of the geographic information
([the geographic information chapter](geoinfo.md)). The tide level is
forced on the sea cells as a water level, and the flow in the sea
cells themselves is not solved (the sea behaves as a "huge boundary
that prescribes the water level", while flooding and drainage on the
land side are solved by the ordinary shallow-water computation).

```
&list_tide
  titype = 2                     ! uniform time series
  hsea0 = 1.0                    ! apparent water column thickness of sea cells (m)
  tival(1:2,1) = 0,    0.0       ! (time (min), tide level (m))
  tival(1:2,2) = 180,  0.8
  tival(1:2,3) = 360,  0.0
  tival(1:2,4) = 540, -0.8
/
```

## How the tide level is given (titype)

| titype | How it is given | Parameters used |
|---|---|---|
| 1 | Uniform fixed value | ti0 |
| 2 | Uniform time series (linear interpolation) | tival |
| 3 | One distribution x multiplier time series | fn_timap, tival (multiplier) |
| 4 | List of distribution files (linear interpolation between adjacent frames) | fn_timaplist, dt_timaplist |

| Parameter | Default | Meaning |
|---|---|---|
| ti0 | - | titype=1: uniform fixed tide level (m; same elevation datum as z) |
| tival | - | titype=2, 3: time series `(time (min), tide level (m) or multiplier)` |
| fn_timap | "" | titype=3: tide level distribution file (m) |
| fn_timaplist / dt_timaplist(_c) | "" / 60 | titype=4: list of distribution files and their time interval (min). Frame i is at time (i-1) x interval; outside the range the end values persist |
| dt_tiupdate | 1 | Tide level update interval (min) |
| hsea0 | - | Apparent water column thickness of sea cells (m) (see below) |

## hsea0 - apparent water column thickness of sea cells

In flooding where the sea is the supplying side (storm surge, rising
tide), this water column of the sea cells provides the dry test, the
depth at cell interfaces, and the friction. **Several tens of times
the threshold depth dd or more** is recommended (too small a value
makes the sea-to-land flooding discharge too small; a value at or
below dd is an error). Typically start around 1 m, and if the
sensitivity of the flooding discharge to hsea0 is a concern, vary the
value and check.

## Usage patterns

- **Flooding by storm surge / rising tide**: raise the tide level with
  a titype=2 time series. Combined with seawalls
  ([the geographic information chapter](geoinfo.md)), protection
  before overtopping and breach is represented.
- **Drainage toward low tide**: lower the tide level, and ponded water
  on the land side drains to the sea.
- **Steady operation at a warning tide level**: a fixed value with
  titype=1.
- **Tsunami (incidence from the boundary)**: not the tide feature -
  the basic setup is the long-wave radiation edge boundary (type 2)
  combined with water-level-prescribed cells and an initial water
  level ([the boundary conditions chapter](boundary.md)). When the
  domain contains a sea area, use fn_sw and fn_seaside for the sea
  surface initialization and the seaside test of breakwaters.

## Constraints and notes

- ENC grid system only (not available in the legacy STG).
- Sea-mask cells do not solve the flow, and **none of the
  landform-change (sediment) processes act on sea cells**. To handle
  tsunami / storm-surge resuspension and deposition of bottom mud or
  sand, represent the water body as ordinary cells + an initial water
  level (see the suspended-sediment section of
  [Sediment and landform change](geomorph.md)).
- The tide update phase is based on the absolute step number, so after
  a [restart](restart.md) updates occur at the same timing as an
  uninterrupted run (a restart round trip with tide enabled is also
  bit-identical).
- Working example: [test/tide](../../../test/tide/) (drainage -> rising-tide
  flooding). Worked examples of the format:
  [examples/List_samples/list_tide.txt](../../../examples/List_samples/en/list_tide.txt).
