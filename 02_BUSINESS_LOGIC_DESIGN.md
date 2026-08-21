# 🧠 Business Logic Design

Every non-random pattern in this dataset comes from an explicit, parameterized rule. This
document explains each rule and, more importantly, *why* it's shaped the way it is.

## ⚠️ Supplier risk curves

Six of the 45 suppliers quietly degrade over time — but not uniformly. An early version had
all six degrade in lock-step on both lead-time and reject-rate, which made the "diagnose
which metric is actually the problem" exercise trivial (both signals always moved together).
Fixed by splitting failure modes explicitly:

| Type | Count | What degrades |
|---|---|---|
| `lead_time_only` | 2 | Delivery delay grows; quality stays normal |
| `reject_rate_only` | 2 | Quality/reject rate grows; delivery stays on time |
| `both_mild` | 1 | Both degrade, moderately |
| `both_severe` | 1 | Both degrade sharply — a real crisis-level supplier |

Degradation starts July 2024 (ramping over ~400 days) for all risk suppliers; the severe
case gets an additional acceleration from January 2025. Non-risk suppliers aren't perfectly
reliable either — they get occasional random outlier days (3-5% of days) so "risk vs
non-risk" isn't trivially separable by a single bad day.

**Good-streak noise, and why it's time-position-aware**: risk suppliers occasionally have a
good 7-14 day stretch (simulating a good batch/good week), but these streaks are
deliberately *not* allowed once a supplier is deep into degradation — a good streak
appearing during the severe supplier's crisis period would have undermined the "this is a
real crisis" narrative. Streak placement is restricted to days where the degradation ramp is
still under 60% (and, for the severe supplier, under 30% of its extra crisis ramp).

## 🚚 Carrier delay probability

Base reliability differs per carrier (70-93%), then two additive effects layer on top:
a monsoon bump (June-September, +12 percentage points, applied to all carriers so the
*relative* gap between good and bad carriers stays visible) and a high-volume-day bump
(near Eid/year-end, +10 points, simulating capacity strain). Combined with a route bonus
(+15 points for cross-region/overflow shipments), the whole thing is capped at 90% — no
shipment is ever "guaranteed late," and a floor of 4% means no carrier is ever
"guaranteed on-time" either.

## 📈 Product demand curves

Each product gets a trend label — stable (50%), growing (30%), or declining (20%) — which
combines with daily noise (±10-20%) and the shared seasonality curve (Eid, Boishakh,
year-end, weekly patterns). **Important nuance**: the trend must drive how *often* a product
gets selected into a transaction, not just the quantity per transaction — an early version
only fed the trend into quantity, which diluted the signal almost to invisibility (see
Engineering Process doc, Case Study 1).

## 🏷️ Promotions

Discount % (10-45%) and duration (3-14 days) vary per campaign — not fixed — so promotion
effects aren't trivially predictable. Products sourced from risk suppliers get promoted at a
reduced rate (60% of normal frequency) and promotions are mostly avoided during known
stockout windows for that product, with a small (~8%) deliberate exception rate so
"promotion ran straight into a stockout" occasionally happens — a realistic edge case, not a
generation error.

## 👋 Customer churn

18% of eligible customers (joined before mid-2024) churn, split 58% gradual / 42% abrupt —
not an arbitrary 50/50. The reasoning: in retail, a slow fade from dissatisfaction is more
common than a single abrupt drop-off (bad experience, moved away, switched to a
competitor), so the split reflects that.

## 🏙️ Store-type and regional effects

Flagship stores get the highest daily transaction volume and largest basket size; Express
stores the lowest volume and smallest baskets; Standard in between. Dhaka region gets the
highest overall sales volume multiplier, reflecting population/store density.

**Honest limitation**: the original intent for Express stores was "smaller but more
frequent" — only the "smaller/fewer" half was implemented (via multipliers on daily
transaction count and basket size). A distinct per-customer visit-frequency model was
deliberately not built — a scope simplification, not an oversight left undocumented.
