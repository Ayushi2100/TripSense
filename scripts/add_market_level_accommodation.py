"""Adds market-level accommodation reference rows for destinations where a fetched page states a
'starting from' price. No hotel names or room prices are invented; the figure is quoted in the
notes only, as in the existing Amritsar row. Run: python -m scripts.add_market_level_accommodation
"""
from pathlib import Path

import pandas as pd

from scripts.csv_append import append_rows

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
CK = "23-11-2026"
BASE = dict(accommodation_type="Market-level reference", room_type="Mixed property/room types",
            price_checked_date=CK, price_basis="market-level reference only", currency="INR",
            data_quality_notes="Market minimum only, not a named property's rate; no taxes, dates or room type stated on the page.")
rows = [
    dict(destination_id="D10", property_name="Bir budget accommodation market minimum", location="Bir (Himachal) area-wide",
         source="ixigo", source_url="https://www.ixigo.com/hotels/5-star-hotels-in-bir",
         price_observation_notes="Page header says 'price starting from' INR 793 per night (Tathastu Retreat Bir, per room). The same page also lists another property at INR 394, so INR 793 is not a true minimum. Page URL is a '5 star' category page."),
    dict(destination_id="D11", property_name="Palampur budget accommodation market minimum", location="Palampur area-wide",
         source="ixigo", source_url="https://www.ixigo.com/hotels/hotels-in-palampur",
         price_observation_notes="Page says hotels in Palampur 'start at INR 836 per night for budget accommodations'. The same page lists a Bir property at INR 394, so the figure is a page headline, not a verified minimum."),
    dict(destination_id="D13", property_name="Kullu budget accommodation market minimum", location="Kullu area-wide",
         source="ixigo", source_url="https://www.ixigo.com/hotels/hotels-in-kullu",
         price_observation_notes="Page says hotels in Kullu 'start at INR 601 per night for budget accommodations'. The same page lists lower per-night rates (INR 350 dorm at Bhuntar, 411 and 450), so INR 601 is a page headline, not a verified minimum."),
    dict(destination_id="D14", property_name="Manali budget accommodation market minimum", location="Manali area-wide",
         source="ixigo", source_url="https://www.ixigo.com/hotels/budget-hotels-in-manali",
         price_observation_notes="Page says 'Budget Hotels In Manali with prices starting at just INR 826'; listings are labelled per night, per room. Another ixigo Manali page shows INR 442 for all hotels."),
    dict(destination_id="D15", property_name="Kasol budget accommodation market minimum", location="Kasol area-wide",
         source="OYO Rooms", source_url="https://www.oyorooms.com/hotels-in-kasol/",
         price_observation_notes="Page headline says starting at INR 756 (a crossed-out price on its own listing, discounted to INR 444 plus INR 115 taxes); its FAQ says roughly INR 660 to 1000 per room per night. The page's own figures conflict, so none is stored as a price."),
]
rows = [{**BASE, **r} for r in rows]
last = pd.read_csv(RAW / "accommodation.csv", dtype=str, encoding="utf-8-sig").accommodation_id.iloc[-1]
for i, r in enumerate(rows, int(last[2:]) + 1):
    r["accommodation_id"] = f"AC{i:03d}"
print(append_rows(RAW / "accommodation.csv", rows, key="accommodation_id"))
log = [dict(destination_id=r["destination_id"], column_name="accommodation", source=r["source"], url=r["source_url"],
            date_collected="2026-11-23", is_estimate="TRUE", notes="Market-level 'starting from' figure quoted in notes only") for r in rows]
print(append_rows(RAW.parent / "source_log.csv", log))
for r in log:
    r["date_collected"] = "23-11-2026"
print(append_rows(RAW / "source_log.csv", log))
