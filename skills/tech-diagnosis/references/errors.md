# Error investigation

Classify frames against the matching platform reference, using only actual paths and inspected ownership. Session-specific user-provided ownership overrides can refine the classification; no home-directory config is required.

Merchant code is fixable once source is connected ([source access](../../querying-noibu-data/references/source-access.md)); platform code needs a platform/vendor path; telemetry-only errors are not automatically user-facing failures. Reactive vendor issues remain useful findings even when the merchant cannot edit that code. Missing stack frames limit confidence; do not discard an explicitly requested issue without explaining that limitation.

Prefer root-cause fixes. A generic try/catch or null guard must not be advertised as the root-cause fix when it merely suppresses the symptom. Consent-related short recordings may indicate an observability gap, not a prevented purchase.

Fetch the supported detail/diagnosis/trend tools for the exact issue. Human issue number and UUID differ; consult console parsing and the live schema. Show occurrences, distinct sessions, pages, browser/OS concentration, last seen, and measured trend where available. A browser/source check may verify file/line or element identity; without it, say the cause is a hypothesis.

For requested technical details, include message, signature, the relevant three to five labeled stack frames, inspected file/line, and redacted relevant HTTP fields. Do not publish raw credentials, cookies, customer fields, or full request payloads in a report or external ticket.

Projected revenue follows the shared guide. Correlation is not causal impact; "observed in N sessions" is different from "blocked N shoppers."
