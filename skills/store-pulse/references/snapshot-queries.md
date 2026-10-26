# Snapshot queries

Read the session reference for the exact aggregate envelope. Use the same timestamp, currency scope, and domain for both periods.

For each period:
- COUNT(SESSION_ID), predefined BOUNCE_RATE, predefined CONVERSION_RATE.
- SUM(CHECKOUT_COMPLETE_TOTAL_VALUE) filtered to CHECKOUT_COMPLETED = true.
- SUM(CHECKOUT_COMPLETE_COUNT) filtered to completed sessions when populated. If unavailable, use distinct completed sessions as a clearly labeled order-count proxy; do not silently equate sessions with orders.
- Order by session count DESCENDING and limit 1 when ungrouped.

Separate revenue by CART_CURRENCY when multi-currency is present. An AOV on all sessions' completed-value AVG can be diluted by non-purchasers; derive AOV from completed revenue and actual completed-order count instead. Median completed-order value must be labeled "median," not AOV.

Funnel: COUNT(SESSION_ID), groupBy CONVERSION_FUNNEL_DEPTH, order by count DESCENDING, limit 10, for each window. Sum exact depth buckets cumulatively. Hold onto raw rows for interpretation of null/0 and express checkout.

Output metric calculations:
- engagement = 1 − bounce rate
- AOV = completed revenue / completed orders
- revenue/session = completed revenue / sessions
- rate delta in pp = 100 × (current rate − prior rate)
- relative percent delta = 100 × (current − prior) / prior; when prior = 0, report undefined or new activity rather than infinity.
