#!/usr/bin/env python3

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/live.json"

UA = "CoastlineApp/0.7"

TIDES = [
    {"station": "9443090", "name": "Neah Bay, WA", "lat": 48.370, "lng": -124.602},
    {"station": "9444090", "name": "Port Angeles, WA", "lat": 48.125, "lng": -123.440},
    {"station": "9447130", "name": "Seattle, WA", "lat": 47.602, "lng": -122.339},

    {"station": "9439040", "name": "Astoria, OR", "lat": 46.207, "lng": -123.768},
    {"station": "9437540", "name": "Garibaldi, OR", "lat": 45.554, "lng": -123.918},
    {"station": "9435380", "name": "South Beach, OR", "lat": 44.625, "lng": -124.044},
    {"station": "9432780", "name": "Charleston, OR", "lat": 43.345, "lng": -124.322},

    {"station": "9419750", "name": "Crescent City, CA", "lat": 41.745, "lng": -124.184},
    {"station": "9418767", "name": "North Spit, Humboldt Bay, CA", "lat": 40.767, "lng": -124.217},
    {"station": "9414290", "name": "San Francisco, CA", "lat": 37.807, "lng": -122.465},
    {"station": "9413450", "name": "Monterey, CA", "lat": 36.605, "lng": -121.888},
    {"station": "9412110", "name": "Port San Luis, CA", "lat": 35.169, "lng": -120.754},
    {"station": "9411340", "name": "Santa Barbara, CA", "lat": 34.408, "lng": -119.685},
    {"station": "9410660", "name": "Los Angeles, CA", "lat": 33.720, "lng": -118.272},
    {"station": "9410580", "name": "Newport Bay Entrance, CA", "lat": 33.603, "lng": -117.883},
    {"station": "9410230", "name": "La Jolla, CA", "lat": 32.867, "lng": -117.257},
    {"station": "9410170", "name": "San Diego, CA", "lat": 32.714, "lng": -117.174},
]

NAMES = {
    "46256": "Long Beach Channel",
    "PRJC1": "Los Angeles Pier J",
    "AGXC1": "Angels Gate",
    "PFDC1": "Los Angeles Pier 400",
    "PFXC1": "Los Angeles Pier F",

    "46042": "Monterey Bay",
    "46012": "Half Moon Bay",
    "46026": "San Francisco",
    "46022": "Eel River",
    "46027": "St. Georges",

    "46050": "Stonewall Bank",
    "46029": "Columbia River Bar",
    "46041": "Cape Elizabeth",
    "46087": "Neah Bay",
    "46088": "New Dungeness",

    "46025": "Santa Monica Basin",
    "46053": "East Santa Barbara Channel",
    "46054": "West Santa Barbara Channel",
    "46086": "San Clemente Basin",
}


def get(url, timeout=25):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": UA}
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def num(value):
    if value in (None, "MM", "M", "", "999", "999.0"):
        return None

    try:
        return float(value)
    except Exception:
        return None


def west_coast(lat, lon):
    if not (32.3 <= lat <= 49.1 and -131 <= lon <= -116.5):
        return False

    if lat >= 42:
        return lon <= -122.3

    if lat >= 38:
        return lon <= -122.0

    if lat >= 34.35:
        return lon <= -119.0

    return lon <= -117.0


def parse_ndbc(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    header = None
    output = []

    for line in lines:

        if line.startswith("#STN"):
            header = line.lstrip("#").split()
            continue

        if line.startswith("#") or header is None:
            continue

        parts = line.split()

        if len(parts) < len(header):
            continue

        row = dict(zip(header, parts))

        lat = num(row.get("LAT"))
        lon = num(row.get("LON"))

        if lat is None or lon is None:
            continue

        if not west_coast(lat, lon):
            continue

        wind_speed = num(row.get("WSPD"))
        gust = num(row.get("GST"))
        wind_direction = num(row.get("WDIR"))

        wave_height = num(row.get("WVHT"))
        dominant_period = num(row.get("DPD"))
        average_period = num(row.get("APD"))
        wave_direction = num(row.get("MWD"))

        pressure = num(row.get("PRES"))
        air_temp = num(row.get("ATMP"))
        water_temp = num(row.get("WTMP"))

        def ms_to_knots(value):
            if value is None:
                return None
            return value * 1.94384449

        def meters_to_feet(value):
            if value is None:
                return None
            return value * 3.2808399

        def celsius_to_fahrenheit(value):
            if value is None:
                return None
            return value * 9 / 5 + 32

        try:
            observation_time = datetime(
                int(row["YYYY"]),
                int(row["MM"]),
                int(row["DD"]),
                int(row["hh"]),
                int(row["mm"]),
                tzinfo=timezone.utc,
            )

            observed_at = observation_time.isoformat().replace("+00:00", "Z")

        except Exception:
            observed_at = None

        station = row.get("STN")

        output.append({
            "station": station,
            "name": NAMES.get(
                station,
                "Station " + str(station)
            ),

            "lat": lat,
            "lng": lon,

            "observed_at": observed_at,

            "wind_from_deg": wind_direction,

            "wind_kt": (
                None if wind_speed is None
                else round(ms_to_knots(wind_speed), 1)
            ),

            "gust_kt": (
                None if gust is None
                else round(ms_to_knots(gust), 1)
            ),

            "wave_ft": (
                None if wave_height is None
                else round(meters_to_feet(wave_height), 1)
            ),

            "period_sec": (
                dominant_period
                if dominant_period is not None
                else average_period
            ),

            "wave_from_deg": wave_direction,

            "pressure_hpa": pressure,

            "air_f": (
                None if air_temp is None
                else round(celsius_to_fahrenheit(air_temp), 1)
            ),

            "water_f": (
                None if water_temp is None
                else round(celsius_to_fahrenheit(water_temp), 1)
            ),

            "source": "NOAA/NDBC latest observations",
        })

    return output


def coops(params):

    base_url = (
        "https://api.tidesandcurrents.noaa.gov/"
        "api/prod/datagetter"
    )

    params = {
        **params,
        "units": "english",
        "time_zone": "gmt",
        "application": "CoastlineApp",
        "format": "json",
    }

    url = base_url + "?" + urllib.parse.urlencode(params)

    return json.loads(get(url))


def parse_datetime(value):

    if not value:
        return None

    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ):

        try:
            return datetime.strptime(
                value,
                fmt
            ).replace(tzinfo=timezone.utc)

        except Exception:
            pass

    return None


