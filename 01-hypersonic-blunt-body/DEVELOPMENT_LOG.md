# Project 01 — Development Log

Running narrative of decisions, experiments, failures, and diagnostics.
`PROJECT_DEFINITION.md` and `CASE_SPECIFICATION.md` hold the current,
authoritative specification; this file holds the history of how we got there.

---

## 2026-09-22: Project Reset — Repository Recreated, Methodology Revised

### Why this reset happened

The prior incarnation of this repository built a fully explicit, structured
O-grid mesh (near-body blocks + buffer ring + unstructured far-field) across
two verified stages, specifically to eliminate a structural axis-region
topology defect present in an earlier automatic-BoundaryLayer-field mesh. That
defect was real, and the O-grid rebuild fixed it — verified via `checkMesh`
showing zero topology corruption and meaningfully better mesh-quality metrics
than the original mesh in every respect (max aspect ratio 322.5 vs 761.8,
zero negative volumes/open cells/zero-area faces throughout).

Despite this, the first CFD attempt on the new mesh still crashed via the
identical `sigFpe`/`hePsiThermo::calculate()` failure mechanism as the
original mesh — but at the very first timestep (`t=1.2e-10s`), far earlier
than the original mesh's best-case survival (`~4.5e-7s`).

### What the diagnosis actually showed

A sequence of controlled, single-variable experiments (documented in full in
the prior repository, summarized here since that repository no longer exists):

