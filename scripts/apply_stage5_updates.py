"""Stage 5: accommodation, best_months and route-source updates (run once; inputs in data/_stage5_collected)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from scripts.csv_append import append_rows

ROOT = Path(__file__).resolve().parents[1]
RAW, COL = ROOT / "data" / "raw", ROOT / "data" / "_stage5_collected"
TODAY_RAW, TODAY_ISO = "23-11-2026", "2026-11-23"

# 1. accommodation (D28 excluded: only Pathankot city hotels with mixed/unknown years were found, not lakeside stays)
acc = pd.read_csv(COL / "acc_new.csv", dtype=str, keep_default_na=False)
acc = acc[acc.destination_id != "D28"].copy()
n0 = len(pd.read_csv(RAW / "accommodation.csv", encoding="utf-8-sig"))
acc.insert(0, "accommodation_id", [f"AC{n0 + i + 1:03d}" for i in range(len(acc))])
acc["currency"] = "INR"
acc["price_basis"] = acc["price_basis"].replace("", "price not captured")
acc["data_quality_notes"] = acc["data_quality_notes"].where(acc["data_quality_notes"] != "", "") 
acc.loc[acc.source == "Cleartrip", "data_quality_notes"] = (
    acc.loc[acc.source == "Cleartrip", "data_quality_notes"] + " Listing dates 28-29 Dec 2026 fall in the New Year peak, so this is a peak-week price, not a typical rate.").str.strip()
print("accommodation", append_rows(RAW / "accommodation.csv", acc.to_dict("records")))

# 2. best_months
bm = pd.read_csv(COL / "best_months_new.csv", dtype=str, keep_default_na=False)
p = RAW / "destinations.csv"
d = pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")
log = []
for _, r in bm.iterrows():
    m = d.destination_id == r.destination_id
    assert d.loc[m, "best_months"].iloc[0] == "", r.destination_id
    d.loc[m, "best_months"] = r.best_months
    d.loc[m, "data_notes"] += f" best_months added 23-11-2026 from {r.source}: \"{r.quote}\" (page-stated, not verified against weather)."
    log.append(dict(destination_id=r.destination_id, column_name="best_months", source=r.source, url=r.source_url,
                    date_collected=TODAY_RAW, is_estimate="FALSE", notes=f"Page-stated: {r.quote}"))
d.to_csv(p, index=False, encoding="utf-8-sig", lineterminator="\n")

# 3. routes: single unambiguous source claims upgrade estimated -> source_reported; conflicts only annotated
v = pd.read_csv(COL / "route_verified.csv", dtype=str, keep_default_na=False)
rp = RAW / "route_data.csv"
rt = pd.read_csv(rp, dtype=str, keep_default_na=False, encoding="utf-8-sig")
for (o, dest), g in v.groupby(["origin", "destination"]):
    m = (rt.origin_name == o) & (rt.destination == dest)
    i = rt.index[m][0]
    kms = sorted(set(g.road_km.astype(int)))
    cite = "; ".join(f"{s} {k} km ({u})" for s, k, u in zip(g.source.str.split(" ").str[0], g.road_km, g.source_url))
    if rt.at[i, "data_quality"] == "estimated" and len(kms) == 1:
        old = rt.at[i, "road_distance_km"]
        rt.at[i, "road_distance_km"] = str(kms[0])
        rt.at[i, "data_quality"] = "source_reported"
        rt.at[i, "last_verified"] = TODAY_ISO
        rt.at[i, "route_source"] = f"Page states {cite}. Previous assistant estimate was {old} km. Drive hours remain an estimate."
        kind = "upgraded to source_reported"
    else:
        rt.at[i, "route_source"] += f" Independent check 23-11-2026: {cite}." + (" Sources disagree; left unchanged." if len(kms) > 1 or rt.at[i, "data_quality"] == "estimated" else "")
        kind = "annotated only"
    log.append(dict(destination_id=rt.at[i, "destination_id"], column_name="route:" + o, source="Route page(s) via search", url=g.source_url.iloc[0],
                    date_collected=TODAY_RAW, is_estimate="FALSE", notes=f"{kind}: {'/'.join(map(str,kms))} km"))
rt.to_csv(rp, index=False, encoding="utf-8-sig", lineterminator="\n")

# 4. source log (raw copies use DD-MM-YYYY, top-level ISO)
for a in acc.itertuples():
    log.append(dict(destination_id=a.destination_id, column_name="accommodation", source=a.source, url=a.source_url,
                    date_collected=TODAY_RAW, is_estimate="FALSE", notes=f"{a.property_name}; price as listed on page"))
for path, iso in [(RAW / "source_log.csv", False), (ROOT / "data" / "source_log.csv", True)]:
    rows = [dict(x, date_collected=TODAY_ISO) if iso else x for x in log]
    print(path.name, append_rows(path, rows))
