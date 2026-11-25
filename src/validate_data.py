"""Data validation for the 30-destination, 3-origin dataset.

Run:  python -m src.validate_data      (exit code 1 if any check fails)
Each check returns (name, passed, detail).
"""
import sys

import pandas as pd

from . import config
from .load import read_csv


def _tables():
    t = {n: read_csv(f"{n}.csv") for n in
         ["destinations", "weather", "attractions", "activities", "accommodation", "transportation",
          "origin_locations", "route_data", "source_log"]}
    try:
        t["accommodation_coverage"] = read_csv("accommodation_coverage.csv")
    except FileNotFoundError:
        t["accommodation_coverage"] = pd.DataFrame(columns=["destination_id", "coverage_status"])
    return t


def run_checks(t=None):
    t = t or _tables()
    d, w = t["destinations"], t["weather"]
    ids = set(d.destination_id)
    out = []
    add = lambda name, ok, detail="": out.append((name, bool(ok), detail))

    add("1. exactly 30 unique destination IDs", d.destination_id.nunique() == 30 and len(d) == 30, f"{d.destination_id.nunique()} unique, {len(d)} rows")
    add("2. no duplicate destination IDs or names", d.destination_id.is_unique and d.destination.str.lower().is_unique)
    expected = [f"D{i:02d}" for i in range(1, 31)]
    add("   IDs are D01..D30 in sequence", list(d.destination_id) == expected)
    lat, lon = pd.to_numeric(d.latitude, errors="coerce"), pd.to_numeric(d.longitude, errors="coerce")
    add("3. valid latitude/longitude (India bounding box)",
        lat.between(6, 38).all() and lon.between(68, 98).all(), "")
    add("4. every destination has a state", d.state.fillna("").str.strip().ne("").all())
    wc = w.groupby("destination_id").size()
    with_weather = set(wc.index)
    add("5a. weather: 12 monthly rows for every destination that has weather", (wc == 12).all(), f"{len(wc)} destinations")
    add("5b. weather: every destination has weather", with_weather == ids,
        "missing: " + ", ".join(sorted(ids - with_weather)) if with_weather != ids else "")
    add("5c. weather months are 1-12 with no duplicates", not w.duplicated(["destination_id", "month"]).any()
        and w.month.between(1, 12).all())
    add("5d. weather values plausible (min<=max, rain>=0)",
        (w.avg_temp_min_c <= w.avg_temp_max_c).all() and (w.rainfall_mm >= 0).all())
    add("6. attractions reference existing destinations", set(t["attractions"].destination_id) <= ids)
    add("6b. every destination has attractions", set(t["attractions"].destination_id) == ids)
    add("7. activities reference existing destinations", set(t["activities"].destination_id) <= ids)
    add("7b. every destination has activities", set(t["activities"].destination_id) == ids)
    add("8. accommodation references existing destinations", set(t["accommodation"].destination_id) <= ids)
    # A destination with no listing must be declared in accommodation_coverage.csv
    # (status "no_collected_listings") so a gap is a documented decision, not an accident.
    cov = t.get("accommodation_coverage", pd.DataFrame(columns=["destination_id", "coverage_status"]))
    declared = set(cov.loc[cov.coverage_status == "no_collected_listings", "destination_id"])
    has_rows = set(t["accommodation"].destination_id)
    undeclared = ids - has_rows - declared
    contradictory = declared & has_rows
    add("8b. every destination has accommodation rows or is declared 'no_collected_listings'",
        not undeclared and not contradictory and declared <= ids,
        ("undeclared gap: " + ", ".join(sorted(undeclared)) if undeclared else "")
        + ("; declared but has rows: " + ", ".join(sorted(contradictory)) if contradictory else "")
        or (f"declared no listings: {', '.join(sorted(declared))}" if declared else ""))
    add("9. transportation references existing destinations", set(t["transportation"].destination_id) <= ids)
    add("9b. every destination has a transportation row", set(t["transportation"].destination_id) == ids)

    r, o = t["route_data"], t["origin_locations"]
    add("origins: exactly O01, O02, O03", list(o.origin_id) == ["O01", "O02", "O03"]
        and list(o.origin_name) == ["Pathankot", "Chandigarh", "Delhi"])
    combos = set(zip(r.origin_id, r.destination_id))
    full = {(x, y) for x in o.origin_id for y in ids}
    add("10. all 90 origin-destination routes present", len(r) == 90 and combos == full and r.route_id.is_unique, f"{len(r)} rows")
    quality = {"author_entered", "source_reported", "estimated", "not_applicable", "unavailable"}
    add("    route data_quality is a known label", set(r.data_quality) <= quality, str(sorted(set(r.data_quality))))
    road = pd.to_numeric(r.road_distance_km, errors="coerce")
    straight = pd.to_numeric(r.straight_line_distance_km, errors="coerce")
    has = road.notna()
    add("    road km >= straight-line km wherever a road km exists", (road[has] >= straight[has]).all())
    add("    every route without a road km is marked not_applicable/unavailable",
        r.loc[~has, "data_quality"].isin(["not_applicable", "unavailable"]).all())
    add("    estimates are never dated 'last_verified'", r.loc[r.data_quality == "estimated", "last_verified"].isna().all())

    num_ok = True
    for tbl, cols in [("destinations", ["latitude", "longitude", "elevation_m"]), ("weather", ["avg_temp_min_c", "avg_temp_max_c", "rainfall_mm"]),
                      ("route_data", ["straight_line_distance_km"])]:
        for c in cols:
            num_ok &= pd.to_numeric(t[tbl][c], errors="coerce").notna().all()
    add("11. numeric columns parse (no stray text)", num_ok)
    keys = {"attractions": "attraction_id", "activities": "activity_id", "accommodation": "accommodation_id",
            "transportation": "transport_id"}
    add("12. IDs unique in every table", all(t[k][c].is_unique for k, c in keys.items()))
    dupes = {k: int(t[k].duplicated([c for c in t[k].columns if c != keys[k]]).sum()) for k in keys}
    add("13. no accidental duplicate records", sum(dupes.values()) == 0, str(dupes))
    return out


def main():
    results = run_checks()
    for name, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