def old_live():

    try:
        return json.loads(
            OUT.read_text()
        )

    except Exception:
        return {}


def predictions_fresh(old):

    timestamp = old.get(
        "tide_predictions_generated_at"
    )

    if not timestamp:
        return False

    try:
        old_time = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        return (
            datetime.now(timezone.utc) - old_time
            < timedelta(hours=6)
        )

    except Exception:
        return False


def tide_data():

    old = old_live()

    old_by_station = {
        item.get("station"): item
        for item in old.get("tides", [])
    }

    reuse_predictions = predictions_fresh(old)

    now = datetime.now(timezone.utc)

    today = now.strftime("%Y%m%d")

    results = []

    for station in TIDES:

        item = {
            **station,
            "height_ft": None,
            "observed_at": None,
            "trend": None,
            "next_high": None,
            "next_low": None,
        }

        try:

            water_level = coops({
                "date": "latest",
                "station": station["station"],
                "product": "water_level",
                "datum": "MLLW",
            })

            data = water_level.get("data") or []

            if data:

                latest = data[-1]

                item["height_ft"] = num(
                    latest.get("v")
                )

                item["observed_at"] = latest.get("t")

        except Exception as error:

            item["water_level_error"] = str(error)[:140]

        predictions = None

        if (
            reuse_predictions
            and station["station"] in old_by_station
        ):

            predictions = old_by_station[
                station["station"]
            ].get("predictions")

        if not predictions:

            try:

                prediction_json = coops({
                    "begin_date": today,
                    "range": "48",
                    "station": station["station"],
                    "product": "predictions",
                    "datum": "MLLW",
                    "interval": "hilo",
                })

                predictions = (
                    prediction_json.get("predictions")
                    or []
                )

            except Exception as error:

                item["prediction_error"] = str(error)[:140]

                predictions = []

        item["predictions"] = predictions

        future = []

        for prediction in predictions:

            prediction_time = parse_datetime(
                prediction.get("t")
            )

            if (
                prediction_time
                and prediction_time
                >= now - timedelta(minutes=10)
            ):

                future.append(
                    (prediction_time, prediction)
                )

        future.sort(
            key=lambda value: value[0]
        )

        if future:

            event_type = (
                future[0][1].get("type") or ""
            ).upper()

            if event_type == "H":
                item["trend"] = "Rising"

            elif event_type == "L":
                item["trend"] = "Falling"

            for prediction_time, prediction in future:

                tide_event = {
                    "time": prediction.get("t"),
                    "height_ft": num(
                        prediction.get("v")
                    ),
                }

                event_type = (
                    prediction.get("type") or ""
                ).upper()

                if (
                    event_type == "H"
                    and item["next_high"] is None
                ):
                    item["next_high"] = tide_event

                if (
                    event_type == "L"
                    and item["next_low"] is None
                ):
                    item["next_low"] = tide_event

                if (
                    item["next_high"]
                    and item["next_low"]
                ):
                    break

        results.append(item)

    if reuse_predictions:

        prediction_timestamp = old.get(
            "tide_predictions_generated_at"
        )

    else:

        prediction_timestamp = (
            now.isoformat().replace("+00:00", "Z")
        )

    return results, prediction_timestamp


def main():

    now = datetime.now(timezone.utc)

    ndbc_text = get(
        "https://www.ndbc.noaa.gov/"
        "data/latest_obs/latest_obs.txt"
    )

    ndbc = parse_ndbc(ndbc_text)

    tides, prediction_timestamp = tide_data()

    output = {
        "generated_at": (
            now.isoformat().replace("+00:00", "Z")
        ),

        "tide_predictions_generated_at":
            prediction_timestamp,

        "status": "live",

        "ndbc": ndbc,

        "tides": tides,

        "sources": {
            "ndbc": (
                "https://www.ndbc.noaa.gov/"
                "data/latest_obs/latest_obs.txt"
            ),

            "coops": (
                "https://api.tidesandcurrents.noaa.gov/"
                "api/prod/datagetter"
            ),
        },
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=False
        ) + "\n"
    )

    print(
        f"Wrote {len(ndbc)} West Coast "
        f"NDBC observations and "
        f"{len(tides)} tide stations"
    )


if __name__ == "__main__":
    main()
