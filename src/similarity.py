"""Similar destinations: four equally weighted similarity groups, each in 0-1.

interest   cosine of the five interest shares
type       Jaccard overlap of the destination-type flags
elevation  1 - |difference| / range
distance   1 - |difference in drive hours| / range
"""
import numpy as np
import pandas as pd

from . import config
from .data_access import effective_drive_hours
from .features import cosine_similarity_matrix

TYPE_COLS = ["type_hill_station", "type_historic_town", "type_city", "type_pilgrimage", "type_valley", "type_lake"]


def group_similarities(feats):
    """Return {group: DataFrame (n x n)} indexed by destination name."""
    f = effective_drive_hours(feats).reset_index(drop=True)
    names = f["destination"].tolist()
    n = len(f)
    inter = cosine_similarity_matrix(f, [f"share_{i}" for i in config.INTERESTS])
    inter = np.asarray(inter, float)
    t = f[[c for c in TYPE_COLS if c in f.columns]].values.astype(bool)
    typ = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            u = (t[i] | t[j]).sum()
            typ[i, j] = (t[i] & t[j]).sum() / u if u else 1.0
    def closeness(col):
        v = f[col].astype(float)
        v = v.fillna(v.median()).values          # a missing drive time (no route) is treated as the median
        rng = v.max() - v.min()
        return 1 - np.abs(v[:, None] - v[None, :]) / rng
    mats = {"interest": inter, "type": typ, "elevation": closeness("elevation_m"),
            "distance": closeness("drive_hours")}
    return {k: pd.DataFrame(m, index=names, columns=names) for k, m in mats.items()}


def similar_to(name, feats, k=3, weights=None):
    """Top-k most similar destinations with each group's contribution."""
    w = weights or config.SIMILARITY_WEIGHTS
    g = group_similarities(feats)
    wsum = sum(w.values())
    total = sum(w[k_] * g[k_] for k_ in g) / wsum
    order = total[name].drop(name).sort_values(ascending=False).head(k)
    rows = []
    for other, s in order.items():
        parts = {k_: g[k_].loc[name, other] for k_ in g}
        best = max(parts, key=parts.get)
        rows.append({"destination": other, "similarity": s,
                     **{f"sim_{k_}": v for k_, v in parts.items()},
                     "most_alike_in": best})
    return pd.DataFrame(rows)
