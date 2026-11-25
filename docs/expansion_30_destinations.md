# Expansion to 30 destinations and three starting cities

## What changed
- 21 destinations added (D10-D30), D01-D09 untouched. IDs follow the order you listed.
- Fixed Pathankot origin removed. `origin_locations.csv` (O01 Pathankot, O02 Chandigarh, O03 Delhi) and
  `route_data.csv` (90 rows) hold origin-specific distance and time. `destinations.csv` keeps its old Pathankot
  `road_distance_km` / `travel_time_hrs` for D01-D09 only (legacy); the engine reads `route_data.csv`.
- The sidebar has "Where are you starting your journey?". Every page, the recommender, the budget and the
  itinerary use that city, and it can be changed at any time.
- Chandigarh is both a destination (D27) and a starting city (O02). Starting in Chandigarh excludes D27 with the
  reason "this is your starting city". Pathankot and Delhi are not destinations.
- The scoring formula and weights are unchanged. The origin only changes the distance, drive-time and
  transport-cost inputs, as you specified.

## Files
| Area | Change |
|---|---|
| New data | `origin_locations.csv`, `route_data.csv` |
| Appended rows | destinations (+21), weather (+252), attractions (+113), activities (+100), accommodation (+45), transportation (+44), source_log (+186) |
| Code | `features.apply_origin`, `data_access.origin_view`, `Prefs.origin_id`, budget (outward and return lines, origin-aware fares), recommender, similarity (valley and lake types), sidebar input, pages, download button |
| New tooling | `src/validate_data.py`, `tests/test_origin.py`, `scripts/` |

## How each value is labelled
**Routes (90):** 9 author-entered (Pathankot, D01-D09), 24 `source_reported` (road km copied from a cited page,
hours estimated), 56 `estimated` (assistant estimate, not verified against a route engine, treat as +/- 15 %),
1 `not_applicable` (Chandigarh to Chandigarh). Straight-line distance is calculated from coordinates and is real.
**Coordinates, elevation, destination type (D10-D30):** approximate values from general knowledge, flagged in
`source_log.csv` as estimates. Verify before publishing.
**Weather:** all 30 destinations have 12 monthly rows. Own-place tables (`is_proxy_data` FALSE): D10, D11, D12, D14, D15, D17, D24 (Srinagar, IMD via
Wikipedia), D25 and D27. Proxy rows (TRUE, with the proxy and the likely
bias in `data_notes`): Kullu, Tirthan Valley, Jibhi, Barot Valley use Manali; Kasauli, Solan, Chail use Shimla;
Spiti uses Leh (a different high desert, so weakest); Patnitop and Sanasar use Udhampur (about 1,300 m lower);
Anandpur Sahib uses Chandigarh; Ranjit Sagar Lake uses Pathankot. Proxy temperatures are usually wrong in the
direction stated in each row, so season scores for these places are indicative only.
**Attractions and activities:** sourced from official or credible pages; visit times and durations are estimates.
**Accommodation:** named properties only where a page showed a tariff; otherwise a market-level reference row with
the page's "starting from" figure kept in the notes (not used as a price). Stage 5 added 22 rows (Mandi, Solan,
Chail, Patnitop, Sanasar, Srinagar) from Cleartrip/Expedia listing pages. Cleartrip dates fell in the 28-29 Dec New Year
peak, so those are peak-week prices. Sanasar has a name only (PY Resorts, no verified price). A destination with
fewer than 3 priced listings uses the pooled stay price, and the app labels it "pooled".
**best_months:** added for 20 of 21 new destinations, copied from a page's stated best time (quoted in `data_notes`
and `source_log.csv`). Blank for Barot Valley (no reliable page naming months). Srinagar (Apr-Oct, Holidify), Pahalgam (Mar-Nov, Holidify) and Ranjit Sagar Lake (Aug-Sep, OYO travel guide) were added on 24-11-2026.
**Fares:** collected fares are Pathankot-only. For other starting cities the budget uses a per-km rate derived from
short Pathankot routes (labelled "derived"); this ignores trains and flights and is rough for long journeys.

