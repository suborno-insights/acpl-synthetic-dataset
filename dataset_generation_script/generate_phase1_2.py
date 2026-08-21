import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(42)

OUT = "../data"
import os
os.makedirs(OUT, exist_ok=True)

START = date(2024, 1, 1)
END = date(2025, 12, 31)
ALL_DATES = pd.date_range(START, END, freq="D")
N_DAYS = len(ALL_DATES)

# ---------------------------------------------------------------
# 0. Seasonality helper (Bangladesh context)
# ---------------------------------------------------------------
EID_FITR = [date(2024, 4, 10), date(2025, 3, 31)]
EID_ADHA = [date(2024, 6, 17), date(2025, 6, 7)]
BOISHAKH = [date(2024, 4, 14), date(2025, 4, 14)]
WINTER_WEDDING = [(date(2024,11,1),date(2025,2,15)), (date(2025,11,1),date(2025,12,31))]
YEAR_END = [(date(2024,12,15),date(2024,12,31)), (date(2025,12,15),date(2025,12,31))]

def seasonal_multiplier(d):
    m = 1.0
    for e in EID_FITR + EID_ADHA + BOISHAKH:
        delta = abs((d.date() - e).days)
        if delta <= 10:
            m += 0.9 * max(0, (10 - delta) / 10)
    for s, en in WINTER_WEDDING:
        if s <= d.date() <= en:
            m += 0.15
    for s, en in YEAR_END:
        if s <= d.date() <= en:
            m += 0.3
    # mild weekly pattern: Thu/Fri busier (BD weekend Fri-Sat)
    wd = d.weekday()  # Mon=0
    if wd in (3, 4):  # Thu, Fri
        m += 0.2
    if wd == 5:  # Sat
        m += 0.1
    return m

SEASONAL = np.array([seasonal_multiplier(d) for d in ALL_DATES])
# mild upward yearly growth trend
TREND = 1.0 + 0.00025 * np.arange(N_DAYS)
DAILY_FACTOR = SEASONAL * TREND

print("Seasonality range:", DAILY_FACTOR.min(), DAILY_FACTOR.max())
np.save(f"{OUT}/_daily_factor.npy", DAILY_FACTOR)

COMPANY = "Apex Consumer Products Ltd."

# ---------------------------------------------------------------
# PHASE 1: DIMENSION TABLES (clean skeleton)
# ---------------------------------------------------------------
REGIONS = ["Dhaka", "Chattogram", "Sylhet", "Rajshahi", "Khulna", "Barishal"]
CITIES = {
    "Dhaka": ["Dhaka", "Gazipur", "Narayanganj"],
    "Chattogram": ["Chattogram", "Cox's Bazar"],
    "Sylhet": ["Sylhet", "Moulvibazar"],
    "Rajshahi": ["Rajshahi", "Bogura"],
    "Khulna": ["Khulna", "Jessore"],
    "Barishal": ["Barishal", "Patuakhali"],
}

# ---- Warehouses (3) ----
warehouses = pd.DataFrame({
    "warehouse_id": [f"W{i+1:02d}" for i in range(3)],
    "warehouse_name": ["Dhaka Central DC", "Chattogram Regional DC", "Rajshahi Regional DC"],
    "region": ["Dhaka", "Chattogram", "Rajshahi"],
    "capacity_units": [500000, 250000, 200000],
    "operational_since": [date(2019,1,1), date(2020,6,1), date(2021,3,1)],
})

# ---- Stores (20) ----
n_stores = 20
store_regions = rng.choice(REGIONS, size=n_stores, p=[0.35,0.2,0.12,0.13,0.12,0.08])
store_types = rng.choice(["Flagship","Standard","Express"], size=n_stores, p=[0.15,0.55,0.30])
open_dates = [date(2018,1,1) + timedelta(days=int(x)) for x in rng.integers(0, 2000, n_stores)]
stores = pd.DataFrame({
    "store_id": [f"ST{i+1:02d}" for i in range(n_stores)],
    "store_name": [f"ACPL Store {i+1}" for i in range(n_stores)],
    "region": store_regions,
    "city": [rng.choice(CITIES[r]) for r in store_regions],
    "store_type": store_types,
    "store_size_sqft": [int(x) for x in rng.integers(800, 6000, n_stores)],
    "opening_date": open_dates,
    "manager_name": [f"Manager_{i+1}" for i in range(n_stores)],
})

