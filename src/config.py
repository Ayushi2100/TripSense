"""TripSense Phases 4-5: every provisional choice lives in this file.

Nothing here is a measured fact. Each value is an assumption or a decision
that can be changed in one place, and the pipeline re-runs from it.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"

# Approximate Pathankot city-centre coordinates, used only for the straight-line
# (haversine) sanity check. Source not yet logged; verify before relying on it.
PATHANKOT = (32.2643, 75.6421)

# Origins (starting locations) live in data/raw/origin_locations.csv; routes in route_data.csv.
# PATHANKOT above is kept for the legacy Pathankot comparison columns only.
DEFAULT_ORIGIN_ID = "O01"
# Default "longest one-way drive" per origin. A UI convenience only (the scoring formula is
# unchanged): from Delhi almost nothing is within 4 hours, so a 4-hour default would show no results.
ORIGIN_DEFAULT_MAX_DRIVE = {"O01": 4.0, "O02": 8.0, "O03": 12.0}

# Which road-distance column feeds the features while the three sources conflict.
#   entered         -> the author's own entries in destinations.csv
#   clean_file      -> destinations_clean.csv
#   transport_table -> road rows of transportation.csv (Vaishno Devi = sum of legs)
DISTANCE_SOURCE = "entered"

# A distance is flagged as conflicting when sources differ by more than this share.
DISTANCE_CONFLICT_TOLERANCE = 0.10

# Rule-based monthly suitability (assumptions, tested in season_rule_sensitivity.csv).
#   cold  : average daily maximum below cold_tmax (deg C)
#   hot   : average daily maximum above hot_tmax (deg C)
#   wet   : monthly rainfall at or above wet_mm (mm); checked first
#   comfortable: none of the above
#   near_freezing is a separate flag: average daily minimum <= freezing_tmin
SEASON_RULES = {"cold_tmax": 15.0, "hot_tmax": 32.0, "wet_mm": 200.0, "freezing_tmin": 2.0}

SENSITIVITY_SCENARIOS = [
    {"cold_tmax": c, "hot_tmax": h, "wet_mm": w}
    for (c, h) in [(13.0, 30.0), (15.0, 32.0), (17.0, 34.0)]
    for w in (150.0, 200.0, 250.0)
]

# A destination's weather is flagged when its annual rainfall differs from its
# nearest neighbour's by more than this factor.
RAIN_NEIGHBOUR_FACTOR = 3.0

# Minimum priced listings before an accommodation median is called reliable.
ACCOM_MIN_PRICED = 3

INTERESTS = ["nature", "adventure", "culture", "history", "spiritual"]

# Attraction types in attractions.csv are already one of the five interests.
ATTRACTION_TYPE_MAP = {i: [i] for i in INTERESTS}

# activity_type is free text such as "Culture / Heritage". It is split on "/" and each
# token is mapped here. An empty list means the token says nothing about interest
# (leisure, golf, walking alone, boating alone, pilgrimage transport = logistics).
# An item with several interests splits its weight equally between them.
ACTIVITY_TOKEN_MAP = {
    "nature": ["nature"], "nature walk": ["nature"], "birdwatching": ["nature"],
    "wildlife": ["nature"],
    "trekking": ["adventure"], "hiking": ["adventure"], "paragliding": ["adventure"],
    "cycling": ["adventure"], "water activity": ["adventure"], "water sports": ["adventure"],
    "culture": ["culture"], "cultural": ["culture"], "shopping": ["culture"],
    "ceremony": ["culture"], "museum": ["culture"],
    "heritage": ["history"], "history": ["history"],
    "spiritual": ["spiritual"], "pilgrimage": ["spiritual"], "ritual": ["spiritual"],
    "boating": [], "walking": [], "leisure": [], "golf": [],
    "pilgrimage transport": [],
}
# A trek that is part of a pilgrimage is not counted as adventure.
PILGRIMAGE_DROPS_TREKKING = True


# ---------------------------------------------------------------------------
# Phase 6+ : budget, recommender, itinerary. ALL of these are assumptions.
# None is a measured fact. Placeholders are labelled and shown as such in the app.
# ---------------------------------------------------------------------------

# Spending not covered by any collected table (entry fees and activity costs are
# empty in the raw data). INR per person per day. PLACEHOLDERS: replace with real
# data or your own experience.
FOOD_PER_PERSON_DAY = {"budget": 400.0, "standard": 700.0, "comfort": 1200.0}
LOCAL_PER_PERSON_DAY = {"budget": 150.0, "standard": 300.0, "comfort": 500.0}

# Room price per night: which quantile of the listed prices a tier uses.
ROOM_QUANTILE = {"budget": 0.25, "standard": 0.50, "comfort": 0.75}
PEOPLE_PER_ROOM = 2
PEOPLE_PER_TAXI = 4

# Taxi and bus rates (INR per km) are DERIVED from the rows in
# transport_fare_estimates.csv (midpoint fare / road km), only to fill destinations
# with no collected fare. They are labelled "derived" in the output.

# Itinerary: usable sightseeing minutes per day (assumption).
SIGHTSEEING_MIN_PER_DAY = 360

# Season score: how quickly a month's score falls as it leaves the comfortable band.
# penalty = temp_gap / SEASON_TEMP_TOL + rain_excess / SEASON_RAIN_TOL, capped at 1.
SEASON_TEMP_TOL_C = 10.0
SEASON_RAIN_TOL_MM = 200.0

# Default importance of the four score components. Equal on purpose: nothing in the
# data justifies a different split. The user can change them; evaluation.py tests
# how much the ranking depends on them.
DEFAULT_WEIGHTS = {"interest": 1.0, "season": 1.0, "budget": 1.0, "distance": 1.0}

# Similar-destination groups (equal weight by default).
SIMILARITY_WEIGHTS = {"interest": 1.0, "type": 1.0, "elevation": 1.0, "distance": 1.0}
