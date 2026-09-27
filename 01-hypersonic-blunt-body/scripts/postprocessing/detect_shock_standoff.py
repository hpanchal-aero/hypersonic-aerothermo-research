#!/usr/bin/env python3
"""
Shock stand-off distance detection via TRUE axis-adjacent cells (exact
r=0 membership from mesh topology), not a radius-tolerance selection.
Reimplements the validated method from the prior repository's
investigation (which explicitly rejected two radius-tolerance-based
methods for axis-contamination). Isolates the UPSTREAM axis chain
(nose stagnation streamline) from the separate downstream wake/base
axis chain by x-range, since both exist in this mesh topology but
only the upstream one is relevant to shock stand-off.
"""
import numpy as np
import re
import sys

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

def read_internal_scalar(path):
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1))
    start = m.end()
    end = content.index(')', start)
    nums = content[start:end].split()
    return np.array([float(x) for x in nums[:n]])

TIMESTEP = sys.argv[1] if len(sys.argv) > 1 else None
UPSTREAM_XMAX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05  # excludes downstream wake axis chain
P_INF = float(sys.argv[3]) if len(sys.argv) > 3 else 1197.0

points = read_points("constant/polyMesh/points")
faces = read_faces("constant/polyMesh/faces")
owner = read_owner("constant/polyMesh/owner")
n_cells = owner.max() + 1

# True axis points: exact r=0 (y=0 and z=0), not a tolerance-based selection
r = np.hypot(points[:, 1], points[:, 2])
axis_point_mask = r < 1e-12
axis_point_ids = set(np.where(axis_point_mask)[0])

# Cells touching at least one true axis point
cell_pts_sum = np.zeros((n_cells, 3))
cell_pts_count = np.zeros(n_cells)
cell_touches_axis = np.zeros(n_cells, dtype=bool)
for fid, verts in enumerate(faces):
    o = owner[fid]
    pts = points[verts]
    cell_pts_sum[o] += pts.sum(axis=0)
    cell_pts_count[o] += len(verts)
    if any(v in axis_point_ids for v in verts):
        cell_touches_axis[o] = True

centroids = cell_pts_sum / cell_pts_count[:, None]
axis_cells = np.where(cell_touches_axis)[0]
axis_x = centroids[axis_cells, 0]

print(f"Total true-axis-adjacent cells (both chains): {len(axis_cells)}")

# Isolate UPSTREAM chain only (excludes the separate downstream wake/base axis chain)
upstream_mask = axis_x < UPSTREAM_XMAX
up_cells = axis_cells[upstream_mask]
up_x = axis_x[upstream_mask]

order = np.argsort(up_x)
up_cells = up_cells[order]
up_x = up_x[order]

print(f"Upstream (stagnation-streamline) axis chain: {len(up_cells)} cells, "
      f"x=[{up_x[0]:.6f}, {up_x[-1]:.6f}]")

# uniqueness check
if len(np.unique(up_x)) != len(up_x):
    print("WARNING: duplicate x values in axis chain - possible contamination")

if TIMESTEP is None:
    print("\nNo timestep given - pass a timestep directory to extract p and locate the shock.")
    sys.exit(0)

p = read_internal_scalar(f"{TIMESTEP}/p")
up_p = p[up_cells]

print(f"\n=== True-axis pressure profile at t={TIMESTEP} ===")
print(f"{'x':>12} {'p (Pa)':>12} {'p/p_inf':>10}")
for x, pv in zip(up_x, up_p):
    print(f"{x:12.6f} {pv:12.4f} {pv/P_INF:10.4f}")

# Method 1: first axis cell (moving downstream, i.e. increasing x) where p > threshold*p_inf
for thresh in [1.5, 2.0]:
    idx = np.argmax(up_p > thresh * P_INF)  # first True
    if up_p[idx] > thresh * P_INF:
        standoff = -up_x[idx]  # nose tip is at x=0; standoff measured upstream (negative x)
        print(f"\n[Threshold method, {thresh}x p_inf] onset at x={up_x[idx]:.6f} "
              f"-> shock stand-off delta = {standoff:.6f} m ({standoff*1000:.3f} mm)")
    else:
        print(f"\n[Threshold method, {thresh}x p_inf] NOT REACHED anywhere on the upstream axis chain")

# Method 2: peak |dp/dx| (steepest compression gradient)
dp = np.diff(up_p)
dx = np.diff(up_x)
grad = dp / dx
peak_idx = np.argmax(np.abs(grad))
x_peak = 0.5 * (up_x[peak_idx] + up_x[peak_idx+1])
standoff_grad = -x_peak
print(f"\n[Peak |dp/dx| method] steepest gradient at x={x_peak:.6f} "
      f"(|dp/dx|={abs(grad[peak_idx]):.4e} Pa/m) -> shock stand-off delta = "
      f"{standoff_grad:.6f} m ({standoff_grad*1000:.3f} mm)")

print(f"\nStagnation cell (x closest to 0): x={up_x[-1]:.6f}, p={up_p[-1]:.4f} Pa "
      f"(p/p_inf={up_p[-1]/P_INF:.2f})")
