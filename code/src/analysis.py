import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE     = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE, "../data/simulation_log.csv")
TOD_FILE = os.path.join(BASE, "../data/simulation_log_tod.csv")
OUT_DIR  = os.path.join(BASE, "../experiments")
os.makedirs(OUT_DIR, exist_ok=True)

df     = pd.read_csv(LOG_FILE)
Q      = df["total_queue"].values
mu     = Q.mean()
sigma  = Q.std()

# ── 1. Statistical Summary ───────────────────────────────────────────
print("=" * 50)
print("  FIXED TIMER — STATISTICAL SUMMARY")
print("=" * 50)
print(f"  Mean     μ       = {mu:.2f}")
print(f"  Median           = {np.median(Q):.2f}")
print(f"  Variance Var(Q)  = {Q.var():.2f}")
print(f"  Std Dev  σ       = {sigma:.2f}")

# ── 2. Jensen's Inequality Proof ─────────────────────────────────────
f_EQ = mu ** 2
Ef_Q = (Q ** 2).mean()
print(f"\n  Jensen's Inequality:")
print(f"  f(E[Q])  = {f_EQ:.2f}  (uniform assumption)")
print(f"  E[f(Q)]  = {Ef_Q:.2f}  (real chaotic data)")
print(f"  Gap      = {Ef_Q - f_EQ:.2f}  <- fixed timer underestimates delay by this much")
print(f"  Jensen holds: {Ef_Q >= f_EQ}")
print("=" * 50)

# ── Load TOD if available ────────────────────────────────────────────
tod_available = os.path.exists(TOD_FILE)
if tod_available:
    df_tod  = pd.read_csv(TOD_FILE)
    Q_tod   = df_tod["total_queue"].values
    mu_tod  = Q_tod.mean()
    sig_tod = Q_tod.std()

    print("\n" + "=" * 50)
    print("  TOD TIMER — STATISTICAL SUMMARY")
    print("=" * 50)
    print(f"  Mean     μ       = {mu_tod:.2f}")
    print(f"  Median           = {np.median(Q_tod):.2f}")
    print(f"  Variance Var(Q)  = {Q_tod.var():.2f}")
    print(f"  Std Dev  σ       = {sig_tod:.2f}")

    f_EQ_tod = mu_tod ** 2
    Ef_Q_tod = (Q_tod ** 2).mean()
    print(f"\n  Jensen's Inequality (TOD):")
    print(f"  f(E[Q])  = {f_EQ_tod:.2f}")
    print(f"  E[f(Q)]  = {Ef_Q_tod:.2f}")
    print(f"  Gap      = {Ef_Q_tod - f_EQ_tod:.2f}")
    print(f"  Jensen holds: {Ef_Q_tod >= f_EQ_tod}")

    print("\n" + "=" * 50)
    print("  FIXED TIMER vs TOD — COMPARISON")
    print("=" * 50)
    print(f"  Fixed  — Mean Q: {mu:.2f}     | Var: {Q.var():.2f}     | Max: {Q.max()}")
    print(f"  TOD    — Mean Q: {mu_tod:.2f}  | Var: {Q_tod.var():.2f} | Max: {Q_tod.max()}")
    print(f"  Queue Reduction : {((mu - mu_tod) / mu * 100):.1f}%")
    print(f"  Variance Drop   : {((Q.var() - Q_tod.var()) / Q.var() * 100):.1f}%")
    print(f"  Jensen Gap Drop : {((Ef_Q - f_EQ) - (Ef_Q_tod - f_EQ_tod)):.2f}")
    print("=" * 50)
else:
    print("\nTOD log not found — run runner_tod.py for full comparison.")

# ── Helper: demand phase spans ───────────────────────────────────────
def add_spans(ax):
    ax.axvspan(0,   50,  alpha=0.05, color="green",  label="Off-peak (λ=0.17)")
    ax.axvspan(50,  150, alpha=0.05, color="orange", label="Build-up (λ=0.42)")
    ax.axvspan(150, 300, alpha=0.08, color="red",    label="Peak Hour (λ=0.50)")


# ── Plot 1: Chebyshev Histogram — Fixed vs TOD ───────────────────────
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(Q, bins=40, color="steelblue", edgecolor="white",
        density=True, alpha=0.6, label="Fixed Timer — Observed Q")
if tod_available:
    ax.hist(Q_tod, bins=40, color="seagreen", edgecolor="white",
            density=True, alpha=0.6, label="TOD Timer — Observed Q")

# Chebyshev bounds for Fixed Timer
colors = ["gold", "orange", "red"]
for k, c in zip([1, 2, 3], colors):
    bound = 1 / k**2
    ax.axvline(mu + k * sigma, linestyle="--", color=c, linewidth=1.2,
               label=f"Fixed μ+{k}σ  →  P(exceed) ≤ {bound:.2f}")

# Chebyshev bounds for TOD
if tod_available:
    for k, c in zip([1, 2, 3], colors):
        ax.axvline(mu_tod + k * sig_tod, linestyle=":", color=c, linewidth=1.2,
                   label=f"TOD   μ+{k}σ  →  P(exceed) ≤ {1/k**2:.2f}")

ax.set_title("Queue Distribution with Chebyshev Bounds — Fixed Timer vs TOD", fontsize=13)
ax.set_xlabel("Queue Length (vehicles)")
ax.set_ylabel("Density")
ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "chebyshev_histogram.png"), dpi=150)
print("Saved chebyshev_histogram.png")

