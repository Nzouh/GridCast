"""GridCast — Problem framing visualizations.

The pitch in 4 charts, walking the narrative arc:

  1. Reserve headroom — there is a mountain of unsold capacity. (TIME SERIES)
  2. Demand vs temperature — but demand IS predictable from weather.
  3. Texas Winter Storm 2021 — yet utilities miss when it matters most. (TIME SERIES)
  4. Hourly profiles by season — every grid has structure waiting to be modeled. (TIME SERIES facet)

Each chart saves a PNG to notebooks/figures/. Run from project root with
the venv active:

    python notebooks/01_problem_framing.py

If a chart errors out because the underlying parquet is missing or doesn't
cover the required window, the script prints a clear message and continues
to the next chart.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "backend" / "data" / "raw"
FIG = ROOT / "notebooks" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Light fintech style (matches the sf.atmo.ai aesthetic from PLAN.md)
# ---------------------------------------------------------------------------

GRIDCAST_TEAL = "#0F3D56"
GRIDCAST_TEAL_2 = "#3B6E89"
GRIDCAST_TEAL_3 = "#7BA4BC"
STRESS_GREEN = "#16A34A"
STRESS_AMBER = "#F59E0B"
STRESS_RED = "#DC2626"
TEXT_PRIMARY = "#0B0F19"
TEXT_SECONDARY = "#6B7280"
TEXT_TERTIARY = "#9CA3AF"
GRID_COLOR = "#E5E7EB"

SEASON_COLORS = {
    "Winter": "#3B82F6",
    "Spring": "#10B981",
    "Summer": "#F59E0B",
    "Fall":   "#A855F7",
}


def apply_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": TEXT_TERTIARY,
        "axes.labelcolor": TEXT_PRIMARY,
        "axes.titlecolor": TEXT_PRIMARY,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.labelpad": 6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.7,
        "xtick.color": TEXT_SECONDARY,
        "ytick.color": TEXT_SECONDARY,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "font.family": "DejaVu Sans",
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    })


def beat_label(fig, text: str) -> None:
    fig.text(0.07, 0.985, text, ha="left", va="top",
             fontsize=10.5, color=TEXT_TERTIARY, weight="medium")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_demand_pivot(ba: str) -> pd.DataFrame:
    """Returns wide DataFrame indexed by period with columns D, DF, NG, TI."""
    path = RAW / f"eia_{ba.lower()}_demand.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    return df.pivot_table(index="period", columns="type", values="value")


def load_subba_dom_demand() -> pd.Series:
    path = RAW / "eia_pjm_dom_demand.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    return df.set_index("period")["value"].rename("demand_mw").sort_index()


def load_weather(node: str) -> pd.DataFrame:
    path = RAW / f"weather_{node}.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    return df.set_index("period").sort_index()


# ---------------------------------------------------------------------------
# Chart 1 — Reserve headroom over a year (TIME SERIES, Beat 1)
# ---------------------------------------------------------------------------

def chart_reserve_headroom() -> None:
    """The opening hook: a mountain of unsold capacity in PJM 2024.

    Story: utilities hold ~18% reserve margin against forecast uncertainty.
    With sharper forecasts, that could be ~8%. The 10pp delta times peak demand
    times wholesale price = unlocked annual revenue.
    """
    pjm = load_demand_pivot("PJM")

    yr = pjm[pjm.index.year == 2024]
    demand = yr["D"].dropna() / 1000  # GW

    historical_peak = pjm["D"].max() / 1000  # GW
    op_capacity = historical_peak * 1.15

    # Conservative-vs-tight reserve framing
    avg_demand = demand.mean()
    current_reserve_pct = 0.18
    target_reserve_pct = 0.08
    unlock_gw = (current_reserve_pct - target_reserve_pct) * historical_peak
    proxy_price = 35  # $/MWh, rough PJM 2024 wholesale average
    unlock_dollars = unlock_gw * 1000 * 8760 * proxy_price  # $

    fig, ax = plt.subplots(figsize=(13.5, 5.8))

    ax.fill_between(demand.index, demand, op_capacity,
                    color=GRIDCAST_TEAL, alpha=0.10, lw=0,
                    label=f"Idle capacity ({(op_capacity - demand.mean()):.0f} GW avg)")
    ax.plot(demand.index, demand, color=GRIDCAST_TEAL, lw=0.8, label="PJM hourly demand")
    ax.axhline(op_capacity, color=STRESS_RED, lw=1.0, ls="--",
               label=f"Operating capacity proxy (peak × 1.15 = {op_capacity:.0f} GW)")

    ax.set_ylabel("PJM demand (GW)")
    ax.set_xlabel("")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_xlim(demand.index.min(), demand.index.max())
    ax.set_ylim(0, op_capacity * 1.05)

    ax.set_title(
        f"PJM 2024 — ${unlock_dollars/1e9:.1f}B/year is held back by forecast uncertainty",
        loc="left",
    )

    note = (
        f"Average demand: {avg_demand:.0f} GW   |   Peak: {demand.max():.0f} GW\n"
        f"Current reserve margin: ~{current_reserve_pct:.0%}  →  with sharper forecasts: ~{target_reserve_pct:.0%}\n"
        f"Unlocked: {unlock_gw:.0f} GW × 8760 h × ${proxy_price}/MWh = ${unlock_dollars/1e9:.1f}B/year"
    )
    ax.text(0.012, 0.965, note, transform=ax.transAxes, va="top", ha="left",
            color=TEXT_SECONDARY, fontsize=10,
            bbox=dict(facecolor="white", edgecolor=GRID_COLOR, linewidth=0.7,
                      boxstyle="round,pad=0.5"))

    ax.legend(loc="lower right", ncol=3)

    beat_label(fig, "Beat 1 — A mountain of unsold capacity")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG / "01_reserve_headroom.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


# ---------------------------------------------------------------------------
# Chart 2 — Demand vs temperature (4-panel hexbin scatter, Beat 2)
# ---------------------------------------------------------------------------

def _polyfit_curve(x: np.ndarray, y: np.ndarray, degree: int = 3, n: int = 200):
    coef = np.polyfit(x, y, deg=degree)
    xs = np.linspace(x.min(), x.max(), n)
    ys = np.polyval(coef, xs)
    return xs, ys


def chart_demand_vs_temperature() -> None:
    """4 panels: each node's demand vs local temperature.

    SP15 and NP15 share BA-level CISO demand (apportionment to nodal-level
    demand needs CAISO-internal data we don't have). The chart is honest
    about this — what differs is the *weather*, which is the point.
    """
    nodes = [
        ("dominion_hub",   "Dominion Hub (PJM/DOM)",     load_subba_dom_demand()),
        ("caiso_sp15",     "CAISO SP15 — LA",            load_demand_pivot("CISO")["D"]),
        ("caiso_np15",     "CAISO NP15 — Bay Area",      load_demand_pivot("CISO")["D"]),
        ("ercot_houston",  "ERCOT Houston Hub",          load_demand_pivot("ERCO")["D"]),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.5))
    axes = axes.flatten()

    for ax, (node, label, demand) in zip(axes, nodes):
        weather = load_weather(node)
        temp = weather["temperature_2m"]

        df = pd.concat([demand.rename("demand"), temp.rename("temp")], axis=1).dropna()
        df = df[df["demand"] > 0]
        df["demand_gw"] = df["demand"] / 1000

        hb = ax.hexbin(df["temp"], df["demand_gw"], gridsize=55, mincnt=2,
                       cmap="Blues", linewidths=0.0)

        # Polynomial fit overlay
        xs, ys = _polyfit_curve(df["temp"].values, df["demand_gw"].values, degree=3)
        ax.plot(xs, ys, color=STRESS_RED, lw=2, label="Cubic fit")

        corr = df[["demand_gw", "temp"]].corr().iloc[0, 1]

        ax.set_title(label, loc="left")
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("Demand (GW)")
        ax.text(0.97, 0.96,
                f"corr = {corr:+.2f}\nn = {len(df):,}",
                transform=ax.transAxes, ha="right", va="top",
                color=TEXT_SECONDARY, fontsize=9,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85))
        ax.legend(loc="upper left", fontsize=9)

    fig.suptitle(
        "Demand IS predictable from weather — every node has a clean V or U curve",
        x=0.07, y=0.97, ha="left", fontsize=14, fontweight="bold",
        color=TEXT_PRIMARY,
    )
    beat_label(fig, "Beat 2 — Predictability")

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = FIG / "02_demand_vs_temperature.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


# ---------------------------------------------------------------------------
# Chart 3 — Texas Winter Storm 2021 (TIME SERIES, Beat 4)
# ---------------------------------------------------------------------------

def chart_texas_2021() -> None:
    """The iconic event: ERCOT day-ahead forecast vs realized demand
    during Winter Storm Uri, with Houston temperature on a synced bottom axis.

    Uses BA-level ERCO demand because the user re-pulled EIA from 2020-01-01.
    If that data isn't present (because the pull script wasn't re-run),
    raises FileNotFoundError early.
    """
    erco = load_demand_pivot("ERCO")
    weather = load_weather("ercot_houston")

    window_start = pd.Timestamp("2021-02-08", tz="UTC")
    window_end = pd.Timestamp("2021-02-22", tz="UTC")

    if erco.index.min() > window_start:
        raise RuntimeError(
            f"EIA ERCO data starts at {erco.index.min().date()} — "
            f"need 2021-02 coverage. Re-run pull_eia.py with START='2020-01-01T00'."
        )

    actual = erco["D"].loc[window_start:window_end] / 1000  # GW
    forecast = erco["DF"].loc[window_start:window_end] / 1000
    temp = weather["temperature_2m"].loc[window_start:window_end]

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(14, 8.5), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
    )

    # Top: demand actual vs forecast, with under-forecast shading
    ax_top.plot(actual.index, actual, color=GRIDCAST_TEAL, lw=2.2, label="Actual demand")
    ax_top.plot(forecast.index, forecast, color=STRESS_RED, lw=1.6, ls="--",
                alpha=0.9, label="EIA day-ahead forecast")
    under = (actual > forecast)
    ax_top.fill_between(actual.index, forecast, actual, where=under, alpha=0.18,
                        color=STRESS_RED, label="Under-forecast (cost zone)")

    ax_top.set_ylabel("ERCOT demand (GW)")
    ax_top.set_title(
        "Texas Winter Storm Uri — utility forecast missed for days, exactly when it cost the most",
        loc="left",
    )
    ax_top.legend(loc="upper right", ncol=3)

    gap_series = (actual - forecast).clip(lower=0)
    peak_gap = gap_series.max()
    total_underforecast_gwh = gap_series.sum()
    hours_with_gap = (gap_series > 1).sum()

    note = (
        f"Peak under-forecast: {peak_gap:.1f} GW   |   "
        f"Hours with >1 GW gap: {hours_with_gap}   |   "
        f"Cumulative under-forecast: {total_underforecast_gwh:.0f} GWh"
    )
    ax_top.text(0.012, 0.965, note, transform=ax_top.transAxes, va="top", ha="left",
                color=TEXT_SECONDARY, fontsize=10,
                bbox=dict(facecolor="white", edgecolor=GRID_COLOR, linewidth=0.7,
                          boxstyle="round,pad=0.5"))

    # Bottom: Houston temperature
    ax_bot.plot(temp.index, temp, color=TEXT_PRIMARY, lw=1.5)
    below_zero = temp < 0
    ax_bot.fill_between(temp.index, temp, 0, where=below_zero, alpha=0.25,
                        color=STRESS_RED, lw=0)
    ax_bot.axhline(0, color=TEXT_TERTIARY, lw=0.8, ls=":")
    ax_bot.set_ylabel("Houston temp (°C)")
    ax_bot.set_xlabel("")

    ax_bot.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    beat_label(fig, "Beat 4 — Forecasts fail when it matters most")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = FIG / "03_texas_winter_storm_2021.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


# ---------------------------------------------------------------------------
# Chart 4 — Hourly demand profiles by season (TIME SERIES facet, Beat 2)
# ---------------------------------------------------------------------------

def chart_hourly_profiles_by_season() -> None:
    """Each grid has a 'personality' — distinct hourly load shape per season.

    Three small multiples (Dominion sub-zone, CAISO total, ERCOT total).
    Story: this structure is exploitable. A weather-aware seq2seq model
    learns it; flat utility models don't.
    """
    panels = [
        ("Dominion zone (PJM/DOM)", load_subba_dom_demand()),
        ("CAISO (system-level)",    load_demand_pivot("CISO")["D"]),
        ("ERCOT (system-level)",    load_demand_pivot("ERCO")["D"]),
    ]

    def season_of(month: int) -> str:
        return ("Winter" if month in (12, 1, 2)
                else "Spring" if month in (3, 4, 5)
                else "Summer" if month in (6, 7, 8)
                else "Fall")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharex=True)

    for ax, (label, demand) in zip(axes, panels):
        df = demand.dropna().to_frame("demand_mw").copy()
        df["hour"] = df.index.hour
        df["season"] = df.index.month.map(season_of)
        df["demand_gw"] = df["demand_mw"] / 1000

        for season, color in SEASON_COLORS.items():
            grp = df[df["season"] == season].groupby("hour")["demand_gw"]
            mean = grp.mean()
            std = grp.std()
            ax.plot(mean.index, mean, color=color, lw=2.2, label=season)
            ax.fill_between(mean.index, mean - std, mean + std,
                            color=color, alpha=0.10, lw=0)

        ax.set_title(label, loc="left")
        ax.set_xlabel("Hour of day (UTC)")
        ax.set_xticks([0, 6, 12, 18, 23])

    axes[0].set_ylabel("Demand (GW)")
    axes[-1].legend(title="Season", loc="upper right", title_fontsize=10)

    fig.suptitle(
        "Each grid has a personality — hour × season demand profiles",
        x=0.07, y=0.99, ha="left", fontsize=14, fontweight="bold",
        color=TEXT_PRIMARY,
    )
    beat_label(fig, "Beat 2 — Predictability (continued)")

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = FIG / "04_hourly_profiles_by_season.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHARTS = [
    ("reserve headroom",          chart_reserve_headroom),
    ("demand vs temperature",     chart_demand_vs_temperature),
    ("Texas Winter Storm 2021",   chart_texas_2021),
    ("hourly profiles",           chart_hourly_profiles_by_season),
]


def main() -> None:
    apply_style()
    print(f"Output: {FIG}\n")
    for label, fn in CHARTS:
        try:
            fn()
        except FileNotFoundError as e:
            print(f"[skip] {label}: missing data {e}")
        except RuntimeError as e:
            print(f"[skip] {label}: {e}")
    print(f"\nAll figures in: {FIG}")


if __name__ == "__main__":
    main()
