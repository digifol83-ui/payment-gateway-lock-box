"""
uae_sme.yardstick
=================
Yardstick Percentage calculator.

Formula:
    Yardstick % = (Agent Overall Success Rate / Yardstick Target) × 100

Default target: 80 % (YARDSTICK_TARGET in data.py)

Public API:
    calculate_yardstick(simulation_results, target) -> list[dict]
"""
from .data import YARDSTICK_TARGET


def calculate_yardstick(
    simulation_results: list[dict],
    target: float = None,
) -> list[dict]:
    """
    Append yardstick_pct to each simulation result row.

    Args:
        simulation_results: output of run_simulation()
        target:             yardstick target rate 0–1 (default YARDSTICK_TARGET = 0.80)

    Returns:
        same list with yardstick_pct added to each dict
    """
    target = target if target is not None else YARDSTICK_TARGET

    enriched = []
    for row in simulation_results:
        agent_rate = row["agent_success"] / 100.0
        yardstick  = round((agent_rate / target) * 100, 1)
        enriched.append({**row, "yardstick_pct": yardstick})

    return enriched
