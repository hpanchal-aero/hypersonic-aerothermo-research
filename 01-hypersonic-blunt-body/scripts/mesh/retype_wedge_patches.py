#!/usr/bin/env python3
"""
Retype the frontWedge/backWedge patches in an OpenFOAM polyMesh/boundary
file from 'patch' to 'wedge'. gmshToFoam always writes these as generic
'patch' type, but the wedge-axisymmetric formulation requires them to be
declared as 'wedge' for OpenFOAM to treat them as the required constraint
patch type. createPatch cannot retype an existing same-named patch, so
this does a direct, careful text substitution instead.

Usage: python3 retype_wedge_patches.py <path-to-boundary-file>
"""
import re
import sys

def retype_wedge_patches(path):
    with open(path) as f:
        content = f.read()

    patch_names = ["frontWedge", "backWedge"]
    substitutions = 0

    for name in patch_names:
        # Match the patch's own block: name, opening brace, then find the
        # 'type ...;' line within that specific block (not any other patch).
        pattern = re.compile(
            r'(\b' + re.escape(name) + r'\s*\n\s*\{[^}]*?type\s+)(\w+)(\s*;)',
            re.DOTALL
        )
        new_content, n = pattern.subn(r'\1wedge\3', content, count=1)
        if n == 1:
            content = new_content
            substitutions += 1
            print(f"{name}: 1 substitution(s) made")
        else:
            print(f"{name}: WARNING - 0 substitutions made (pattern not found)")

    with open(path, 'w') as f:
        f.write(content)

    print(f"Wrote updated file: {path}")
    return substitutions

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 retype_wedge_patches.py <path-to-boundary-file>")
        sys.exit(1)
    n = retype_wedge_patches(sys.argv[1])
    if n != 2:
        print(f"WARNING: expected 2 substitutions (frontWedge, backWedge), got {n}")
        sys.exit(1)
