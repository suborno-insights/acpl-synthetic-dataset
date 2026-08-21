import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

rng = np.random.default_rng(2024)
OUT = "../data"
FINAL = "../data"

with open(f"{OUT}/_issue_log_partial.pkl","rb") as f:
    ISSUE_LOG = pickle.load(f)

def log(table, issue_type, rate, desc):
    ISSUE_LOG.append({"table": table, "issue_type": issue_type, "approx_rate": rate, "description": desc})

def drop_internal(df):
    return df[[c for c in df.columns if not c.endswith("_INTERNAL")]].copy()

def random_mask(n, rate):
    return rng.random(n) < rate

def mixed_date_format(d):
    if pd.isna(d):
        return d
    d = pd.Timestamp(d)
    fmt = rng.choice(["iso","slash","text"])
    if fmt == "iso":
        return d.strftime("%Y-%m-%d")
    elif fmt == "slash":
        return d.strftime("%d/%m/%Y")
    else:
        try:
            return d.strftime("%B %-d, %Y")
        except ValueError:
            return d.strftime("%B %d, %Y")

def messy_case(s):
    r = rng.random()
    if r < 0.33: return str(s).upper()
    elif r < 0.66: return str(s).lower()
    else: return " " + str(s) + " "

# =====================================================================
# 6. CARRIERS
# =====================================================================
carriers = pd.read_pickle(f"{OUT}/_carriers.pkl")
mask = random_mask(len(carriers), 0.4)
carriers.loc[mask, "carrier_name"] = carriers.loc[mask, "carrier_name"].apply(messy_case)
log("carriers","inconsistent_text_case_whitespace",0.4,"carrier_name case/whitespace inconsistency")
carriers.to_csv(f"{FINAL}/carriers.csv", index=False)

# =====================================================================
# 7. PURCHASE ORDERS
# =====================================================================
po = pd.read_pickle(f"{OUT}/_purchase_orders.pkl")
n = len(po)

# missing qty_rejected (7%)
mask = random_mask(n, 0.07)
po.loc[mask, "qty_rejected"] = np.nan
log("purchase_orders","missing_values",0.07,"qty_rejected blank")

# negative order_qty outlier (data entry error, ~0.3%)
mask = random_mask(n, 0.003)
po.loc[mask, "order_qty"] = -po.loc[mask, "order_qty"]
log("purchase_orders","outlier_negative_qty",0.003,"order_qty entered as negative (sign error)")

# logical inconsistency: actual_delivery_date before order_date (typo) ~0.5%
valid_actual = po["actual_delivery_date"].notna()
candidates = po[valid_actual].sample(frac=0.005, random_state=1).index
po.loc[candidates, "actual_delivery_date"] = po.loc[candidates, "order_date"] - pd.to_timedelta(rng.integers(1,10,len(candidates)), unit="D")
log("purchase_orders","logical_inconsistency",0.005,"actual_delivery_date earlier than order_date (impossible, data entry typo)")

# orphan product_id / supplier_id (typo'd IDs that don't exist in dimension tables) ~0.4%
mask = random_mask(n, 0.002)
po.loc[mask, "product_id"] = po.loc[mask, "product_id"].apply(lambda x: x[:-1] + "9X")
log("purchase_orders","orphan_foreign_key",0.002,"product_id typo'd, no longer matches products table (orphan record)")
mask2 = random_mask(n, 0.002)
po.loc[mask2, "supplier_id"] = po.loc[mask2, "supplier_id"].apply(lambda x: "S999")
log("purchase_orders","orphan_foreign_key",0.002,"supplier_id set to non-existent S999 (orphan record)")

# rejection_reason inconsistent casing / placeholders
mask = random_mask(n, 0.15)
po.loc[mask & (po["rejection_reason"]!=""), "rejection_reason"] = po.loc[mask & (po["rejection_reason"]!=""), "rejection_reason"].apply(
    lambda x: messy_case(x) if x else x)
log("purchase_orders","inconsistent_text_case",0.15,"rejection_reason case/whitespace inconsistency")

# duplicate rows (system glitch double-submit) ~0.5%
dup_idx = rng.choice(po.index, size=int(n*0.005), replace=False)
dups = po.loc[dup_idx].copy()
po = pd.concat([po, dups], ignore_index=True)
log("purchase_orders","duplicate_rows",len(dup_idx),"PO rows duplicated (simulated double-submit)")

