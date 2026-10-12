# Prescribed bed motion explained (supplement to the prescribed bed motion chapter)

> English mirror of docs/users_guide/bedmotion_models.md. The Japanese file is the master copy.

[Back to the prescribed bed motion chapter](bedmotion.md) | [Back to the user's guide index](../users_guide.md)

This page gives the formulation behind the [prescribed bed motion
chapter](bedmotion.md): the time interpolation of the displacement and the
update of the bed elevation, the fault displacement field and the initial
sea surface, the treatment of short waves in hydrostatic and
non-hydrostatic runs, the behaviour contract (restart, MPI) and the
verification cases. The implementation is in `src/m_bedmotion.f90` and
`utils/fault2disp`; the design history is in docs/bedmotion_plan.md and
developer.md §70 (in Japanese).

## 1. Time interpolation of the displacement and update of the bed

```math
d(t) = d_k + \frac{t - t_k}{t_{k+1} - t_k}\left(d_{k+1} - d_k\right)\ (\texttt{f\_bminterp} = 1),
\qquad
z^{\,n+1} = z^{\,n} + \left[d(t_{n+1}) - d_{prev}\right],
\quad h\ \text{unchanged},\quad e = z + h
```

- At the head of each step the displacement at the end-of-step time is
  interpolated and the **difference** from the previously applied
  displacement is added to z. With linear interpolation the bed velocity is
  constant between snapshots and jumps at their boundaries.
- The step interpolation (f_bminterp = 0) switches to the next snapshot only
  when the evaluation time **exceeds** its time; at exact equality the
  previous value is kept (the advance condition in `m_bedmotion_calc`). The
  step line in panel (a) of the chapter's figure illustrates the
  interpolation mode; it does not specify which side is used at an exact
  switch time.
- Because the displacement is applied as an increment, it does not conflict
  with sediment/landform change, the moving bed layer or lava flow moving z
  in the same run (each module adds only its own increment).

## 2. Fault displacement field and initial sea surface

utils/fault2disp computes the surface displacement from the fault
position, strike, dip, rake, length, width and slip with the analytical
solution of an elastic half-space (Okada's formulas[^okada85]) and turns it
into a time history with the rupture start time and rise time. On a steep
sea floor the initial sea-surface displacement is taken as the vertical
displacement plus the product of the horizontal displacement and the bed
slope,

```math
\eta_0 = u_z + u_h\cdot\nabla z
```

which matters there[^tanioka96]; fault2disp computes it when a bed elevation
is given.

The difference from the instantaneous input that omits the rupture process
(pattern C of the chapter) appears in the near-field arrival time and wave
height: 2–3 % in the maximum level of
[examples/tsunami_fault](../../../examples/tsunami_fault/) and +24 to 40 % at
the bay mouth and shelf of
[examples/tsunami_coast](../../../examples/tsunami_coast/) (see the READMEs).

## 3. Hydrostatic and non-hydrostatic

In a hydrostatic run the bed uplift maps directly onto the surface. This is
sufficient for subduction-zone earthquakes whose source width is much
larger than the depth. For short deformation whose width is comparable to
the depth (splay faults, narrow deep-sea slip, submarine slides) the
inertia of the water column attenuates the short waves (the Kajiura filter
$`1/\cosh kH`$[^kajiura63]). The [non-hydrostatic correction](nonhydrostatic.md)
§7 with f_nonhydrostatic=1 and f_nh_bottom=1 provides it in the one-layer
approximation $`1/(1 + \beta k^2)^2`$ (developer.md §69.10). The velocity
jumps then enter as acceleration pulses, so write the snapshots densely
(increase nout of fault2disp; [test/nhbottom](../../../test/nhbottom/) writes
one per step). In [examples/tsunami_fault](../../../examples/tsunami_fault/)
the non-hydrostatic run lowers the coastal maximum level by 24 %
(dispersion), and the acceleration term contributes a further −2 %.

## 4. Behaviour contract (restart, MPI, API)

- The increment is added to z of eligible cells (x > 0, sw = 0); h is kept
  and e = z + h is recovered. Momentum is untouched. The soil depth sd is
  unchanged (the bedrock surface z − sd moves). Sea-mask cells (sw > 0) have
  their level prescribed and do not move even if a displacement is given.
- Restart: no private displacement history is saved. Mode 1 with a saved
  step `it0 > 0` reconstructs the displacement at the restart time from the
  same table as already applied. With the step interpolation, however, the
  initialization selects snapshots with an equality-inclusive condition,
  unlike normal advancement, so exact agreement is not guaranteed when
  saving and restarting exactly at a switch time. Mode 2 starts the history
  at zero; supply a series that does not reapply deformation already in
  the saved terrain ([Suspend and Restart](restart.md)).
- ENC only: initialization stops if bedmotion is enabled with STG. The
  library API set_value('z') is refused while fn_bedmotion is active (z has
  a single producer).
- MPI: every rank reads the whole displacement file and cuts out its own
  band (the file read is redundant, the application is per band). Even with
  windowed files the retained displacement arrays and the time
  interpolation cover the whole band of each rank. See
  [Parallel Execution](parallel.md) for the reproducibility conditions.

## 5. Verification cases

- [test/nhbottom](../../../test/nhbottom/) configuration 3: a Hammack-type uplift of 0.2 m in 1 s over
|x − x_c| < 20 m in a 10 m deep channel, given as a snapshot table with
one entry per step, matches the driver that applies the same motion
through the library API (identical except the last digit of the
full-precision volume column of the Log). Restart (save → restore at
0.5 s) matches the uninterrupted run (hydrostatic; with the non-hydrostatic
f_nh_bottom it differs by one step of the acceleration term), and coexisting
with a submarine slide (f_bedslide) Σ(z − z0) = Σ d holds within output
precision (the internal transfer of the bed layer sums to zero).
- [examples/tsunami_fault](../../../examples/tsunami_fault/README.md): comparison of hydrostatic / instantaneous / non-hydrostatic + acceleration term.
- [examples/tsunami_coast](../../../examples/tsunami_coast/README.md): the time lag between coastal subsidence/uplift and the offshore tsunami.

## References

[^okada85]: Okada, Y. (1985): Surface deformation due to shear and tensile faults in a half-space. *Bull. Seismol. Soc. Am.*, 75, 1135–1154.
[^tanioka96]: Tanioka, Y. and Satake, K. (1996): Tsunami generation by horizontal displacement of ocean bottom. *Geophys. Res. Lett.*, 23, 861–864.
[^kajiura63]: Kajiura, K. (1963): The leading wave of a tsunami. *Bull. Earthq. Res. Inst. Univ. Tokyo*, 41, 535–571.
