"""Optional PDF bundle of Δ curves."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, matplotlib.dates as mdates
from matplotlib.ticker import ScalarFormatter


def make_pdf(df_slice, out_pdf):
    point = df_slice["PointName"].iloc[0]
    fig, ax = plt.subplots(figsize=(8.5,5))
    ax.plot(df_slice["TIMESTAMP"], df_slice["Delta_H_mm"], label="ΔH (mm)")
    ax.set_title(point)
    ax.set_ylabel("mm")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.grid(True, linestyle="--", alpha=.5)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)