"""Stage 3: origin_locations.csv, route_data.csv and the 21 new destination rows.

Run once from the project root:  python scripts/build_stage3_data.py
Everything that is NOT in a source is labelled. Nothing here is a live route-engine result.

Quality labels in route_data.csv
  author_entered   the author's own Pathankot figures for D01-D09 (sources conflict, see features)
  source_reported  road km copied from a page that states it (URL in route_source); hours are estimates
  estimated        assistant estimate from general knowledge of the road network, rounded,
                   NOT verified against a route engine; treat as +/- 15 %
  not_applicable   origin and destination are the same place
"""
import math
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

ORIGINS = [
    ("O01", "Pathankot", "Punjab", 32.2643, 75.6421),
    ("O02", "Chandigarh", "Chandigarh (UT)", 30.7333, 76.7794),
    ("O03", "Delhi", "Delhi", 28.6139, 77.2090),
]

# id, name, state, ref point, lat, lon, elevation_m, primary_type
NEW_DEST = [
    ("D10", "Bir Billing", "Himachal Pradesh", "Bir village (Billing take-off is above)", 32.0419, 76.7203, 1500, "valley"),
    ("D11", "Palampur", "Himachal Pradesh", "Town centre", 32.1109, 76.5363, 1220, "hill station"),
    ("D12", "Mandi", "Himachal Pradesh", "Town centre (Indira Market)", 31.7088, 76.9320, 800, "historic town"),
    ("D13", "Kullu", "Himachal Pradesh", "Town centre (Dhalpur)", 31.9592, 77.1089, 1280, "valley"),
    ("D14", "Manali", "Himachal Pradesh", "Town centre (Mall Road)", 32.2396, 77.1887, 2050, "hill station"),
    ("D15", "Kasol", "Himachal Pradesh", "Village centre (Parvati Valley)", 32.0100, 77.3150, 1640, "valley"),
    ("D16", "Kasauli", "Himachal Pradesh", "Mall Road", 30.8989, 76.9647, 1900, "hill station"),
    ("D17", "Shimla", "Himachal Pradesh", "The Ridge", 31.1048, 77.1734, 2205, "hill station"),
    ("D18", "Solan", "Himachal Pradesh", "Town centre", 30.9045, 77.0967, 1550, "city"),
    ("D19", "Tirthan Valley", "Himachal Pradesh", "Gushaini (valley base)", 31.6200, 77.3500, 1500, "valley"),
    ("D20", "Spiti Valley", "Himachal Pradesh", "Kaza town (valley headquarters)", 32.2276, 78.0710, 3800, "valley"),
    ("D21", "Chail", "Himachal Pradesh", "Chail village", 30.9667, 77.2000, 2250, "hill station"),
    ("D22", "Patnitop", "Jammu & Kashmir", "Patnitop plateau", 33.0870, 75.3300, 2020, "hill station"),
    ("D23", "Sanasar", "Jammu & Kashmir", "Sanasar village (approximate)", 33.0700, 75.3500, 2080, "hill station"),
    ("D24", "Srinagar", "Jammu & Kashmir", "City centre (Lal Chowk)", 34.0837, 74.7973, 1585, "city"),
    ("D25", "Pahalgam", "Jammu & Kashmir", "Town centre", 34.0161, 75.3150, 2200, "hill station"),
    ("D26", "Anandpur Sahib", "Punjab", "Takht Sri Kesgarh Sahib", 31.2393, 76.5003, 300, "pilgrimage"),
    ("D27", "Chandigarh", "Chandigarh (UT)", "Sector 17 city centre", 30.7333, 76.7794, 321, "city"),
    ("D28", "Ranjit Sagar Lake", "Punjab", "Ranjit Sagar Dam, Shahpur Kandi (approximate)", 32.4450, 75.7170, 430, "lake"),
    ("D29", "Jibhi", "Himachal Pradesh", "Jibhi village (Seraj valley)", 31.5951, 77.3552, 1550, "valley"),
    ("D30", "Barot Valley", "Himachal Pradesh", "Barot village (Uhl river)", 32.0467, 76.8052, 1830, "valley"),
]

DEST_NOTE = ("Added in the 30-destination expansion. Latitude, longitude and elevation are approximate "
             "values from the assistant's general knowledge, rounded, NOT taken from a cited page: verify "
             "against OpenStreetMap or an official source. road_distance_km, travel_time_hrs, rating, "
             "recommended days and best_months are blank on purpose (road data lives in route_data.csv; "
             "the others were not sourced).")

# (road_km, drive_hours, quality, route_source note)   keys: (origin, dest)
E = "estimated"; S = "source_reported"
GEN = "Assistant estimate from general knowledge of the road network; not verified against a route engine."
R = {}
def add(o, rows):
    for d, km, hrs, q, src in rows:
        R[(o, d)] = (km, hrs, q, src or GEN)

