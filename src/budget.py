"""Transparent trip-cost estimate. Every line says where its number came from.

basis values: "collected" (from a sourced table), "derived" (computed from collected
rows), "pooled" (a stay price pooled from other destinations' listings), "placeholder" (an assumption in config.py, replace it with real data).
"""
import math

import numpy as np
import pandas as pd

from . import config


_CACHE = {}


def _priced(accommodation):
    key = ("acc", id(accommodation))
    if key not in _CACHE:
        acc = accommodation.copy()
        acc["price"] = pd.to_numeric(acc["displayed_total_per_night_inr"], errors="coerce")
        _CACHE[key] = acc.dropna(subset=["price"])
    return _CACHE[key]


def derived_rates(fares, feats):
    """INR per km for taxi (whole car) and bus (per person), from collected rows only."""
    key = ("rates", id(fares), id(feats))
    if key in _CACHE:
        return _CACHE[key]
    # The collected fares are Pathankot-origin, so the rate must use the Pathankot road km
    # (not the km of whichever origin is currently selected).
    col = "road_km_from_pathankot" if "road_km_from_pathankot" in feats.columns else "road_distance_km"
    km = feats.set_index("destination_id")[col]
    out = {}
    for mode in ["taxi", "bus"]:
        f = fares[fares["mode"] == mode].copy()
        f["mid"] = (f["fare_low_inr"] + f["fare_high_inr"]) / 2
        f["rate"] = f["mid"] / f["destination_id"].map(km)
        out[mode] = float(f["rate"].median())
    _CACHE[key] = out
    return out


def one_way_fare(dest_id, mode, fares, feats, rates):
    """Return (fare_inr, basis). Taxi fare is for the whole car, bus fare per person.

    Collected fares are Pathankot-to-destination only, so they are used only when the selected
    origin is Pathankot (O01). For any other origin the fare is the per-km rate times that
    route's road km, labelled "derived". The rate comes from short Pathankot-area routes, so
    it is a rough guide for long routes (and ignores trains and flights).
    """
    row = feats.loc[feats["destination_id"] == dest_id].iloc[0]
    origin_id = row["origin_id"] if "origin_id" in feats.columns else "O01"
    f = fares[(fares["destination_id"] == dest_id) & (fares["mode"] == mode)]
    if len(f) and origin_id == "O01":
        r = f.iloc[0]
        return (r["fare_low_inr"] + r["fare_high_inr"]) / 2, "collected"
    return float(rates[mode] * row["road_distance_km"]), "derived"


def room_price(dest_id, tier, accommodation, feats):
    """Nightly room price for the tier. Uses the destination's own listings when it has
    at least ACCOM_MIN_PRICED of them, otherwise the pooled listings of all destinations."""
    acc = _priced(accommodation)
    q = config.ROOM_QUANTILE[tier]
    own = acc[acc["destination_id"] == dest_id]["price"]
    if len(own) >= config.ACCOM_MIN_PRICED:
        return float(own.quantile(q)), "collected", len(own)
    # Fewer than ACCOM_MIN_PRICED priced listings: NOT this destination's own price.
    return float(acc["price"].quantile(q)), "pooled", len(own)


def estimate(dest_id, travellers, nights, tier, mode, data):
    """Line-by-line estimate for one destination. Returns a dict with a DataFrame."""
    feats, fares, acc = data["features"], data["fares"], data["accommodation"]
    rates = derived_rates(fares, feats)
    days = nights + 1
    lines = []

    row = feats.loc[feats["destination_id"] == dest_id].iloc[0]
    origin = row["origin_name"] if "origin_name" in feats.columns else "Pathankot"
    place = row["destination"]
    fare, basis = one_way_fare(dest_id, mode, fares, feats, rates)
    if mode == "taxi":
        cars = math.ceil(travellers / config.PEOPLE_PER_TAXI)
        leg = fare * cars
        note = f"{cars} car(s), one-way fare INR {fare:,.0f}"
    else:
        leg = fare * travellers
        note = f"{travellers} person(s), one-way fare INR {fare:,.0f}"
    if basis == "derived":
        note += f" (rate per km x {row['road_distance_km']:.0f} km; rate comes from short Pathankot routes)"
    lines.append((f"Outward transport: {origin} to {place}", leg, basis, note))
    lines.append((f"Return transport: {place} to {origin}", leg, basis, note))

    price, basis, n_own = room_price(dest_id, tier, acc, feats)
    rooms = math.ceil(travellers / config.PEOPLE_PER_ROOM)
    how = f"{nights} night(s), {rooms} room(s), INR {price:,.0f} per room-night"
    if basis == "pooled":
        how += (f" (ESTIMATE, pooled across all destinations: {place} has only {n_own} priced listing(s), "
                f"fewer than {config.ACCOM_MIN_PRICED}, so this is not a {place}-specific price)")
    lines.append(("Stay", price * rooms * nights, basis, how))

    food = config.FOOD_PER_PERSON_DAY[tier]
    lines.append(("Food", food * travellers * days, "placeholder",
                  f"INR {food:,.0f} per person per day, {days} day(s)"))
    local = config.LOCAL_PER_PERSON_DAY[tier]
    lines.append(("Local travel, entry fees, activities", local * travellers * days,
                  "placeholder", f"INR {local:,.0f} per person per day (no fee data collected)"))

    df = pd.DataFrame(lines, columns=["item", "cost_inr", "basis", "how"])
    total = float(df["cost_inr"].sum())
    data_backed = float(df.loc[df["basis"] != "placeholder", "cost_inr"].sum())
    return {"table": df, "total": total, "per_person": total / travellers,
            "data_backed_share": data_backed / total if total else float("nan")}
