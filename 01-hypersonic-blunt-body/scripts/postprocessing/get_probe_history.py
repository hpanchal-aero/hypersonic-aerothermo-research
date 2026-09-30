#!/usr/bin/env python3
"""
Concatenates the probe histories of a restarted OpenFOAM case (one
postProcessing/<probe>/<startTime>/ folder per (re)start) into one
continuous time series, then reports stagnation and forebody pressure
versus time against the steady Pitot value (M=7, gamma=1.4,
p_inf=1197 Pa -> p02 = 76072 Pa).

Run from inside the case directory:
    /usr/bin/python3 ../../scripts/postprocessing/get_probe_history.py
When a later chunk starts at time t0, earlier-chunk rows with time >= t0
are dropped (the restart overrides the overlap).
"""
import os
import numpy as np

P_INF = 1197.0
PITOT_P02 = 76072.0
SAMPLES = [2.62e-6, 1e-5, 2e-5, 3e-5, 4e-5, 5e-5, 6e-5, 7e-5, 8e-5, 9e-5, 1e-4]


def read_chunk(path):
    times, rows = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            try:
                vals = [float(x) for x in line.split()]
            except ValueError:
                continue
            times.append(vals[0])
            rows.append(vals[1:])
    return np.array(times), np.array(rows)


def load(probe, field):
    base = os.path.join("postProcessing", probe)
    chunks = []
    for d in os.listdir(base):
        path = os.path.join(base, d, field)
        if os.path.isfile(path):
            t, v = read_chunk(path)
            if len(t):
                chunks.append((float(d), t, v))
    chunks.sort(key=lambda c: c[0])
    T, V = [], []
    for i, (start, t, v) in enumerate(chunks):
        if i + 1 < len(chunks):
            keep = t < chunks[i + 1][1][0]
            t, v = t[keep], v[keep]
        T.append(t)
        V.append(v)
    T = np.concatenate(T)
    V = np.vstack(V)
    print(f"[{probe}/{field}] chunks: {[c[0] for c in chunks]}  rows: {len(T)}  "
          f"t=[{T[0]:.3e}, {T[-1]:.6e}]  strictly increasing: {bool(np.all(np.diff(T) > 0))}")
    return T, V


def at(T, t):
    return int(np.abs(T - t).argmin())


Ts, Ps = load("probeStagnation", "p")
_, Tt = load("probeStagnation", "T")
Tf, Pf = load("probeForebody", "p")

print("\n=== Stagnation point vs time (steady Pitot p02 = %.0f Pa = %.1f p_inf) ===" %
      (PITOT_P02, PITOT_P02 / P_INF))
print("   t (s)      p_stag (Pa)   p/p_inf   %% of Pitot   T_stag (K)")
for s in SAMPLES:
    i = at(Ts, s)
    print(f"{Ts[i]:.4e}  {Ps[i,0]:11.1f}  {Ps[i,0]/P_INF:8.2f}  {100*Ps[i,0]/PITOT_P02:9.1f}     {Tt[i,0]:8.2f}")

print("\n=== Drift of p_stag ===")
for a, b in [(8e-5, 1e-4), (9e-5, 1e-4)]:
    ia, ib = at(Ts, a), at(Ts, b)
    print(f"{Ts[ia]:.3e} -> {Ts[ib]:.3e}: {Ps[ia,0]:.1f} -> {Ps[ib,0]:.1f} Pa  "
          f"({100*(Ps[ib,0]-Ps[ia,0])/Ps[ia,0]:+.3f} %)")

print("\n=== Forebody pressure (Pa) at the 5 wall_cone stations ===")
print("   t (s)      st0        st1        st2        st3        st4")
for s in [1e-5, 3e-5, 5e-5, 7e-5, 9e-5, 1e-4]:
    i = at(Tf, s)
    print(f"{Tf[i]:.4e}  " + "  ".join(f"{x:9.1f}" for x in Pf[i]))
i8, i10 = at(Tf, 8e-5), at(Tf, 1e-4)
print("change 8e-5 -> 1e-4 (%):   " +
      "  ".join(f"{100*(Pf[i10,k]-Pf[i8,k])/Pf[i8,k]:+9.3f}" for k in range(5)))
