# Decision Control for Traffic Signal
### Probabilistic Adaptive Signal Control at a 4-Way Intersection

---

## Problem Statement

Traffic signals operating on fixed schedules cannot respond to real-time variations in vehicle demand. This project models a 4-way urban intersection using a **Non-Homogeneous Poisson Process** to capture stochastic vehicle arrivals, and implements three progressively intelligent signal controllers:

1. **Fixed Timer** — deterministic baseline
2. **Time-of-Day (ToD)** — schedule-aware but static
3. **Adaptive Probabilistic Controller** — real-time queue-reactive with starvation guarantees

We demonstrate that a probabilistic, threshold-gated approach outperforms deterministic controllers by **37.2% in mean vehicle waiting time**, reducing it from 447s to 281s under identical demand conditions.

---

## Random Variables

- **Arrivals in time interval** — Number of vehicles arriving at the crossroads in one interval Δt is random, denoted by A(t) ~ Poisson(λ(t)·Δt)
- **Arrival rate λ** — Treated as uncertain; varies by time-of-day across three demand phases
- **Input flow q_in(k)** — Stochastic at each time step k due to random arrivals
- **Output flow q_out(k)** — Depends on signal state u(k) (green/red) and current queue length
- **Congestion state** — Binary: congested if queue > dynamic threshold T(t), else non-congested
- **State transitions** — Queue evolves as Q(t+1) = max(Q(t) + A(t) − D(t), 0); state changes modeled via transition probabilities

---

## Stochastic Modeling of Traffic Flow

Vehicle arrivals at each direction (N, S, E, W) are modeled as independent Non-Homogeneous Poisson streams. The arrival rate λ(t) changes with the time-of-day demand phase:

| Phase | Time Window | λ (veh/s) | Approx. Flow |
|-------|-------------|-----------|--------------|
| Off-peak | 0 – 50s | 0.17 | ~200 veh/hr |
| Build-up | 50 – 150s | 0.42 | ~500 veh/hr |
| Peak Hour | 150 – 300s | 0.50 | ~600 veh/hr |

The dynamic threshold (followed in adaptive controller) is computed as:

```
T(t) = ceil( λ(t) × DELTA_T × THRESHOLD_K )
     = ceil( λ(t) × 3 × 4 )
```

This means the threshold tightens automatically as traffic grows — the adaptive controller becomes more reactive during peak hours without any manual tuning.

---

## Project Structure

```
code/
├── data/
│   ├── demand.rou.xml              # Poisson-distributed vehicle demand
│   ├── edges.edg.xml               # Road edge definitions
│   ├── intersection.net.xml        # SUMO compiled network
│   ├── nodes.nod.xml               # Intersection node definitions
│   ├── sensors.add.xml             # Lane-area detectors (e2 detectors)
│   ├── simulation_log.csv          # Fixed timer simulation output
│   ├── simulation_log_tod.csv      # ToD simulation output
│   └── simulation_log_random.csv   # Adaptive controller output
│
├── experiments/
│   ├── chebyshev_histogram.png         # Chebyshev inequality visualization
│   ├── chernoff_bound.png              # Chernoff bounds for burst arrivals
│   ├── fixed_vs_tod_queue_sidebyside.png
│   ├── fixed_vs_tod_waiting_sidebyside.png
│   ├── m4_queue_all_three.png          # Queue comparison — all 3 controllers
│   ├── m4_waiting_all_three.png        # Waiting time — all 3 controllers
│   ├── m4_metrics_barchart.png         # Summary bar chart
│   ├── m4_chebyshev_all_three.png      # Chebyshev bounds across controllers
│   ├── m4_probability_evolution.png    # Direction probability over time
│   ├── m4_skip_counts.png              # Per-direction skip count tracking
│   └── m4_green_duration_dist.png      # Green phase duration distribution
│
├── src/
│   ├── generate_demand.py          # Generates Poisson traffic demand
│   ├── runner.py                   # Fixed timer simulation (Algorithm 1)
│   ├── runner_tod.py               # Time-of-Day simulation (Algorithm 2)
│   ├── runner_random.py            # Adaptive controller (Algorithm 3)
│   └── analysis.py                 # Statistical analysis and all plots
│
└── requirements.txt
```

