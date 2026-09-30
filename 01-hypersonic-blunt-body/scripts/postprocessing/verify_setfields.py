#!/usr/bin/env python3
"""
Verifies a setFields result: reads a cellSet file (OpenFOAM labelList
format) and reports p/T/U statistics for cells IN the set vs cells NOT
in the set, at a given timestep. Run from inside the case directory.
Usage: /usr/bin/python3 verify_setfields.py <timestep> <cellSetPath>
"""
import sys
import re
import numpy as np

def read_labellist(path):
    with open(path) as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().isdigit())
    n = int(lines[start].strip())
    vals = []
    i = start + 2
    count = 0
    while count < n:
        line = lines[i].strip()
        if line and line[0].isdigit():
            vals.append(int(line))
            count += 1
        i += 1
    return np.array(vals)

def read_scalar_field(path):
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1)); start = m.end()
    end = content.index(')', start)
    return np.array([float(x) for x in content[start:end].split()[:n]])

def read_vector_field(path):
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1)); start = m.end()
    end = content.rindex(')')
    triples = re.findall(r'\(([^()]+)\)', content[start:end])
    return np.array([[float(x) for x in t.split()] for t in triples[:n]])

TIMESTEP = sys.argv[1]
SETPATH = sys.argv[2]

far_cells = set(read_labellist(SETPATH))
p = read_scalar_field(f"{TIMESTEP}/p")
T = read_scalar_field(f"{TIMESTEP}/T")
U = read_vector_field(f"{TIMESTEP}/U")

n_cells = len(p)
mask_far = np.zeros(n_cells, dtype=bool)
mask_far[list(far_cells)] = True

print(f"Total cells: {n_cells}, farFreestream set size: {len(far_cells)}")
print(f"\n=== Cells IN farFreestream (should be p=1197, T=226.5, Ux=2111.72) ===")
print(f"p:  min={p[mask_far].min():.2f} max={p[mask_far].max():.2f} mean={p[mask_far].mean():.2f}")
print(f"T:  min={T[mask_far].min():.2f} max={T[mask_far].max():.2f} mean={T[mask_far].mean():.2f}")
print(f"Ux: min={U[mask_far,0].min():.2f} max={U[mask_far,0].max():.2f} mean={U[mask_far,0].mean():.2f}")

print(f"\n=== Cells NOT in farFreestream (should be UNCHANGED, relaxed non-uniform values) ===")
print(f"p:  min={p[~mask_far].min():.2f} max={p[~mask_far].max():.2f} mean={p[~mask_far].mean():.2f}")
print(f"T:  min={T[~mask_far].min():.2f} max={T[~mask_far].max():.2f} mean={T[~mask_far].mean():.2f}")
print(f"Ux: min={U[~mask_far,0].min():.2f} max={U[~mask_far,0].max():.2f} mean={U[~mask_far,0].mean():.2f}")

