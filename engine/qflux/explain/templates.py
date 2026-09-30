"""Deterministic explanation sentences built only from computed numbers (§7.14). No LLM."""


def _hhmm(minutes: float) -> str:
    m = int(round(minutes)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def route_sentence(r: dict) -> str:
    return (f"Vehicle {r['vehicle']} serves {len(r['stops'])} stops (load {r['load']:.0f}/{r['capacity']:.0f}) "
            f"in {r['time_min']:.0f} min, of which {r['congestion_delay_min']:.0f} min is congestion delay; "
            f"{r['distance_km']:.1f} km; {r['co2_kg']:.1f} kg CO2.")


def summary_sentences(kpis: dict, tau0: float) -> list[str]:
    out = []
    used, K = kpis["vehicles_used"], kpis["fleet_limit"]
    fleet = f"{used} of {K} vehicles" if K is not None else f"{used} vehicles"
    out.append(f"Plan departs at {_hhmm(tau0)} and uses {fleet}: {kpis['total_time_min']:.0f} min total driving, "
               f"{kpis['total_distance_km']:.1f} km, {kpis['co2_kg']:.1f} kg CO2.")
    if kpis["total_time_min"] > 0:
        share = 100.0 * kpis["congestion_delay_min"] / kpis["total_time_min"]
        out.append(f"Congestion accounts for {kpis['congestion_delay_min']:.0f} min ({share:.0f}%) of driving "
                   f"time (simulated traffic).")
    if K is not None and used > K:
        out.append(f"The plan needs {used - K} more vehicle(s) than the fleet limit; a penalty was applied.")
    return out


def incident_sentence(vehicle: int, area: str, d_before_km: float, d_after_km: float) -> str:
    pct = 100.0 * (d_after_km - d_before_km) / max(d_before_km, 1e-9)
    return f"Vehicle {vehicle} avoids the simulated incident zone near {area} at {pct:+.0f}% distance."


def reroute_sentences(report: dict) -> list[str]:
    out = []
    if report["accepted"]:
        how = "detours and re-sequenced stops" if report.get("resequenced") else "road-level detours"
        out.append(f"Re-routing after the simulated incident ({how}) saves {report['delay_avoided_min']:.1f} min "
                   f"of driving versus vehicles keeping their old road paths "
                   f"({report['reopt_time_s']:.1f} s to re-plan).")
    else:
        out.append("Re-routing found no cheaper plan under the new traffic, so the original routes and paths were kept.")
    affected = [e for e in report.get("eta_change", []) if e.get("affected")]
    if affected:
        out.append(f"{len(affected)} vehicle(s) had a remaining road path through the incident zone.")
    return out


def fleet_sentence(naive: dict, so: dict) -> str:
    diff = naive["externality_veh_h"] - so["externality_veh_h"]
    verb = "reducing" if diff >= 0 else "increasing"
    dt = so["kpis"]["total_time_min"] - naive["kpis"]["total_time_min"]
    return (f"System-optimal routing used {so['corridors_used']} major-road corridors (naive: "
            f"{naive['corridors_used']}), {verb} the delay imposed on background traffic by {abs(diff):.1f} "
            f"vehicle-hours, at {dt:+.0f} min of fleet driving time.")


def shortest_path_sentence(before: dict, after: dict) -> str:
    return (f"With the simulated incident the fastest path ETA changes from {before['eta_min']:.1f} to "
            f"{after['eta_min']:.1f} min.")
