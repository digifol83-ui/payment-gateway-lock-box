"""
uae_sme.report
==============
Consolidated report runner.

Chains: simulation → yardstick → proxy_validator → formatted output.

CLI usage:
    python3 -m uae_sme.report [--seed N] [--csv path]

API usage:
    from uae_sme.report import generate_report
    data = generate_report()
"""
import argparse
import csv
import sys
from .data import SME_COMPANIES, BASELINE_BENCHMARKS, YARDSTICK_TARGET
from .simulation import run_simulation
from .yardstick import calculate_yardstick
from .proxy_validator import run_proxy_validator

# Validation status display icons
_ICON = {"PASS": "✓", "CONDITIONAL PASS": "~", "FAIL": "✗"}


def generate_report(seed: int = None) -> dict:
    """
    Run the full analysis pipeline.

    Args:
        seed: random seed for reproducible simulation (None = stochastic)

    Returns:
        {
            "simulation":        list[dict],
            "yardstick":         list[dict],
            "proxy_validator":   dict (rows, pass, conditional_pass, fail, counts),
        }
    """
    sim    = run_simulation(SME_COMPANIES, BASELINE_BENCHMARKS, seed=seed)
    yard   = calculate_yardstick(sim, target=YARDSTICK_TARGET)
    proxy  = run_proxy_validator(yard)
    return {"simulation": sim, "yardstick": yard, "proxy_validator": proxy}


def _print_section(title: str):
    width = 80
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def _print_report(report: dict):
    proxy  = report["proxy_validator"]
    rows   = proxy["rows"]
    counts = proxy["counts"]

    # ── Simulation Results ────────────────────────────────────────────────────
    _print_section("1. Agent Impact Simulation Results")
    print(f"  {'Company':<24} {'Sector':<24} {'Baseline':>9} {'Agent':>7} {'Δ%':>8}")
    print(f"  {'─'*24} {'─'*24} {'─'*9} {'─'*7} {'─'*8}")
    for r in rows:
        print(
            f"  {r['company']:<24} {r['sector']:<24} "
            f"{r['baseline_success']:>8.1f}% {r['agent_success']:>6.1f}% "
            f"{r['improvement_pct']:>7.1f}%"
        )

    # ── Yardstick ─────────────────────────────────────────────────────────────
    _print_section(f"2. Yardstick Percentage  (target = {int(YARDSTICK_TARGET*100)}%)")
    print(f"  {'Company':<24} {'Agent Success':>14} {'Yardstick %':>12}")
    print(f"  {'─'*24} {'─'*14} {'─'*12}")
    for r in rows:
        print(f"  {r['company']:<24} {r['agent_success']:>13.1f}% {r['yardstick_pct']:>11.1f}%")

    # ── Proxy Validator ───────────────────────────────────────────────────────
    _print_section("3. Proxy Validator Report")
    print(f"  {'St'} {'Company':<24} {'Agent%':>7} {'Yardstick%':>11} {'Class':<12} {'Status'}")
    print(f"  {'──'} {'─'*24} {'─'*7} {'─'*11} {'─'*12} {'─'*16}")
    for r in rows:
        icon = _ICON.get(r["validation_status"], "?")
        print(
            f"  {icon}  {r['company']:<24} "
            f"{r['agent_success']:>6.1f}% "
            f"{r['yardstick_pct']:>10.1f}% "
            f"  {r['classification']:<12} "
            f"{r['validation_status']}"
        )

    # ── Tier Groups ───────────────────────────────────────────────────────────
    _print_section("4. Tier Groups")

    def _tier(label, items):
        if not items:
            return
        print(f"\n  {label} ({len(items)})")
        for r in items:
            print(f"    • {r['company']:<22} {r['agent_success']:.1f}%  —  {r['sector']}")

    _tier("✓ PASS",             proxy["pass"])
    _tier("~ CONDITIONAL PASS", proxy["conditional_pass"])
    _tier("✗ FAIL",             proxy["fail"])

    # ── Summary ───────────────────────────────────────────────────────────────
    _print_section("5. Summary")
    print(
        f"  Total clients : {counts['total']}\n"
        f"  PASS          : {counts['pass']}\n"
        f"  CONDITIONAL   : {counts['conditional_pass']}\n"
        f"  FAIL          : {counts['fail']}\n"
    )

    # ── Agent Strategies for FAIL clients ─────────────────────────────────────
    _print_section("6. Recommended Agent Strategies (FAIL clients)")
    for r in proxy["fail"]:
        print(f"\n  {r['company']}  [{r['classification']}]")
        print(f"    Bottleneck : {r['bottleneck']}")
        print(f"    Strategy   : {r['agent_strategy']}")


def _write_csv(report: dict, path: str):
    rows = report["proxy_validator"]["rows"]
    fieldnames = [
        "company", "sector", "compliance", "risk",
        "baseline_success", "agent_success", "improvement_pct",
        "yardstick_pct", "classification", "validation_status",
        "bottleneck", "agent_strategy",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n  CSV saved → {path}")


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="UAE SME Payment Gateway Optimization — Report Runner"
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible simulation")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to export results as CSV")
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║  BeastPay / OpenClaw — UAE SME Payment Gateway Optimization Report          ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")

    report = generate_report(seed=args.seed)
    _print_report(report)

    if args.csv:
        _write_csv(report, args.csv)

    sys.exit(0)
