"""Robust MAD‑based helpers."""
from __future__ import annotations
import numpy as np, pandas as pd

__all__ = ["mad_scores", "mad_filter"]


def mad_scores(series: pd.Series) -> pd.Series:
    """Return robust z‑scores (0.6745|x‑median|/MAD)."""
    median = series.median()
    mad = np.median(np.abs(series - median))
    if mad == 0 or pd.isna(mad):
        return pd.Series(0, index=series.index)
    return 0.6745 * (series - median).abs() / mad # type: ignore


def mad_filter(df: pd.DataFrame, cols, thresh: float, baselines: dict | None = None):
    """Remove rows whose MAD z‑score > thresh in **any** listed column.
    Optionally subtract *baselines* before scoring so big static offsets
    don't look like outliers.
    """
    work = df.copy()
    if baselines:
        for c, b in baselines.items():
            if c in work.columns and pd.notna(b):
                work[c] = work[c] - float(b)
    mask = np.zeros(len(work), dtype=bool)
    for c in cols:
        if c in work:
            mask |= mad_scores(work[c]) > thresh
    return df.loc[~mask].copy()