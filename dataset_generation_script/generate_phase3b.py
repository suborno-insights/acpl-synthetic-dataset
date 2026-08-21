import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

rng = np.random.default_rng(456)

OUT = "../data"
START = date(2024, 1, 1)
END = date(2025, 12, 31)
ALL_DATES = pd.date_range(START, END, freq="D")
N_DAYS = len(ALL_DATES)

warehouses = pd.read_pickle(f"{OUT}/_warehouses.pkl")
products = pd.read_pickle(f"{OUT}/_products.pkl")
purchase_orders = pd.read_pickle(f"{OUT}/_purchase_orders.pkl")
with open(f"{OUT}/_phase2_logic.pkl","rb") as f:
    L = pickle.load(f)

active_products = products[products["is_active"]].copy()

def day_of(d):
    if pd.isna(d):
        return None
    if hasattr(d, "date"):
        d = d.date()
    return (d - START).days

# pre-index PO receipts by (product, warehouse) -> array of (day, qty_received)
po = purchase_orders.copy()
po["recv_day"] = po["actual_delivery_date"].apply(day_of)
po_valid = po.dropna(subset=["recv_day"])

snap_rows = []
RISK_LINKED_IDS = set(products[products["_risk_linked_INTERNAL"]]["product_id"])

for _, prod in active_products.iterrows():
    pid = prod["product_id"]
    demand_curve = L["PRODUCT_DEMAND_MULT"][pid]
    daily_granularity = pid in RISK_LINKED_IDS

    for wh_id in warehouses["warehouse_id"]:
        receipts = po_valid[(po_valid["product_id"]==pid) & (po_valid["warehouse_id"]==wh_id)]
        recv_by_day = np.zeros(N_DAYS)
        for _, r in receipts.iterrows():
            d = int(r["recv_day"])
            if 0 <= d < N_DAYS:
                recv_by_day[d] += r["qty_received"]

        # simulate daily outflow proportional to product demand curve (represents shipments-to-store + local consumption)
        base_outflow = rng.uniform(15, 45)  # units/day baseline for this product-warehouse
        outflow = base_outflow * demand_curve
        outflow *= (1 + rng.normal(0, 0.12, N_DAYS))  # extra daily noise
        outflow = np.clip(outflow, 0, None)

        reorder_point = int(base_outflow * 18)  # ~18 days of average demand as safety buffer

        stock = np.zeros(N_DAYS)
        cur = rng.uniform(reorder_point*2, reorder_point*3.5)  # starting stock, healthier buffer
        stockout_flag = np.zeros(N_DAYS, dtype=bool)
        for d in range(N_DAYS):
            cur += recv_by_day[d]
            cur -= outflow[d]
            if cur < 0:
                cur = 0
            stock[d] = cur
            stockout_flag[d] = cur <= 0

        if daily_granularity:
            for d in range(N_DAYS):
                snap_rows.append({
                    "snapshot_date": START + timedelta(days=d),
                    "product_id": pid,
                    "warehouse_id": wh_id,
                    "stock_qty": int(round(stock[d])),
                    "reorder_point": reorder_point,
                    "stockout_flag": bool(stockout_flag[d]),
                    "snapshot_granularity": "daily",
                })
        else:
            for d in range(0, N_DAYS, 7):
                snap_rows.append({
                    "snapshot_date": START + timedelta(days=d),
                    "product_id": pid,
                    "warehouse_id": wh_id,
                    "stock_qty": int(round(stock[d])),
                    "reorder_point": reorder_point,
                    "stockout_flag": bool(stockout_flag[d]),
                    "snapshot_granularity": "weekly",
                })

inventory_snapshots = pd.DataFrame(snap_rows)
print("inventory_snapshots:", inventory_snapshots.shape)
print(inventory_snapshots["snapshot_granularity"].value_counts())
print("Overall stockout rate:", inventory_snapshots["stockout_flag"].mean())

# compare stockout rate for risk-linked vs non-risk-linked (sanity check the story)
risk_snap = inventory_snapshots[inventory_snapshots["product_id"].isin(RISK_LINKED_IDS)]
nonrisk_snap = inventory_snapshots[~inventory_snapshots["product_id"].isin(RISK_LINKED_IDS)]
print("Stockout rate - risk-linked products:", risk_snap["stockout_flag"].mean())
print("Stockout rate - non-risk products:", nonrisk_snap["stockout_flag"].mean())

inventory_snapshots.to_pickle(f"{OUT}/_inventory_snapshots.pkl")
