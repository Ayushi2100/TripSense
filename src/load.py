"""Loaders. Raw files are never modified; text repair and parsing happen in memory."""
import re

import numpy as np
import pandas as pd

from . import config

_GARBLE = ("â€", "â‚", "Ã")


def fix_mojibake(value):
    """Repair UTF-8 text that was decoded as Windows-1252 (e.g. 'â€“' -> '-')."""
    if not isinstance(value, str) or not any(m in value for m in _GARBLE):
        return value
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def read_csv(name, **kwargs):
    df = pd.read_csv(config.RAW / name, encoding="utf-8-sig", **kwargs)
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            df[col] = df[col].map(fix_mojibake)
    return df


def parse_hmm(value):
    """'2.2' -> 2.33 h, '3.26' -> 3.43 h. Values read as hours.minutes.

    A single digit after the point is read as tens of minutes (2.2 = 2h20m), on the
    assumption that a spreadsheet dropped a trailing zero. Minutes of 60 or more are
    impossible, so the result is NaN instead of a guess (e.g. '3.7').
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value).strip()
    if not text:
        return np.nan
    hours, _, mins = text.partition(".")
    minutes = 0 if mins == "" else (int(mins) * 10 if len(mins) == 1 else int(mins[:2]))
    if minutes >= 60:
        return np.nan
    return round(int(hours) + minutes / 60, 2)


def parse_months(value):
    """'1,2,12' or '1|2|12' -> [1, 2, 12]. Missing -> []."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return sorted({int(p) for p in re.split(r"[,;|\s]+", str(value)) if p.strip().isdigit()})


def load_all():
    """Return every table used in Phases 4-5."""
    dest = read_csv("destinations.csv", dtype={"travel_time_hrs": str, "best_months": str})
    dest["travel_time_hrs_entered"] = dest["travel_time_hrs"]
    dest["travel_time_hrs"] = dest["travel_time_hrs_entered"].map(parse_hmm)
    for col in ["latitude", "longitude", "elevation_m", "road_distance_km"]:
        dest[col] = pd.to_numeric(dest[col], errors="coerce")
    dest["best_months_list"] = dest["best_months"].map(parse_months)

    return {
        "destinations": dest,
        "destinations_clean": read_csv("destinations_clean.csv"),
        "attractions": read_csv("attractions.csv"),
        "activities": read_csv("activities.csv"),
        "accommodation": read_csv("accommodation.csv"),
        "transportation": read_csv("transportation.csv"),
        "weather": read_csv("weather.csv"),
        "origins": read_csv("origin_locations.csv"),
        "routes": read_csv("route_data.csv"),
    }
