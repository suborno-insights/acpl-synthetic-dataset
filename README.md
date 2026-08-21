# 🏭 ACPL Retail Supply-Chain Data Simulation Pipeline

A rule-based statistical simulation pipeline that generates a large, internally-consistent,
intentionally-messy synthetic dataset for a fictional Bangladeshi retail company —
**Apex Consumer Products Ltd. (ACPL)**. Built to support supply-chain / retail / logistics
analytics projects that need a realistic, connected dataset no public dataset provides.

This is not just "a dataset" — it's a small **data engineering project**: schema design,
parameterized business-logic modeling, calibration against target statistics, iterative
bug-catching, and post-generation validation.

---

## 🎯 Why this exists

Public retail/supply-chain datasets are usually either too clean (no real analytical
challenge) or disconnected (a sales table with no matching supplier/logistics data behind
it). This pipeline generates **11 interlinked tables** spanning procurement, inventory,
logistics, and retail sales — all driven by the same underlying "company," so a finding in
one table (e.g. a supplier's reliability degrading) causally connects to what shows up
downstream (stockouts, delayed shipments, sales dips) if you dig for it.

---

## 📚 Contents

| Section | What it covers |
|---|---|
| [Schema Design](01_SCHEMA_DESIGN.md) | 11 tables, why they exist, how they relate |
| [Business Logic Design](02_BUSINESS_LOGIC_DESIGN.md) | Supplier risk curves, carrier delay modeling, promotion lift/dip, churn types — what and why |
| [Data Quality Issues Log](03_DATA_QUALITY_ISSUES_LOG.md) | 49 injected issue types + validation report (no row-level answer key — it's meant to be an exercise) |
| [Engineering Process](04_ENGINEERING_PROCESS.md) | Calibration story, 3 bug-catching case studies, post-messiness validation |
| [Data Dictionary](05_DATA_DICTIONARY.md) | Every table/column explained |

**Brief summary of each below; click through for the full detail.**

### 🗂️ Schema Design (brief)
11 tables — `stores`, `warehouses`, `suppliers`, `products`, `customers`, `carriers`,
`purchase_orders`, `inventory_snapshots`, `shipments`, `promotions`, `sales_transactions` —
linked by foreign keys that trace a product from a supplier, into a warehouse, out to a
store, and into a customer's basket. → [full reasoning](docs/01_SCHEMA_DESIGN.md)

### 🧠 Business Logic Design (brief)
Six suppliers quietly degrade over time (different failure modes: lead-time-only,
reject-rate-only, mild/severe combined), carriers have route- and monsoon-sensitive delay
probabilities, products carry individual growing/declining/stable demand trends layered
under shared seasonality, and customers churn either abruptly or gradually. Every curve has
a documented reason for its shape. → [full reasoning](docs/02_BUSINESS_LOGIC_DESIGN.md)

### 🔧 Engineering Process (brief)
This is where the pipeline stops being "just a script" — includes the calibration work
(e.g. tuning stockout rate from 28.6% down to 15.6% with a documented reason), three
bug-catching case studies (a product-trend signal that was silently getting lost, a
shipment-volume shortfall traced to a miscalibrated constant, and a date-parsing ambiguity
bug), and a full **post-messiness validation** pass confirming the injected messiness didn't
distort the underlying business signals. → [full write-up](docs/04_ENGINEERING_PROCESS.md)

### 🧹 Data Quality / Messiness Injection (brief)
The dataset is deliberately messy — 49 distinct issue types across all 11 tables (missing
values, duplicate rows, inconsistent date formats, outliers, orphan foreign keys, mixed
units, and more), split into two categories with different density rules: **data-loss
messiness** (kept under 20% per column) and **structural/representational messiness**
(date-format inconsistency, kept at 100% — no information is lost, it's a realistic
multi-source-integration problem worth practicing). → [full log + validation](docs/03_DATA_QUALITY_ISSUES_LOG.md)

---

## 📐 Methodology & honest scope note

This pipeline uses **rule-based statistical simulation** — probability distributions,
parameterized degradation/growth curves, seasonality functions, and layered random noise —
not GAN-based or deep-learning-based synthetic data generation. It's a deliberately
transparent, inspectable approach: every pattern in the data traces back to an explicit,
documented rule, which is what makes the dataset usable as a learning/practice tool in the
first place. This is **not** a claim to ML-based synthetic-data-engineering expertise.

---

## 🧩 How this fits the larger portfolio

This dataset is the foundation for six downstream analytics projects. None are built yet —
this repo is the first piece.

| Project | Status |
|---|---|
| Demand Forecasting | 🔜 Planned |
| Inventory Optimization | 🔜 Planned |
| Procurement & Supplier Risk | 🔜 Planned |
| Logistics & Delivery Performance | 🔜 Planned |
| Retail Sales & Pricing | 🔜 Planned |
| Customer Analytics (RFM/Churn) | 🔜 Planned |

---

## ⚙️ Tech stack & reproducibility

- **Python 3**, `pandas`, `numpy` — no other dependencies for generation.
- Fully **deterministic / reproducible**: every generation script uses a fixed
  `np.random.default_rng(seed)`. Seeds used, in generation order:

  | Script | Seed |
  |---|---|
  | `generate_phase1_2.py` (dimensions + story logic) | 42 |
  | `generate_phase3a.py` (purchase_orders) | 123 |
  | `generate_phase3b.py` (inventory_snapshots) | 456 |
  | `generate_phase3c.py` (shipments) | 789 |
  | `generate_phase3d.py` (promotions) | 101112 |
  | `generate_phase3e.py` (sales_transactions) | 131415 |
  | `generate_phase4a.py` (messiness: dimensions) | 999 |
  | `generate_phase4b.py` (messiness: transactional) | 2024 |
  | `generate_phase4c.py` (messiness: sales_transactions) | 4040 |

  Running the scripts in order reproduces the exact same dataset every time — verified by
  running the full pipeline from a clean checkout and confirming byte-for-byte identical
  CSV output against the committed `data/` files.

- Run: `pip install pandas numpy && python generate/generate_phase1_2.py && python generate/generate_phase3a.py && ...` (see `dataset_generation_script/` for the full ordered list).

---

## 📁 File structure

```
bcpl-synthetic-dataset/
├── README.md
├── generate/
│   ├── generate_phase1_2.py       # dimension tables + business-logic curves
│   ├── generate_phase3a.py        # purchase_orders
│   ├── generate_phase3b.py        # inventory_snapshots
│   ├── generate_phase3c.py        # shipments
│   ├── generate_phase3d.py        # promotions
│   ├── generate_phase3e.py        # sales_transactions
│   └── generate_phase4a/b/c.py    # messiness injection
├── data/                          # final CSV output (~28 MB total, well under GitHub's
│                                   # 50MB soft-limit per file — no Git LFS needed)
│   ├── stores.csv, warehouses.csv, suppliers.csv, products.csv, customers.csv,
│   │   carriers.csv, purchase_orders.csv, inventory_snapshots.csv, shipments.csv,
│   │   promotions.csv, sales_transactions.csv (largest, ~20MB, ~290,700 rows)
├── 01_SCHEMA_DESIGN.md
├── 02_BUSINESS_LOGIC_DESIGN.md
├── 03_DATA_QUALITY_ISSUES_LOG.md
├── 04_ENGINEERING_PROCESS.md
└── 05_DATA_DICTIONARY.md
```
