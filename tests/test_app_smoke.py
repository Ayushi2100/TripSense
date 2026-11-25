"""Runs every page with a fake streamlit. Run: python -m tests.test_app_smoke
Real Streamlit is not required; see README for how to run the real app."""
from tests.fake_streamlit import install, FakeSt

install()
import importlib
from src.data_access import load_engine_data
from src.recommender import Prefs
from app_ui import pages
from src.data_access import origin_view
from app_ui.inputs import sidebar_inputs


PAGE_NAMES = ["home", "plan_my_trip", "recommendations", "destination_details", "budget_planner",
              "compare", "itinerary", "analytics", "methods"]


def test_all_pages_run():
    data = load_engine_data()
    for origin in ["Pathankot", "Chandigarh", "Delhi"]:
        FakeSt.overrides = {"Where are you starting your journey?": origin}
        prefs = sidebar_inputs()
        assert isinstance(prefs, Prefs) and prefs.origin_id == {"Pathankot": "O01", "Chandigarh": "O02", "Delhi": "O03"}[origin]
        view = origin_view(data, prefs.origin_id)
        for name in PAGE_NAMES:
            getattr(pages, name)(view, prefs)
    FakeSt.overrides = {}
    assert "dataframe" in FakeSt.calls and "download_button" in FakeSt.calls


def test_chandigarh_as_destination_when_starting_in_chandigarh():
    """Selecting Chandigarh as the start must not crash the destination pages for Chandigarh itself."""
    data = load_engine_data()
    FakeSt.overrides = {"Where are you starting your journey?": "Chandigarh", "Destination": "Chandigarh"}
    prefs = sidebar_inputs()
    view = origin_view(data, prefs.origin_id)
    for name in ["destination_details", "budget_planner", "itinerary"]:
        getattr(pages, name)(view, prefs)
    FakeSt.overrides = {}


def test_destination_with_no_collected_listings_shows_message_and_pooled_label():
    """Ranjit Sagar Lake has no accommodation rows: details, budget and itinerary must still render."""
    data = load_engine_data()
    for origin in ["Pathankot", "Chandigarh", "Delhi"]:
        FakeSt.overrides = {"Where are you starting your journey?": origin, "Destination": "Ranjit Sagar Lake"}
        FakeSt.texts = []
        prefs = sidebar_inputs()
        view = origin_view(data, prefs.origin_id)
        for name in ["destination_details", "budget_planner", "itinerary"]:
            getattr(pages, name)(view, prefs)
        seen = " ".join(FakeSt.texts)
        assert "No accommodation listings were collected for Ranjit Sagar Lake" in seen, origin
        assert "pooled estimate" in seen, origin
    FakeSt.overrides = {}


def test_app_module_runs():
    import sys
    sys.modules.pop("app", None)
    importlib.import_module("app")


if __name__ == "__main__":
    test_all_pages_run(); test_chandigarh_as_destination_when_starting_in_chandigarh(); test_destination_with_no_collected_listings_shows_message_and_pooled_label(); test_app_module_runs(); print("smoke tests passed")
