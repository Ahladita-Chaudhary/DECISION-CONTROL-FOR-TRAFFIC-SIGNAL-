import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE     = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE, "../data/simulation_log.csv")
OUT_DIR  = os.path.join(BASE, "../experiments")
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(LOG_FILE)
Q  = df["total_queue"].values
mu, sigma = Q.mean(), Q.std()

# ── 1. Statistical Summary ───────────────────────────────────────────
print("=" * 45)
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
print(f"  Gap      = {Ef_Q - f_EQ:.2f}  ← fixed timer underestimates delay by this much")
print(f"  Jensen holds: {Ef_Q >= f_EQ}")
print("=" * 45)

# ── 3. Plot 1: Queue Length vs Time ──────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(df["time"], df["total_queue"], color="crimson", linewidth=0.8, label="Queue Length Qk")
ax.axhline(3, linestyle="--", color="gray", linewidth=1, label="Threshold T=3")

ax.axvspan(0,   50,  alpha=0.05, color="green",  label="Off-peak (λ=0.17)")
ax.axvspan(50,  150, alpha=0.05, color="orange", label="Build-up (λ=0.42)")
ax.axvspan(150, 300, alpha=0.08, color="red",    label="Peak Hour (λ=0.50)")

ax.set_xlim(0, df["time"].max() + 10)
ax.set_title("Queue Length vs Time — Fixed Timer Baseline (M3)", fontsize=13)
ax.set_xlabel("Simulation Time (s)")
ax.set_ylabel("Total Vehicles on Detectors")
ax.legend(loc="upper right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "queue_vs_time.png"), dpi=150)
print("Saved queue_vs_time.png")

# ── 4. Plot 2: Waiting Time vs Time ──────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(df["time"], df["total_waiting_time"], color="steelblue", linewidth=0.8, label="Total Waiting Time")
ax.axvspan(0,   50,  alpha=0.05, color="green",  label="Off-peak (λ=0.17)")
ax.axvspan(50,  150, alpha=0.05, color="orange", label="Build-up (λ=0.42)")
ax.axvspan(150, 300, alpha=0.08, color="red",    label="Peak Hour (λ=0.50)")

ax.set_xlim(0, df["time"].max() + 10)
ax.set_title("Total Vehicle Waiting Time vs Time — Fixed Timer Fails at Peak Hour", fontsize=13)
ax.set_xlabel("Simulation Time (s)")
ax.set_ylabel("Total Waiting Time (seconds)")
ax.legend(loc="upper right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "waiting_time_vs_time.png"), dpi=150)
print("Saved waiting_time_vs_time.png")

# ── 5. Plot 3: Chebyshev-bounded Queue Histogram ─────────────────────
fig, ax = plt.subplots(figsize=(9, 4))
ax.hist(Q, bins=40, color="steelblue", edgecolor="white", density=True, label="Observed Q")
colors = ["gold", "orange", "red"]
for k, c in zip([1, 2, 3], colors):
    bound = 1 / k**2
    ax.axvline(mu + k*sigma, linestyle="--", color=c,
               label=f"μ+{k}σ  →  P(exceed) ≤ {bound:.2f}")
ax.set_title("Queue Distribution with Chebyshev Bounds (M2 Validation)", fontsize=13)
ax.set_xlabel("Queue Length (vehicles)")
ax.set_ylabel("Density")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "chebyshev_histogram.png"), dpi=150)
print("Saved chebyshev_histogram.png")
