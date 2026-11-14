# Phase 27 — Road-route geometry

## Goal

Replace the Phase 26 approximate straight-line connectors with road-following paths returned by the configured OSRM routing service, while preserving the existing route-plan API behavior and graceful fallback.

## Implementation

- Request full GeoJSON geometry from the OSRM Trip service using `overview=full` and `geometries=geojson`.
- Preserve OSRM's GeoJSON coordinate order: `[longitude, latitude]`.
- Validate every returned point for numeric, finite values and geographic bounds before exposing it.
- Include the shared route path once per partner group, on its first ordered stop, avoiding repeated large coordinate arrays on every stop.
- Render solid, road-aligned SVG paths on the existing interactive street map when geometry is available.
- Keep dashed stop-order connectors as a clearly labelled fallback when OSRM geometry is unavailable or invalid.
- Preserve stop markers, partner filtering, pan/zoom, fit-to-stops, delivery-window details, per-leg estimates, and the external OpenStreetMap route link.

## API compatibility

The route-plan endpoint remains `GET /api/v1/delivery/route-plan?delivery_date=YYYY-MM-DD`. The additive optional `route_geometry` field is null or absent for older/heuristic responses and is populated only on the first stop in a partner route when valid geometry is returned. No database migration or new frontend dependency is required.

## Accuracy and operational limits

The path is an OSRM road-network route estimate, not a live GPS trace, live traffic-aware ETA, or turn-by-turn navigation instruction. Routing remains dependent on the configured OSRM provider and its coverage/availability. If routing fails, the existing deterministic partner/stop proposal remains available.

## Verification

Automated backend tests cover GeoJSON retrieval and ordering, one-time route-path attachment, per-leg values, and invalid geometry rejection. GitHub Actions is used for the frontend production build and backend test suite. No local tests or build are run as part of this development workflow.