# ---- Carriers (5) ----
carriers = pd.DataFrame({
    "carrier_id": [f"CR{i+1:02d}" for i in range(5)],
    "carrier_name": ["SwiftHaul Logistics","Padma Express Cargo","Jamuna Freight Co.",
                      "Delta Transport Ltd.","Meghna Movers"],
    # base reliability: fraction of shipments that are on-time before other effects
    "base_reliability": [0.90, 0.82, 0.88, 0.70, 0.93],
})
# CR04 (Delta Transport) intentionally the weakest carrier; CR05 the most reliable

# ---- Warehouse -> Region service mapping (for route/delay logic) ----
WAREHOUSE_SERVES = {
    "W01": ["Dhaka", "Barishal"],
    "W02": ["Chattogram", "Sylhet"],
    "W03": ["Rajshahi", "Khulna"],
}
# reverse map: region -> primary warehouse
REGION_PRIMARY_WH = {r: w for w, regs in WAREHOUSE_SERVES.items() for r in regs}

# ---- Suppliers (45) ----
n_suppliers = 45
CATEGORIES = ["Grocery","Beverages","Home & Kitchen","Personal Care","Apparel",
              "Electronics Accessories","Stationery","Footwear"]
supplier_cats = [rng.choice(CATEGORIES, size=rng.integers(1,3), replace=False).tolist() for _ in range(n_suppliers)]
suppliers = pd.DataFrame({
    "supplier_id": [f"S{i+1:03d}" for i in range(n_suppliers)],
    "supplier_name": [f"Supplier_{i+1}" for i in range(n_suppliers)],
    "region": rng.choice(REGIONS, size=n_suppliers),
    "categories_supplied": ["; ".join(c) for c in supplier_cats],
    "contract_start_date": [date(2018,1,1) + timedelta(days=int(x)) for x in rng.integers(0, 2500, n_suppliers)],
    "payment_terms_days": rng.choice([15,30,45,60], size=n_suppliers),
    "base_lead_time_days": rng.integers(3, 21, n_suppliers),
})

# explicit risk_type lock (6 suppliers, rest = none)
chosen = rng.choice(suppliers["supplier_id"], size=6, replace=False).tolist()
risk_type_map = {
    chosen[0]: "lead_time_only",
    chosen[1]: "lead_time_only",
    chosen[2]: "reject_rate_only",
    chosen[3]: "reject_rate_only",
    chosen[4]: "both_mild",
    chosen[5]: "both_severe",
}
suppliers["risk_type_INTERNAL"] = suppliers["supplier_id"].map(risk_type_map).fillna("none")
RISK_SUPPLIER_IDS = chosen
SEVERE_SUPPLIER_ID = chosen[5]

# ---- Products (180) ----
n_products = 180
prod_cat = rng.choice(CATEGORIES, size=n_products, p=[0.25,0.15,0.12,0.13,0.12,0.08,0.08,0.07])
sub_cat_map = {
    "Grocery": ["Rice & Grains","Snacks","Cooking Oil","Spices"],
    "Beverages": ["Soft Drinks","Juice","Tea & Coffee"],
    "Home & Kitchen": ["Cookware","Cleaning Supplies","Storage"],
    "Personal Care": ["Skincare","Haircare","Oral Care"],
    "Apparel": ["Menswear","Womenswear","Kidswear"],
    "Electronics Accessories": ["Mobile Accessories","Small Appliances"],
    "Stationery": ["Office Supplies","School Supplies"],
    "Footwear": ["Casual","Formal","Sports"],
}
sub_cats = [rng.choice(sub_cat_map[c]) for c in prod_cat]
unit_cost = np.round(rng.gamma(shape=3, scale=60, size=n_products) + 20, 2)
margin_pct = rng.uniform(0.15, 0.45, n_products)
unit_price = np.round(unit_cost * (1 + margin_pct), 2)
launch_dates = [date(2017,1,1) + timedelta(days=int(x)) for x in rng.integers(0, 3200, n_products)]

