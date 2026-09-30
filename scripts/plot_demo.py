"""Demo figures from results/demo/*.json (master doc §11.7 figures 6 and 7).

    python scripts/plot_demo.py       # after scripts/run_fleet_demo.py

    results/demo/fig_fleet_impact.png   naive vs system-optimal fleet flows + externality bars (fig 6)
    results/demo/fig_time_of_day.png    same 60 customers planned at 03:00 vs 17:30 (fig 7)
Every caption states the planner that produced the data, S and that traffic is simulated.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "results" / "demo"
NAVY, TEAL, AMBER, GREY = "#0f172a", "#0d9488", "#f59e0b", "#94a3b8"


def load(name):
    return json.loads((DEMO / name).read_text(encoding="utf-8"))


def draw_routes(ax, res, lw=1.6, alpha=0.9):
    for r in res["routes"]:
        g = r["geometry"]
        ax.plot([p[1] for p in g], [p[0] for p in g], color=r["color"], lw=lw, alpha=alpha)
    depot = res["routes"][0]["geometry"][0]
    ax.plot(depot[1], depot[0], marker="*", ms=14, color=NAVY, zorder=5)


def draw_flows(ax, res):
    segs = [[(e["geometry"][0][1], e["geometry"][0][0]), (e["geometry"][1][1], e["geometry"][1][0])]
            for e in res["edge_flows"]]
    vc = [e["vc_ratio"] for e in res["edge_flows"]]
    lc = LineCollection(segs, cmap="YlOrRd", linewidths=2.2)
    lc.set_array(vc)
    lc.set_clim(0.5, 1.7)
    ax.add_collection(lc)
    return lc


def style_map(ax, title):
    ax.set_title(title, fontsize=11, color=NAVY, loc="left")
    ax.set_aspect(1 / 0.954)            # ~cos(17.4 deg)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#e2e8f0")


def fig_fleet():
    d = load("fleet_demo.json")
    naive, so = d["modes"]["naive"], d["modes"]["system_opt"]
    fig = plt.figure(figsize=(13, 6.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8], wspace=0.08)
    for k, (res, title) in enumerate(((naive, "Naive (every van takes its fastest path)"),
                                      (so, "System-optimal (marginal-cost planning)"))):
        ax = fig.add_subplot(gs[k])
        lc = draw_flows(ax, res)
        ax.autoscale()
        style_map(ax, title)
    cb = fig.colorbar(lc, ax=fig.axes, shrink=0.6, location="bottom", pad=0.04, aspect=40)
    cb.set_label("V/C on edges used by the fleet (background + fleet flow)")
    ax = fig.add_subplot(gs[2])
    labels = ["Externality\n(veh-h)", "Edges over\ncapacity", "Fleet time\n(min)"]
    a = [naive["externality_veh_h"], naive["edges_over_capacity"], naive["kpis"]["total_time_min"]]
    b = [so["externality_veh_h"], so["edges_over_capacity"], so["kpis"]["total_time_min"]]
    x = range(3)
    ax.bar([i - 0.2 for i in x], [1.0] * 3, 0.4, color=GREY, label="naive = 100%")
    ax.bar([i + 0.2 for i in x], [bi / ai for ai, bi in zip(a, b)], 0.4, color=TEAL, label="system-optimal")
    for i, (ai, bi) in enumerate(zip(a, b)):
        ax.text(i - 0.2, 1.02, f"{ai:.0f}", ha="center", fontsize=8)
        ax.text(i + 0.2, bi / ai + 0.02, f"{bi:.0f}", ha="center", fontsize=8, color=TEAL)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("relative to naive"); ax.legend(fontsize=8, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Fleet impact, Hyderabad-60 at 17:30", x=0.01, ha="left", fontsize=13, color=NAVY)
    fig.text(0.01, 0.01, f"Planner: {so['algorithm']}. S = {d['S']:g} vehicle-equivalents per route (modelling "
             "assumption). Traffic simulated (load-ratio + BPR). Source: results/demo/fleet_demo.json",
             fontsize=8, color="#475569")
    out = DEMO / "fig_fleet_impact.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"wrote {out.relative_to(ROOT)}")


def fig_time_of_day():
    night, peak = load("result_0300.json"), load("result_demo.json")
    fig = plt.figure(figsize=(13, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8], wspace=0.08)
    for k, (res, title) in enumerate(((night, "Planned for 03:00"), (peak, "Planned for 17:30"))):
        ax = fig.add_subplot(gs[k])
        draw_routes(ax, res)
        style_map(ax, title)
    ax = fig.add_subplot(gs[2])
    keys = [("total_time_min", "Driving\ntime (min)"), ("congestion_delay_min", "Congestion\ndelay (min)"),
            ("co2_kg", "CO2 (kg)")]
    x = range(len(keys))
    ax.bar([i - 0.2 for i in x], [night["kpis"][k] for k, _ in keys], 0.4, color=GREY, label="03:00")
    ax.bar([i + 0.2 for i in x], [peak["kpis"][k] for k, _ in keys], 0.4, color=AMBER, label="17:30")
    for i, (k, _) in enumerate(keys):
        ax.text(i - 0.2, night["kpis"][k] * 1.01, f"{night['kpis'][k]:.0f}", ha="center", fontsize=8)
        ax.text(i + 0.2, peak["kpis"][k] * 1.01, f"{peak['kpis'][k]:.0f}", ha="center", fontsize=8)
    ax.set_xticks(list(x)); ax.set_xticklabels([l for _, l in keys], fontsize=9)
    ax.legend(fontsize=8); ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Same 60 customers, different departure time", x=0.01, ha="left", fontsize=13, color=NAVY)
    fig.text(0.01, 0.01, f"Planner: {peak['algorithm']}, weights balanced, seed {peak['seed']}. Traffic simulated. "
             "Sources: results/demo/result_0300.json, result_demo.json", fontsize=8, color="#475569")
    out = DEMO / "fig_time_of_day.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    fig_fleet()
    fig_time_of_day()
