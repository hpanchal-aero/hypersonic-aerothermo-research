#!/usr/bin/env python3
"""
Inspect field data at the last-written timestep before a solver crash.
Parses OpenFOAM ASCII volScalarField/volVectorField files directly
(no PyFoam/pandas dependency), reports basic stats and locates extreme
cells, with their approximate (x,r) location via the mesh points/owner
data - to check for spatial localization of anomalies.
"""
import numpy as np
import re
import sys
import os

def read_scalar_field(path):
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', content)
    if not m:
        # uniform field - not useful for spatial diagnosis but handle gracefully
        m2 = re.search(r'internalField\s+uniform\s+([\-\d.eE+]+)', content)
        if m2:
            return None, float(m2.group(1))
        return None, None
    n = int(m.group(1))
    start = m.end()
    end = content.index(')', start)
    nums = content[start:end].split()
    vals = np.array([float(x) for x in nums[:n]])
    return vals, None

def read_vector_field(path):
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(', content)
    if not m:
        return None
    n = int(m.group(1))
    start = m.end()
    end = content.rindex(')')
    body = content[start:end]
    triples = re.findall(r'\(([^()]+)\)', body)
    vecs = np.array([[float(x) for x in t.split()] for t in triples[:n]])
    return vecs

def read_points(path):
    with open(path) as f:
        content = f.read()
    nums = re.findall(r'\(([^)]+)\)', content.split("(", 1)[1])
    return np.array([[float(x) for x in n.split()] for n in nums])

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

TIMESTEP = sys.argv[1] if len(sys.argv) > 1 else "2.63989e-06"

print(f"=== Inspecting timestep {TIMESTEP} ===\n")

# Build cell centroids (approx, from face-of-cell 0 average - good enough for localization)
points = read_points("constant/polyMesh/points")
faces = read_faces("constant/polyMesh/faces")
owner = read_owner("constant/polyMesh/owner")
n_cells = owner.max() + 1

cell_pts_sum = np.zeros((n_cells, 3))
cell_pts_count = np.zeros(n_cells)
for fid, verts in enumerate(faces):
    o = owner[fid]
    pts = points[verts]
    cell_pts_sum[o] += pts.sum(axis=0)
    cell_pts_count[o] += len(verts)
centroids = cell_pts_sum / cell_pts_count[:, None]

for field, reader in [("p", read_scalar_field), ("T", read_scalar_field), ("e", read_scalar_field)]:
    path = f"{TIMESTEP}/{field}"
    if not os.path.exists(path):
        print(f"{field}: file not found")
        continue
    vals, uniform = reader(path)
    if vals is None:
        print(f"{field}: uniform value {uniform}")
        continue
    print(f"{field}: min={vals.min():.6e} max={vals.max():.6e} mean={vals.mean():.6e}")
    worst = np.argsort(vals)[-3:]
    for idx in worst:
        c = centroids[idx]
        print(f"    cell {idx}: {field}={vals[idx]:.6e}  x={c[0]:.6f} r={np.hypot(c[1],c[2]):.6f}")
    worst_lo = np.argsort(vals)[:3]
    for idx in worst_lo:
        c = centroids[idx]
        print(f"    cell {idx}: {field}={vals[idx]:.6e}  x={c[0]:.6f} r={np.hypot(c[1],c[2]):.6f}  (LOW)")
    print()

Upath = f"{TIMESTEP}/U"
if os.path.exists(Upath):
    U = read_vector_field(Upath)
    if U is not None:
        Uz = U[:, 2]
        print(f"Uz: min={Uz.min():.6e} max={Uz.max():.6e} mean={Uz.mean():.6e} std={Uz.std():.6e}")
        worst = np.argsort(np.abs(Uz))[-10:]
        print("Top 10 |Uz| cells:")
        for idx in worst:
            c = centroids[idx]
            print(f"    cell {idx}: Uz={Uz[idx]:.6e}  Ux={U[idx,0]:.4f} Uy={U[idx,1]:.6e}  x={c[0]:.6f} r={np.hypot(c[1],c[2]):.6f}")
