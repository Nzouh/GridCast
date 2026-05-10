"""GridCast — ERCOT recent LMP analysis (last ~40 days available).

Uses what's actually on disk: ERCOT DAM + RTM prices, EIA demand and
day-ahead forecast, Houston weather. Joins on hourly UTC and produces 4
charts that tell the imbalance-cost story during normal-ish operations
(no Winter Storm here — that needs deeper historical pulls).

Run:
    python notebooks/03_ercot_recent_lmp.py
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

GRIDCAST_TEAL = "#0F3D56"
GRIDCAST_TEAL_2 = "#3B6E89"
STRESS_GREEN = "#16A34A"
STRESS_AMBER = "#F59E0B"
STRESS_RED = "#DC2626"
TEXT_PRIMARY = "#0B0F19"
TEXT_SECONDARY = "#6B7280"
TEXT_TERTIARY = "#9CA3AF"
GRID_COLOR = "#E5E7EB"

mpl.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": TEXT_TERTIARY, "axes.labelcolor": TEXT_PRIMARY,
    "axes.titlecolor": TEXT_PRIMARY, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.titlepad": 12,
    "axes.labelsize": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID_COLOR, "grid.linewidth": 0.7,
    "xtick.color": TEXT_SECONDARY, "ytick.color": TEXT_SECONDARY,
    "legend.frameon": False, "legend.fontsize": 9,
    "font.family": "DejaVu Sans", "savefig.dpi": 200,
    "savefig.bbox": "tight", "savefig.facecolor": "white",
})


# ---------------------------------------------------------------------------
# Load and join
# ---------------------------------------------------------------------------

def load_joined() -> pd.DataFrame:
    erco = pd.read_parquet(RAW / "eia_erco_demand.parquet")
    erco = erco.pivot_table(index="period", columns="type", values="value")

    weather = pd.read_parquet(RAW / "weather_ercot_houston.parquet").set_index("period")

    lmp = pd.read_parquet(RAW / "lmp_ercot_houston.parquet")
    lmp = lmp.pivot_table(index="period", columns="market", values="price")

    df = pd.concat([
        erco[["D", "DF"]].rename(columns={"D": "demand_mw", "DF": "forecast_mw"}),
        weather[["temperature_2m"]].rename(columns={"temperature_2m": "temp_c"}),
        lmp[["DAM", "RTM"]].rename(columns={"DAM": "dam_usd", "RTM": "rtm_usd"}),
    ], axis=1)

    # Restrict to the LMP window (smallest of the three)
    df = df.loc[lmp.index.min():lmp.index.max()].copy()
    df = df.dropna(subset=["dam_usd", "rtm_usd"])

    df["forecast_err_mw"] = df["demand_mw"] - df["forecast_mw"]
    df["price_spread"] = df["rtm_usd"] - df["dam_usd"]
    df["imbalance_dollars"] = df["forecast_err_mw"] * df["price_spread"]
    return df


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(df: pd.DataFrame) -> None:
    bar = "=" * 72
    print(bar)
    print(f"ERCOT — {df.index.min().date()}  →  {df.index.max().date()}   ({len(df):,} hours)")
    print(bar)

    print("\n--- PRICES ($/MWh) ---")
    for c in ["dam_usd", "rtm_usd"]:
        s = df[c]
        label = "Day-ahead " if c == "dam_usd" else "Real-time "
        print(f"{label} mean ${s.mean():>6,.1f}   median ${s.median():>6,.1f}   "
              f"min ${s.min():>6,.1f}   max ${s.max():>7,.1f}   std ${s.std():>5,.1f}")

    print(f"\nRTM > DAM in {(df['price_spread'] > 0).mean()*100:.0f}% of hours")
    print(f"RTM > DAM by >$50 in {(df['price_spread'] > 50).sum()} hours "
          f"({(df['price_spread'] > 50).mean()*100:.1f}% of all hours)")
    print(f"RTM > DAM by >$200 in {(df['price_spread'] > 200).sum()} hours "
          f"({(df['price_spread'] > 200).mean()*100:.2f}%) — scarcity events")

    print("\n--- DEMAND (GW) ---")
    print(f"Mean {df['demand_mw'].mean()/1000:.1f}   "
          f"Peak {df['demand_mw'].max()/1000:.1f}   "
          f"Min {df['demand_mw'].min()/1000:.1f}")

    print("\n--- DAY-AHEAD FORECAST ERROR (actual − forecast, MW) ---")
    err = df["forecast_err_mw"].dropna()
    print(f"Mean {err.mean():+.0f}   |err| mean {err.abs().mean():.0f}   "
          f"max under-forecast {err.max():+.0f}   max over-forecast {err.min():+.0f}")
    mape = (err.abs() / df["demand_mw"]).mean() * 100
    print(f"MAPE: {mape:.2f}%")

    print("\n--- IMBALANCE COST = (D − DF) × (RTM − DAM) ---")
    imb = df["imbalance_dollars"].dropna()
    print(f"Total over the window:        ${imb.sum()/1e6:>+8,.2f} M")
    print(f"Positive part (forecast lost): ${imb.clip(lower=0).sum()/1e6:>+8,.2f} M")
    print(f"Mean per hour: ${imb.mean():>+8,.0f}   stdev: ${imb.std():,.0f}")

    print("\n--- CORRELATIONS ---")
    cols = ["demand_mw", "temp_c", "dam_usd", "rtm_usd", "forecast_err_mw", "price_spread"]
    print(df[cols].corr().round(2).to_string())
    print(bar)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def chart_overview(df: pd.DataFrame) -> None:
    """Time series: DAM vs RTM, with demand below."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                     gridspec_kw={"height_ratios": [2, 1], "hspace": 0.15})

    ax1.plot(df.index, df["dam_usd"], color=GRIDCAST_TEAL_2, lw=1.0, label="Day-ahead LMP")
    ax1.plot(df.index, df["rtm_usd"], color=STRESS_RED, lw=1.0, alpha=0.85,
             label="Real-time LMP")
    ax1.fill_between(df.index, df["dam_usd"], df["rtm_usd"],
                     where=(df["rtm_usd"] > df["dam_usd"]),
                     alpha=0.18, color=STRESS_RED, label="RTM > DAM (scarcity hours)")
    ax1.set_ylabel("LMP ($/MWh)")
    ax1.legend(loc="upper right", ncol=3)
    ax1.set_title("ERCOT Houston Hub — day-ahead vs real-time, last 40 days",
                  loc="left")

    ax2.plot(df.index, df["demand_mw"]/1000, color=GRIDCAST_TEAL, lw=1.0)
    ax2.set_ylabel("ERCOT demand (GW)")
    ax2.set_xlabel("")

    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=4))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    out = FIG / "tx_recent_01_overview.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


