import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


BASE     = os.path.dirname(os.path.abspath(__file__))
LOG_FIX  = os.path.join(BASE, "../data/simulation_log.csv")
LOG_TOD  = os.path.join(BASE, "../data/simulation_log_tod.csv")
LOG_RND  = os.path.join(BASE, "../data/simulation_log_random.csv")
OUT_DIR  = os.path.join(BASE, "../experiments")
os.makedirs(OUT_DIR, exist_ok=True)


# ── Load Data ─────────────────────────────────────────────────────────
df_fix = pd.read_csv(LOG_FIX)
df_tod = pd.read_csv(LOG_TOD)
rnd_available = os.path.exists(LOG_RND)
if rnd_available:
    df_rnd = pd.read_csv(LOG_RND)
    print(f"Randomized log loaded: {len(df_rnd)} rows")


# ── Helpers ───────────────────────────────────────────────────────────
def add_spans(ax):
    ax.axvspan(0,   50,  alpha=0.05, color="green",  label="Off-peak (λ=0.17)")
    ax.axvspan(50,  150, alpha=0.05, color="orange", label="Build-up (λ=0.42)")
    ax.axvspan(150, 300, alpha=0.08, color="red",    label="Peak Hour (λ=0.50)")


def markov_transitions(states, name):
    n    = len(states) - 1
    n0   = sum(1 for i in range(n) if states[i] == 0)
    n1   = sum(1 for i in range(n) if states[i] == 1)
    p00  = sum(1 for i in range(n) if states[i]==0 and states[i+1]==0) / max(n0, 1)
    p11  = sum(1 for i in range(n) if states[i]==1 and states[i+1]==1) / max(n1, 1)
    print(f"\n  {name} Markov Transitions:")
    print(f"    P00={p00:.3f}  P01={1-p00:.3f}  P11={p11:.3f}  P10={1-p11:.3f}")
    return p00, 1-p00, 1-p11, p11


def chernoff_poisson(lam, delta):
    return (math.exp(delta) / ((1 + delta) ** (1 + delta))) ** lam


def stats(df, name):
    Q  = df["total_queue"].values
    W  = df["total_waiting_time"].values
    mu = Q.mean()
    sd = Q.std()
    f_EQ = mu ** 2
    Ef_Q = (Q ** 2).mean()
    print(f"\n{'='*52}\n  {name}\n{'='*52}")
    print(f"  Mean Queue  E[Q]   = {mu:.2f}")
    print(f"  Median             = {np.median(Q):.2f}")
    print(f"  Variance  Var(Q)   = {Q.var():.2f}")
    print(f"  Std Dev   σ(Q)     = {sd:.2f}")
    print(f"  Max Queue          = {Q.max()}")
    print(f"  Mean Wait E[W]     = {W.mean():.2f}s")
    print(f"  Peak Wait max(W)   = {W.max():.2f}s")
    print(f"  Jensen Gap         = {Ef_Q - f_EQ:.2f}  (lower=better)")
    return mu, Q.var(), Q.max(), W.mean(), sd


# ════════════════════════════════════════════════════════════════════
# SECTION 1 — M3: Fixed Timer vs TOD (Stats + Markov + Chernoff)
# ════════════════════════════════════════════════════════════════════
print("\n" + "█"*52)
print("  M3 ANALYSIS — FIXED TIMER vs TOD")
print("█"*52)

Q      = df_fix["total_queue"].values
mu     = Q.mean()
sigma  = Q.std()
f_EQ   = mu**2
Ef_Q   = (Q**2).mean()

print(f"\n  Fixed Timer — Jensen Gap: {Ef_Q - f_EQ:.2f}")

Q_tod   = df_tod["total_queue"].values
mu_tod  = Q_tod.mean()
sig_tod = Q_tod.std()
f_EQ_t  = mu_tod**2
Ef_Q_t  = (Q_tod**2).mean()
print(f"  TOD Timer   — Jensen Gap: {Ef_Q_t - f_EQ_t:.2f}")
print(f"\n  Queue Reduction (TOD vs Fixed) : {(mu - mu_tod)/mu*100:.1f}%")
print(f"  Variance Drop                  : {(Q.var()-Q_tod.var())/Q.var()*100:.1f}%")