1. **Mesh cell volume was directly checked and ruled out.** An initial
   diagnostic script had a face-winding sign-convention bug (cross-product
   argument order reversed, flipping every computed cell volume's sign) —
   caught and fixed before drawing any conclusion from it. The corrected
   result showed the mesh's smallest cells form a smooth, healthy geometric
   progression (ratio ≈1.12, matching the design intent exactly) at the
   stagnation-point location — not an anomaly.
2. **Timestep-size dependence was demonstrated directly.** A fixed
   `deltaT=1e-13s` run (on the exact same mesh that crashed instantly under
   the adaptive controller) survived thousands of steps with quiet,
   converging residuals — ruling out a static field/geometry defect that
   would blow up regardless of step size.
3. **A log-scale bisection attempt (`deltaT=3.46e-12s`) complicated the
   picture rather than simply confirming it:** this run survived ~4,223 steps
   to `t=1.46e-8s` before crashing via the identical mechanism — later in
   physical time than where the `1e-13s` run had been stopped (not run to
   failure). This means the evidence supports "failure is tied to physical
   simulation time, with fixed-step survival simply taking longer wall-clock
   to reach that same time" at least as well as it supports a clean
   step-size stability threshold. Bisecting on step size alone would not have
   reliably located anything meaningful without also controlling for physical
   time reached.
4. **An unexplained secondary lead was noted but not investigated:**
   persistently elevated/noisy `Uz` velocity component in the solver log
   (should be ~0 in a 2D-axisymmetric wedge case) just before the `3.46e-12s`
   run's crash.
5. **`FOAM_SIGFPE=false` did not work** in this OpenFOAM 11/`foamRun` setup —
   confirmed set in the environment, but the crash trace remained byte-
   identical to FPE-trapping-enabled runs. Mechanism for disabling FPE
   trapping in this environment remains unresolved; not to be assumed
   functional without direct re-verification if attempted again.

### Working hypothesis (not yet confirmed)

The crash is caused by cold-start boundary-condition/initial-condition
stiffness: a uniform M=7 freestream field applied everywhere, including at
wall-adjacent cells, meeting an instantaneously-imposed no-slip/300K wall
condition at a micron-scale first cell (`h0=5.607e-6m`). This is a startup-
methodology problem, not a mesh-topology problem — checkMesh-clean geometry is
not sufficient evidence a mesh will survive a solver cold start, since
angle/volume-based mesh-quality metrics don't capture acoustic/diffusive
startup stiffness from an abrupt BC/IC mismatch.

### Decision: full reset

Rather than continue reactive, back-and-forth debugging on the existing
repository, the research question was kept unchanged, but:
- The GitHub repository was deleted and recreated fresh.
- `PROJECT_DEFINITION.md` and `CASE_SPECIFICATION.md` were reformulated from
  scratch (carrying forward the verified O-grid meshing methodology and all
  freestream/geometry parameters, which were never implicated in the crash).
- This `DEVELOPMENT_LOG.md` replaces the old pattern of appending "Session
  Update" narrative sections directly into the spec files.
- A two-stage shakedown sequence (Shakedown A: M=3 reduced-severity cold-start
  test; Shakedown B: full M=7 with a coarser far-field mesh for faster
  iteration) was added ahead of any production run, specifically to validate
  a timestep-ramp startup strategy before committing to full-resolution
  compute time.

### Status

Repository skeleton, master README, `.gitignore`, `PROJECT_DEFINITION.md`, and
`CASE_SPECIFICATION.md` complete. Next: Shakedown A mesh generation (same
O-grid methodology, full near-wall resolution, M=3 freestream).

---

## 2026-09-22: Shakedown A Complete — Mach-Ramp Startup Strategy Validated

### Objective

Determine whether a timestep-ramp or Mach-ramp startup strategy allows the
verified O-grid mesh to survive the cold-start instability observed at full
M=7 severity (instant `sigFpe` crash at `t=1.2e-10s`), using a reduced-severity
test case as a first proving ground.

### CFL sanity check (before the Mach investigation)

Before investigating Mach severity, confirmed the basic CFL constraint governing
this mesh: the smallest cell (wall-adjacent, `Δx≈5.6e-6m`) limits `deltaT` to
roughly `1.68e-9s` at `maxCo=0.5` (M=3 condition). A direct test at a fixed
`deltaT=1e-5s` (requested to see the failure mode firsthand) confirmed this:
momentum residuals diverged (`Ux`/`Uy` to `~1e10`/`1e11`) within the first
timestep, followed by a distinct failure signature (energy→temperature
inversion failing to converge after 100 iterations, `T` pinned at `~3e14 K`) —
a different, more diagnostic failure than the cold-start `sigFpe`, confirming
this is a separate, well-understood numerical-stability limit, not the subject
of this investigation.

### Mach-number bisection (unmodified adaptive timestep settings)

With the original `adjustTimeStep yes / maxCo 0.5 / maxDeltaT 1e-6` settings
(unchanged from every prior baseline), tested cold-start survival across
Mach number, all other conditions (30km atmosphere, same near-wall mesh
resolution) held fixed:

| Mach | Result |
|---|---|
| 3.0 | Stable (ran ~2.6 hours wall-clock to t=1.585e-4s, residuals quiet/converging) |
| 5.0 | Stable (ran ~12s wall-clock to t=9.77e-8s, residuals converging) |
| 5.125 | Stable (confirmed to t=9.3e-9s before stopped) |
| 5.25 | Crashes (identical sigFpe/hePsiThermo mechanism, t=1.2e-10s) |
| 5.5 | Crashes (same) |
| 6.0 | Crashes (same) |
| 7.0 | Crashes (same, from prior repository) |

**Cold-start instability threshold: (M=5.125, M=5.25]** — a sharp transition,
not a gradual degradation, consistent with a genuine BC/IC-severity threshold
rather than accumulating numerical error with Mach number.

A recurring secondary observation across every stable run (M=3, M=5, M=5.125):
the `Uz` velocity residual (should be ~0 in a 2D-axisymmetric wedge case) is
consistently 2-4 orders of magnitude larger than `Ux`/`Uy`, and slower to
decay. Not blocking convergence in any run so far. Flagged as an open item,
not yet investigated (see Open Items below).

### Mach-ramp strategy: validated

Designed a startup strategy using a time-varying `uniformFixedValue`/`table`
boundary condition on `U` at the farfield patches: linear ramp from the
proven-stable M=5 velocity (1508.4 m/s) to the M=7 production velocity
(2111.72 m/s) over `t=0` to `t=5e-8s`, then held constant. `p` and `T` were
NOT ramped — with altitude (and therefore T∞/a∞) fixed, Mach number depends
only on U, so p/T are identical at every point along the ramp path; ramping
them would have been unnecessary complexity.

**Result: the run survived past t=5.4e-7s** — beyond the ramp's completion
(full M=7 reached and held from t=5e-8s onward), beyond the historical
crash-zone equivalent identified via bisection (~t=3.1e-9s to 6.25e-9s on this
ramp's timeline), and beyond the OLD repository's best-ever survival time on
any M=7 attempt (~4.5e-7s to 4.52e-7s, achieved only after the fan-point mesh
fix, on a mesh that eventually still crashed there). Residuals were
excellent and clearly converging throughout (Ux/Uy final residuals down at
~1e-11/1e-10, e at ~1e-14), not merely "hasn't crashed yet." Run was stopped
manually (Ctrl+C) at t=5.4e-7s to conclude the shakedown, not due to any sign
of instability.

### Conclusion

**The cold-start-severity hypothesis is confirmed with direct, strong
evidence.** The repeated crashes that motivated this project's full reset were
never caused by mesh topology (the O-grid mesh is checkMesh-clean and
unchanged throughout this entire investigation) — they were caused by the
abruptness of the M=7 boundary condition jump imposed on a uniform initial
field. A 50-nanosecond linear Mach ramp, using a proven-stable Mach number as
the starting point, resolves the instability entirely.

### Open items carried forward

- The elevated/slow-decaying `Uz` residual pattern (observed in every stable
  run so far) remains unexplained. Not blocking, but should be investigated
  before or during Shakedown B.
- The Mach-ramp duration (5e-8s) was a first attempt and was not
  systematically tuned — it happened to work on the first try. Whether a
  shorter ramp would also work, or whether this specific duration has margin
  to spare, is unknown and not necessary to determine for Shakedown A's
  purposes, but may be worth characterizing before committing to it as the
  permanent production startup strategy.
- This result is specific to the near-wall mesh resolution tested (production
  resolution, coarse far-field not yet involved) — Shakedown B will confirm
  the same ramp strategy also works once the far-field mesh changes.

### Status

Shakedown A complete. Ready to proceed to Shakedown B (full M=7, coarser
far-field mesh, Mach-ramp startup) to confirm the strategy generalizes before
committing to the production mesh.

---

## 2026-09-22: Shakedown A Complete — Mach-Ramp Startup Strategy Validated

### Objective

Determine whether a timestep-ramp or Mach-ramp startup strategy allows the
verified O-grid mesh to survive the cold-start instability observed at full
M=7 severity (instant `sigFpe` crash at `t=1.2e-10s`), using a reduced-severity
test case as a first proving ground.

### CFL sanity check (before the Mach investigation)

Before investigating Mach severity, confirmed the basic CFL constraint governing
this mesh: the smallest cell (wall-adjacent, `Δx≈5.6e-6m`) limits `deltaT` to
roughly `1.68e-9s` at `maxCo=0.5` (M=3 condition). A direct test at a fixed
`deltaT=1e-5s` (requested to see the failure mode firsthand) confirmed this:
momentum residuals diverged (`Ux`/`Uy` to `~1e10`/`1e11`) within the first
timestep, followed by a distinct failure signature (energy→temperature
inversion failing to converge after 100 iterations, `T` pinned at `~3e14 K`) —
a different, more diagnostic failure than the cold-start `sigFpe`, confirming
this is a separate, well-understood numerical-stability limit, not the subject
of this investigation.

### Mach-number bisection (unmodified adaptive timestep settings)

With the original `adjustTimeStep yes / maxCo 0.5 / maxDeltaT 1e-6` settings
(unchanged from every prior baseline), tested cold-start survival across
Mach number, all other conditions (30km atmosphere, same near-wall mesh
resolution) held fixed:

| Mach | Result |
|---|---|
| 3.0 | Stable (ran ~2.6 hours wall-clock to t=1.585e-4s, residuals quiet/converging) |
| 5.0 | Stable (ran ~12s wall-clock to t=9.77e-8s, residuals converging) |
| 5.125 | Stable (confirmed to t=9.3e-9s before stopped) |
| 5.25 | Crashes (identical sigFpe/hePsiThermo mechanism, t=1.2e-10s) |
| 5.5 | Crashes (same) |
| 6.0 | Crashes (same) |
| 7.0 | Crashes (same, from prior repository) |

**Cold-start instability threshold: (M=5.125, M=5.25]** — a sharp transition,
not a gradual degradation, consistent with a genuine BC/IC-severity threshold
rather than accumulating numerical error with Mach number.

A recurring secondary observation across every stable run (M=3, M=5, M=5.125):
the `Uz` velocity residual (should be ~0 in a 2D-axisymmetric wedge case) is
consistently 2-4 orders of magnitude larger than `Ux`/`Uy`, and slower to
decay. Not blocking convergence in any run so far. Flagged as an open item,
not yet investigated (see Open Items below).

### Mach-ramp strategy: validated

Designed a startup strategy using a time-varying `uniformFixedValue`/`table`
boundary condition on `U` at the farfield patches: linear ramp from the
proven-stable M=5 velocity (1508.4 m/s) to the M=7 production velocity
(2111.72 m/s) over `t=0` to `t=5e-8s`, then held constant. `p` and `T` were
NOT ramped — with altitude (and therefore T∞/a∞) fixed, Mach number depends
only on U, so p/T are identical at every point along the ramp path; ramping
them would have been unnecessary complexity.

**Result: the run survived past t=5.4e-7s** — beyond the ramp's completion
(full M=7 reached and held from t=5e-8s onward), beyond the historical
crash-zone equivalent identified via bisection (~t=3.1e-9s to 6.25e-9s on this
ramp's timeline), and beyond the OLD repository's best-ever survival time on
any M=7 attempt (~4.5e-7s to 4.52e-7s, achieved only after the fan-point mesh
fix, on a mesh that eventually still crashed there). Residuals were
excellent and clearly converging throughout (Ux/Uy final residuals down at
~1e-11/1e-10, e at ~1e-14), not merely "hasn't crashed yet." Run was stopped
manually (Ctrl+C) at t=5.4e-7s to conclude the shakedown, not due to any sign
of instability.

### Conclusion

**The cold-start-severity hypothesis is confirmed with direct, strong
evidence.** The repeated crashes that motivated this project's full reset were
never caused by mesh topology (the O-grid mesh is checkMesh-clean and
unchanged throughout this entire investigation) — they were caused by the
abruptness of the M=7 boundary condition jump imposed on a uniform initial
field. A 50-nanosecond linear Mach ramp, using a proven-stable Mach number as
the starting point, resolves the instability entirely.

### Open items carried forward

- The elevated/slow-decaying `Uz` residual pattern (observed in every stable
  run so far) remains unexplained. Not blocking, but should be investigated
  before or during Shakedown B.
- The Mach-ramp duration (5e-8s) was a first attempt and was not
  systematically tuned — it happened to work on the first try. Whether a
  shorter ramp would also work, or whether this specific duration has margin
  to spare, is unknown and not necessary to determine for Shakedown A's
  purposes, but may be worth characterizing before committing to it as the
  permanent production startup strategy.
- This result is specific to the near-wall mesh resolution tested (production
  resolution, coarse far-field not yet involved) — Shakedown B will confirm
  the same ramp strategy also works once the far-field mesh changes.

### Status

Shakedown A complete. Ready to proceed to Shakedown B (full M=7, coarser
far-field mesh, Mach-ramp startup) to confirm the strategy generalizes before
committing to the production mesh.

---

## 2026-09-24: Shakedown B Complete — Mach-Ramp Strategy Generalizes to Coarsened Far-Field

### Objective

Confirm the Mach-ramp startup strategy validated in Shakedown A (full near-wall
resolution) also works with the coarsened far-field mesh intended to speed up
iteration for the eventual production case.

### Mesh

Same near-body + buffer-ring geometry as Shakedown A, byte-identical (verified:
max aspect ratio, min volume, max non-orthogonality, and the 283 severely
non-orthogonal face count all identical to Shakedown A — confirms these live
entirely in the unchanged collar). Far-field background field coarsened
(SizeMin 4.5mm→9mm, SizeMax 40mm→80mm, DistMax unchanged at 0.4m), reducing
total cells from 22,266 to 19,179. Average non-orthogonality (13.85°→14.68°)
and max skewness (0.778→1.014) increased modestly, as expected for coarser
unstructured cells, both remaining well within checkMesh OK bounds. Same
single benign wedge-planarity failure as every prior stage.

Far-field patch index mapping (outlet/farfield_outer/farfield_upstream)
independently re-verified via the same BoundingBox diagnostic used in the
original repository's Stage 2 and in Shakedown A — confirmed identical
indices (outFarfield[6]/[7]/[8]) despite the different sizing field, since
only Field[2] parameters changed, not point/curve/surface topology or
extrusion order.

### Result

Using the identical Mach-ramp strategy validated in Shakedown A (linear U
ramp M=5→7 over t=0 to 5e-8s, p/T held constant), the run survived past
t=5.5e-7s at full M=7 severity — beyond the ramp's completion, beyond the
historical crash zone, and beyond the old repository's best-ever M=7
survival (~4.5e-7s) — with the same clean, converging residual pattern seen
in Shakedown A. Run stopped manually (Ctrl+C) at t=5.5e-7s, not due to any
sign of instability.

A wall-clock difference was observed: at matched physical time (~5.33e-7s),
this run's ExecutionTime (~21s) was substantially lower than Shakedown A's
ramp run at the equivalent point (~138s) — larger than the ~14% cell-count
reduction alone would explain. No confirmed cause identified (possible
system load variation between sessions); noted factually, not claimed as a
verified effect of far-field coarsening.

The Uz residual anomaly (elevated, slower-decaying than Ux/Uy/e) was
observed again, now in 5 consecutive stable runs (M=3, M=5, M=5.125, the
M=5→7 ramp, and this coarse-far-field M=7 ramp) — still not investigated.

### Conclusion

The Mach-ramp startup strategy is validated across both near-wall resolution
(Shakedown A) and far-field mesh density (Shakedown B). Both required
shakedown stages are complete. Ready to proceed to the production mesh
(full near-wall resolution + fine far-field, matching Shakedown A's mesh
exactly) using this validated startup strategy.

### Open items carried forward (unchanged)

- Uz residual anomaly: still unexplained, now observed in 5 stable runs.
  Should be investigated before or during production runs, since it could
  matter for later QoI accuracy even though it hasn't blocked convergence.
- The unexplained wall-clock discrepancy between Shakedown A and B (noted
  above) — not investigated, low priority.
- Mach-ramp duration (5e-8s) still not systematically tuned — validated at
  two mesh configurations on the first attempt, but shorter/longer durations
  were never tested.

### Status

Shakedown A and B both complete. Next: build the production mesh (full
near-wall resolution, fine far-field — reusing Shakedown A's exact mesh) and
begin the standard verification (grid convergence) → validation (Fay-Riddell,
Billig) → parametric sweep sequence from PROJECT_DEFINITION.md.

---

## 2026-09-24: First Production Run — Correction to Shakedown Conclusions, Modeling-Scope Decision Adopted

### Correction to prior entries

The Shakedown A and Shakedown B entries above state that the Mach-ramp
startup strategy "resolves" or "eliminates" the cold-start instability.
This was premature. Both shakedown runs were manually stopped (Ctrl+C) at
t≈5.4-5.5e-7s because the result looked sufficient at the time - neither
run was allowed to continue to a real endpoint. This first production run,
given a generous endTime=1e-5 rather than being stopped early, revealed
that the instability was delayed, not eliminated: the run crashed via the
identical sigFpe/hePsiThermo::calculate() mechanism at t=2.64154e-06s -
roughly 22,000x later than the raw cold-start crash (1.2e-10s), but still
a crash. The corrected understanding: the Mach-ramp is a genuine, large
improvement to startup robustness, not a complete fix for an unrelated,
separate issue (see below).

### Crash diagnosis

Direct inspection of the last written field snapshot (t=2.63989e-06s, one
step before the crash) via a spatial diagnostic script (locating field
extremes by cell centroid, derived independently from polyMesh points/
faces/owner - not trusted from any prior assumption):

- High p/T (p≈5.16e4 Pa, T≈1833K) localized at the nose stagnation region
  (x≈0.0004-0.0005, r≈0.006-0.007) - physically expected at M=7, not
  anomalous.
- Low p/T (p≈0.035 Pa, T≈1.04 K) localized at x≈0.41662 (matching L, the
  wall_base patch location) across a wide radial range (r≈0.001-0.137) -
  a near-vacuum, continuum-invalid condition at the base wall/wake.
- The previously-flagged "elevated Uz residual" open item (observed in
  5+ prior runs) was checked directly against actual Uz field values at
  this snapshot: all ~1e-10 to 1e-11, i.e. floating-point noise. This
  closes that open item as resolved-benign - the anomaly was in the
  solver's linear-system residual metric (relative to a very small RHS),
  not in the physical field. It was a red herring, not a contributing
  factor to the crash.

**Conclusion: this is the same base/wake continuum-breakdown limitation
documented in the prior repository's "Corner/Base Investigation Concluded"
entry** (Boyd et al. Knudsen-number criterion showed 2-4 orders of
magnitude past the continuum-breakdown threshold in that region, under
the same freestream conditions). The Mach-ramp did not fix this - it
isn't a startup problem - but by eliminating the earlier, separate
axis-topology and cold-start-severity failure modes, it allowed the
solution to run long enough for this pre-existing, physically-real
modeling-domain limitation to become the new limiting factor.

### Forebody QoI convergence check (before accepting any scope decision)

Rather than assume the base/wake limitation doesn't matter for the actual
research question, checked directly:

**Stagnation point** (probeStagnation, 1,685 samples, t=0 to t=2.6399e-06s):
- p_stag: last 3 relative changes 0.0175%, 0.0171%, 0.0167% - PASS (formal
  1%-for-3-consecutive-snapshots criterion), monotonically decreasing.
- T_stag: last 3 relative changes 0.0209%, 0.0207%, 0.0205% - PASS, same
  pattern.
- Both results are far more robust than the prior repository's "marginal
  pass" on the same criterion (0.3-0.4%, achieved only in a narrow window
  immediately before failure) - here the margin is roughly 15-20x tighter,
  well clear of the crash, not scraping by.

**Forebody surface pressure** (5 wall_cone stations spanning x=0.039 to
x=0.412, extracted from owner-cell values across 20 written snapshots -
correct interpretation of the zeroGradient wall BC):
- All 5 stations PASS, last-3 relative changes ranging 0.0004% to 0.015% -
  comprehensive, not cherry-picked: the entire forebody pressure
  distribution is converged well before the crash, not just the
  stagnation point.

### Decision: modeling-scope limitation adopted, drag dropped from Project 01 scope (Harsh's explicit call)

Following the same resolution as the prior repository's investigation:
**forebody QoIs (shock stand-off distance, stagnation-point heat flux,
forebody surface pressure distribution) are accepted as valid** for this
project's research question. The base/wake region is documented as an
out-of-scope continuum-breakdown limitation - the calorically-perfect-gas
Navier-Stokes model is not physically valid there at these freestream
conditions, independent of mesh or startup strategy, and this does not
invalidate the CFD solution in the forebody region where the research
question's quantities of interest are evaluated.

**Total drag is dropped from this project's scope entirely** (not bounded
or estimated) - forebody (pressure) drag remains computable from the
converged forebody pressure field, but total drag requires the
base-pressure contribution, which sits in the continuum-invalid region
and is not resolvable within this project's perfect-gas, continuum-CFD
methodology. This is noted as a candidate topic for a future, separate
project (rarefied/DSMC-hybrid treatment of hypersonic base flow), not a
Project 01 modification.

### Status

Ready to proceed to grid convergence (verification) on the three confirmed
forebody QoIs (shock stand-off distance, stagnation-point heat flux,
forebody surface pressure distribution), followed by validation against
Fay-Riddell (stagnation heat flux) and Billig (shock stand-off)
correlations, per PROJECT_DEFINITION.md. Drag is removed from Required
Outputs. The production mesh, Mach-ramp startup strategy, and this QoI
scoping are now the settled methodology going into that work.

---

## 2026-09-24: First Production Run — Correction to Shakedown Conclusions, Modeling-Scope Decision Adopted

### Correction to prior entries

The Shakedown A and Shakedown B entries above state that the Mach-ramp
startup strategy "resolves" or "eliminates" the cold-start instability.
This was premature. Both shakedown runs were manually stopped (Ctrl+C) at
t≈5.4-5.5e-7s because the result looked sufficient at the time - neither
run was allowed to continue to a real endpoint. This first production run,
given a generous endTime=1e-5 rather than being stopped early, revealed
that the instability was delayed, not eliminated: the run crashed via the
identical sigFpe/hePsiThermo::calculate() mechanism at t=2.64154e-06s -
roughly 22,000x later than the raw cold-start crash (1.2e-10s), but still
a crash. The corrected understanding: the Mach-ramp is a genuine, large
improvement to startup robustness, not a complete fix for an unrelated,
separate issue (see below).

### Crash diagnosis

Direct inspection of the last written field snapshot (t=2.63989e-06s, one
step before the crash) via a spatial diagnostic script (locating field
extremes by cell centroid, derived independently from polyMesh points/
faces/owner - not trusted from any prior assumption):

- High p/T (p≈5.16e4 Pa, T≈1833K) localized at the nose stagnation region
  (x≈0.0004-0.0005, r≈0.006-0.007) - physically expected at M=7, not
  anomalous.
- Low p/T (p≈0.035 Pa, T≈1.04 K) localized at x≈0.41662 (matching L, the
  wall_base patch location) across a wide radial range (r≈0.001-0.137) -
  a near-vacuum, continuum-invalid condition at the base wall/wake.
- The previously-flagged "elevated Uz residual" open item (observed in
  5+ prior runs) was checked directly against actual Uz field values at
  this snapshot: all ~1e-10 to 1e-11, i.e. floating-point noise. This
  closes that open item as resolved-benign - the anomaly was in the
  solver's linear-system residual metric (relative to a very small RHS),
  not in the physical field. It was a red herring, not a contributing
  factor to the crash.

**Conclusion: this is the same base/wake continuum-breakdown limitation
documented in the prior repository's "Corner/Base Investigation Concluded"
entry** (Boyd et al. Knudsen-number criterion showed 2-4 orders of
magnitude past the continuum-breakdown threshold in that region, under
the same freestream conditions). The Mach-ramp did not fix this - it
isn't a startup problem - but by eliminating the earlier, separate
axis-topology and cold-start-severity failure modes, it allowed the
solution to run long enough for this pre-existing, physically-real
modeling-domain limitation to become the new limiting factor.

### Forebody QoI convergence check (before accepting any scope decision)

Rather than assume the base/wake limitation doesn't matter for the actual
research question, checked directly:

**Stagnation point** (probeStagnation, 1,685 samples, t=0 to t=2.6399e-06s):
- p_stag: last 3 relative changes 0.0175%, 0.0171%, 0.0167% - PASS (formal
  1%-for-3-consecutive-snapshots criterion), monotonically decreasing.
- T_stag: last 3 relative changes 0.0209%, 0.0207%, 0.0205% - PASS, same
  pattern.
- Both results are far more robust than the prior repository's "marginal
  pass" on the same criterion (0.3-0.4%, achieved only in a narrow window
  immediately before failure) - here the margin is roughly 15-20x tighter,
  well clear of the crash, not scraping by.

**Forebody surface pressure** (5 wall_cone stations spanning x=0.039 to
x=0.412, extracted from owner-cell values across 20 written snapshots -
correct interpretation of the zeroGradient wall BC):
- All 5 stations PASS, last-3 relative changes ranging 0.0004% to 0.015% -
  comprehensive, not cherry-picked: the entire forebody pressure
  distribution is converged well before the crash, not just the
  stagnation point.

### Decision: modeling-scope limitation adopted, drag dropped from Project 01 scope (Harsh's explicit call)

Following the same resolution as the prior repository's investigation:
**forebody QoIs (shock stand-off distance, stagnation-point heat flux,
forebody surface pressure distribution) are accepted as valid** for this
project's research question. The base/wake region is documented as an
out-of-scope continuum-breakdown limitation - the calorically-perfect-gas
Navier-Stokes model is not physically valid there at these freestream
conditions, independent of mesh or startup strategy, and this does not
invalidate the CFD solution in the forebody region where the research
question's quantities of interest are evaluated.

**Total drag is dropped from this project's scope entirely** (not bounded
or estimated) - forebody (pressure) drag remains computable from the
converged forebody pressure field, but total drag requires the
base-pressure contribution, which sits in the continuum-invalid region
and is not resolvable within this project's perfect-gas, continuum-CFD
methodology. This is noted as a candidate topic for a future, separate
project (rarefied/DSMC-hybrid treatment of hypersonic base flow), not a
Project 01 modification.

