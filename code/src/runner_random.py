import os
import sys
import math
import numpy as np
import traci
import pandas as pd

if 'SUMO_HOME' not in os.environ:
    raise EnvironmentError(
        "SUMO_HOME environment variable is not set.\n"
        "Please install SUMO from https://sumo.dlr.de/docs/Downloads.php\n"
        "Then set SUMO_HOME to your SUMO installation folder."
    )

sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

# ── Paths ────────────────────────────────────────────────────────────
BASE     = os.path.dirname(os.path.abspath(__file__))
DATA     = os.path.join(BASE, "../data")
NET_FILE = os.path.join(DATA, "intersection.net.xml")
ROU_FILE = os.path.join(DATA, "demand.rou.xml")
ADD_FILE = os.path.join(DATA, "sensors.add.xml")
LOG_FILE = os.path.join(DATA, "simulation_log_random.csv")

SUMO_CMD = [
    "sumo-gui",
    "-n", NET_FILE,
    "-r", ROU_FILE,
    "--additional-files", ADD_FILE,
    "--no-warnings", "true",
    "--step-length", "1",
    "--delay", "100"
]

# ── Constants ────────────────────────────────────────────────────────
TL_ID       = "C"
DELTA_T     = 3
YELLOW_DUR  = 3
THRESHOLD_K = 4
MAX_SKIP    = 2
EPSILON     = 0.01
G_MAX       = 45
DEMAND_END  = 300
SAFETY_STOP = 700

def get_gmin(t):
    return 3 if t > DEMAND_END else 8   # ← v19: was 5, now 3 post-demand

# ── Detector & Phase Mappings ────────────────────────────────────────
DETECTORS = [
    "e2_N_0", "e2_N_1",
    "e2_S_0", "e2_S_1",
    "e2_E_0", "e2_E_1",
    "e2_W_0", "e2_W_1"
]
DIR_DETECTORS = {
    "N": ["e2_N_0", "e2_N_1"],
    "S": ["e2_S_0", "e2_S_1"],
    "E": ["e2_E_0", "e2_E_1"],
    "W": ["e2_W_0", "e2_W_1"],
}
GREEN_PHASES  = {"N": 2, "S": 6, "E": 0, "W": 4}
YELLOW_PHASES = {"N": 3, "S": 7, "E": 1, "W": 5}
DIRECTIONS    = ["N", "S", "E", "W"]

# ── Helpers ──────────────────────────────────────────────────────────
def get_lambda(t):
    if t < 50:    return 0.17
    elif t < 150: return 0.42
    else:         return 0.50

def get_threshold(t):
    return math.ceil(get_lambda(t) * DELTA_T * THRESHOLD_K)

def predictive_queue(q_current, lam):
    return q_current + (lam * DELTA_T) / 4.0

def compute_probabilities(q_star, skip_counts):
    q_values = [q_star[d] for d in DIRECTIONS]
    q_max    = max(q_values) if max(q_values) > 0 else 1.0
    weights  = []
    for d in DIRECTIONS:
        boost = 0.0
        if skip_counts[d] > MAX_SKIP:
            extra = skip_counts[d] - MAX_SKIP
            boost = (2 ** extra) * q_max
        weights.append(q_star[d] + EPSILON + boost)
    weights = np.array(weights)
    return weights / weights.sum()

def should_skip_empty(q_star_i, skip_count):
    return q_star_i < 0.1 and skip_count <= MAX_SKIP

def fresh_read(t):
    raw = {d: traci.lanearea.getLastStepVehicleNumber(d) for d in DETECTORS}
    q_current = {
        direction: sum(raw[det] for det in dets)
        for direction, dets in DIR_DETECTORS.items()
    }
    lam    = get_lambda(t)
    q_star = {d: predictive_queue(q_current[d], lam) for d in DIRECTIONS}
    return raw, q_current, q_star

