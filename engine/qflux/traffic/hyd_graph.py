"""Hyderabad drive graph: download once, cache, convert to RoadNet arrays (§6.2)."""
from pathlib import Path

import numpy as np
import pandas as pd

from qflux.config import REPO_ROOT, load_config

from .roadnet import RoadNet, class_params

HYD_DIR = REPO_ROOT / "data" / "hyd"
GRAPHML = HYD_DIR / "hyd_drive.graphml"
ROADNET_NPZ = HYD_DIR / "roadnet.npz"
CUSTOMERS_CSV = REPO_ROOT / "data" / "customers_hyd.csv"

# Approximate area centres (lat, lon), used only to sample illustrative customer locations
AREAS = {
    "Hitech City": (17.4474, 78.3762), "Gachibowli": (17.4401, 78.3489), "Madhapur": (17.4483, 78.3915),
    "Kondapur": (17.4640, 78.3640), "Kukatpally": (17.4948, 78.3996), "Ameerpet": (17.4375, 78.4482),
    "Begumpet": (17.4447, 78.4664), "Secunderabad": (17.4399, 78.4983), "Banjara Hills": (17.4156, 78.4347),
    "Jubilee Hills": (17.4326, 78.4071), "Abids": (17.3918, 78.4758), "Dilsukhnagar": (17.3688, 78.5247),
    "LB Nagar": (17.3457, 78.5522), "Mehdipatnam": (17.3959, 78.4312), "Tolichowki": (17.3988, 78.4136),
}
DEPOT_LATLON = (17.4717, 78.4479)   # Balanagar logistics hub (illustrative)


def download_graph(dist_m: int | None = None):
    """Download the OSM drive network (slow; run once via scripts/build_hyd.py)."""
    import osmnx as ox
    cfg = load_config()["hyd"]
    G = ox.graph_from_point(tuple(cfg["center"]), dist=dist_m or cfg["radius_m"], network_type="drive",
                            simplify=True)
    G = ox.truncate.largest_component(G, strongly=True)      # guarantees reachability
    HYD_DIR.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, GRAPHML)
    return G


def graph_to_roadnet(G) -> RoadNet:
    """Class-based free-flow speeds and capacities (§6.2). OSM maxspeed is ignored for consistency."""
    nodes = list(G.nodes)
    index = {n: i for i, n in enumerate(nodes)}
    xy = np.array([[G.nodes[n]["y"], G.nodes[n]["x"]] for n in nodes], dtype=float)
    eu, ev, L, T0, C, grp = [], [], [], [], [], []
    for u, v, d in G.edges(data=True):
        speed, cap, g = class_params(d.get("highway", "residential"))
        length_km = max(float(d.get("length", 1.0)), 1.0) / 1000.0
        eu.append(index[u]); ev.append(index[v]); L.append(length_km)
        T0.append(length_km / speed * 60.0); C.append(cap); grp.append(g)
    return RoadNet(node_id=np.array(nodes, dtype=np.int64), node_xy=xy, eu=np.array(eu, np.int32),
                   ev=np.array(ev, np.int32), length_km=np.array(L), t0_min=np.array(T0),
                   capacity=np.array(C), group=np.array(grp, np.int8), latlon=True)


def load_roadnet() -> RoadNet:
    if not ROADNET_NPZ.exists():
        raise FileNotFoundError(f"{ROADNET_NPZ} missing: run `python scripts/build_hyd.py` first")
    return RoadNet.load(ROADNET_NPZ)


def make_customers(net: RoadNet, n: int = 60, seed: int = 7) -> pd.DataFrame:
    """n illustrative customers sampled round-robin around the listed areas, snapped to graph nodes.

    Row 0 is the depot. Demand ~ U{5..25}, service 5 min (§6.2).
    """
    rng = np.random.default_rng(seed)
    names = list(AREAS)
    depot_node = net.nearest_node(DEPOT_LATLON)
    used = {depot_node}
    rows = [dict(id=0, area="Balanagar (depot)", lat=net.node_xy[depot_node, 0], lon=net.node_xy[depot_node, 1],
                 osmid=int(net.node_id[depot_node]), demand=0, service=0.0)]
    k = 0
    while len(rows) <= n:
        area = names[k % len(names)]
        k += 1
        lat, lon = AREAS[area]
        node = net.nearest_node((lat + rng.normal(0, 0.006), lon + rng.normal(0, 0.006)))  # ~650 m jitter
        if node in used:
            continue
        used.add(node)
        rows.append(dict(id=len(rows), area=area, lat=net.node_xy[node, 0], lon=net.node_xy[node, 1],
                         osmid=int(net.node_id[node]), demand=int(rng.integers(5, 26)), service=5.0))
    return pd.DataFrame(rows)


def customers_path(n: int) -> Path:
    return CUSTOMERS_CSV if n == 60 else REPO_ROOT / "data" / f"customers_hyd_{n}.csv"


def load_customers(net: RoadNet, n: int = 60, seed: int = 7) -> pd.DataFrame:
    """Customers table with a `node_index` column valid for `net` (row 0 = depot)."""
    path = customers_path(n)
    if path.exists() and seed == 7:
        df = pd.read_csv(path)
    else:
        df = make_customers(net, n, seed)
        if seed == 7:
            df.to_csv(path, index=False)
    idx = {int(o): i for i, o in enumerate(net.node_id)}
    df["node_index"] = [idx[int(o)] for o in df["osmid"]]
    return df