### Status

Ready to proceed to grid convergence (verification) on the three confirmed
forebody QoIs (shock stand-off distance, stagnation-point heat flux,
forebody surface pressure distribution), followed by validation against
Fay-Riddell (stagnation heat flux) and Billig (shock stand-off)
correlations, per PROJECT_DEFINITION.md. Drag is removed from Required
Outputs. The production mesh, Mach-ramp startup strategy, and this QoI
scoping are now the settled methodology going into that work.

## 2026-09-27 — Grid Convergence Study: Ramp-Start-Mach Confound Discovered and Resolved

### Objective

Establish mesh independence for the three confirmed forebody QoIs (shock
stand-off distance, stagnation-point heat flux/temperature, forebody
surface pressure distribution) across three O-grid mesh densities
(coarse, production=medium, fine), refined via wall-normal near-body
resolution (h0) at a fixed sqrt(2) ratio, per PROJECT_DEFINITION.md's
Verification Strategy.

### Coarse and fine meshes built and cold-start-checked independently

Per the established protocol (a Mach-ramp validated at one mesh density
does not automatically transfer to another), each new density's cold-start
tolerance was checked directly rather than assumed:

- Coarse mesh: production's existing M=5->7 ramp worked without
  modification (a coarser cell relaxes CFL severity). Crashed at
  t=2.63249e-06s - essentially the same physical time as production's
  t=2.64154e-06s crash, initially read as evidence the base/wake crash
  timing is independent of near-wall mesh resolution (later shown to be
  an artifact of both runs sharing the same M=5-start ramp, not a
  resolution-independence result - see below).
