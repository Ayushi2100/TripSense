"""Phase 4 charts. Run all with:  python -m src.eda_plots   (from the TripSense folder).

Style rules (validated palette, one hue for magnitude, no more than 3 hues in grids,
direct labels, recessive grid) follow the dataviz skill. Colour never carries meaning
alone: every coloured cell or mark also has a letter, label or value.
"""
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from . import config, features, load

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NEUTRAL = "#e1e0d9", "#c3c2b7", "#e9e8e3"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]   # validated slots 1-5
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
CMAP = LinearSegmentedColormap.from_list("tripsense_blue", SEQ)
MARK = {"proxy": "\u2020", "inconsistent_with_neighbour": "\u2021"}


def _style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.edgecolor": AXIS, "font.family": "DejaVu Sans", "font.size": 9.5,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def _lum(color):
    r, g, b = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in to_rgb(color)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _text_on(color):
    if color == CAT[3]:
        return INK
    return "#ffffff" if _lum(color) < 0.30 else INK


def _wrap(name):
    return name.replace(" ", "\n", 1) if " " in name else name


def _title(fig, title, subtitle=None, note=None):
    fig.text(0.012, 0.975, title, fontsize=13, fontweight="bold", ha="left", va="top", color=INK)
    if subtitle:
        fig.text(0.012, 0.925, subtitle, fontsize=9.5, ha="left", va="top", color=INK2)
    if note:
        fig.text(0.012, 0.012, "\n".join(textwrap.wrap(note, width=165)), fontsize=8, ha="left",
                 va="bottom", color=MUTED, linespacing=1.4)


def _context():
    _style()
    # The EDA figures (and their written titles) describe the ORIGINAL nine destinations, whose
    # data was fully collected and checked. The 21 added destinations are not plotted here:
    # many lack weather rows, and the titles state findings about these nine.
    nine = [f"D{i:02d}" for i in range(1, 10)]
    tables = {k: (v[v.destination_id.isin(nine)].copy() if "destination_id" in v.columns else v)
              for k, v in load.load_all().items()}
    feats = pd.read_csv(config.PROC / "destination_features.csv")
    feats = feats[feats.destination_id.isin(nine)].reset_index(drop=True)
    months = pd.read_csv(config.PROC / "destination_month_features.csv")
    months = months[months.destination_id.isin(nine)].reset_index(drop=True)
    order = feats.sort_values("elevation_m", ascending=False)
    ids = order.destination_id.tolist()
    names = {r.destination_id: r.destination + (" " + MARK[r.weather_quality_flag]
             if r.weather_quality_flag in MARK else "") for r in feats.itertuples()}
    return tables, feats, months, ids, names


def _save(fig, name):
    config.FIG.mkdir(parents=True, exist_ok=True)
    path = config.FIG / name
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _heatmap(ax, mat, xlabels, ylabels, fmt, vmin, vmax):
    ax.pcolormesh(np.arange(mat.shape[1] + 1), np.arange(mat.shape[0] + 1), np.ma.masked_invalid(mat),
                  cmap=CMAP, vmin=vmin, vmax=vmax, edgecolors=SURFACE, linewidth=2)
    ax.set_ylim(mat.shape[0], 0)
    ax.set_xticks(np.arange(mat.shape[1]) + 0.5)
    ax.set_xticklabels(xlabels)
    ax.set_yticks(np.arange(mat.shape[0]) + 0.5)
    ax.set_yticklabels(ylabels)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if not np.isnan(v):
                bg = CMAP((v - vmin) / (vmax - vmin))
                ax.text(j + 0.5, i + 0.5, fmt(v), ha="center", va="center", fontsize=8.5, color=_text_on(bg))


