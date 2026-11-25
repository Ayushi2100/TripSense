# TripSense

A content-based travel decision-support project: 30 destinations in northern India, three selectable starting cities (Pathankot, Chandigarh, Delhi).

**Status:** full working project: EDA, feature engineering, budget estimator, recommender, similar destinations,
itinerary builder, evaluation and a Streamlit app. Data collection and cleaning are not finished; known conflicts
and placeholders are flagged in the app, not hidden. See `docs/methodology_and_viva.md` and `docs/phase4_5_summary.md`.

## Folder layout

```text
data/raw/         source CSVs exactly as collected (only weather(1).csv was renamed to weather.csv)
data/processed/   derived tables written by the pipeline
app.py            Streamlit entry point (9 pages)
app_ui/           page functions and sidebar inputs
src/              validate_data.py (13 data checks), config.py (all assumptions), load.py, features.py, build_features.py, eda_plots.py,
                  data_access.py, budget.py, recommender.py, similarity.py, itinerary.py, evaluation.py
notebooks/        03_eda, 04_feature_engineering, 05_recommendation_system, 06_evaluation
reports/figures/  fig01 ... fig10 (PNG)
tests/            unit tests for parsers and feature rules
docs/             findings and decisions
```

## Run

```bash
pip install -r requirements.txt
python -m src.build_features      # writes data/processed/*.csv
python -m src.eda_plots           # writes reports/figures/*.png
python -m src.evaluation          # personas + weight sensitivity -> data/processed
python -m tests.test_features     # unit tests (features)
python -m tests.test_engine       # unit tests (budget, recommender, similarity, itinerary)
python -m tests.test_origin       # the starting city really changes distance, time, cost and ranking
python -m tests.test_app_smoke    # runs every page for all three starting cities against a fake streamlit
python -m src.validate_data       # data checks: IDs, references, 90 routes, weather coverage

streamlit run app.py              # the app (needs streamlit installed)
```

Open the notebooks from inside the `notebooks/` folder.

## Outputs in `data/processed/`

| File | Content |
|---|---|
| `destination_features.csv` | one row per destination, 42 columns |
| `destination_month_features.csv` | one row per destination and month (108 rows) |
| `feature_dictionary.csv` | every feature: meaning, raw or derived, method, limitation |
| `interest_mapping.csv` | how attraction and activity types map to interests |
| `season_rule_sensitivity.csv` | comfortable-month counts under 9 threshold settings |
| `interest_similarity.csv` | cosine similarity of interest shares (preview) |
| `evaluation_personas.csv`, `evaluation_weight_sensitivity.csv` | persona checks and weight sensitivity |
| `survey_template.csv` | empty template for real traveller rankings |

## Principles

- Raw data is never edited; every assumption lives in `src/config.py`.
- Features come from countable records or a stated rule, not from opinion.
- Unknown values stay unknown (blank), never zero or a guess.
- This is a content-based decision-support system, not machine learning: 30 items are too few to train on.
- Route data (`route_data.csv`) is separate from destination data. Most routes are estimates; see `docs/expansion_30_destinations.md`.

## 30-destination expansion

See `docs/expansion_30_destinations.md` for what was added, how each number is labelled, and the open gaps.
Original files are backed up in `data/_backup_before_30_destinations/`; the sourced batches that were merged
are in `data/_stage4_collected_batches/`; the scripts that did the merge are in `scripts/`.
