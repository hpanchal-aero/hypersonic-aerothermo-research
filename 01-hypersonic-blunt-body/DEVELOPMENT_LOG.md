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
