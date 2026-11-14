from types import SimpleNamespace

from app import route_planning
from app.schemas import DeliveryRouteStop


class FakeDatabase:
    def __init__(self, parcels):
        self.parcels = parcels

    def get(self, model, parcel_id):
        return self.parcels.get(parcel_id)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def make_stop(parcel_id, tracking_number):
    return DeliveryRouteStop(
        parcel_id=parcel_id,
        tracking_number=tracking_number,
        recipient_name="Synthetic Recipient",
        city="Prayagraj",
        state="Uttar Pradesh",
        pincode="211001",
        delivery_date="2027-01-15",
        slot_start="10:00:00",
        slot_end="12:00:00",
        suggested_partner_id=7,
        suggested_partner_name="Demo Rider",
        route_sequence=parcel_id,
        partner_active_jobs=0,
        zone_key="211",
        recommendation="Test route",
    )


def test_enrich_partner_route_attaches_osrm_geojson_once(monkeypatch):
    monkeypatch.setattr(route_planning.settings, "route_mapping_enabled", True)
    parcels = {1: SimpleNamespace(id=1), 2: SimpleNamespace(id=2)}
    monkeypatch.setattr(
        route_planning,
        "_geocode_parcel",
        lambda db, parcel: {1: (25.4358, 81.8463), 2: (25.4500, 81.8500)}[parcel.id],
    )
    payload = {
        "code": "Ok",
        "trips": [{
            "legs": [
                {"distance": 1200.4, "duration": 300.2},
                {"distance": 900.2, "duration": 240.4},
            ],
            "geometry": {
                "type": "LineString",
                "coordinates": [[81.8500, 25.4500], [81.8480, 25.4440], [81.8463, 25.4358]],
            },
        }],
        "waypoints": [{"waypoint_index": 1}, {"waypoint_index": 0}],
    }
    requests = []

    def fake_get(url, params, timeout):
        requests.append((url, params, timeout))
        return FakeResponse(payload)

    monkeypatch.setattr(route_planning.httpx, "get", fake_get)
    stops = [make_stop(1, "TD-001"), make_stop(2, "TD-002")]

    result = route_planning.enrich_partner_route(FakeDatabase(parcels), stops, 7)

    assert [stop.parcel_id for stop in result] == [2, 1]
    assert requests[0][1]["overview"] == "full"
    assert requests[0][1]["geometries"] == "geojson"
    assert result[0].route_geometry == [
        [81.8500, 25.4500],
        [81.8480, 25.4440],
        [81.8463, 25.4358],
    ]
    assert result[1].route_geometry is None
    assert result[0].leg_distance_m == 1200
    assert result[0].leg_duration_seconds == 300


def test_enrich_partner_route_ignores_invalid_geojson_geometry(monkeypatch):
    monkeypatch.setattr(route_planning.settings, "route_mapping_enabled", True)
    parcels = {1: SimpleNamespace(id=1), 2: SimpleNamespace(id=2)}
    monkeypatch.setattr(
        route_planning,
        "_geocode_parcel",
        lambda db, parcel: {1: (25.4358, 81.8463), 2: (25.4500, 81.8500)}[parcel.id],
    )
    payload = {
        "code": "Ok",
        "trips": [{
            "legs": [],
            "geometry": {"type": "LineString", "coordinates": [[999, 25.45], [81.85, 25.45]]},
        }],
        "waypoints": [{"waypoint_index": 0}, {"waypoint_index": 1}],
    }
    monkeypatch.setattr(route_planning.httpx, "get", lambda *args, **kwargs: FakeResponse(payload))
    result = route_planning.enrich_partner_route(
        FakeDatabase(parcels), [make_stop(1, "TD-001"), make_stop(2, "TD-002")], 7
    )

    assert all(stop.route_geometry is None for stop in result)
    assert [stop.route_sequence for stop in result] == [1, 2]
