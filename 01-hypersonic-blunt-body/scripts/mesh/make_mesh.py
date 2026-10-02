#!/usr/bin/env python3
"""
Nose-radius sweep driver, stage 1: geometry + mesh for ONE nose radius.

Derives <mesh-root>/<name>/<name>.geo from mesh/production/production.geo by
replacing the single line "R_n = 0.05;" and appending an outFarfield[]
bounding-box diagnostic. Everything else (h0, growth ratio, divisions,
collar/buffer, fillet, far-field sizing) is unchanged; the domain extents
scale with R_n through the expressions already in the .geo.

Steps: gmsh (-3 -format msh2) -> check outFarfield[6,7,8] are outlet /
farfield_outer / farfield_upstream -> gmshToFoam (minimal placeholder
controlDict; a copied production controlDict made gmshToFoam segfault) ->
retype_wedge_patches.py -> checkMesh -> report.

Requires OpenFOAM 11 sourced (gmshToFoam, checkMesh on PATH).
Refuses to overwrite existing output directories.

Usage:
  /usr/bin/python3 scripts/mesh/make_mesh.py --rn 0.05 --name rn0500
      [--mesh-root DIR] [--case-root DIR]
      [--reference-msh FILE] [--reference-polymesh DIR]
"""
import argparse
import filecmp
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
BASE_GEO = PROJECT / "mesh" / "production" / "production.geo"
RETYPE = PROJECT / "scripts" / "mesh" / "retype_wedge_patches.py"
BASE_RN_LINE = "R_n = 0.05;"
CHORD_N3 = "N3 = newl; Line(N3)   = {p_nose_tip_off, p_tangent_off};"
ARC_N3 = "N3 = newl; Circle(N3) = {p_nose_tip_off, p_nose_center, p_tangent_off};"
CHORD_NBUF = "NbufOuter  = newl; Line(NbufOuter)  = {p_nose_tip_off_buf, p_tangent_off_buf};"
ARC_NBUF = "NbufOuter  = newl; Circle(NbufOuter)  = {p_nose_tip_off_buf, p_nose_center, p_tangent_off_buf};"

# Constants of the production recipe (read from production.geo) used only to
# predict the expected domain extents for the patch-index check.
THETA = 15.0 * math.pi / 180.0
R_B = 0.15
H0, RATIO, NWN = 5.607e-6, 1.12, 51
T_BUF, MARGIN = 0.018, 0.020

DIAG = '''
// ---- Diagnostic: verify outFarfield[] indices for THIS mesh ----
Printf("=== outFarfield[] has %g entries ===", #outFarfield[]);
For i In {2:#outFarfield[]-1}
  bb[] = BoundingBox Surface{outFarfield[i]};
  Printf("outFarfield[%g] = Surface %g | x=[%.6f,%.6f]  y=[%.6f,%.6f]", i, outFarfield[i], bb[0], bb[3], bb[1], bb[4]);
EndFor
'''

PLACEHOLDER_CONTROLDICT = '''FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}
application     rhoCentralFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
'''


def run(cmd, cwd, logfile):
    with open(logfile, "w") as f:
        r = subprocess.run([str(c) for c in cmd], cwd=str(cwd),
                           stdout=f, stderr=subprocess.STDOUT)
    return r.returncode


def expected_extents(rn):
    x_t = rn * (1 - math.sin(THETA))
    r_t = rn * math.cos(THETA)
    base_x = x_t + (R_B - r_t) / math.tan(THETA)
    delta_star = H0 * (RATIO ** NWN - 1) / (RATIO - 1)
    x_outlet = base_x + delta_star + T_BUF + MARGIN
    return {"x_up": -6 * rn, "r_out": 15 * rn, "x_outlet": x_outlet, "base_x": base_x}