def pick_next_direction(live_q_star, threshold_now, skip_counts, current_dir):
    eligible = [
        d for d in DIRECTIONS
        if not should_skip_empty(live_q_star[d], skip_counts[d])
    ]
    if len(eligible) == 0:
        eligible = [current_dir]

    non_empty = [d for d in eligible if live_q_star[d] >= 0.1]

    if len(non_empty) == 1:
        chosen = non_empty[0]
        print(f"  SOLE {chosen} Q*={live_q_star[chosen]:.1f} — direct serve")
        return chosen

    urgent = [d for d in eligible if live_q_star[d] >= threshold_now]
    if urgent:
        chosen = max(urgent, key=lambda d: live_q_star[d])
        print(f"  URGENT {chosen} Q*={live_q_star[chosen]:.1f} >= T={threshold_now}")
        return chosen

    # ── Hard starvation guard — fires at skip=3 ──────────────────────
    starving = [d for d in eligible if skip_counts[d] > MAX_SKIP]
    if starving:
        chosen = max(starving, key=lambda d: skip_counts[d])
        print(f"  STARVE RESCUE {chosen} skip={skip_counts[chosen]}")
        return chosen

    q_max_e = max(live_q_star[d] for d in eligible) or 1.0
    weights = []
    for d in eligible:
        boost = 0.0
        if skip_counts[d] > MAX_SKIP:
            extra = skip_counts[d] - MAX_SKIP
            boost = (2 ** extra) * q_max_e
        weights.append(live_q_star[d] + EPSILON + boost)
    weights = np.array(weights, dtype=float)
    probs   = weights / weights.sum()
    return np.random.choice(eligible, p=probs)

# ── Main Simulation ──────────────────────────────────────────────────
np.random.seed(42)
traci.start(SUMO_CMD)

log              = []
step             = 0
current_dir      = "N"
phase_timer      = 0
in_yellow        = False
active_green_dur = 0

skip_counts      = {d: 0 for d in DIRECTIONS}
cached_q_current = {d: 0.0 for d in DIRECTIONS}
cached_q_star    = {d: EPSILON for d in DIRECTIONS}
cached_raw       = {d: 0 for d in DETECTORS}

traci.trafficlight.setPhase(TL_ID, GREEN_PHASES[current_dir])
print("Randomized Adaptive Simulation started (v19 — gmin=3 post-demand)...")