def chart_price_patterns(df: pd.DataFrame) -> None:
    """Two panels: price duration curve + hour-of-day profile."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    # Price duration curve (sorted descending)
    ax = axes[0]
    dam_sorted = df["dam_usd"].sort_values(ascending=False).reset_index(drop=True)
    rtm_sorted = df["rtm_usd"].sort_values(ascending=False).reset_index(drop=True)
    pct = np.linspace(0, 100, len(dam_sorted))
    ax.plot(pct, dam_sorted, color=GRIDCAST_TEAL_2, lw=2, label="Day-ahead")
    ax.plot(pct, rtm_sorted, color=STRESS_RED, lw=2, label="Real-time")
    ax.set_xlabel("% of hours (sorted by price, descending)")
    ax.set_ylabel("LMP ($/MWh)")
    ax.set_title("Price duration curve — most hours are cheap, a few are very expensive",
                  loc="left")
    ax.legend()
    ax.set_yscale("symlog", linthresh=50)
    p99_rtm = df["rtm_usd"].quantile(0.99)
    ax.axhline(p99_rtm, color=TEXT_TERTIARY, ls=":", lw=1)
    ax.text(50, p99_rtm * 1.2, f"P99 RTM = ${p99_rtm:.0f}",
            color=TEXT_SECONDARY, fontsize=9)

    # Hour-of-day profile
    ax = axes[1]
    df_local = df.copy()
    df_local["hour"] = df.index.tz_convert("US/Central").hour
    by_hour = df_local.groupby("hour").agg(
        dam_mean=("dam_usd", "mean"),
        rtm_mean=("rtm_usd", "mean"),
        rtm_p10=("rtm_usd", lambda x: x.quantile(0.10)),
        rtm_p90=("rtm_usd", lambda x: x.quantile(0.90)),
    )
    ax.fill_between(by_hour.index, by_hour["rtm_p10"], by_hour["rtm_p90"],
                    alpha=0.15, color=STRESS_RED, label="RTM P10–P90")
    ax.plot(by_hour.index, by_hour["dam_mean"], color=GRIDCAST_TEAL_2,
            lw=2, marker="o", label="DAM mean")
    ax.plot(by_hour.index, by_hour["rtm_mean"], color=STRESS_RED,
            lw=2, marker="o", label="RTM mean")
    ax.set_xlabel("Hour of day (Texas local time)")
    ax.set_ylabel("LMP ($/MWh)")
    ax.set_title("Hourly price rhythm — evening ramp burns through reserves",
                  loc="left")
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.legend()

    fig.suptitle("ERCOT pricing patterns — the shape of when scarcity hits",
                 x=0.07, y=1.0, ha="left", fontsize=14, fontweight="bold")

    out = FIG / "tx_recent_02_price_patterns.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


def chart_demand_vs_price(df: pd.DataFrame) -> None:
    """Scatter: demand vs RTM, colored by hour-of-day."""
    fig, ax = plt.subplots(figsize=(11, 6.5))

    df_local = df.copy()
    df_local["hour"] = df.index.tz_convert("US/Central").hour

    sc = ax.scatter(df_local["demand_mw"]/1000, df_local["rtm_usd"],
                    c=df_local["hour"], cmap="twilight_shifted", s=20,
                    alpha=0.65, edgecolor="white", lw=0.3)
    ax.set_yscale("symlog", linthresh=50)
    ax.set_xlabel("ERCOT demand (GW)")
    ax.set_ylabel("Real-time LMP ($/MWh)")

    corr = df_local[["demand_mw", "rtm_usd"]].corr().iloc[0,1]
    spear = df_local[["demand_mw", "rtm_usd"]].corr(method="spearman").iloc[0,1]

    ax.set_title(
        f"Demand drives price — but the relationship is non-linear and tail-heavy",
        loc="left", fontsize=14)
    ax.text(0.02, 0.97,
            f"Pearson r = {corr:+.2f}\nSpearman ρ = {spear:+.2f}\nn = {len(df_local):,}",
            transform=ax.transAxes, va="top", ha="left",
            color=TEXT_SECONDARY, fontsize=10,
            bbox=dict(facecolor="white", edgecolor=GRID_COLOR, linewidth=0.7,
                      boxstyle="round,pad=0.5"))

    cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.85)
    cb.set_label("Hour of day (Texas local)", color=TEXT_SECONDARY)

    out = FIG / "tx_recent_03_demand_vs_price.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


def chart_forecast_error_vs_cost(df: pd.DataFrame) -> None:
    """The GridCast pitch chart: forecast error → imbalance cost."""
    d = df.dropna(subset=["forecast_err_mw", "imbalance_dollars"]).copy()

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

    # Left: scatter, |err| vs imbalance$
    ax = axes[0]
    sc = ax.scatter(d["forecast_err_mw"]/1000, d["imbalance_dollars"]/1000,
                    c=np.abs(d["price_spread"]), cmap="Reds", s=22,
                    alpha=0.7, edgecolor="white", lw=0.3,
                    norm=mpl.colors.SymLogNorm(linthresh=10))
    ax.axvline(0, color=TEXT_TERTIARY, lw=0.7, ls=":")
    ax.axhline(0, color=TEXT_TERTIARY, lw=0.7, ls=":")
    ax.set_xlabel("Day-ahead forecast error (GW)\n← over-forecast    under-forecast →")
    ax.set_ylabel("Imbalance cost ($k per hour)")
    ax.set_title("Each dot = one hour", loc="left")

    cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.85)
    cb.set_label("|RTM − DAM| spread ($/MWh)", color=TEXT_SECONDARY)

    # Right: cumulative imbalance over time
    ax = axes[1]
    cum = d["imbalance_dollars"].cumsum() / 1e6
    pos_only = d["imbalance_dollars"].clip(lower=0).cumsum() / 1e6
    ax.plot(cum.index, cum, color=GRIDCAST_TEAL, lw=2.5, label="Net cumulative")
    ax.plot(pos_only.index, pos_only, color=STRESS_RED, lw=2.0, ls="--",
             label="Positive only (forecast loss)")
    ax.fill_between(pos_only.index, 0, pos_only, alpha=0.10, color=STRESS_RED)
    ax.set_ylabel("Cumulative imbalance ($M)")
    ax.set_xlabel("")
    ax.legend(loc="upper left")
    ax.set_title(f"Cumulative imbalance over {len(d):,} hours", loc="left")
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    fig.suptitle(
        "Forecast errors leak money even in normal operations — and GridCast targets exactly this",
        x=0.07, y=1.0, ha="left", fontsize=14, fontweight="bold")

    out = FIG / "tx_recent_04_forecast_error_vs_cost.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    df = load_joined()
    if df.empty:
        print("[FAIL] No overlapping rows. Check parquet windows.")
        return
    print_stats(df)
    print()
    print(f"Output: {FIG}")
    chart_overview(df)
    chart_price_patterns(df)
    chart_demand_vs_price(df)
    chart_forecast_error_vs_cost(df)


if __name__ == "__main__":
    main()
