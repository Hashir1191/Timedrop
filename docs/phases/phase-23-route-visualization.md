# Phase 23 — Interactive route visualization

Operations route planning now includes a coordinate-based geographic stop preview. Users can filter by suggested partner, inspect stop details and visit order, and open the existing external route map when the backend provides a supported link. The visualization uses geocoded coordinates from the existing route-plan API and does not imply live GPS or show fabricated roads. When geocodes are absent, the planner displays an explicit fallback and preserves the full stop list and assignment controls.

The backend remains authoritative for assignment eligibility, capacity, availability, and routing recommendations. This is a presentation-only change with no new runtime dependencies or migrations.

Local end-to-end testing is deferred to the planned testing phase. CI build results should be checked before merge.
