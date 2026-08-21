import numpy as np
import pandas as pd
from datetime import date, timedelta
import os

rng = np.random.default_rng(999)
OUT = "../data"
FINAL = "../data"
os.makedirs(FINAL, exist_ok=True)

ISSUE_LOG = []  # (table, issue_type, approx_rate_or_count, description)

def log(table, issue_type, rate, desc):
    ISSUE_LOG.append({"table": table, "issue_type": issue_type, "approx_rate": rate, "description": desc})

def drop_internal(df):
    return df[[c for c in df.columns if not c.endswith("_INTERNAL")]].copy()

def random_mask(n, rate):
    return rng.random(n) < rate

def mixed_date_format(d):
    """Return a date rendered in one of 3 different string formats (simulates inconsistent manual entry)."""
    if pd.isna(d):
        return d
    d = pd.Timestamp(d)
    fmt = rng.choice(["iso","slash","text"])
    if fmt == "iso":
        return d.strftime("%Y-%m-%d")
    elif fmt == "slash":
        return d.strftime("%d/%m/%Y")
    else:
        return d.strftime("%B %-d, %Y") if hasattr(d,'strftime') else str(d)

def messy_case(s, rng_local=rng):
    r = rng_local.random()
    if r < 0.33:
        return str(s).upper()
    elif r < 0.66:
        return str(s).lower()
    else:
        return " " + str(s) + " "  # stray whitespace

# =====================================================================
# 1. STORES
# =====================================================================
stores = drop_internal(pd.read_pickle(f"{OUT}/_stores.pkl"))
n = len(stores)
# inconsistent city/region casing + whitespace (aggressive: 25%)
mask = random_mask(n, 0.25)
stores.loc[mask, "city"] = stores.loc[mask, "city"].apply(lambda x: messy_case(x))
log("stores","inconsistent_text_case_whitespace",0.25,"city field randomly upper/lower/whitespace-padded")
# missing manager_name (8%)
mask = random_mask(n, 0.08)
stores.loc[mask, "manager_name"] = np.nan
log("stores","missing_values",0.08,"manager_name blank")
# 1 duplicate store row (slightly different formatting)
dup = stores.iloc[[2]].copy()
dup["city"] = dup["city"].astype(str) + " "
stores = pd.concat([stores, dup], ignore_index=True)
log("stores","duplicate_row",1,"1 store duplicated with trailing whitespace variant")
# mixed date format in opening_date (all rows, rendered as string)
stores["opening_date"] = stores["opening_date"].apply(mixed_date_format)
log("stores","inconsistent_date_format",1.0,"opening_date mixes ISO / DD-MM-YYYY / 'Month D, YYYY' text formats")

# =====================================================================
# 2. WAREHOUSES
# =====================================================================
warehouses = drop_internal(pd.read_pickle(f"{OUT}/_warehouses.pkl"))
warehouses.loc[1, "capacity_units"] = np.nan
log("warehouses","missing_values",1,"1 warehouse missing capacity_units")
warehouses["operational_since"] = warehouses["operational_since"].apply(mixed_date_format)
log("warehouses","inconsistent_date_format",1.0,"operational_since mixed formats")

# =====================================================================
# 3. SUPPLIERS
# =====================================================================
suppliers_full = pd.read_pickle(f"{OUT}/_suppliers.pkl")
suppliers = drop_internal(suppliers_full)
n = len(suppliers)
mask = random_mask(n, 0.20)
suppliers.loc[mask, "region"] = suppliers.loc[mask, "region"].apply(lambda x: messy_case(x))
log("suppliers","inconsistent_text_case_whitespace",0.20,"region field case/whitespace inconsistency")
mask = random_mask(n, 0.10)
suppliers.loc[mask, "payment_terms_days"] = np.nan
log("suppliers","missing_values",0.10,"payment_terms_days blank")
suppliers["contract_start_date"] = suppliers["contract_start_date"].apply(mixed_date_format)
log("suppliers","inconsistent_date_format",1.0,"contract_start_date mixed formats")
# placeholder values in categories_supplied
mask = random_mask(n, 0.05)
suppliers.loc[mask, "categories_supplied"] = rng.choice(["N/A","Unknown","-","TBD"], size=mask.sum())
log("suppliers","placeholder_values",0.05,"categories_supplied replaced with N/A-style placeholders")