- Fine mesh: production's M=5-start ramp crashed it instantly
  (t=1.2e-10s). A fresh Mach bisection performed directly on the fine
  mesh found a new, lower cold-start threshold at (M=4, M=4.25] -
  confirming a finer near-wall cell is more cold-start-severe, and that
  ramp validation does not transfer across mesh densities. A new M=4->7
  ramp (same 5e-8s duration as production's) was designed and this run
  did NOT crash - it ran cleanly to the full endTime=1e-5s.

### QoI comparison at matched absolute time revealed a large, initially
### unexplained discrepancy

Re-extracting the fine mesh's stagnation p/T from its probeStagnation
history at the same absolute time as production/coarse's crash point
(t~2.60-2.65e-6s, rather than the fine mesh's own t=1e-5s endpoint) still
showed p_stag ~33,000 Pa on the fine mesh vs ~49,000 Pa on
production/coarse - a 25-39% discrepancy across every QoI, far too large
for genuine grid-refinement sensitivity across a modest sqrt(2) h0
refinement. This disproved the initial working hypothesis (that the
discrepancy was purely a "still relaxing, sampled at different post-ramp
elapsed times" artifact) - matching absolute time barely moved the
fine-mesh numbers.

### Root cause isolated: ramp-start Mach, not grid density

A controlled confound-isolation test was performed: the unchanged
production mesh (byte-identical dictionaries confirmed via `diff -rq`
against the original production case in constant/, system/, 0/p, 0/T -
only 0/U's ramp-start values differed) was rerun with its ramp-start
changed from M=5 to M=4, holding everything else fixed. This single
change moved p_stag from ~49,000 Pa to ~32,950 Pa - landing within ~0.3%
of the fine mesh's own M=4-start value (~33,063 Pa). **Confirmed: the
ramp's starting Mach number, not mesh density, was the dominant driver of
the original discrepancy.** The flow retains a strong, ramp-trajectory-
dependent transient state for microseconds after reaching the M=7
target - it does not depend only on "how long since the ramp ended."

This also reframes the earlier coarse/production crash-timing
"agreement" (both ~2.63-2.64e-6s): it demonstrated that *same ramp-start
Mach produces similar crash timing*, not that crash timing is
mesh-independent in general.

### Resolution: all three densities standardized on an M=4-start ramp

- Production and fine were already available at M=4-start (from the
  confound test and the earlier bisection respectively).
- Coarse's own M=4 cold-start tolerance was verified directly (not
  assumed from its M=5 stability) - it ran cleanly to endTime=1e-5s with
  no crash, consistent with production and fine.
- Continuous forebody-pressure probes were added to all three cases (5
  wall_cone stations, exact cell centroids computed per-mesh from
  constant/polyMesh data at the mid-wedge-plane z=0, since the earlier
  extraction attempt found the relevant field-directory timesteps had
  already been deleted by purgeWrite=20 by the time each run reached its
  endTime). All three cases were rerun fresh from t=0 with full probe
  coverage (probeStagnation + probeForebody); none crashed.

### Final matched-ramp, matched-time (t~2.62e-6s) three-way comparison

| QoI | Coarse | Production | Fine |
|---|---|---|---|
| p_stag (Pa) | 32,714.3 | 33,005.1 | 33,087.1 |
| T_stag (K) | 462.11 | 409.80 | 374.91 |

p_stag: clean, monotonic, shrinking increments (291 Pa, then 82 Pa) -
the signature of genuine grid convergence.
T_stag: also monotonic but far more sensitive (~19% total spread vs
~1.1% for p_stag) - consistent with near-wall temperature-gradient
resolution against the isothermal 300K wall being much more
h0-sensitive than the largely-inviscid shock-layer pressure.

Forebody surface pressure at the 5 wall_cone stations: monotonic at the
nose-adjacent and base-adjacent stations; NOT monotonic at the 3
mid-cone stations. Forebody surface temperature: monotonic at all 5
stations, same direction/magnitude as T_stag.

### Richardson extrapolation (refinement ratio confirmed sqrt(2) between
### all three levels)

- p_stag: observed order p=3.65, extrapolated (h->0) value 33,119.3 Pa,
  GCI(fine)=0.12% - genuinely well-converged, defensible verification
  result.
- T_stag: observed order p=1.17 (well below the schemes' nominal spatial
  order), extrapolated value 305.0 K, GCI(fine)=23.3% - NOT trustworthy.
  Diagnosed as a consequence of sampling a still-transient state
  (~2.55e-6s post-ramp): classical Richardson/GCI theory assumes a
  converged spatial error field, which does not strictly hold for a
  transient snapshot. The near-wall thermal boundary layer has likely
  not yet reached a self-similar profile at this sampled instant,
  particularly on the coarser meshes.

**Decision:** p_stag is reported as verified (GCI 0.12%). T_stag and the
mid-cone forebody-pressure non-monotonicity are documented as a
pre-asymptotic-temporal-state limitation of this verification exercise,
not force-fit into a Richardson extrapolation the data doesn't support.
Per the finalized Project 01 completion scope (see below), this is not
investigated further with additional ramp-strategy or later-sampling-time
experiments - the marginal research value does not justify further time
against the project's actual research question (nose-radius effects,
not yet addressed by any of this verification work).

### Base/wake re-confirmation: M=4-start delays, does not eliminate, the
### continuum-breakdown crash

Since none of the three M=4-start runs crashed by their endTime=1e-5s
(compared to production/coarse's original M=5-start crash at
t~2.63-2.64e-6s), directly checked whether this indicated the base/wake
limitation had been avoided rather than delayed - field inspection
(same script/method as the original vacuum-condition discovery) at
production's final M=4-start timestep (t=9.99952e-06s) found base-wall
minimum p=0.368 Pa (~0.03% of freestream p_inf=1197 Pa) at x=0.416655
(the base wall x-location) - the same near-vacuum regime as the original
crash (p~0.035 Pa), roughly 10x less severe and not yet fatal, but on
the identical trajectory. **Conclusion: the M=4-start ramp delays the
base/wake continuum-breakdown further (roughly 4x more simulated time
survived); it does not eliminate the underlying physical limitation.**
This is a second, independent confirmation of the original base/wake
finding via a completely different ramp strategy - it reinforces rather
than overturns the decision (documented above, commit c8c70d5) to drop
total drag from Project 01's scope.

### Status / scope going forward

Grid convergence study is complete for p_stag (verified, GCI 0.12%);
T_stag and mid-cone forebody-p are documented as pre-asymptotic
limitations rather than further investigated. This closes the
verification stage. Per a finalized project-completion scope (Harsh's
explicit decision, prompted by a pace/progress check-in), the remaining
Project 01 work is scoped tightly: (1) validation against Fay-Riddell
(stagnation heat flux) and Billig (shock stand-off) for the baseline
geometry, one comparison each, no iterative refinement chasing; (2) a
2-geometry nose-radius comparison (baseline R_n=0.05m + one contrast
radius, TBD) using a Python driver script to reproduce the proven
O-grid/M=4-ramp case-setup methodology rather than manual step-by-step
setup; (3) physical interpretation and engineering conclusion; (4) final
documentation and GitHub packaging.

## 2026-09-29 — Major Correction: Grid-Convergence Study Was Run at M=4/M=5, Not M=7; M=7 Achieved via Field-Based Reinitialization

### Summary

A post-commit sanity check against classical theory revealed that every
run in this project claiming to represent M=7 flow - including the
entire grid-convergence study committed as 7c8d54a - actually contained
M=4 or M=5 gas around the body, not M=7. The root cause, resolution
attempts, and final outcome are documented below. This corrects, but
does not retract the underlying methodology value of, the
grid-convergence study: the O-grid mesh, the checkMesh verification,
and the p_stag Richardson/GCI analysis remain valid AS A MESH-INDEPENDENCE
STUDY, but the physical regime they were verified at was M=4/M=5, not
the project's stated M=7 freestream condition. This must be corrected
before any comparison against Fay-Riddell or Billig (both M=7
correlations) is attempted.

### How the error was found

Immediately after committing the grid-convergence study, a long
restart of the production M=4-start case (from its existing t~1e-5s
state out to t=1e-4s, ~8h wall time) was run specifically to check
whether p_stag was approaching the theoretical M=7 Rayleigh-Pitot
stagnation pressure (63.55 x p_inf = 76,072 Pa) as simulated time
increased. Instead, p_stag moved AWAY from theory: 43% of the Pitot
value at t=2.6e-6s, falling to 31% by t=1e-4s, with a -5% to -8% drift
over the final 20 microseconds - the opposite of convergence.

An independent Taylor-Maccoll calculation of the sharp 15-degree cone's
surface pressure at M=7 (shock angle 18.4 deg, surface p/p_inf=6.07)
was compared against the measured forebody wall pressures (~2.8-3.3
p_inf) - roughly half the theoretical value and still falling. Both the
stagnation-point and forebody-surface deficits, independently, matched
Mach 4 theory almost exactly instead (Pitot 21.07 p_inf vs. measured
19.7-22.7 p_inf; cone surface 2.80 p_inf vs. measured 2.8-3.3 p_inf).

### Root cause

The Mach-ramp startup strategy (see Shakedown A/B and the production
run entries above) only changes the velocity BOUNDARY CONDITION at the
upstream inlet over 5e-8s. The `0/U` internalField - the initial
condition for the entire interior of the domain - was left uniform at
the ramp's STARTING velocity (1206.72 m/s = M4, or 1508.4 m/s = M5,
depending on the case). The new M=7 gas entering at the inlet has to
physically travel from x=-0.30 (the inlet plane) to the body at x=0
before the body ever experiences M=7 conditions. At U~2112 m/s this
transit takes at least 1.4e-4s; the actual front moved slower
(~1350 m/s observed). Every run to date, including all three
grid-convergence densities, was stopped (by a crash or an endTime) well
before the M=7 front reached the body - the entire domain the body
"saw" was still at the ramp's start-Mach conditions the whole time.

This reframes the earlier "ramp-start-Mach confound" finding (this
log, 2026-09-27 entry): it was not a confound between two representations
of the same M=7 flow, it was a comparison between two different,
genuinely distinct STEADY flow regimes (M=4 gas vs M=5 gas) that
happened to look like a Mach-ramp artifact because both were mislabeled
as "M=7". The grid-convergence study's p_stag Richardson/GCI result
(GCI=0.12%) is a legitimate verification of mesh-independence AT
WHATEVER CONDITION WAS ACTUALLY SIMULATED (M=4-ish gas, given the
matched M=4-start ramp used for that comparison) - it is not invalid,
but it must be relabeled, and it cannot be used as an M=7 validation
baseline as previously assumed.

### Resolution attempts (coarse mesh only, before replicating on
### production/fine)

Three approaches were considered: (B) surgically reinitialize the
far-field interior to true M=7 conditions so the transit distance
collapses to a few cm instead of 0.30m; (C) shrink the physical domain
and remesh so transit time is inherently short; (E) change the
project's locked-in freestream condition to M=4 (a research-scope
decision, not attempted). B was chosen first as the cheapest to test.

