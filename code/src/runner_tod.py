import os
import sys
import traci
import pandas as pd

if 'SUMO_HOME' not in os.environ:
    raise EnvironmentError(
        "SUMO_HOME environment variable is not set.\n"
        "Please install SUMO from https://sumo.dlr.de/docs/Downloads.php\n"
        "Then set SUMO_HOME to your SUMO installation folder."
    )

sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

# --- Paths ---
BASE     = os.path.dirname(os.path.abspath(__file__))
DATA     = os.path.join(BASE, "../data")
NET_FILE = os.path.join(DATA, "intersection.net.xml")
ROU_FILE = os.path.join(DATA, "demand.rou.xml")
ADD_FILE = os.path.join(DATA, "sensors.add.xml")
LOG_FILE = os.path.join(DATA, "simulation_log_tod.csv")

# --- SUMO Command ---
SUMO_CMD = [
    "sumo-gui",
    "-n", NET_FILE,
    "-r", ROU_FILE,
    "--additional-files", ADD_FILE,
    "--no-warnings", "true",
    "--step-length", "1",
    "--delay", "100"
]

DETECTORS = [
    "e2_N_0", "e2_N_1",
    "e2_S_0", "e2_S_1",
    "e2_E_0", "e2_E_1",
    "e2_W_0", "e2_W_1"
]

TL_ID   = "C"
T       = 3       # congestion threshold
DELTA_T = 3       # decision interval in seconds

# ── TOD Phase Plan ───────────────────────────────────────────────────
# Matches generate_demand.py lambda phases exactly
# 8-phase order: E-green, E-yellow, N-green, N-yellow,
#                W-green, W-yellow, S-green, S-yellow
# Indices:       0        1         2        3
#                4        5         6        7

def get_green_duration(sim_time):
    """Return green duration (seconds) based on time-of-day demand phase."""
    if sim_time < 50:
        return 15    # Off-peak  λ=0.17  ~200 veh/hr
    elif sim_time < 150:
        return 25    # Build-up  λ=0.42  ~500 veh/hr
    else:
        return 40    # Peak hour λ=0.50  ~600 veh/hr

YELLOW_DURATION = 3   # always fixed

# Phase index mapping in your tlLogic (8 phases, index 0–7)
GREEN_PHASES  = [0, 2, 4, 6]   # E, N, W, S green phases
YELLOW_PHASES = [1, 3, 5, 7]   # E, N, W, S yellow phases

# ────────────────────────────────────────────────────────────────────

traci.start(SUMO_CMD)
log   = []
step  = 0

# Track what phase we are in and how long it has been active
current_phase_index = 0          # which of the 4 green phases (0–3)
phase_timer         = 0          # seconds elapsed in current sub-phase
in_yellow           = False      # are we currently in yellow?

traci.trafficlight.setPhase(TL_ID, GREEN_PHASES[current_phase_index])
print("TOD Simulation started...")

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1
        t = traci.simulation.getTime()
        phase_timer += 1

        # ── TOD Phase Switching Logic ────────────────────────────────
        green_duration = get_green_duration(t)

        if not in_yellow:
            # Currently in green — check if green time is up
            if phase_timer >= green_duration:
                # Switch to yellow for this direction
                traci.trafficlight.setPhase(TL_ID, YELLOW_PHASES[current_phase_index])
                in_yellow   = True
                phase_timer = 0

        else:
            # Currently in yellow — check if yellow time is up
            if phase_timer >= YELLOW_DURATION:
                # Advance to next direction's green
                current_phase_index = (current_phase_index + 1) % 4
                traci.trafficlight.setPhase(TL_ID, GREEN_PHASES[current_phase_index])
                in_yellow   = False
                phase_timer = 0

        # ── Data Logging every DELTA_T seconds ──────────────────────
        if step % DELTA_T == 0:
            queues     = {d: traci.lanearea.getLastStepVehicleNumber(d) for d in DETECTORS}
            total_q    = sum(queues.values())
            vehicle_ids = traci.vehicle.getIDList()
            total_wait = sum(traci.vehicle.getWaitingTime(v) for v in vehicle_ids)
            congestion_state = int(total_q >= T)

            log.append({
                "time"               : t,
                "total_queue"        : total_q,
                "total_waiting_time" : total_wait,
                "congestion_state"   : congestion_state,
                "green_duration"     : green_duration,
                "tod_phase"          : ("off-peak" if t < 50 else "build-up" if t < 150 else "peak"),
                **queues
            })

            if step % 300 == 0:
                print(f"  t={int(t)}s | Q={total_q} | Sk={congestion_state} | green={green_duration}s")

except traci.exceptions.FatalTraCIError:
    print("Simulation ended (SUMO closed connection).")

finally:
    try:
        traci.close()
    except Exception:
        pass

df = pd.DataFrame(log)
df.to_csv(LOG_FILE, index=False)
print(f"\nDone. {len(df)} rows logged → {LOG_FILE}")
