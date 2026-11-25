"""Evaluation without ground truth.

1. Personas: face-validity check, each persona has an expected top destination.
2. Weight sensitivity: random weight vectors, how often does the top choice change?
3. Survey: template for collecting real traveller rankings, and a comparison utility.
No claim of accuracy is made from personas; they only catch obviously wrong behaviour.
"""
import numpy as np
import pandas as pd

from . import config
from .recommender import Prefs, recommend

def _interests(**kw):
    return {i: kw.get(i, 0.0) for i in config.INTERESTS}

PERSONAS = {
    "Pilgrim family (October)": dict(month=10, travellers=4, nights=2, budget_total=40000, tier="standard",
        mode="taxi", max_drive_hours=5, interests=_interests(spiritual=5), expect=["Vaishno Devi"]),
    "Nature and trek couple (May)": dict(month=5, travellers=2, nights=3, budget_total=25000, tier="standard",
        mode="taxi", max_drive_hours=4, interests=_interests(nature=5, adventure=4), expect=["Dalhousie", "Khajjiar"]),
    "Culture seekers (April)": dict(month=4, travellers=2, nights=2, budget_total=25000, tier="standard",
        mode="taxi", max_drive_hours=4, interests=_interests(culture=5, spiritual=2), expect=["McLeod Ganj"]),
    "History buffs (November)": dict(month=11, travellers=2, nights=2, budget_total=25000, tier="standard",
        mode="taxi", max_drive_hours=4, interests=_interests(history=5, culture=2), expect=["Amritsar", "Chamba", "Kangra", "Jammu"]),
    "Tight budget solo (June)": dict(month=6, travellers=1, nights=1, budget_total=5000, tier="budget",
        mode="bus", max_drive_hours=4, interests=_interests(nature=3, culture=2), expect=[]),
}

def run_personas(data, top_k=3, origin_id="O01"):
    """Run every persona from one starting city. For Chandigarh and Delhi the drive limit is the
    UI default for that city (config.ORIGIN_DEFAULT_MAX_DRIVE), otherwise nothing is within reach."""
    rows = []
    for name, p in PERSONAS.items():
        p = dict(p); expect = p.pop("expect")
        p["origin_id"] = origin_id
        if origin_id != "O01":
            p["max_drive_hours"] = config.ORIGIN_DEFAULT_MAX_DRIVE[origin_id]
        ranked, excl = recommend(Prefs(**p), data)
        top = ranked["destination"].head(top_k).tolist()
        # The expected answers were written for the original 9 destinations and a Pathankot start,
        # so they are only checked there. For other starting cities the top 3 is shown for inspection.
        checked = bool(expect) and origin_id == "O01"
        rows.append({"origin_id": origin_id, "persona": name, "top_3": ", ".join(top),
                     "expected_any_of": ", ".join(expect) if checked else "(expectations apply to Pathankot only)",
                     "expectation_met": bool(set(top) & set(expect)) if checked else None,
                     "n_excluded": len(excl)})
    return pd.DataFrame(rows)


def run_personas_all_origins(data, top_k=3):
    return pd.concat([run_personas(data, top_k, o) for o in ["O01", "O02", "O03"]], ignore_index=True)


def weight_sensitivity(data, n_samples=100, seed=0):
    """For each persona: share of random weight vectors under which the top choice is unchanged."""
    rng = np.random.default_rng(seed)
    keys = list(config.DEFAULT_WEIGHTS)
    rows = []
    for name, p in PERSONAS.items():
        p = dict(p); p.pop("expect")
        base = recommend(Prefs(**p), data)[0]
        if base.empty:
            continue
        base_top = base["destination"].iloc[0]
        base_top3 = set(base["destination"].head(3))
        same, overlap, tops = 0, [], {}
        for _ in range(n_samples):
            w = dict(zip(keys, rng.dirichlet(np.ones(4))))
            r = recommend(Prefs(**{**p, "weights": w}), data)[0]
            if r.empty:
                continue
            t = r["destination"].iloc[0]; tops[t] = tops.get(t, 0) + 1
            same += t == base_top
            overlap.append(len(base_top3 & set(r["destination"].head(3))) / 3)
        rows.append({"persona": name, "equal_weight_top": base_top,
                     "top_unchanged_share": same / n_samples,
                     "mean_top3_overlap": float(np.mean(overlap)),
                     "tops_seen": ", ".join(f"{k} ({v / n_samples:.0%})" for k, v in
                                            sorted(tops.items(), key=lambda kv: -kv[1]))})
    return pd.DataFrame(rows)

def survey_template():
    """One row per respondent-scenario. Fill `rank_1..rank_3` with destination names."""
    cols = ["respondent_id", "scenario", "month", "travellers", "nights", "budget_total_inr",
            "interests_stated", "rank_1", "rank_2", "rank_3", "comments"]
    return pd.DataFrame(columns=cols)

def compare_to_survey(survey, data):
    """Share of respondents whose #1 is in our top 3, and top-3 overlap. Needs real survey rows."""
    rows = []
    for _, s in survey.dropna(subset=["rank_1"]).iterrows():
        interests = {i: 0.0 for i in config.INTERESTS}
        for tok in str(s["interests_stated"]).replace(",", "|").split("|"):
            tok = tok.strip().lower()
            if tok in interests:
                interests[tok] = 1.0
        if sum(interests.values()) == 0:
            interests = {i: 1.0 for i in config.INTERESTS}
        prefs = Prefs(month=int(s["month"]), travellers=int(s["travellers"]), nights=int(s["nights"]),
                      budget_total=float(s["budget_total_inr"]), interests=interests,
                      max_drive_hours=99)
        ours = recommend(prefs, data)[0]["destination"].head(3).tolist()
        theirs = [s[c] for c in ("rank_1", "rank_2", "rank_3") if pd.notna(s[c])]
        rows.append({"respondent_id": s["respondent_id"], "top1_in_our_top3": s["rank_1"] in ours,
                     "top3_overlap": len(set(ours) & set(theirs)) / 3})
    return pd.DataFrame(rows)

def main():
    from .data_access import load_engine_data
    d = load_engine_data()
    out = config.PROC
    run_personas_all_origins(d).to_csv(out / "evaluation_personas.csv", index=False)
    weight_sensitivity(d).to_csv(out / "evaluation_weight_sensitivity.csv", index=False)
    survey_template().to_csv(out / "survey_template.csv", index=False)
    print(run_personas_all_origins(d).to_string()); print(weight_sensitivity(d).to_string())

if __name__ == "__main__":
    main()
