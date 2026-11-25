"""Two-stage content-based recommender: hard filters, then a weighted score.

Not machine learning. Each component is a 0-1 score from a stated rule, the final score
is a weighted mean, and every result carries a plain-language explanation.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import budget as bud
from . import config
from .data_access import effective_drive_hours, month_name, origin_view


@dataclass
class Prefs:
    month: int = 5
    travellers: int = 2
    nights: int = 2
    budget_total: float = 10000.0
    tier: str = "standard"
    mode: str = "taxi"
    max_drive_hours: float = 4.0
    interests: dict = field(default_factory=lambda: {i: 1.0 for i in config.INTERESTS})
    weights: dict = field(default_factory=lambda: dict(config.DEFAULT_WEIGHTS))
    season_method: str = "weather"          # weather | entered | both
    origin_id: str = "O01"                  # starting location (origin_locations.csv): O01 Pathankot, O02 Chandigarh, O03 Delhi


def cosine(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def season_score(dest_id, month, months, feats, method):
    """1 = comfortable by the weather rule, falling to 0 as temperature or rain leave the band."""
    rows = months[(months["destination_id"] == dest_id) & (months["month"] == month)]
    if rows.empty:                       # no weather data collected for this destination
        return None, None
    r = rows.iloc[0]
    penalty = min(1.0, r["temp_gap_c"] / config.SEASON_TEMP_TOL_C
                  + r["rain_excess_mm"] / config.SEASON_RAIN_TOL_MM)
    weather = 1.0 - penalty
    entered = float(r["in_best_months_entered"])
    score = {"weather": weather, "entered": entered, "both": (weather + entered) / 2}[method]
    return score, r


def recommend(prefs, data):
    """Return (ranked DataFrame of passing destinations, DataFrame of excluded ones)."""
    data = origin_view(data, prefs.origin_id)        # distances, drive times and fares follow the selected origin
    feats = effective_drive_hours(data["features"])
    months = data["months"]
    iv = np.array([prefs.interests.get(i, 0.0) for i in config.INTERESTS], float)
    w = prefs.weights
    rows, excluded = [], []

    for _, d in feats.iterrows():
        did, name = d["destination_id"], d["destination"]
        if not d["route_available"]:
            excluded.append({"destination_id": did, "destination": name,
                             "reason": f"no route from {d['origin_name']}: this is your starting city"})
            continue
        est = bud.estimate(did, prefs.travellers, prefs.nights, prefs.tier, prefs.mode, data)
        cost = est["total"]

        reasons = []
        if d["drive_hours"] > prefs.max_drive_hours:
            reasons.append(f"drive about {d['drive_hours']:.1f} h is over your {prefs.max_drive_hours:.1f} h limit")
        if cost > prefs.budget_total:
            reasons.append(f"estimated cost INR {cost:,.0f} is over your budget INR {prefs.budget_total:,.0f}")
        if reasons:
            excluded.append({"destination_id": did, "destination": name, "reason": "; ".join(reasons)})
            continue

        s_int = cosine(iv, d[[f"share_{i}" for i in config.INTERESTS]].values) if iv.sum() else 0.0
        s_sea, mrow = season_score(did, prefs.month, months, feats, prefs.season_method)
        s_bud = max(0.0, 1 - cost / prefs.budget_total)
        s_dis = max(0.0, 1 - d["drive_hours"] / prefs.max_drive_hours)
        comp = {"interest": s_int, "season": s_sea, "budget": s_bud, "distance": s_dis}
        # A component with no data (season, when no weather was collected) is left out and the
        # remaining weights are renormalised; the result carries a warning.
        used = {k: w[k] for k in comp if comp[k] is not None}
        wsum = sum(used.values())
        total = sum(used[k] * comp[k] for k in used) / wsum if wsum else 0.0

        rows.append({"destination_id": did, "destination": name, "score": total,
                     **{f"s_{k}": v for k, v in comp.items()},
                     "est_cost_inr": cost, "drive_hours": d["drive_hours"],
                     "season_category": mrow["category"] if mrow is not None else "no data",
                     "route_quality": d["route_quality"], "origin_name": d["origin_name"],
                     "explanation": explain(prefs, d, comp, mrow, est, w),
                     "warnings": warnings(d, mrow, est, prefs)})

    cols = ["destination_id", "destination", "score", "s_interest", "s_season", "s_budget",
            "s_distance", "est_cost_inr", "drive_hours", "season_category", "route_quality", "origin_name",
            "explanation", "warnings"]
    ranked = pd.DataFrame(rows, columns=cols).sort_values("score", ascending=False).reset_index(drop=True)
    ranked.insert(0, "rank", np.arange(1, len(ranked) + 1))
    return ranked, pd.DataFrame(excluded, columns=["destination_id", "destination", "reason"])


def explain(prefs, d, comp, mrow, est, w):
    used = {k: w[k] for k in comp if comp[k] is not None}
    wsum = sum(used.values()) or 1.0
    contrib = {k: used[k] * comp[k] / wsum for k in used}
    top = sorted(contrib, key=contrib.get, reverse=True)[:2]
    parts = []
    for k in top:
        if k == "interest":
            best = max(config.INTERESTS, key=lambda i: prefs.interests.get(i, 0) * d[f"share_{i}"])
            parts.append(f"interest match {comp[k]:.2f} (strongest shared theme: {best}, "
                         f"{d[f'share_{best}']:.0%} of its listed items)")
        elif k == "season":
            parts.append(f"{month_name(prefs.month)} is {mrow['category']} here "
                         f"(avg max {mrow['avg_temp_max_c']:.0f} C, rain {mrow['rainfall_mm']:.0f} mm), score {comp[k]:.2f}")
        elif k == "budget":
            parts.append(f"estimated cost INR {est['total']:,.0f} leaves {comp[k]:.0%} of your budget unspent")
        else:
            parts.append(f"about {d['drive_hours']:.1f} h drive from {d['origin_name']}, score {comp[k]:.2f}")
    return "Strongest points: " + "; ".join(parts) + "."


def warnings(d, mrow, est, prefs):
    out = []
    if mrow is None:
        out.append("no weather data collected, so season is not scored")
    if d["weather_quality_flag"] not in ("ok", "no_weather_data"):
        out.append(f"weather data flagged '{d['weather_quality_flag']}'")
    if d["drive_time_estimated"]:
        out.append("drive time not entered; estimated from distance")
    if d["route_quality"] == "estimated":
        out.append(f"road distance and drive time from {d['origin_name']} are estimates, not verified")
    if d["origin_id"] == "O01" and d["distance_conflict_flag"] == 1:
        out.append("road distance differs between the source files")
    if mrow is not None and mrow["near_freezing"] == 1:
        out.append("near-freezing nights this month")
    if (est["table"]["basis"] == "pooled").any():
        out.append("stay price is a pooled estimate (too few priced listings for this destination)")
    if est["data_backed_share"] < 0.5:
        out.append(f"only {est['data_backed_share']:.0%} of the cost estimate rests on collected data")
    return "; ".join(out)
