"""Sidebar trip inputs, shared by every page."""
import streamlit as st

from src import config
from src.data_access import month_name, origin_choices
from src.recommender import Prefs

MONTHS = [month_name(m) for m in range(1, 13)]


def sidebar_inputs():
    sb = st.sidebar
    sb.header("Your trip")
    origins = origin_choices()
    origin_name = sb.selectbox("Where are you starting your journey?", [n for _, n in origins], index=0,
                               help="Distances, drive times and transport costs are recalculated from this city.")
    origin_id = dict((n, i) for i, n in origins)[origin_name]
    month = sb.selectbox("Month of travel", MONTHS, index=4)
    travellers = int(sb.number_input("Travellers", min_value=1, max_value=12, value=2, step=1))
    nights = int(sb.slider("Nights away", 1, 7, 2))
    budget = float(sb.number_input("Total budget (INR)", min_value=2000, max_value=300000,
                                   value=10000, step=1000))
    tier = sb.selectbox("Comfort level", ["budget", "standard", "comfort"], index=1)
    mode = sb.radio("Getting there", ["taxi", "bus"], index=0)
    max_drive = float(sb.slider("Longest one-way drive (hours)", 1.0, 30.0,
                                config.ORIGIN_DEFAULT_MAX_DRIVE.get(origin_id, 4.0), 0.5,
                                key=f"max_drive_{origin_id}"))

    sb.subheader("What do you enjoy? (0 = not at all, 5 = a lot)")
    interests = {i: float(sb.slider(i.capitalize(), 0, 5, 3)) for i in config.INTERESTS}

    with sb.expander("Advanced: scoring settings"):
        st.write("Importance of each part of the score. Equal by default because nothing in "
                 "the data justifies a different split.")
        weights = {k: float(st.slider(k.capitalize(), 0.0, 3.0, 1.0, 0.25, key=f"w_{k}"))
                   for k in config.DEFAULT_WEIGHTS}
        season_method = st.selectbox("Season rule", ["weather", "entered", "both"], index=0,
                                     help="weather = derived from monthly temperature and rain; "
                                          "entered = your own best_months list; both = average")
    return Prefs(month=MONTHS.index(month) + 1, travellers=travellers, nights=nights,
                 budget_total=budget, tier=tier, mode=mode, max_drive_hours=max_drive,
                 interests=interests, weights=weights, season_method=season_method,
                 origin_id=origin_id)
