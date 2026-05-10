"""GridCast — Texas Winter Storm Uri (Feb 2021) deep dive.

Computes descriptive stats and 4 charts for ERCOT's iconic failure event,
using all data we have: ERCOT demand + day-ahead forecast (EIA),
Houston weather (Open-Meteo archive), ERCOT fuel mix (EIA),
and ERCOT real-time + day-ahead LMP (gridstatus).

Run from project root:
    python notebooks/02_texas_2021.py
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
# Style (light fintech, matches PLAN.md)
# ---------------------------------------------------------------------------

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
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": TEXT_TERTIARY,
    "axes.labelcolor": TEXT_PRIMARY,
    "axes.titlecolor": TEXT_PRIMARY,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlepad": 12,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID_COLOR,
    "grid.linewidth": 0.7,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "font.family": "DejaVu Sans",
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

# ---------------------------------------------------------------------------
# Storm windows
# ---------------------------------------------------------------------------

STORM_WINDOW_START = pd.Timestamp("2021-02-08", tz="UTC")
STORM_WINDOW_END = pd.Timestamp("2021-02-22", tz="UTC")
STORM_PEAK_START = pd.Timestamp("2021-02-13", tz="UTC")
STORM_PEAK_END = pd.Timestamp("2021-02-18", tz="UTC")
PRESTORM_START = pd.Timestamp("2021-01-15", tz="UTC")
PRESTORM_END = pd.Timestamp("2021-02-08", tz="UTC")
POSTSTORM_START = pd.Timestamp("2021-02-22", tz="UTC")
POSTSTORM_END = pd.Timestamp("2021-03-15", tz="UTC")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_data():
    erco = pd.read_parquet(RAW / "eia_erco_demand.parquet")
    erco_pivot = erco.pivot_table(index="period", columns="type", values="value")

    fuel = pd.read_parquet(RAW / "eia_erco_fuelmix.parquet")
    fuel_pivot = fuel.pivot_table(index="period", columns="fueltype", values="value")

    weather = pd.read_parquet(RAW / "weather_ercot_houston.parquet").set_index("period")

    lmp_path = RAW / "lmp_ercot_houston.parquet"
    if lmp_path.exists():
        lmp = pd.read_parquet(lmp_path)
        lmp_pivot = lmp.pivot_table(index="period", columns="market", values="price")
    else:
        lmp_pivot = pd.DataFrame()

    return erco_pivot, fuel_pivot, weather, lmp_pivot


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(erco, fuel, weather, lmp):
    bar = "=" * 72
    print(bar)
    print("TEXAS WINTER STORM URI — DESCRIPTIVE STATS")
    print(bar)

    storm = (STORM_WINDOW_START, STORM_WINDOW_END)
    peak = (STORM_PEAK_START, STORM_PEAK_END)
    pre = (PRESTORM_START, PRESTORM_END)

    def sl(s, w):
        return s.loc[w[0]:w[1]]

    print("\n--- HOUSTON TEMPERATURE ---")
    t = weather["temperature_2m"]
    print(f"Pre-storm  mean: {sl(t,pre).mean():6.1f}°C   median: {sl(t,pre).median():6.1f}°C")
    print(f"Storm wind mean: {sl(t,storm).mean():6.1f}°C   median: {sl(t,storm).median():6.1f}°C")
    print(f"Peak       mean: {sl(t,peak).mean():6.1f}°C   median: {sl(t,peak).median():6.1f}°C")
    print(f"Min during storm: {sl(t,storm).min():.1f}°C  at  {sl(t,storm).idxmin()}")
    print(f"Hours below 0°C in storm window: {(sl(t,storm) < 0).sum()}")

    print("\n--- ERCOT DEMAND ---")
    d = erco["D"]
    print(f"Pre-storm mean: {sl(d,pre).mean()/1000:6.1f} GW")
    print(f"Storm     mean: {sl(d,storm).mean()/1000:6.1f} GW")
    print(f"Storm     peak: {sl(d,storm).max()/1000:6.1f} GW  at  {sl(d,storm).idxmax()}")
    pre_peak = sl(d,pre).max()/1000
    storm_peak = sl(d,storm).max()/1000
    print(f"Storm peak vs pre-storm peak: {storm_peak:.1f} GW vs {pre_peak:.1f} GW ({(storm_peak-pre_peak)/pre_peak*100:+.1f}%)")

    if "DF" in erco.columns:
        df_ = erco["DF"]
        joined = pd.concat([d, df_], axis=1).loc[storm[0]:storm[1]].dropna()
        joined.columns = ["actual", "forecast"]
        err = joined["actual"] - joined["forecast"]
        mape = (err.abs() / joined["actual"]).mean() * 100
        print("\n--- DAY-AHEAD FORECAST ERROR (storm window) ---")
        print(f"MAPE: {mape:.1f}%")
        print(f"Mean signed error (actual - forecast): {err.mean()/1000:+.2f} GW")
        print(f"Max under-forecast (forecast missed by): {err.max()/1000:.2f} GW")
        print(f"Hours under-forecast > 1 GW: {(err > 1000).sum()}")
        print(f"Cumulative under-forecast: {err.clip(lower=0).sum()/1000:.0f} GWh missed")

    if "RTM" in lmp.columns:
        rtm = lmp["RTM"]
        print("\n--- ERCOT REAL-TIME LMP ---")
        print(f"Pre-storm mean: ${sl(rtm,pre).mean():>7,.0f}/MWh   median: ${sl(rtm,pre).median():>6,.0f}/MWh")
        print(f"Storm     mean: ${sl(rtm,storm).mean():>7,.0f}/MWh   median: ${sl(rtm,storm).median():>6,.0f}/MWh")
        print(f"Peak      mean: ${sl(rtm,peak).mean():>7,.0f}/MWh   median: ${sl(rtm,peak).median():>6,.0f}/MWh")
        print(f"Storm max: ${sl(rtm,storm).max():>7,.0f}/MWh")
        cap_hours = (sl(rtm,storm) >= 8000).sum()
        print(f"Hours at/near $9,000 cap (>= $8,000): {cap_hours}")

    if "DAM" in lmp.columns and "RTM" in lmp.columns:
        spread = (lmp["RTM"] - lmp["DAM"]).loc[storm[0]:storm[1]].dropna()
        print(f"\nRTM-DAM spread during storm: mean ${spread.mean():,.0f}/MWh  max ${spread.max():,.0f}/MWh")

    if "DF" in erco.columns and "RTM" in lmp.columns and "DAM" in lmp.columns:
        joined = pd.DataFrame({
            "actual": erco["D"],
            "forecast": erco["DF"],
            "rtm": lmp["RTM"],
            "dam": lmp["DAM"],
        }).loc[storm[0]:storm[1]].dropna()
        imbalance = (joined["actual"] - joined["forecast"]) * (joined["rtm"] - joined["dam"])
        print("\n--- IMBALANCE COST DURING STORM ---")
        print(f"Sum (D-DF)x(RTM-DAM): ${imbalance.sum()/1e6:>10,.1f} M")
        print(f"Positive part only:   ${imbalance.clip(lower=0).sum()/1e6:>10,.1f} M  (forecast-miss × scarcity)")

    print("\n--- CORRELATIONS DURING STORM ---")
    cols = {"temp": weather["temperature_2m"], "demand_GW": erco["D"]/1000}
    if "RTM" in lmp.columns:
        cols["rtm_USD"] = lmp["RTM"]
    if "DF" in erco.columns:
        cols["forecast_err_GW"] = (erco["D"] - erco["DF"])/1000
    corr_df = pd.DataFrame(cols).loc[storm[0]:storm[1]].dropna()
    print(corr_df.corr().round(3).to_string())

    print("\n--- FUEL MIX (peak vs pre-storm, mean MW) ---")
    for f in ["NG", "COL", "WND", "NUC", "SUN"]:
        if f in fuel.columns:
            pre_mean = sl(fuel[f], pre).mean()
            peak_mean = sl(fuel[f], peak).mean()
            change = ((peak_mean - pre_mean) / pre_mean * 100) if pre_mean else 0
            print(f"  {f:>3}:  {pre_mean:>7,.0f} MW  ->  {peak_mean:>7,.0f} MW  ({change:+6.1f}%)")
    print(bar)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def chart_collapse(erco, fuel, weather, lmp):
    """4-panel time series: temp, demand vs forecast, fuel mix, LMP."""
    s, e = STORM_WINDOW_START, STORM_WINDOW_END

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True,
                              gridspec_kw={"height_ratios": [1, 2.2, 1.8, 1.6], "hspace": 0.20})

    # 1. Temperature
    ax = axes[0]
    t = weather["temperature_2m"].loc[s:e]
    ax.plot(t.index, t, color=TEXT_PRIMARY, lw=1.5)
    ax.fill_between(t.index, t, 0, where=(t < 0), alpha=0.30, color=STRESS_RED, lw=0)
    ax.axhline(0, color=TEXT_TERTIARY, lw=0.8, ls=":")
    ax.set_ylabel("Temp (°C)")
    ax.set_title("Houston temperature — 80+ hours below freezing", loc="left", fontsize=11)

    # 2. Demand vs forecast
    ax = axes[1]
    d = erco["D"].loc[s:e] / 1000
    df_ = erco["DF"].loc[s:e] / 1000
    ax.plot(d.index, d, color=GRIDCAST_TEAL, lw=2.0, label="Actual demand")
    ax.plot(df_.index, df_, color=STRESS_RED, lw=1.5, ls="--", label="Day-ahead forecast")
    ax.fill_between(d.index, df_, d, where=(d > df_), alpha=0.20, color=STRESS_RED,
                    label="Under-forecast")
    ax.set_ylabel("Demand (GW)")
    ax.set_title("ERCOT demand vs day-ahead forecast — utility forecast collapsed under the surge",
                 loc="left", fontsize=11)
    ax.legend(loc="upper right", ncol=3, fontsize=9)

    # 3. Fuel mix
    ax = axes[2]
    fuels = [f for f in ["COL", "NG", "NUC", "WND", "SUN", "WAT"] if f in fuel.columns]
    fuel_palette = {
        "COL": "#6B7280", "NG": "#F59E0B", "NUC": "#10B981",
        "WND": "#3B82F6", "SUN": "#FCD34D", "WAT": "#06B6D4"
    }
    fd = fuel[fuels].loc[s:e].fillna(0) / 1000
    ax.stackplot(fd.index, fd.T.values, labels=fuels,
                 colors=[fuel_palette[f] for f in fuels], alpha=0.85)
    ax.set_ylabel("Generation (GW)")
    ax.set_title("ERCOT fuel mix — gas freeze-offs gutted supply at the worst possible moment",
                 loc="left", fontsize=11)
    ax.legend(loc="upper right", ncol=len(fuels), fontsize=9)

    # 4. LMP
    ax = axes[3]
    if "DAM" in lmp.columns and "RTM" in lmp.columns:
        dam = lmp["DAM"].loc[s:e]
        rtm = lmp["RTM"].loc[s:e]
        ax.plot(dam.index, dam, color=GRIDCAST_TEAL_2, lw=1.0, label="Day-ahead LMP")
        ax.plot(rtm.index, rtm, color=STRESS_RED, lw=1.5, label="Real-time LMP")
        ax.axhline(9000, color=STRESS_AMBER, lw=0.8, ls="--", label="$9,000 cap")
        ax.set_yscale("symlog", linthresh=100)
    ax.set_ylabel("LMP ($/MWh)")
    ax.set_title("ERCOT LMP — real-time hit the $9,000 cap and stayed there",
                 loc="left", fontsize=11)
    ax.legend(loc="upper right", ncol=3, fontsize=9)

    axes[-1].xaxis.set_major_locator(mdates.DayLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    fig.suptitle("Texas Winter Storm Uri — the cascading collapse",
                 x=0.07, y=0.995, ha="left", fontsize=15, fontweight="bold")

    out = FIG / "tx_01_collapse.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


def chart_imbalance_cost(erco, lmp):
    """Hourly imbalance cost bars + cumulative line."""
    s, e = STORM_WINDOW_START, STORM_WINDOW_END

    df = pd.DataFrame({
        "actual": erco["D"], "forecast": erco["DF"],
        "rtm": lmp.get("RTM"), "dam": lmp.get("DAM"),
    }).loc[s:e].dropna()
    df["imbalance"] = (df["actual"] - df["forecast"]) * (df["rtm"] - df["dam"])
    df["cumulative"] = df["imbalance"].cumsum()

    fig, ax1 = plt.subplots(figsize=(13, 6))

    colors = np.where(df["imbalance"] >= 0, STRESS_RED, STRESS_GREEN)
    ax1.bar(df.index, df["imbalance"]/1e6, width=0.04, color=colors, alpha=0.75)
    ax1.set_ylabel("Hourly imbalance ($M)")
    ax1.axhline(0, color=TEXT_TERTIARY, lw=0.7)

    ax2 = ax1.twinx()
    ax2.plot(df.index, df["cumulative"]/1e6, color=GRIDCAST_TEAL, lw=2.5)
    ax2.set_ylabel("Cumulative imbalance ($M)", color=GRIDCAST_TEAL)
    ax2.tick_params(axis="y", colors=GRIDCAST_TEAL)
    ax2.grid(False)

    total = df["imbalance"].sum()/1e6
    pos_total = df["imbalance"].clip(lower=0).sum()/1e6
    fig.suptitle(f"ERCOT imbalance cost — ${total:,.0f}M settled in 14 days",
                 x=0.07, y=0.99, ha="left", fontsize=14, fontweight="bold")
    ax1.set_title(
        f"Each red bar = one hour where forecast missed and prices spiked. "
        f"Forecast-miss × scarcity exposure: ${pos_total:,.0f}M.",
        loc="left", fontsize=10, color=TEXT_SECONDARY)

    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    out = FIG / "tx_02_imbalance_cost.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] {out.name}")


def chart_cascade(erco, weather, lmp):
    """3-panel scatter: temp vs demand, demand vs LMP, temp vs LMP."""
    s, e = STORM_WINDOW_START, STORM_WINDOW_END

    df = pd.DataFrame({
        "temp": weather["temperature_2m"],
        "demand_gw": erco["D"]/1000,
        "rtm": lmp.get("RTM"),
    }).loc[s:e].dropna()
    df["day"] = df.index.day

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 1. Temp -> Demand
    ax = axes[0]
    sc = ax.scatter(df["temp"], df["demand_gw"], c=df["day"],
                    cmap="coolwarm_r", s=22, alpha=0.75, edgecolor="white", lw=0.3)
    ax.set_xlabel("Houston temperature (°C)")
    ax.set_ylabel("ERCOT demand (GW)")
    c = df[["temp", "demand_gw"]].corr().iloc[0,1]
    ax.set_title(f"Cold drives demand (r = {c:+.2f})", loc="left")

    # 2. Demand -> RTM
    ax = axes[1]
    ax.scatter(df["demand_gw"], df["rtm"], c=df["day"],
               cmap="coolwarm_r", s=22, alpha=0.75, edgecolor="white", lw=0.3)
    ax.set_xlabel("ERCOT demand (GW)")
    ax.set_ylabel("Real-time LMP ($/MWh)")
    ax.set_yscale("symlog", linthresh=100)
    c = df[["demand_gw", "rtm"]].corr().iloc[0,1]
    ax.set_title(f"High demand → scarcity prices (r = {c:+.2f})", loc="left")

    # 3. Temp -> RTM
    ax = axes[2]
    ax.scatter(df["temp"], df["rtm"], c=df["day"],
               cmap="coolwarm_r", s=22, alpha=0.75, edgecolor="white", lw=0.3)
    ax.set_xlabel("Houston temperature (°C)")
    ax.set_ylabel("Real-time LMP ($/MWh)")
    ax.set_yscale("symlog", linthresh=100)
    c = df[["temp", "rtm"]].corr().iloc[0,1]
    ax.set_title(f"Cold → expensive (r = {c:+.2f})", loc="left")

    cb = fig.colorbar(sc, ax=axes, shrink=0.7, pad=0.02)
    cb.set_label("Day of February", color=TEXT_SECONDARY)

    fig.suptitle("The cascade — temperature → demand → price",
                 x=0.07, y=1.0, ha="left", fontsize=14, fontweight="bold")

    out = FIG / "tx_03_cascade.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


def chart_distribution_shift(erco, lmp, weather):
    """3-panel histograms before/during/after."""
    periods = [
        ("Pre  (Jan 15 – Feb 8)",  (PRESTORM_START, PRESTORM_END),  GRIDCAST_TEAL),
        ("Storm (Feb 8 – 22)",     (STORM_WINDOW_START, STORM_WINDOW_END), STRESS_RED),
        ("Post  (Feb 22 – Mar 15)", (POSTSTORM_START, POSTSTORM_END), STRESS_GREEN),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))

    # Temperature
    ax = axes[0]
    for label, (a, b), color in periods:
        data = weather["temperature_2m"].loc[a:b].dropna()
        ax.hist(data, bins=30, alpha=0.55, color=color, label=label)
    ax.set_xlabel("Houston temperature (°C)")
    ax.set_ylabel("Hours")
    ax.set_title("Temperature distribution shifted brutally cold", loc="left")
    ax.legend(fontsize=8)

    # Demand
    ax = axes[1]
    for label, (a, b), color in periods:
        data = erco["D"].loc[a:b].dropna() / 1000
        ax.hist(data, bins=30, alpha=0.55, color=color, label=label)
    ax.set_xlabel("ERCOT demand (GW)")
    ax.set_title("Demand pushed past every prior winter peak", loc="left")

    # LMP (log)
    if "RTM" in lmp.columns:
        ax = axes[2]
        for label, (a, b), color in periods:
            data = lmp["RTM"].loc[a:b].dropna()
            data = np.log10(np.maximum(data.values, 1.0))
            ax.hist(data, bins=30, alpha=0.55, color=color, label=label)
        ax.set_xlabel("log10(real-time LMP) — $/MWh")
        ax.set_title("Prices became a different distribution", loc="left")

    fig.suptitle("Distribution shift: storm vs the months around it",
                 x=0.07, y=1.0, ha="left", fontsize=14, fontweight="bold")

    out = FIG / "tx_04_distribution_shift.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[ok] {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    erco, fuel, weather, lmp = load_data()
    print_stats(erco, fuel, weather, lmp)
    print()
    print(f"Output: {FIG}")
    chart_collapse(erco, fuel, weather, lmp)
    chart_imbalance_cost(erco, lmp)
    chart_cascade(erco, weather, lmp)
    chart_distribution_shift(erco, lmp, weather)


if __name__ == "__main__":
    main()
