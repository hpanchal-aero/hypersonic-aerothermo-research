#!/usr/bin/env python3
"""
History of one cell and its K nearest neighbours across snapshots, with
cellSet membership. Run from the case directory, after
  postProcess -func writeCellCentres -time <t0>
has written C into the <t0> directory (centres are static; read from <t0>).

Prints, for the target cell, p, T, Ux, Uy at every snapshot with time >= t0,
and whether it is in the cellSet. Then, for the K nearest cells by centre
distance, their set membership and p, T, Ux at the first and last snapshot.

Usage: /usr/bin/python3 cell_history.py <cell> <t0> <cellSetPath> [K=8]
"""
import os
import re
import sys
import numpy as np


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


def read_labels(path):
    lines = open(path).readlines()
    s = next(i for i, l in enumerate(lines) if l.strip().isdigit())
    n = int(lines[s].strip())
    return set(int(l) for l in lines[s + 2:s + 2 + n])


cell, t0, setpath = int(sys.argv[1]), sys.argv[2], sys.argv[3]
K = int(sys.argv[4]) if len(sys.argv) > 4 else 8

C = read_vector(f"{t0}/C")
inset = read_labels(setpath)
times = sorted([d for d in os.listdir('.')
                if re.match(r'^[0-9.]+(e-?[0-9]+)?$', d) and float(d) >= float(t0)
                and os.path.exists(f"{d}/p") and os.path.exists(f"{d}/U")],
               key=float)
print(f"cell {cell}: centre ({C[cell,0]:.5f}, {C[cell,1]:.5f}, {C[cell,2]:.2e}), "
      f"in set: {cell in inset}; {len(times)} snapshots from {t0}")

d = np.linalg.norm(C - C[cell], axis=1)
near = [int(i) for i in np.argsort(d)[1:K + 1]]

hist = {}
for t in times:
    p = read_scalar(f"{t}/p")
    T = read_scalar(f"{t}/T")
    U = read_vector(f"{t}/U")
    hist[t] = (p, T, U)

print(f"\n{'time':>11} {'p (Pa)':>10} {'T (K)':>9} {'Ux':>9} {'Uy':>9}")
for t in times:
    p, T, U = hist[t]
    print(f"{t:>11} {p[cell]:10.2f} {T[cell]:9.3f} {U[cell,0]:9.1f} {U[cell,1]:9.1f}")

tf, tl = times[0], times[-1]
print(f"\nnearest {K} cells (distance mm, dx, dy mm, in set, first/last snapshot)")
print(f"{'cell':>6} {'dist':>6} {'dx':>7} {'dy':>7} {'inset':>5} "
      f"{'p_first':>9} {'T_first':>8} {'Ux_first':>8} {'p_last':>9} {'T_last':>8} {'Ux_last':>8}")
for i in near:
    pf, Tf, Uf = hist[tf]
    pl, Tl, Ul = hist[tl]
    print(f"{i:6d} {1e3*d[i]:6.2f} {1e3*(C[i,0]-C[cell,0]):7.2f} {1e3*(C[i,1]-C[cell,1]):7.2f} "
          f"{str(i in inset):>5} {pf[i]:9.1f} {Tf[i]:8.2f} {Uf[i,0]:8.1f} "
          f"{pl[i]:9.1f} {Tl[i]:8.2f} {Ul[i,0]:8.1f}")
