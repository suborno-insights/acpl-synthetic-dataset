import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

rng = np.random.default_rng(131415)

OUT = "../data"
START = date(2024, 1, 1)
END = date(2025, 12, 31)
ALL_DATES = pd.date_range(START, END, freq="D")
N_DAYS = len(ALL_DATES)

stores = pd.read_pickle(f"{OUT}/_stores.pkl")
products = pd.read_pickle(f"{OUT}/_products.pkl")
customers = pd.read_pickle(f"{OUT}/_customers.pkl")
promotions = pd.read_pickle(f"{OUT}/_promotions.pkl")
inventory_snapshots = pd.read_pickle(f"{OUT}/_inventory_snapshots.pkl")
with open(f"{OUT}/_warehouse_serves.pkl","rb") as f:
    WMAP = pickle.load(f)
with open(f"{OUT}/_phase2_logic.pkl","rb") as f:
    L = pickle.load(f)

REGION_PRIMARY_WH = WMAP["REGION_PRIMARY_WH"]
DAILY_FACTOR = np.load(f"{OUT}/_daily_factor.npy")

active_products = products[products["is_active"]].copy()
prod_ids = active_products["product_id"].values
prod_category = dict(zip(active_products["product_id"], active_products["category"]))
prod_price = dict(zip(active_products["product_id"], active_products["unit_price"]))

# category popularity weights (grocery/beverages bought far more often than e.g. footwear)
CATEGORY_WEIGHT = {
    "Grocery": 3.5, "Beverages": 2.5, "Personal Care": 1.8, "Home & Kitchen": 1.2,
    "Stationery": 1.0, "Apparel": 0.8, "Footwear": 0.5, "Electronics Accessories": 0.6,
}
prod_weight = np.array([CATEGORY_WEIGHT[prod_category[p]] for p in prod_ids])
prod_weight = prod_weight / prod_weight.sum()

# product_id -> daily demand multiplier array (trend+noise), and category baseline
PRODUCT_DEMAND_MULT = L["PRODUCT_DEMAND_MULT"]

# FIX: precompute a per-day product selection weight matrix so each product's own
# growing/declining/stable trend actually drives how OFTEN it's bought, not just the
# quantity per transaction. Previously prod_weight was static (category-only), which
# diluted the trend signal almost entirely. weight(p,d) ∝ category_weight * demand_mult(p,d)
demand_matrix = np.vstack([PRODUCT_DEMAND_MULT[p] for p in prod_ids])  # shape (n_products, N_DAYS)
weighted_matrix = demand_matrix * prod_weight[:, None]
DAILY_PROD_WEIGHTS = weighted_matrix / weighted_matrix.sum(axis=0, keepdims=True)  # normalize per day

# Build product-day stockout suppression lookup (only for risk-linked/daily-granularity products
# since those are the ones we can trace at daily level; store mapped to its primary warehouse)
RISK_LINKED_IDS = set(products[products["_risk_linked_INTERNAL"]]["product_id"])
stockout_by_prod_wh_day = {}
daily_snap = inventory_snapshots[inventory_snapshots["snapshot_granularity"]=="daily"]
for (pid, wh), grp in daily_snap.groupby(["product_id","warehouse_id"]):
    days = set(pd.to_datetime(grp[grp["stockout_flag"]]["snapshot_date"]).dt.date)
    stockout_by_prod_wh_day[(pid, wh)] = days

# promotions lookup: for a given product+date, is there an active promo? what lift/discount?
promo_by_product = {}
for _, p in promotions.iterrows():
    promo_by_product.setdefault(p["product_id"], []).append(p)

def active_promo(pid, d):
    for p in promo_by_product.get(pid, []):
        if p["start_date"] <= d <= p["end_date"]:
            return p
    return None

STORE_TXN_COUNT_MULT = L["STORE_TXN_COUNT_MULT"]
STORE_BASKET_SIZE_MULT = L["STORE_BASKET_SIZE_MULT"]
REGION_VOLUME_MULT = L["REGION_VOLUME_MULT"]

