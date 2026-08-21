# 🔧 Engineering Process

This is the part of the project that goes beyond "write a script that generates rows" —
judging whether the output actually makes sense, catching it when it doesn't, and verifying
fixes didn't break something else.

---

## 🎛️ 1. Calibration

Generation parameters were tuned against target statistics, not accepted on the first run.

**Example: inventory stockout rate.** The first pass of the inventory simulation produced a
28.6% overall stockout rate — unrealistically high (real-world retail is typically 5-10%) —
and a weak risk-vs-non-risk gap (33% vs 24%, both too high to separate from noise). Root
cause: the reorder-point buffer was too thin relative to how often purchase orders were
placed. Fixed by increasing the safety-stock buffer (from ~12 days of demand to ~18 days)
and tightening the purchase-order cycle (from every 10-18 days to every 7-13 days). Result:
15.6% overall stockout rate, with a clearer, still-realistic (not artificially clean)
17.6% (risk-linked) vs 13.4% (non-risk) gap — a detectable, non-trivial ~31% relative
difference, not an overwhelming, obviously-planted one.

**Example: shipment volume.** Target was ~9,000 shipments (locked during schema planning);
the first generation run produced only 3,276 — a 64% shortfall. Rather than accept "close
enough," the root cause was traced (see Case Study 2 below) and the frequency formula
recalibrated, landing at 8,968 — within 0.4% of target.

---

## 🐛 2. Bug-catching case studies

### 📉 Case Study 1 — Product trend signal was silently getting lost

**Symptom**: after generating `sales_transactions`, aggregate monthly quantity for
"declining" products showed +13.3% growth instead of declining, and "stable" products
showed +45.8% growth instead of flat.

**Root cause**: a product's growing/declining/stable trend was only being applied to
*quantity per transaction*, not to *how often the product got selected into a transaction
at all*. Since transaction frequency (the dominant driver of total volume) used a static,
time-invariant category-based weight, the individual product trend was almost entirely
diluted by the store-level seasonal/growth pattern shared by all products.

**Fix**: product selection probability was made dynamic per day —
`weight(product, day) ∝ category_weight × demand_curve(product, day)` — so a growing
product's transaction frequency actually rises over time, not just its basket quantity.

**Verification**: after the fix, growing products showed +103.7% growth vs first-3-months
baseline, declining showed -11.3%, and the residual "stable +39.8%" was checked against
pure seasonality (comparing average daily seasonal factor across the same two windows)
and found to be ~82% explained by the shared seasonal/trend curve alone (32.5 of the 39.8
points) — the rest within the ±10% noise band intentionally built into "stable" products.

### 📦 Case Study 2 — Shipment volume shortfall

**Symptom**: 3,276 shipments generated against a 9,000 target — a 64% shortfall.

**Root cause investigation**: computed the *expected* shipment count directly from the
generation formula (no randomness) and compared to actual output — they matched almost
exactly (3,285 expected vs 3,276 actual). This ruled out a code bug (no rows were being
silently dropped or filtered) and isolated the problem to a single miscalibrated constant:
the base gap-between-shipments parameter (4.5 days) was simply too conservative relative to
the volume target set during schema planning.

**Fix**: recalibrated the base constant from 4.5 to 1.6 days.

**Verification**: re-ran and got 8,968 shipments (0.4% off target), with the carrier
delay-rate differentiation (CR04 worst at ~35%, CR05 best at ~12%) still intact after the
change.

### 📅 Case Study 3 — Date-parsing ambiguity (dayfirst vs MM/DD)

**Symptom**: comparing the "before messiness" and "after messiness" sales trend numbers
showed the growing-product trend shift from +103.7% to +86.4% — a ~17 percentage point
swing, larger than the acceptable-noise threshold.

**Root cause**: the messiness-injection step deliberately renders dates in three mixed
string formats, including `DD/MM/YYYY`. When re-parsed with `pd.to_datetime(...,
format="mixed")` (no `dayfirst` flag), pandas defaults to interpreting ambiguous dates
(day ≤ 12) as `MM/DD/YYYY` — silently misreading e.g. `02/01/2024` (2 January) as 1
February. Dates with day > 12 parsed correctly regardless (unambiguous).

**This was not a data-generation bug** — it's a realistic reflection of an ambiguity any
analyst working with mixed-locale date data would have to resolve. It was, however, a bug
in the *validation script* used to check the dataset.

**Fix**: re-ran the before/after comparison with `dayfirst=True`. Shift dropped to 2.2-9.3
percentage points across the three trend labels — the growing/stable/declining *ordering*
was intact throughout, only the exact magnitude was ever affected, and only in the naive
(non-dayfirst) parsing.

**Takeaway documented in the data dictionary**: anyone using this dataset must parse
`transaction_date` (and other mixed-format date columns) with `dayfirst=True`.

---

## ✅ 3. Post-messiness validation

Before declaring the messiness-injection phase (Phase 4) complete, every key business
signal calibrated during Phases 2-3 was re-measured from the final messy CSVs and compared
against the pre-messiness "clean" values, to confirm messiness injection hadn't distorted
the underlying patterns it was layered on top of.

| Signal | Before | After | Shift | Verdict |
|---|---|---|---|---|
| PO status distribution | 58.91/35.11/4.69/1.29% | 58.94/35.08/4.69/1.29% | 0.03pp | Negligible |
| Stockout gap (risk vs non-risk) | 31.4% relative | 31.4% relative | 0pp | Unchanged |
| Carrier delay differential (CR04 vs CR05) | 35.7% vs 11.8% | 35.7% vs 11.8% | ≤0.1pp | Negligible |
| Growing/declining/stable trend ordering | 103.7 / -11.3 / 39.8% | 94.4 / -13.5 / 40.8% (dayfirst-corrected) | 2.2-9.3pp | Ordering intact |
| Column-level messiness density (data-loss category) | — | max 11% (payment_method) | — | All under the 20% ceiling |
| Category-string messiness — bias check | — | z-scores all within ±2 | — | Sampling noise, not systematic bias |
| Missing/duplicate rate vs risk-linked products | — | 5.02% vs 5.15% (missing customer_id); 13.5% vs 13.8% (duplicate share) | ~0pp | No correlation/bias found |

**Why the bias checks matter**: "aggressive, overlapping" messiness injection carries a
real risk that issues land disproportionately on certain rows (e.g., risk-linked products
getting more missing values, which would fabricate a spurious correlation on top of the
real, intentional one). Both checks above — missing-value rate and duplicate-row rate,
split by risk-linked status — came back statistically indistinguishable, confirming the
injection mechanism is genuinely uniform-random and doesn't manufacture bias.

**Category-string bias check methodology**: category-level case/whitespace-messiness rates
ranged from 12% to 37% at first glance, which looked suspicious. A z-score test
(`(observed - injection_probability) / sqrt(p(1-p)/n)` per category) showed every category
within ±2 standard deviations of the expected 22% injection rate — consistent with small
per-category sample sizes (14-44 products/category) producing binomial sampling noise, not
a systematic injection bias toward specific categories.
