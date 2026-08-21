import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

rng = np.random.default_rng(101112)

OUT = "../data"
START = date(2024, 1, 1)
END = date(2025, 12, 31)

products = pd.read_pickle(f"{OUT}/_products.pkl")
inventory_snapshots = pd.read_pickle(f"{OUT}/_inventory_snapshots.pkl")

active_products = products[products["is_active"]].copy()
RISK_LINKED_IDS = set(products[products["_risk_linked_INTERNAL"]]["product_id"])

# build a quick lookup: product_id -> sorted list of stockout date ranges (from any warehouse)
stockout_dates = {}
for pid, grp in inventory_snapshots[inventory_snapshots["stockout_flag"]].groupby("product_id"):
    stockout_dates[pid] = set(pd.to_datetime(grp["snapshot_date"]).dt.date)

def overlaps_stockout(pid, start, end):
    dates_set = stockout_dates.get(pid, set())
    if not dates_set:
        return False
    d = start
    while d <= end:
        if d in dates_set:
            return True
        d += timedelta(days=1)
    return False

CAMPAIGN_NAMES = ["Eid Special","New Year Sale","Weekend Flash Deal","Season Clearance",
                  "Boishakh Bonanza","Anniversary Discount","Buy More Save More","Festive Combo Offer"]
CHANNELS = ["In-store","Online","Both"]

TARGET_TOTAL = 180  # locked in Phase 2 fix (C)
promo_rows = []
promo_id_ctr = 1
attempts = 0
max_attempts = TARGET_TOTAL * 20

# weight: risk-linked products get 0.6x selection weight vs 1.0x for others
weights = active_products["product_id"].apply(lambda p: 0.6 if p in RISK_LINKED_IDS else 1.0).values
weights = weights / weights.sum()

while len(promo_rows) < TARGET_TOTAL and attempts < max_attempts:
    attempts += 1
    pid = rng.choice(active_products["product_id"].values, p=weights)
    start_day = int(rng.integers(0, (END-START).days - 14))
    start = START + timedelta(days=start_day)
    duration = int(rng.integers(3, 15))
    end = start + timedelta(days=duration)

    is_risk = pid in RISK_LINKED_IDS
    if is_risk and overlaps_stockout(pid, start, end):
        # intentionally allow a rare exception (documented edge case) instead of a hard skip
        if rng.random() > 0.08:
            continue  # 92% of the time, avoid the conflict (skip and retry)
        # else: fall through and keep this promo -> deliberate "promo ran into a stockout" edge case

    discount_pct = round(rng.uniform(10, 45), 0)
    lift_pct = round(rng.uniform(30, 80), 0)  # varies per promo, not fixed

    promo_rows.append({
        "promo_id": f"PROMO{promo_id_ctr:04d}",
        "product_id": pid,
        "campaign_name": rng.choice(CAMPAIGN_NAMES),
        "discount_pct": discount_pct,
        "start_date": start,
        "end_date": end,
        "channel": rng.choice(CHANNELS, p=[0.5,0.25,0.25]),
        "_lift_pct_INTERNAL": lift_pct,  # used by Phase 3e sales generation, not exported to final CSV as-is
    })
    promo_id_ctr += 1

promotions = pd.DataFrame(promo_rows)
n_risk_promos = promotions["product_id"].isin(RISK_LINKED_IDS).sum()
print("First pass promotions:", promotions.shape, "| risk-linked:", n_risk_promos)

# FIX: the conflict-avoidance skip was too aggressive for risk-linked products (high
# stockout rate -> most random windows conflict -> too few risk-linked promos survive,
# undermining statistical power). Top up with a guaranteed minimum quota of risk-linked
# promos using a lighter conflict check (only checks the start date, not full window).
MIN_RISK_PROMOS = 16
risk_products_list = active_products[active_products["product_id"].isin(RISK_LINKED_IDS)]["product_id"].values

while n_risk_promos < MIN_RISK_PROMOS:
    pid = rng.choice(risk_products_list)
    start_day = int(rng.integers(0, (END-START).days - 14))
    start = START + timedelta(days=start_day)
    duration = int(rng.integers(3, 15))
    end = start + timedelta(days=duration)
    if start.date() if hasattr(start,'date') else start in stockout_dates.get(pid, set()):
        continue  # only skip if the exact start day is a stockout day (lighter check)

    discount_pct = round(rng.uniform(10, 45), 0)
    lift_pct = round(rng.uniform(30, 80), 0)
    promo_rows.append({
        "promo_id": f"PROMO{promo_id_ctr:04d}",
        "product_id": pid,
        "campaign_name": rng.choice(CAMPAIGN_NAMES),
        "discount_pct": discount_pct,
        "start_date": start,
        "end_date": end,
        "channel": rng.choice(CHANNELS, p=[0.5,0.25,0.25]),
        "_lift_pct_INTERNAL": lift_pct,
    })
    promo_id_ctr += 1
    n_risk_promos += 1

promotions = pd.DataFrame(promo_rows)
print("Final promotions:", promotions.shape)
n_risk_promos = promotions["product_id"].isin(RISK_LINKED_IDS).sum()
print("Promotions on risk-linked products:", n_risk_promos, f"({n_risk_promos/len(promotions)*100:.1f}%)")
print("Duration range:", promotions.apply(lambda r: (r['end_date']-r['start_date']).days, axis=1).describe())

promotions.to_pickle(f"{OUT}/_promotions.pkl")

