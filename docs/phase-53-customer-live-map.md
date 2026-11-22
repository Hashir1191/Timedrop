# Phase 53 — Customer live map and partner location controls

## Customer experience

- A parcel card shows a live delivery map only while the assignment is `out_for_delivery`.
- The map is centred on the latest location accepted by TimeDrop and includes an OpenStreetMap marker.
- The customer can manually refresh; the screen also polls every 20 seconds while active.
- Live positions are labelled separately from stale positions. The recorded time and reported GPS accuracy are shown when available.
- Before the partner shares their first position, the customer sees a waiting state rather than a fabricated map marker.
- The published ETA window remains visible when available.
- A clear disclaimer explains that GPS can be delayed by device permissions and network coverage.

## Partner experience

- A partner must explicitly tap **Share my location** for each active out-for-delivery assignment.
- The browser asks for device location permission; TimeDrop does not silently enable tracking.
- While enabled and while this assignment remains on the screen, the browser watches GPS and sends an update no more frequently than every 15 seconds.
- The partner can stop sharing at any time.
- The control exists only on an out-for-delivery assignment; leaving the page or changing the assignment status unmounts the control and stops the browser location watch.
- Permission denial, unavailable GPS and timeout errors are described in the partner workspace.

## Technical decisions

- Uses the Phase 52 owner-scoped API; no partner coordinates are placed in customer page markup or shared through public tracking links.
- Uses OpenStreetMap's embeddable map view and attribution; no proprietary API key is required for this initial map experience.
- This is foreground browser GPS, not a native background tracking service. Browser background tabs, mobile OS battery policies and permission settings can pause updates.
- The customer sees the last server-accepted position. The API's 120-second freshness threshold determines whether it is labelled live.
- The map does not draw a route line or claim traffic-aware ETA. Those require a destination geocode and a routing provider decision, plus cost/coverage validation for Indian service areas.
- Production requires HTTPS for browser geolocation, explicit location consent copy, a retention/deletion policy and review of OpenStreetMap tile/embed usage terms.

## Manual acceptance checklist

1. Sign in as a delivery partner and open an assignment.
2. Move it to **Out for delivery**.
3. Tap **Share my location** and grant browser location permission.
4. Confirm the partner workspace reports that the latest position is shared.
5. Sign in as the parcel owner in another browser and open **My parcels**.
6. Confirm the map marker appears and refreshes after the next partner update.
7. Stop sharing on the partner screen and confirm the customer eventually sees a stale position rather than a falsely live marker.
8. Confirm another customer cannot access the parcel location (covered by Phase 52 API tests).
9. Mark the assignment delivered and confirm the live map is no longer displayed.
