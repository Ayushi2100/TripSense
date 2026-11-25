"""Append rows to an existing raw CSV without touching the existing rows.

Existing values are read as text and written back as text, so numbers keep their original
formatting (94, not 94.0) and the file keeps its BOM and any encoding quirks.
"""
from pathlib import Path

import pandas as pd


def append_rows(path, new_rows, key=None):
    path = Path(path)
    head = path.read_bytes()[:3]
    bom = head == b"\xef\xbb\xbf"
    old = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    new = pd.DataFrame(new_rows).reindex(columns=old.columns).astype(object)
    new = new.where(new.notna(), "")
    new = new.map(lambda v: "" if v is None else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)))
    if key is not None:
        dup = set(old[key]) & set(new[key])
        if dup:
            raise ValueError(f"{path.name}: keys already present {sorted(dup)[:5]}")
    out = pd.concat([old, new], ignore_index=True)
    out.to_csv(path, index=False, encoding="utf-8-sig" if bom else "utf-8", lineterminator="\n")
    return len(old), len(out)