products = pd.DataFrame({
    "product_id": [f"P{i+1:03d}" for i in range(n_products)],
    "product_name": [f"{prod_cat[i]}_Item_{i+1}" for i in range(n_products)],
    "category": prod_cat,
    "sub_category": sub_cats,
    "unit_cost": unit_cost,
    "unit_price": unit_price,
    "primary_supplier_id": None,  # filled below by matching category
    "launch_date": launch_dates,
    "is_active": rng.choice([True, True, True, True, False], size=n_products),  # ~20% discontinued
})
# assign primary supplier: pick a supplier that supplies this product's category
sup_by_cat = {c: suppliers.loc[suppliers["categories_supplied"].str.contains(c), "supplier_id"].tolist() for c in CATEGORIES}
def pick_supplier(cat):
    pool = sup_by_cat.get(cat) or suppliers["supplier_id"].tolist()
    return rng.choice(pool)
products["primary_supplier_id"] = products["category"].apply(pick_supplier)

# mark a subset of products as "trending up" / "trending down" / "seasonal-heavy" for Phase 2 story
trend_labels = rng.choice(["stable","growing","declining"], size=n_products, p=[0.5,0.3,0.2])
products["_trend_label_INTERNAL"] = trend_labels

# flag products sourced from a risk supplier (for stockout-chain and promotion-sparsity logic)
products["_risk_linked_INTERNAL"] = products["primary_supplier_id"].isin(RISK_SUPPLIER_IDS)
products["_risk_type_INTERNAL"] = products["primary_supplier_id"].map(risk_type_map).fillna("none")
print("Risk-linked products:", products["_risk_linked_INTERNAL"].sum())

# ---- Customers (6000) ----
n_customers = 6000
join_dates = [date(2018,1,1) + timedelta(days=int(x)) for x in rng.integers(0, 2920, n_customers)]
customers = pd.DataFrame({
    "customer_id": [f"C{i+1:05d}" for i in range(n_customers)],
    "join_date": join_dates,
    "region": rng.choice(REGIONS, size=n_customers, p=[0.35,0.2,0.12,0.13,0.12,0.08]),
    "preferred_store_id": rng.choice(stores["store_id"], size=n_customers),
    "acquisition_channel": rng.choice(["Walk-in","Online","Referral","Social Media"], size=n_customers, p=[0.5,0.25,0.15,0.10]),
})
# mark a subset of customers as "churned" (no purchase in last 6 months) for Phase 2 story
customers["_churn_risk_INTERNAL"] = rng.choice([True, False], size=n_customers, p=[0.18, 0.82])

print("stores:", stores.shape, "| warehouses:", warehouses.shape, "| suppliers:", suppliers.shape,
      "| products:", products.shape, "| customers:", customers.shape)

warehouses.to_pickle(f"{OUT}/_warehouses.pkl")
stores.to_pickle(f"{OUT}/_stores.pkl")
suppliers.to_pickle(f"{OUT}/_suppliers.pkl")
products.to_pickle(f"{OUT}/_products.pkl")
customers.to_pickle(f"{OUT}/_customers.pkl")
carriers.to_pickle(f"{OUT}/_carriers.pkl")
import pickle
with open(f"{OUT}/_warehouse_serves.pkl","wb") as f:
    pickle.dump({"WAREHOUSE_SERVES": WAREHOUSE_SERVES, "REGION_PRIMARY_WH": REGION_PRIMARY_WH,
                 "RISK_SUPPLIER_IDS": RISK_SUPPLIER_IDS, "SEVERE_SUPPLIER_ID": SEVERE_SUPPLIER_ID,
                 "risk_type_map": risk_type_map}, f)
