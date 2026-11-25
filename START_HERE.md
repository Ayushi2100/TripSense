# TripSense — Start Here (Windows)

## 1. Requirements
Install Python 3.10 or newer and make sure `python` works in PowerShell.

## 2. First launch
Double-click `START_TRIPSENSE.bat`. On first run it creates a local `.venv`, installs the packages in `requirements.txt`, rebuilds the processed feature tables, and launches the Streamlit app.

## 3. Later launches
Double-click `RUN_TRIPSENSE.bat`. It uses the existing virtual environment and launches the app.

If Windows blocks the script, open PowerShell in this folder and run:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.build_features
.\.venv\Scripts\python.exe -m src.evaluation
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## What is included
- 9-page Streamlit app
- destination recommendations and explanations
- budget estimation and itinerary planning
- destination comparison and analytics
- raw datasets, source registers, processed features, figures, notebooks, tests, and methodology notes

## Data limitations
The app deliberately labels estimates and known data conflicts. Some fees, activity costs, fares, ratings, and travel-time values are missing or provisional. Do not treat estimated values as verified quotes. The raw CSV files are retained as collected; feature-building writes derived files under `data/processed/`.

## Test commands
```powershell
.\.venv\Scripts\python.exe -m tests.test_features
.\.venv\Scripts\python.exe -m tests.test_engine
.\.venv\Scripts\python.exe -m tests.test_app_smoke
```
