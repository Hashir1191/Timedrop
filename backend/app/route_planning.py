import hashlib
import time
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Parcel, RouteGeocodeCache


_last_geocode_request = 0.0


def _address_key(parcel: Parcel) -> tuple[str, str]:
    address = ", ".join(
        part.strip()
        for part in (parcel.address_line, parcel.city, parcel.state, parcel.pincode, "India")
        if part and part.strip()
    )
    digest = hashlib.sha256(address.casefold().encode("utf-8")).hexdigest()
    return digest, address


def _geocode_parcel(db: Session, parcel: Parcel) -> tuple[float, float] | None:
    global _last_geocode_request
    key, address = _address_key(parcel)
    cached = db.scalar(select(RouteGeocodeCache).where(RouteGeocodeCache.address_hash == key))
    if cached:
        return cached.latitude, cached.longitude

    # Nominatim's public service requires a descriptive User-Agent and a maximum
    # request rate of one request per second. Deployments should use a hosted
    # provider or self-hosted instance for higher volume.
    wait = 1.1 - (time.monotonic() - _last_geocode_request)
    if wait > 0:
        time.sleep(wait)
    try:
        response = httpx.get(
            settings.route_geocoder_url,
            params={"q": address, "format": "jsonv2", "limit": 1, "countrycodes": "in"},
            headers={"User-Agent": settings.route_provider_user_agent},
            timeout=settings.route_geocode_timeout_seconds,
        )
        response.raise_for_status()
        results = response.json()
        _last_geocode_request = time.monotonic()
        if not results:
            return None
        latitude, longitude = float(results[0]["lat"]), float(results[0]["lon"])
        db.add(RouteGeocodeCache(
            address_hash=key, latitude=latitude, longitude=longitude, provider="nominatim"
        ))
        db.flush()
        return latitude, longitude
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None


def enrich_partner_route(db: Session, stops: list, partner_id: int) -> list:
    """Geocode and road-optimize one partner's proposed stops; gracefully fall back."""
    if not settings.route_mapping_enabled or len(stops) < 2:
        if settings.route_mapping_enabled and stops:
            coordinates = _geocode_parcel(db, db.get(Parcel, stops[0].parcel_id))
            if coordinates:
                stops[0].latitude, stops[0].longitude = coordinates
        return stops

    parcel_coordinates = {}
    for stop in stops:
        parcel = db.get(Parcel, stop.parcel_id)
        if parcel is not None:
            parcel_coordinates[stop.parcel_id] = _geocode_parcel(db, parcel)

    located = [stop for stop in stops if parcel_coordinates.get(stop.parcel_id)]
    for stop in located:
        stop.latitude, stop.longitude = parcel_coordinates[stop.parcel_id]

    if len(located) < 2:
        return stops

    coordinate_path = ";".join(
        f"{parcel_coordinates[stop.parcel_id][1]},{parcel_coordinates[stop.parcel_id][0]}"
        for stop in located
    )
    try:
        response = httpx.get(
            f"{settings.route_router_url.rstrip('/')}/trip/v1/driving/{coordinate_path}",
            params={"roundtrip": "false", "source": "first", "destination": "last", "overview": "false", "steps": "false"},
            timeout=settings.route_geocode_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "Ok" or not payload.get("trips"):
            return stops
        trip = payload["trips"][0]
        waypoints = payload.get("waypoints", [])
        ordered = sorted(
            zip(waypoints, located),
            key=lambda item: item[0].get("waypoint_index", 10**9),
        )
        ordered_stops = [stop for _, stop in ordered]
        ordered_coords = [
            (parcel_coordinates[stop.parcel_id][0], parcel_coordinates[stop.parcel_id][1])
            for stop in ordered_stops
        ]
        map_route = ";".join(f"{longitude},{latitude}" for latitude, longitude in ordered_coords)
        map_url = (
            "https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route="
            + quote(";".join(f"{latitude},{longitude}" for latitude, longitude in ordered_coords), safe=";,")
        )
        legs = trip.get("legs", [])
        for index, stop in enumerate(ordered_stops):
            stop.route_sequence = index + 1
            stop.map_url = map_url
            if index < len(legs):
                stop.leg_distance_m = round(float(legs[index].get("distance", 0)))
                stop.leg_duration_seconds = round(float(legs[index].get("duration", 0)))
        unlocated_stops = [stop for stop in stops if stop not in located]
        return ordered_stops + unlocated_stops
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return stops
