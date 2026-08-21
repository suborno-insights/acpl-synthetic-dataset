# 🧹 Data Quality Issues — Type Log

This document lists **which type of issue was intentionally injected into which table** —
but it does not say which exact row has which problem (that's the whole point: it's meant
to be a cleaning exercise, not a solved answer sheet).

Each issue comes with an approximate rate/count so you can verify, after cleaning, whether
you caught everything.

## 🗃️ Two categories of messiness (an important distinction)

This dataset has two fundamentally different kinds of messiness, and their density
thresholds are deliberately different:

1. **Data-loss messiness** (missing values, outliers, orphan foreign keys, duplicate rows,
   logical inconsistencies) — information is genuinely lost or corrupted here. This category
   was deliberately kept **under 20% per column**, so the dataset stays usable and cleaning
   doesn't become the entire exercise.

2. **Structural/representational messiness** (date format inconsistency — the same date
   written in three different string formats: ISO / `DD-MM-YYYY` / `Month D, YYYY`) — no
   information is lost here; every value is fully recoverable/parseable, only its
   representation differs. This category was **deliberately kept at 100%** (the 20% ceiling
   does not apply here), because:
   - this is genuinely common in real multi-source data integration (different
     systems/Excel exports/manual entry each defaulting to their own format)
   - handling date-parsing ambiguity (e.g., is `02/01/2024` `DD/MM/YYYY` or `MM/DD/YYYY`?) is
     a practical, real-world analytical skill — reducing the rate would have blunted the
     point of the exercise

## ✅ Validation (before vs. after messiness injection — signal integrity check)

After injecting messiness, the underlying business signals (carefully calibrated in Phases
2-3) were re-checked to confirm they hadn't been distorted:

| Signal | Before | After | Verdict |
|---|---|---|---|
| PO status distribution | 58.91/35.11/4.69/1.29% | 58.94/35.08/4.69/1.29% | ✅ Shift 0.03pp |
| Stockout gap (risk vs non-risk) | 31.4% relative | 31.4% relative | ✅ Unchanged |
| Carrier delay differential (CR04 vs CR05) | 35.7% vs 11.8% | 35.7% vs 11.8% | ✅ Shift ≤0.1pp |
| Growing/declining/stable trend ordering | 103.7/-11.3/39.8% | 94.4/-13.5/40.8% (dayfirst-corrected) | ✅ Ordering intact, small magnitude shift (from duplicate injection, expected) |
| Column-level messiness density (data-loss category) | — | max: payment_method 11% | ✅ All under 20% |
| Category-string messiness bias | — | z-scores all within ±2 | ✅ Sampling noise, not systematic bias |
| Missing/duplicate rate vs risk-linked product correlation | — | 5.02% vs 5.15% (customer_id), 13.5% vs 13.8% (duplicate share) | ✅ No bias found |

**Note**: when parsing `transaction_date` with `pd.to_datetime()`, use `dayfirst=True` —
otherwise `DD/MM/YYYY`-format dates will be misread as `MM/DD/YYYY` (this is only ambiguous
when day ≤ 12; pandas parses day > 12 correctly regardless).


## 🏬 `stores`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| inconsistent_text_case_whitespace | 25.0% | city field randomly upper/lower/whitespace-padded |
| missing_values | 8.0% | manager_name blank |
| duplicate_row | 100.0% | 1 store duplicated with trailing whitespace variant |
| inconsistent_date_format | 100.0% | opening_date mixes ISO / DD-MM-YYYY / 'Month D, YYYY' text formats |

## 🏭 `warehouses`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 100.0% | 1 warehouse missing capacity_units |
| inconsistent_date_format | 100.0% | operational_since mixed formats |

## 🤝 `suppliers`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| inconsistent_text_case_whitespace | 20.0% | region field case/whitespace inconsistency |
| missing_values | 10.0% | payment_terms_days blank |
| inconsistent_date_format | 100.0% | contract_start_date mixed formats |
| placeholder_values | 5.0% | categories_supplied replaced with N/A-style placeholders |

