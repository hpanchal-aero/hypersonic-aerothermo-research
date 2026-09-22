# Project 01 — Case Specification

## Freestream Conditions (US Standard Atmosphere, 30 km altitude)

Shared by both the production case and Shakedown A (only Mach number/velocity
differs between them — see below).

| Quantity | Symbol | Value | Units |
|---|---|---|---|
| Altitude | — | 30 | km |
| Static temperature | T∞ | 226.5 | K |
| Static pressure | p∞ | 1197 | Pa |
| Density | ρ∞ | 1.841×10⁻² | kg/m³ |
| Ratio of specific heats | γ | 1.4 | — |
| Specific gas constant (air) | R | 287.0 | J/(kg·K) |
| Speed of sound | a∞ = √(γRT∞) | 301.68 | m/s |

### Production (full-resolution) freestream

| Quantity | Symbol | Value | Units |
|---|---|---|---|
| Freestream Mach number | M∞ | 7.0 | — |
| Freestream velocity | U∞ = M∞·a∞ | 2111.72 | m/s |

### Shakedown A freestream

| Quantity | Symbol | Value | Units |
|---|---|---|---|
| Freestream Mach number | M∞ | 3.0 | — |
| Freestream velocity | U∞ = M∞·a∞ | 905.04 | m/s |

### Shakedown B freestream

Identical to production (M=7, U∞=2111.72 m/s) — Shakedown B tests solver
startup robustness at full severity, only the far-field mesh resolution is
reduced relative to production (see Mesh section below).

## Baseline Geometry — Spherically-Blunted Cone (Axisymmetric)

Identical geometry used across production, Shakedown A, and Shakedown B —
only freestream conditions and far-field mesh resolution vary between cases.

**Governing relations:**
Spherical cap: r(x) = sqrt(R_n^2 - (x - R_n)^2), 0 <= x <= x_t
Tangent point: r_t = R_n * cos(theta_c)
x_t = R_n * (1 - sin(theta_c))
Conical afterbody: r(x) = r_t + (x - x_t) * tan(theta_c), x_t <= x <= L
Body length: L = x_t + (R_b - r_t) / tan(theta_c)
| Quantity | Symbol | Baseline Value | Units |
|---|---|---|---|
| Nose radius | R_n | 0.05 | m |
| Cone half-angle | θ_c | 15 | deg |
| Base radius | R_b | 0.15 | m |
| Tangent point (axial) | x_t | 0.037059 | m |
| Tangent point (radial) | r_t | 0.048296 | m |
| Overall body length | L | 0.416622 | m |
| Fillet radius (cone/base corner) | r_f | 0.003 | m |

## Wall Boundary Condition

Fixed isothermal wall temperature: T_w = 300 K (all cases, all wall patches).

## Mesh Topology — O-Grid (Structured Near-Body + Buffer Ring + Unstructured Far-Field)

Methodology carried forward from the prior repository incarnation's verified
O-grid design (checkMesh-clean: zero topology corruption, no negative volumes,
no open cells — see DEVELOPMENT_LOG.md for the full design history). Rebuilt
fresh in this repository; the parameters below are unchanged from the prior
verified design.

**Near-body structured blocks** (Nose, Cone, Fillet, Base — curved/straight
wall + 2 wall-normal spokes + straight collar per block):

| Quantity | Value |
|---|---|
| Wall-normal first-cell height | h0 = 5.607×10⁻⁶ m |
| Wall-normal growth ratio | 1.12 |
| Wall-normal divisions | 51 (52 points) |
| Collar offset distance (δ*) | 0.015077 m |
| Tangential divisions (Nose / Cone / Fillet / Base) | 61 / 151 / 15 / 76 |

**Structured buffer ring** (4 blocks, one per collar segment, immediately
outside the collar):

| Quantity | Value |
|---|---|
| Buffer thickness | t_buf = 0.018 m |
| Radial divisions | 8 |
| First buffer cell (continuity with collar) | 1.6204 mm |
| Buffer progression ratio | 1.091986 |
| Last buffer cell (outer) | 3.000 mm |

**Unstructured far-field** (production/Shakedown A resolution):

