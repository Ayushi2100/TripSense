"""TripSense Streamlit app. Run: streamlit run app.py"""
import streamlit as st

from app_ui import pages
from app_ui.inputs import sidebar_inputs
from src.data_access import load_engine_data, origin_view

st.set_page_config(page_title="TripSense | Travel, thoughtfully planned", page_icon="✦", layout="wide", initial_sidebar_state="expanded")


def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ts-ink:#18352f; --ts-green:#1e5948; --ts-mint:#e7f1eb; --ts-cream:#f7f7f2; --ts-orange:#df815b; }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp { background:var(--ts-cream); color:var(--ts-ink); }
    [data-testid="stHeader"] { background:rgba(247,247,242,.92); }
    [data-testid="stSidebar"] { background:#edf2ec; border-right:1px solid #dce5dc; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color:var(--ts-ink); font-family:'Manrope',sans-serif; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color:#3d5a50; font-weight:600; }
    h1, h2, h3 { font-family:'Manrope',sans-serif !important; color:var(--ts-ink) !important; letter-spacing:-.035em; }
    h1 { font-size:2.25rem !important; font-weight:800 !important; }
    h2 { font-size:1.55rem !important; font-weight:750 !important; }
    h3 { font-size:1.15rem !important; font-weight:700 !important; }
    p, li, label { color:#3f554e; }
    [data-testid="stMetric"] { background:#fff; border:1px solid #e3e9e1; padding:18px 20px; border-radius:18px; box-shadow:0 5px 18px rgba(24,53,47,.04); }
    [data-testid="stMetricLabel"] { color:#678076 !important; font-weight:600; }
    [data-testid="stMetricValue"] { color:var(--ts-green) !important; font-family:'Manrope',sans-serif; font-weight:800; }
    .stButton > button, [data-testid="stFormSubmitButton"] button { border-radius:12px; border:0; background:var(--ts-green); color:white; font-weight:700; padding:.6rem 1rem; }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover { background:#174637; color:white; border:0; }
    [data-testid="stAlert"] { border-radius:14px; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid #e2e9e1; border-radius:14px; overflow:hidden; }
    [data-baseweb="select"] > div, [data-baseweb="input"] > div { border-radius:10px; }
    div[data-testid="stExpander"] { border:1px solid #e0e8df; border-radius:14px; background:white; }
    .ts-eyebrow { text-transform:uppercase; letter-spacing:.15em; font-size:.72rem; font-weight:800; color:#e7b28f; }
    .ts-hero { padding:2.3rem 2.4rem; border-radius:26px; color:white; background:linear-gradient(115deg,#173f35 0%,#246b53 68%,#52866c 100%); position:relative; overflow:hidden; margin:.3rem 0 1.25rem; }
    .ts-hero:after { content:'✦'; position:absolute; right:5%; top:-45px; font-size:13rem; color:rgba(255,255,255,.07); transform:rotate(15deg); }
    .ts-hero h1 { color:white !important; font-size:3rem !important; margin:.45rem 0 .6rem; line-height:1.1; }
    .ts-hero p { color:#e4efe8; font-size:1.05rem; max-width:680px; line-height:1.65; margin-bottom:0; }
    .ts-stat { background:white; border:1px solid #e3e9e1; border-radius:17px; padding:17px 19px; min-height:105px; }
    .ts-stat-label { color:#71857b; font-size:.82rem; font-weight:600; }
    .ts-stat-value { color:#1e5948; font-family:'Manrope',sans-serif; font-size:1.8rem; font-weight:800; margin-top:5px; }
    .ts-section-label { color:#df815b; text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:800; margin-bottom:.25rem; }
    .ts-step { background:white; border:1px solid #e3e9e1; border-radius:16px; padding:18px; min-height:145px; }
    .ts-step-num { color:#df815b; font-size:.78rem; font-weight:800; letter-spacing:.1em; }
    .ts-step-title { color:#18352f; font-weight:800; font-size:1rem; margin:.45rem 0; }
    .ts-step-copy { color:#60766b; font-size:.9rem; line-height:1.5; }
    footer { visibility:hidden; }
    </style>
    """, unsafe_allow_html=True)


PAGES = {
    "Home": pages.home,
    "Plan My Trip": pages.plan_my_trip,
    "Recommendations": pages.recommendations,
    "Destination Details": pages.destination_details,
    "Budget Planner": pages.budget_planner,
    "Compare Destinations": pages.compare,
    "Itinerary": pages.itinerary,
    "Travel Analytics": pages.analytics,
    "Methods and Data": pages.methods,
}


@st.cache_resource
def get_data():
    return load_engine_data()


def main():
    apply_theme()
    data = get_data()
    st.sidebar.markdown("<div style='font-size:1.45rem;font-weight:800;color:#1e5948;font-family:Manrope,sans-serif'>✦ TripSense</div><div style='font-size:.78rem;color:#6b8277;margin:.15rem 0 1.2rem'>YOUR NEXT GOOD GETAWAY</div>", unsafe_allow_html=True)
    page = st.sidebar.radio("Page", list(PAGES), index=0)
    prefs = sidebar_inputs()
    PAGES[page](origin_view(data, prefs.origin_id), prefs)   # every page sees the selected origin's routes


main()