---

## Prerequisites

### 1. Install SUMO
Download from: https://sumo.dlr.de/docs/Downloads.php

Set the environment variable:

```bash
# Windows
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

# Linux / Mac
export SUMO_HOME=/usr/share/sumo
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## How to Run

Navigate to the project directory first:

```bash
cd code
```

---

### Step 1 — Generate Traffic Demand

```bash
python src/generate_demand.py
```

Generates `data/demand.rou.xml` with Poisson-distributed vehicle arrivals.
This file is shared by all three simulations and only needs to be generated once.

---

### Step 2a — Fixed Timer Simulation (Baseline)

```bash
python src/runner.py
```

Runs the **8-phase fixed-timer** signal controller in SUMO-GUI.
Each phase gets a fixed green duration regardless of traffic conditions.

Output: `data/simulation_log.csv`

---

### Step 2b — Time-of-Day Simulation

```bash
python src/runner_tod.py
```

Runs the **Time-of-Day (ToD)** scheduled controller.
Green durations are pre-assigned per demand phase but do not react to real-time queues.

| Demand Phase | Time Window | Green Duration |
|--------------|-------------|----------------|
| Off-peak | 0 – 50s | 15s |
| Build-up | 50 – 150s | 25s |
| Peak Hour | 150 – 300s | 40s |

Output: `data/simulation_log_tod.csv`

---

### Step 2c — Adaptive Probabilistic Controller

```bash
python src/runner_random.py
```

Runs the **Adaptive Probabilistic Controller** (Algorithm 3).
Reads live detector data every 3 seconds and makes real-time switching decisions
based on predictive queue estimates and a dynamic congestion threshold.

Output: `data/simulation_log_random.csv`

---

### Step 3 — Analyse and Compare All Three Controllers

```bash
python src/analysis.py
```

Reads all three simulation logs and generates all output charts in `experiments/`.

---

## Algorithm 3 — Adaptive Probabilistic Controller

This is the core contribution of the project. Every **DELTA_T = 3 seconds**, the controller:

1. **Reads live detector counts** from all 8 lane-area sensors (2 per direction)
2. **Computes a predictive queue** estimate:
   ```
   Q*(dir) = Q_current(dir) + λ(t) × Δt / 4
   ```
3. **Computes the dynamic threshold** T(t) from the current arrival rate
4. **Applies the green phase rules** (in priority order):

| Rule | Condition | Action |
|------|-----------|--------|
| G_MAX | phase_timer ≥ 45s | Force switch — no direction monopolises the signal |
| G_MIN | phase_timer < 8s (peak) / 3s (off-peak) | Hold green — minimum service guarantee |
| All Empty | total_q == 0 | Hold green — nothing to serve elsewhere |
| Congestion | Q*(current) ≥ T(t) | Hold green — finish serving the busy lane |
| Urgent Cut | Another dir has Q* ≥ T(t) | Switch immediately to urgent lane |
| Drain Done | Current lane emptied, others waiting | Clean handoff — no timer waste |
| Drain Cap | phase_timer ≥ 2 × G_MIN | Rotate — prevent starvation on low-traffic lanes |

5. **Selects the next direction** using a 4-priority decision chain:

```
① SOLE       — Only one lane has vehicles → serve it directly
② URGENT     — Any lane Q* ≥ T(t) → serve the most congested
③ STARVE RESCUE — Any lane skipped 3+ times → guaranteed service
④ Lottery    — Weighted random pick: p ∝ Q* + starvation boost
```

The starvation boost in the lottery doubles exponentially with each extra skip:
```
boost = 2^(skip - MAX_SKIP) × q_max   when skip > MAX_SKIP
```

This ensures no lane waits more than 3 rotation cycles, even probabilistically.

---

## Output Plots

| File | Description |
|------|-------------|
| `chebyshev_histogram.png` | Queue distribution with Chebyshev probability bounds |
| `chernoff_bound.png` | Burst arrival probability under Poisson demand |
| `fixed_vs_tod_queue_sidebyside.png` | Queue: Fixed vs ToD |
| `fixed_vs_tod_waiting_sidebyside.png` | Waiting time: Fixed vs ToD |
| `m4_queue_all_three.png` | Queue length over time — all 3 controllers |
| `m4_waiting_all_three.png` | Waiting time over time — all 3 controllers |
| `m4_metrics_barchart.png` | Mean queue, variance, max queue, mean wait — side by side |
| `m4_chebyshev_all_three.png` | Chebyshev bounds applied to all 3 controllers |
| `m4_probability_evolution.png` | Per-direction selection probability over time |
| `m4_skip_counts.png` | Skip count per direction — fairness tracking |
| `m4_green_duration_dist.png` | Distribution of green phase durations |

---

## Performance Results

| Metric                              | Fixed Timer | Time-of-Day  | Randomized Adaptive |
|-------------------------------------|------------:|-------------:|--------------------:|
| Mean Waiting Time                   | 447s        | 648s         | 281s                |
| Peak Waiting Time                   | 1568s       | 2896s        | 1039s               |
| Congestion Persistence (stays busy) | 0.896       | 0.907        | 0.643               |
| Queue Clearing Speed                | baseline (0.104)   | 0.9× as fast  (0.093)   | 3.4× faster  (0.357)              |
| Improvement vs Fixed — Mean Wait    | baseline    | 44.8% higher | 37.2% lower       |
| Improvement vs Fixed — Mean Queue   | baseline    | 8.9% higher  | 2.6% lower        |

---

## Key Insights

1. **Fixed timers fail under stochastic demand**
   Queue spikes appear during peak periods because the controller cannot respond to burst arrivals. Chernoff bounds confirm that burst events are frequent enough to matter.

2. **ToD scheduling improves variance but not peak congestion**
   Adapting green durations to the time-of-day reduces queue fluctuation marginally, but the controller is still blind to real-time conditions within each phase.

3. **Adaptive probabilistic control delivers a 37.2% reduction in mean wait time**
   By combining a predictive queue estimate Q*, a dynamic threshold T(t), and a starvation-aware direction picker, the controller keeps mean waiting time at 281s versus the 447s fixed-timer baseline.

4. **Chebyshev and Chernoff bounds explain why deterministic approaches fail**
   The probability of burst arrivals exceeding a fixed threshold is non-negligible under Poisson demand. A reactive controller that tracks these deviations in real time is demonstrably superior.

5. **Fairness and efficiency are not in conflict**
   The starvation rescue mechanism guarantees every lane is served within 3 rotation cycles, while the weighted lottery ensures busier lanes are still prioritised — no trade-off between fairness and throughput.

---

## Probabilistic Analysis

### Chebyshev Inequality
Applied to queue lengths to identify the probability of extreme congestion events:
```
P(|Q − μ| ≥ kσ) ≤ 1/k²
```

### Chernoff Bound
Applied to Poisson arrival bursts to quantify tail risk:
```
P(X ≥ (1+δ)μ) ≤ e^(−μδ²/3)
```

### Jensen's Inequality Verification
Real traffic delay is higher than predicted using average queue values:
```
f(E[Q]) < E[f(Q)]
```
This confirms the nonlinear nature of congestion and validates why average-based fixed timers systematically underestimate delay.


## Members
- Swayam Prajapati
- Jay Daftari
- Hiya Soni
- Arya Patel
- Ahladita Chaudary