print("Phase 1 (updated) done.")
print("\nRisk supplier map:")
print(suppliers[suppliers["risk_type_INTERNAL"]!="none"][["supplier_id","risk_type_INTERNAL"]])
print("\nWarehouse serves:", WAREHOUSE_SERVES)

# =================================================================
# PHASE 2: STORY LOGIC (time-based behavior functions)
# =================================================================
DAY_IDX = {d.date(): i for i, d in enumerate(ALL_DATES)}

def days_since(d, ref):
    return (d - ref).days

# ---- 2a. Supplier performance curves ----
# For each supplier, produce a daily lead_time_multiplier and reject_rate array.
SUPPLIER_LEAD_MULT = {}   # supplier_id -> np.array(N_DAYS) multiplier on base_lead_time_days
SUPPLIER_REJECT_RATE = {} # supplier_id -> np.array(N_DAYS) probability a unit is rejected

DEGRADE_START = date(2024, 7, 1)          # mild degradation start for most risk suppliers
SEVERE_START = date(2025, 1, 1)           # severe supplier degrades faster from here

for _, row in suppliers.iterrows():
    sid = row["supplier_id"]
    rtype = row["risk_type_INTERNAL"]
    base_reject = rng.uniform(0.01, 0.03)  # normal suppliers: 1-3% baseline reject rate
    lead_mult = np.ones(N_DAYS)
    reject_rate = np.full(N_DAYS, base_reject)

    if rtype == "none":
        # 3-5% random outlier days (occasional bad batch even for reliable suppliers)
        outlier_days = rng.choice(N_DAYS, size=int(N_DAYS*rng.uniform(0.03,0.05)), replace=False)
        reject_rate[outlier_days] *= rng.uniform(2.5, 4, size=len(outlier_days))
        outlier_days2 = rng.choice(N_DAYS, size=int(N_DAYS*rng.uniform(0.03,0.05)), replace=False)
        lead_mult[outlier_days2] *= rng.uniform(1.5, 2.2, size=len(outlier_days2))

    else:
        t_since_degrade = np.array([max(0, days_since(d.date(), DEGRADE_START)) for d in ALL_DATES])
        ramp = np.clip(t_since_degrade / 400, 0, 1)  # ramps up over ~400 days

        if rtype in ("lead_time_only", "both_mild", "both_severe"):
            severity = 2.5 if rtype == "both_severe" else (1.4 if rtype=="both_mild" else 1.6)
            lead_mult = 1 + ramp * (severity - 1)
        if rtype in ("reject_rate_only", "both_mild", "both_severe"):
            severity_r = 0.22 if rtype == "both_severe" else (0.10 if rtype=="both_mild" else 0.12)
            reject_rate = base_reject + ramp * severity_r

        extra_ramp = np.zeros(N_DAYS)
        if sid == SEVERE_SUPPLIER_ID:
            t_since_severe = np.array([max(0, days_since(d.date(), SEVERE_START)) for d in ALL_DATES])
            extra_ramp = np.clip(t_since_severe / 250, 0, 1)
            lead_mult = lead_mult + extra_ramp * 1.8
            reject_rate = reject_rate + extra_ramp * 0.18

        # FIX A (v2, per reviewer feedback): good streaks must NOT appear once the
        # supplier is deep into degradation/crisis, or they undermine the severity
        # narrative. Restrict streak placement to days where ramp<0.6 AND (for the
        # severe supplier) extra_ramp<0.3 — i.e. streaks fade out and stop entirely
        # as the supplier approaches/enters crisis, they don't appear at random.
        allowed = (ramp < 0.6) & (extra_ramp < 0.3)
        allowed_days = np.where(allowed)[0]
        n_streaks = rng.integers(3, 6)
        for _ in range(n_streaks):
            streak_len = rng.integers(7, 15)
            valid_starts = allowed_days[allowed_days < N_DAYS - streak_len]
            if len(valid_starts) == 0:
                continue  # no safe window left (e.g. severe supplier late in timeline) -> skip, correct behavior
            streak_start = rng.choice(valid_starts)
            idx = slice(streak_start, streak_start + streak_len)
            lead_mult[idx] = np.clip(lead_mult[idx] * rng.uniform(0.5, 0.8), 1.0, None)
            reject_rate[idx] = base_reject * rng.uniform(0.9, 1.2)

    reject_rate = np.clip(reject_rate, 0.005, 0.6)
    SUPPLIER_LEAD_MULT[sid] = lead_mult
    SUPPLIER_REJECT_RATE[sid] = reject_rate

