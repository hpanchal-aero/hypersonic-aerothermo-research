#!/usr/bin/env python3
"""
Extracts pressure at several stations along wall_cone from all written
field snapshots, using the owner-cell value (correct for a zeroGradient
wall BC), and checks temporal convergence per station using the same
1%-for-3-consecutive-snapshots criterion.
"""
import numpy as np
import re
import glob
import os

def read_points(path):
    with open(path) as f:
        content = f.read()
    nums = re.findall(r'\(([^)]+)\)', content.split("(", 1)[1])
    return np.array([[float(x) for x in n.split()] for n in nums])

def read_faces(path):
    with open(path) as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().isdigit())
    n = int(lines[start].strip())
    faces = []
    i = start + 2
    count = 0
    while count < n:
        line = lines[i].strip()
        if line and line[0].isdigit():
            idxs = [int(x) for x in line.split('(')[1].split(')')[0].split()]
            faces.append(idxs)
            count += 1
        i += 1
    return faces

def read_owner(path):
    with open(path) as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().isdigit())
    n = int(lines[start].strip())
    vals = []
    i = start + 2
    count = 0
    while count < n:
        line = lines[i].strip()
        if line and (line[0].isdigit() or line[0] == '-'):
            vals.append(int(line))
            count += 1
        i += 1
    return np.array(vals)

def read_boundary_patch_range(path, patch_name):
    with open(path) as f:
        content = f.read()
    m = re.search(patch_name + r'\s*\{[^}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);', content, re.DOTALL)
    nFaces, startFace = int(m.group(1)), int(m.group(2))
    return startFace, nFaces

def read_internal_scalar(path):
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1))
    start = m.end()
    end = content.index(')', start)
    nums = content[start:end].split()
    return np.array([float(x) for x in nums[:n]])

# ---- setup: identify wall_cone owner cells and their centroids ----
points = read_points("constant/polyMesh/points")
faces = read_faces("constant/polyMesh/faces")
owner = read_owner("constant/polyMesh/owner")

startFace, nFaces = read_boundary_patch_range("constant/polyMesh/boundary", "wall_cone")
cone_face_ids = list(range(startFace, startFace + nFaces))
cone_owner_cells = owner[cone_face_ids]

n_cells = owner.max() + 1
cell_pts_sum = np.zeros((n_cells, 3))
cell_pts_count = np.zeros(n_cells)
for fid, verts in enumerate(faces):
    o = owner[fid]
    pts = points[verts]
    cell_pts_sum[o] += pts.sum(axis=0)
    cell_pts_count[o] += len(verts)
centroids = cell_pts_sum / cell_pts_count[:, None]

cone_x = centroids[cone_owner_cells, 0]
order = np.argsort(cone_x)
cone_owner_cells_sorted = cone_owner_cells[order]
cone_x_sorted = cone_x[order]

# pick 5 stations evenly spaced along the cone's x-range
station_idxs = np.linspace(0, len(cone_owner_cells_sorted) - 1, 5).astype(int)
station_cells = cone_owner_cells_sorted[station_idxs]
station_x = cone_x_sorted[station_idxs]

print("Stations (cell id, x location):")
for c, x in zip(station_cells, station_x):
    print(f"  cell {c}: x={x:.6f}")

# ---- gather all written timesteps ----
dirs = [d for d in glob.glob("*e-*") if os.path.isdir(d) and os.path.exists(f"{d}/p")]
times = sorted([float(d) for d in dirs])
print(f"\nFound {len(times)} written timesteps with p field")

series = {c: [] for c in station_cells}
for t in times:
    d = repr(t) if repr(t) in dirs else None
    # match directory name format directly since float repr may differ
    for cand in dirs:
        if abs(float(cand) - t) < 1e-15:
            d = cand
            break
    p = read_internal_scalar(f"{d}/p")
    for c in station_cells:
        series[c].append(p[c])

times = np.array(times)
print(f"\n=== Convergence check per station ===")
for c, x in zip(station_cells, station_x):
    vals = np.array(series[c])
    if len(vals) < 4:
        print(f"Station x={x:.4f} (cell {c}): not enough samples")
        continue
    rel_changes = np.abs(np.diff(vals)) / np.abs(vals[:-1]) * 100
    last3 = rel_changes[-3:]
    passed = np.all(last3 < 1.0)
    print(f"\nStation x={x:.4f} (cell {c}):")
    print(f"  final 5 p values: {vals[-5:]}")
    print(f"  last 3 rel changes (%): {last3}")
    print(f"  => {'PASS' if passed else 'FAIL'}")
