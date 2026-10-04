"""API tests T18-T27 (§10.1). Uses a temporary SQLite DB and a short job timeout.

Tests marked `jobs` run real optimizations (CPU heavy): skip them while a benchmark is running
(pytest -m "not jobs").
"""
import os
import tempfile
import time
from pathlib import Path

import pytest

_DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ["QR_DB_URL"] = f"sqlite:///{_DB.as_posix()}"
os.environ["QR_JOB_TIMEOUT_S"] = "6"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

W = {"wT": 0.5, "wD": 0.2, "wC": 0.2, "wE": 0.1}
SYNTH = {"name": "synth-test", "source": "synth", "n_customers": 20, "K": 4, "Q": 200, "seed": 3, "tau0": 1050}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def synth_id(client):
    r = client.post("/api/scenarios", json=SYNTH)
    assert r.status_code == 201, r.text
    return r.json()["scenario"]["id"]


def wait(client, job_id, timeout=90):
    t = time.time()
    while time.time() - t < timeout:
        st = client.get(f"/api/jobs/{job_id}").json()["status"]
        if st in ("COMPLETED", "COMPLETED_PARTIAL", "FAILED", "CANCELLED"):
            return st
        time.sleep(0.2)
    raise TimeoutError(job_id)


def test_health_and_seeded_scenarios(client):
    assert client.get("/api/health").json()["status"] == "ok"
    names = {s["name"] for s in client.get("/api/scenarios").json()}
    assert {"Hyderabad-60", "SynthCity-60"} <= names


def test_t18_create_scenario(client, synth_id):
    d = client.get(f"/api/scenarios/{synth_id}").json()
    assert d["scenario"]["id"] == synth_id and len(d["customers"]) == 20 and "lat" in d["depot"]


def test_t19_infeasible_scenario(client):
    r = client.post("/api/scenarios", json={**SYNTH, "name": "too-small", "K": 1, "Q": 30})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INFEASIBLE"