markov_transitions(df_fix["congestion_state"].values, "Fixed Timer")
markov_transitions(df_tod["congestion_state"].values, "TOD Timer")

lambdas = {"Off-peak": 0.17*3, "Build-up": 0.42*3, "Peak Hour": 0.50*3}
print(f"\n  Chernoff Bound — Poisson Tail Probabilities")
for phase, lam in lambdas.items():
    print(f"\n  {phase} (λΔt={lam:.2f}):")
    for d in [0.5, 1.0, 2.0]:
        print(f"    P(N >= {(1+d)*lam:.2f}) <= {chernoff_poisson(lam,d):.6f}  [δ={d}]")


# ── M3 Plot 1: Chebyshev Histogram Fixed vs TOD ───────────────────────
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(Q,     bins=40, color="steelblue", density=True, alpha=0.6,
        edgecolor="white", label="Fixed Timer")
ax.hist(Q_tod, bins=40, color="seagreen",  density=True, alpha=0.6,
        edgecolor="white", label="TOD Timer")
for k, c in zip([1,2,3], ["gold","orange","red"]):
    ax.axvline(mu     + k*sigma,   linestyle="--", color=c, linewidth=1.2,
               label=f"Fixed μ+{k}σ → P≤{1/k**2:.2f}")
    ax.axvline(mu_tod + k*sig_tod, linestyle=":",  color=c, linewidth=1.2,
               label=f"TOD   μ+{k}σ → P≤{1/k**2:.2f}")
