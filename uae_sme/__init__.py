"""
uae_sme — UAE SME Payment Gateway Optimization Module
Master Technical Specification: BeastPay / OpenClaw

Submodules:
  data            — 10 UAE SME company profiles + report constants
  simulation      — agent impact simulation engine
  yardstick       — yardstick percentage calculator
  proxy_validator — performance tier classifier + validation status
  report          — consolidated report runner (CLI + API)
"""
from .data import SME_COMPANIES, BASELINE_BENCHMARKS, YARDSTICK_TARGET
from .simulation import run_simulation
from .yardstick import calculate_yardstick
from .proxy_validator import classify, validate, run_proxy_validator
from .report import generate_report

__all__ = [
    "SME_COMPANIES",
    "BASELINE_BENCHMARKS",
    "YARDSTICK_TARGET",
    "run_simulation",
    "calculate_yardstick",
    "classify",
    "validate",
    "run_proxy_validator",
    "generate_report",
]
