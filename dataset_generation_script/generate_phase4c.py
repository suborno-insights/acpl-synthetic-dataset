import numpy as np
import pandas as pd
import pickle

rng = np.random.default_rng(4040)
OUT = "../data"
FINAL = "../data"

with open(f"{OUT}/_issue_log_partial2.pkl","rb") as f:
    ISSUE_LOG = pickle.load(f)

def log(table, issue_type, rate, desc):
    ISSUE_LOG.append({"table": table, "issue_type": issue_type, "approx_rate": rate, "description": desc})

def random_mask(n, rate):
    return rng.random(n) < rate

def mixed_date_format(d):
    if pd.isna(d): return d
    d = pd.Timestamp(d)
    fmt = rng.choice(["iso","slash","text"])
    if fmt == "iso": return d.strftime("%Y-%m-%d")
    elif fmt == "slash": return d.strftime("%d/%m/%Y")
    else:
        try: return d.strftime("%B %-d, %Y")
        except ValueError: return d.strftime("%B %d, %Y")

sales = pd.read_pickle(f"{OUT}/_sales_transactions.pkl")
n = len(sales)
print("Starting sales_transactions:", sales.shape)

# 1. Missing customer_id (anonymous/cash sale not logged properly) ~5%
mask = random_mask(n, 0.05)
sales.loc[mask, "customer_id"] = np.nan
log("sales_transactions","missing_values",0.05,"customer_id blank (anonymous/unlogged sale)")

# 2. Missing discount_pct representation inconsistency: NaN vs 0 vs "None" string mixed
sales["discount_pct"] = sales["discount_pct"].astype(object)
mask = random_mask(n, 0.04)
sales.loc[mask, "discount_pct"] = np.nan
mask2 = random_mask(n, 0.03)
sales.loc[mask2, "discount_pct"] = "None"
log("sales_transactions","inconsistent_missing_representation",0.07,"discount_pct blank in some rows, literal string 'None' in others (inconsistent null representation)")

# 3. Duplicate transactions (system glitch double-charge) ~0.8%
dup_idx = rng.choice(sales.index, size=int(n*0.008), replace=False)
dups = sales.loc[dup_idx].copy()
sales = pd.concat([sales, dups], ignore_index=True)
log("sales_transactions","duplicate_rows",len(dup_idx),"transaction rows duplicated (simulated POS double-submit)")
n = len(sales)

# 4. Outliers: negative quantity, price=0, absurdly large quantity (data entry errors)
idx_neg_qty = rng.choice(sales.index, size=max(1,int(n*0.001)), replace=False)
sales.loc[idx_neg_qty, "quantity"] = -sales.loc[idx_neg_qty, "quantity"]
idx_zero_price = rng.choice(sales.index, size=max(1,int(n*0.001)), replace=False)
sales.loc[idx_zero_price, "unit_price"] = 0
idx_huge_qty = rng.choice(sales.index, size=max(1,int(n*0.0005)), replace=False)
sales.loc[idx_huge_qty, "quantity"] = sales.loc[idx_huge_qty, "quantity"] * rng.integers(50,150,len(idx_huge_qty))
log("sales_transactions","outliers",0.0025,"negative quantity / zero unit_price / absurdly large quantity (data entry errors)")

# 5. total_amount inconsistency: for a small % of rows, total_amount NOT recomputed after the above edits
#    (simulates a system that stores total_amount separately and doesn't always reconcile) -- already
#    naturally inconsistent for the outlier rows above since we didn't recompute; document it.
log("sales_transactions","logical_inconsistency",0.0025,"total_amount not recalculated for the outlier rows above -> total_amount no longer equals quantity*unit_price for those rows")

# 6. orphan product_id: a few transactions reference a product_id that is NOT in products.csv
#    (simulates historical sales of a fully-removed/delisted SKU)
mask = random_mask(n, 0.001)
sales.loc[mask, "product_id"] = "P999"
log("sales_transactions","orphan_foreign_key",0.001,"product_id set to non-existent P999 (delisted SKU no longer in products table)")

# 7. payment_method casing inconsistency + placeholder
mask = random_mask(n, 0.10)
sales.loc[mask, "payment_method"] = sales.loc[mask, "payment_method"].apply(lambda x: str(x).upper() if rng.random()<0.5 else str(x).lower())
mask2 = random_mask(n, 0.01)
sales.loc[mask2, "payment_method"] = rng.choice(["N/A","Unknown","-"], size=mask2.sum())
log("sales_transactions","inconsistent_text_case_and_placeholders",0.11,"payment_method case inconsistency + N/A-style placeholders")

# 8. store_id whitespace/case inconsistency
mask = random_mask(n, 0.06)
sales.loc[mask, "store_id"] = sales.loc[mask, "store_id"].apply(lambda x: f" {x} " if rng.random()<0.5 else str(x).lower())
log("sales_transactions","inconsistent_text_case_whitespace",0.06,"store_id whitespace/case inconsistency")

# 9. mixed date formats
sales["transaction_date"] = sales["transaction_date"].apply(mixed_date_format)
log("sales_transactions","inconsistent_date_format",1.0,"transaction_date mixed formats")

print("Final sales_transactions:", sales.shape)
sales.to_csv(f"{FINAL}/sales_transactions.csv", index=False)

with open(f"{OUT}/_issue_log_final.pkl","wb") as f:
    pickle.dump(ISSUE_LOG, f)
print(f"Total issues logged: {len(ISSUE_LOG)}")