# ------------------------------------------------------------------ figures
def fig_coverage():
    tables, feats, months, ids, names = _context()
    d = tables["destinations"].set_index("destination_id")
    att, act = tables["attractions"], tables["activities"]
    tr, acc, wx = tables["transportation"], tables["accommodation"], tables["weather"]
    by = lambda df, col: df.groupby("destination_id")[col].apply(lambda s: s.notna().mean())
    rows = {
        "Coordinates and elevation": d[["latitude", "longitude", "elevation_m"]].notna().mean(axis=1),
        "Road distance and drive time": d[["road_distance_km", "travel_time_hrs"]].notna().mean(axis=1),
        "Rating and review count": d[["rating", "rating_count"]].notna().mean(axis=1),
        "Recommended stay (days)": d[["recommended_days_min", "recommended_days_max"]].notna().mean(axis=1),
        "Attraction entry fee": by(att, "entry_fee_inr"),
        "Activity cost": by(act, "estimated_cost_inr"),
        "Transport fare": by(tr, "fare_inr"),
        "Accommodation price": by(acc, "displayed_total_per_night_inr"),
        "Weather (own series, not a proxy)": 1 - wx.groupby("destination_id").is_proxy_data.max().astype(float),
    }
    mat = np.array([[rows[r].get(i, 0.0) for i in ids] for r in rows]) * 100
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    _heatmap(ax, mat, [_wrap(names[i]) for i in ids], list(rows), lambda v: f"{v:.0f}%", 0, 100)
    fig.subplots_adjust(left=0.24, right=0.985, top=0.80, bottom=0.08)
    _title(fig, "Locations and weather are complete; fees, fares, ratings and stay lengths are almost all missing",
           "Share of records with a value, by destination (ordered from highest to lowest elevation)",
           "Blank cells are left blank on purpose rather than filled with guesses.  "
           "\u2020 Dharamshala weather used as a proxy.  \u2021 weather series flagged as inconsistent with neighbours.")
    return _save(fig, "fig01_data_coverage.png")


def _climate_heatmap(column, title, subtitle, fname, fmt, vmin, vmax, note=None):
    tables, feats, months, ids, names = _context()
    piv = months.pivot(index="destination_id", columns="month", values=column).reindex(ids)
    fig, ax = plt.subplots(figsize=(10.5, 4.9))
    _heatmap(ax, piv.values.astype(float), features.MONTH_NAMES, [names[i] for i in ids], fmt, vmin, vmax)
    fig.subplots_adjust(left=0.14, right=0.985, top=0.82, bottom=0.14)
    _title(fig, title, subtitle,
           note or "Source: weather.csv (Climate-Data.org monthly tables, WeatherAndClimate.com for Kangra).  "
           "\u2020 Dharamshala series used as proxy for McLeod Ganj.  \u2021 Kangra rainfall and temperatures look "
           "inconsistent with its neighbours and need checking.")
    return _save(fig, fname)


def fig_temperature():
    return _climate_heatmap("avg_temp_max_c", "Hill towns peak at 24\u201328 \u00b0C by day; Amritsar and Jammu reach 37\u201339 \u00b0C",
                            "Average daily maximum temperature (\u00b0C) by month, ordered from highest to lowest elevation",
                            "fig02_monthly_max_temp.png", lambda v: f"{v:.0f}", 0, 42)


def fig_rainfall():
    return _climate_heatmap("rainfall_mm", "July and August dominate the rainfall everywhere in the hills",
                            "Average monthly rainfall (mm) by month, ordered from highest to lowest elevation",
                            "fig03_monthly_rainfall.png", lambda v: f"{v:.0f}", 0, 400,
                            note="Khajjiar, Dalhousie and Chamba carry identical rainfall figures, and McLeod Ganj copies "
                                 "Dharamshala (proxy), so rainfall cannot tell those places apart.  Source: weather.csv.  "
                                 "\u2020 proxy series.  \u2021 Kangra's rainfall (361 mm a year against 1,401 mm in Dharamshala) "
                                 "looks inconsistent and needs checking.")