# =====================================================================
# 4. PRODUCTS
# =====================================================================
products_full = pd.read_pickle(f"{OUT}/_products.pkl")
products = drop_internal(products_full)
n = len(products)
mask = random_mask(n, 0.22)
products.loc[mask, "category"] = products.loc[mask, "category"].apply(lambda x: messy_case(x))
log("products","inconsistent_text_case_whitespace",0.22,"category field case/whitespace inconsistency")
# missing unit_cost / unit_price
mask = random_mask(n, 0.06)
products.loc[mask, "unit_cost"] = np.nan
log("products","missing_values",0.06,"unit_cost blank")
# currency-symbol string inconsistency in unit_price (stored as text with Tk symbol for some rows)
mask = random_mask(n, 0.08)
products["unit_price"] = products["unit_price"].astype(object)
products.loc[mask, "unit_price"] = products.loc[mask, "unit_price"].apply(lambda x: f"৳{x}")
log("products","currency_symbol_inconsistency",0.08,"unit_price stored as string with ৳ symbol instead of numeric")
# outlier: a couple of impossible prices (data entry error - extra zero, or zero price)
outlier_idx = rng.choice(products.index, size=3, replace=False)
for i, idx in enumerate(outlier_idx):
    if i == 0:
        products.loc[idx, "unit_price"] = 0
    elif i == 1:
        try:
            products.loc[idx, "unit_cost"] = float(products.loc[idx, "unit_cost"]) * 10
        except Exception:
            pass
    else:
        products.loc[idx, "unit_cost"] = -abs(float(str(products.loc[idx,"unit_cost"]).replace("৳","")) if not pd.isna(products.loc[idx,"unit_cost"]) else 50)
log("products","outliers_impossible_values",3,"3 products with zero price / 10x cost typo / negative cost")
# 1 duplicate product row
dup = products.iloc[[5]].copy()
products = pd.concat([products, dup], ignore_index=True)
log("products","duplicate_row",1,"1 product duplicated exactly")
products["launch_date"] = products["launch_date"].apply(mixed_date_format)
log("products","inconsistent_date_format",1.0,"launch_date mixed formats")

# =====================================================================
# 5. CUSTOMERS
# =====================================================================
customers_full = pd.read_pickle(f"{OUT}/_customers.pkl")
customers = drop_internal(customers_full)
n = len(customers)
mask = random_mask(n, 0.07)
customers.loc[mask, "region"] = np.nan
log("customers","missing_values",0.07,"region blank")
mask = random_mask(n, 0.15)
customers.loc[mask, "region"] = customers.loc[mask, "region"].apply(lambda x: messy_case(x) if pd.notna(x) else x)
log("customers","inconsistent_text_case_whitespace",0.15,"region case/whitespace inconsistency")
customers["join_date"] = customers["join_date"].apply(mixed_date_format)
log("customers","inconsistent_date_format",1.0,"join_date mixed formats")
# duplicates: 40 customers appear twice (simulating duplicate signup)
dup_idx = rng.choice(customers.index, size=40, replace=False)
dups = customers.loc[dup_idx].copy()
customers = pd.concat([customers, dups], ignore_index=True)
log("customers","duplicate_rows",40,"40 customer_id rows duplicated (simulated duplicate signup / system glitch)")

print("Dimension tables done. Saving intermediate...")
stores.to_csv(f"{FINAL}/stores.csv", index=False)
warehouses.to_csv(f"{FINAL}/warehouses.csv", index=False)
suppliers.to_csv(f"{FINAL}/suppliers.csv", index=False)
products.to_csv(f"{FINAL}/products.csv", index=False)
customers.to_csv(f"{FINAL}/customers.csv", index=False)

import pickle
with open(f"{OUT}/_issue_log_partial.pkl","wb") as f:
    pickle.dump(ISSUE_LOG, f)
print(f"Issues logged so far: {len(ISSUE_LOG)}")
