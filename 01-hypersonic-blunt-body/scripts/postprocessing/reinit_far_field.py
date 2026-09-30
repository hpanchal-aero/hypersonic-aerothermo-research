#!/usr/bin/env python3
"""
Reinitializes ONLY the cells in a given cellSet to specified uniform
values, while leaving every other cell's existing value untouched.
Unlike setFields, this never touches cells outside the set. Writes new
files in-place (after backing up the originals with a .bak suffix).

Usage: /usr/bin/python3 reinit_far_field.py <timestep> <cellSetPath>
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

def reinit_scalar(path, cellset, value):
    shutil.copy(path, path + ".bak")
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1))
    start = m.end()
    end = content.index(')', start)  # first ')' after start is unambiguous for scalars
    nums = content[start:end].split()
    assert len(nums) == n, f"expected {n} values, found {len(nums)}"
    for idx in cellset:
        nums[idx] = f"{value:.6g}"
    new_body = "\n".join(nums)
    new_content = content[:start] + "\n" + new_body + "\n" + content[end:]
    with open(path, "w") as f:
        f.write(new_content)
    print(f"{path}: rewrote {len(cellset)} of {n} cells to {value}")

def reinit_vector(path, cellset, value_tuple):
    shutil.copy(path, path + ".bak")
    with open(path) as f:
        content = f.read()
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(', content)
    n = int(m.group(1))
    list_start = m.end()  # position right after the outer '(' of the internalField list

    # Scan EXACTLY n "(a b c)" tuples starting from list_start - do not assume
    # the list ends at the last ')' in the file, since boundary patch data
    # (written for AUTO_WRITE fields) also contains vector-looking tuples
    # further down in the file.
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

    # The very next ')' after the nth tuple closes the internalField list itself
    close_idx = content.index(')', last_end)

    for idx in cellset:
        triples[idx] = f"{value_tuple[0]:.6g} {value_tuple[1]:.6g} {value_tuple[2]:.6g}"
    new_body = "\n".join(f"({t})" for t in triples)
    # content[close_idx:] starts with the list's own ')' and preserves
    # everything after it (boundaryField etc.) completely untouched
    new_content = content[:list_start] + "\n" + new_body + "\n" + content[close_idx:]
    with open(path, "w") as f:
        f.write(new_content)
    print(f"{path}: rewrote {len(cellset)} of {n} cells to {value_tuple}")

TIMESTEP = sys.argv[1]
SETPATH = sys.argv[2]

cellset = read_labellist(SETPATH)
print(f"Reinitializing {len(cellset)} cells (farFreestream) at t={TIMESTEP}")

reinit_scalar(f"{TIMESTEP}/p", cellset, 1197.0)
reinit_scalar(f"{TIMESTEP}/T", cellset, 226.5)
reinit_vector(f"{TIMESTEP}/U", cellset, (2111.72, 0.0, 0.0))

print("Done. Originals backed up as .bak in the same directory.")
