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
LOG_FILE = os.path.join(DATA, "simulation_log.csv")

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

T       = 3     # congestion threshold: Sk=1 if total_queue >= T
DELTA_T = 3     # Δt cycle in seconds (matches M2 model)

traci.start(SUMO_CMD)
log  = []
step = 0

print("Simulation started...")

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        if step % DELTA_T == 0:
            t = traci.simulation.getTime()

            # Qk from all 8 detectors
            queues  = {d: traci.lanearea.getLastStepVehicleNumber(d) for d in DETECTORS}
            total_q = sum(queues.values())

            # Total waiting time across all active vehicles
            vehicle_ids = traci.vehicle.getIDList()
            total_wait  = sum(traci.vehicle.getWaitingTime(v) for v in vehicle_ids)

            # Binary congestion state 
            congestion_state = int(total_q >= T)

            log.append({
                "time"               : t,
                "total_queue"        : total_q,
                "total_waiting_time" : total_wait,
                "congestion_state"   : congestion_state,
                **queues
            })

            if step % 300 == 0:
                print(f"  t={int(t)}s | Q={total_q} | Sk={congestion_state}")

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
