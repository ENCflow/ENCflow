> English mirror of docs/developer.md, §0 (project policy) only. The Japanese file is
> the master copy. The remaining sections (§1 onward: design records, conventions and
> bug records) are developer documentation and are kept in Japanese only
> (developer.md §34.2); the section numbers cited below refer to that file.

## 0. Project policy (established 2026-08-10)

Every design decision is made against this policy. A proposal that conflicts with it
must first open a discussion to revise the policy (do not quietly create an
exception). For the positioning relative to other models see docs/comparison.md.

(Added 2026-08-26) The purpose of development that this set of policies supports is
stated explicitly here. ENCflow does not compete on accuracy with the specialised
models of each field. It aims at the following three things.

1. **A unified representation**: to represent the whole world of phenomena involving
   water on the land surface as one integrated process-chain model (a rough estimate
   is acceptable). The value lies not in the detailed reproduction of individual
   processes but in the chain of processes (rainfall → snowmelt → runoff → erosion →
   inundation …) being connected within one grid and one time evolution
   (policies 1, 2, 4, 5).
2. **A laboratory**: to be a laboratory in which whatever one is curious about can be
   tried at once. "What happens under this condition", "how does it change when this
   process is added" can be run just by adding or changing configuration files, even
   on a laptop (policies 6, 7, 9, 11).
3. **Lowering the barrier to entry**: to lower the barrier for a researcher to
   "compute once, as a first try" a phenomenon adjacent to their speciality. Keeping
   the same grid, the same input system and the same way of running, adjacent
   processes are added one at a time, the size of their effect is estimated with a
   concise model, and only once they are found to matter does one move on to a
   specialised model where necessary. ENCflow supports that first step (policies 1,
   4, 6, 7). What is lowered, however, is the barrier to "trying", not the barrier of
   expertise: interpreting the results requires knowledge of the field concerned (the
   wording of user documentation must also keep to this line).

"Why is each process not elaborated to the highest accuracy" (policies 4 and 5)
follows from all three of these purposes.

1. **Aim to solve seamlessly every phenomenon related to the flow of water on the
   land surface.**
2. **Build every model raster-based on an orthogonal grid.** Vector-based models are
   not brought in (where needed, they are handled by external coupling).
   (Implementation examples: channels are a sub-grid raster (rw + width + σ cross
   section), structures are specified as groups of cells, and gauging lines are DDA
   staircase faces. None of them carries a vector representation.)
3. **The target scale extends as far as can be solved in a projected coordinate
   system.** The continental scale is out of scope.
4. **The framework is plane two-dimensional, and its purpose is to estimate several
   processes simultaneously and roughly.** Detailed reproduction of physical
   processes is not the purpose.
   (Note: "roughly" refers to the level of abstraction of the physics; numerical
   rigour (ULP=0 verification, bit reproducibility, mass conservation) is not
   relaxed. The disciplines of §7 and §11 are compatible with this policy.)
5. **Horizontal processes are implemented at most up to the full shallow water
   equations plus a one-equation diffusion model. Vertical processes are abstracted
   and conceptualised, and implemented simply** (examples: the Green–Ampt piston,
   priority subtraction for evapotranspiration, the bucket coupling of the two-layer
   groundwater).
   (Exception agreed 2026-10-05: only for research uses in which dispersion is
   essential (soliton fission of tsunamis running up rivers, near-field wave
   generation by landslide tsunamis), a non-hydrostatic correction with one cell
   scalar (one layer; the vertical structure is abstracted to β = h²/4) may be
   superposed on the SWE. The default is the SWE; the conditions are zero additional
   memory, CPU and communication when not enabled, and bit-identical results with
   the existing references when disabled. The authoritative design is
   docs/nonhydrostatic_plan.md and the record of the decision is §69.)
   (Exception agreed 2026-10-26: only for uses in which the response of vertical
   unsaturated infiltration itself is the object of study (the VZ runoff model of
   Tani (2023)), the one-dimensional Richards equation may be solved on a small
   number of **shared reference columns**. Conditions: (1) no vertical grid is held
   per cell (the vertical state is number of columns × number of layers; the cell
   side holds only the zone number and the read-out weights of the soil depth),
   (2) lateral subsurface flow is not solved, and the drainage of a zone is moved to
   explicitly specified outlets (the horizontal upper limit is unchanged), (3) zero
   additional memory, CPU and communication when fn_vz is not specified, and
   bit-identical results with the existing references when disabled. The
   authoritative design is docs/vz_plan.md and the record of the decision is §87.)
   (Exception agreed 2026-10-27: only for uses in which coastal morphological change
   driven by waves and the interaction between waves and currents are the object of
   study, short-period waves may be solved on the same grid as the SWE as a
   phase-averaged **action balance with one representative frequency and
   directional bins**. Conditions: (1) the phase is not resolved (phase-resolving
   short waves are out of scope; the dispersion of long waves is the task of the
   non-hydrostatic correction), (2) there is no frequency dimension (one
   representative frequency; the state per cell is at most N_θ directional values
   plus one roller energy), (3) no wind growth and no nonlinear wave–wave
   interactions (offshore waves are given at the boundary), (4) the effects on the
   flow are limited to three paths — a body force (radiation stress), mass transport
   (Stokes) and bottom friction — and the effects on sediment to two paths, stirring
   and the transport velocity, (5) zero additional memory, CPU and communication when
   fn_wavefield is not specified, and bit-identical results with the existing
   references when disabled. The authoritative design is docs/wavefield_plan.md and
   the record of the decision is §88.)
