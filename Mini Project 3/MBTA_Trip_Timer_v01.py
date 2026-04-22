"""
MBTA_Trip_Timer_v01.py — API logic for the "Can I Make It?" MBTA trip planner.

All external API calls live here. No Flask imports — testable standalone.
Run: python MBTA_Trip_Timer_v01.py
"""

import math
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

MAPBOX_TOKEN: str = os.environ.get("MAPBOX_TOKEN", "")
MBTA_API_KEY: str = os.environ.get("MBTA_API_KEY", "")

MAPBOX_BASE = "https://api.mapbox.com"
MBTA_BASE = "https://api-v3.mbta.com"

# route_type 0 = light rail (Green Line, Mattapan Trolley)
# route_type 1 = heavy rail (Red, Orange, Blue Lines)
SUBWAY_ROUTE_TYPES = "0,1"

# If the nearest subway stop is farther than this, there's no good subway option
MAX_WALK_MILES = 1.5

# Official MBTA route colors (#hex) and human-readable display names
ROUTE_META: dict[str, tuple[str, str]] = {
    "Red":      ("#DA291C", "Red Line"),
    "Orange":   ("#ED8B00", "Orange Line"),
    "Blue":     ("#003DA5", "Blue Line"),
    "Green-B":  ("#00843D", "Green Line (B)"),
    "Green-C":  ("#00843D", "Green Line (C)"),
    "Green-D":  ("#00843D", "Green Line (D)"),
    "Green-E":  ("#00843D", "Green Line (E)"),
    "Mattapan": ("#DA291C", "Mattapan Trolley"),
}

# Approximate minutes per stop by route type — used to estimate ride time.
# Heavy rail (Red/Orange/Blue): ~2 min/stop
# Light rail (Green/Mattapan): ~3 min/stop (slower surface segments)
MINS_PER_STOP: dict[int, int] = {0: 3, 1: 2}


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def get_lat_lng(place_name: str) -> tuple[float, float]:
    """
    Convert a place name or address to (latitude, longitude) using Mapbox Geocoding.

    Results are biased toward Boston, MA. Returns the top match only.

    Args:
        place_name: Address or place name, e.g. "Harvard Square, Cambridge"

    Returns:
        (latitude, longitude) as floats

    Raises:
        ValueError: No results found for the given place name
        requests.HTTPError: Non-2xx response from Mapbox
        requests.Timeout: Request timed out
    """
    if not MAPBOX_TOKEN:
        raise EnvironmentError(
            "MAPBOX_TOKEN is not set. Copy .env.example → .env and add your key."
        )

    url = f"{MAPBOX_BASE}/geocoding/v5/mapbox.places/{requests.utils.quote(place_name)}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "proximity": "-71.0589,42.3601",  # bias toward Boston city center
        "country": "us",
        "limit": 1,
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    features = resp.json().get("features", [])
    if not features:
        raise ValueError(f"Location not found: {place_name!r}")

    # Mapbox returns coordinates as [longitude, latitude]
    lng, lat = features[0]["geometry"]["coordinates"]
    return float(lat), float(lng)


# ---------------------------------------------------------------------------
# Walking time (Haversine approximation)
# ---------------------------------------------------------------------------

