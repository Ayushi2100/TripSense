# Phases 4–5 summary: EDA and feature engineering

## What was built

- `src/` pipeline that turns the six raw tables into 42 destination features and 15 destination-month features.
- Ten figures and two notebooks (`03_eda`, `04_feature_engineering`).
- Unit tests, a feature dictionary, and a sensitivity table for the weather rule.

## Provisional choices (all in `src/config.py`)

| Choice | Current value | Why it is provisional |
|---|---|---|
| Road distance source | `entered` (your own entries) | Three sources conflict for 7 of 9 destinations |
| Comfortable month | daytime max 15–32 °C and rain < 200 mm | Assumption; counts shift by 1–4 months across 9 alternatives |
| Interest mapping | token table in `interest_mapping.csv` | Judgement calls, e.g. heritage → history, shopping → culture |
| Travel-time format | hours.minutes, single digit = tens of minutes | `2.2` read as 2 h 20 min |
| Pathankot reference point | 32.2643, 75.6421 | Approximate; only used for the straight-line check |

## Findings that matter for the next phase

1. **Road distances.** Your entries differ from the other two files for 7 of 9 destinations. The clean file and `transportation.csv` agree except for Vaishno Devi, where the clean file shows 48 km (the Jammu–Katra leg). The legs sum to 160 km.
2. **Best months.** The weather rule calls September–November comfortable for Dharamshala, Dalhousie and Khajjiar; the entered lists omit them. Amritsar matches exactly; McLeod Ganj lists all 12 months.
3. **Weather quality.** McLeod Ganj is a Dharamshala proxy. Khajjiar, Dalhousie and Chamba have identical rainfall. Kangra's rainfall (361 mm a year) and temperatures (41 °C in June) look inconsistent with its neighbours.
4. **Interests.** Vaishno Devi is 89% spiritual; Dalhousie 91% and Khajjiar 78% nature plus adventure; McLeod Ganj 41% culture and 41% spiritual. Dharamshala and McLeod Ganj are not especially similar (cosine 0.58).
5. **Budget data is missing.** No entry fees, almost no activity costs or transport fares, and prices for 21 of 27 accommodation listings (none for Dharamshala).

## Limitations

- Item lists are a curated sample (4–7 attractions, 5–6 activities per destination), so shares describe collected items.
- Weather comes from grid-based or modelled monthly tables, not station records.
- Rating, review count and recommended stay are empty and not yet features.

## Decisions needed before Phase 6

1. Which road-distance source is authoritative, with a logged source and date.
2. Whether to keep the entered `best_months` or replace the season component with the weather-derived rule.
3. Whether to recheck Kangra's weather and coordinates.

## Two files named `destinations_clean.csv`

- `data/processed/destinations_clean.csv` is the version produced earlier in this project: your entered distances, times converted to decimal hours, `best_months` pipe-separated.
- `data/raw/destinations_clean.csv` is the copy from the Streamlit starter zip. Its distances match `transportation.csv`, not your entries, and its Kangra and Vaishno Devi times do not follow from your values.

The pipeline reads `data/raw/destinations.csv` (your entries) and uses the clean copy in `raw/` only for the distance comparison. Settle which one is authoritative during cleaning, then keep a single file.
