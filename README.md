# Computational Aerospace Research Program

Harsh Panchal — Aerospace Engineering student/researcher

## Purpose

This repository is a research-oriented computational aerospace program, separate
from conventional CFD/FEA showcase portfolios. The goal is not to produce
impressive-looking simulations, but to investigate real engineering problems,
formulate hypotheses, perform credible computational studies, understand the
underlying physics, and arrive at defensible engineering conclusions.

Each project follows the same methodology:
Engineering problem → Research question → Hypothesis → Theory →
Computational model → Verification → Validation → Parametric investigation →
Physical interpretation → Engineering decision → Limitations
## Research Interests

Hypersonic aerodynamics, aerothermodynamics, heat transfer, thermal protection
systems, fluid–structure interaction, aeroelasticity, aerospace structures,
computational fluid dynamics, computational mechanics, aerospace propulsion,
high-speed flow — with a particular interest in the interaction between fluid
flow, thermal physics, structures, and propulsion.

## Computational Toolchain

| Category | Tools |
|---|---|
| CFD | OpenFOAM 11, ANSYS Fluent |
| FEA / Structural mechanics | CalculiX, ANSYS Mechanical |
| Geometry | OpenSCAD, Fusion 360 |
| Meshing | Gmsh |
| Programming / Analysis | Python (NumPy, SciPy, Pandas, Matplotlib, PyVista) |
| Visualization | PyVista, Matplotlib, ParaView (secondary) |
| Environment | Windows + WSL2, Ubuntu 24.04 LTS |

## Research Philosophy

Correctness + Reproducibility + Verification + Validation + Physical
Understanding + Engineering Insight — not maximum complexity. A simple problem
investigated rigorously is better than a complicated problem investigated
poorly. Negative results are documented honestly; artificial fixes that mask
underlying physics or numerics are explicitly rejected in favor of transparent,
evidence-based diagnosis.

## The 12 Projects

| # | Project | Research Area | Status |
|---|---|---|---|
| 01 | Hypersonic Blunt Body | Hypersonic aerodynamics / aerothermodynamics | **In progress** |
| 02 | Shock–Boundary-Layer Interaction Control | Hypersonic aerodynamics / flow control | Planned |
| 03 | Hypersonic Boundary-Layer Transition and Heating | Hypersonic boundary layers / aerothermodynamics | Planned |
| 04 | Thermal Protection System Mass Optimization | Aerothermodynamics / TPS | Planned |
| 05 | Active / Effusion Cooling of Hypersonic Structures | Aerothermodynamics / thermal management | Planned |
| 06 | Hypersonic Aerothermoelastic Panel | Fluid–structure interaction / aerothermoelasticity | Planned |
| 07 | Flexible Hypersonic Control Surface | FSI / aeroelasticity | Planned |
| 08 | Scramjet Isolator Shock-Train Dynamics | Hypersonic propulsion | Planned |
| 09 | Scramjet Inlet–Isolator–Combustor | Hypersonic propulsion | Planned |
| 10 | Hypersonic Blunt-Body Aerothermal Optimization | Hypersonic vehicle design / optimization | Planned |
| 11 | Aero-Thermo-Structural Optimization | Multiphysics / FSI / MDO | Planned |
| 12 | Integrated Hypersonic System | Integrated aerospace systems | Planned |

Each project is independently executable — no project depends on another's
files, though methodology and lessons learned carry forward. Difficulty
broadly progresses: Phase 1 (hypersonic physics, 01–03) → Phase 2
(aerothermodynamics, 04–05) → Phase 3 (FSI, 06–07) → Phase 4 (propulsion,
08–09) → Phase 5 (multidisciplinary design, 10–12).

## Project 01 — Current Status

Hypersonic blunt-body aerodynamics and aerothermal characterization at Mach 7.
See [`01-hypersonic-blunt-body/PROJECT_DEFINITION.md`](01-hypersonic-blunt-body/PROJECT_DEFINITION.md)
and [`01-hypersonic-blunt-body/CASE_SPECIFICATION.md`](01-hypersonic-blunt-body/CASE_SPECIFICATION.md)
for the full specification, and
[`01-hypersonic-blunt-body/DEVELOPMENT_LOG.md`](01-hypersonic-blunt-body/DEVELOPMENT_LOG.md)
for the running development narrative.
