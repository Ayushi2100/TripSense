"""One function per page. Each takes (data, prefs)."""
import pandas as pd
import streamlit as st

from src import budget as bud
from src import config, evaluation
from src.data_access import effective_drive_hours, month_name
from src.itinerary import build as build_itinerary
from src.recommender import recommend
from src.similarity import group_similarities, similar_to

BASIS_TEXT = {"collected": "collected from a sourced table",
              "derived": "derived from collected rows",
              "pooled": "ESTIMATE (pooled): median of other destinations' listings, not this destination's own price",
              "placeholder": "placeholder assumption: replace with real data"}


def _inr(x):
    return f"INR {x:,.0f}"


def _pick_destination(data, key, label="Destination"):
    names = data["features"]["destination"].tolist()
    return st.selectbox(label, names, key=key)


def _row(data, name):
    f = effective_drive_hours(data["features"])
    return f[f["destination"] == name].iloc[0]


def _show_budget_table(est):
    t = est["table"].copy()
    t["cost_inr"] = t["cost_inr"].round(0).astype(int)
    t["basis"] = t["basis"].map(BASIS_TEXT)
    st.dataframe(t, hide_index=True)
    if (est["table"]["basis"] == "pooled").any():
        st.warning("The Stay line is a pooled estimate, not a price collected for this destination. "
                   "It uses the median of listings from other destinations because this destination has "
                   "fewer than 3 priced listings.")
    st.caption(f"Total {_inr(est['total'])} ({_inr(est['per_person'])} per person). "
               f"{est['data_backed_share']:.0%} of this total rests on collected or derived data; "
               f"the rest is placeholder spending.")


def trip_plan_text(data, prefs, dest_id, score_line=""):
    """Plain-text trip plan for the download button. Every number comes from the same
    functions the pages use, so the file always matches what is on screen."""
    r = effective_drive_hours(data["features"]).set_index("destination_id").loc[dest_id]
    est = bud.estimate(dest_id, prefs.travellers, prefs.nights, prefs.tier, prefs.mode, data)
    plan, rest, used = build_itinerary(dest_id, prefs.nights + 1, prefs.interests, data)
    L = [f"TripSense trip plan: {r['origin_name']} to {r['destination']}", "=" * 50,
         f"Starting from: {r['origin_name']}",
         f"Travel month: {month_name(prefs.month)}   Travellers: {prefs.travellers}   Nights: {prefs.nights}",
         f"Comfort: {prefs.tier}   Travel mode: {prefs.mode}   Budget: {_inr(prefs.budget_total)}",
         f"Road distance: {r['road_distance_km']:.0f} km   Drive time: {r['drive_hours']:.1f} h "
         f"(route data quality: {r['route_quality']})"]
    if score_line:
        L.append(score_line)
    L += ["", "COST ESTIMATE (INR)"]
    for _, x in est["table"].iterrows():
        L.append(f"- {x['item']}: {x['cost_inr']:,.0f}  [{x['basis']}]  {x['how']}")
    L.append(f"TOTAL: {est['total']:,.0f}  ({est['per_person']:,.0f} per person; "
             f"{est['data_backed_share']:.0%} rests on collected or derived data)")
    L += ["", "DAY PLAN"]
    for d, items in enumerate(plan, 1):
        arrive = f" (after a {r['drive_hours']:.1f} h drive in from {r['origin_name']})" if d == 1 else ""
        L.append(f"Day {d}{arrive}, about {used[d - 1] / 60:.1f} h planned")
        L += [f"  - {it['name']} ({it['kind']}, about {it['minutes']:.0f} min)" for it in items] or ["  - Free day"]
    if rest:
        L.append("Not scheduled: " + ", ".join(i["name"] for i in rest))
    L += ["", "NOTES", "Estimates are labelled in the cost lines. Food and local spending are placeholders.",
          "Check current fares, road conditions and seasonal closures before you travel."]
    return "\n".join(L)


def _download_plan(data, prefs, dest_id, key, score_line=""):
    name = dest_id_name(data, dest_id).replace(" ", "_")
    st.download_button("Download this trip plan (.txt)", trip_plan_text(data, prefs, dest_id, score_line),
                       file_name=f"TripSense_{prefs_origin(data)}_to_{name}.txt", mime="text/plain", key=key)


def dest_id_name(data, dest_id):
    f = data["features"]
    return f.loc[f["destination_id"] == dest_id, "destination"].iloc[0]


def prefs_origin(data):
    return data["features"]["origin_name"].iloc[0]


