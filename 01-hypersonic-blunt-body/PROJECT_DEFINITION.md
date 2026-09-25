# Project 01 — Hypersonic Blunt-Body Aerodynamics and Aerothermal Characterization

## Research Area
Hypersonic aerodynamics / aerothermodynamics

## Engineering Problem

Hypersonic vehicles with blunt forebodies (re-entry capsules, blunt leading edges,
interceptor noses) generate a strong detached bow shock. This shock layer governs
surface pressure distribution, drag, and aerodynamic heating. Nose bluntness is a
primary design lever for managing heat flux, but the relationship between nose
radius, shock stand-off distance, drag, and heating is nonlinear and must be
quantified computationally for a given geometry family and flow regime.

## Research Question

How does nose (bluntness) radius influence shock stand-off distance, surface
pressure distribution, and the distribution/peak of surface heat flux on an
axisymmetric hypersonic blunt body at fixed freestream conditions? (Total drag
was originally part of this question; it was dropped from scope on 2026-09-24
after CFD investigation found the base/wake region falls outside this
project's continuum-CFD validity — see DEVELOPMENT_LOG.md and the Limitations
section below.)

## Engineering Objective

Establish a verified, mesh-independent, correlation-validated compressible CFD
methodology in OpenFOAM 11 for hypersonic blunt-body flow — **proven stable from
a cold start via a staged shakedown sequence before any full-resolution
production run is attempted** — then apply it to quantify the nose-radius →
aerothermal-loading trade-off via a single-variable parametric sweep.

## Hypotheses

**Aerothermal (the original research hypotheses, unchanged):**
Increasing nose radius (at fixed cone half-angle and base radius) will:
- increase shock stand-off distance,
- decrease peak stagnation-point heat flux, consistent with Fay–Riddell scaling
  (q̇_stag ∝ R⁻¹ᐟ²),
- increase forebody (pressure) drag due to increased frontal bluntness. (Total
  drag, including the base contribution, is out of scope — see Limitations.)

These trends are hypotheses to be tested against our own CFD results, not assumed
conclusions.

**Methodological (new, added during the project reset):**
The repeated first-timestep `sigFpe` solver crash observed in this project's
prior development is caused by cold-start boundary-condition/initial-condition
stiffness — a uniform freestream field instantaneously meeting a no-slip,
fixed-temperature wall at a micron-scale near-wall cell — rather than by mesh
topology. This is testable directly: a timestep-ramped startup strategy should
allow the solver to survive the initial transient, first demonstrated at reduced
severity (lower Mach number) before being confirmed at the full M=7 condition.

## Physical Regime and Major Modelling Decisions

