# Phase 46 — UI and customer experience

## Scope
- Improve customer dashboard recovery when parcel loading fails.
- Make dashboard loading and assignment refresh states more explicit to assistive technology.
- Prevent duplicate partner refresh requests while a request is already in progress.
- Add a responsive finishing layer for customer and partner workspaces: readable controls, touch targets, overflow handling, and reduced-motion support.

## Validation
Run the frontend production build with `npm run build`. Existing API contracts and delivery workflows are unchanged.

## Manual acceptance
- Customer dashboard can retry a failed parcel request without reloading the page.
- Partner refresh is disabled while assignments are loading.
- Customer and partner workspaces remain usable on narrow screens and with reduced-motion preferences.
