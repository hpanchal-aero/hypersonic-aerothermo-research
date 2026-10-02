# Project 01 — Validation Against Analytical References (DRAFT)

STATUS: DRAFT for author review. Not committed. All numbers come from
runs and scratch calculations documented in DEVELOPMENT_LOG.md (entries
2026-09-29 and 2026-09-30). Each citation carries its own verification status (section 9);
unverified ones are marked [UNVERIFIED].

## 1. What this document is, and is not

This is a comparison of the baseline case (R_n = 0.05 m) with analytical
and semi-empirical references: Rayleigh-Pitot pressure, the normal-shock
pressure ratio, Billig's stand-off correlation, and the Fay-Riddell and
Sutton-Graves stagnation heating relations.

It is NOT experimental validation. No experimental dataset has been
identified or used. References are correlations and perfect-gas theory.
Agreement with them is evidence that the model behaves sensibly; it is
not evidence that it reproduces a measured flow.

No pass/fail tolerance was set. Each difference is reported next to its
own uncertainty.

Verification (mesh independence) is a separate matter and is limited to
two meshes at M=7; see section 7.

## 2. Case

- Freestream (30 km, US Standard Atmosphere): T = 226.5 K, p = 1197 Pa,
  rho = 0.018407 kg/m3, a = 301.68 m/s, M = 7, U = 2111.72 m/s.
- Perfect gas, gamma = 1.4, R = 287.0 J/(kg K); Sutherland viscosity.
- Spherically-blunted cone, R_n = 0.05 m, half-angle 15 deg, R_b = 0.15 m.
- Laminar, 2D-axisymmetric (1 deg wedge), isothermal wall T_w = 300 K.
- Solver: OpenFOAM 11 foamRun -solver shockFluid (rhoCentralFoam
  formulation), transient.
- M=7 state: the Mach ramp alone does not produce M=7 in the domain
  interior. The interior was reinitialized (U only) in 7,836 cells
  (production) / ~7,835 cells (coarse) selected by p within 1192-1202 Pa
  and x <= 0.40 m. See the 2026-09-29 log entry.

## 3. Data used

| Mesh | Wall-normal first cell d1 | Snapshots | Time past reinit |
|---|---|---|---|
| Coarse | 3.83 um | 1.0478e-4 - 1.0488e-4 s | ~9.4e-5 s |
| Production | 2.71 um | 4e-5 - 8.2e-5 s (2e-6 s output) | 3e-5 - 7.2e-5 s |

Both runs ended in a sigFpe crash (coarse 1.0488e-4 s, production
8.2167e-5 s). Only pre-crash snapshots are used. The coarse history is
short because purgeWrite removed earlier snapshots. The fine mesh failed
within 1.9e-6 s of its reinit and contributes no M=7 data.

## 4. Reference values (scratch calculations)

| Quantity | Value | Assumptions |
|---|---|---|
| Rayleigh-Pitot pressure | 76,072 Pa (63.55 p_inf) | perfect gas, normal shock then isentropic |
| Normal-shock pressure ratio | 57.0 (68.2 kPa) | M=7, gamma=1.4 |
| Stagnation temperature | 2,446 K | T_inf (1 + 0.2 M^2) |
| Billig stand-off | 7.64 mm | Delta/R_n = 0.143 exp(3.24/M^2), sphere |
| Stand-off at M=4 (wrong regime) | 8.75 mm | same correlation |
| Fay-Riddell q_stag | ~916 kW/m2 (Pr 0.71); 909 (Pr 0.72) | perfect gas, Le=1, Newtonian velocity gradient (see ref. 5) |
| Sutton-Graves q_stag | ~995 kW/m2 | empirical, Earth air |

## 5. Results

### 5.1 Stagnation pressure (axis)

- Production: window means over 1e-5 s blocks, 4e-5 to 8e-5 s: 96.5,
  101.2, 93.9, 102.3 % of Pitot (mean of the four: 98.5 %), with swings of
  +-4-5 % inside windows and 66.8-81.1 kPa at the extremes. No plateau.
- Production axis maximum at 4e-5 s: 63.65 p_inf (Pitot 63.55 p_inf), at
  2.25 mm from the wall; the wall-adjacent cell reads 59.6 p_inf, so a
  dip toward the wall appeared at some times and not at others.
- Coarse: p_stag = 67,964 Pa = 89.3 % of Pitot at 1.0488e-4 s. The coarse
  axis profile sits flat at 57.0-57.4 p_inf from 1.2 mm to the wall,
  equal to the normal-shock value, with none of the subsonic recovery
  (factor 1.115) that takes the pressure from 57.0 to 63.55 p_inf. The
  ratio 57.0/63.55 = 0.897 is close to the measured 0.893. This is an
  observation; its cause was not investigated.

### 5.2 Shock stand-off (stagnation axis)

Method: half-jump crossing between p_inf and the post-shock level,
linearly interpolated on the axis cell chain
(scripts/postprocessing/axis_shock_history.py).