def _month_grid(fig, ax, ids, names, cells, right_text=None):
    n = len(ids)
    for i, dest_id in enumerate(ids):
        for m in range(1, 13):
            fill, glyph = cells[(dest_id, m)]
            ax.add_patch(Rectangle((m - 1 + 0.04, i + 0.04), 0.92, 0.92, facecolor=fill, edgecolor="none"))
            if glyph:
                ax.text(m - 0.5, i + 0.5, glyph, ha="center", va="center", fontsize=9,
                        color=_text_on(fill), fontweight="bold")
        if right_text:
            ax.text(12.25, i + 0.5, right_text[dest_id], ha="left", va="center", fontsize=9, color=INK2)
    ax.set_xlim(0, 12)
    ax.set_ylim(n, 0)
    ax.set_xticks(np.arange(12) + 0.5)
    ax.set_xticklabels(features.MONTH_NAMES)
    ax.set_yticks(np.arange(n) + 0.5)
    ax.set_yticklabels([names[i] for i in ids])
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)


def fig_season_grid():
    tables, feats, months, ids, names = _context()
    letter = {"hot": "H", "cold": "C", "wet": "W"}
    cells = {(r.destination_id, r.month): ((CAT[0], "\u2713") if r.comfortable else (NEUTRAL, letter[r.category]))
             for r in months.itertuples()}
    f = feats.set_index("destination_id")
    right = {i: f"{f.n_comfortable_months[i]} of 12" for i in ids}
    fig, ax = plt.subplots(figsize=(10.5, 4.9))
    _month_grid(fig, ax, ids, names, cells, right)
    fig.subplots_adjust(left=0.14, right=0.90, top=0.82, bottom=0.14)
    r = config.SEASON_RULES
    _title(fig, "Weather alone leaves 5 to 8 comfortable months per destination",
           f"\u2713 = comfortable: daytime maximum {r['cold_tmax']:.0f}\u2013{r['hot_tmax']:.0f} \u00b0C and rainfall under "
           f"{r['wet_mm']:.0f} mm.   H = too hot, C = too cold, W = too wet (wet is checked first)",
           "Thresholds are assumptions, tested in season_rule_sensitivity.csv.  \u2020 proxy series.  "
           "\u2021 Kangra's series looks unreliable, so its row is unconfirmed.")
    return _save(fig, "fig04_comfortable_months.png")


def fig_agreement():
    tables, feats, months, ids, names = _context()
    spec = {"both": (CAT[0], "\u2713"), "entered_only": (CAT[1], "E"),
            "weather_only": (CAT[2], "W"), "neither": (NEUTRAL, "")}
    cells = {(r.destination_id, r.month): spec[r.agreement] for r in months.itertuples()}
    f = feats.set_index("destination_id")
    right = {i: f"overlap {f.season_agreement_jaccard[i]:.2f}" for i in ids}
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    _month_grid(fig, ax, ids, names, cells, right)
    fig.subplots_adjust(left=0.14, right=0.89, top=0.73, bottom=0.14)
    _title(fig, "Your best-months lists and the weather rule disagree most for Dharamshala and Khajjiar",
           "Months you entered (best_months) compared with months the weather rule calls comfortable", None)
    handles = [Patch(facecolor=CAT[0], label="\u2713  in both"),
               Patch(facecolor=CAT[1], label="E  entered by you, weather says not comfortable"),
               Patch(facecolor=CAT[2], label="W  weather says comfortable, not in your list"),
               Patch(facecolor=NEUTRAL, label="in neither")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.012, 0.90), ncol=2, frameon=False,
               fontsize=8.8, handlelength=1.2, columnspacing=1.6)
    fig.text(0.012, 0.012, "Winter months entered as best (E) may reflect snow interest rather than comfort.  "
             "Overlap = shared months divided by months in either list.", fontsize=8, color=MUTED)
    return _save(fig, "fig05_best_months_vs_weather.png")


