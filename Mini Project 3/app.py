"""
app.py — Flask routes for "Can I Make It?" MBTA trip planner.

Routes:
    GET  /       → index.html  (input form)
    POST /plan   → result.html or error.html
"""

from datetime import datetime, timedelta

import requests
from flask import Flask, render_template, request

import MBTA_Trip_Timer_v01 as mbta_helper

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Jinja2 filter: format a datetime as "3:47 PM" (no leading zero, cross-platform)
# ---------------------------------------------------------------------------

@app.template_filter("timeformat")
def timeformat_filter(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%I:%M %p").lstrip("0")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/plan", methods=["POST"])
def plan():
    origin = request.form.get("origin", "").strip()
    destination = request.form.get("destination", "").strip()
    arrival_time_str = request.form.get("arrival_time", "").strip()

    # --- Input validation ---
    if not origin or not destination or not arrival_time_str:
        return render_template(
            "error.html",
            message="Please fill in all three fields before submitting.",
        )

    # HTML <input type="time"> delivers "HH:MM" in 24-hour format
    try:
        arrival_naive = datetime.strptime(arrival_time_str, "%H:%M")
    except ValueError:
        return render_template("error.html", message="Invalid arrival time. Please use the time picker.")

    # Combine with today's date. If the time has already passed today, assume tomorrow.
    now_local = datetime.now()
    arrival_dt = now_local.replace(
        hour=arrival_naive.hour,
        minute=arrival_naive.minute,
        second=0,
        microsecond=0,
    )
    if arrival_dt <= now_local:
        arrival_dt += timedelta(days=1)

    arrival_display = arrival_dt.strftime("%I:%M %p").lstrip("0")

    # --- Geocode both locations ---
    try:
        origin_lat, origin_lng = mbta_helper.get_lat_lng(origin)
        dest_lat, dest_lng = mbta_helper.get_lat_lng(destination)
    except ValueError as exc:
        return render_template("error.html", message=str(exc))
    except (requests.HTTPError, requests.Timeout, requests.ConnectionError):
        return render_template(
            "error.html",
            message="Could not reach the Mapbox geocoding service. Check your connection and try again.",
        )

    # --- Find nearest subway stops ---
    try:
        origin_stop = mbta_helper.get_nearest_subway_station(origin_lat, origin_lng)
        dest_stop = mbta_helper.get_nearest_subway_station(dest_lat, dest_lng)
    except (requests.HTTPError, requests.Timeout, requests.ConnectionError):
        return render_template(
            "error.html",
            message="Could not reach the MBTA API. Check your connection and try again.",
        )

    if not origin_stop:
        return render_template(
            "error.html",
            message=f'No subway stop within 1.5 miles of "{origin}". '
                    "The MBTA subway may not serve this area.",
        )
    if not dest_stop:
        return render_template(
            "error.html",
            message=f'No subway stop within 1.5 miles of "{destination}". '
                    "The MBTA subway may not serve this area.",
        )

    # --- Walk times ---
    walk_to = mbta_helper.estimate_walk_time(
        origin_lat, origin_lng, origin_stop["lat"], origin_stop["lng"]
    )
    walk_from = mbta_helper.estimate_walk_time(
        dest_stop["lat"], dest_stop["lng"], dest_lat, dest_lng
    )

    # Common template context (map pins + labels always needed)
    map_ctx = {
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "dest_lat": dest_lat,
        "dest_lng": dest_lng,
        "mapbox_token": mbta_helper.MAPBOX_TOKEN,
        "origin": origin,
        "destination": destination,
        "origin_stop": origin_stop,
        "dest_stop": dest_stop,
    }

    # --- Edge case: same stop for both ends → just walk ---
    if origin_stop["stop_id"] == dest_stop["stop_id"]:
        walk_direct = mbta_helper.estimate_walk_time(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        return render_template("result.html", same_stop=True, walk_direct=walk_direct, **map_ctx)

    # --- Determine whether a transfer is needed ---
    origin_route_ids = {r["route_id"] for r in origin_stop["routes"]}
    dest_route_ids = {r["route_id"] for r in dest_stop["routes"]}
    shared_routes = origin_route_ids & dest_route_ids
    transfer_needed = len(shared_routes) == 0

    # Helper: determine route_type integer from route_id
    def route_type(rid: str) -> int:
        return 1 if rid in ("Red", "Orange", "Blue") else 0

    # -----------------------------------------------------------------------
    # Case A: Transfer required
    # -----------------------------------------------------------------------
    if transfer_needed:
        origin_route_id = next(iter(origin_route_ids))
        dest_route_id = next(iter(dest_route_ids))
        origin_route_info = next(r for r in origin_stop["routes"] if r["route_id"] == origin_route_id)
        dest_route_info = next(r for r in dest_stop["routes"] if r["route_id"] == dest_route_id)

        try:
            transfer_stop = mbta_helper.find_transfer_stop(origin_route_id, dest_route_id)
        except (requests.HTTPError, requests.Timeout):
            transfer_stop = None

        if transfer_stop:
            dir_to_transfer = mbta_helper.get_direction(
                origin_stop["stop_id"], transfer_stop["stop_id"], origin_route_id
            )
            ride1 = mbta_helper.estimate_ride_time(
                origin_stop["stop_id"], transfer_stop["stop_id"],
                origin_route_id, route_type(origin_route_id),
            )
            ride2 = mbta_helper.estimate_ride_time(
                transfer_stop["stop_id"], dest_stop["stop_id"],
                dest_route_id, route_type(dest_route_id),
            )
        else:
            dir_to_transfer = 0
            ride1, ride2 = 10, 10  # rough fallback if transfer station unknown

        transfer_penalty = 5  # minutes to walk between platforms
        total_ride = ride1 + transfer_penalty + ride2

        try:
            predictions = mbta_helper.get_arrival_predictions(
                origin_stop["stop_id"], dir_to_transfer
            )
        except (requests.HTTPError, requests.Timeout):
            predictions = []

        if not predictions:
            return render_template(
                "error.html",
                message="No upcoming trains found at your origin stop. "
                        "The MBTA subway may not be running right now.",
            )

        first_train = next((p for p in predictions if p["minutes_away"] is not None), None)
        wait_min = first_train["minutes_away"] if first_train else 0
        total_min = walk_to + wait_min + total_ride + walk_from
        leave_by_dt = arrival_dt - timedelta(minutes=total_min)
        leave_by_str = leave_by_dt.strftime("%I:%M %p").lstrip("0")

        too_late = leave_by_dt <= now_local

        return render_template(
            "result.html",
            same_stop=False,
            transfer_needed=True,
            arrival_time=arrival_display,
            leave_by=leave_by_str,
            too_late=too_late,
            walk_to_min=walk_to,
            walk_from_min=walk_from,
            ride1_min=ride1,
            ride2_min=ride2,
            transfer_penalty=transfer_penalty,
            wait_min=wait_min,
            total_min=total_min,
            origin_route=origin_route_info,
            dest_route=dest_route_info,
            transfer_stop=transfer_stop,
            transfer_lat=transfer_stop["lat"] if transfer_stop else None,
            transfer_lng=transfer_stop["lng"] if transfer_stop else None,
            predictions=predictions[:3],
            **map_ctx,
        )

    # -----------------------------------------------------------------------
    # Case B: Direct connection (no transfer)
    # -----------------------------------------------------------------------
    route_id = next(iter(shared_routes))
    route_info = next(r for r in origin_stop["routes"] if r["route_id"] == route_id)

    direction_id = mbta_helper.get_direction(
        origin_stop["stop_id"], dest_stop["stop_id"], route_id
    )

    try:
        predictions = mbta_helper.get_arrival_predictions(
            origin_stop["stop_id"], direction_id
        )
    except (requests.HTTPError, requests.Timeout):
        return render_template(
            "error.html",
            message="Could not fetch train predictions. Please try again in a moment.",
        )

    if not predictions:
        return render_template(
            "error.html",
            message="No upcoming trains found at your origin stop. "
                    "The MBTA subway may not be running right now.",
        )

    ride_min = mbta_helper.estimate_ride_time(
        origin_stop["stop_id"], dest_stop["stop_id"], route_id, route_type(route_id)
    )

    first_train = next((p for p in predictions if p["minutes_away"] is not None), None)
    wait_min = first_train["minutes_away"] if first_train else 0
    total_min = walk_to + wait_min + ride_min + walk_from
    leave_by_dt = arrival_dt - timedelta(minutes=total_min)
    leave_by_str = leave_by_dt.strftime("%I:%M %p").lstrip("0")

    too_late = leave_by_dt <= now_local

    return render_template(
        "result.html",
        same_stop=False,
        transfer_needed=False,
        arrival_time=arrival_display,
        leave_by=leave_by_str,
        too_late=too_late,
        walk_to_min=walk_to,
        walk_from_min=walk_from,
        ride_min=ride_min,
        wait_min=wait_min,
        total_min=total_min,
        route=route_info,
        direction_id=direction_id,
        predictions=predictions[:3],
        **map_ctx,
    )


if __name__ == "__main__":
    app.run(debug=True)
