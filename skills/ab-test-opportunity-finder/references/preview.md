# Variation previews in ChatGPT

A preview is a design approximation, not deployed code and not evidence of conversion lift.

Preferred: real before/after captures through supported, authorized browser controls. Use observed elements/copy and identical viewport and scroll position. DOM/CSS mutation requires an actual supported execution interface and any required developer approval. Do not use a read-only evaluator to mutate, inject arbitrary page scripts through a hidden channel, or assume full CDP permission.

Use a temporary preview context, never create an order or send a network write for a visual preview, and reload/reset afterward. Do not transfer the user's cookies into another browser. Save images through the runtime's supported capture/export mechanism only.

If the browser session, supported mutation, capture, or image export is unavailable, finish the recommendations and implementation handoff without a visual preview. Add a short, specific explanation, such as "Visual preview omitted: this session has no browser with approved DOM mutation." Do not block the report or draft creation on previews, and do not require a substitute mockup. Proposed copy/layout can still be described normally in the recommendation. Use verified shipping/promotion facts; no invented free-shipping threshold.

Do not imply a mockup is a screenshot. A captured desktop variant is not a verified mobile layout; state the actual viewport. Variation selectors are supplied only when inspected; an inferred selector must never enter the implementation handoff as a verified selector.
