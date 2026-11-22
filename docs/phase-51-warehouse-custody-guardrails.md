# Warehouse custody-aware storage controls

The warehouse inventory response now includes the latest custody event type and a server-computed `can_update_location` flag. The flag is true only when the latest custody event is `received` or `returned`, matching the existing write-endpoint rule.

The warehouse UI hides storage editing for parcels outside operations custody and explains why. The PATCH endpoint remains protected and continues to return HTTP 409 if a stale client attempts an invalid update; this is intentional server-side enforcement, not an error to bypass.

The inventory endpoint fetches latest custody events in one additional grouped query for the visible parcel set, avoiding per-parcel queries.