add("O01", [  # Pathankot -> new destinations
    ("D10", 135, 3.5, E, ""), ("D11", 125, 3.25, E, ""), ("D12", 215, 6.0, E, ""), ("D13", 290, 8.5, E, ""),
    ("D14", 330, 10.0, E, ""), ("D15", 310, 10.0, E, ""), ("D16", 290, 6.5, E, ""), ("D17", 320, 8.0, E, ""),
    ("D18", 270, 6.5, E, ""), ("D19", 300, 9.0, E, ""), ("D20", 530, 18.0, E, GEN + " Spiti roads are seasonal; not modelled."),
    ("D21", 320, 8.0, E, ""), ("D22", 215, 6.0, E, ""), ("D23", 230, 6.5, E, ""), ("D24", 370, 10.5, E, ""),
    ("D25", 465, 13.5, E, ""),
    ("D26", 165, 4.0, E, ""),
    ("D27", 246, 5.0, S, "Chandigarh Tourism how-to-reach page states Chandigarh-Pathankot 246 km: https://chandigarhtourism.gov.in/pages/fullpage/how_to_reach . Hours estimated."),
    ("D28", 30, 1.0, S, "Punjab Wildlife dept and Pathankot district pages state about 30 km: https://pathankot.nic.in/tourist-places/ . Hours estimated."),
    ("D29", 315, 9.5, E, ""), ("D30", 220, 6.5, E, ""),
])
add("O02", [  # Chandigarh -> all
    ("D01", 250, 6.5, E, ""), ("D02", 260, 7.0, E, ""), ("D03", 330, 8.5, E, ""), ("D04", 345, 9.0, E, ""),
    ("D05", 355, 9.5, E, ""), ("D06", 230, 5.5, E, ""), ("D07", 230, 4.5, E, ""), ("D08", 350, 7.5, E, ""),
    ("D09", 400, 8.5, E, ""),
    ("D10", 270, 7.0, E, ""), ("D11", 245, 6.5, E, ""),
    ("D12", 200, 5.5, E, GEN + " Wikipedia states both 163 km and 200 km (bus 6 h, taxi 5 h); 200 km used: https://en.wikipedia.org/wiki/Mandi,_Himachal_Pradesh"),
    ("D13", 260, 7.0, S, "Himachal Tourism distance table: https://himachaltourism.gov.in/destination/kullu-2/ . Hours estimated."),
    ("D14", 300, 8.5, S, "Himachal Tourism distance table: https://himachaltourism.gov.in/destination/manali/ . Hours estimated."),
    ("D15", 280, 8.5, E, ""),
    ("D16", 60, 2.0, S, "Incredible India: about 60 km, roughly two hours: https://www.incredibleindia.gov.in/en/himachal-pradesh/kasauli"),
    ("D17", 115, 3.5, E, ""),
    ("D18", 67, 1.75, S, "Himachal Tourism Solan page lists 67 km: https://himachaltourism.gov.in/destination/solan/ . Hours estimated."),
    ("D19", 270, 8.0, E, ""),
    ("D20", 500, 17.0, E, GEN + " Spiti roads are seasonal; not modelled."),
    ("D21", 105, 3.0, E, ""), ("D22", 460, 10.0, E, ""), ("D23", 475, 10.5, E, ""), ("D24", 620, 14.0, E, ""),
    ("D25", 715, 16.5, E, ""),
    ("D26", 80, 2.0, S, "Outlook Traveller (May 2015): nearest airport Chandigarh, about 80 km / 2 h; measured from the airport, not the city centre: https://www.outlooktraveller.com/amp/story/destinations/india/quick-guide-anandpur-sahib-punjab"),
    ("D28", 276, 5.5, E, ""), ("D29", 280, 8.5, E, ""), ("D30", 275, 8.0, E, ""),
])
add("O03", [  # Delhi -> all
    ("D01", 480, 10.5, E, ""), ("D02", 490, 11.0, E, ""), ("D03", 555, 11.5, E, ""), ("D04", 570, 12.0, E, ""),
    ("D05", 580, 12.5, E, ""), ("D06", 470, 9.5, E, ""), ("D07", 450, 8.0, E, ""), ("D08", 585, 10.5, E, ""),
    ("D09", 640, 12.0, E, ""),
    ("D10", 520, 11.5, E, ""), ("D11", 500, 10.5, E, ""),
    ("D12", 430, 9.5, E, GEN + " Wikipedia states both 395 km and 475 km; neither used: https://en.wikipedia.org/wiki/Mandi,_Himachal_Pradesh"),
    ("D13", 495, 11.0, S, "Himachal Tourism lists 495 km (district page says 497): https://himachaltourism.gov.in/destination/kullu-2/ . Hours estimated."),
    ("D14", 530, 12.0, S, "Himachal Tourism distance table lists 530 km (its transport text says about 550): https://himachaltourism.gov.in/destination/manali/ . Hours estimated."),
    ("D15", 520, 12.0, E, ""), ("D16", 290, 6.0, E, ""), ("D17", 345, 7.5, E, ""),
    ("D18", 300, 6.5, S, "Himachal Tourism Solan page lists 300 km: https://himachaltourism.gov.in/destination/solan/ . Hours estimated."),
    ("D19", 480, 11.0, S, "Great Himalayan National Park page: about 480 km, 10-12 h (to the park area, not Gushaini exactly): https://greathimalayannationalpark.org/?p=43 . Hours = midpoint of stated range."),
    ("D20", 740, 26.0, E, GEN + " Spiti roads are seasonal; not modelled."),
    ("D21", 330, 7.0, E, ""), ("D22", 690, 13.5, E, ""), ("D23", 705, 14.0, E, ""), ("D24", 870, 18.0, E, ""),
    ("D25", 960, 21.0, E, ""),
    ("D26", 318, 6.0, S, "Outlook Traveller (May 2015, older source): https://www.outlooktraveller.com/amp/story/destinations/india/quick-guide-anandpur-sahib-punjab . Hours estimated."),
    ("D27", 248, 5.0, S, "Chandigarh Tourism how-to-reach page: https://chandigarhtourism.gov.in/pages/fullpage/how_to_reach . Hours estimated."),
    ("D28", 495, 9.0, E, ""), ("D29", 495, 11.5, E, ""), ("D30", 520, 12.5, E, ""),
])


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(a))


