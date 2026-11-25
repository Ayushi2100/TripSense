"""Unit tests for budget, recommender, similarity, itinerary. Run: python -m tests.test_engine"""
import math

import numpy as np

from src import budget, config
from src.data_access import load_engine_data
from src.itinerary import build, parse_duration_min
from src.recommender import Prefs, cosine, recommend
from src.similarity import group_similarities, similar_to

D = load_engine_data()


def test_cosine():
    assert abs(cosine([1, 0], [1, 0]) - 1) < 1e-9
    assert abs(cosine([1, 0], [0, 1])) < 1e-9
    assert cosine([0, 0], [1, 1]) == 0.0


def test_parse_duration():
    assert parse_duration_min("~1–2 hours") == 90
    assert parse_duration_min("~30–60 min") == 45
    assert parse_duration_min("~4 hours one way") == 480
    assert parse_duration_min("unknown") is None and parse_duration_min(None) is None


def test_budget_hand_check():
    # Dharamshala, taxi: midpoint of 850-1300 = 1075 one way, 2 travellers -> 1 car -> 2150 return
    e = budget.estimate("D01", 2, 2, "standard", "taxi", D)
    t = e["table"].set_index("item")
    # outward and return are separate lines, each half of the old return total
    assert t.loc["Outward transport: Pathankot to Dharamshala", "cost_inr"] == 1075
    assert t.loc["Return transport: Dharamshala to Pathankot", "cost_inr"] == 1075
    assert t.loc["Outward transport: Pathankot to Dharamshala", "basis"] == "collected"
    # food placeholder: 700 x 2 people x 3 days
    assert t.loc["Food", "cost_inr"] == 700 * 2 * 3
    assert t.loc["Food", "basis"] == "placeholder"
    assert abs(e["total"] - t["cost_inr"].sum()) < 1e-6
    assert 0 <= e["data_backed_share"] <= 1


def test_budget_derived_when_no_fare():
    e = budget.estimate("D06", 2, 1, "standard", "taxi", D)   # Kangra: no collected fare
    assert e["table"].iloc[0]["basis"] == "derived"


def test_taxi_cars_scale():
    a = budget.estimate("D01", 4, 1, "standard", "taxi", D)["table"].iloc[0]["cost_inr"]
    b = budget.estimate("D01", 5, 1, "standard", "taxi", D)["table"].iloc[0]["cost_inr"]
    assert b == 2 * a


def test_recommender_ranking_and_filters():
    r, ex = recommend(Prefs(), D)
    assert r["score"].is_monotonic_decreasing and r["score"].between(0, 1).all()
    assert len(r) + len(ex) == 30
    r2, ex2 = recommend(Prefs(budget_total=2000), D)
    assert r2.empty and len(ex2) == 30 and ex2["reason"].str.contains("budget").all()
    r3, ex3 = recommend(Prefs(max_drive_hours=2.3), D)
    assert (r3["drive_hours"] <= 2.3).all()


def test_interest_changes_winner():
    spiritual = {i: 0.0 for i in config.INTERESTS}; spiritual["spiritual"] = 5
    r, _ = recommend(Prefs(month=10, interests=spiritual, budget_total=40000, max_drive_hours=5), D)
    assert r.iloc[0]["destination"] == "Vaishno Devi"


def test_weights_zero_ignores_component():
    w = {"interest": 0, "season": 0, "budget": 0, "distance": 1}
    r, _ = recommend(Prefs(weights=w, budget_total=40000, max_drive_hours=8), D)
    assert np.allclose(r["score"], r["s_distance"])


def test_similarity_properties():
    g = group_similarities(D["features"])
    for m in g.values():
        assert np.allclose(np.diag(m.values), 1) and np.allclose(m.values, m.values.T)
        assert m.values.min() >= -1e-9 and m.values.max() <= 1 + 1e-9
    s = similar_to("Dharamshala", D["features"], k=3)
    assert len(s) == 3 and "Dharamshala" not in s["destination"].values


def test_itinerary_respects_cap_and_loses_nothing():
    plan, left, used = build("D01", 3, {"nature": 3}, D)
    placed = sum(len(d) for d in plan)
    total = len([1 for _ in __import__("src.itinerary", fromlist=["x"]).candidate_items("D01", D)])
    assert placed + len(left) == total
    for day, u in zip(plan, used):
        assert u <= config.SIGHTSEEING_MIN_PER_DAY or len(day) == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        f(); print("ok", f.__name__)
    print(f"{len(fns)} engine tests passed")
