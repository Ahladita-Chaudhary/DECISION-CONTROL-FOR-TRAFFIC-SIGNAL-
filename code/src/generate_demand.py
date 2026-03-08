import numpy as np
import os

np.random.seed(42)

DELTA_T    = 3
TOTAL_TIME = 300
OUT_FILE   = os.path.join(os.path.dirname(__file__), "../data/demand.rou.xml")

ROUTES = {
    "N_to_C": ["C_to_S", "C_to_E", "C_to_W"],
    "S_to_C": ["C_to_N", "C_to_E", "C_to_W"],
    "E_to_C": ["C_to_W", "C_to_N", "C_to_S"],
    "W_to_C": ["C_to_E", "C_to_N", "C_to_S"],
}

def get_lambda(t):
    if t < 50:   return 0.17    # ~200 veh/hr  off-peak
    elif t < 150: return 0.42    # ~500 veh/hr  building
    else:          return 0.50    # ~600 veh/hr  peak hour

vehicles = []
veh_id = 0

for t in range(0, TOTAL_TIME, DELTA_T):
    lam = get_lambda(t)
    n_arrivals = np.random.poisson(lam * DELTA_T)
    for _ in range(n_arrivals):
        src = np.random.choice(list(ROUTES.keys()))
        dst = np.random.choice(ROUTES[src])
        vehicles.append((veh_id, t, src, dst))
        veh_id += 1

os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

with open(OUT_FILE, "w") as f:
    f.write('<routes>\n')
    for src, destinations in ROUTES.items():
        for dst in destinations:
            f.write(f'  <route id="r_{src}_{dst}" edges="{src} {dst}"/>\n')
    f.write('\n')
    for vid, depart, src, dst in vehicles:
        f.write(f'  <vehicle id="v{vid}" depart="{depart}" route="r_{src}_{dst}"/>\n')
    f.write('</routes>\n')

print(f"Generated {len(vehicles)} vehicles → {OUT_FILE}")
