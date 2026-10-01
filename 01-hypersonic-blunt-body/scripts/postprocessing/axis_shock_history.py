#!/usr/bin/env python3
"""
Axis-profile history across snapshots. For each time, runs
detect_shock_standoff.py, parses its printed upstream axis profile
(x, p, p/p_inf rows), then reports:
  - shock position: half-jump crossing between p_inf and the local
    post-shock level, and the resulting stand-off in mm
  - wall-cell pressure vs the axis pressure maximum (and where it is)
  - upstream feature (x < -0.05 m): position/value of max and min p

Run from inside the case directory.
Usage: /usr/bin/python3 axis_shock_history.py <t1> <t2> ...
"""
import os
import re
import subprocess
import sys
import numpy as np

P_INF = 1197.0
HERE = os.path.dirname(os.path.abspath(__file__))
DETECT = os.path.join(HERE, "detect_shock_standoff.py")
ROW = re.compile(r'^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$')


def profile(t):
    out = subprocess.run(["/usr/bin/python3", DETECT, t],
                         capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        m = ROW.match(line)
        if m:
            rows.append((float(m.group(1)), float(m.group(2))))
    a = np.array(sorted(rows))
    return a[:, 0], a[:, 1]


print(f"{'t':>9} {'standoff_mm':>11} {'p_wall':>9} {'p_axmax':>9} {'x_axmax_mm':>10}"
      f" {'feat_pmax':>9} {'feat_x':>8} {'feat_pmin':>9} {'feat_x':>8}")
for t in sys.argv[1:]:
    x, p = profile(t)
    if len(x) < 10:
        print(f"{t:>9}  could not parse profile ({len(x)} rows)")
        continue
    near = (x > -0.02)
    xn, pn = x[near], p[near]
    post = pn[xn > -0.006].max() if np.any(xn > -0.006) else np.nan
    half = 0.5 * (P_INF + post)
    idx = np.where((pn[:-1] < half) & (pn[1:] >= half))[0]
    if len(idx):
        i = idx[0]
        xs = xn[i] + (half - pn[i]) * (xn[i + 1] - xn[i]) / (pn[i + 1] - pn[i])
        so = -xs * 1000.0
    else:
        so = float('nan')
    imax = np.argmax(pn)
    far = x < -0.05
    xf, pf = x[far], p[far]
    print(f"{t:>9} {so:11.2f} {p[-1]:9.0f} {pn[imax]:9.0f} {-xn[imax]*1000:10.2f}"
          f" {pf.max():9.0f} {xf[np.argmax(pf)]:8.3f} {pf.min():9.0f} {xf[np.argmin(pf)]:8.3f}")
