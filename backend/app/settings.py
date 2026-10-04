"""Backend settings (§4.3). Limits come from configs/default.yaml (§5.7) so engine and API agree."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = REPO_ROOT / "engine"
if str(ENGINE_DIR) not in sys.path:          # the engine is a standalone package (pip install -e engine)
    sys.path.insert(0, str(ENGINE_DIR))

from qflux.config import load_config  # noqa: E402

CFG = load_config()
LIMITS = CFG["limits"]

VERSION = "0.4.0"
RESULTS_DIR = REPO_ROOT / "results"
DB_URL = os.environ.get("QR_DB_URL", f"sqlite:///{REPO_ROOT / 'backend' / 'quantumroute.db'}")
CORS_ORIGINS = os.environ.get("QR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

MAX_CUSTOMERS = int(LIMITS["max_customers"])          # 1000
MAX_ITERATIONS = int(LIMITS["max_iterations"])        # 5000
MAX_CONCURRENT_JOBS = int(LIMITS["max_concurrent_jobs"])   # 2 (-> 429 above)
JOB_TIMEOUT_S = float(os.environ.get("QR_JOB_TIMEOUT_S", LIMITS["job_timeout_s"]))   # 120 -> COMPLETED_PARTIAL
MAX_SWARM = 200
JOB_WORKERS = int(os.environ.get("QR_JOB_WORKERS", MAX_CONCURRENT_JOBS))

# Seeded at startup (§9 Phase 4 step 2)
SEED_SCENARIOS = [
    {"name": "Hyderabad-60", "source": "hyderabad", "n_customers": 60, "K": CFG["hyd"]["K"], "Q": CFG["hyd"]["Q"],
     "seed": 7, "tau0": CFG["hyd"]["tau0"]},
    {"name": "SynthCity-60", "source": "synth", "n_customers": 60, "K": CFG["hyd"]["K"], "Q": CFG["hyd"]["Q"],
     "seed": 0, "tau0": CFG["hyd"]["tau0"]},
]