def fig_interest_mix():
    tables, feats, months, ids, names = _context()
    f = feats.set_index("destination_id")
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    y = np.arange(len(ids))
    left = np.zeros(len(ids))
    for k, interest in enumerate(config.INTERESTS):
        vals = np.array([f[f"share_{interest}"][i] for i in ids])
        ax.barh(y, vals, left=left, height=0.62, color=CAT[k], edgecolor=SURFACE, linewidth=2)
        for j, v in enumerate(vals):
            if v >= 0.07:
                ax.text(left[j] + v / 2, y[j], f"{v * 100:.0f}%", ha="center", va="center", fontsize=8.5,
                        color=_text_on(CAT[k]), fontweight="bold")
        left += vals
    for j, i in enumerate(ids):
        n = int(f.n_attractions[i] + f.n_activities[i] - f.n_items_unmapped[i])
        ax.text(1.015, y[j], f"{n} items", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([names[i] for i in ids])
    ax.set_ylim(len(ids) - 0.4, -0.6)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v * 100:.0f}%")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.subplots_adjust(left=0.14, right=0.90, top=0.80, bottom=0.12)
    _title(fig, "Vaishno Devi is almost entirely spiritual; Dalhousie and Khajjiar lean on nature and adventure",
           "Share of each destination's attractions and activities by interest",
           "Built from 56 attractions and 46 activities (4\u20137 and 5\u20136 per destination), a curated sample "
           "rather than every sight.  Items with no interest signal are left out.")
    fig.legend(handles=[Patch(facecolor=CAT[k], label=i.capitalize()) for k, i in enumerate(config.INTERESTS)],
               loc="upper left", bbox_to_anchor=(0.012, 0.895), ncol=5, frameon=False, fontsize=9)
    return _save(fig, "fig06_interest_mix.png")


