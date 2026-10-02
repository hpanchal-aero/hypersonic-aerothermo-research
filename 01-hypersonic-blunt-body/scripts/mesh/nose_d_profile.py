#!/usr/bin/env python3
"""
Wall-normal distance d from each wall_nose face to its owner cell centre,
along the nose arc. Mesh only (no solution fields). Run from the case
directory after
    mkdir -p 0 && postProcess -func writeCellCentres -time 0
has written 0/C.

Faces are sorted from the axis outward. Prints every STEP-th face with the
arc angle atan2(hypot(n_y, n_z), n_x) of its normal, then a summary: d at
the tip face, minimum d and its angle, d at the last face, the min/tip
ratio, and the number of faces with d <= 0.

Usage: /usr/bin/python3 nose_d_profile.py [STEP=5] [CTIME=0]
"""
import math
import re
import sys

import numpy as np


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


step = int(sys.argv[1]) if len(sys.argv) > 1 else 5
ctime = sys.argv[2] if len(sys.argv) > 2 else "0"

points = read_points("constant/polyMesh/points")
faces = read_faces("constant/polyMesh/faces")
owner = read_owner("constant/polyMesh/owner")
start, nf = patch_range("constant/polyMesh/boundary", "wall_nose")
C = read_vector(f"{ctime}/C")

rows = []
for fid in range(start, start + nf):
    fc, S = face_geom(points[faces[fid]])
    n = S / np.linalg.norm(S)
    o = owner[fid]
    d = float(np.dot(fc - C[o], n))
    ang = math.degrees(math.atan2(math.hypot(n[1], n[2]), n[0]))
    rows.append((fc[1], ang, d, fid, o))
rows.sort(key=lambda r: r[0])

print(f"wall_nose: {nf} faces (start {start}); every {step}th face from the axis")
print(f"{'face':>7} {'owner':>6} {'fc_y (m)':>11} {'angle (deg)':>11} {'d (m)':>11}")
shown = list(range(0, len(rows), step))
if shown[-1] != len(rows) - 1:
    shown.append(len(rows) - 1)
for i in shown:
    y, ang, d, fid, o = rows[i]
    print(f"{fid:7d} {o:6d} {y:11.4e} {ang:11.2f} {d:11.3e}")

ds = np.array([r[2] for r in rows])
imin = int(np.argmin(ds))
print(f"\ntip face d      : {ds[0]:.4e} m  (angle {rows[0][1]:.2f} deg)")
print(f"minimum d       : {ds[imin]:.4e} m  (angle {rows[imin][1]:.2f} deg)")
print(f"last face d     : {ds[-1]:.4e} m  (angle {rows[-1][1]:.2f} deg)")
print(f"min / tip ratio : {ds[imin] / ds[0]:.3f}")
print(f"faces with d<=0 : {int((ds <= 0).sum())}")
