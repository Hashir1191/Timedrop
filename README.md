
### Interactive operations street map

The operations route planner renders geocoded delivery stops over a pan-and-zoom street map. The default low-volume tile source is OpenStreetMap's standard raster tile service. Configure an alternative provider using frontend build-time variables:

```dotenv
VITE_ROUTE_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_ROUTE_TILE_ATTRIBUTION=© OpenStreetMap contributors
```

The tile URL must be a raster XYZ template containing `{z}`, `{x}`, and `{y}`. The attribution string must match the selected provider's requirements. These are public frontend values, not secrets. The public OpenStreetMap tile service is intended for modest interactive use and is not a production tile CDN; use a suitable hosted provider or self-hosted tile infrastructure for production-scale traffic. The map uses browser requests directly to the tile provider, so review its privacy, availability, caching, and usage policies before deployment.

The map displays the actual basemap tiles and geocoded stop markers. Dashed connectors represent the proposed visit sequence only; they are not road geometry. Per-leg distance and duration remain estimates supplied by the backend routing service. This phase does not add GPS tracking, live traffic, or turn-by-turn navigation. Stops without valid coordinates remain in the assignment list and are excluded from the map rather than being assigned fabricated positions.
\n