| Mesh | Time (s) | Stand-off (mm) |
|---|---|---|
| Production | 4e-5 | 6.11 |
| Production | 5e-5 | 6.38 |
| Production | 6e-5 | 6.72 |
| Production | 7e-5 | 6.90 |
| Production | 8e-5 | 7.41 |
| Production | 8.2e-5 | 7.41 |
| Coarse | 1.0478e-4 - 1.0488e-4 | 7.63 - 7.64 |
| Billig (sphere) | - | 7.64 |
| M=4 correlation value | - | 8.75 |

Uncertainty: axis cell spacing near the shock is 0.97-0.77 mm (coarse)
and about 0.7 mm (production); the jump spans about 2 cells. Moving the
crossing level on the coarse profile gives 8.24 mm (25 % of the jump),
7.64 mm (50 %) and 7.00 mm (75 %); changing the post-shock reference
level moves the 50 % result by up to 0.14 mm. A bound of about +-0.8 mm
is used.

Production stand-off is still increasing at the end of its window. No
extrapolation to a plateau is made.

### 5.3 Stagnation heat flux (tip face)

The OpenFOAM 11 wallHeatFlux function object returned uniform zero on
every wall and was not used (cause not found). The flux was computed
directly from the fields with scripts/postprocessing/wall_flux_true.py:
q = k_w * dT/ds at the wall, from a quadratic through the wall (300 K)
and the first two cells along the face normal, with the true wall-normal
distances from polyMesh. Conductivity: modified-Eucken form (Pr = 0.69);
constant Pr = 0.71 gives values about 3 % lower. The Eucken form was
written from recollection and was not checked against the OpenFOAM 11
source.

Production, 22 snapshots, 4e-5 to 8.2e-5 s:

| Statistic | q (kW/m2) |
|---|---|
| Mean | 617 |
| Standard deviation | 64 (10.4 % of mean) |
| Minimum / maximum | 492 / 728 |
| Mean of first 11 / last 11 snapshots | 621 / 613 |
| Mean / Fay-Riddell (916) | 0.67 (range 0.54 - 0.79) |

q follows the wall-adjacent temperature almost exactly (correlation
0.999, about 11,400 W/m2 per K of T1), which ranged 346-366 K. The
fluctuation is slow compared with the 2e-6 s output spacing; its origin
(physical oscillation, reinit transient, or numerical) was not tested.

Coarse, one snapshot (1.048086e-4 s): 807 kW/m2 (0.88 of Fay-Riddell).
One-cell estimates: coarse 717, production 573 kW/m2 (at 8e-5 s). The
one-cell and quadratic estimates differ by about 8 %.

Resolution evidence on production (8e-5 s): over the first 0.1 rad of the
nose, the first-cell flux rises 573 to 748 kW/m2 while the wall-cell
temperature stays 358-361 K and d1 shrinks from 2.71 to 2.16 um. A real
sphere varies by about 1 % over that arc.

## 6. Assessment

| Quantity | Reference | CFD | Difference | Reading |
|---|---|---|---|---|
| Stagnation pressure, production | 76,072 Pa | 98.5 % (mean of four full 1e-5 s windows), oscillating | about -1.5 %, +-5 % swings | consistent on average; not settled |
| Stagnation pressure, coarse | 76,072 Pa | 89.3 % | -10.7 % | below reference; cause not investigated (5.1) |
| Stand-off, coarse | 7.64 mm | 7.64 mm (7.0-8.2) | 0 within +-0.8 mm | consistent within shock-capturing uncertainty |
| Stand-off, production | 7.64 mm | 7.41 mm at 8e-5 s, still rising | -3 % | consistent within +-0.7 mm; not settled |
| q_stag, production | 916 kW/m2 | 617 mean (492-728) | about -33 % | discrepancy; the reference is itself uncertain (ref. 5) |
| q_stag, coarse | 916 kW/m2 | 807 (single snapshot) | about -12 % | closer, but a single value |

- The stand-off is closer to the M=7 value than to the M=4 value (8.75
  mm), but it is a weak discriminator: the two values differ by 1.1 mm,
  about the axis cell spacing, and the coarse 25 % crossing (8.24 mm) is
  only 0.5 mm below the M=4 value. The regime is established more firmly
  by the post-shock pressure, p/p_inf = 57.0 on the coarse axis and 56.9
  on production, against 18.5 for a normal shock at M=4, and by the
  production axis maximum of 63.65 p_inf (Pitot at M=7: 63.55).
- The stand-off agreement with Billig is not a precise confirmation of
  the correlation. It is agreement within about 0.8 mm.
- The heat flux does not agree with Fay-Riddell. It is about 33 % low on
  production, and refining from coarse to production moved it further
  from the reference. With production fluctuating by 10 % (1 sigma) and
  coarse represented by one snapshot, the size of the mesh effect cannot
  be stated. How much of the gap is wall-normal resolution, how much the
  unsettled state, and how much the reference is not established. The
  reference uses a Newtonian velocity gradient, which ref. 5 identifies as
  a source of deviation between Fay-Riddell and computed or measured
  values; the size of that effect here was not determined.