6. **Do not over-complicate the model; refine it gradually to match the information
   available.** It must run, for a start, with a simple specification of parameters.
7. **Unneeded processes are "not enabled" by not creating or specifying their
   configuration file** (rather than being "disabled"). The presence or absence of
   fn_* is authoritative; a flag inside a file (f_*=0) is a convenience for temporary
   deactivation.
8. **A model that is not enabled wastes as little memory and CPU as possible**
   (arrays not allocated, no calls, no halo exchange; verified by "bit-identical when
   disabled").
9. **A single source code covers everything from a laptop for learning to large
   computations on a supercomputer** (the single-source scheme MODE=serial|mpi of
   §2; cross-compilation for NEC vector machines and the like via make.inc).
10. **The program (the computational core) consists of Fortran only, all source code
    is published, and no external library is used**, which secures absolute
    portability.
    (Refinement: the only permitted dependencies are the language standard
    (iso_fortran_env etc.) and the standard parallel specifications (OpenMP and MPI).
    Compression (RLE, inflate) and GeoTIFF input/output are also implemented in
    house (m_geotiff_* is the example). The verification scripts under test/ (shell,
    Python, gnuplot) are outside the computational core and outside this item.)
    (Added 2026-08-28: external coupling adapters (bmi/ etc.) are likewise outside
    the computational core and outside this item. However, the default build of
    src/ (encflow / encflow_mpi / libencflow.a) must not depend on an adapter.
    Bundling a **specification file** for an adapter (one that contains only abstract
    interfaces and constants and no implementation code, e.g. CSDMS bmi.f90) is
    permitted provided its origin and licence are shown in NOTICE. Bundling
    implementation code is not. Agreed in docs/bmi_plan.md §4.)
11. **Keep the formats of input and output data as simple as possible**, and leave
    pre-processing, post-processing and GUIs for creating parameter files to the user
    side (text matrices, namelists and CSV as the basis; binary only to the practical
    minimum of bil/GeoTIFF).
12. **Give the physical quantities used in the computation directly wherever they can
    be given directly.** Generating a derived quantity from other data inside the
    model is limited to cases with a clear reason (example: the sea-to-domain mask of
    f_masktype=2 is generated internally because it uses the knowledge, internal to
    the discretisation, of the "one-cell sea band"). Pre-processing such as
    conversion through code tables belongs in utils or on the GIS side (examples:
    lu2mask §40, the removal of f_rntype=2 §41). (Added 2026-08-15)
13. **Fulfil accountability.** In addition to publishing all source (policy 10), keep
    the state in which users and third parties can trace back and verify "why this
    result". The following three points are part of every piece of work that adds or
    changes a feature (added 2026-10-24).
    - **State the sources**: write, wherever possible, the source of each model,
      governing equation and parameter (including default and recommended values).
      The origin of equations and formulations goes in the relevant § of developer.md
      or in the respective plan document; the sources of the coefficients a user
      chooses go in the relevant chapter of the users guide (its "References"
      section). Simplifications and conceptualisations original to this project
      that do not rest on the literature (the vertical abstraction of policy 5 is
      the typical case) are marked explicitly as "original". Not hiding the absence
      of a source is also part of accountability.
    - **Verify against theoretical solutions**: behaviour for which an analytical
      solution, a conservation law or an exact solution exists is checked for being
      "correct" by an environment-independent verification script that judges
      pass/fail by itself (test/<case>/Check_*.py), separately from regression
      against the reference (which checks that "nothing has changed"). Examples: the
      Stoker solution of dambreak, the Gaussian solutions of diffusion and creep, the
      Manning uniform flow of bendloss, swi, dissol and culvert. The visual
      confirmation at reference updates (§10) complements this and does not replace
      it.
    - **Automate consistency checks**: the agreement between "code and
      documentation", "master copy and translation" and "tests and references" is
      checked mechanically by CI rather than relying on human attention (the
      regression, MPI np=1,2,4, -fcheck=all and BMI conformance of ci.yml /
      nightly.yml; the translation records, links and params_index cross-check of
      i18n.yml). When a new kind of inconsistency actually occurs, do not only fix
      the instance but add a check so that the recurrence is blocked mechanically
      (the scripting of the cross-check in §35.1 is the example). Checks live
      outside the computational core (shell, Python standard library; outside the
      scope of policy 10) and no generation mechanism is built (§35.1).

    Where "wherever possible" draws the line: for sources, analytical solutions and
    checks alike, the rule is not "do not implement because there is none" but "when
    there is none, say so". Retrofitting the existing modules (taking stock of
    chapters without a References section, adding verification scripts to cases that
    have an analytical solution but no script, promoting the benchmark cases to
    analytical-solution tests §10) proceeds step by step as items in docs/handoff.md.