def fig_accommodation():
    tables, feats, months, ids, names = _context()
    acc = tables["accommodation"]
    priced = acc[acc.displayed_total_per_night_inr.notna()].copy()
    priced["hostel"] = priced.accommodation_type.str.contains("hostel", case=False)
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    for j, i in enumerate(ids):
        rows = priced[priced.destination_id == i]
        if rows.empty:
            ax.text(200, j, "no priced listings", va="center", fontsize=8.5, color=MUTED)
            continue
        offsets = np.linspace(-0.22, 0.22, len(rows)) if len(rows) > 1 else [0]
        for off, r in zip(offsets, rows.itertuples()):
            ax.scatter(r.displayed_total_per_night_inr, j + off, s=70, marker="D" if r.hostel else "o",
                       color=CAT[0], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        med = rows.displayed_total_per_night_inr.median()
        ax.plot([med, med], [j - 0.32, j + 0.32], color=INK, linewidth=1.6, zorder=2)
        ax.text(1.005, j, f"n = {len(rows)}", transform=ax.get_yaxis_transform(), va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels([names[i] for i in ids])
    ax.set_ylim(len(ids) - 0.5, -0.6)
    ax.set_xlim(0, priced.displayed_total_per_night_inr.max() * 1.08)
    ax.xaxis.set_major_formatter(lambda v, _: f"\u20b9{v:,.0f}")
    ax.set_xlabel("Displayed total per night (\u20b9)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.subplots_adjust(left=0.14, right=0.93, top=0.82, bottom=0.14)
    _title(fig, "Accommodation prices are too thin to rank destinations: 21 priced listings across 8 of 9 places",
           "Each mark is one priced listing; the bar is the median; diamonds are hostels",
           "One snapshot per listing (checked 09-10-2026 in the file), mixed property types.  Dharamshala has no priced "
           "listing, Dalhousie 2 and Amritsar 1.")
    return _save(fig, "fig07_accommodation_prices.png")


def fig_distance_sources():
    tables, feats, months, ids, names = _context()
    f = feats.set_index("destination_id")
    series = [("road_km_entered", "Entered by you (destinations.csv)", CAT[0], "o", 0.20),
              ("road_km_clean_file", "destinations_clean.csv", CAT[1], "D", 0.0),
              ("road_km_transport_table", "transportation.csv", CAT[2], "s", -0.20)]
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    for j, i in enumerate(ids):
        vals = [f[c][i] for c, *_ in series]
        ax.plot([np.nanmin(vals), np.nanmax(vals)], [j, j], color=AXIS, linewidth=2, zorder=1)
        ax.plot([f.straight_km[i]], [j], marker="|", markersize=16, color=MUTED, linestyle="none", zorder=2)
        for col, label, color, marker, off in series:
            if pd.notna(f[col][i]):
                ax.scatter(f[col][i], j + off, s=44, marker=marker, color=color, edgecolor=SURFACE,
                           linewidth=1.2, zorder=3)
    j9 = ids.index("D09")
    ax.annotate("48 km = the Jammu\u2013Katra leg only", (48, j9), xytext=(58, j9 - 0.62), fontsize=8.5,
                color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels([names[i] for i in ids])
    ax.set_ylim(len(ids) - 0.4, -0.7)
    ax.set_xlim(30, 180)
    ax.set_xlabel("Road distance from Pathankot (km)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.subplots_adjust(left=0.14, right=0.985, top=0.80, bottom=0.14)
    _title(fig, "Your road distances differ from the other two files for 7 of 9 destinations",
           "The clean file and transportation.csv agree everywhere except Vaishno Devi.  Grey tick = straight-line distance",
           "Transport-table value for Vaishno Devi is the sum of its two recorded legs (112 + 48).  "
           "Pathankot reference coordinate is approximate.")
    fig.legend(handles=[Line2D([], [], marker=m, color=c, linestyle="none", markersize=7, label=lab)
                        for _, lab, c, m, _ in series] +
               [Line2D([], [], marker="|", color=MUTED, linestyle="none", markersize=10, label="Straight line")],
               loc="upper left", bbox_to_anchor=(0.012, 0.895), ncol=4, frameon=False, fontsize=8.8)
    return _save(fig, "fig08_distance_sources.png")


def fig_similarity():
    tables, feats, months, ids, names = _context()
    sim = pd.read_csv(config.PROC / "interest_similarity.csv", index_col=0)
    order = [feats.set_index("destination_id").destination[i] for i in ids]
    sim = sim.loc[order, order]
    fig, ax = plt.subplots(figsize=(9.6, 6.6))
    _heatmap(ax, sim.values, [_wrap(n) for n in order], order, lambda v: f"{v:.2f}", 0, 1)
    fig.subplots_adjust(left=0.17, right=0.985, top=0.80, bottom=0.05)
    _title(fig, "Jammu and Kangra have the closest interest mix; Dalhousie is the most distinct",
           "Cosine similarity of the five interest shares (1 = identical mix, 0 = nothing in common)",
           "Preview only: a full similarity measure will also use season, cost and distance.")
    return _save(fig, "fig09_interest_similarity.png")


def fig_season_sensitivity():
    tables, feats, months, ids, names = _context()
    sens = pd.read_csv(config.PROC / "season_rule_sensitivity.csv", index_col=0)
    f = feats.set_index("destination_id")
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    for j, i in enumerate(ids):
        lo, hi = sens[i].min(), sens[i].max()
        ax.plot([lo, hi], [j, j], color=AXIS, linewidth=5, solid_capstyle="round", zorder=1)
        ax.scatter(f.n_comfortable_months[i], j, s=60, color=CAT[0], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.text(hi + 0.25, j, f"{lo}\u2013{hi}", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels([names[i] for i in ids])
    ax.set_ylim(len(ids) - 0.4, -0.6)
    ax.set_xlim(3, 11)
    ax.set_xlabel("Comfortable months out of 12")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.subplots_adjust(left=0.14, right=0.97, top=0.82, bottom=0.14)
    _title(fig, "Changing the weather thresholds shifts each comfortable-month count by 1 to 4 months",
           "Dot = chosen rule; bar = range across 9 alternative threshold settings (temperature band and rainfall limit)",
           "Any season score built from this rule should be tested against the same range.")
    return _save(fig, "fig10_season_rule_sensitivity.png")


def make_all():
    return {fn.__name__: fn() for fn in [
        fig_coverage, fig_temperature, fig_rainfall, fig_season_grid, fig_agreement,
        fig_interest_mix, fig_accommodation, fig_distance_sources, fig_similarity, fig_season_sensitivity]}


if __name__ == "__main__":
    for name, path in make_all().items():
        print(name, "->", path)
