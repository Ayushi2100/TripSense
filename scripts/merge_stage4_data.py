"""Stage 4: merge the sourced batches in data/_stage4_collected_batches into the raw tables.

Appends only. IDs are assigned here. Items removed as duplicates of a neighbouring
destination are listed in REMOVE with the reason.
Run once from the project root:  python -m scripts.merge_stage4_data
"""
from pathlib import Path

import pandas as pd

from scripts.csv_append import append_rows

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BATCH = ROOT / "data" / "_stage4_collected_batches"
GROUPS = ["g1", "g2", "g3"]

# (table, destination_id, name column value, reason)
REMOVE = [
    ("attractions", "D10", "Andretta village", "Andretta is kept under Palampur (D11), which it is closer to"),
    ("attractions", "D29", "Great Himalayan National Park", "belongs to Tirthan Valley (D19); Jibhi is only a neighbouring base"),
    ("activities", "D12", "Barot Valley trout fishing and camping", "Barot Valley is its own destination (D30)"),
    ("activities", "D29", "Trekking in Great Himalayan National Park", "belongs to Tirthan Valley (D19)"),
]
SHARED_NOTE = ("Also listed for the neighbouring destination (Tirthan Valley D19 / Jibhi D29) because it "
               "genuinely lies between them.")
SHARED = {("D19", "Serolsar Lake"), ("D29", "Serolsar Lake"), ("D19", "Jalori Pass"), ("D29", "Jalori Pass")}


def load(table):
    return pd.concat([pd.read_csv(BATCH / f"{table}_{g}.csv", dtype=str, keep_default_na=False) for g in GROUPS],
                     ignore_index=True)


def next_ids(path, col, prefix, n, width):
    last = pd.read_csv(path, dtype=str, encoding="utf-8-sig")[col].iloc[-1]
    start = int(last[len(prefix):]) + 1
    return [f"{prefix}{i:0{width}d}" for i in range(start, start + n)]


def main():
    # weather
    w = load("weather")
    assert w.groupby("destination_id").size().eq(12).all()
    print("weather", append_rows(RAW / "weather.csv", w))

    # attractions
    a = load("attractions")
    name_col = {"attractions": "attraction_name", "activities": "activity_name"}
    for t, d, n, why in REMOVE:
        if t == "attractions":
            mask = (a.destination_id == d) & (a[name_col[t]] == n)
            assert mask.sum() == 1, (d, n)
            a = a[~mask]
    for i, r in a.iterrows():
        if (r.destination_id, r.attraction_name) in SHARED:
            a.loc[i, "data_notes"] = (r.data_notes + " " + SHARED_NOTE).strip()
    a["attraction_id"] = next_ids(RAW / "attractions.csv", "attraction_id", "A", len(a), 3)
    print("attractions", append_rows(RAW / "attractions.csv", a, key="attraction_id"))

    # activities
    b = load("activities")
    for t, d, n, why in REMOVE:
        if t == "activities":
            mask = (b.destination_id == d) & (b[name_col[t]] == n)
            assert mask.sum() == 1, (d, n)
            b = b[~mask]
    b["activity_id"] = next_ids(RAW / "activities.csv", "activity_id", "A", len(b), 3)
    print("activities", append_rows(RAW / "activities.csv", b, key="activity_id"))

    # accommodation
    c = load("accommodation")
    c["accommodation_id"] = next_ids(RAW / "accommodation.csv", "accommodation_id", "AC", len(c), 3)
    print("accommodation", append_rows(RAW / "accommodation.csv", c, key="accommodation_id"))

    # transportation
    t = load("transportation")
    t["transport_id"] = next_ids(RAW / "transportation.csv", "transport_id", "T", len(t), 2)
    print("transportation", append_rows(RAW / "transportation.csv", t, key="transport_id"))

    # source log (raw copy uses DD-MM-YYYY dates, the top-level copy uses ISO)
    s = load("source_log")
    extra = []
    dest = pd.read_csv(RAW / "destinations.csv", dtype=str, encoding="utf-8-sig")
    for _, d in dest[dest.destination_id > "D09"].iterrows():
        for col in ["latitude", "longitude", "elevation_m"]:
            extra.append({"destination_id": d.destination_id, "column_name": col,
                          "source": "Assistant general knowledge (approximate, not from a cited page)", "url": "",
                          "date_collected": "2026-11-22", "is_estimate": "TRUE",
                          "notes": "Verify against OpenStreetMap or an official source"})
        extra.append({"destination_id": d.destination_id, "column_name": "primary_type",
                      "source": "Assistant classification", "url": "", "date_collected": "2026-11-22",
                      "is_estimate": "TRUE", "notes": "One of: hill station, historic town, city, pilgrimage, valley, lake"})
    for o in ["O01", "O02", "O03"]:
        extra.append({"destination_id": o, "column_name": "origin_locations",
                      "source": "Assistant general knowledge (approximate city-centre coordinates)", "url": "",
                      "date_collected": "2026-11-22", "is_estimate": "TRUE", "notes": "data/raw/origin_locations.csv"})
    extra.append({"destination_id": "ALL", "column_name": "route_data",
                  "source": "See route_source and data_quality columns in route_data.csv", "url": "",
                  "date_collected": "2026-11-22", "is_estimate": "TRUE",
                  "notes": "67 of 90 routes are estimates; 13 copy a source-stated road km; 9 are the author's own Pathankot entries"})
    s = pd.concat([s, pd.DataFrame(extra)], ignore_index=True)
    iso = s.copy()
    print("source_log (top level)", append_rows(ROOT / "data" / "source_log.csv", iso))
    s["date_collected"] = pd.to_datetime(s["date_collected"]).dt.strftime("%d-%m-%Y")
    print("source_log (raw)", append_rows(RAW / "source_log.csv", s))


if __name__ == "__main__":
    main()
