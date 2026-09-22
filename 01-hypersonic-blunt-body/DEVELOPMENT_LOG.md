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