## 📦 `products`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| inconsistent_text_case_whitespace | 22.0% | category field case/whitespace inconsistency |
| missing_values | 6.0% | unit_cost blank |
| currency_symbol_inconsistency | 8.0% | unit_price stored as string with ৳ symbol instead of numeric |
| outliers_impossible_values | 3.0 | 3 products with zero price / 10x cost typo / negative cost |
| duplicate_row | 100.0% | 1 product duplicated exactly |
| inconsistent_date_format | 100.0% | launch_date mixed formats |

## 👥 `customers`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 7.0% | region blank |
| inconsistent_text_case_whitespace | 15.0% | region case/whitespace inconsistency |
| inconsistent_date_format | 100.0% | join_date mixed formats |
| duplicate_rows | 40.0 | 40 customer_id rows duplicated (simulated duplicate signup / system glitch) |

## 🚚 `carriers`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| inconsistent_text_case_whitespace | 40.0% | carrier_name case/whitespace inconsistency |

## 🧾 `purchase_orders`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 7.0% | qty_rejected blank |
| outlier_negative_qty | 0.3% | order_qty entered as negative (sign error) |
| logical_inconsistency | 0.5% | actual_delivery_date earlier than order_date (impossible, data entry typo) |
| orphan_foreign_key | 0.2% | product_id typo'd, no longer matches products table (orphan record) |
| orphan_foreign_key | 0.2% | supplier_id set to non-existent S999 (orphan record) |
| inconsistent_text_case | 15.0% | rejection_reason case/whitespace inconsistency |
| duplicate_rows | 140.0 | PO rows duplicated (simulated double-submit) |
| inconsistent_date_format | 100.0% | order/expected/actual delivery dates mixed formats |

## 📊 `inventory_snapshots`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 4.0% | stock_qty blank |
| outlier_negative_stock | 0.2% | stock_qty negative (impossible, sensor/entry glitch) |
| inconsistent_date_format | 100.0% | snapshot_date mixed formats |

## 🚛 `shipments`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 5.0% | shipment_cost blank |
| mixed_units | 10.0% | distance_km sometimes actually recorded in miles, unlabeled (unit inconsistency) |
| orphan_foreign_key | 0.3% | store_id set to non-existent ST99 (orphan record) |
| duplicate_rows | 89.0 | shipment rows duplicated |
| inconsistent_date_format | 100.0% | dispatch/expected/actual arrival dates mixed formats |

## 🏷️ `promotions`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 8.0% | discount_pct blank |
| inconsistent_text_case_whitespace | 15.0% | channel case/whitespace inconsistency |
| inconsistent_date_format | 100.0% | start/end date mixed formats |

## 💳 `sales_transactions`

| Issue Type | Approx Rate/Count | Description |
|---|---|---|
| missing_values | 5.0% | customer_id blank (anonymous/unlogged sale) |
| inconsistent_missing_representation | 7.0% | discount_pct blank in some rows, literal string 'None' in others (inconsistent null representation) |
| duplicate_rows | 2306.0 | transaction rows duplicated (simulated POS double-submit) |
| outliers | 0.2% | negative quantity / zero unit_price / absurdly large quantity (data entry errors) |
| logical_inconsistency | 0.2% | total_amount not recalculated for the outlier rows above -> total_amount no longer equals quantity*unit_price for those rows |
| orphan_foreign_key | 0.1% | product_id set to non-existent P999 (delisted SKU no longer in products table) |
| inconsistent_text_case_and_placeholders | 11.0% | payment_method case inconsistency + N/A-style placeholders |
| inconsistent_text_case_whitespace | 6.0% | store_id whitespace/case inconsistency |
| inconsistent_date_format | 100.0% | transaction_date mixed formats |