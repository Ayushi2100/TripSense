"""Tests that the starting city really drives distance, time, cost and ranking.
Run: python -m tests.test_origin"""
import numpy as np
import pandas as pd

from src import budget, config
from src.data_access import load_engine_data, origin_view, effective_drive_hours
from src.features import apply_origin
from src.recommender import Prefs, recommend
from src.validate_data import run_checks

D = load_engine_data()


def test_three_origins_loaded():
    assert list(D["origins"].origin_name) == ["Pathankot", "Chandigarh", "Delhi"]
    assert len(D["routes"]) == 90 and len(D["features"]) == 30


def test_view_uses_selected_origin_distances():
    km = {}
    for o in ["O01", "O02", "O03"]:
        f = origin_view(D, o)["features"]
        assert (f["origin_id"] == o).all()
        km[o] = f.set_index("destination")["road_distance_km"]
    # Shimla: close to Chandigarh, far from Delhi and Pathankot
    assert km["O02"]["Shimla"] < km["O03"]["Shimla"] < km["O01"]["Shimla"] + 100
    assert km["O02"]["Shimla"] < 150
    # Dharamshala is nearest to Pathankot
    assert km["O01"]["Dharamshala"] < km["O02"]["Dharamshala"] < km["O03"]["Dharamshala"]
    # nothing is silently reusing Pathankot figures
    assert not np.allclose(km["O01"].dropna(), km["O03"].reindex(km["O01"].dropna().index))


def test_pathankot_values_for_original_nine_unchanged():
    f = origin_view(D, "O01")["features"].set_index("destination_id")
    assert list(f.loc["D01":"D09", "road_distance_km"]) == [94, 94, 89, 101, 108, 115, 112, 117, 163]


def test_straight_line_never_exceeds_road():
    for o in ["O01", "O02", "O03"]:
        f = origin_view(D, o)["features"]
        f = f[f.route_available]
        assert (f.road_distance_km >= f.straight_km).all()


def test_transport_cost_follows_origin():
    cost = {}
    for o in ["O01", "O02", "O03"]:
        v = origin_view(D, o)
        e = budget.estimate("D17", 2, 2, "standard", "taxi", v)["table"]       # Shimla
        assert o in {"O01": "O01", "O02": "O02", "O03": "O03"}
        cost[o] = e.iloc[0]["cost_inr"]
        assert e.iloc[0]["item"].startswith("Outward transport: " + v["features"].origin_name.iloc[0])
    assert cost["O02"] < cost["O01"] and cost["O02"] < cost["O03"]


def test_collected_pathankot_fares_not_used_for_other_origins():
    e1 = budget.estimate("D01", 2, 2, "standard", "taxi", origin_view(D, "O01"))["table"].iloc[0]
    e3 = budget.estimate("D01", 2, 2, "standard", "taxi", origin_view(D, "O03"))["table"].iloc[0]
    assert e1["basis"] == "collected" and e3["basis"] == "derived"
    assert e3["cost_inr"] > 4 * e1["cost_inr"]


def test_outward_equals_return_and_total_adds_up():
    e = budget.estimate("D14", 3, 3, "comfort", "bus", origin_view(D, "O03"))
    t = e["table"]
    assert t.iloc[0]["cost_inr"] == t.iloc[1]["cost_inr"]
    assert abs(e["total"] - t["cost_inr"].sum()) < 1e-6


def test_ranking_changes_with_origin_but_scores_use_same_formula():
    base = dict(month=5, budget_total=60000, travellers=2, nights=3, max_drive_hours=12)
    r = {o: recommend(Prefs(origin_id=o, **base), D)[0] for o in ["O01", "O02", "O03"]}
    tops = [r[o]["destination"].iloc[0] for o in r]
    assert len(set(r[o]["destination"].head(5).tolist().__str__() for o in r)) > 1
    # same destination, same interests/season: only distance/budget components differ
    for dest in ["Shimla", "Manali"]:
        a = r["O01"].set_index("destination").loc[dest]; b = r["O03"].set_index("destination").loc[dest]
        assert a["s_interest"] == b["s_interest"] and a["s_season"] == b["s_season"]
        assert a["s_distance"] != b["s_distance"]


def test_starting_city_excluded_as_destination():
    r, ex = recommend(Prefs(origin_id="O02", max_drive_hours=30, budget_total=300000), D)
    assert "Chandigarh" not in r.destination.tolist()
    assert ex[ex.destination == "Chandigarh"].reason.str.contains("starting city").all()
    r1, _ = recommend(Prefs(origin_id="O01", max_drive_hours=30, budget_total=300000), D)
    assert "Chandigarh" in r1.destination.tolist()


def test_missing_weather_not_scored_and_warned():
    # every destination now has weather (some via flagged proxy), so remove Solan's months to test the no-data path
    D2 = dict(D)
    D2.pop("_views", None)
    D2["months"] = D["months"][D["months"].destination_id != "D18"]
    r, _ = recommend(Prefs(origin_id="O02", max_drive_hours=30, budget_total=300000), D2)
    row = r[r.destination == "Solan"].iloc[0]
    assert pd.isna(row["s_season"]) and "no weather data" in row["warnings"]
    assert 0 <= row["score"] <= 1


def test_all_origins_handle_all_30_destinations():
    for o in ["O01", "O02", "O03"]:
        r, ex = recommend(Prefs(origin_id=o, max_drive_hours=30, budget_total=500000), D)
        assert len(r) + len(ex) == 30
        assert r["score"].between(0, 1).all()


def test_validation_all_pass_and_gap_must_be_declared():
    assert [n for n, ok, _ in run_checks() if not ok] == []
    # a destination with no listing and no declaration must fail check 8b
    from src.validate_data import _tables
    t = _tables()
    t["accommodation_coverage"] = t["accommodation_coverage"].iloc[0:0]
    assert [n for n, ok, _ in run_checks(t) if not ok and n.startswith("8b")]
    # declaring a destination that does have rows is a contradiction
    t = _tables()
    t["accommodation_coverage"] = pd.DataFrame({"destination_id": ["D28", "D01"],
                                                "coverage_status": ["no_collected_listings"] * 2})
    assert [n for n, ok, _ in run_checks(t) if not ok and n.startswith("8b")]


def test_no_listing_destination_is_budgeted_as_labelled_pooled_estimate():
    from src import budget as bud
    d = origin_view(D, "O01")
    e = bud.estimate("D28", 2, 2, "standard", "taxi", d)
    stay = e["table"][e["table"].item == "Stay"].iloc[0]
    assert stay.basis == "pooled" and "ESTIMATE" in stay.how and "0 priced" in stay.how
    assert (D["accommodation"].destination_id == "D28").sum() == 0
    assert Prefs().budget_total == 10000.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        f(); print("ok", f.__name__)
    print(f"{len(fns)} origin tests passed")
