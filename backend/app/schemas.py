"""Request bodies (§5.4) with the §9 Phase 4 bounds. Shape errors -> 400 with the field list; semantic
errors (weights not summing to 1, infeasible scenario, budget too large) -> 422 (§10.1 T19/T20)."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .settings import MAX_CUSTOMERS, MAX_ITERATIONS, MAX_SWARM

Source = Literal["hyderabad", "synth", "cvrplib"]
FleetMode = Literal["naive", "user_eq", "system_opt"]
JobAlgorithm = Literal["qpso", "pso", "ga", "sa", "ortools", "milp"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScenarioCreate(Strict):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    source: Source
    n_customers: Annotated[int, Field(ge=1, le=MAX_CUSTOMERS)]
    K: Annotated[int, Field(ge=1, le=MAX_CUSTOMERS)]
    Q: Annotated[float, Field(gt=0)]
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)] = 0
    tau0: Annotated[float, Field(ge=0, lt=1440)] = 480.0


class ZoneIncident(Strict):
    type: Literal["zone"]
    center: tuple[float, float]
    radius_m: Annotated[float, Field(gt=0, le=20000)]
    factor: Annotated[float, Field(ge=1.0, le=20.0)]
    start_min: Annotated[float, Field(ge=0, le=1440)]
    end_min: Annotated[float, Field(ge=0, le=1440)]


class EdgesIncident(Strict):
    type: Literal["edges"]
    edge_ids: Annotated[list[int | str], Field(min_length=1)]
    factor: Annotated[float, Field(ge=1.0, le=20.0)] = 2.5
    start_min: Annotated[float, Field(ge=0, le=1440)] = 0.0
    end_min: Annotated[float, Field(ge=0, le=1440)] = 1440.0


class WeightsIn(Strict):
    wT: Annotated[float, Field(ge=0)]
    wD: Annotated[float, Field(ge=0)]
    wC: Annotated[float, Field(ge=0)]
    wE: Annotated[float, Field(ge=0)]
    lam: Annotated[float, Field(ge=0)] | None = None

    def total(self) -> float:
        return self.wT + self.wD + self.wC + self.wE


class Budget(Strict):
    evals: Annotated[int, Field(ge=1, le=1_000_000)] | None = None
    time_s: Annotated[float, Field(gt=0, le=600)] | None = None


class JobParams(BaseModel):
    """Frontend names (§8.1 S3); unknown keys are kept and passed to the optimizer."""
    model_config = ConfigDict(extra="allow")
    N: Annotated[int, Field(ge=2, le=MAX_SWARM)] | None = None
    iterations: Annotated[int, Field(ge=1, le=MAX_ITERATIONS)] | None = None
    alpha_start: Annotated[float, Field(gt=0, lt=1.78)] | None = None
    alpha_end: Annotated[float, Field(gt=0, lt=1.78)] | None = None


class JobCreate(Strict):
    scenario_id: Annotated[str, Field(min_length=1, max_length=64)]
    algorithm: JobAlgorithm
    weights: WeightsIn
    params: JobParams = JobParams()
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)] = 0
    budget: Budget = Budget()
    fleet_mode: FleetMode = "naive"
    warm_start_job_id: str | None = None


class ShortestPathIn(Strict):
    scenario_id: str
    source: tuple[float, float]
    target: tuple[float, float]
    depart_min: Annotated[float, Field(ge=0, lt=1440)]
    algorithm: Literal["dijkstra", "astar", "qpso"] = "dijkstra"
    weights: dict[str, float] | None = None


class FleetCompareIn(Strict):
    scenario_id: str
    modes: Annotated[list[FleetMode], Field(min_length=1)]
    S: Annotated[float, Field(gt=0, le=1000)] = 25
    weights: WeightsIn
    seed: int = 0

    @field_validator("modes")
    @classmethod
    def unique(cls, v):
        return list(dict.fromkeys(v))


class SolveRouteIn(Strict):
    route_stops: Annotated[list[int], Field(min_length=2)]
    backend: Literal["neal", "brute", "2opt", "heldkarp", "qiskit", "dwave"] = "neal"
    job_id: str | None = None          # optional: which job's scenario the stops belong to
    scenario_id: str | None = None
