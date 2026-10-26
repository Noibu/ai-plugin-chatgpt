# Segment Analysis — Query Workflow

---

## Step 1 — Broad overview (fire all three in one turn)

| Query | Group by | Measures | Limit | Order |
|---|---|---|---|---|
| Device breakdown | Device type | Sessions, CVR, rev/session | — | CVR ↓ |
| Country breakdown | Country | Sessions, CVR, rev/session | 30 | Sessions ↓ |
| Channel breakdown | UTM source + UTM medium | Sessions, CVR, rev/session | 30 | Sessions ↓ |

> **Device:** More completed purchases than payment page views is expected on mobile — Apple Pay / Shop Pay bypass the payment step. Flag as normal, not a data error.

> **Country:** Very high rev/session for a single country likely means local currency, not USD — flag rather than present at face value.

> **Channel:** A large `(none)/(none)` share is unattributed traffic; it does not prove tracking is broken. Use page-referrer attribution recovery when relevant. Zero-CVR rows for awareness campaigns are expected — confirm campaign objective before flagging as a problem.

---

## Step 1.5 — Traffic-quality check

High-volume, zero-conversion traffic can reflect awareness intent, unsupported shipping markets, sparse events, automation, or genuine friction. Country and conversion alone do not establish bots. Inspect time patterns and available behavioral evidence; separate confirmed non-addressable/automated traffic from unverified hypotheses. Exclude a cohort from an opportunity benchmark only with an explicit supported reason, and preserve both inclusive and qualified baselines when useful.

## Step 2 — Compute benchmark and find signals

Compute **site-wide CVR** from a direct whole-domain aggregate of distinct purchasing sessions ÷ distinct sessions, not by summing overlapping, missing or capped device/country/channel rows. Compare grouped results with this control and disclose unverified differences rather than force them to match. Use this baseline only where the rules below permit; channel and device comparisons need their appropriate peers/history.

**Benchmarking rules — apply before selecting any signal:**
- **Device:** Do not flag a DEVICE GAP just because mobile CVR ≠ desktop CVR — some gap is structurally expected. Only flag if the mobile/desktop CVR ratio has worsened between two equal halves of the requested window, labeling exact dates (two 15-day periods in a 30-day window). If both devices declined equally the ratio holds and there is no signal. Only raise a DEVICE GAP card if the ratio worsened by ~10%+ (e.g. mobile/desktop CVR went from 0.80 to 0.72).
- **Channel benchmarks:** Use the most specific baseline available. Preferred: peer group (paid vs paid, email vs email, social vs social). Do not use site average to benchmark individual channels — each channel type has a structurally different CVR by design (email converts high, paid social converts low) so site average comparisons are misleading in both directions. Use site average only for country comparisons. Flag a channel based on underperformance relative to its peer group, or a CVR that worsened notably between the compared periods.

Identify up to 3 signals to follow up on — these become the priority cards.

| Signal | Suggested follow-up |
|---|---|
| High-traffic country well below site CVR | Landing page breakdown for that country |
| Country with near-zero CVR | Landing page breakdown, or check for a broken campaign sending traffic there |
| Channel converting notably below its peer group, or CVR worsened between the compared periods | Campaign breakdown to find which campaigns drag the channel down |
| One channel converting notably better than comparable channels | Deeper breakdown by campaign or source to find scaling opportunities |
| Mobile/desktop CVR ratio worsened by ~10%+ between the compared periods | Week-over-week breakdown by device to confirm the trend |
| Rev/session and CVR moving in opposite directions | Flag as likely a currency difference — may not need a follow-up query |

Before running follow-ups, write a short plain-language transition referencing actual numbers and segment names. Example: "Canada's CVR is 0.3% vs your 2.1% site average, so I'm going to look at which landing pages that traffic is hitting." Then auto-run follow-ups (preferred for broad prompts) or ask first if they're a significant departure from what was asked.

---

## Step 3 — Deeper follow-up queries

Run only the follow-ups the signals call for. This is the first point where minimum session count thresholds apply — the broad overview runs without them so no segments are filtered out prematurely. Calibrate thresholds to store volume:
- >500K sessions/month → ~0.1–0.2% of total
- 50K–500K → ~0.3–0.5%
- <50K → keep very low or skip

**Campaign breakdown** — when a channel's aggregate CVR hides per-campaign variation. Group by UTM campaign + UTM medium (limit 25). Measure: sessions, CVR, rev/session. Order by sessions ↓.

**Landing page breakdown** — when a country or campaign shows entry-point friction. Group by landing URL (limit 25). Filter to the relevant country or campaign. Order by sessions ↓.

**Funnel stage breakdown** — to find where a segment drops off. Group by funnel depth + one dimension (device, country, or UTM medium — whichever the overview flagged). Order by sessions ↓.