# ── Plot 2: Side-by-Side Queue Subplots ──────────────────────────────
if tod_available:
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
    for ax, data, label, color in zip(
        axes,
        [df,       df_tod],
        ["Fixed Timer Baseline", "TOD Scheduled Timer"],
        ["crimson", "seagreen"]
    ):
        ax.plot(data["time"], data["total_queue"],
                color=color, linewidth=0.8, label=label)
        ax.axhline(3, linestyle="--", color="gray", linewidth=1, label="Threshold T=3")
        add_spans(ax)
        ax.set_title(label, fontsize=12)
        ax.set_ylabel("Queue Length (vehicles)")
        ax.set_xlabel("Simulation Time (s)")
        ax.legend(loc="upper right", fontsize=8)
    plt.suptitle("Fixed Timer vs TOD — Queue Length Side by Side",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fixed_vs_tod_queue_sidebyside.png"), dpi=150)
    print("Saved fixed_vs_tod_queue_sidebyside.png")

# ── Plot 3: Side-by-Side Waiting Time Subplots ───────────────────────
if tod_available:
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
    for ax, data, label, color in zip(
        axes,
        [df,          df_tod],
        ["Fixed Timer Baseline", "TOD Scheduled Timer"],
        ["steelblue",  "darkorange"]
    ):
        ax.plot(data["time"], data["total_waiting_time"],
                color=color, linewidth=0.8, label=label)
        add_spans(ax)
        ax.set_title(label, fontsize=12)
        ax.set_ylabel("Total Waiting Time (seconds)")
        ax.set_xlabel("Simulation Time (s)")
        ax.legend(loc="upper right", fontsize=8)
    plt.suptitle("Fixed Timer vs TOD — Waiting Time Side by Side",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fixed_vs_tod_waiting_sidebyside.png"), dpi=150)
    print("Saved fixed_vs_tod_waiting_sidebyside.png")

# ── 4. Markov Chain Transition Matrix ────────────────────────────────
print("\n" + "=" * 50)
print("  MARKOV CHAIN — TRANSITION PROBABILITIES")
print("=" * 50)

def markov_transitions(states):
    n        = len(states) - 1
    P_00_num = sum(1 for i in range(n) if states[i]==0 and states[i+1]==0)
    P_11_num = sum(1 for i in range(n) if states[i]==1 and states[i+1]==1)
    n_0      = sum(1 for i in range(n) if states[i]==0)
    n_1      = sum(1 for i in range(n) if states[i]==1)
    P_00 = P_00_num / max(n_0, 1)
    P_01 = 1 - P_00
    P_11 = P_11_num / max(n_1, 1)
    P_10 = 1 - P_11
    return P_00, P_01, P_10, P_11

S_fixed            = df["congestion_state"].values
P00f, P01f, P10f, P11f = markov_transitions(S_fixed)

print(f"  Fixed Timer:")
print(f"    P(non-cong → non-cong) P00 = {P00f:.3f}")
print(f"    P(non-cong → cong)     P01 = {P01f:.3f}")
print(f"    P(cong     → cong)     P11 = {P11f:.3f}")
print(f"    P(cong     → non-cong) P10 = {P10f:.3f}")

if tod_available:
    S_tod                  = df_tod["congestion_state"].values
    P00t, P01t, P10t, P11t = markov_transitions(S_tod)
    print(f"\n  TOD Timer:")
    print(f"    P(non-cong → non-cong) P00 = {P00t:.3f}")
    print(f"    P(non-cong → cong)     P01 = {P01t:.3f}")
    print(f"    P(cong     → cong)     P11 = {P11t:.3f}")
    print(f"    P(cong     → non-cong) P10 = {P10t:.3f}")
print("=" * 50)

# ── 5. Chernoff Bound for Poisson Arrivals ────────────────────────────
print("\n" + "=" * 50)
print("  CHERNOFF BOUND — POISSON ARRIVAL TAIL PROBABILITIES")
print("=" * 50)

import math

def chernoff_poisson(lam, delta):
    """
    Chernoff bound for Poisson(lam):
    P(N >= (1+delta)*lam) <= (e^delta / (1+delta)^(1+delta))^lam
    """
    return (math.exp(delta) / ((1 + delta) ** (1 + delta))) ** lam

lambdas    = {"Off-peak": 0.17 * 3, "Build-up": 0.42 * 3, "Peak Hour": 0.50 * 3}
deltas     = [0.5, 1.0, 2.0]

for phase, lam in lambdas.items():
    print(f"\n  {phase} (λΔt = {lam:.2f}):")
    for d in deltas:
        bound    = chernoff_poisson(lam, d)
        threshold = (1 + d) * lam
        print(f"    P(N >= {threshold:.2f}) <= {bound:.6f}  [δ={d}]")
print("=" * 50)

# ── Plot 5: Chernoff Bound Visualization ─────────────────────────────
fig, ax = plt.subplots(figsize=(10, 4))

delta_range = np.linspace(0.01, 3.0, 200)
colors_ch   = {"Off-peak": "green", "Build-up": "orange", "Peak Hour": "red"}

for phase, lam in lambdas.items():
    bounds     = [chernoff_poisson(lam, d) for d in delta_range]
    thresholds = [(1 + d) * lam for d in delta_range]
    ax.plot(thresholds, bounds, color=colors_ch[phase],
            linewidth=1.5, label=f"{phase} (λΔt={lam:.2f})")

ax.set_title("Chernoff Bound — P(Arrivals ≥ threshold) for Poisson Demand Phases", fontsize=13)
ax.set_xlabel("Arrival Threshold (vehicles per 3s interval)")
ax.set_ylabel("Probability Upper Bound")
ax.set_yscale("log")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "chernoff_bound.png"), dpi=150)
print("Saved chernoff_bound.png")