- An 11 % lower stagnation pressure would lower the expected q by about
  4 % in the Fay-Riddell scaling (q goes as p_e^0.4). That does not
  account for the heat-flux gap.

## 7. Caveats and open items

- Nose mesh feature (found 2026-10-02): in the mesh behind every M=7
  result here (chord collar), the nominal 15.08 mm wall-normal collar is
  only about 1.6 mm thick near 40 deg of nose arc. On production the
  first-cell distance falls from 2.71 um at the tip to 0.293 um there and
  returns to 2.74 um at the tangent point. Off-axis nose quantities
  (heat-flux and pressure distributions, flank shock resolution) depend
  on the mesh in a way that varies along the nose; the first-cell flux
  rise from 573 to 748 kW/m2 over the first 0.1 rad is explained by it.
  The tip face (d = 2.71 um, designed h0/2 = 2.80 um) and the
  stagnation line are the least affected, but the size of the effect on
  them was not measured. A circular-arc collar (mesh v2) exists and the
  baseline is to be re-run on it; see DEVELOPMENT_LOG.md, 2026-10-02.
- Two meshes only at M=7. No convergence order or GCI can be computed
  for any M=7 quantity. The earlier p_stag GCI (0.12 %) applies to
  M=4/M=5-like conditions (see the 2026-09-29 log entry).
- The M=7 state is not steady: both runs were stopped by a crash, and
  production was run only 3e-5 - 7.2e-5 s past the reinit (a gas pass
  along the body takes about 2e-4 s). Aft-cone quantities are probably
  not at steady state. Stagnation-region quantities equilibrate faster.
- The reinit selection leaves unreinitialized M=4-velocity gas outside
  the set. A census on the fine mesh found 263 such cells. An upstream
  pressure wave (compression to ~4-5 kPa, expansion to ~0.5 kPa) is
  present on both meshes and moves at 1500-1800 m/s; it was still about
  0.05-0.1 m from the shock at each crash. Whether it relates to these
  cells was not tested.
- Open, uninvestigated: the coarse nose-region instability (reproducible
  crash), the unlocated production crash, the fine-mesh crash (cause
  untested), a dip in forebody station 2 (x = 0.131 m) to about 5,000 Pa
  on both meshes, and the wallHeatFlux zero output.
- Billig's correlation is for a sphere. The body is a sphere-cone whose
  spherical portion covers 75 deg from the axis; the near-axis stand-off
  is expected to be close to a sphere's, but this was not verified.
- Perfect gas, no real-gas chemistry, no radiation, laminar flow: the
  same assumptions as the references, so these do not separate the CFD
  from them. Real-gas effects at a stagnation temperature near 2,450 K
  were not estimated.
- Forebody probe coordinates came from an owner-face vertex average and
  may not sit exactly at cell centres. The pressure trends are not
  affected, but "exact cell centroid" overstates them.

## 8. Reproducibility

Run from the case directory (openfoam/production_m7_reinit or
openfoam/grid_convergence_coarse_m4start), with OpenFOAM 11 sourced:

    postProcess -func writeCellCentres -time <t>
    /usr/bin/python3 ../../scripts/postprocessing/axis_shock_history.py <t1> <t2> ...
    /usr/bin/python3 ../../scripts/postprocessing/wall_flux_true.py <t> 1

writeCellCentres writes C, Ccx, Ccy, Ccz into the time directory; remove
them afterwards. The reinitialized start states are in gitignored time
directories and are rebuilt from the M=4-start snapshots (not in git)
with topoSet (system/topoSetDict) and scripts/postprocessing/
reinit_U_only.py. The committed controlDicts are in their last-used
states, not baselines.

## 9. References

Each entry states what was and was not checked. Nothing here has been
checked against the full text of the primary source.

1. Billig, F. S., "Shock-wave shapes around spherical- and
   cylindrical-nosed bodies," Journal of Spacecraft and Rockets 4,
   822-823 (1967). Title, journal, volume and pages taken from the
   reference list of ref. 5. The stand-off formula used here,
   Delta/R_n = 0.143 exp(3.24/M^2), was NOT confirmed against the paper.
2. Fay, J. A. and Riddell, F. R., "Theory of stagnation point heat
   transfer in dissociated air," Journal of the Aeronautical Sciences
   25(2), 73-85 (1958). Citation details confirmed in several independent
   citing papers; the paper itself was not read.
3. Sutton, K. and Graves, R. A., "A general stagnation-point convective
   heating equation for arbitrary gas mixtures," NASA technical report,
   1971. [UNVERIFIED] Not checked at all.
4. Rayleigh-Pitot and normal-shock relations for a perfect gas: standard
   compressible-flow texts. No specific source has been chosen.
5. Olivier, H., "Influence of the velocity gradient on the stagnation
   point heating in hypersonic flow," Shock Waves 5, 205-216 (1995).
   Abstract read; full text not accessed. It reports that deviations
   between computed or measured stagnation-point heat flux and the
   Fay-Riddell theory are partly due to the Newtonian velocity gradient
   used in the reference; no magnitude or sign is available from the
   abstract.