def check_diagnostic(log_text, ex):
    pat = re.compile(r"outFarfield\[(\d+)\] = Surface (\d+) \| "
                     r"x=\[([^,\]]+),([^\]]+)\]\s+y=\[([^,\]]+),([^\]]+)\]")
    found = {}
    for m in pat.finditer(log_text):
        found[int(m.group(1))] = tuple(float(m.group(k)) for k in (3, 4, 5, 6))
    print("  outFarfield diagnostic (index: xmin xmax ymin ymax):")
    for i in sorted(found):
        print(f"    [{i}]: " + " ".join(f"{v:.6f}" for v in found[i]))
    ok = True
    tol = 1e-6
    if not all(i in found for i in (6, 7, 8)):
        print("  FAIL: diagnostic lines for indices 6, 7, 8 not all found")
        return False
    xmin, xmax, ymin, ymax = found[6]
    if abs(xmin - ex["x_outlet"]) > tol or abs(xmax - ex["x_outlet"]) > tol:
        print(f"  FAIL: [6] is not the outlet plane at x={ex['x_outlet']:.6f}")
        ok = False
    xmin, xmax, ymin, ymax = found[7]
    if (abs(ymax - ex["r_out"]) / ex["r_out"] > 0.005 or abs(xmin - ex["x_up"]) > tol
            or abs(xmax - ex["x_outlet"]) > tol):
        print(f"  FAIL: [7] is not the outer boundary (r_out={ex['r_out']:.6f})")
        ok = False
    xmin, xmax, ymin, ymax = found[8]
    if abs(xmin - ex["x_up"]) > tol or abs(xmax - ex["x_up"]) > tol:
        print(f"  FAIL: [8] is not the upstream plane at x={ex['x_up']:.6f}")
        ok = False
    return ok


def grab(pattern, text, cast=float):
    m = re.search(pattern, text)
    return cast(m.group(1).rstrip(".")) if m else None


