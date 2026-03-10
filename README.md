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

## How to Run
First, navigate to the project directory:
```bash
cd code
```

Then run the three steps in order.

### Step 1 — Generate Traffic Demand

```bash
python src/generate_demand.py
```

Generates `data/demand.rou.xml` with **Poisson-distributed vehicle arrivals**.

- **Off-peak (0–50s):** λ = 0.17 vehicles/s (~200 veh/hr)  
- **Build-up (50–150s):** λ = 0.42 vehicles/s (~500 veh/hr)  
- **Peak Hour (150–300s):** λ = 0.50 vehicles/s (~600 veh/hr)

---

### Step 2 — Run Simulation

```bash
python src/runner.py
```

Opens **SUMO-GUI** and runs the simulation.  
Logs queue length, waiting time, and congestion state every **3 seconds** to:

```
data/simulation_log.csv
```

---

### Step 3 — Analyse Results

```bash
python src/analysis.py
```

Produces the following output plots:

- `experiments/queue_vs_time.png`
- `experiments/waiting_time_vs_time.png`
- `experiments/chebyshev_histogram.png`

Console output includes:

- Variance calculation
- Jensen's Inequality verification
- Statistical summary of traffic metrics


## Members
- Swayam Prajapati
- Hiya Soni  
- Jay Daftari 
- Arya Patel 
- Ahladita Chaudary