def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance in miles between two lat/lng points."""
    R = 3958.8  # Earth radius in miles
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def estimate_walk_time(
    from_lat: float, from_lng: float, to_lat: float, to_lng: float
) -> int:
    """
    Estimate walking time in minutes using straight-line (Haversine) distance.

    Assumes 3 mph average walking speed. Will slightly underestimate real walk
    time since it ignores street geometry. Returns a minimum of 1 minute.
    """
    miles = _haversine_miles(from_lat, from_lng, to_lat, to_lng)
    return max(1, round((miles / 3.0) * 60))


# ---------------------------------------------------------------------------
# MBTA: nearest subway stop
# ---------------------------------------------------------------------------

def get_nearest_subway_station(lat: float, lng: float) -> dict | None:
    """
    Find the nearest MBTA subway stop to the given coordinates.

    Filters to subway only (route_type 0 and 1). Returns None if the nearest
    stop is more than MAX_WALK_MILES (1.5 mi) away.

    Args:
        lat: Latitude of the point to search from
        lng: Longitude of the point to search from

    Returns:
        Dict with keys:
            name (str)            — stop display name, e.g. "Park Street"
            stop_id (str)         — MBTA stop ID, e.g. "place-pktrm"
            lat (float)           — stop latitude
            lng (float)           — stop longitude
            wheelchair (bool)     — True if fully wheelchair accessible
            distance_miles (float)— straight-line distance from input coords
            routes (list[dict])   — each entry: {route_id, display_name, color}

        Returns None if no subway stop is within MAX_WALK_MILES.

    Raises:
        requests.HTTPError: Non-2xx from MBTA API
        requests.Timeout: Request timed out
    """
    headers = {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}

    # filter[radius] is in degrees; 0.025° ≈ 1.75 miles — slightly above MAX_WALK_MILES
    # to give the distance check below a margin to work with
    params = {
        "filter[route_type]": SUBWAY_ROUTE_TYPES,
        "filter[latitude]": lat,
        "filter[longitude]": lng,
        "filter[radius]": 0.025,
        "sort": "distance",
        "page[limit]": 1,
    }

    resp = requests.get(f"{MBTA_BASE}/stops", params=params, headers=headers, timeout=10)
    resp.raise_for_status()

    stops = resp.json().get("data", [])
    if not stops:
        return None

    platform_stop = stops[0]
    platform_lat = platform_stop["attributes"]["latitude"]
    platform_lng = platform_stop["attributes"]["longitude"]

    # Distance check uses the platform stop's coords — it's the closest physical point
    distance = _haversine_miles(lat, lng, platform_lat, platform_lng)
    if distance > MAX_WALK_MILES:
        return None

    # Resolve the parent station if one exists.
    # MBTA platform stops (location_type=0, e.g. "70079") have a parent station
    # (location_type=1, e.g. "place-sstat") that is the canonical stop for predictions
    # and route queries. Using the platform ID would only return one direction's trains.
    parent_rel = platform_stop["relationships"].get("parent_station", {}).get("data")
    if parent_rel:
        station_id = parent_rel["id"]
        station_resp = requests.get(
            f"{MBTA_BASE}/stops/{station_id}", headers=headers, timeout=10
        )
        station_resp.raise_for_status()
        attrs = station_resp.json()["data"]["attributes"]
        stop_lat = attrs["latitude"]
        stop_lng = attrs["longitude"]
    else:
        station_id = platform_stop["id"]
        attrs = platform_stop["attributes"]
        stop_lat = platform_lat
        stop_lng = platform_lng

    # Fetch routes serving the parent station
    route_params = {
        "filter[stop]": station_id,
        "filter[type]": SUBWAY_ROUTE_TYPES,
    }
    route_resp = requests.get(
        f"{MBTA_BASE}/routes", params=route_params, headers=headers, timeout=10
    )
    route_resp.raise_for_status()

    routes = []
    for r in route_resp.json().get("data", []):
        rid = r["id"]
        color, display_name = ROUTE_META.get(rid, ("#888888", rid))
        routes.append({"route_id": rid, "display_name": display_name, "color": color})

    return {
        "name": attrs["name"],
        "stop_id": station_id,
        "lat": stop_lat,
        "lng": stop_lng,
        "wheelchair": attrs.get("wheelchair_boarding", 0) == 1,
        "distance_miles": round(distance, 2),
        "routes": routes,
    }


# ---------------------------------------------------------------------------
# MBTA: arrival predictions
# ---------------------------------------------------------------------------

def get_arrival_predictions(
    stop_id: str, direction_id: int | None = None
) -> list[dict]:
    """
    Fetch upcoming subway arrival predictions for a stop.

    Filters to subway routes only. Skips predictions that have already passed.

    Args:
        stop_id: MBTA stop ID (e.g. "place-pktrm")
        direction_id: 0 or 1 to restrict to one direction; None returns both

    Returns:
        List of dicts (sorted by arrival time), each with:
            route_id (str)
            route_name (str)
            direction_id (int)
            arrival_time (datetime | None)   — timezone-aware UTC
            departure_time (datetime | None) — timezone-aware UTC
            minutes_away (int | None)        — minutes until arrival from now

        Returns an empty list when the subway isn't running or no trains are
        predicted — the caller should handle this as "T not running."

    Raises:
        requests.HTTPError: Non-2xx from MBTA API
        requests.Timeout: Request timed out
    """
    headers = {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}

    params: dict = {
        "filter[stop]": stop_id,
        "filter[route_type]": SUBWAY_ROUTE_TYPES,
        "sort": "arrival_time",
        "page[limit]": 10,
        "include": "route",
    }
    if direction_id is not None:
        params["filter[direction_id]"] = direction_id

    resp = requests.get(
        f"{MBTA_BASE}/predictions", params=params, headers=headers, timeout=10
    )
    resp.raise_for_status()
    data = resp.json()

    # Build route_id → display_name from the "included" sideloaded data
    route_lookup: dict[str, str] = {}
    for item in data.get("included", []):
        if item["type"] == "route":
            rid = item["id"]
            _, display = ROUTE_META.get(rid, ("#888888", rid))
            route_lookup[rid] = display

    now = datetime.now(timezone.utc)
    results: list[dict] = []

    for pred in data.get("data", []):
        attrs = pred["attributes"]
        arrival_str = attrs.get("arrival_time")
        departure_str = attrs.get("departure_time")
        route_id = pred["relationships"]["route"]["data"]["id"]

        arrival_dt = datetime.fromisoformat(arrival_str) if arrival_str else None
        departure_dt = datetime.fromisoformat(departure_str) if departure_str else None

        # Use arrival time for timing; fall back to departure (e.g. first stop of a trip)
        reference_dt = arrival_dt or departure_dt
        minutes_away: int | None = None

        if reference_dt:
            delta_min = (reference_dt - now).total_seconds() / 60
            if delta_min < -1:
                continue  # Train already departed — skip
            minutes_away = max(0, round(delta_min))

        results.append({
            "route_id": route_id,
            "route_name": route_lookup.get(route_id, route_id),
            "direction_id": attrs.get("direction_id"),
            "arrival_time": arrival_dt,
            "departure_time": departure_dt,
            "minutes_away": minutes_away,
        })

    return results


# ---------------------------------------------------------------------------
# Ride time estimation
# ---------------------------------------------------------------------------

def estimate_ride_time(
    origin_stop_id: str,
    destination_stop_id: str,
    route_id: str,
    route_type: int = 1,
) -> int:
    """
    Estimate subway ride time between two stops in minutes.

    Uses stop sequence ordering from the MBTA /stops endpoint to count stops,
    then multiplies by a per-type rate (2 min/stop heavy rail, 3 min/stop light rail).

    This is an approximation — it counts stops between the two stations on the
    route and applies a fixed per-stop rate. Transfers are not handled here.

    Args:
        origin_stop_id: MBTA stop ID of boarding stop
        destination_stop_id: MBTA stop ID of alighting stop
        route_id: MBTA route ID (e.g. "Red", "Green-B")
        route_type: 0 for light rail, 1 for heavy rail

    Returns:
        Estimated ride time in minutes (minimum 2).
    """
    headers = {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}

    # Get the ordered stop list for this route
    params = {
        "filter[route]": route_id,
        "include": "route",
    }
    resp = requests.get(f"{MBTA_BASE}/stops", params=params, headers=headers, timeout=10)
    resp.raise_for_status()

    stop_ids = [s["id"] for s in resp.json().get("data", [])]

    try:
        origin_idx = stop_ids.index(origin_stop_id)
        dest_idx = stop_ids.index(destination_stop_id)
    except ValueError:
        # Stop not found on this route — return a safe fallback
        return 15

    num_stops = abs(dest_idx - origin_idx)
    mins_per_stop = MINS_PER_STOP.get(route_type, 2)
    return max(2, num_stops * mins_per_stop)


# ---------------------------------------------------------------------------
# Direction detection
# ---------------------------------------------------------------------------

def get_direction(origin_stop_id: str, dest_stop_id: str, route_id: str) -> int:
    """
    Determine which MBTA direction_id (0 or 1) to board at origin_stop_id to
    reach dest_stop_id on route_id.

    Fetches the stop sequence for direction 0 and checks whether origin appears
    before destination. If so, direction 0 is correct; otherwise direction 1.
    Defaults to 0 if either stop isn't found in the sequence.

    Args:
        origin_stop_id: Parent station ID of boarding stop (e.g. "place-sstat")
        dest_stop_id:   Parent station ID of alighting stop (e.g. "place-harsq")
        route_id:       MBTA route ID (e.g. "Red", "Green-B")

    Returns:
        0 or 1
    """
    headers = {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}

    params = {
        "filter[route]": route_id,
        "direction_id": 0,
    }
    resp = requests.get(f"{MBTA_BASE}/stops", params=params, headers=headers, timeout=10)
    resp.raise_for_status()

    stop_ids = [s["id"] for s in resp.json().get("data", [])]

    try:
        origin_idx = stop_ids.index(origin_stop_id)
        dest_idx = stop_ids.index(dest_stop_id)
    except ValueError:
        return 0  # Can't determine — show both directions' trains, default 0

    return 0 if origin_idx < dest_idx else 1


def find_transfer_stop(route_id_a: str, route_id_b: str) -> dict | None:
    """
    Find a station where two subway routes intersect (used for transfer planning).

    Fetches parent station IDs for each route and returns the first station that
    appears on both. Returns None if the routes don't share any stations.

    Args:
        route_id_a: Origin route ID (e.g. "Orange")
        route_id_b: Destination route ID (e.g. "Blue")

    Returns:
        Dict with name, stop_id, lat, lng — or None if no shared station found.
    """
    headers = {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}

    def fetch_stops(route_id: str) -> dict[str, dict]:
        resp = requests.get(
            f"{MBTA_BASE}/stops",
            params={"filter[route]": route_id},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return {s["id"]: s for s in resp.json().get("data", [])}

    stops_a = fetch_stops(route_id_a)
    stops_b = fetch_stops(route_id_b)

    common_ids = set(stops_a.keys()) & set(stops_b.keys())
    if not common_ids:
        return None

    stop_id = next(iter(common_ids))
    attrs = stops_a[stop_id]["attributes"]
    return {
        "name": attrs["name"],
        "stop_id": stop_id,
        "lat": attrs["latitude"],
        "lng": attrs["longitude"],
    }


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

def main() -> None:
    """
    End-to-end test of all pipeline functions.
    Uses South Station → Harvard Square as the test route.
    """
    print("=" * 60)
    print("Can I Make It? — Milestone 1 pipeline test")
    print("=" * 60)

    origin_name = "South Station, Boston, MA"
    destination_name = "Harvard Square, Cambridge, MA"

    # 1. Geocoding
    print(f"\n[1] Geocoding origin: '{origin_name}'")
    origin_lat, origin_lng = get_lat_lng(origin_name)
    print(f"    {origin_lat:.5f}, {origin_lng:.5f}")

    print(f"\n[1] Geocoding destination: '{destination_name}'")
    dest_lat, dest_lng = get_lat_lng(destination_name)
    print(f"    {dest_lat:.5f}, {dest_lng:.5f}")

    # 2. Nearest subway stop
    print(f"\n[2] Nearest subway stop to origin")
    origin_stop = get_nearest_subway_station(origin_lat, origin_lng)
    if origin_stop:
        print(f"    {origin_stop['name']}  (id: {origin_stop['stop_id']})")
        print(f"    {origin_stop['distance_miles']} mi away | wheelchair: {origin_stop['wheelchair']}")
        print(f"    Routes: {', '.join(r['display_name'] for r in origin_stop['routes'])}")
    else:
        print("    No subway stop within 1.5 miles.")

    print(f"\n[2] Nearest subway stop to destination")
    dest_stop = get_nearest_subway_station(dest_lat, dest_lng)
    if dest_stop:
        print(f"    {dest_stop['name']}  (id: {dest_stop['stop_id']})")
        print(f"    {dest_stop['distance_miles']} mi away | wheelchair: {dest_stop['wheelchair']}")
        print(f"    Routes: {', '.join(r['display_name'] for r in dest_stop['routes'])}")
    else:
        print("    No subway stop within 1.5 miles.")

    # 3. Walk time
    if origin_stop:
        wt = estimate_walk_time(origin_lat, origin_lng, origin_stop["lat"], origin_stop["lng"])
        print(f"\n[3] Walk to {origin_stop['name']}: {wt} min")
    if dest_stop:
        wt = estimate_walk_time(dest_stop["lat"], dest_stop["lng"], dest_lat, dest_lng)
        print(f"[3] Walk from {dest_stop['name']} to destination: {wt} min")

    # 4. Arrival predictions at origin stop
    if origin_stop:
        print(f"\n[4] Upcoming arrivals at {origin_stop['name']}")
        preds = get_arrival_predictions(origin_stop["stop_id"])
        if preds:
            for p in preds[:5]:
                t = p["arrival_time"].strftime("%I:%M %p") if p["arrival_time"] else "—"
                print(
                    f"    {p['route_name']:20s}  dir={p['direction_id']}  "
                    f"{t}  ({p['minutes_away']} min)"
                )
        else:
            print("    No upcoming arrivals — subway may not be running.")

    # 5. Ride time estimate (only if both stops found and share a route)
    if origin_stop and dest_stop:
        origin_route_ids = {r["route_id"] for r in origin_stop["routes"]}
        dest_route_ids = {r["route_id"] for r in dest_stop["routes"]}
        shared = origin_route_ids & dest_route_ids

        if shared:
            route_id = next(iter(shared))
            # Determine route_type from ROUTE_META key presence
            route_type = 1 if route_id in ("Red", "Orange", "Blue") else 0
            ride = estimate_ride_time(
                origin_stop["stop_id"], dest_stop["stop_id"], route_id, route_type
            )
            print(f"\n[5] Estimated ride time ({route_id}): {ride} min")
        else:
            print(
                f"\n[5] No direct route — transfer likely needed. "
                f"Origin routes: {origin_route_ids} | Dest routes: {dest_route_ids}"
            )

    print("\n" + "=" * 60)
    print("Pipeline test complete.")


if __name__ == "__main__":
    main()
