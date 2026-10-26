# candidates.json

Schema identifier: `noibu.ab-candidates/2`. This ChatGPT handoff uses an explicit version because the old hosted-page pipeline is not included. Do not claim it is byte-compatible with version 1 consumers.

Root: schema, generatedAt (ISO), domain (name), domainId (UUID), goal, window {start,end}, tests, caveats. Each test: rank, title, hypothesis, what, evidence [{claim,numbers,source}], validation {status: verified|partial|unvalidated, notes}, createInput. Optional selectors and preview paths must come from actual inspected/exported evidence.

createInput is the exact reviewed payload for noibu_create_ab_test excluding domainId and call telemetry. Allowed fields: title, hypothesis, successMetric, secondaryMetrics, deviceTypes, utmConditions, variations. No status, arbitrary JS, credentials, tool names, or hidden lifecycle actions. Undefined country/location configuration is omitted.

Keep title and hypothesis consistent with createInput. The control is the observed current experience. Don't insert a guessed selector when no browser inspection occurred. Numeric evidence must be finite; evidence numbers must match the report. Never treat a proposed variant screenshot as implemented behavior.

Run `scripts/validate_candidates.py <candidates.json>` before handing off a file. Validation does not create a test. The file contains no live "Create" button and cannot call MCP directly; selected drafts are created through the user's ChatGPT conversation and authorization.