print("Sample severe supplier reject_rate (start/mid/end):",
      SUPPLIER_REJECT_RATE[SEVERE_SUPPLIER_ID][0],
      SUPPLIER_REJECT_RATE[SEVERE_SUPPLIER_ID][N_DAYS//2],
      SUPPLIER_REJECT_RATE[SEVERE_SUPPLIER_ID][-1])

# ---- 2b. Carrier delay probability curves ----
MONSOON_MONTHS = {6,7,8,9}
CARRIER_DELAY_PROB = {}  # carrier_id -> np.array(N_DAYS) probability of delay
for _, row in carriers.iterrows():
    cid = row["carrier_id"]
    base_delay_prob = 1 - row["base_reliability"]
    arr = np.full(N_DAYS, base_delay_prob)
    for i, d in enumerate(ALL_DATES):
        if d.month in MONSOON_MONTHS:
            arr[i] += 0.12  # monsoon bump, same for all carriers but base differs so relative impact varies
        if seasonal_multiplier(d) > 1.6:  # high-volume days (near Eid/year-end) -> capacity strain
            arr[i] += 0.10
    # noise: even best carrier delays sometimes (5-8%), even worst carrier on-time sometimes (handled by prob cap)
    arr = np.clip(arr, 0.04, 0.85)
    CARRIER_DELAY_PROB[cid] = arr

print("Carrier delay prob range (CR04 Delta - weakest):", CARRIER_DELAY_PROB["CR04"].min(), CARRIER_DELAY_PROB["CR04"].max())
print("Carrier delay prob range (CR05 Meghna - strongest):", CARRIER_DELAY_PROB["CR05"].min(), CARRIER_DELAY_PROB["CR05"].max())

# route multiplier: cross-region (non-primary) routes get extra delay probability
def route_delay_bonus(warehouse_id, store_region):
    served = WAREHOUSE_SERVES[warehouse_id]
    return 0.0 if store_region in served else 0.15  # cross-region/overflow route penalty

# FIX D: explicit, locked formula for combining carrier base delay probability with
# route bonus, WITH a hard cap so probability never approaches/exceeds 1.0.
def final_shipment_delay_prob(carrier_id, day_idx, warehouse_id, store_region):
    base = CARRIER_DELAY_PROB[carrier_id][day_idx]
    bonus = route_delay_bonus(warehouse_id, store_region)
    return float(np.clip(base + bonus, 0.04, 0.90))

# ---- 2c. Product demand trend curves (combined with global seasonality) ----
PRODUCT_DEMAND_MULT = {}  # product_id -> np.array(N_DAYS) multiplier (on top of DAILY_FACTOR)
for _, row in products.iterrows():
    pid = row["product_id"]
    label = row["_trend_label_INTERNAL"]
    t = np.arange(N_DAYS) / N_DAYS
    if label == "growing":
        base = 1 + t * rng.uniform(0.4, 0.9)
    elif label == "declining":
        base = 1 - t * rng.uniform(0.3, 0.6)
    else:  # stable
        base = np.ones(N_DAYS)
    noise = 1 + rng.normal(0, 0.15 if label!="stable" else 0.10, N_DAYS)  # weekly-ish noise (iid daily approx)
    curve = np.clip(base * noise, 0.1, None)
    PRODUCT_DEMAND_MULT[pid] = curve

# ---- 2d. Stockout risk windows (prep only; actual inventory sim happens in Phase 3) ----
# For risk-linked products, degraded lead time -> higher chance warehouse runs dry periodically.
# We just expose the lead_mult/reject arrays per product via its supplier; Phase 3 inventory sim will consume these.
products_supplier_leadmult = {pid: SUPPLIER_LEAD_MULT[sup] for pid, sup in zip(products["product_id"], products["primary_supplier_id"])}

# ---- 2e. Promotion scheduling helper rules (used in Phase 3) ----
# FIX C: bumped from 50%->60% risk-linked promo rate, and total promo count will be
# 150->180 in Phase 3, to guarantee enough promo events land on risk-linked products
# for a meaningful sample (est. ~16 events on the 25 risk-linked products).
def promo_allowed_base_rate(is_risk_linked):
    return 0.6 if is_risk_linked else 1.0
PROMO_TOTAL_COUNT_TARGET = 180  # used by Phase 3

# ---- 2f. Customer churn logic ----
# split churn customers (18% flagged) into abrupt vs gradual, only for customers who joined before 2024-07-01
eligible_mask = customers["join_date"].apply(lambda d: d < date(2024,7,1))
churn_mask = customers["_churn_risk_INTERNAL"] & eligible_mask
# FIX B: replaced arbitrary 50-50 split with a business-reasoned ratio.
# Rationale (documented for data dictionary): in retail, gradual dissatisfaction
# (declining visit frequency) is more common than an abrupt one-time drop-off
# (e.g., single bad experience, moved away, switched to a competitor) — so we use
# 58% gradual / 42% abrupt.
churn_idx = customers[churn_mask].index
churn_idx_shuffled = rng.permutation(churn_idx)
split_point = int(len(churn_idx_shuffled) * 0.58)
gradual_idx = churn_idx_shuffled[:split_point]
abrupt_idx = churn_idx_shuffled[split_point:]
customers["_churn_type_INTERNAL"] = "none"
customers.loc[abrupt_idx, "_churn_type_INTERNAL"] = "abrupt"
customers.loc[gradual_idx, "_churn_type_INTERNAL"] = "gradual"
# for those flagged churn but not eligible (joined too recently), reset flag
customers.loc[customers["_churn_risk_INTERNAL"] & ~eligible_mask, "_churn_risk_INTERNAL"] = False

print("\nChurn type counts:")
print(customers["_churn_type_INTERNAL"].value_counts())

# ---- 2g. Store-type / region multipliers for sales generation ----
STORE_TXN_COUNT_MULT = {"Flagship": 2.2, "Standard": 1.0, "Express": 0.55}
STORE_BASKET_SIZE_MULT = {"Flagship": 1.6, "Standard": 1.0, "Express": 0.6}
STORE_VISIT_FREQ_MULT = {"Flagship": 0.9, "Standard": 1.0, "Express": 1.4}  # express: more frequent, smaller visits
REGION_VOLUME_MULT = {"Dhaka": 1.6, "Chattogram": 1.15, "Sylhet": 0.85,
                       "Rajshahi": 0.9, "Khulna": 0.8, "Barishal": 0.65}

# ---- Save all Phase 2 artifacts for Phase 3 ----
import pickle
with open(f"{OUT}/_phase2_logic.pkl", "wb") as f:
    pickle.dump({
        "SUPPLIER_LEAD_MULT": SUPPLIER_LEAD_MULT,
        "SUPPLIER_REJECT_RATE": SUPPLIER_REJECT_RATE,
        "CARRIER_DELAY_PROB": CARRIER_DELAY_PROB,
        "PRODUCT_DEMAND_MULT": PRODUCT_DEMAND_MULT,
        "STORE_TXN_COUNT_MULT": STORE_TXN_COUNT_MULT,
        "STORE_BASKET_SIZE_MULT": STORE_BASKET_SIZE_MULT,
        "STORE_VISIT_FREQ_MULT": STORE_VISIT_FREQ_MULT,
        "REGION_VOLUME_MULT": REGION_VOLUME_MULT,
        "MONSOON_MONTHS": MONSOON_MONTHS,
        "DEGRADE_START": DEGRADE_START,
        "SEVERE_START": SEVERE_START,
    }, f)

customers.to_pickle(f"{OUT}/_customers.pkl")  # re-save with churn_type added
products.to_pickle(f"{OUT}/_products.pkl")
print("\nPhase 2 done.")