| Decision | Choice | Justification |
|---|---|---|
| Freestream regime | Mach ≈ 7, perfect gas (γ = 1.4), ~30 km altitude | Genuinely hypersonic (M > 5) while remaining thermally/chemically frozen — tractable without real-gas chemistry, which OpenFOAM 11 does not natively support |
| Geometry | Spherically-blunted cone, axisymmetric | Reusable methodology for Project 10 (aerothermal optimization); still has established correlations for V&V |
| Solver | `rhoCentralFoam` (via `foamRun -solver shockFluid`) | Density-based, shock-capturing — standard OpenFOAM solver for compressible supersonic/hypersonic flow |
| Turbulence | Laminar | Keeps scope honest; laminar stagnation heating is exactly the regime Fay–Riddell was derived for; turbulent/transitional heating is Project 03's scope |
| Dimensionality | 2D-axisymmetric (wedge mesh) | Physically appropriate at zero yaw; research question does not involve angle-of-attack effects |
| Wall thermal BC | Fixed isothermal wall, 300 K | Isolates the aerodynamic effect of bluntness on heating; avoids conflating with wall-temperature feedback (reserved for Project 04, TPS) |
| Time treatment | Transient, adaptive timestep (Courant-limited), run toward a steady shock structure | Blunt-body hypersonic flow reaches a steady shock structure under fixed freestream conditions; transient marching is `rhoCentralFoam`'s native mode |
| Radiation | Not modeled | Documented limitation |
| Ablation | Not modeled — rigid, non-ablating wall | Documented limitation |
| Mesh topology | Explicit structured (transfinite/O-grid) near-body blocks + structured buffer ring + broad unstructured far-field | Prior automatic-BoundaryLayer-field meshing produced an unresolvable axis-region topology defect (documented in the prior repository incarnation); the explicit O-grid approach eliminated that defect entirely, verified via checkMesh, and is retained in this reset |
| Solver startup | Timestep-ramped cold start, validated via a two-stage shakedown sequence before production resolution | Direct evidence (this project's own prior development) shows the adaptive Courant-based timestep controller's own first-step choice can trigger an immediate solver crash despite a clean, verified mesh — addressed as a startup-methodology problem, not a mesh problem |

## Major Design Variable (Parametric Sweep)

- **Primary:** Nose (bluntness) radius, R
- **Held fixed during Project 01 sweep:** cone half-angle (15°), base radius (0.15 m)

## Constraints

- Transient, laminar, calorically perfect gas, no radiation, no ablation, no
  real-gas chemistry, fixed isothermal wall.
- 2D-axisymmetric domain only (no 3D / angle-of-attack cases in this project).

## Required Outputs

1. Shock stand-off distance δ as a function of nose radius R
2. Surface pressure coefficient distribution Cp(s)
3. Surface heat flux distribution q̇(s), with emphasis on stagnation value q̇_stag
4. Validation comparison: q̇_stag(R) vs. Fay–Riddell correlation
5. Verification/validation comparison: δ(R) vs. Billig's empirical correlation

Total drag coefficient Cd(R) was originally listed here; dropped from Required
Outputs on 2026-09-24 (see Limitations).

## Shakedown Sequence (methodology verification, precedes production runs)

1. **Shakedown A — lower-Mach cold-start test.** Same blunt-body geometry and
   near-wall cell sizing as the eventual production mesh (preserves the actual
   startup-stiffness mechanism), at a reduced freestream Mach number (exact value
   TBD — a separate, explicit decision). Goal: demonstrate a timestep-ramp
   startup strategy survives the initial transient at manageable wall-clock cost.
2. **Shakedown B — full M=7, coarse far-field.** Same near-wall resolution as
   Shakedown A/production, coarser far-field mesh purely for faster iteration.
   Goal: confirm the startup strategy validated in Shakedown A also survives the
   real M=7 severity.
3. **Production.** Full-resolution mesh (proven O-grid methodology, rebuilt
   fresh in this repository) with the validated startup strategy, followed by
   the standard verification/validation/parametric-sweep sequence below.

## Verification Strategy

- **Startup-methodology verification (new):** each shakedown stage documented
  with explicit pass/fail evidence — startup parameters tested, survival time,
  residual behavior — before production resolution is attempted.
- Grid convergence study on the production baseline case: ≥3 mesh densities,
  tracking stagnation-point heat flux and shock stand-off distance. Richardson
  extrapolation / GCI reported where practical.
- Global mass conservation check (inflow vs. outflow mass flux).

## Validation Strategy

- Stagnation-point heat flux compared against the **Fay–Riddell** laminar
  stagnation-point heating correlation.
- Shock stand-off distance compared against **Billig's** empirical correlation
  for blunt-body shock stand-off.
- This is validation against established engineering correlations, not against
  a specific experimental dataset. If a suitable digitized experimental dataset
  is later located and verified as genuine, it may be added; none is assumed or
  fabricated here.

## Limitations (documented up front, to be revisited at project completion)

- Perfect-gas (calorically perfect, γ = 1.4) assumption — no real-gas
  dissociation/ionization effects relevant at true re-entry Mach numbers.
- No radiative heat transfer (surface-to-surroundings or shock-layer radiation).
- No ablation or surface mass loss.
- Laminar flow assumption — no boundary-layer transition or turbulent heating
  augmentation.
- Fixed isothermal wall — does not capture radiative-equilibrium wall-temperature
  feedback relevant to real TPS design (deferred to Project 04).
- 2D-axisymmetric only — no angle-of-attack or 3D asymmetric effects.
- Validation is against analytical/empirical correlations, not direct
  experimental data.
- Shakedown-derived startup parameters (timestep ramp schedule) are tuned for
  this specific geometry/mesh combination and are not claimed to generalize
  automatically to other cases in the eventual nose-radius sweep — each sweep
  case's startup behavior should be spot-checked, not assumed.
- Total drag is out of scope for this project. The base/wake region was found
  (via direct field inspection of the production M=7 run) to develop
  near-vacuum, continuum-invalid conditions (consistent with the prior
  repository's documented Knudsen-number-based continuum-breakdown finding),
  which drives an eventual solver crash there. Forebody QoIs (shock stand-off,
  stagnation heat flux, forebody pressure) were independently confirmed to
  converge robustly well before this occurs and remain valid; total drag
  requires the base-pressure contribution, which does not. Forebody
  (pressure) drag alone remains computable but is not part of this project's
  Required Outputs. A rarefied/DSMC-hybrid treatment of hypersonic base flow,
  which would be needed to resolve total drag properly, is noted as candidate
  scope for a future, separate project — not a Project 01 extension.

## Status

## Status

Shakedown A and B complete (Mach-ramp startup strategy validated at reduced
Mach and at full M=7 severity with a coarsened far-field mesh). First
production run (full resolution, M=7) completed a diagnosis cycle: the
Mach-ramp substantially delays but does not eliminate an eventual base/wake
continuum-breakdown crash; forebody QoIs were independently confirmed to
converge robustly well before that point, and total drag was dropped from
scope accordingly (see Limitations). Full history in `DEVELOPMENT_LOG.md`.
Next: grid convergence study on the confirmed forebody QoIs.