# mixed date formats (render dates as strings)
for col in ["order_date","expected_delivery_date","actual_delivery_date"]:
    po[col] = po[col].apply(mixed_date_format)
log("purchase_orders","inconsistent_date_format",1.0,"order/expected/actual delivery dates mixed formats")

po.to_csv(f"{FINAL}/purchase_orders.csv", index=False)
print("purchase_orders messy:", po.shape)

# =====================================================================
# 8. INVENTORY SNAPSHOTS
# =====================================================================
inv = pd.read_pickle(f"{OUT}/_inventory_snapshots.pkl")
n = len(inv)
mask = random_mask(n, 0.04)
inv.loc[mask, "stock_qty"] = np.nan
log("inventory_snapshots","missing_values",0.04,"stock_qty blank")
# negative stock outlier (should never happen logically, simulate sensor/entry glitch) ~0.2%
mask = random_mask(n, 0.002)
inv.loc[mask, "stock_qty"] = -np.abs(inv.loc[mask, "stock_qty"].fillna(10))
log("inventory_snapshots","outlier_negative_stock",0.002,"stock_qty negative (impossible, sensor/entry glitch)")
inv["snapshot_date"] = inv["snapshot_date"].apply(mixed_date_format)
log("inventory_snapshots","inconsistent_date_format",1.0,"snapshot_date mixed formats")
inv.to_csv(f"{FINAL}/inventory_snapshots.csv", index=False)
print("inventory_snapshots messy:", inv.shape)

# =====================================================================
# 9. SHIPMENTS
# =====================================================================
sh = pd.read_pickle(f"{OUT}/_shipments.pkl")
n = len(sh)
mask = random_mask(n, 0.05)
sh.loc[mask, "shipment_cost"] = np.nan
log("shipments","missing_values",0.05,"shipment_cost blank")
# mixed units: some distance_km rows actually recorded in miles (unlabeled, value divided by 1.609)
mask = random_mask(n, 0.10)
sh.loc[mask, "distance_km"] = (sh.loc[mask, "distance_km"] / 1.609).round(1)
log("shipments","mixed_units",0.10,"distance_km sometimes actually recorded in miles, unlabeled (unit inconsistency)")
# orphan store_id typo ~0.3%
mask = random_mask(n, 0.003)
sh.loc[mask, "store_id"] = "ST99"
log("shipments","orphan_foreign_key",0.003,"store_id set to non-existent ST99 (orphan record)")
# duplicate shipments
dup_idx = rng.choice(sh.index, size=int(n*0.01), replace=False)
dups = sh.loc[dup_idx].copy()
sh = pd.concat([sh, dups], ignore_index=True)
log("shipments","duplicate_rows",len(dup_idx),"shipment rows duplicated")
for col in ["dispatch_date","expected_arrival_date","actual_arrival_date"]:
    sh[col] = sh[col].apply(mixed_date_format)
log("shipments","inconsistent_date_format",1.0,"dispatch/expected/actual arrival dates mixed formats")
sh.to_csv(f"{FINAL}/shipments.csv", index=False)
print("shipments messy:", sh.shape)

# =====================================================================
# 10. PROMOTIONS
# =====================================================================
promo = pd.read_pickle(f"{OUT}/_promotions.pkl")
promo = promo.drop(columns=[c for c in promo.columns if c.endswith("_INTERNAL")])
n = len(promo)
mask = random_mask(n, 0.08)
promo.loc[mask, "discount_pct"] = np.nan
log("promotions","missing_values",0.08,"discount_pct blank")
mask = random_mask(n, 0.15)
promo.loc[mask, "channel"] = promo.loc[mask, "channel"].apply(messy_case)
log("promotions","inconsistent_text_case_whitespace",0.15,"channel case/whitespace inconsistency")
for col in ["start_date","end_date"]:
    promo[col] = promo[col].apply(mixed_date_format)
log("promotions","inconsistent_date_format",1.0,"start/end date mixed formats")
promo.to_csv(f"{FINAL}/promotions.csv", index=False)
print("promotions messy:", promo.shape)

with open(f"{OUT}/_issue_log_partial2.pkl","wb") as f:
    pickle.dump(ISSUE_LOG, f)
print(f"Total issues logged so far: {len(ISSUE_LOG)}")
