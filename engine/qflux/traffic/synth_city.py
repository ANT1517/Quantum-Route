"""SynthCity: seeded grid city with arterials and a ring road (§6.3). Coordinates are [y, x] in km.

Uses the same traffic model as Hyderabad (§6.4) — there is no second model.
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from qflux.config import load_config

from .profiles import ARTERIAL, RESIDENTIAL
from .roadnet import RoadNet

# (speed km/h, capacity pcu/h, group)
RING = (55.0, 3 * 1800.0, ARTERIAL)       # trunk
ART = (45.0, 2 * 1500.0, ARTERIAL)        # primary, 2 lanes
LOCAL = (25.0, 600.0, RESIDENTIAL)        # residential, 1 lane


def _strongly_connected(N: int, eu: np.ndarray, ev: np.ndarray) -> bool:
    mat = csr_matrix((np.ones(len(eu)), (eu, ev)), shape=(N, N))
    return connected_components(mat, directed=True, connection="strong")[0] == 1


def build_synth(grid: int | None = None, block_km: float | None = None, arterial_every: int | None = None,
                seed: int = 0, delete_frac: float = 0.05) -> RoadNet:
    cfg = load_config()["synth"]
    g = grid or cfg["grid"]
    blk = block_km or cfg["block_km"]
    every = arterial_every or cfg["arterial_every"]
    rng = np.random.default_rng(seed)

    def cls(line: int):
        if line in (0, g - 1):
            return RING
        return ART if line % every == 0 else LOCAL

    und = []   # undirected segments (a, b, class)
    for r in range(g):
        for c in range(g):
            a = r * g + c
            if c + 1 < g:
                und.append((a, a + 1, cls(r)))          # horizontal: class of its row
            if r + 1 < g:
                und.append((a, a + g, cls(c)))          # vertical: class of its column
    # delete ~5% of local segments while keeping strong connectivity
    keep = np.ones(len(und), bool)
    local = [k for k, s in enumerate(und) if s[2] is LOCAL]
    for k in rng.permutation(local)[: int(round(delete_frac * len(local)))]:
        keep[k] = False
        eu = np.array([s[0] for s, kk in zip(und, keep) if kk] + [s[1] for s, kk in zip(und, keep) if kk])
        ev = np.array([s[1] for s, kk in zip(und, keep) if kk] + [s[0] for s, kk in zip(und, keep) if kk])
        if not _strongly_connected(g * g, eu, ev):
            keep[k] = True                               # re-add
    segs = [s for s, kk in zip(und, keep) if kk]
    eu = np.array([a for a, b, _ in segs] + [b for a, b, _ in segs], np.int32)
    ev = np.array([b for a, b, _ in segs] + [a for a, b, _ in segs], np.int32)
    spd = np.array([s[2][0] for s in segs] * 2)
    cap = np.array([s[2][1] for s in segs] * 2)
    grp = np.array([s[2][2] for s in segs] * 2, np.int8)
    L = np.full(len(eu), blk)
    rr, cc = np.divmod(np.arange(g * g), g)
    xy = np.stack([rr * blk, cc * blk], axis=1).astype(float)
    return RoadNet(node_id=np.arange(g * g, dtype=np.int64), node_xy=xy, eu=eu, ev=ev, length_km=L,
                   t0_min=L / spd * 60.0, capacity=cap, group=grp, latlon=False)


def synth_customers(net: RoadNet, n: int, seed: int = 0):
    """(terminals, demand, service): depot = centre node, customers = random distinct nodes."""
    rng = np.random.default_rng(seed)
    g = int(round(np.sqrt(net.N)))
    depot = (g // 2) * g + g // 2
    others = np.setdiff1d(np.arange(net.N), [depot])
    if n > len(others):
        raise ValueError(f"SynthCity grid {g}x{g} has only {len(others)} customer nodes")
    cust = rng.choice(others, size=n, replace=False)
    terminals = np.concatenate([[depot], cust]).astype(np.int64)
    demand = np.concatenate([[0], rng.integers(5, 26, size=n)]).astype(float)
    service = np.concatenate([[0.0], np.full(n, 5.0)])
    return terminals, demand, service
