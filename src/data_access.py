"""Loads the tables the engine and the app need. Read-only."""
import numpy as np
import pandas as pd

from . import config, features as feature_code
from .load import read_csv


def load_engine_data():
    """Return a dict of DataFrames. Run `python -m src.build_features` first."""
    feats = pd.read_csv(config.PROC / "destination_features.csv")
    months = pd.read_csv(config.PROC / "destination_month_features.csv")
    attractions = read_csv("attractions.csv")
    activities = read_csv("activities.csv")
    accommodation = read_csv("accommodation.csv")
    fares = pd.read_csv(config.RAW / "transport_fare_estimates.csv")
    origins = read_csv("origin_locations.csv")
    routes = read_csv("route_data.csv")
    return {"features": feats, "months": months, "attractions": attractions,
            "activities": activities, "accommodation": accommodation, "fares": fares,
            "origins": origins, "routes": routes}


def origin_choices(data=None):
    """[(origin_id, origin_name), ...] in file order."""
    o = data["origins"] if data is not None else read_csv("origin_locations.csv")
    return list(zip(o["origin_id"], o["origin_name"]))


def origin_view(data, origin_id):
    """Same data, but `features` describes the trip from `origin_id`.

    Views are cached inside the base dict, so repeated calls are cheap and the features object
    stays the same between reruns. Calling it on a view returns a view for the new origin.
    """
    base = data.get("_base", data)
    views = base.setdefault("_views", {})
    if origin_id not in views:
        view = dict(base)
        view["features"] = feature_code.apply_origin(base["features"], base["routes"], origin_id, base["origins"])
        view["_base"] = base
        view["_origin_id"] = origin_id
        views[origin_id] = view
    return views[origin_id]


def effective_drive_hours(feats):
    """Drive time in hours. Where the entered time is missing, road km divided by the
    median speed of the other destinations (flagged by `drive_time_estimated`)."""
    f = feats.copy()
    speed = f["avg_speed_kmh"].median()
    f["drive_time_estimated"] = f["travel_time_hrs"].isna()
    f["drive_hours"] = f["travel_time_hrs"].fillna(f["road_distance_km"] / speed)
    return f


def month_name(m):
    return ["January", "February", "March", "April", "May", "June", "July", "August",
            "September", "October", "November", "December"][int(m) - 1]