ax.set_title("Queue Distribution with Chebyshev Bounds — Fixed vs TOD",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Queue Length (vehicles)")
ax.set_ylabel("Density")
ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m3_chebyshev_fixed_tod.png"), dpi=150)
print("\nSaved m3_chebyshev_fixed_tod.png")


# ── M3 Plot 2: Queue Side by Side ────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
for ax, data, label, color in zip(
    axes,
    [df_fix, df_tod],
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
plt.suptitle("Fixed Timer vs TOD — Queue Length",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m3_queue_fixed_tod.png"), dpi=150)
print("Saved m3_queue_fixed_tod.png")


# ── M3 Plot 3: Waiting Time Side by Side ─────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
for ax, data, label, color in zip(
    axes,
    [df_fix, df_tod],
    ["Fixed Timer Baseline", "TOD Scheduled Timer"],
    ["steelblue", "darkorange"]
):
    ax.plot(data["time"], data["total_waiting_time"],
            color=color, linewidth=0.8, label=label)
    add_spans(ax)
    ax.set_title(label, fontsize=12)
    ax.set_ylabel("Total Waiting Time (seconds)")
    ax.set_xlabel("Simulation Time (s)")
    ax.legend(loc="upper right", fontsize=8)
plt.suptitle("Fixed Timer vs TOD — Waiting Time",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m3_waiting_fixed_tod.png"), dpi=150)
print("Saved m3_waiting_fixed_tod.png")


# ── M3 Plot 4: Chernoff Bound Curve ──────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 4))
delta_range  = np.linspace(0.01, 3.0, 200)
colors_phase = {"Off-peak": "green", "Build-up": "orange", "Peak Hour": "red"}
for phase, lam in lambdas.items():
    bounds     = [chernoff_poisson(lam, d) for d in delta_range]
    thresholds = [(1+d)*lam for d in delta_range]
    ax.plot(thresholds, bounds, color=colors_phase[phase],
            linewidth=1.5, label=f"{phase} (λΔt={lam:.2f})")
ax.set_title("Chernoff Bound — P(Arrivals ≥ threshold) per Demand Phase",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Arrival Threshold (vehicles / 3s)")
ax.set_ylabel("Probability Upper Bound")
ax.set_yscale("log")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m3_chernoff_bound.png"), dpi=150)
print("Saved m3_chernoff_bound.png")


# ════════════════════════════════════════════════════════════════════
# SECTION 2 — M4: All Three Controllers
# ════════════════════════════════════════════════════════════════════
print("\n" + "█"*52)
print("  M4 ANALYSIS — ALL THREE CONTROLLERS")
print("█"*52)

m_fix, v_fix, mx_fix, w_fix, s_fix = stats(df_fix, "FIXED TIMER")
m_tod, v_tod, mx_tod, w_tod, s_tod = stats(df_tod, "TOD TIMER")
if rnd_available:
    m_rnd, v_rnd, mx_rnd, w_rnd, s_rnd = stats(df_rnd, "RANDOMIZED ADAPTIVE")
    print(f"\n  Improvement: Randomized vs Fixed")
    print(f"  Mean Queue  : {(m_fix-m_rnd)/m_fix*100:.1f}% reduction")
    print(f"  Variance    : {(v_fix-v_rnd)/v_fix*100:.1f}% reduction")
    print(f"  Mean Wait   : {(w_fix-w_rnd)/w_fix*100:.1f}% reduction")
    print(f"  Max Queue   : {mx_fix - mx_rnd} vehicles less")

markov_transitions(df_fix["congestion_state"].values, "Fixed Timer")
markov_transitions(df_tod["congestion_state"].values, "TOD Timer")
if rnd_available:
    markov_transitions(df_rnd["congestion_state"].values, "Randomized")

datasets = [
    (df_fix, "Fixed Timer Baseline",  "crimson"),
    (df_tod, "TOD Scheduled Timer",   "steelblue"),
]
if rnd_available:
    datasets.append((df_rnd, "Randomized Adaptive", "darkorchid"))
rows = len(datasets)


# ── M4 Plot 1: Queue — All Three ─────────────────────────────────────
fig, axes = plt.subplots(rows, 1, figsize=(13, 4*rows), sharex=False)
for ax, (data, label, color) in zip(axes, datasets):
    ax.plot(data["time"], data["total_queue"],
            color=color, linewidth=0.9, label=label)
    if "dynamic_threshold" in data.columns:
        ax.plot(data["time"], data["dynamic_threshold"],
                color="black", linewidth=1.2, linestyle="--",
                label="Dynamic Threshold T(t)")
    else:
        ax.axhline(3, linestyle="--", color="gray", linewidth=1,
                   label="Threshold T=3")
    add_spans(ax)
    ax.set_title(label, fontsize=12, fontweight="bold")
    ax.set_ylabel("Queue Length (vehicles)")
    ax.set_xlabel("Simulation Time (s)")
    ax.legend(loc="upper right", fontsize=7)
plt.suptitle("Queue Length: Fixed Timer vs TOD vs Randomized Adaptive",
             fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m4_queue_all_three.png"), dpi=150)
print("\nSaved m4_queue_all_three.png")


# ── M4 Plot 2: Waiting Time — All Three ──────────────────────────────
fig, axes = plt.subplots(rows, 1, figsize=(13, 4*rows), sharex=False)
for ax, (data, label, color) in zip(axes, datasets):
    ax.plot(data["time"], data["total_waiting_time"],
            color=color, linewidth=0.9, label=label)
    add_spans(ax)
    ax.set_title(label, fontsize=12, fontweight="bold")
    ax.set_ylabel("Total Waiting Time (seconds)")
    ax.set_xlabel("Simulation Time (s)")
    ax.legend(loc="upper right", fontsize=7)
plt.suptitle("Waiting Time: Fixed Timer vs TOD vs Randomized Adaptive",
             fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m4_waiting_all_three.png"), dpi=150)
print("Saved m4_waiting_all_three.png")


# ── M4 Plot 3: Metrics Bar Chart ─────────────────────────────────────
metrics  = ["Mean Queue\nE[Q]", "Std Dev\nσ(Q)", "Max Queue", "Mean Wait\n(÷10)"]
fix_vals = [m_fix, s_fix, mx_fix, w_fix/10]
tod_vals = [m_tod, s_tod, mx_tod, w_tod/10]
fig, ax  = plt.subplots(figsize=(10, 5))
x  = np.arange(len(metrics))
bw = 0.25
ax.bar(x - bw, fix_vals, bw, label="Fixed Timer", color="crimson",   alpha=0.85)
ax.bar(x,      tod_vals, bw, label="TOD Timer",   color="steelblue", alpha=0.85)
for i, v in enumerate(fix_vals):
    ax.text(x[i]-bw, v+0.1, f"{v:.1f}", ha="center", fontsize=8, color="crimson")
for i, v in enumerate(tod_vals):
    ax.text(x[i],    v+0.1, f"{v:.1f}", ha="center", fontsize=8, color="steelblue")
if rnd_available:
    rnd_vals = [m_rnd, s_rnd, mx_rnd, w_rnd/10]
    ax.bar(x+bw, rnd_vals, bw, label="Randomized", color="darkorchid", alpha=0.85)
    for i, v in enumerate(rnd_vals):
        ax.text(x[i]+bw, v+0.1, f"{v:.1f}", ha="center", fontsize=8, color="darkorchid")
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=11)
ax.set_ylabel("Value (Mean Wait ÷10 for scale)", fontsize=10)
ax.set_title("Performance Metrics — All Three Controllers",
             fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m4_metrics_barchart.png"), dpi=150)
print("Saved m4_metrics_barchart.png")


# ── M4 Plot 4: Chebyshev — All Three ─────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 5))
ax.hist(df_fix["total_queue"], bins=40, color="crimson",   density=True,
        alpha=0.5, label="Fixed Timer",  edgecolor="white")
ax.hist(df_tod["total_queue"], bins=40, color="steelblue", density=True,
        alpha=0.5, label="TOD Timer",    edgecolor="white")
if rnd_available:
    Q_rnd = df_rnd["total_queue"].values
    ax.hist(Q_rnd, bins=40, color="darkorchid", density=True,
            alpha=0.5, label="Randomized", edgecolor="white")
    for k, c in zip([1,2,3], ["gold","orange","red"]):
        ax.axvline(m_fix + k*s_fix, linestyle="--", color=c, linewidth=1.2,
                   label=f"Fix μ+{k}σ → P≤{1/k**2:.2f}")
        ax.axvline(Q_rnd.mean() + k*Q_rnd.std(), linestyle=":", color=c,
                   linewidth=1.5, label=f"Rnd μ+{k}σ → P≤{1/k**2:.2f}")
else:
    for k, c in zip([1,2,3], ["gold","orange","red"]):
        ax.axvline(m_fix + k*s_fix, linestyle="--", color=c, linewidth=1.2,
                   label=f"Fix μ+{k}σ → P≤{1/k**2:.2f}")
ax.set_title("Queue Distribution with Chebyshev Bounds — All Three Controllers",
             fontsize=12, fontweight="bold")
ax.set_xlabel("Queue Length (vehicles)")
ax.set_ylabel("Density")
ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "m4_chebyshev_all_three.png"), dpi=150)
print("Saved m4_chebyshev_all_three.png")


# ════════════════════════════════════════════════════════════════════
# SECTION 3 — M4 Randomized-Specific Plots (IMPROVED)
# ════════════════════════════════════════════════════════════════════
if rnd_available:

    # ── M4 Plot 5: Stacked Area — Phase Selection Probabilities ──────
    # CHANGED from noisy 4-line overlap → stacked area shows share cleanly
    if "p_N" in df_rnd.columns:
        fig, ax = plt.subplots(figsize=(13, 5))
        time_vals = df_rnd["time"].values
        p_N = df_rnd["p_N"].values
        p_S = df_rnd["p_S"].values
        p_E = df_rnd["p_E"].values
        p_W = df_rnd["p_W"].values

        ax.stackplot(
            time_vals,
            p_N, p_S, p_E, p_W,
            labels=["North", "South", "East", "West"],
            colors=["#4477BB", "#44AA55", "#CC4444", "#EE9922"],
            alpha=0.85
        )
        # demand phase markers as vertical lines (not spans, less clutter)
        ax.axvline(50,  color="white", linestyle="--", linewidth=1.0, alpha=0.6)
        ax.axvline(150, color="white", linestyle="--", linewidth=1.0, alpha=0.6)
        ax.text(10,  0.97, "Off-peak",  color="white", fontsize=8, va="top", alpha=0.8)
        ax.text(60,  0.97, "Build-up",  color="white", fontsize=8, va="top", alpha=0.8)
        ax.text(160, 0.97, "Peak Hour", color="white", fontsize=8, va="top", alpha=0.8)
        ax.set_title(
            "Phase Selection Probability Share Over Time — Randomized Controller",
            fontsize=12, fontweight="bold"
        )
        ax.set_xlabel("Simulation Time (s)")
        ax.set_ylabel("Probability Share (sums to 1)")
        ax.set_ylim(0, 1)
        ax.legend(loc="lower right", fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "m4_probability_evolution.png"), dpi=150)
        print("Saved m4_probability_evolution.png")

    # ── M4 Plot 6: Green Duration Distribution (G_MAX fix: 45s) ──────
    # CHANGED: fixed G_MAX label from 60s → 45s (actual value)
    if "active_green_dur" in df_rnd.columns:
        fig, ax = plt.subplots(figsize=(10, 4))
        durations = df_rnd["active_green_dur"].dropna().values
        ax.hist(durations, bins=20, color="darkorchid", alpha=0.8, edgecolor="white")
        ax.axvline(8,  color="red",        linestyle="--", linewidth=1.5,
                   label="G_MIN = 8s (demand)  /  3s (post-demand)")
        ax.axvline(45, color="dodgerblue",  linestyle="--", linewidth=1.5,
                   label="G_MAX = 45s (hard ceiling)")
        # annotate the two regions
        ax.axvspan(0,  8,  alpha=0.07, color="red",       label="Below G_MIN (not expected)")
        ax.axvspan(45, ax.get_xlim()[1] if ax.get_xlim()[1] > 45 else 50,
                   alpha=0.07, color="dodgerblue", label="Above G_MAX (not possible)")
        ax.set_title("Distribution of Green Phase Durations — Randomized Controller",
                     fontsize=12, fontweight="bold")
        ax.set_xlabel("Green Duration (seconds)")
        ax.set_ylabel("Count")
        ax.legend(fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "m4_green_duration_dist.png"), dpi=150)
        print("Saved m4_green_duration_dist.png")

    # ── M4 Plot 7: Skip Count Heatmap ────────────────────────────────
    # CHANGED from 4 noisy spike lines → heatmap, one row per direction
    # colour = skip count, x = time → instantly readable
    if "skip_N" in df_rnd.columns:
        skip_data = np.array([
            df_rnd["skip_N"].values,
            df_rnd["skip_S"].values,
            df_rnd["skip_E"].values,
            df_rnd["skip_W"].values,
        ], dtype=float)
        time_vals = df_rnd["time"].values

        fig, axes = plt.subplots(
            2, 1, figsize=(13, 6),
            gridspec_kw={"height_ratios": [3, 1]}, sharex=True
        )

        # top: heatmap
        ax_heat = axes[0]
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "skip_cmap", ["#1a1a2e", "#16213e", "#f5a623", "#e74c3c"]
        )
        im = ax_heat.imshow(
            skip_data,
            aspect="auto",
            cmap=cmap,
            vmin=0, vmax=4,
            extent=[time_vals[0], time_vals[-1], -0.5, 3.5],
            interpolation="nearest"
        )
        ax_heat.set_yticks([0, 1, 2, 3])
        ax_heat.set_yticklabels(["West", "East", "South", "North"], fontsize=11)
        ax_heat.set_title(
            "Skip Count Heatmap Per Direction — Anti-Starvation Monitor\n"
            "(orange/red = approaching or exceeding MAX_SKIP=2, triggers STARVE RESCUE)",
            fontsize=11, fontweight="bold"
        )
        cbar = plt.colorbar(im, ax=ax_heat, orientation="vertical", pad=0.01)
        cbar.set_label("Consecutive Skips", fontsize=9)
        cbar.set_ticks([0, 1, 2, 3, 4])

        # vertical lines for demand phases
        for t, lbl in [(50, "Build-up"), (150, "Peak")]:
            ax_heat.axvline(t, color="white", linestyle="--", linewidth=1.0, alpha=0.5)
            ax_heat.text(t+2, 3.3, lbl, color="white", fontsize=7, alpha=0.7)

        # bottom: total skip across all directions over time (easy summary)
        ax_sum = axes[1]
        total_skip = skip_data.sum(axis=0)
        ax_sum.fill_between(time_vals, total_skip, color="darkorchid", alpha=0.7)
        ax_sum.axhline(2, color="red", linestyle="--", linewidth=1.0,
                       label="MAX_SKIP=2 per direction")
        ax_sum.set_ylabel("Total\nSkips", fontsize=9)
        ax_sum.set_xlabel("Simulation Time (s)")
        ax_sum.legend(fontsize=8, loc="upper right")

        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "m4_skip_counts.png"), dpi=150)
        print("Saved m4_skip_counts.png")


print("\n✓ All analysis complete — M3 + M4 unified.")
