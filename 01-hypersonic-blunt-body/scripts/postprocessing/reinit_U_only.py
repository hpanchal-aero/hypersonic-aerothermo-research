#!/usr/bin/env python3
"""
Sets U (only) to a target value in the cells of a given cellSet, leaving
p, T, and every other cell's U completely untouched. Intended for use
with a field-based selection (fieldToCell on p) that already guarantees
the selected cells are undisturbed freestream, so p/T need no change.

Usage: /usr/bin/python3 reinit_U_only.py <timestep> <cellSetPath> <Ux> <Uy> <Uz>
"""
import sys
import re
import shutil

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
    return set(vals)

def reinit_vector(path, cellset, value_tuple):
    shutil.copy(path, path + ".bak")
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1))
    list_start = m.end()

    pat = re.compile(r'\(([^()]+)\)')
    pos = list_start
    triples = []
    last_end = list_start
    for _ in range(n):
        mm = pat.search(content, pos)
        if mm is None:
            raise ValueError(f"only found {len(triples)} of {n} expected tuples")
        triples.append(mm.group(1))
        pos = mm.end()
        last_end = mm.end()

    close_idx = content.index(')', last_end)

    for idx in cellset:
        triples[idx] = f"{value_tuple[0]:.6g} {value_tuple[1]:.6g} {value_tuple[2]:.6g}"
    new_body = "\n".join(f"({t})" for t in triples)
    new_content = content[:list_start] + "\n" + new_body + "\n" + content[close_idx:]
    with open(path, "w") as f:
        f.write(new_content)
    print(f"{path}: rewrote {len(cellset)} of {n} cells to {value_tuple}")

TIMESTEP = sys.argv[1]
SETPATH = sys.argv[2]
Ux, Uy, Uz = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])

cellset = read_labellist(SETPATH)
print(f"Setting U in {len(cellset)} undisturbed-freestream cells at t={TIMESTEP}")
reinit_vector(f"{TIMESTEP}/U", cellset, (Ux, Uy, Uz))
print("Done. p and T were NOT touched. Original U backed up as .bak.")
