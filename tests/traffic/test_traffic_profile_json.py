"""The UI's 24-hour congestion chart reads frontend/src/data/traffic_profile.json; its values must be an exact
copy of engine/qflux/traffic/profiles.py (UI redesign v3: the only allowed data addition)."""
import json
from pathlib import Path

from qflux.traffic import profiles

ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / "frontend" / "src" / "data" / "traffic_profile.json"


def test_traffic_profile_json_matches_engine():
    d = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert d["source"] == "engine/qflux/traffic/profiles.py"
    assert d["day_min"] == float(profiles.DAY)
    assert d["slot_centers_min"] == [float(x) for x in profiles.SLOT_CENTERS]
    assert d["slot_labels"] == list(profiles.SLOT_LABELS)
    assert d["groups"] == list(profiles.GROUP_NAMES)
    assert d["load_ratio"] == [[float(x) for x in row] for row in profiles.LOAD_RATIO]


def test_traffic_profile_json_interpolation_matches_engine():
    """Re-implements the chart's interpolation (frontend/src/lib/trafficProfile.ts) and checks it against
    profiles.load_ratio at every 10 minutes, including the wrap around midnight."""
    import numpy as np

    d = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    c, M, day = d["slot_centers_min"], d["load_ratio"], d["day_min"]
    S = len(c)

    def ui_value(t, g):
        t = t % day
        if t < c[0] or t >= c[-1]:
            s, s1, span = S - 1, 0, c[0] + day - c[-1]
            lam = ((t - c[-1]) % day) / span
        else:
            s = max(i for i in range(S) if c[i] <= t)
            s1 = s + 1
            lam = (t - c[s]) / (c[s1] - c[s])
        return (1 - lam) * M[s][g] + lam * M[s1][g]

    for t in range(0, 1440, 10):
        eng = profiles.load_ratio(float(t), np.array([0, 1, 2]))
        for g in range(3):
            assert abs(ui_value(float(t), g) - float(eng[g])) < 1e-12