# customers grouped by preferred store for faster sampling
cust_by_store = {sid: grp["customer_id"].values for sid, grp in customers.groupby("preferred_store_id")}
cust_join = dict(zip(customers["customer_id"], customers["join_date"]))
cust_churn_type = dict(zip(customers["customer_id"], customers["_churn_type_INTERNAL"]))

# churn cutoff: customers stop (abrupt) or fade (gradual) in the last ~6 months (from ~2025-07-01)
CHURN_WINDOW_START = date(2025, 7, 1)

txn_rows = []
txn_id_ctr = 1
PAYMENTS = ["Cash","Card","Mobile Banking"]

for _, st in stores.iterrows():
    store_id = st["store_id"]
    region = st["region"]
    store_type = st["store_type"]
    primary_wh = REGION_PRIMARY_WH[region]
    cust_pool = cust_by_store.get(store_id, np.array([]))
    if len(cust_pool) == 0:
        continue

    base_daily_txn = 18 * STORE_TXN_COUNT_MULT[store_type] * REGION_VOLUME_MULT[region]

    for d_idx, d in enumerate(ALL_DATES):
        dday = d.date()
        day_factor = DAILY_FACTOR[d_idx]
        n_txn = rng.poisson(max(1, base_daily_txn * day_factor))

        for _ in range(n_txn):
            pid = rng.choice(prod_ids, p=DAILY_PROD_WEIGHTS[:, d_idx])

            # stockout suppression (only meaningful for risk-linked products at primary warehouse)
            if pid in RISK_LINKED_IDS:
                so_days = stockout_by_prod_wh_day.get((pid, primary_wh), set())
                if dday in so_days and rng.random() < 0.75:
                    continue  # 75% chance this sale simply doesn't happen (stockout suppressed demand)

            cust_id = rng.choice(cust_pool)
            join_d = cust_join[cust_id]
            if join_d > dday:
                continue  # customer hadn't joined yet
            ctype = cust_churn_type[cust_id]
            if ctype == "abrupt" and dday >= CHURN_WINDOW_START:
                if rng.random() < 0.97:
                    continue  # abrupt churner: essentially stops after churn window starts
            elif ctype == "gradual" and dday >= date(2025,1,1):
                months_in = max(0, (dday - date(2025,1,1)).days / 30)
                fade_prob = min(0.95, months_in * 0.08)  # gradually increasing chance of no purchase
                if rng.random() < fade_prob:
                    continue

            demand_mult = PRODUCT_DEMAND_MULT[pid][d_idx]
            # quantity per transaction: basket size effect only (trend already applied via selection weight above)
            qty = max(1, int(round(rng.poisson(1.6 * STORE_BASKET_SIZE_MULT[store_type]))))

            base_price = prod_price[pid]
            promo = active_promo(pid, dday)
            discount_pct = 0
            promo_id = None
            if promo is not None:
                discount_pct = promo["discount_pct"]
                promo_id = promo["promo_id"]
                # lift: probabilistically add extra transactions handled implicitly via higher qty/selection;
                # here we boost qty using the promo's lift_pct
                lift = promo["_lift_pct_INTERNAL"] / 100
                if rng.random() < lift:
                    qty += max(1, int(round(qty * rng.uniform(0.3,0.8))))

            unit_price = round(base_price * (1 - discount_pct/100), 2)
            total_amount = round(unit_price * qty, 2)

            txn_rows.append({
                "transaction_id": f"TXN{txn_id_ctr:07d}",
                "transaction_date": dday,
                "store_id": store_id,
                "customer_id": cust_id,
                "product_id": pid,
                "quantity": qty,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "promo_id": promo_id,
                "payment_method": rng.choice(PAYMENTS, p=[0.35,0.40,0.25]),
                "total_amount": total_amount,
            })
            txn_id_ctr += 1

    print(f"{store_id} done, running total rows: {len(txn_rows)}")

sales_transactions = pd.DataFrame(txn_rows)
print("\nsales_transactions:", sales_transactions.shape)
print(sales_transactions["promo_id"].notna().mean(), "fraction with active promo")
sales_transactions.to_pickle(f"{OUT}/_sales_transactions.pkl")
