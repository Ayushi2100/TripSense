"""Phase 5 feature engineering. Every feature is derived from a countable record or a
stated rule; no subjective scores. Thresholds and mappings live in config.py."""
import re

import numpy as np
import pandas as pd

from . import config

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------- geometry
def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------- interests
def activity_interests(activity_type):
    """Unique interests for one activity row, from its '/'-separated type text."""
    if not isinstance(activity_type, str):
        return []
    tokens = [t.strip().lower() for t in re.split(r"[/,|]", activity_type) if t.strip()]
    if config.PILGRIMAGE_DROPS_TREKKING and "pilgrimage" in tokens:
        tokens = [t for t in tokens if t != "trekking"]
    found = []
    for token in tokens:
        for interest in config.ACTIVITY_TOKEN_MAP.get(token, []):
            if interest not in found:
                found.append(interest)
    return found


def attraction_interests(attraction_type):
    if not isinstance(attraction_type, str):
        return []
    return config.ATTRACTION_TYPE_MAP.get(attraction_type.strip().lower(), [])


def interest_features(attractions, activities):
    """Share of each interest among a destination's attractions and activities.

    Each item carries weight 1, split equally across its interests. Items with no
    interest (golf, leisure, pilgrimage transport) are counted as unmapped and left
    out of the shares. Shares sum to 1 per destination.
    """
    items = []
    for _, r in attractions.iterrows():
        items.append((r.destination_id, "attraction", attraction_interests(r.attraction_type)))
    for _, r in activities.iterrows():
        items.append((r.destination_id, "activity", activity_interests(r.activity_type)))

    rows = []
    for dest_id in sorted({i[0] for i in items}):
        mine = [i for i in items if i[0] == dest_id]
        weights = dict.fromkeys(config.INTERESTS, 0.0)
        unmapped = 0
        for _, _, interests in mine:
            if not interests:
                unmapped += 1
                continue
            for interest in interests:
                weights[interest] += 1.0 / len(interests)
        total = sum(weights.values())
        row = {"destination_id": dest_id,
               "n_attractions": sum(1 for i in mine if i[1] == "attraction"),
               "n_activities": sum(1 for i in mine if i[1] == "activity"),
               "n_items_unmapped": unmapped}
        for interest in config.INTERESTS:
            row[f"share_{interest}"] = round(weights[interest] / total, 4) if total else np.nan
        row["top_interest"] = max(config.INTERESTS, key=lambda k: weights[k]) if total else None
        rows.append(row)
    return pd.DataFrame(rows)