| Quantity | Value |
|---|---|
| Background field size at buffer boundary | 4.5 mm |
| Far-field coarsening target | 40 mm |
| Coarsening distance | 0.4 m |

**Domain extents** (production, Shakedown A — full resolution):

| Boundary | Value |
|---|---|
| Upstream farfield | x = −0.30 m (−6×R_n) |
| Outer radial farfield | r = 0.75 m (15×R_n) |
| Outlet | x = 0.469700 m |

**Shakedown B far-field resolution:** coarser than the above (specific
coarsening parameters TBD when Shakedown B is reached — near-body/buffer-ring
resolution stays identical to production, only far-field cell size changes,
for faster iteration while preserving the actual near-wall stiffness
mechanism under test).

## Boundary Conditions (all cases — patch names shared across production,
Shakedown A, and Shakedown B meshes)

| Patch | p | T | U |
|---|---|---|---|
| farfield_upstream | fixedValue (freestream) | fixedValue (T∞) | fixedValue (U∞, case-dependent) |
| farfield_outer | fixedValue (freestream) | fixedValue (T∞) | fixedValue (U∞, case-dependent) |
| outlet | zeroGradient | zeroGradient | zeroGradient |
| wall_nose / wall_cone / wall_fillet / wall_base | zeroGradient | fixedValue (300 K) | noSlip |
| frontWedge / backWedge | wedge | wedge | wedge |

No differentiation between the four wall patches (per explicit decision).

## Solver

- `rhoCentralFoam` via `foamRun -solver shockFluid` (OpenFOAM 11)
- Laminar (`simulationType laminar;`)
- Thermophysical model: `hePsiThermo` / `pureMixture` / `sutherland` transport /
  `hConst` thermo / `perfectGas` equation of state / `sensibleInternalEnergy`
- `interpolationSchemes`: `reconstruct(rho/U/T)` = `vanAlbada`
- `PIMPLE`: `nOuterCorrectors=1`, `nCorrectors=1`, `nNonOrthogonalCorrectors=0`

These solver/scheme settings are unchanged from the prior repository
incarnation and were never implicated in the cold-start crash investigation —
only the time-stepping/startup strategy (below) is new.

## Solver Startup Strategy — Timestep Ramp (NEW, motivated by the reset)

**Status: not yet designed.** To be determined empirically via Shakedown A,
starting from the evidence already gathered in the prior incarnation:

- The adaptive controller's own unconstrained first-step choice
  (`maxCo=0.5`, `maxDeltaT=1e-6` → actual first step `deltaT=1.2e-10s`) crashes
  immediately on the production-resolution mesh.
- A fixed `deltaT=1e-13s` survived thousands of steps with quiet, converging
  residuals but is impractically slow (~58 minutes of wall-clock to reach
  `t≈2.9e-9s`).
- A fixed `deltaT=3.46e-12s` survived ~4,223 steps (`t=1.46e-8s`) before
  crashing via the same mechanism — establishing that a working step size
  exists between these bounds, and that fixed-step survival is a function of
  physical time reached, not simply "small enough forever."

Shakedown A will determine a specific ramp schedule (e.g., a tightly capped
`maxDeltaT` for an initial transient window, relaxing once gradients have
smoothed) at the reduced M=3 severity, to be documented here once validated.

## Verification Strategy

- **Shakedown methodology verification (new):** each shakedown stage
  documented with explicit pass/fail evidence (startup parameters tested,
  survival time, residual behavior) before production resolution is attempted.
- Grid convergence study on the production baseline case (once reached): ≥3
  mesh densities, tracking stagnation-point heat flux and shock stand-off
  distance.
- Global mass conservation check (inflow vs. outflow mass flux).

## Validation Strategy

- Stagnation-point heat flux vs. **Fay–Riddell** laminar stagnation-point
  heating correlation.
- Shock stand-off distance vs. **Billig's** empirical correlation.
- Validation against established correlations, not a specific experimental
  dataset (none assumed or fabricated).

## Status

Specification drafted for the reset repository. Shakedown A (M=3, same
geometry/near-wall mesh resolution as production) is the next implementation
step: mesh generation, then timestep-ramp strategy design and testing.