def parse_checkmesh(path):
    txt = Path(path).read_text()
    rep = txt[txt.rindex("Mesh stats"):]
    stars = re.findall(r"^\s*\*\*\*(.*)$", rep, re.M)
    patches = {m.group(1): int(m.group(2)) for m in
               re.finditer(r"^\s+(\w+)\s+(\d+)\s+\d+\s+ok", rep, re.M)}
    return {
        "cells": grab(r"cells:\s+(\d+)", rep, int),
        "hexahedra": grab(r"hexahedra:\s+(\d+)", rep, int),
        "prisms": grab(r"prisms:\s+(\d+)", rep, int),
        "min_volume": grab(r"Min volume =\s+([\d.eE+-]+)", rep),
        "max_aspect": grab(r"Max aspect ratio =\s+([\d.eE+-]+)", rep),
        "nonorth_max": grab(r"Mesh non-orthogonality Max:\s+([\d.eE+-]+)", rep),
        "nonorth_avg": grab(r"average:\s+([\d.eE+-]+)", rep),
        "n_over_70": grab(r"non-orthogonal \(> 70 degrees\) faces:\s+(\d+)", rep, int),
        "max_skew": grab(r"Max skewness =\s+([\d.eE+-]+)", rep),
        "failed": grab(r"Failed (\d+) mesh checks", rep, int) or 0,
        "unexpected_failures": [s.strip() for s in stars if "Wedge patch" not in s],
        "patch_faces": patches,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rn", type=float, required=True)
    ap.add_argument("--name", default=None)
    ap.add_argument("--mesh-root", default=str(PROJECT / "mesh"))
    ap.add_argument("--case-root", default=str(PROJECT / "openfoam"))
    ap.add_argument("--nose-arcs", action="store_true",
                    help="make the nose collar and buffer outer edges circular arcs")
    ap.add_argument("--reference-msh", default=None)
    ap.add_argument("--reference-polymesh", default=None)
    a = ap.parse_args()

    rn = a.rn
    if not (0.01 < rn < 0.14):
        sys.exit(f"R_n={rn} outside the supported range 0.01-0.14 m")
    name = a.name or f"rn{round(rn * 1e4):04d}"
    geo_dir = Path(a.mesh_root) / name
    case_dir = Path(a.case_root) / name
    for d in (geo_dir, case_dir):
        if d.exists():
            sys.exit(f"REFUSING to overwrite existing directory: {d}")
    for tool in ("gmshToFoam", "checkMesh"):
        if shutil.which(tool) is None:
            sys.exit(f"{tool} not on PATH: source /opt/openfoam11/etc/bashrc first")

    ok = True
    ex = expected_extents(rn)
    print(f"R_n = {rn} m  name = {name}")
    print(f"  expected: base x = {ex['base_x']:.6f}, x_upstream = {ex['x_up']:.4f}, "
          f"r_outer = {ex['r_out']:.4f}, x_outlet = {ex['x_outlet']:.6f}")

    # 1. geo
    s = BASE_GEO.read_text()
    assert s.count(BASE_RN_LINE) == 1, "R_n line not found exactly once in production.geo"
    rn_str = f"{rn:.10g}"
    s = s.replace(BASE_RN_LINE, f"R_n = {rn_str};")
    arcs_note = ""
    if a.nose_arcs:
        assert s.count(CHORD_N3) == 1 and s.count(CHORD_NBUF) == 1, "chord lines not found exactly once"
        s = s.replace(CHORD_N3, ARC_N3).replace(CHORD_NBUF, ARC_NBUF)
        arcs_note = "// ALSO: N3 and NbufOuter are circular arcs about p_nose_center (--nose-arcs).\n"
    header = (f"// GENERATED by scripts/mesh/make_mesh.py from mesh/production/production.geo\n"
              f"// Only change: R_n = {rn_str}; (production: 0.05). Appended: outFarfield[] diagnostic.\n"
              f"// Do not edit by hand.\n")
    geo_dir.mkdir(parents=True)
    geo = geo_dir / f"{name}.geo"
    geo.write_text(header + arcs_note + s + DIAG)
    print(f"  wrote {geo}")

    # 2. gmsh
    msh = geo_dir / f"{name}.msh"
    glog = geo_dir / f"{name}_gmsh_log.txt"
    rc = run(["/usr/bin/gmsh", "-3", geo, "-format", "msh2", "-o", msh], geo_dir, glog)
    gtxt = glog.read_text()
    m = re.search(r"Info\s*:\s*(\d+) nodes (\d+) elements", gtxt)
    print(f"  gmsh exit {rc}; nodes/elements: {m.groups() if m else 'NOT FOUND'}")
    if rc != 0 or not m or not msh.exists():
        sys.exit("gmsh failed: see " + str(glog))

    # 3. patch-index check
    if not check_diagnostic(gtxt, ex):
        ok = False
        print("  PATCH-INDEX CHECK FAILED: patch assignment in the .geo is not valid for this radius")

    # 4. OpenFOAM mesh
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "system" / "controlDict").write_text(PLACEHOLDER_CONTROLDICT)
    rc = run(["gmshToFoam", msh], case_dir, case_dir / "gmshToFoam_log.txt")
    bpath = case_dir / "constant" / "polyMesh" / "boundary"
    print(f"  gmshToFoam exit {rc}; boundary file exists: {bpath.exists()}")
    if rc != 0 or not bpath.exists():
        sys.exit("gmshToFoam failed: see " + str(case_dir / "gmshToFoam_log.txt"))
    rc = subprocess.run(["/usr/bin/python3", str(RETYPE), str(bpath)],
                        capture_output=True, text=True)
    print("  retype: " + " | ".join(l for l in rc.stdout.splitlines() if "substitution" in l)
          + f" (exit {rc.returncode})")
    if rc.returncode != 0:
        sys.exit("wedge retyping failed")
    run(["checkMesh"], case_dir, case_dir / "checkMesh_log.txt")
    st = parse_checkmesh(case_dir / "checkMesh_log.txt")

    print("  checkMesh:")
    for k in ("cells", "hexahedra", "prisms", "min_volume", "max_aspect",
              "nonorth_max", "nonorth_avg", "n_over_70", "max_skew", "failed"):
        print(f"    {k}: {st[k]}")
    print(f"    patch faces: {st['patch_faces']}")
    if st["unexpected_failures"]:
        ok = False
        print(f"    UNEXPECTED check failures: {st['unexpected_failures']}")
    if st["min_volume"] is None or st["min_volume"] <= 0:
        ok = False
        print("    FAIL: non-positive minimum cell volume")

    # 5. optional references
    if a.reference_msh:
        same = filecmp.cmp(msh, a.reference_msh, shallow=False)
        print(f"  .msh vs reference: {'IDENTICAL' if same else 'DIFFERENT'}")
        ok = ok and same
    if a.reference_polymesh:
        for f in ("points", "faces", "owner", "neighbour", "boundary"):
            same = filecmp.cmp(case_dir / "constant" / "polyMesh" / f,
                               Path(a.reference_polymesh) / f, shallow=False)
            print(f"  polyMesh/{f} vs reference: {'IDENTICAL' if same else 'DIFFERENT'}")
            ok = ok and same

    print("PIPELINE OK" if ok else "PIPELINE HAS PROBLEMS (see above)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