def interest_mapping_table():
    rows = [{"source": "attractions.attraction_type", "token": k, "interests": "|".join(v), "note": ""}
            for k, v in config.ATTRACTION_TYPE_MAP.items()]
    for k, v in config.ACTIVITY_TOKEN_MAP.items():
        note = "logistics, not an interest" if k == "pilgrimage transport" else (
            "no interest signal on its own" if not v else "")
        rows.append({"source": "activities.activity_type", "token": k,
                     "interests": "|".join(v), "note": note})
    rows.append({"source": "activities.activity_type", "token": "trekking (with 'pilgrimage')",
                 "interests": "", "note": "dropped: pilgrimage treks are not counted as adventure"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- season
def season_category(tmax, rain, rules=None):
    rules = rules or config.SEASON_RULES
    if rain >= rules["wet_mm"]:
        return "wet"
    if tmax > rules["hot_tmax"]:
        return "hot"
    if tmax < rules["cold_tmax"]:
        return "cold"
    return "comfortable"


def month_features(weather, destinations, rules=None):
    rules = rules or config.SEASON_RULES
    w = weather.copy()
    w["category"] = [season_category(t, r, rules) for t, r in zip(w.avg_temp_max_c, w.rainfall_mm)]
    w["comfortable"] = (w.category == "comfortable").astype(int)
    w["temp_gap_c"] = np.maximum.reduce([
        np.zeros(len(w)), rules["cold_tmax"] - w.avg_temp_max_c, w.avg_temp_max_c - rules["hot_tmax"]]).round(2)
    w["rain_excess_mm"] = np.maximum(0, w.rainfall_mm - rules["wet_mm"]).round(1)
    w["near_freezing"] = (w.avg_temp_min_c <= rules["freezing_tmin"]).astype(int)

    entered = destinations.set_index("destination_id").best_months_list.to_dict()
    w["in_best_months_entered"] = [int(m in entered.get(d, [])) for d, m in zip(w.destination_id, w.month)]
    w["agreement"] = np.select(
        [(w.comfortable == 1) & (w.in_best_months_entered == 1),
         (w.comfortable == 0) & (w.in_best_months_entered == 1),
         (w.comfortable == 1) & (w.in_best_months_entered == 0)],
        ["both", "entered_only", "weather_only"], default="neither")
    keep = ["destination_id", "month", "month_name", "avg_temp_min_c", "avg_temp_max_c", "avg_temp_mean_c",
            "rainfall_mm", "category", "comfortable", "temp_gap_c", "rain_excess_mm", "near_freezing",
            "in_best_months_entered", "agreement", "is_proxy_data"]
    return w[keep].sort_values(["destination_id", "month"]).reset_index(drop=True)


def weather_quality_flags(weather, destinations, factor=None, k=3):
    """'proxy' if borrowed from another place; 'inconsistent_with_neighbour' if annual
    rainfall differs by more than `factor` from the median of the `k` nearest other
    destinations (a median, so one odd neighbour cannot make a good series look bad)."""
    factor = factor or config.RAIN_NEIGHBOUR_FACTOR
    annual = weather.groupby("destination_id").rainfall_mm.sum()
    proxy = weather.groupby("destination_id").is_proxy_data.max().astype(bool)
    d = destinations.set_index("destination_id")
    flags = {}
    for dest_id in annual.index:
        if proxy[dest_id]:
            flags[dest_id] = "proxy"
            continue
        others = [o for o in annual.index if o != dest_id and not proxy[o]]
        dist = {o: haversine_km(d.latitude[dest_id], d.longitude[dest_id], d.latitude[o], d.longitude[o])
                for o in others}
        nearest = sorted(dist, key=dist.get)[:k]
        ratio = annual[dest_id] / annual[nearest].median()
        flags[dest_id] = "inconsistent_with_neighbour" if (ratio > factor or ratio < 1 / factor) else "ok"
    return pd.Series(flags, name="weather_quality_flag")


def season_sensitivity(weather):
    rows = []
    for sc in config.SENSITIVITY_SCENARIOS:
        rules = {**config.SEASON_RULES, **sc}
        cats = [season_category(t, r, rules) for t, r in zip(weather.avg_temp_max_c, weather.rainfall_mm)]
        n = pd.Series((np.array(cats) == "comfortable"), index=weather.destination_id).groupby(level=0).sum()
        label = f"band {sc['cold_tmax']:.0f}-{sc['hot_tmax']:.0f} C, wet >= {sc['wet_mm']:.0f} mm"
        rows.append(n.rename(label))
    return pd.concat(rows, axis=1).T


# ------------------------------------------------------------- logistics
def distance_table(destinations, destinations_clean, transportation):
    entered = destinations.set_index("destination_id").road_distance_km
    clean = pd.to_numeric(destinations_clean.set_index("destination_id").road_distance_km, errors="coerce")
    # Only rows measured from Pathankot belong in this Pathankot-source comparison;
    # transportation.csv now also holds origin-neutral "how to reach" rows for new destinations.
    from_pathankot = transportation.origin.str.contains("Pathankot", case=False, na=False)
    road = transportation[(transportation.transport_mode == "road") & from_pathankot] \
        .drop_duplicates("destination_id").set_index("destination_id").distance_km
    transport = road.reindex(entered.index)
    legs = transportation[(transportation.destination_id == "D09")
                          & (transportation.transport_mode == "road_or_rail")
                          & transportation.distance_km.notna()]
    if "D09" in transport.index and pd.isna(transport["D09"]) and len(legs) == 2:
        transport["D09"] = legs.distance_km.sum()  # Pathankot-Jammu + Jammu-Katra
    out = pd.DataFrame({"road_km_entered": entered, "road_km_clean_file": clean.reindex(entered.index),
                        "road_km_transport_table": transport})
    spread = out.max(axis=1) - out.min(axis=1)
    out["distance_conflict_flag"] = (spread / out.min(axis=1) > config.DISTANCE_CONFLICT_TOLERANCE).astype(int)
    return out


# ------------------------------------------------------------- origin
def apply_origin(feats, routes, origin_id, origins=None):
    """Return a copy of `feats` whose distance and drive-time columns describe the trip from
    `origin_id`. Values come from route_data.csv (road km, drive hours, straight-line km).

    Overwritten in place: road_distance_km, travel_time_hrs, straight_km, detour_ratio,
    avg_speed_kmh. Added: route_quality, route_hours_basis, route_available, origin_id,
    origin_name and road_km_from_pathankot (the only origin the collected fares refer to).
    """
    r = routes[routes.origin_id == origin_id].set_index("destination_id")
    if r.empty:
        raise ValueError(f"no route rows for origin {origin_id!r}")
    num = lambda c: pd.to_numeric(r[c], errors="coerce")
    f = feats.copy().set_index("destination_id")
    p = routes[routes.origin_id == config.DEFAULT_ORIGIN_ID].set_index("destination_id")
    f["road_km_from_pathankot"] = pd.to_numeric(p.road_distance_km, errors="coerce").reindex(f.index)
    road = num("road_distance_km").reindex(f.index)
    hours = num("estimated_drive_hours").reindex(f.index)
    straight = num("straight_line_distance_km").reindex(f.index)
    f["road_distance_km"] = road
    f["travel_time_hrs"] = hours
    f["straight_km"] = straight
    f["detour_ratio"] = (road / straight.where(straight > 0)).round(2)
    f["avg_speed_kmh"] = (road / hours).round(1)
    f["route_quality"] = r.data_quality.reindex(f.index)
    f["route_hours_basis"] = r.drive_hours_basis.reindex(f.index) if "drive_hours_basis" in r else ""
    f["route_available"] = road.notna() & (f["route_quality"] != "not_applicable")
    name = r.origin_name.iloc[0]
    f["origin_id"] = origin_id
    f["origin_name"] = name
    return f.reset_index()


# --------------------------------------------------------- accommodation
def accommodation_features(accommodation):
    priced = accommodation[accommodation.displayed_total_per_night_inr.notna()]
    g = priced.groupby("destination_id").displayed_total_per_night_inr
    out = pd.DataFrame({
        "accom_n_listed": accommodation.groupby("destination_id").size(),
        "accom_n_priced": g.size(),
        "accom_median_inr": g.median(), "accom_min_inr": g.min(), "accom_max_inr": g.max()})
    out["accom_n_priced"] = out["accom_n_priced"].fillna(0).astype(int)
    out["accom_reliable_flag"] = (out.accom_n_priced >= config.ACCOM_MIN_PRICED).astype(int)
    return out


# -------------------------------------------------------------- assemble
def build_all(tables):
    dest = tables["destinations"].copy()
    weather = tables["weather"]

    months = month_features(weather, dest)
    dist = distance_table(dest, tables["destinations_clean"], tables["transportation"])
    interests = interest_features(tables["attractions"], tables["activities"])
    accom = accommodation_features(tables["accommodation"])
    quality = weather_quality_flags(weather, dest)

    f = dest[["destination_id", "destination", "state", "primary_type",
              "latitude", "longitude", "elevation_m", "travel_time_hrs"]].set_index("destination_id")
    f = f.join(dist)
    f["distance_source"] = config.DISTANCE_SOURCE
    f["road_distance_km"] = f[{"entered": "road_km_entered", "clean_file": "road_km_clean_file",
                               "transport_table": "road_km_transport_table"}[config.DISTANCE_SOURCE]]
    f["straight_km"] = haversine_km(config.PATHANKOT[0], config.PATHANKOT[1], f.latitude, f.longitude).round(1)
    f["detour_ratio"] = (f.road_distance_km / f.straight_km).round(2)
    f["avg_speed_kmh"] = (f.road_distance_km / f.travel_time_hrs).round(1)

    for t in ["hill station", "historic town", "city", "pilgrimage", "valley", "lake"]:
        f["type_" + t.replace(" ", "_")] = (f.primary_type == t).astype(int)

    f = f.join(interests.set_index("destination_id"))

    comfy = months[months.comfortable == 1].groupby("destination_id").month.apply(list)
    entered = dest.set_index("destination_id").best_months_list
    f["n_comfortable_months"] = months.groupby("destination_id").comfortable.sum()
    f["comfortable_months"] = comfy.reindex(f.index).map(lambda m: "|".join(map(str, m)) if isinstance(m, list) else "")
    f["best_months_entered"] = entered.map(lambda m: "|".join(map(str, m)))

    def jaccard(dest_id):
        a = set(comfy.get(dest_id, []))
        b = set(entered[dest_id])
        if not a or not b:      # no weather data, or no entered best_months: agreement is unknown
            return np.nan
        return round(len(a & b) / len(a | b), 2)

    f["season_agreement_jaccard"] = [jaccard(i) for i in f.index]
    f["near_freezing_months"] = months.groupby("destination_id").near_freezing.sum()
    f["weather_quality_flag"] = quality
    f["weather_quality_flag"] = f["weather_quality_flag"].fillna("no_weather_data")
    f = f.join(accom)
    for c in ["accom_n_listed", "accom_n_priced", "accom_reliable_flag"]:   # destinations with no listings at all
        f[c] = f[c].fillna(0).astype(int)
    f = f.reset_index()
    # Route columns default to the first origin (Pathankot); the app re-applies the selected origin.
    if "routes" in tables:
        f = apply_origin(f, tables["routes"], config.DEFAULT_ORIGIN_ID, tables.get("origins"))
    return f, months


FEATURE_DICTIONARY = [
    ("destination_id", "Join key", "assigned", "destinations.csv", "D01-D30", ""),
    ("road_distance_km", "Road distance from the selected origin (saved file: Pathankot, O01)", "raw / estimate (see route_quality)",
     "route_data.csv", "Looked up by origin and destination; apply_origin() swaps the origin",
     "Most routes are estimates; see route_quality. For D01-D09 from Pathankot three sources conflict (distance_conflict_flag)"),
    ("road_km_entered / road_km_clean_file / road_km_transport_table", "Each source's value, kept side by side",
     "raw", "see column", "Vaishno Devi transport value = sum of Pathankot-Jammu and Jammu-Katra legs", ""),
    ("distance_conflict_flag", "1 if sources differ by more than 10% of the smallest", "derived",
     "the three distance columns", "(max-min)/min > 0.10", "Tolerance is an assumption"),
    ("travel_time_hrs", "Drive time from the selected origin, decimal hours", "raw (estimate), converted",
     "route_data.csv (Pathankot D01-D09 entered as H.MM)", "H.MM -> hours + minutes/60; a digit-only minute = tens of minutes",
     "Kangra's 3.7 from Pathankot is not a valid H.MM value and is left blank; other drive times are estimates"),
    ("straight_km", "Straight-line distance from the selected origin", "derived", "origin_locations.csv, destinations.csv",
     "Haversine between origin and destination coordinates", "Coordinates are approximate and not yet sourced"),
    ("detour_ratio", "Road distance divided by straight-line distance", "derived",
     "road_distance_km, straight_km", "Below 1 is impossible and signals an error", ""),
    ("avg_speed_kmh", "Road distance divided by drive time", "derived", "road_distance_km, travel_time_hrs",
     "", "Blank where time is blank"),
    ("elevation_m", "Elevation of the reference point", "raw", "destinations.csv", "", "Source not yet logged; D10-D30 are approximate"),
    ("route_quality", "How trustworthy the origin-destination route values are", "label", "route_data.csv",
     "author_entered | source_reported | estimated | not_applicable", "estimated = not verified against a route engine"),
    ("route_hours_basis", "Where the drive hours come from", "label", "route_data.csv", "author_entered | estimated | not_available", ""),
    ("route_available", "False when no route value exists (e.g. Chandigarh as a destination from Chandigarh)", "derived", "route_data.csv", "", ""),
    ("origin_id / origin_name", "Starting location the route columns describe", "assigned", "origin_locations.csv", "", ""),
    ("road_km_from_pathankot", "Road km from Pathankot whatever the selected origin", "derived", "route_data.csv", "Used to derive per-km fare rates, because collected fares are Pathankot-only", ""),
    ("type_*", "One-hot of primary_type", "derived", "destinations.csv", "", "Type labels are a project classification"),
    ("share_nature / adventure / culture / history / spiritual",
     "Share of the destination's attractions and activities in each interest", "derived",
     "attractions.csv, activities.csv", "Each item has weight 1 split across its interests; mapping in interest_mapping.csv",
     "Item lists are a curated sample of 4-7 attractions and 5-6 activities per destination, not exhaustive"),
    ("top_interest", "Interest with the largest share", "derived", "share_* columns", "", "Ties resolve in the order of config.INTERESTS"),
    ("n_attractions / n_activities", "Number of records collected", "raw count",
     "attractions.csv, activities.csv", "", "Reflects collection coverage; do not read as destination richness"),
    ("n_items_unmapped", "Items with no interest signal (golf, leisure, pilgrimage transport)", "derived",
     "activities.csv", "", ""),
    ("n_comfortable_months", "Months classed comfortable by the weather rule", "derived", "weather.csv",
     "daytime max 15-32 C and rain < 200 mm (config.SEASON_RULES)", "Thresholds are assumptions; see season_rule_sensitivity.csv"),
    ("comfortable_months", "Pipe-separated comfortable month numbers", "derived", "weather.csv", "as above", ""),
    ("best_months_entered", "Author-entered best months", "raw (estimate)", "destinations.csv", "",
     "Conflicts with sources for several destinations; compare with comfortable_months"),
    ("season_agreement_jaccard", "Overlap of entered best months and weather-comfortable months", "derived",
     "the two month lists", "|A and B| / |A or B|", "A low value means the two disagree, not which one is right"),
    ("near_freezing_months", "Months with average daily minimum <= 2 C", "derived", "weather.csv",
     "avg_temp_min_c <= config.SEASON_RULES['freezing_tmin']", "Town-level climate; snow depends on more than this"),
    ("weather_quality_flag", "ok / proxy / inconsistent_with_neighbour", "derived", "weather.csv",
     "Proxy if borrowed; inconsistent if annual rainfall differs 3x from the median of the 3 nearest destinations",
     "Detects only gross inconsistency"),
    ("accom_n_listed / accom_n_priced", "Listings recorded and listings with a price", "raw count", "accommodation.csv", "", ""),
    ("accom_median_inr / min / max", "Displayed total per night, listings with a price", "derived",
     "accommodation.csv", "Median of priced listings", "Mixed hostels, hotels and homestays; one snapshot date"),
    ("accom_reliable_flag", "1 if at least 3 priced listings", "derived", "accom_n_priced", "", "Threshold is an assumption"),
]


def feature_dictionary():
    return pd.DataFrame(FEATURE_DICTIONARY, columns=[
        "feature", "meaning", "raw_or_derived", "source_tables", "method", "limitation"])


def cosine_similarity_matrix(features, columns):
    x = features.set_index("destination")[columns].astype(float).values
    norm = np.linalg.norm(x, axis=1, keepdims=True)
    sim = (x @ x.T) / (norm @ norm.T)
    return pd.DataFrame(sim, index=features.destination, columns=features.destination).round(3)