def parse_hmm(v):
    from src.load import parse_hmm as p
    return p(str(v)) if pd.notna(v) else float("nan")


def main():
    import sys
    sys.path.insert(0, str(RAW.parents[1]))
    # origins
    pd.DataFrame(ORIGINS, columns=["origin_id", "origin_name", "state", "latitude", "longitude"]).assign(
        data_notes="Approximate city-centre coordinates, assistant general knowledge, not from a cited page."
    ).to_csv(RAW / "origin_locations.csv", index=False, encoding="utf-8")

    # destinations (append, never overwrite existing rows)
    from scripts.csv_append import append_rows
    existing = pd.read_csv(RAW / "destinations.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if len(existing) == 9:
        new = pd.DataFrame(NEW_DEST, columns=["destination_id", "destination", "state", "reference_point",
                                              "latitude", "longitude", "elevation_m", "primary_type"])
        new["data_notes"] = DEST_NOTE
        append_rows(RAW / "destinations.csv", new, key="destination_id")
    dest = pd.read_csv(RAW / "destinations.csv", encoding="utf-8-sig", dtype={"travel_time_hrs": str, "best_months": str})

    # route rows for Pathankot -> D01-D09 come from the author's entries
    legacy = dest[dest.destination_id <= "D09"].set_index("destination_id")
    for d, r in legacy.iterrows():
        hrs = parse_hmm(r.travel_time_hrs)
        note = "Author-entered road km and drive time (H.MM). Three sources conflict for this destination; see features."
        if pd.isna(hrs):
            note += " Drive time entered as an invalid H.MM value, so it is left blank."
        R[("O01", d)] = (float(r.road_distance_km), hrs, "author_entered", note)

    rows = []
    n = 0
    for o_id, o_name, _, o_lat, o_lon in ORIGINS:
        for _, d in dest.iterrows():
            n += 1
            sl = round(haversine(o_lat, o_lon, d.latitude, d.longitude), 1)
            base = {"route_id": f"R{n:03d}", "origin_id": o_id, "origin_name": o_name,
                    "destination_id": d.destination_id, "destination": d.destination,
                    "straight_line_distance_km": sl}
            if o_id == "O02" and d.destination_id == "D27":
                rows.append({**base, "straight_line_distance_km": 0.0, "road_distance_km": None,
                             "estimated_drive_hours": None, "route_source": "Origin and destination are the same city; "
                             "Chandigarh as a destination is not offered when it is the starting point.",
                             "last_verified": None, "data_quality": "not_applicable", "drive_hours_basis": "not_applicable"})
                continue
            km, hrs, q, src = R[(o_id, d.destination_id)]
            rows.append({**base, "road_distance_km": km, "estimated_drive_hours": None if pd.isna(hrs) else hrs,
                         "route_source": src, "last_verified": "2026-11-22" if q == "source_reported" else None,
                         "data_quality": q,
                         "drive_hours_basis": "author_entered" if q == "author_entered" and pd.notna(hrs) else
                         ("not_available" if pd.isna(hrs) else "estimated")})
    rd = pd.DataFrame(rows)
    rd.to_csv(RAW / "route_data.csv", index=False, encoding="utf-8")
    print(rd.data_quality.value_counts().to_string(), len(rd))


if __name__ == "__main__":
    main()
