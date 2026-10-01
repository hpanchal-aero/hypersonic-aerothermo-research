#!/usr/bin/env python3
"""
Nose-tip wall heat flux with TRUE wall-normal distances. Run from the case
directory, after
  postProcess -func writeCellCentres -time <t>
has written C into the timestep directory.

For the N wall_nose faces closest to the axis (smallest face-centre y):
  face centre (area-weighted), outward unit normal, owner cell, normal
  distance d = (fc - C_owner) . n, T_owner, and
  q1 = k_w (T_owner - Tw) / d           (first-order, one cell)
For the tip face only, also a second-order estimate: fit
  T(s) = Tw + a s + b s^2  through the two cells at owner and owner+1
  (checked to lie along the face normal), q2 = k_w * a.

k_w is printed for (a) modified Eucken (OpenFOAM sutherlandTransport form,
NOT verified against the v11 source) and (b) constant Pr = 0.71.

Usage: /usr/bin/python3 wall_flux_true.py <timestep> [N=5]
"""
import re
import sys
import numpy as np

MU_AS, MU_TS = 1.458e-6, 110.4
CP, W = 1005.0, 28.96
RGAS = 8314.47 / W
TW = 300.0


def mu(T):
    return MU_AS * T ** 1.5 / (T + MU_TS)


def read_points(path):
    content = open(path).read()
    nums = re.findall(r'\(([^)]+)\)', content.split("(", 1)[1])
    return np.array([[float(x) for x in n.split()] for n in nums])


def read_faces(path):
    lines = open(path).readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().isdigit())
    n = int(lines[start].strip())
    faces, i, count = [], start + 2, 0
    while count < n:
        line = lines[i].strip()
        if line and line[0].isdigit():
            faces.append([int(x) for x in line.split('(')[1].split(')')[0].split()])
            count += 1
        i += 1
    return faces


def read_owner(path):
    lines = open(path).readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().isdigit())
    n = int(lines[start].strip())
    vals, i, count = [], start + 2, 0
    while count < n:
        line = lines[i].strip()
        if line and (line[0].isdigit() or line[0] == '-'):
            vals.append(int(line))
            count += 1
        i += 1
    return np.array(vals)


def patch_range(path, name):
    content = open(path).read()
    m = re.search(name + r'\s*\{[^}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);',
                  content, re.DOTALL)
    return int(m.group(2)), int(m.group(1))


def read_scalar(path):
    t = open(path).read()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', t)
    n = int(m.group(1))
    v = np.array(t[m.end():].split(')')[0].split(), dtype=float)
    assert len(v) == n
    return v


def read_vector(path):
    t = open(path).read()
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(', t)
    n = int(m.group(1))
    v = re.findall(r'\(([^()]+)\)', t[m.end():])[:n]
    return np.array([[float(a) for a in s.split()] for s in v])


def face_geom(pts):
    """Area-weighted centre and area vector (triangle fan about vertex mean)."""
    c0 = pts.mean(axis=0)
    S = np.zeros(3)
    fc = np.zeros(3)
    A = 0.0
    for k in range(len(pts)):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        s = 0.5 * np.cross(a - c0, b - c0)
        area = np.linalg.norm(s)
        S += s
        fc += area * (a + b + c0) / 3.0
        A += area
    return fc / A, S


t = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5

points = read_points("constant/polyMesh/points")
faces = read_faces("constant/polyMesh/faces")
owner = read_owner("constant/polyMesh/owner")
start, nf = patch_range("constant/polyMesh/boundary", "wall_nose")
T = read_scalar(f"{t}/T")
C = read_vector(f"{t}/C")
assert len(T) == len(C)

cv = CP - RGAS
kw_e = mu(TW) * cv * (1.32 + 1.77 * RGAS / cv)
kw_p = mu(TW) * CP / 0.71

rows = []
for fid in range(start, start + nf):
    fc, S = face_geom(points[faces[fid]])
    n = S / np.linalg.norm(S)          # OpenFOAM: boundary face normals point out of the domain
    o = owner[fid]
    d = float(np.dot(fc - C[o], n))    # positive if C[o] is inside the domain
    rows.append((fc[1], fid, o, fc, n, d))
rows.sort(key=lambda r: r[0])

print(f"time {t}: wall_nose has {nf} faces (start {start}); {N} faces nearest the axis")
print(f"k_w Eucken = {kw_e:.5f} (Pr {CP*mu(TW)/kw_e:.3f}), k_w Pr0.71 = {kw_p:.5f} W/m/K")
print(f"{'face':>6} {'owner':>6} {'fc_x':>11} {'fc_y':>11} {'n_x':>8} {'n_y':>8} "
      f"{'d (m)':>11} {'T (K)':>8} {'q1 Eucken':>11} {'q1 Pr.71':>11}")
for _, fid, o, fc, n, d in rows[:N]:
    print(f"{fid:6d} {o:6d} {fc[0]:11.3e} {fc[1]:11.3e} {n[0]:8.4f} {n[1]:8.4f} "
          f"{d:11.3e} {T[o]:8.2f} {kw_e*(T[o]-TW)/d:11.0f} {kw_p*(T[o]-TW)/d:11.0f}")

_, fid, o, fc, n, d1 = rows[0]
print(f"\nTIP FACE {fid}: owner cell {o}, d1 = {d1:.4e} m, T1 = {T[o]:.2f} K")
o2 = o + 1
d2 = float(np.dot(fc - C[o2], n))
lateral = np.linalg.norm((C[o2] - fc) - np.dot(C[o2] - fc, n) * n)
print(f"next cell {o2}: d2 = {d2:.4e} m, T2 = {T[o2]:.2f} K, "
      f"lateral offset from face normal = {lateral:.2e} m")
if d2 > d1 > 0:
    M = np.array([[d1, d1 ** 2], [d2, d2 ** 2]])
    rhs = np.array([T[o] - TW, T[o2] - TW])
    a, b = np.linalg.solve(M, rhs)
    print(f"quadratic fit: dT/ds at wall = {a:.4e} K/m, curvature b = {b:.3e}")
    print(f"q2 second-order, Eucken : {kw_e*a:12.0f} W/m2")
    print(f"q2 second-order, Pr 0.71: {kw_p*a:12.0f} W/m2")
else:
    print("distances not increasing along the normal; skipping quadratic fit")
print("\nReference (scratch Fay-Riddell, Le=1, Pr 0.71): ~916,000 W/m2")
