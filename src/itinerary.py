"""Rule-based itinerary: packs collected attractions and activities into days.

Greedy packing in order of the user's interest weights, at most SIGHTSEEING_MIN_PER_DAY
minutes per day. Durations come from the raw tables (attraction visit time, activity
duration text). Items with no parseable duration are listed separately, not guessed.
"""
import re

import numpy as np
import pandas as pd

from . import config
from .features import activity_interests, attraction_interests


def parse_duration_min(text):
    """'~1-2 hours' -> 90, '~30-60 min' -> 45, '~4 hours one way' -> 480 (return). None if unreadable."""
    if not isinstance(text, str):
        return None
    t = text.replace("–", "-").replace("—", "-").lower()
    m = re.search(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*(hour|hr|min)", t)
    if not m:
        return None
    lo = float(m.group(1))
    hi = float(m.group(2)) if m.group(2) else lo
    mid = (lo + hi) / 2
    minutes = mid * (60 if m.group(3) in ("hour", "hr") else 1)
    return minutes * 2 if "one way" in t else minutes   # return trip


def candidate_items(dest_id, data):
    a = data["attractions"]; b = data["activities"]
    items = []
    for _, r in a[a["destination_id"] == dest_id].iterrows():
        items.append({"name": r["attraction_name"], "kind": "attraction",
                      "minutes": pd.to_numeric(r["visit_time_min_estimate"], errors="coerce"),
                      "interests": attraction_interests(r["attraction_type"])})
    for _, r in b[b["destination_id"] == dest_id].iterrows():
        mins = parse_duration_min(r["estimated_duration"])
        items.append({"name": r["activity_name"], "kind": "activity",
                      "minutes": np.nan if mins is None else mins,
                      "interests": activity_interests(r["activity_type"])})
    return items


def build(dest_id, days, interest_weights, data, drive_hours=None):
    """Return (days list, unscheduled list). Each day is a list of item dicts."""
    items = candidate_items(dest_id, data)
    def relevance(it):
        return sum(interest_weights.get(i, 0) for i in it["interests"]) / max(1, len(it["interests"]))
    known = [i for i in items if pd.notna(i["minutes"])]
    unknown = [i for i in items if pd.isna(i["minutes"])]
    known.sort(key=lambda i: (-relevance(i), i["minutes"]))

    plan = [[] for _ in range(days)]
    used = [0.0] * days
    left = []
    cap = config.SIGHTSEEING_MIN_PER_DAY
    for it in known:
        placed = False
        for d in range(days):
            if used[d] + it["minutes"] <= cap or not plan[d]:
                plan[d].append(it); used[d] += it["minutes"]; placed = True
                break
        if not placed:
            left.append(it)
    return plan, left + unknown, used
