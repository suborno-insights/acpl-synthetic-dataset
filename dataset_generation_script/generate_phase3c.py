import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

rng = np.random.default_rng(789)

OUT = "../data"
START = date(2024, 1, 1)
END = date(2025, 12, 31)
ALL_DATES = pd.date_range(START, END, freq="D")
N_DAYS = len(ALL_DATES)

warehouses = pd.read_pickle(f"{OUT}/_warehouses.pkl")
stores = pd.read_pickle(f"{OUT}/_stores.pkl")
carriers = pd.read_pickle(f"{OUT}/_carriers.pkl")
with open(f"{OUT}/_warehouse_serves.pkl","rb") as f:
    WMAP = pickle.load(f)
with open(f"{OUT}/_phase2_logic.pkl","rb") as f:
    L = pickle.load(f)

WAREHOUSE_SERVES = WMAP["WAREHOUSE_SERVES"]
REGION_PRIMARY_WH = WMAP["REGION_PRIMARY_WH"]

# approximate distance (km) between region pairs (for cost calc); same-region short, cross-region long
REGION_COORDS = {  # rough lat/lon for distance-ish calc
    "Dhaka": (23.81, 90.41), "Chattogram": (22.36, 91.78), "Sylhet": (24.90, 91.87),
    "Rajshahi": (24.37, 88.60), "Khulna": (22.82, 89.55), "Barishal": (22.70, 90.37),
}
def region_distance(r1, r2):
    import math
    lat1,lon1 = REGION_COORDS[r1]; lat2,lon2 = REGION_COORDS[r2]
    return round(math.hypot(lat1-lat2, lon1-lon2) * 111, 1)  # rough km

def final_shipment_delay_prob(carrier_id, day_idx, warehouse_id, store_region):
    base = L["CARRIER_DELAY_PROB"][carrier_id][day_idx]
    served = WAREHOUSE_SERVES[warehouse_id]
    bonus = 0.0 if store_region in served else 0.15
    return float(np.clip(base + bonus, 0.04, 0.90))

shipment_rows = []
ship_id_ctr = 1
STORE_TXN_COUNT_MULT = L["STORE_TXN_COUNT_MULT"]
REGION_VOLUME_MULT = L["REGION_VOLUME_MULT"]

for _, st in stores.iterrows():
    store_id = st["store_id"]
    region = st["region"]
    primary_wh = REGION_PRIMARY_WH[region]
    # shipment frequency scales with store type & region volume: base every ~4 days, adjusted
    freq_mult = STORE_TXN_COUNT_MULT[st["store_type"]] * REGION_VOLUME_MULT[region]
    avg_gap = max(1.0, 1.6 / freq_mult)  # recalibrated (was 4.5) to hit the ~9,000 volume lock

    cursor = int(rng.integers(0, 4))
    while cursor < N_DAYS:
        # 90% of shipments from primary warehouse, 10% overflow from another warehouse
        if rng.random() < 0.90:
            wh_id = primary_wh
        else:
            wh_id = rng.choice([w for w in warehouses["warehouse_id"] if w != primary_wh])

        # carrier selection: weighted by reliability (better carriers get more volume, mildly)
        carrier_id = rng.choice(carriers["carrier_id"], p=[0.24,0.20,0.22,0.14,0.20])

        dispatch_date = START + timedelta(days=cursor)
        wh_region = warehouses[warehouses["warehouse_id"]==wh_id]["region"].iloc[0]
        dist_km = region_distance(wh_region, region) if wh_region != region else round(rng.uniform(8,35),1)
        base_transit_days = max(1, int(round(dist_km / 250)) + 1)
        expected_arrival = dispatch_date + timedelta(days=base_transit_days)

        delay_prob = final_shipment_delay_prob(carrier_id, min(cursor, N_DAYS-1), wh_id, region)
        is_delayed = rng.random() < delay_prob
        extra_days = int(rng.integers(1,5)) if is_delayed else 0
        actual_arrival = expected_arrival + timedelta(days=extra_days)

        # small chance of damaged/lost regardless of delay
        r = rng.random()
        if r < 0.015:
            status = "Lost"
        elif r < 0.045:
            status = "Damaged"
        elif is_delayed:
            status = "Delayed"
        else:
            status = "On-time"

        cost_per_km = rng.uniform(35, 55)
        shipment_cost = round(dist_km * cost_per_km * rng.uniform(0.9,1.15) + rng.uniform(200,600), 2)

        shipment_rows.append({
            "shipment_id": f"SH{ship_id_ctr:06d}",
            "warehouse_id": wh_id,
            "store_id": store_id,
            "carrier_id": carrier_id,
            "dispatch_date": dispatch_date,
            "expected_arrival_date": expected_arrival,
            "actual_arrival_date": actual_arrival if actual_arrival <= END else pd.NaT,
            "distance_km": dist_km,
            "shipment_cost": shipment_cost,
            "shipment_status": status if actual_arrival <= END else "In-Transit",
        })
        ship_id_ctr += 1
        cursor += int(round(rng.uniform(avg_gap*0.6, avg_gap*1.4)))

shipments = pd.DataFrame(shipment_rows)
print("shipments:", shipments.shape)
print(shipments["shipment_status"].value_counts())
print(shipments.groupby("carrier_id")["shipment_status"].apply(lambda s: (s=="Delayed").mean()).sort_values())

shipments.to_pickle(f"{OUT}/_shipments.pkl")
