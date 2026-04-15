"""
uae_sme.simulation
==================
Agent impact simulation engine.

Models baseline (no agent) vs agent-assisted success rates across
four verification stages. Compliance and risk profiles adjust the
base rate; agent_intervention adds a 10–20 % stochastic boost.

Public API:
    run_simulation(companies, benchmarks, seed) -> list[dict]
"""
import random
from .data import SME_COMPANIES, BASELINE_BENCHMARKS


# ── Internal helpers ──────────────────────────────────────────────────────────

def _compliance_delta(compliance: str) -> float:
    return {"Very High": +0.05, "Medium": -0.05}.get(compliance, 0.0)


def _risk_delta(risk: str) -> float:
    return {"Low": +0.05, "Medium-High": -0.10, "Medium": -0.05}.get(risk, 0.0)


def _stage_rate(company: dict, benchmark: tuple[float, float], agent: bool) -> float:
    base = random.uniform(*benchmark)
    base += _compliance_delta(company["compliance"])
    base += _risk_delta(company["risk"])
    if agent:
        base += random.uniform(0.10, 0.20)
    return min(max(base, 0.0), 1.0)


def _overall(company: dict, benchmarks: dict, agent: bool) -> float:
    rate = 1.0
    for stage_range in benchmarks.values():
        rate *= _stage_rate(company, stage_range, agent)
    return rate


# ── Public API ────────────────────────────────────────────────────────────────

def run_simulation(
    companies: list[dict] = None,
    benchmarks: dict = None,
    seed: int = None,
) -> list[dict]:
    """
    Run the agent impact simulation.

    Args:
        companies:  list of SME company dicts (defaults to SME_COMPANIES)
        benchmarks: stage benchmark ranges (defaults to BASELINE_BENCHMARKS)
        seed:       random seed for reproducible runs (None = stochastic)

    Returns:
        list of result dicts with keys:
            company, sector, baseline_success, agent_success,
            improvement_pct, bottleneck
    """
    if seed is not None:
        random.seed(seed)

    companies  = companies  or SME_COMPANIES
    benchmarks = benchmarks or BASELINE_BENCHMARKS

    results = []
    for company in companies:
        baseline = _overall(company, benchmarks, agent=False)
        with_agent = _overall(company, benchmarks, agent=True)
        improvement = (with_agent - baseline) / baseline if baseline > 0 else 0.0

        results.append({
            "company":          company["name"],
            "sector":           company["sector"],
            "compliance":       company["compliance"],
            "risk":             company["risk"],
            "baseline_success": round(baseline * 100, 1),
            "agent_success":    round(with_agent * 100, 1),
            "improvement_pct":  round(improvement * 100, 1),
            "bottleneck":       company["bottleneck"],
            "agent_strategy":   company["agent_strategy"],
        })

    return results