**B, attempt 1 (geometric protect-cylinder) - FAILED, new crash mode.**
`setFields`/`topoSet` were used to overwrite p/T/U to M=7 values in all
cells outside a protect-cylinder (x=-0.015 to 0.43, r=0.16) around the
body. Two dictionary bugs were found and fixed in the process
(`cellToCell` is not a valid `setFieldsDict` region source; the
correct source is `cellSet`; and `defaultFieldValues` unconditionally
overwrites the ENTIRE domain before `regions` is applied, so setting
it equal to the intended region values masked a real region-application
failure on the first attempt). Once genuinely fixed and verified
per-cell (via a new script, verify_setfields.py), a trial run crashed
in ~1.2e-5s of simulated time via the usual sigFpe/hePsiThermo
mechanism. Diagnosis: the protect-cylinder boundary sits right at the
base/wake edge (base at x=0.4166), so genuinely near-vacuum protected
cells (p as low as 0.34 Pa) sat immediately adjacent to reinitialized
freestream cells at 1197 Pa - a ~3500x artificial pressure
discontinuity, a new self-inflicted numerical stiffness distinct from
any previously-documented mechanism.

**B, attempt 2 (field-based selection) - SUCCEEDED for ~9.4e-5s,
new distinct instability found at the end.** Replaced the geometric
cylinder with a `fieldToCell` selection on p (cells within 1192-1202 Pa
of freestream, i.e. genuinely undisturbed pre-shock cells), changing
ONLY U in those cells (p, T are already correct there by construction,
so no discontinuity is possible - a `setFields`-cannot-preserve-cells
limitation was also discovered and worked around by writing a
dedicated read-modify-write Python script, reinit_U_only.py, instead of
using setFields at all for the final approach). An initial pass of this
selection picked up 9238 cells including 5749 near the body; direct
inspection showed most were legitimate freestream pockets just outside
the thin oblique shock layer along the cone flank, but a further
x<=0.40 restriction was applied (Harsh's decision) to exclude the
ambiguous base/wake-adjacent portion entirely, giving a final selection
of 7835 cells.

This run SURVIVED to t=1.0488e-4s (~9.4e-5s past the reinit, ~38 min
wall time, ~8x longer than attempt 1) and produced genuine M=7 physics:
p_stag reached 104% of the theoretical Pitot value within 10
microseconds of the reinit and oscillated 89-104% of Pitot for the rest
of the run; stagnation temperature matched the theoretical M=7 value
(~2446K) to within 1% at the final timestep (2416K measured). This is
strong, independent, positive confirmation the field-based reinit
approach works.

The run's crash showed a SECOND new instability, distinct from the
base wall (which was also present, and even more extreme than before -
p down to 4.7e-4 Pa - consistent with, not contradicting, the
documented base/wake limitation): a cell just upstream of the nose tip
(x=-0.0083, r=0.0103) showed a smooth, monotonic decline in p and T
across all ~20 available snapshots (p: 222 -> 0.097 Pa; T: 41.3 ->
0.018 K over ~9e-8s), with Ux/Uy also drifting steadily - the signature
of a genuine, locally runaway numerical expansion, not noise or a
last-instant artifact. A restart from the earliest surviving snapshot
(where the decline was already underway) with a short target endTime
reproduced the crash within 2e-9s of the original crash time -
confirming this is a real, deterministic instability tied to the
reinit interface near the nose, not a fluke.

### Decision (Harsh's explicit call)

Per an agreed test-then-decide protocol: the reproducibility test (J)
was run once; since it reproduced the crash rather than surviving
further, the decision moved to option K: accept the ~9.4e-5s window as
sufficient positive evidence that the field-based reinit produces
genuine M=7 physics, do not chase the nose-region instability to a
stable endpoint, and use the settled portion of this run (t~1.03e-4s to
the crash at 1.0488e-4s, where p_stag/T_stag/forebody-p all show flat,
non-drifting trends with no sign of the nose anomaly reaching them) as
the coarse-mesh baseline for validation. The final values: p_stag
67,964 Pa (89.3% of the theoretical Pitot value), T_stag 402.2K,
forebody stations 8,915 / 5,229 / 7,826 / 7,788 / 7,788 Pa. The
remaining ~11% shortfall in p_stag against theory is documented as an
open, unresolved uncertainty (possibly further settling needed, a
residual effect of only partially reinitializing the domain, or a
mesh-density effect) rather than investigated further, consistent with
the project's finalized completion scope.

### Consequences / what needs correcting going forward

- The grid-convergence study (7c8d54a) verified mesh-independence at an
  M=4/M=5-ish condition, not M=7 as originally labeled. Its p_stag
  Richardson/GCI result stands as a verification-methodology
  demonstration but cannot be used as-is as the M=7 validation baseline.
- The same field-based reinitialization approach (fieldToCell on p,
  U-only reinit via reinit_U_only.py, x<=0.40 wake exclusion) needs to
  be replicated on the production and fine meshes before a genuine,
  matched, mesh-independent M=7 comparison can be attempted.
- PROJECT_DEFINITION.md's Status section needs updating to reflect that
  M=7 has now been achieved (with a documented startup-method
  limitation), correcting the implicit assumption in prior entries that
  the Mach-ramp alone was sufficient.
- Validation against Fay-Riddell/Billig can now proceed using the
  settled-window values above as the coarse-mesh datapoint, once
  production/fine mesh equivalents exist.