# ---------------------------------------------------------------- Home
def home(data, prefs):
    f = data["features"]
    st.markdown("""
    <section class="ts-hero">
      <div class="ts-eyebrow">A little closer to your next escape</div>
      <h1>Find your kind<br>of getaway.</h1>
      <p>Thoughtful trip ideas from Pathankot, Chandigarh or Delhi, matched to your travel month, interests, budget and drive time — with the reasoning shown clearly.</p>
    </section>
    """, unsafe_allow_html=True)

    stats = st.columns(3, gap="medium")
    stat_data = [
        ("DESTINATIONS", str(len(f)), "From mountains to spiritual stops"),
        ("PRICED STAYS", str(int(f["accom_n_priced"].sum())), "Listings with a recorded price"),
        ("FARE RANGES", str(len(data["fares"])), "Fare ranges in the dataset"),
    ]
    for col, (label, value, note) in zip(stats, stat_data):
        with col:
            st.markdown(f"<div class='ts-stat'><div class='ts-stat-label'>{label}</div><div class='ts-stat-value'>{value}</div><div style='color:#71857b;font-size:.8rem;margin-top:4px'>{note}</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div><div class='ts-section-label'>A simple way to choose</div>", unsafe_allow_html=True)
    st.header("A trip that fits you, not the other way around")
    steps = st.columns(4, gap="medium")
    step_data = [
        ("01", "Set your scene", "Choose your month, group size, budget and preferred travel style in the sidebar."),
        ("02", "Find your fit", "Destinations are filtered against your budget and maximum drive time."),
        ("03", "Compare the match", "Interest, season, budget and distance contribute to each score."),
        ("04", "See the reasoning", "Review why a place ranks well and where data is estimated or missing."),
    ]
    for col, (num, title, copy) in zip(steps, step_data):
        with col:
            st.markdown(f"<div class='ts-step'><div class='ts-step-num'>{num}</div><div class='ts-step-title'>{title}</div><div class='ts-step-copy'>{copy}</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.subheader("Start with your trip details")
        st.write("Use the trip controls in the left panel, then open **Recommendations** to see the destinations that fit your plans.")
        if st.button("Explore recommendations", type="primary", use_container_width=True):
            st.session_state["Page"] = "Recommendations"
            st.rerun()
    with right:
        st.markdown("<div style='background:#e7f1eb;border:1px solid #d7e6da;border-radius:17px;padding:20px 22px'><div style='font-size:1rem;font-weight:800;color:#1e5948;margin-bottom:7px'>A note on transparency</div><div style='font-size:.91rem;line-height:1.6;color:#47665a'>TripSense is a rule-based decision-support tool, not a machine-learning model. It labels estimates and data gaps instead of presenting them as verified facts.</div></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Plan My Trip
def plan_my_trip(data, prefs):
    st.title("Plan my trip")
    ranked, excluded = recommend(prefs, data)
    st.write(f"{month_name(prefs.month)}, {prefs.travellers} traveller(s), {prefs.nights} night(s), "
             f"budget {_inr(prefs.budget_total)}, {prefs.tier} comfort, by {prefs.mode}.")
    if ranked.empty:
        st.warning("No destination passes your filters. Raise the budget or the drive limit.")
        near = effective_drive_hours(data["features"])
        near = near[near["route_available"]].sort_values("drive_hours")
        if len(near):
            n = near.iloc[0]
            st.info(f"From {n['origin_name']} the closest destination is {n['destination']}, "
                    f"about {n['drive_hours']:.1f} h away.")
        st.dataframe(excluded, hide_index=True)
        return
    top = ranked.iloc[0]
    st.subheader(f"Best match: {top['destination']}")
    c = st.columns(3)
    c[0].metric("Score", f"{top['score']:.2f}")
    c[1].metric("Estimated cost", _inr(top["est_cost_inr"]))
    c[2].metric(f"Drive from {top['origin_name']}", f"{top['drive_hours']:.1f} h")
    st.write(top["explanation"])
    if top["warnings"]:
        st.warning("Data caveats: " + top["warnings"])
    est = bud.estimate(top["destination_id"], prefs.travellers, prefs.nights, prefs.tier, prefs.mode, data)
    st.subheader("Cost breakdown")
    _show_budget_table(est)
    st.subheader("Day plan")
    _show_itinerary(data, top["destination_id"], prefs)
    _download_plan(data, prefs, top["destination_id"], "dl_plan",
                   f"Match score {top['score']:.2f}. {top['explanation']}")
    if len(ranked) > 1:
        st.subheader("Other options")
        st.dataframe(ranked[["rank", "destination", "score", "est_cost_inr"]].round(2).iloc[1:4], hide_index=True)


# ---------------------------------------------------------------- Recommendations
def recommendations(data, prefs):
    st.title("Recommendations")
    ranked, excluded = recommend(prefs, data)
    if ranked.empty:
        st.warning("No destination passes your filters.")
    else:
        show = ranked[["rank", "destination", "score", "s_interest", "s_season", "s_budget",
                       "s_distance", "est_cost_inr", "drive_hours"]].copy()
        st.dataframe(show.round(2), hide_index=True)
        st.caption("Component scores run from 0 (worst) to 1 (best). Score = weighted average.")
        st.bar_chart(ranked.set_index("destination")[["s_interest", "s_season", "s_budget", "s_distance"]])
        st.subheader("Why each place ranks where it does")
        for _, r in ranked.iterrows():
            with st.expander(f"{int(r['rank'])}. {r['destination']}  (score {r['score']:.2f})"):
                st.write(r["explanation"])
                if r["warnings"]:
                    st.caption("Caveats: " + r["warnings"])
    if len(excluded):
        st.subheader("Excluded by your filters")
        st.dataframe(excluded, hide_index=True)


# ---------------------------------------------------------------- Destination Details
def destination_details(data, prefs):
    st.title("Destination details")
    name = _pick_destination(data, "dd_dest")
    r = _row(data, name)
    c = st.columns(4)
    if not r["route_available"]:
        st.info(f"{name} is your starting city, so there is no route to show.")
    c[0].metric(f"Road distance from {r['origin_name']}", f"{r['road_distance_km']:.0f} km" if r["route_available"] else "n/a")
    c[1].metric("Drive time", (f"{r['drive_hours']:.1f} h" + (" (est.)" if r["drive_time_estimated"] else "")) if r["route_available"] else "n/a")
    c[2].metric("Elevation", f"{r['elevation_m']:.0f} m")
    c[3].metric("Type", r["primary_type"])
    if r["route_available"]:
        st.caption(f"Route data quality: {r['route_quality']}"
                   + (" (estimate, not verified against a route engine)" if r["route_quality"] == "estimated" else ""))
    if r["origin_id"] == "O01" and r["distance_conflict_flag"] == 1:
        st.warning(f"Road distance differs between source files: entered {r['road_km_entered']:.0f} km, "
                   f"clean file {r['road_km_clean_file']:.0f} km, transport table {r['road_km_transport_table']:.0f} km.")
    st.subheader("Interest mix of the collected items")
    st.bar_chart(pd.Series({i: r[f"share_{i}"] for i in config.INTERESTS}, name="share"))
    st.caption(f"Based on {int(r['n_attractions'])} attractions and {int(r['n_activities'])} activities collected; "
               "a curated sample, not every thing to do.")
    st.subheader("Month by month")
    m = data["months"][data["months"]["destination_id"] == r["destination_id"]]
    if m.empty:
        st.info("No monthly weather data has been collected for this destination yet, so it is not scored on season.")
    else:
        st.dataframe(m[["month_name", "avg_temp_min_c", "avg_temp_max_c", "rainfall_mm", "category"]], hide_index=True)
    if r["weather_quality_flag"] not in ("ok", "no_weather_data"):
        st.warning(f"Weather data flag: {r['weather_quality_flag']}. Treat monthly figures with care.")
    tabs = st.tabs(["Attractions", "Activities", "Stay", "Similar places"])
    with tabs[0]:
        a = data["attractions"]
        st.dataframe(a[a["destination_id"] == r["destination_id"]][["attraction_name", "attraction_type", "visit_time_min_estimate"]], hide_index=True)
    with tabs[1]:
        b = data["activities"]
        st.dataframe(b[b["destination_id"] == r["destination_id"]][["activity_name", "activity_type", "estimated_duration"]], hide_index=True)
    with tabs[2]:
        acc = data["accommodation"]
        sub = acc[acc["destination_id"] == r["destination_id"]][["property_name", "accommodation_type", "displayed_total_per_night_inr", "price_checked_date"]]
        if sub.empty:
            st.info(f"No accommodation listings were collected for {name}. Nothing is invented here; "
                    "the budget uses a pooled estimate from other destinations' listings.")
        else:
            st.dataframe(sub, hide_index=True)
        if r["accom_reliable_flag"] != 1:
            st.caption("Fewer than 3 priced listings: the stay price in the budget is a pooled ESTIMATE "
                       "(median of all destinations' listings), not this destination's own price.")
    with tabs[3]:
        sim = similar_to(name, data["features"], k=3)
        st.dataframe(sim.round(2), hide_index=True)
        st.caption("Similarity = equal-weight mean of interest, type, elevation and drive-time closeness.")


# ---------------------------------------------------------------- Budget Planner
def budget_planner(data, prefs):
    st.title("Budget planner")
    name = _pick_destination(data, "bp_dest")
    r = _row(data, name)
    if not r["route_available"]:
        st.info(f"{name} is your starting city, so no transport cost applies.")
        return
    est = bud.estimate(r["destination_id"], prefs.travellers, prefs.nights, prefs.tier, prefs.mode, data)
    _show_budget_table(est)
    if est["total"] > prefs.budget_total:
        st.error(f"Over your budget of {_inr(prefs.budget_total)} by {_inr(est['total'] - prefs.budget_total)}.")
    else:
        st.success(f"Within your budget, with {_inr(prefs.budget_total - est['total'])} to spare.")
    st.subheader("All destinations at your settings")
    rows = []
    for _, d in data["features"].iterrows():
        if not d["route_available"]:
            continue
        e = bud.estimate(d["destination_id"], prefs.travellers, prefs.nights, prefs.tier, prefs.mode, data)
        rows.append({"destination": d["destination"], "total_inr": round(e["total"]),
                     "per_person_inr": round(e["per_person"]), "share_on_collected_data": round(e["data_backed_share"], 2)})
    df = pd.DataFrame(rows).sort_values("total_inr")
    st.dataframe(df, hide_index=True)
    st.bar_chart(df.set_index("destination")["total_inr"])
    st.caption("Food and local spending are placeholders (config.py) because no fee or meal prices were collected.")


# ---------------------------------------------------------------- Compare
def compare(data, prefs):
    st.title("Compare destinations")
    names = data["features"]["destination"].tolist()
    chosen = st.multiselect("Pick 2 to 4", names, default=names[:3])
    if len(chosen) < 2:
        st.info("Pick at least two.")
        return
    f = effective_drive_hours(data["features"]).set_index("destination").loc[chosen]
    mi = data["months"]
    table = pd.DataFrame({
        "Road km": f["road_distance_km"], "Drive hours": f["drive_hours"].round(1),
        "Elevation m": f["elevation_m"], "Type": f["primary_type"],
        **{f"Share {i}": f[f"share_{i}"].round(2) for i in config.INTERESTS},
        "Comfortable months": f["n_comfortable_months"]}).T
    st.dataframe(table)
    mrows = []
    for n in chosen:
        did = f.loc[n, "destination_id"]
        m = mi[(mi["destination_id"] == did)].sort_values("month")
        mrows.append(pd.Series(m["avg_temp_max_c"].values, name=n, index=[month_name(x)[:3] for x in m["month"]]))
    st.subheader("Average daily maximum temperature (C)")
    st.line_chart(pd.DataFrame(mrows).T)
    costs = {n: bud.estimate(f.loc[n, "destination_id"], prefs.travellers, prefs.nights, prefs.tier, prefs.mode, data)["total"] for n in chosen}
    st.subheader("Estimated trip cost at your settings")
    st.bar_chart(pd.Series(costs, name="INR"))


# ---------------------------------------------------------------- Itinerary
def _show_itinerary(data, dest_id, prefs):
    days = prefs.nights + 1
    plan, rest, used = build_itinerary(dest_id, days, prefs.interests, data)
    f = effective_drive_hours(data["features"])
    drive = f.loc[f["destination_id"] == dest_id, "drive_hours"].iloc[0]
    origin = f["origin_name"].iloc[0]
    st.write(f"Starting from **{origin}**.")
    for d, items in enumerate(plan, 1):
        arrive = f" (after a {drive:.1f} h drive in from {origin})" if d == 1 else ""
        st.markdown(f"**Day {d}**{arrive}  ~{used[d - 1] / 60:.1f} h planned")
        for it in items:
            st.write(f"- {it['name']} ({it['kind']}, about {it['minutes']:.0f} min)")
        if not items:
            st.write("- Free day: nothing left to schedule from the collected items.")
    if rest:
        st.caption("Not scheduled (no room, or no readable duration): " + ", ".join(i["name"] for i in rest))
    st.caption(f"Rule: up to {config.SIGHTSEEING_MIN_PER_DAY // 60} h of sightseeing per day, most relevant to your "
               "interests first. Attractions and activities may overlap (for example Triund), and the last "
               "day should allow for the drive back.")


def itinerary(data, prefs):
    st.title("Itinerary")
    name = _pick_destination(data, "it_dest")
    row = _row(data, name)
    did = row["destination_id"]
    if not row["route_available"]:
        st.info(f"{name} is your starting city, so there is no trip to plan.")
        return
    _show_itinerary(data, did, prefs)
    _download_plan(data, prefs, did, "dl_itinerary")


# ---------------------------------------------------------------- Analytics
FIGS = [("fig01_data_coverage.png", "How much data each destination has"),
        ("fig02_monthly_max_temp.png", "Average daily maximum temperature"),
        ("fig03_monthly_rainfall.png", "Monthly rainfall"),
        ("fig04_comfortable_months.png", "Comfortable months by the weather rule"),
        ("fig05_best_months_vs_weather.png", "Entered best months vs the weather rule"),
        ("fig06_interest_mix.png", "Interest mix"),
        ("fig07_accommodation_prices.png", "Stay prices"),
        ("fig08_distance_sources.png", "Road distance, three sources"),
        ("fig09_interest_similarity.png", "Interest similarity"),
        ("fig10_season_rule_sensitivity.png", "Sensitivity of the season rule")]


def analytics(data, prefs):
    st.title("Travel analytics")
    st.write("Figures from the EDA and feature-engineering phases. They were produced for the original nine "
             "destinations (Pathankot as the starting point) and have not been regenerated for the 30-destination data.")
    f = effective_drive_hours(data["features"])
    f = f[f["route_available"]]
    st.subheader(f"Drive time from {f['origin_name'].iloc[0]} to all destinations")
    st.bar_chart(f.set_index("destination")["drive_hours"].sort_values())
    st.caption("Hours. Routes marked 'estimated' in route_data.csv are not verified against a route engine.")
    for fname, cap in FIGS:
        path = config.FIG / fname
        if path.exists():
            st.image(str(path), caption=cap)


# ---------------------------------------------------------------- Methods
def methods(data, prefs):
    st.title("Methods, data and limits")
    st.subheader("What is real, what is estimated")
    st.write("- **Collected**: destinations, attractions, activities, stay listings, monthly weather, 11 fare ranges.\n"
             "- **Derived**: interest shares, comfortable months, detour ratio, taxi and bus rate per km.\n"
             "- **Placeholder**: food and local spending per day, people per room and per taxi, sightseeing hours per day.")
    st.subheader("Scoring")
    st.write("Interest = cosine similarity of your interest sliders and the destination's interest shares. "
             "Season = 1 inside the comfortable band (15 to 32 C daytime, under 200 mm rain), falling to 0 as "
             "temperature or rain leave it. Budget = share of budget left. Distance = 1 minus drive time over your limit.")
    st.subheader("Evaluation")
    st.caption("Persona checks catch obviously wrong behaviour. They do not prove accuracy. "
               "The personas and expectations were written by the author.")
    st.dataframe(evaluation.run_personas(data, origin_id=prefs.origin_id), hide_index=True)
    sens = config.PROC / "evaluation_weight_sensitivity.csv"
    if sens.exists():
        st.write("How often the top choice survives random changes to the weights:")
        st.dataframe(pd.read_csv(sens), hide_index=True)
    st.subheader("Known data issues")
    f = data["features"]
    st.write(f"- **Starting location**: distances, drive times and transport costs follow the starting city you pick. "
             f"Of the {len(data['routes'])} route records, "
             f"{int((data['routes']['data_quality'] == 'estimated').sum())} are estimates, "
             f"{int((data['routes']['data_quality'] == 'source_reported').sum())} copy a distance stated on a source page "
             f"and {int((data['routes']['data_quality'] == 'author_entered').sum())} are your own Pathankot entries.\n"
             f"- **Weather**: {int((f['weather_quality_flag'] == 'no_weather_data').sum())} destinations have no weather data "
             f"collected, so they are not scored on season (the other components are renormalised). "
             f"{int((f['weather_quality_flag'] == 'proxy').sum())} use a nearby place as a proxy.\n"
             f"- **Fares**: collected fares are Pathankot-only. Other starting cities use a per-km rate derived from "
             f"short Pathankot routes, which is a rough guide for long journeys and ignores trains and flights.\n"
             "- Three road-distance sources conflict for 7 of the original 9 destinations (from Pathankot).\n"
             "- Entered best months disagree with the weather rule for several places.\n"
             "- McLeod Ganj weather is a proxy for Dharamshala; Kangra weather looks inconsistent with neighbours.\n"
             "- No entry fees or activity costs were collected.\n"
             "- Fares come from aggregator and blog snippets, not official tariffs; 4 destinations use a derived rate.")
