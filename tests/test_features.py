"""Run from the TripSense folder:  python -m tests.test_features   (or pytest)"""
import numpy as np
import pandas as pd

from src import config, features, load


def test_parse_hmm():
    assert load.parse_hmm("2.2") == 2.33      # 2h20m
    assert load.parse_hmm("3.26") == 3.43     # 3h26m
    assert load.parse_hmm("2.15") == 2.25
    assert np.isnan(load.parse_hmm("3.7"))    # 70 minutes is impossible
    assert np.isnan(load.parse_hmm(None))


def test_parse_months():
    assert load.parse_months("1,2,12") == [1, 2, 12]
    assert load.parse_months("3|4|5") == [3, 4, 5]
    assert load.parse_months(np.nan) == []


def test_fix_mojibake():
    assert load.fix_mojibake("Dharamkotâ€“Triund") == "Dharamkot–Triund"
    assert load.fix_mojibake("plain") == "plain"


def test_haversine_known_distance():
    # Delhi to Mumbai is about 1,150 km in a straight line
    assert abs(features.haversine_km(28.61, 77.21, 19.08, 72.88) - 1150) < 30


def test_season_category_rules():
    r = config.SEASON_RULES
    assert features.season_category(25, 50, r) == "comfortable"
    assert features.season_category(25, 300, r) == "wet"        # wet is checked first
    assert features.season_category(36, 50, r) == "hot"
    assert features.season_category(10, 50, r) == "cold"
    assert features.season_category(15, 50, r) == "comfortable"  # boundary is inclusive
    assert features.season_category(40, 250, r) == "wet"


def test_activity_interests():
    assert features.activity_interests("Culture / Heritage") == ["culture", "history"]
    assert features.activity_interests("Pilgrimage / Trekking") == ["spiritual"]
    assert features.activity_interests("Pilgrimage Transport") == []
    assert features.activity_interests("Boating / Water activity") == ["adventure"]
    assert features.activity_interests("Golf") == []


def test_pipeline_invariants():
    tables = load.load_all()
    feats, months = features.build_all(tables)
    assert len(feats) == 30 and feats.destination_id.is_unique
    share_cols = [f"share_{i}" for i in config.INTERESTS]
    assert np.allclose(feats[share_cols].sum(axis=1), 1.0, atol=1e-3)
    assert ((feats[share_cols] >= 0) & (feats[share_cols] <= 1)).all().all()
    # every collected record is either mapped or counted as unmapped
    n_records = len(tables["attractions"]) + len(tables["activities"])
    assert (feats.n_attractions + feats.n_activities).sum() == n_records
    n_weather = tables["weather"].destination_id.nunique()   # all 30 have weather (many via flagged proxy)
    assert len(months) == n_weather * 12 and not months.duplicated(["destination_id", "month"]).any()
    # comfortable-month count agrees with the monthly table
    counted = feats.set_index("destination_id").n_comfortable_months.dropna()
    assert (counted == months.groupby("destination_id").comfortable.sum().reindex(counted.index)).all()
    # destinations with no weather data are flagged, not given invented months
    assert (feats.loc[feats.n_comfortable_months.isna(), "weather_quality_flag"] == "no_weather_data").all()
    # road distance cannot be shorter than the straight line (checked on the chosen source)
    ok = feats.dropna(subset=["detour_ratio"])
    assert (ok.detour_ratio >= 1.0).all(), ok.loc[ok.detour_ratio < 1.0, ["destination", "detour_ratio"]]
    # missing times stay missing, never zero
    assert feats.loc[feats.destination == "Kangra", "travel_time_hrs"].isna().all()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
