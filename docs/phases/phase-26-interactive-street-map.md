# Phase 26 — Interactive street map

## Objective
Upgrade the operations route preview from a schematic coordinate canvas to a real pan-and-zoom street map without introducing a new frontend dependency.

## Delivered
- Render raster XYZ map tiles with a configurable provider URL and required attribution.
- Add pan, zoom-in, zoom-out, and fit-visible-stops controls.
- Overlay numbered geocoded stops and partner-colored proposed stop sequences.
- Filter mapped routes by partner and inspect selected parcel, delivery window, coordinates, and available routing estimates.
- Show map tile loading failures and count valid geocoded stops; stops without coordinates remain available in the existing assignment register.
- Keep the map honest: dashed connectors indicate stop order, not road geometry; no GPS or live traffic is implied.
- Add frontend environment examples and provider/usage guidance to the README.
- No backend changes, database migrations, or new npm dependencies.

## Validation
No local test or build was run, consistent with the agreed development-first workflow. GitHub Actions CI runs on the pull request.
