# DECISION CONTROL FOR TRAFFIC SIGNAL 
## Problem Statement 
We are examining traffic lights that are not adjusting per the movement of traffic. We approximate the intersection by modeling it with Markov Decision Process (MDP) and by a Poisson distribution to deal with uncertainty in the arrival of cars at the intersection. This allows us to create a system that is able to make decisions on-the-fly. We aim to identify optimal signal timing that reduces driver waiting time, indicating that a probabilistic approach is superior to fixed-schedule controllers.

## Random Variables
- **Arrivals in time interval**: Number of vehicles arriving at the cross
roads in one interval ∆t is random. We denote this arrival count by
n.
- **Arrival rate λ**: The arrival rate is also treated as uncertain as it can
fluctuate around accordingly with time.
- **Input flow qin(k)**: Since arrivals are random, the input flow becomes
random at each time step k.
- **Output flow qout(k)**: The output flow is also uncertain because it
depends on the signal u(k) (green or red) and the current queue.
- **Congestion state**: Each movement can be placed into one of two
states using a queue threshold: if queue > threshold it is congested,
otherwise it is non-congested.
- **State transitions**: Because arrivals and departures change the queue,
the congestion/non-congestion state can change over time, so we can
model this using transition probabilities between states.

## Stochastic Modeling of Traffic Flow at a Four-Way Intersection (M3 Simulation)

A SUMO-based traffic simulation that shows the 
deterministic fixed-timer signals using
Jensen's Inequality and Poisson arrival modeling.

---

## Project Structure

```
code/
├── data/
│   ├── demand.rou.xml          # Generated vehicle demand (Poisson arrivals)
│   ├── edges.edg.xml           # Road edge definitions
│   ├── intersection.net.xml    # SUMO compiled network
│   ├── nodes.nod.xml           # Node definitions for the intersection
│   ├── sensors.add.xml         # Lane-area detectors 
│   └── simulation_log.csv      # Generated automatically during simulation
│
├── experiments/
│   ├── chebyshev_histogram.png    # Chebyshev inequality visualization
│   ├── queue_vs_time.png          # Queue length vs simulation time
│   └── waiting_time_vs_time.png   # Vehicle waiting time vs time
│
├── src/
│   ├── analysis.py             # Statistical analysis and plotting
│   ├── generate_demand.py      # Generates Poisson traffic demand
│   └── runner.py               # Runs SUMO simulation via TraCI
│
└── requirements.txt            # Python dependencies
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

# How to Run

First, navigate to the project directory:

```bash
cd code
```

Then run the steps in order.

---

### Step 1 — Generate Traffic Demand

```bash
python src/generate_demand.py
```

Generates `data/demand.rou.xml` with **Poisson-distributed vehicle arrivals**.

This file is shared by both simulations — it only needs to be generated once.

### Demand Profile

- **Off-peak (0–50s):** λ = 0.17 vehicles/s (~200 veh/hr)
- **Build-up (50–150s):** λ = 0.42 vehicles/s (~500 veh/hr)
- **Peak Hour (150–300s):** λ = 0.50 vehicles/s (~600 veh/hr)

---

### Step 2a — Run Fixed Timer Simulation (Baseline)

```bash
python src/runner.py
```

Opens **SUMO-GUI** and runs the **8-phase fixed-timer simulation**.

Metrics recorded every **3 seconds**:

- Queue length  
- Waiting time  
- Congestion state  

Results are saved to:

```
data/simulation_log.csv
```

---

### Step 2b — Run TOD Timer Simulation (Deterministic Controller)

```bash
python src/runner_tod.py
```

Opens **SUMO-GUI** and runs the **Time-of-Day (TOD) scheduled timer simulation**.

Green durations adapt to the demand phase (**off-peak / build-up / peak**).

Results are logged every **3 seconds** to:

```
data/simulation_log_tod.csv
```

### TOD Signal Timing

| Demand Phase | Time Window | Green Duration |
|---------------|-------------|----------------|
| Off-peak | 0 – 50s | 15s |
| Build-up | 50 – 150s | 25s |
| Peak Hour | 150 – 300s | 40s |

---

# Step 3 — Analyse and Compare Results

```bash
python src/analysis.py
```

Reads both simulation logs and produces all output charts.

---

# Output Plots

The analysis script generates the following plots inside the `experiments/` directory.

| File | Description |
|-----|-------------|
| `chebyshev_histogram.png` | Queue distribution comparison with Chebyshev probability bounds |
| `chernoff_bound.png` | Chernoff bounds showing probability of burst arrivals under Poisson demand |
| `fixed_vs_tod_queue_sidebyside.png` | Queue length comparison over time for Fixed vs TOD controller |
| `fixed_vs_tod_waiting_sidebyside.png` | Waiting time comparison over time for Fixed vs TOD controller |

---

# Plot Analysis (Summary)

The analysis script generates several plots comparing the **Fixed Timer** controller with the **Time-of-Day (TOD)** scheduled controller.

## Queue Distribution with Chebyshev Bounds

This plot compares the **distribution of queue lengths** for both controllers and overlays Chebyshev bounds.

Key points:
- Both controllers produce **similar queue distributions**
- Maximum queue length observed is **around 10 vehicles**
- TOD slightly reduces **queue variance**, indicating marginally more stable traffic flow

---

## Chernoff Bounds for Poisson Arrivals

This plot analyzes **arrival burst probabilities** using Chernoff bounds under Poisson traffic demand.

Key points:
- Off-peak traffic rarely produces burst arrivals
- Burst arrivals become more probable during **build-up and peak phases**
- This randomness explains why deterministic controllers struggle during heavy demand

---

## Queue Length Comparison

This plot compares **queue length over time** for Fixed Timer and TOD scheduling.

Key points:
- Queues increase significantly during the **peak demand phase**
- TOD scheduling results in **slightly smoother queue behavior**
- However, maximum queue levels remain similar for both controllers

---

## Waiting Time Comparison

This plot compares **total waiting time accumulated by vehicles**.

Key points:
- Waiting time increases rapidly during **peak traffic periods**
- TOD scheduling does not significantly reduce delay
- Both controllers are limited when traffic arrivals become highly stochastic

---

# Console Output

The analysis script prints:

### Statistical Summary
- Mean queue length
- Median queue length
- Variance
- Standard deviation

### Jensen's Inequality Verification
This compares:

```
f(E[Q])  vs  E[f(Q)]
```

Result:

Real traffic delay is **higher than predicted using average queue values**, confirming the nonlinear nature of traffic congestion.

---

### Comparison Metrics

The script also reports:

- Mean queue length comparison
- Variance comparison
- Maximum queue observed
- Queue reduction percentage
- Variance reduction
- Jensen gap difference

These metrics quantify whether the TOD controller improves stability compared to the fixed-timer baseline.

---

# Key Insights from the Experiment

From the simulation results we observe:


1. **Fixed timers cannot adapt to demand changes**  
   Queue spikes appear during peak periods.

2. **TOD scheduling improves stability slightly**  
   Variance of queue lengths decreases, meaning queues fluctuate less.

3. **However TOD does not fully eliminate congestion**  
   Peak demand still creates large queues and long waiting times.

4. **This suggests adaptive control is needed**  
   A dynamic controller (MDP or reinforcement learning) could react to real-time queue conditions instead of relying on predetermined schedules.

---

## Members
- Swayam Prajapati
- Hiya Soni  
- Jay Daftari 
- Arya Patel 
- Ahladita Chaudary
