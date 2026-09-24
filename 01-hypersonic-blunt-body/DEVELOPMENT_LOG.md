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
