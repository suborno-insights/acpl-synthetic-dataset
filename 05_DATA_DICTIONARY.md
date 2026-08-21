# 📖 Apex Consumer Products Ltd. (ACPL) — Dataset Data Dictionary

**Company**: Apex Consumer Products Ltd. (ACPL) — fictional Bangladeshi retail chain, 20 stores, 3 warehouses, 45 suppliers.
**Time span**: 2024-01-01 – 2025-12-31 (2 years, 731 days)
**Purpose**: End-to-end supply chain / retail / logistics analytics portfolio — 6 connected projects (Demand Forecasting, Inventory Optimization, Procurement & Supplier Risk, Logistics & Delivery Performance, Retail Sales & Pricing, Customer Analytics).

**⚠️ This dataset is intentionally messy** — missing values, duplicate rows, inconsistent date/text formats, outliers, orphan foreign keys, etc. are spread across every table. Full details in `03_DATA_QUALITY_ISSUES_LOG.md` (issue **types** only, not exact rows).

---

## 🔗 Entity Relationship (high-level)

```
suppliers ──< products ──< purchase_orders >── warehouses ──< inventory_snapshots
                  │                                │
                  │                                └──< shipments >── stores ──< sales_transactions >── customers
                  │                                                                     │
                  └─────────────────────────< promotions >───────────────────────────────┘
                                                                    carriers ──< shipments
```

---

## 📋 Tables

### 🏬 `stores` (20 rows)
| Column | Type | Notes |
|---|---|---|
| store_id | text | PK |
| store_name | text | |
| region | text | Dhaka/Chattogram/Sylhet/Rajshahi/Khulna/Barishal |
| city | text | messy: case/whitespace inconsistent |
| store_type | text | Flagship / Standard / Express |
| store_size_sqft | int | |
| opening_date | text (mixed date formats) | |
| manager_name | text | some missing |

### 🏭 `warehouses` (3 rows)
warehouse_id (PK), warehouse_name, region, capacity_units (1 missing), operational_since (mixed date formats)

### 🤝 `suppliers` (45 rows)
supplier_id (PK), supplier_name, region (messy case), categories_supplied (some placeholder values), contract_start_date (mixed formats), payment_terms_days (some missing), base_lead_time_days

### 📦 `products` (181 rows incl. 1 duplicate)
product_id (PK), product_name, category (messy case), sub_category, unit_cost (some missing/outlier), unit_price (some stored as string with ৳ symbol), primary_supplier_id (FK→suppliers), launch_date (mixed formats), is_active

### 👥 `customers` (6040 rows incl. 40 duplicates)
customer_id (PK), join_date (mixed formats), region (some missing/messy), preferred_store_id (FK→stores), acquisition_channel

### 🚚 `carriers` (5 rows)
carrier_id (PK), carrier_name (messy case), base_reliability

### 🧾 `purchase_orders` (~28,300 rows)
po_id (PK), supplier_id (FK, a few orphaned), product_id (FK, a few orphaned), warehouse_id (FK), order_date, expected_delivery_date, actual_delivery_date (dates mixed format; a few illogical — actual before order), order_qty (a few negative outliers), unit_cost, qty_received, qty_rejected (some missing), rejection_reason, po_status (Delivered/Delayed/Partial/Cancelled/Pending)

### 📊 `inventory_snapshots` (84,180 rows)
snapshot_date (mixed formats), product_id, warehouse_id, stock_qty (some missing/negative outlier), reorder_point, stockout_flag, **snapshot_granularity** ("daily" for the ~20 risk-supplier-linked products, "weekly" for the rest — daily granularity exists specifically so stockout timing can be traced against shipment delays)

### 🚛 `shipments` (~9,050 rows)
shipment_id (PK), warehouse_id (FK), store_id (FK, a few orphaned), carrier_id (FK), dispatch_date/expected_arrival_date/actual_arrival_date (mixed formats), distance_km (⚠️ ~10% of rows are actually in miles, unlabeled), shipment_cost (some missing), shipment_status (On-time/Delayed/Damaged/Lost/In-Transit)

### 🏷️ `promotions` (190 rows)
promo_id (PK), product_id (FK), campaign_name, discount_pct (some missing), start_date/end_date (mixed formats), channel (messy case)

### 💳 `sales_transactions` (~290,700 rows — largest table)
transaction_id (PK), transaction_date (mixed formats), store_id (FK, messy case/whitespace), customer_id (FK, some missing), product_id (FK, a handful orphaned — P999), quantity (a few negative/absurdly large outliers), unit_price (a few zero), discount_pct (missing represented inconsistently — blank AND literal "None" string), promo_id (FK, nullable), payment_method (messy case + placeholders), total_amount (⚠️ not recalculated for the outlier rows — won't always equal quantity×unit_price there)

---

## 📝 Known Design Notes (documented, not bugs)

- **Store-type "Express = frequent small visits"**: only the "smaller basket, fewer daily transactions" part is modeled (via multipliers). Per-customer visit-frequency was intentionally not modeled separately — a scope simplification.
- **Risk-linked products get daily inventory snapshots**, all others weekly — this is intentional, not inconsistent, and lets you trace stockout timing precisely only for the products where the story requires it.
- **Promotion sample on risk-linked products is modest** (~16 events across 11 unique products) — enough for directional/aggregate comparison, not fine-grained per-product statistical testing.
- Six suppliers are quietly "risk" suppliers with different failure modes (lead-time only / reject-rate only / both mild / both severe) — which ones, and when they degrade, is for you to discover through analysis, not disclosed here.

---

## 🏢 Business background (for project framing)

ACPL has noticed declining margins, recurring stockouts at some stores, and overstock at others. This dataset supports investigating: demand patterns & forecasting, inventory optimization, supplier reliability & risk, logistics/carrier performance, pricing & promotion effectiveness, and customer segmentation/churn — six projects sharing one consistent underlying "company," so findings in one area (e.g. a supplier's degrading reliability) causally connect to what you'll find in another (e.g. stockouts, and downstream sales dips) if you dig for it.