## Known gaps (validation passes 26 of 26; these are documented data limits)
- **No accommodation listings: Ranjit Sagar Lake (D28).** Declared in `data/raw/accommodation_coverage.csv` as `no_collected_listings`; validation check 8b requires every destination to have rows or be declared there. The budget uses a pooled estimate, labelled as such in the app.
- Weather for 13 destinations is a proxy, not that place's own record (see above). Spiti (Leh proxy) is the weakest.
- Accommodation: Sanasar has no verified price; Srinagar houseboats and HPTDC/JKTDC tariffs could not be fetched.
- `best_months` blank only for Barot Valley (D30): the one page found says "any time of the year except for monsoons" without naming months.
- Routes: after Stage 5, 24 are `source_reported` (road km stated by a cited page), 56 `estimated`, 9 author-entered,
  1 not applicable. Drive hours are estimates everywhere. Where sources disagreed, the route stays `estimated`
  and the conflict is noted in `route_source`.
- Coordinates and elevations of D10-D30 were checked on 24-11-2026 (see below). Jibhi (D29) and Tirthan Valley (D19) could not be verified, Pahalgam's longitude is disputed between sources, and destination type is still the author's classification.
- Original EDA figures still describe the first nine destinations; the Analytics page says so.
- Pooled stay prices moved Dharamshala, Dalhousie and Amritsar budget by about INR 700.
- Spiti and other seasonally closed roads are not modelled.

## Regression check
From Pathankot, the original 9 destinations score identically to before for interest, season, budget (six of nine)
and distance (eight of nine). Differences: Dharamshala, Dalhousie and Amritsar budget (pooled stay price, above);
Kangra distance score (its missing drive time is estimated from the median speed, now over 29 routes).

## Coordinate and elevation verification (24-11-2026)
Every decision is in `destinations.data_notes` and `source_log.csv` (column `latitude/longitude/elevation_m`). Tolerance: 0.02 degrees or 100 m.
- **Checked, kept (14):** D10 Bir, D11 Palampur, D12 Mandi, D13 Kullu, D14 Manali, D15 Kasol, D16 Kasauli, D18 Solan, D21 Chail, D22 Patnitop, D24 Srinagar, D26 Anandpur Sahib, D27 Chandigarh, plus D17 Shimla (elevation sources range 2,073-2,397 m; entered 2,205 m kept).
- **Changed (4):** D20 Spiti elevation 3,800 to 3,650 m (Kaza, Wikipedia); D23 Sanasar coordinates to 33.125, 75.26 and elevation to 2,050 m (Wikipedia, Incredible India, JKTDC; arc-minute precision); D28 elevation 430 to 528 m (normal reservoir level, Wikipedia and Punjab Irrigation Dept); D30 Barot coordinates to 32.03639, 76.8475 (Wikipedia).
- **Conflicting or unverified, entered values kept (3):** D19 Tirthan Valley (no coordinates found), D25 Pahalgam (longitude 75.19 on Wikipedia vs 75.315 entered), D29 Jibhi (only a pincode site and an uncorroborated 1,900 m claim).
- Straight-line distances in `route_data.csv` were recomputed for D23 and D30 (6 rows) because their coordinates moved. Road km and drive hours are unchanged.

## Other Stage 6 changes
- `Prefs.budget_total` default is now 10,000 (matches the sidebar).
- `destinations_clean.csv` (raw and processed) now has 30 rows. D01-D09 rows are untouched (the raw and processed copies of those nine differ in road km, as they did originally). `DISTANCE_SOURCE` is still "entered".
- Pooled stay prices are shown as "ESTIMATE (pooled)" in the budget table, with a warning on the budget pages and a message on Destination details when no listings exist.