try:
    while True:

        t_now = traci.simulation.getTime()

        if t_now > SAFETY_STOP:
            print(f"  Safety stop at t={SAFETY_STOP}s")
            break

        if t_now > DEMAND_END and sum(cached_q_current.values()) == 0:
            if traci.simulation.getMinExpectedNumber() == 0:
                print(f"  Clean exit — all vehicles cleared at t={int(t_now)}s")
                break

        if traci.simulation.getMinExpectedNumber() == 0 and t_now > DEMAND_END:
            print(f"  SUMO empty exit at t={int(t_now)}s")
            break

        traci.simulationStep()
        step       += 1
        phase_timer += 1

        if step % DELTA_T == 0:
            t = traci.simulation.getTime()

            cached_raw, cached_q_current, cached_q_star = fresh_read(t)

            lam       = get_lambda(t)
            threshold = get_threshold(t)
            gmin      = get_gmin(t)

            total_q     = sum(cached_q_current.values())
            vehicle_ids = traci.vehicle.getIDList()
            total_wait  = sum(traci.vehicle.getWaitingTime(v) for v in vehicle_ids)
            congestion_state = int(total_q >= threshold)
            probs_log   = compute_probabilities(cached_q_star, skip_counts)

            log.append({
                "time"               : t,
                "total_queue"        : total_q,
                "total_waiting_time" : total_wait,
                "congestion_state"   : congestion_state,
                "dynamic_threshold"  : threshold,
                "lambda"             : lam,
                "active_direction"   : current_dir,
                "active_green_dur"   : active_green_dur,
                "tod_phase"          : ("off-peak" if t < 50
                                        else "build-up" if t < 150
                                        else "peak"),
                "skip_N"             : skip_counts["N"],
                "skip_S"             : skip_counts["S"],
                "skip_E"             : skip_counts["E"],
                "skip_W"             : skip_counts["W"],
                "p_N"                : round(probs_log[0], 4),
                "p_S"                : round(probs_log[1], 4),
                "p_E"                : round(probs_log[2], 4),
                "p_W"                : round(probs_log[3], 4),
                "q_star_N"           : round(cached_q_star["N"], 2),
                "q_star_S"           : round(cached_q_star["S"], 2),
                "q_star_E"           : round(cached_q_star["E"], 2),
                "q_star_W"           : round(cached_q_star["W"], 2),
                **cached_raw
            })

            if step % 300 == 0:
                print(f"  t={int(t)}s | Q={total_q} | T(t)={threshold} "
                      f"| dir={current_dir} | Elapsed={phase_timer}s "
                      f"| Sk={congestion_state} | skips={skip_counts}")

            # ── THRESHOLD-GATED GREEN CONTROL ────────────────────────
            if not in_yellow:

                # Rule 0: hard cap
                if phase_timer >= G_MAX:
                    if t > DEMAND_END and total_q == 0:
                        pass
                    else:
                        print(f"  G_MAX cap {current_dir} — forcing switch")
                        active_green_dur = phase_timer
                        traci.trafficlight.setPhase(TL_ID, YELLOW_PHASES[current_dir])
                        in_yellow   = True
                        phase_timer = 0

                # Rule 1: G_MIN not served
                elif phase_timer < gmin:
                    pass

                # Rule 2: all lanes empty
                elif total_q == 0:
                    pass

                # Rule 3: current lane congested
                elif cached_q_star[current_dir] >= threshold:
                    pass

                # Rule 4: current below threshold, G_MIN already served
                else:
                    urgent_others = [
                        d for d in DIRECTIONS
                        if d != current_dir
                        and cached_q_star[d] >= threshold
                    ]

                    if urgent_others:
                        print(f"  CUT {current_dir} Q*={cached_q_star[current_dir]:.1f}"
                              f" < T={threshold} → urgent: {urgent_others}")
                        active_green_dur = phase_timer
                        traci.trafficlight.setPhase(TL_ID, YELLOW_PHASES[current_dir])
                        in_yellow   = True
                        phase_timer = 0

                    elif cached_q_current[current_dir] == 0:
                        others_waiting = any(
                            cached_q_current[d] > 0
                            for d in DIRECTIONS if d != current_dir
                        )
                        if others_waiting:
                            print(f"  DRAIN DONE {current_dir} — clean handoff")
                            active_green_dur = phase_timer
                            traci.trafficlight.setPhase(TL_ID, YELLOW_PHASES[current_dir])
                            in_yellow   = True
                            phase_timer = 0

                    elif phase_timer >= gmin * 2:
                        # post-demand: 2×3=6s cap | peak: 2×8=16s cap
                        print(f"  DRAIN CAP {current_dir} Elapsed={phase_timer}s → rotating")
                        active_green_dur = phase_timer
                        traci.trafficlight.setPhase(TL_ID, YELLOW_PHASES[current_dir])
                        in_yellow   = True
                        phase_timer = 0

        # ── Yellow phase ──────────────────────────────────────────────
        if in_yellow and phase_timer >= YELLOW_DUR:
            t_switch      = traci.simulation.getTime()
            threshold_now = get_threshold(t_switch)

            _, live_q, live_q_star = fresh_read(t_switch)

            for d in DIRECTIONS:
                if d == current_dir:
                    skip_counts[d] = 0
                elif live_q_star[d] < 0.1:
                    skip_counts[d] = 0
                else:
                    skip_counts[d] += 1

            current_dir = pick_next_direction(
                live_q_star, threshold_now, skip_counts, current_dir
            )

            traci.trafficlight.setPhase(TL_ID, GREEN_PHASES[current_dir])
            in_yellow   = False
            phase_timer = 0

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
print(f"  Mean Queue : {df['total_queue'].mean():.2f}")
print(f"  Variance   : {df['total_queue'].var():.2f}")
print(f"  Max Queue  : {df['total_queue'].max()}")
print(f"  Mean Wait  : {df['total_waiting_time'].mean():.2f}s")
