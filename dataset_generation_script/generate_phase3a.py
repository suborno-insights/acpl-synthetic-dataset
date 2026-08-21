import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

rng = np.random.default_rng(123)  # separate stream for phase 3

OUT = "../data"
START = date(2024, 1, 1)
END = date(2025, 12, 31)
ALL_DATES = pd.date_range(START, END, freq="D")
N_DAYS = len(ALL_DATES)

warehouses = pd.read_pickle(f"{OUT}/_warehouses.pkl")
stores = pd.read_pickle(f"{OUT}/_stores.pkl")
suppliers = pd.read_pickle(f"{OUT}/_suppliers.pkl")
products = pd.read_pickle(f"{OUT}/_products.pkl")
customers = pd.read_pickle(f"{OUT}/_customers.pkl")
carriers = pd.read_pickle(f"{OUT}/_carriers.pkl")
with open(f"{OUT}/_warehouse_serves.pkl","rb") as f:
    WMAP = pickle.load(f)
with open(f"{OUT}/_phase2_logic.pkl","rb") as f:
    L = pickle.load(f)

WAREHOUSE_SERVES = WMAP["WAREHOUSE_SERVES"]
RISK_SUPPLIER_IDS = WMAP["RISK_SUPPLIER_IDS"]

def day_of(d):
    return (d - START).days

# ---------------------------------------------------------------
# 3a. PURCHASE ORDERS (Supplier -> Warehouse)
# ---------------------------------------------------------------
active_products = products[products["is_active"]].copy()
po_rows = []
po_id_ctr = 1

for _, prod in active_products.iterrows():
    pid = prod["product_id"]
    sup_id = prod["primary_supplier_id"]
    sup = suppliers[suppliers["supplier_id"]==sup_id].iloc[0]
    base_lead = sup["base_lead_time_days"]
    lead_mult_arr = L["SUPPLIER_LEAD_MULT"][sup_id]
    reject_arr = L["SUPPLIER_REJECT_RATE"][sup_id]

    # each product ordered into all 3 warehouses periodically (every ~10-18 days), starting from launch
    launch_day = max(0, day_of(prod["launch_date"]) if prod["launch_date"] >= START else 0)
    for wh_id in warehouses["warehouse_id"]:
        cursor = launch_day + int(rng.integers(0, 14))
        while cursor < N_DAYS - 5:
            order_date = START + timedelta(days=int(cursor))
            lead_days = max(1, int(round(base_lead * lead_mult_arr[cursor])))
            expected_delivery = order_date + timedelta(days=lead_days)

            # actual delivery: small noise around expected, occasionally much later for risk suppliers
            extra_delay = 0
            if rng.random() < 0.08:  # 8% chance of extra unexpected delay on top of modeled lead time
                extra_delay = int(rng.integers(1, 6))
            noise = int(rng.integers(-1, 2))  # +/-1 day routine noise
            actual_delivery = expected_delivery + timedelta(days=max(0, extra_delay + noise))

            order_qty = int(max(50, rng.normal(400, 120)))
            reject_p = reject_arr[cursor]
            qty_rejected = int(rng.binomial(order_qty, min(reject_p, 0.9)))
            qty_received = order_qty - qty_rejected

            if actual_delivery > END:
                status = "Pending"
            elif qty_rejected == order_qty:
                status = "Cancelled"
            elif qty_rejected / order_qty > 0.05:  # only material rejection counts as Partial
                status = "Partial"
            elif actual_delivery > expected_delivery:
                status = "Delayed"
            else:
                status = "Delivered"

            rejection_reason = ""
            if qty_rejected > 0:
                rejection_reason = rng.choice(["Quality defect","Damaged in transit","Wrong specification","Expired/near-expiry"],
                                               p=[0.45,0.25,0.15,0.15])

            po_rows.append({
                "po_id": f"PO{po_id_ctr:06d}",
                "supplier_id": sup_id,
                "product_id": pid,
                "warehouse_id": wh_id,
                "order_date": order_date,
                "expected_delivery_date": expected_delivery,
                "actual_delivery_date": actual_delivery if actual_delivery <= END else pd.NaT,
                "order_qty": order_qty,
                "unit_cost": prod["unit_cost"],
                "qty_received": qty_received if actual_delivery <= END else 0,
                "qty_rejected": qty_rejected if actual_delivery <= END else 0,
                "rejection_reason": rejection_reason,
                "po_status": status,
            })
            po_id_ctr += 1
            # next order cycle: 7-13 days (tighter cycle -> fewer natural stockout gaps for reliable suppliers)
            cursor += int(rng.integers(7, 14))

purchase_orders = pd.DataFrame(po_rows)
print("purchase_orders:", purchase_orders.shape)
print(purchase_orders["po_status"].value_counts())
purchase_orders.to_pickle(f"{OUT}/_purchase_orders.pkl")
