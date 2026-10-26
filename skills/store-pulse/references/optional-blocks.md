# Optional Store Pulse slices

Only query blocks selected by the user.

- Products: session search array-joined on viewed product titles; sessions and funnel progression, top five by sessions. Purchase-session count is the product volume measure; whole-cart values are not product revenue.
- Channels: session search grouped by UTM_SOURCE and UTM_MEDIUM; sessions, conversion rate, revenue/session, top five by sessions. Show unattributed rows neutrally.
- Paid attribution: first use populated UTM tags. If absent, page visits filtered on REFERRING_URL parameters such as gclid/gad_, using UNIQ(SESSION_ID). Explain this is a lower bound and do not double-count overlapping recovered parameters. Do not report ROAS without actual ad-spend data.
- Core KPIs and the purchase funnel always remain in the report. Optional rows do not alter their denominator or replace a whole-domain baseline.
