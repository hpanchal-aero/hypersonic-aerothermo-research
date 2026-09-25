#!/usr/bin/env python3
"""
Reads probeStagnation time-series (p, T, U at the nose-tip stagnation
point) and checks temporal convergence using the same criterion as the
prior repository's investigation: |Q(i)-Q(i-1)|/Q(i-1) < 1% for 3
consecutive snapshots, non-reversing trend.
"""
import numpy as np
import re

def read_probe_scalar(path):
    times, vals = [], []
    with open(path) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            times.append(float(parts[0]))
            vals.append(float(parts[1]))
    return np.array(times), np.array(vals)

def read_probe_vector(path):
    times, vals = [], []
    with open(path) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip()
            if not parts:
                continue
            m = re.match(r'([\d.eE+-]+)\s*\(([^)]+)\)', parts)
            if not m:
                continue
            t = float(m.group(1))
            vec = [float(x) for x in m.group(2).split()]
            times.append(t)
            vals.append(vec)
    return np.array(times), np.array(vals)

t_p, p = read_probe_scalar("postProcessing/probeStagnation/0/p")
t_T, T = read_probe_scalar("postProcessing/probeStagnation/0/T")
t_U, U = read_probe_vector("postProcessing/probeStagnation/0/U")

print(f"p: {len(t_p)} samples, t=[{t_p[0]:.4e}, {t_p[-1]:.4e}]")
print(f"T: {len(t_T)} samples, t=[{t_T[0]:.4e}, {t_T[-1]:.4e}]")
print(f"U: {len(t_U)} samples, t=[{t_U[0]:.4e}, {t_U[-1]:.4e}]")

print(f"\nFinal 15 p_stag values (Pa):")
for i in range(max(0, len(p)-15), len(p)):
    rel = abs(p[i]-p[i-1])/abs(p[i-1]) * 100 if i > 0 else float('nan')
    print(f"  t={t_p[i]:.6e}  p={p[i]:.6e}  Δ%={rel:.4f}")

print(f"\nFinal 15 T_stag values (K):")
for i in range(max(0, len(T)-15), len(T)):
    rel = abs(T[i]-T[i-1])/abs(T[i-1]) * 100 if i > 0 else float('nan')
    print(f"  t={t_T[i]:.6e}  T={T[i]:.6e}  Δ%={rel:.4f}")

print(f"\nFinal 5 U_stag vectors (m/s):")
for i in range(max(0, len(U)-5), len(U)):
    print(f"  t={t_U[i]:.6e}  U=({U[i,0]:.4f}, {U[i,1]:.6e}, {U[i,2]:.6e})")

# Formal convergence check on p and T
def check_convergence(t, vals, name):
    if len(vals) < 4:
        print(f"{name}: not enough samples")
        return
    rel_changes = np.abs(np.diff(vals)) / np.abs(vals[:-1]) * 100
    last3 = rel_changes[-3:]
    monotonic = np.all(np.diff(vals[-4:]) <= 0) or np.all(np.diff(vals[-4:]) >= 0)
    passed = np.all(last3 < 1.0)
    print(f"\n{name} convergence check: last 3 rel changes = {last3}")
    print(f"  All < 1%: {passed}   Monotonic (last 4 pts): {monotonic}")
    print(f"  => {'PASS' if passed else 'FAIL'} (formal criterion)")

check_convergence(t_p, p, "p_stag")
check_convergence(t_T, T, "T_stag")
