# qanat — an idealised qanat (karez / foggara) case

> English mirror of examples/qanat/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The conduit continuum layer (`f_gwconduit=1`) plus the layer-2 aquifer
(`f_gwlayer2=1`) represent the collection, conveyance and outlet discharge of
an underground gallery. No code changes (settings of existing features only).
See the header of param.txt for the design background.

## Running

```
python3 gen_data.py          # generates data_qanat/
../../bin/encflow param.txt  # about 8 s (an 8-hour simulation)
python3 plot_qanat.py        # generates qanat_result.png
```

## Verified results (2026-08-23)

- S_total = 1.44202380952386 m constant over the whole period (rounding 2e-14;
  mass conservation in the closed domain)
- Outlet discharge Q(8h) = 6.8 L/s (within the typical 1–100 L/s of real qanats).
  The discharge rises from t≈2.6 h, after the gallery has become pressurized (pipe-full)
- In the collection reach the layer-2 water table drops toward the gallery head
  (cone of depression); in the conveyance reach (3 cells) there is leakage loss
  from the gallery to layer 2

## Variants (feature checks for §46.5 (2)(3); added 2026-08-23)

- **param_lined.txt**: the conveyance reach (i≥32) is lined with fn_gwc_leak=0.
  Final discharge 1.28→2.29 mm (1.8×) — the effect of cutting off the conveyance losses
- **param_open.txt**: the outlet becomes a land-side open outfall with fn_gwc_outfall
  (previously only pressurized outflow from the shaft). Discharge starts at
  0.02 h instead of 2.65 h (no waiting for the gallery to fill), quasi-steady
  6.8→7.9 L/s. For the physics of a qanat this is the correct one

## Entry points for sensitivity experiments

- `gw2_ksh_mmh`: recharge capacity of the aquifer. If it is small (360), the
  water-table drawdown stops the collection and there is no discharge (confirmed
  in the first trial of this case)
- `gwc_leak_mmh`: exchange capacity between the gallery and the aquifer = upper
  limit of the collection (a constant rate)
- Length of the conveyance reach: set by the cliff position and the gallery
  gradient in gen_data.py. On a uniform slope (no cliff) the leakage in the
  conveyance reach balances the collection and no water reaches the outlet
- `gwc_cnd` (conveyance) and `gwc_slot_sy`: conveyance inside the gallery and
  the pressure response. They affect the dt limit (dtcheck shows it at initialization)
