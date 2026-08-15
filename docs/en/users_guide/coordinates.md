# Coordinate System Management

> English mirror of docs/users_guide/coordinates.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

The ENCflow grid is a uniformly spaced planar orthogonal raster, and
the handling of coordinate systems is deliberately limited to
**projected coordinate system scale** (coordinate transformation and
reprojection are the job of the GIS side). If you tell the model the
coordinate system, outputs are georeferenced and open directly in a
GIS. You can also compute without one (which is sufficient for
idealized experiments).

## Cell numbering convention -- 1-based

Cell numbers (i, j) used to specify locations of measurement points,
structures, boundaries, and so on are **1-based everywhere**
(following the Fortran array-index culture). i is 1 at the westernmost
column and increases eastward, 1..nx; j is 1 at the northernmost row
and increases southward, 1..ny (the same direction as the raster row
order, north to south; see [the input/output chapter](io.md)).

**Rasters in QGIS and other GIS software count rows and columns from
0**, so when you pick a cell position in a GIS and specify it to
ENCflow, **add +1 to both the row and the column**. An off-by-one-cell
mistake is hard to notice with specifications that only take effect
on exactly that cell, such as channel cells or levee cells.

## Specifying locations in real coordinates

Locations of measurements (probes and flux transects) can also be
specified in real coordinates instead of cell numbers. **x is
positive eastward and y is positive northward** (the same convention
as projected coordinate systems), and the interpretation of the
coordinates switches automatically.

- **When georeferencing is available** (the coordinate range of the
  grid is known from bil+hdr / GeoTIFF input) -- interpreted as
  **absolute coordinates in the projected coordinate system**. You can
  write coordinates read off in QGIS as they are.
- **When georeferencing is not available** (text input, idealized
  experiments, convenience use of geographic (lat/lon) data) --
  interpreted as **local coordinates (m) with the domain's southwest
  corner at (0, 0)**.

Which interpretation was used, and the resolved cell number, are
displayed at initialization like
`probe 1: absolute coordinates -> cell (150,150)`; always check this
(a mix-up almost always stops with an out-of-range error). A
coordinate that lands exactly on a cell boundary can resolve to
either side depending on rounding, so use coordinates that point to
the interior of a cell.

## How to specify the coordinate system

There are two methods, and they can be combined.

**1. Specifying an EPSG code** -- written in `&list_geoinfo`.

```
&list_geoinfo
  epsg = 6677               ! e.g. JGD2011 Japan Plane Rectangular CS zone IX
  ...
```

**2. Accompanying ESRI header (.hdr)** -- if a `dem.hdr` exists in the
same place as a bil-format input file (e.g. `dem.bil`), it is read
automatically, and `nx, ny, dx, dy` and the origin coordinates are
filled in. The hdr files that GDAL / QGIS / ArcGIS create when writing
bil can be used as they are.

- Values that can be filled in from the hdr no longer need to be
  written in the namelist. **If both are specified and contradict each
  other, the run stops** (neither is silently preferred).
- Examples of coordinate systems verified to work: EPSG:2451 (JGD2000
  Plane Rectangular zone IX), 6677 (JGD2011 Plane Rectangular zone
  IX), 6668 (JGD2011 geographic (lat/lon)), 4326 (WGS84 geographic
  (lat/lon)).

## Using a geographic (lat/lon) grid (data in degrees)

Geographic (lat/lon) grids such as the Japanese National Land
Numerical Information can also be input as they are, but the model
does not convert grid spacing from degrees to meters:

- **Explicit specification of `dx, dy` (in meters) is mandatory**
  (unspecified stops the run).
- The specified values are checked against approximate values derived
  from the degree spacing in the hdr; a specification that differs
  greatly stops the run, while a customary approximation (e.g.
  specifying 100 m for a grid whose true size is 100.2 m) is accepted
  and both values are displayed.
- For a geographic (lat/lon) grid with no CRS specified, WGS84 is
  assumed (with a message; an explicit `epsg` takes precedence). For
  projected coordinates no assumption is made: if `epsg` is not
  specified, no CRS is attached to outputs.

## Georeferencing of outputs

- Text and bil outputs are accompanied by a GDAL-compatible `.hdr`,
  and GeoTIFF outputs have the CRS (GeoKey) embedded. They have been
  verified to display at the correct location as-is in QGIS / ArcGIS.
- If GeoTIFF output (bit 4 of `f_output_mode`) is requested in a
  computation where coordinates are not managed, the run stops at
  initialization (to avoid creating GeoTIFFs without location
  information). Text and bil outputs can be used without coordinates.

For the input/output formats themselves (choosing text / bil /
GeoTIFF), see [the input/output chapter](io.md).
