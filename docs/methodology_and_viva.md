# TripSense: methodology, limitations and viva notes

## 1. What the system is
A content-based decision-support system for 9 destinations around Pathankot. It is not machine
learning: nine items give nothing to train or validate on. It filters, scores with stated rules,
combines with a weighted mean, and explains each result.

## 2. Pipeline
raw tables -> `src/load.py` (repairs encoding, parses H.MM times) -> `src/features.py`
(42 destination features, 15 destination-month features) -> `src/budget.py` and
`src/recommender.py` -> `src/similarity.py`, `src/itinerary.py` -> `app.py`.
Every assumption lives in `src/config.py`.

## 3. Scoring (each part 0 to 1)
| Part | Rule | Basis |
|---|---|---|
| Interest | cosine(user interest sliders, destination interest shares) | shares counted from collected attractions and activities |
| Season | 1 minus min(1, temp_gap/10 + rain_excess/200) for the chosen month | weather rule: comfortable = 15-32 C daytime max and < 200 mm rain; tolerances are assumptions |
| Budget | 1 - cost / budget | cost from budget.py |
| Distance | 1 - drive hours / your limit | entered drive time; estimated from km where missing |

Final score = weighted mean. Default weights are equal because nothing in the data justifies
another split. `evaluation.py` shows how often the winner changes under random weights.

## 4. Budget honesty
Transport fares are 11 ranges taken from search snippets (aggregator pages and travel blogs), not
official tariffs; 4 destinations use a rate per km derived from those ranges. Stay prices come from
21 priced listings; destinations with fewer than 3 use the pooled quantile. Food and local spending
are placeholders. The app shows what share of each total rests on collected data.

## 5. Evaluation
- Persona checks: face validity only, personas written by the author.
- Weight sensitivity: top choice unchanged under random weights for 48% to 91% of samples, depending on the persona.
  The pilgrim persona is the least stable (Vaishno Devi 48%, McLeod Ganj 34%, Amritsar 18%).
- Survey: template and comparison code are ready; no survey has been run, so no accuracy claim is made.

## 6. Known limitations
1. Three road-distance sources conflict for 7 of 9 destinations (default: the author's entries).
2. Entered best months disagree with the weather rule for several destinations.
3. McLeod Ganj weather is a Dharamshala proxy; Kangra weather and coordinates look inconsistent.
4. Entry fees and activity costs were not collected.
5. Attractions and activities lists are curated samples, and some overlap (for example Triund).
6. Itineraries do not model opening hours, distances between sights, or return-drive time.
7. Streamlit was not available in the build environment: pages were executed against a stand-in
   module (tests/test_app_smoke.py), not in a real browser.

## 7. Likely viva questions
- **Why not machine learning?** Nine destinations and no labelled outcomes. A transparent score is more defensible and can be explained.
- **Why equal weights?** No evidence supports others; sensitivity analysis quantifies the risk.
- **How do you know it works?** Unit tests with hand-checked numbers, persona face validity, weight sensitivity; the survey is the missing real validation.
- **What is real data and what is estimated?** See section 4 and `data/data_dictionary.csv`, `source_log.csv`.
- **Biggest weakness?** Budget inputs: placeholders and snippet-sourced fares.