def test_invalid_input_is_400_with_fields(client):
    r = client.post("/api/scenarios", json={"name": "x", "source": "mars"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_INPUT"
    assert "source" in r.json()["error"]["message"]


def test_t20_weights_must_sum_to_one(client, synth_id):
    r = client.post("/api/jobs", json={"scenario_id": synth_id, "algorithm": "qpso",
                                       "weights": {"wT": 0.5, "wD": 0.1, "wC": 0.1, "wE": 0.1}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "WEIGHTS"


def test_unknown_job_and_scenario_404(client):
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.get("/api/scenarios/nope").json()["error"]["code"] == "NOT_FOUND"


def test_t26_files_whitelist(client):
    for bad in ("../secret", "..%2F..%2Fengine%2Fqflux%2Fapi.py", "runs/../../README.md", "C:/Windows/win.ini"):
        r = client.get(f"/api/files/{bad}")
        assert r.status_code == 404, bad
    tables = sorted(Path("results/tables").glob("*.csv"))
    if tables:
        assert client.get(f"/api/files/tables/{tables[0].name}").status_code == 200


def test_t27_sql_injection_name_stored_safely(client):
    evil = "x'); DROP TABLE scenarios; --"
    r = client.post("/api/scenarios", json={**SYNTH, "name": evil})
    assert r.status_code == 201
    names = [s["name"] for s in client.get("/api/scenarios").json()]
    assert evil in names and "Hyderabad-60" in names


def test_benchmarks_listing_marks_kinds(client):
    default = client.get("/api/benchmarks").json()
    assert all(it["kind"] == "benchmark" for it in default)      # Benchmark Studio has no kind filter
    for it in client.get("/api/benchmarks?all=true").json():
        if it["name"].startswith("tune_"):
            assert "not a benchmark" in it["kind"]
        assert "v0_partial" not in it["name"]


def test_benchmark_rows_have_p_values_and_run_arrays(client):
    items = client.get("/api/benchmarks?all=true").json()
    if not items:
        pytest.skip("no tables yet")
    d = client.get(f"/api/benchmarks/{items[0]['name']}").json()
    row = d["table"][0]
    assert {"instance", "algo", "gap_mean_pct", "gap_runs_pct"} <= set(row)
    assert any(k.startswith("wilcoxon_p_holm_vs_") for k in row)
    assert isinstance(d["meta"]["budget"], str) and d["meta"]["budget"]


@pytest.mark.jobs
def test_t21_job_lifecycle(client, synth_id):
    r = client.post("/api/jobs", json={"scenario_id": synth_id, "algorithm": "qpso", "weights": W, "seed": 1,
                                       "budget": {"time_s": 2}})
    assert r.status_code == 201 and r.json()["status"] == "QUEUED"
    jid = r.json()["job_id"]
    assert wait(client, jid) == "COMPLETED"
    res = client.get(f"/api/jobs/{jid}/result")
    assert res.status_code == 200 and res.json()["kpis"]["feasible"] is True
    assert len(client.get(f"/api/jobs/{jid}/convergence").json()) > 0


@pytest.mark.jobs
def test_t22_result_before_finish_is_409(client, synth_id):
    jid = client.post("/api/jobs", json={"scenario_id": synth_id, "algorithm": "qpso", "weights": W,
                                         "budget": {"time_s": 5}}).json()["job_id"]
    r = client.get(f"/api/jobs/{jid}/result")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_FINISHED"
    wait(client, jid)


@pytest.mark.jobs
def test_t23_cancel_keeps_best_so_far(client, synth_id):
    jid = client.post("/api/jobs", json={"scenario_id": synth_id, "algorithm": "qpso", "weights": W,
                                         "budget": {"evals": 500000}}).json()["job_id"]
    t = time.time()
    while client.get(f"/api/jobs/{jid}").json()["status"] != "RUNNING" and time.time() - t < 60:
        time.sleep(0.2)
    time.sleep(1.0)
    assert client.post(f"/api/jobs/{jid}/cancel").json()["status"] == "CANCELLED"
    assert client.get(f"/api/jobs/{jid}/result").json()["kpis"]["feasible"] is True
    assert client.post(f"/api/jobs/{jid}/cancel").status_code == 409


@pytest.mark.jobs
def test_t24_third_concurrent_job_is_429(client, synth_id):
    body = {"scenario_id": synth_id, "algorithm": "qpso", "weights": W, "budget": {"time_s": 4}}
    a = client.post("/api/jobs", json=body).json()["job_id"]
    b = client.post("/api/jobs", json=body).json()["job_id"]
    r = client.post("/api/jobs", json=body)
    assert r.status_code == 429 and r.json()["error"]["code"] == "TOO_MANY_JOBS"
    wait(client, a), wait(client, b)


@pytest.mark.jobs
def test_t25_large_instance_timeout_is_partial(client):
    """§10.1 asks for n = 1000. SynthCity's default 20x20 grid has 399 customer nodes, and a 1000-customer road
    scenario needs ~1-1.5 GB for its per-slot path store (too much next to the benchmark memory limits), so
    the largest default-grid scenario is used: n = 399 (deviation logged in MERGE_NOTES / D52)."""
    r = client.post("/api/scenarios", json={**SYNTH, "name": "synth-399", "n_customers": 399, "K": 60, "Q": 200})
    assert r.status_code == 201, r.text
    sid = r.json()["scenario"]["id"]
    jid = client.post("/api/jobs", json={"scenario_id": sid, "algorithm": "qpso", "weights": W,
                                         "budget": {"evals": 1000000}}).json()["job_id"]
    assert wait(client, jid, timeout=600) == "COMPLETED_PARTIAL"
    assert client.get(f"/api/jobs/{jid}/result").json()["kpis"]["feasible"] is True


@pytest.mark.jobs
def test_websocket_progress(client, synth_id):
    jid = client.post("/api/jobs", json={"scenario_id": synth_id, "algorithm": "qpso", "weights": W,
                                         "budget": {"time_s": 3}}).json()["job_id"]
    types = []
    with client.websocket_connect(f"/ws/jobs/{jid}") as ws:
        while True:
            m = ws.receive_json()
            types.append(m["type"])
            if m["type"] in ("completed", "failed"):
                break
    assert types[-1] == "completed"


def test_websocket_unknown_job_closes_4404(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as e:
        with client.websocket_connect("/ws/jobs/nope") as ws:
            ws.receive_json()
    assert e.value.code == 4404


def test_d53_default_engine_is_qpso_noqubo():
    from backend.app.schemas import JobCreate
    from backend.app.services.job_params import engine_job
    body = JobCreate(scenario_id="x", algorithm="qpso", weights=W)
    j = engine_job(body, None)
    assert j["params"]["qubo_slot"] == {"enabled": False} and j["label"] == "qpso_noqubo"
    body = JobCreate(scenario_id="x", algorithm="qpso", weights=W, params={"qubo_slot": True})
    j = engine_job(body, None)
    assert j["params"]["qubo_slot"] == {"enabled": True} and j["label"] == "qpso_full"
