"""Build (or refresh) the cached Hyderabad graph, customers and TD matrices.

    python scripts/build_hyd.py              # uses cached GraphML if present
    python scripts/build_hyd.py --dist 8000  # smaller download if Overpass is slow
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from qflux.traffic import hyd_graph  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", type=int, default=None)
    ap.add_argument("--graph-only", action="store_true")
    ap.add_argument("--n", type=int, nargs="*", default=[60])
    ap.add_argument("--rebuild", action="store_true", help="re-derive roadnet.npz from the GraphML")
    args = ap.parse_args()

    t = time.time()
    if hyd_graph.ROADNET_NPZ.exists() and not args.rebuild:
        print("using cached roadnet.npz")
        net = hyd_graph.load_roadnet()
    else:
        import osmnx as ox
        if hyd_graph.GRAPHML.exists():
            print("loading cached GraphML ...")
            G = ox.load_graphml(hyd_graph.GRAPHML)
        else:
            print("downloading OSM drive network (slow, once) ...", flush=True)
            G = hyd_graph.download_graph(args.dist)
        print(f"graph: {len(G.nodes)} nodes, {len(G.edges)} edges ({time.time() - t:.0f} s)")
        net = hyd_graph.graph_to_roadnet(G)
        net.save(hyd_graph.ROADNET_NPZ)
        print(f"saved {hyd_graph.ROADNET_NPZ}")
    if args.graph_only:
        return

    from qflux import api
    for n in args.n:
        df = hyd_graph.load_customers(net, n)
        print(f"customers: {len(df) - 1} -> {hyd_graph.customers_path(n)}")
        t = time.time()
        inst = api.build_instance({"source": "hyderabad", "n_customers": n})
        print(f"TD matrices for {inst.name}: {time.time() - t:.1f} s")


if __name__ == "__main__":
    main()
