"""Stage 6 (run once): coordinate/elevation verification notes, three best_months values,
destinations_clean.csv extended to 30 rows, straight-line distances refreshed for moved points.

Sources were fetched on 23/24-11-2026; each decision is written to destinations.data_notes and source_log.csv.
"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from scripts.csv_append import append_rows

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
RAW_DATE, ISO_DATE = "24-11-2026", "2026-11-24"
WP = "https://en.wikipedia.org/wiki/"

# id: (decision, note, source label, url, new_lat, new_lon, new_elev)
V = {
 "D10": ("kept", "Wikipedia Bir village infobox: 32.05N 76.70E (arc-minute rounded), 1,525 m. Point is Bir village, not the higher Billing launch site.", "Wikipedia: Bir, Himachal Pradesh", WP + "Bir,_Himachal_Pradesh"),
 "D11": ("kept", "Wikipedia infobox: 32.109722N 76.536641E, 1,256 m (lead text says about 1,300 m). Entered 1,220 m is 36 m lower, within tolerance.", "Wikipedia: Palampur, Himachal Pradesh", WP + "Palampur,_Himachal_Pradesh"),
 "D12": ("kept", "Wikipedia infobox: 31.70694N 76.93167E, 760 m (the page elsewhere says 764 m and 880 m).", "Wikipedia: Mandi, Himachal Pradesh", WP + "Mandi,_Himachal_Pradesh"),
 "D13": ("kept", "Wikipedia infobox: 31.95N 77.11E, 1,279 m.", "Wikipedia: Kullu", WP + "Kullu"),
 "D14": ("kept", "Wikipedia infobox: 32.243177N 77.189246E, 2,050 m.", "Wikipedia: Manali, Himachal Pradesh", WP + "Manali,_Himachal_Pradesh"),
 "D15": ("kept", "Wikipedia infobox: 32.00972N 77.31528E, 1,580 m. Entered 1,640 m is 60 m higher, within tolerance.", "Wikipedia: Kasol", WP + "Kasol"),
 "D16": ("kept", "Wikipedia: 30.9N 76.96E, 1,800 m. GeoNames: 30.89856N 76.96587E, about 1,858 m (SRTM/ASTER model value). Entered 1,900 m is 42-100 m higher, kept as approximate.", "Wikipedia: Kasauli; GeoNames 1267605", WP + "Kasauli"),
 "D17": ("kept", "Coordinates agree (GeoNames 31.10442N 77.16662E). Elevation sources conflict: GeoNames model 2,073 m, Wikipedia lead about 2,200 m, Wikipedia infobox 2,276 m, Shimla Municipal Corporation mean 2,397.59 m. Entered 2,205 m sits inside that range, kept.", "GeoNames 1256237; Shimla Municipal Corporation", "https://www.geonames.org/1256237"),
 "D18": ("kept", "Wikipedia infobox: 30.907985N 77.098403E, 1,550 m.", "Wikipedia: Solan", WP + "Solan"),
 "D19": ("unverified", "No coordinates found for Tirthan Valley or Gushaini in any fetched source. NativePlanet gives Gushaini about 4,500 ft (about 1,370 m), 130 m below the entered 1,500 m. Values stay approximate and UNVERIFIED.", "NativePlanet: Gushaini", "https://www.nativeplanet.com/gushaini"),
 "D20": ("changed", "Wikipedia (Kaza, the Spiti headquarters) 32.22556N 78.07139E agrees with the entered point, so the point is Kaza. Elevation changed 3,800 m to 3,650 m.", "Wikipedia: Kaza, Himachal Pradesh", WP + "Kaza,_Himachal_Pradesh", None, None, 3650),
 "D21": ("kept", "Wikipedia infobox: 30.9697N 77.1975E, 2,250 m.", "Wikipedia: Chail, Himachal Pradesh", WP + "Chail,_Himachal_Pradesh"),
 "D22": ("kept", "Wikipedia infobox: 33.09028N 75.32639E, 2,024 m.", "Wikipedia: Patnitop", WP + "Patnitop"),
 "D23": ("changed", "Wikipedia: 33.125N 75.260E (rounded to the arc-minute), 2,050 m. Incredible India (Ministry of Tourism) and JKTDC both say 2,050 m and JKTDC places it west of Patnitop. Entered 33.07N 75.35E was east of Patnitop and unsourced, so coordinates and elevation were replaced. Precision is only about 1-2 km.", "Wikipedia: Sanasar; Incredible India; JKTDC", WP + "Sanasar", 33.125, 75.26, 2050),
 "D24": ("kept", "Wikipedia infobox: 34.09N 74.79E, 1,585 m. GeoNames: 34.08333N 74.83333E, about 1,584 m.", "Wikipedia: Srinagar; GeoNames 1255639", WP + "Srinagar"),
 "D25": ("kept", "Elevation agrees (Wikipedia 2,200 m). Longitude CONFLICT: Wikipedia infobox and latitude.to give 75.19E, bamwor.com gives 75.319E, entered 75.315E. No authoritative source settled it, so the entered value is kept and flagged.", "Wikipedia: Pahalgam; bamwor.com", WP + "Pahalgam"),
 "D26": ("kept", "Wikipedia infobox: 31.234961N 76.498808E, 311 m.", "Wikipedia: Anandpur Sahib", WP + "Anandpur_Sahib"),
 "D27": ("kept", "Wikipedia (2022 copy): 30.74N 76.79E, average elevation 321 m.", "Wikipedia: Chandigarh", WP + "Chandigarh"),
 "D28": ("changed", "Reference point is the lake. Wikipedia and the Punjab Irrigation Department give the normal reservoir level as 527.9 m, so elevation changed 430 m to 528 m. Dam coordinates on Wikipedia (32.4425N 75.7286E) are about 1 km from the entered point, so coordinates are kept.", "Wikipedia: Ranjit Sagar Dam; Punjab Irrigation Dept", WP + "Ranjit_Sagar_Dam", None, None, 528),
 "D29": ("unverified", "No reliable source. A pincode site gives 31.633N 77.350E (entered 31.5951N 77.3552E) and HP Eco-tourism says 1,900 m (entered 1,550 m); neither was corroborated, so the entered values are kept and UNVERIFIED.", "indiamapia.com; HP Eco-tourism", "https://himachalecotourism.hp.gov.in/Jibhi"),
 "D30": ("changed", "Wikipedia infobox: 32.03639N 76.84750E, 1,829 m (body text 1,819 m); HP Eco-tourism 1,835 m. Entered longitude was 4 km west, so latitude and longitude were replaced; elevation 1,830 m kept.", "Wikipedia: Barot, Himachal Pradesh; HP Eco-tourism", WP + "Barot,_Himachal_Pradesh", 32.03639, 76.8475, None),
}
BM = {
 "D24": ("4,5,6,7,8,9,10", "Holidify", "https://www.holidify.com/places/srinagar/best-time-to-visit.html", "April to October is the best time to visit Srinagar"),
 "D25": ("3,4,5,6,7,8,9,10,11", "Holidify", "https://www.holidify.com/places/pahalgam/best-time-to-visit.html", "The best time to visit Pahalgam is from March to November."),
 "D28": ("8,9", "OYO travel guide", "https://oyorooms.com/travel-guide/ranjit-sagar-dam-travel-guide", "It is best to visit the dam during August or September when the lake is full and the scenery is at its best."),
}
D30_NOTE = ("best_months left blank: the only page found (TravelTriangle) says Barot 'can be visited at any time of the year except for monsoons' "
            "without naming months, and monsoon months are not stated there.")


def hav(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(h))


p = RAW / "destinations.csv"
d = pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")
log = []
for did, v in V.items():
    m = d.destination_id == did
    dec, note, src, url = v[:4]
    old = (d.loc[m, "latitude"].iloc[0], d.loc[m, "longitude"].iloc[0], d.loc[m, "elevation_m"].iloc[0])
    if dec == "changed":
        la, lo, el = v[4:7]
        if la is not None:
            d.loc[m, "latitude"], d.loc[m, "longitude"] = str(la), str(lo)
        if el is not None:
            d.loc[m, "elevation_m"] = str(el)
    status = {"kept": "Checked 24-11-2026, entered values kept", "changed": f"Checked 24-11-2026, CHANGED (was {old[0]}, {old[1]}, {old[2]} m)",
              "unverified": "Checked 24-11-2026, could NOT be verified"}[dec]
    d.loc[m, "data_notes"] += f" Coordinate check: {status}. {note} Source: {url}"
    log.append(dict(destination_id=did, column_name="latitude/longitude/elevation_m", source=src, url=url,
                    date_collected=RAW_DATE, is_estimate="TRUE" if dec == "unverified" else "FALSE", notes=f"{status}. {note}"))
for did, (months, src, url, quote) in BM.items():
    m = d.destination_id == did
    assert d.loc[m, "best_months"].iloc[0] == ""
    d.loc[m, "best_months"] = months
    d.loc[m, "data_notes"] += f' best_months added 24-11-2026 from {src}: "{quote}" (page-stated, not verified against weather).'
    log.append(dict(destination_id=did, column_name="best_months", source=src, url=url, date_collected=RAW_DATE,
                    is_estimate="FALSE", notes=f"Page-stated: {quote}"))
m = d.destination_id == "D30"
d.loc[m, "data_notes"] += " " + D30_NOTE
log.append(dict(destination_id="D30", column_name="best_months", source="TravelTriangle Barot Valley guide".replace("Tt", "T"),
                url="https://traveltriangle.com/blog/barot-valley/", date_collected=RAW_DATE, is_estimate="FALSE",
                notes="Left blank: " + D30_NOTE))
d.to_csv(p, index=False, encoding="utf-8-sig", lineterminator="\n")

# straight-line distances for points that moved (D23, D30), same rounding as build_stage3_data.py
oc = pd.read_csv(RAW / "origin_locations.csv", dtype=str, encoding="utf-8-sig")
rp = RAW / "route_data.csv"
rt = pd.read_csv(rp, dtype=str, keep_default_na=False, encoding="utf-8-sig")
print(oc.columns.tolist())
for did in ["D23", "D30"]:
    row = d[d.destination_id == did].iloc[0]
    for i in rt.index[rt.destination_id == did]:
        o = oc[oc.origin_id == rt.at[i, "origin_id"]].iloc[0]
        old = rt.at[i, "straight_line_distance_km"]
        new = round(hav(float(o.latitude), float(o.longitude), float(row.latitude), float(row.longitude)), 1)
        rt.at[i, "straight_line_distance_km"] = str(new)
        print(did, rt.at[i, "origin_name"], old, "->", new, "road", rt.at[i, "road_distance_km"])
rt.to_csv(rp, index=False, encoding="utf-8-sig", lineterminator="\n")

# destinations_clean.csv (raw and processed): append D10-D30, D01-D09 rows untouched
new = d.iloc[9:].copy()
new["road_distance_km"] = ""
new["travel_time_hrs"] = ""
new["best_months"] = new["best_months"].str.replace(",", "|")
new["data_notes"] = "Added in the 30-destination expansion; mirrors destinations.csv. Road km and time are blank on purpose (see route_data.csv)."
for path in [RAW / "destinations_clean.csv", PROC / "destinations_clean.csv"]:
    print(path, append_rows(path, new.to_dict("records"), key="destination_id"))

log.append(dict(destination_id="D10-D30", column_name="destinations_clean.csv", source="Project", url="", date_collected=RAW_DATE,
                is_estimate="FALSE", notes="destinations_clean.csv (raw and processed) extended from 9 to 30 rows"))
for path, iso in [(RAW / "source_log.csv", False), (ROOT / "data" / "source_log.csv", True)]:
    rows = [dict(x, date_collected=ISO_DATE) if iso else x for x in log]
    print(path.name, append_rows(path, rows))
