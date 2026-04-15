"""
uae_sme.proxy_validator
=======================
Proxy Validator — classifies agents by success rate tier and assigns
a validation status.

Classification thresholds (agent_success %):
    Excellent    >= 80 %   → PASS
    Good         70–79 %   → PASS
    Fair         60–69 %   → CONDITIONAL PASS
    Poor         50–59 %   → FAIL
    Unacceptable < 50 %    → FAIL

Public API:
    classify(agent_success_pct)         -> str   (e.g. "Excellent")
    validate(classification)            -> str   (e.g. "PASS")
    run_proxy_validator(yardstick_rows) -> dict  (full report with tier groups)
"""

# ── Thresholds ────────────────────────────────────────────────────────────────
THRESHOLD_EXCELLENT   = 80.0
THRESHOLD_GOOD        = 70.0
THRESHOLD_FAIR        = 60.0
THRESHOLD_POOR        = 50.0


def classify(agent_success_pct: float) -> str:
    if agent_success_pct >= THRESHOLD_EXCELLENT:
        return "Excellent"
    elif agent_success_pct >= THRESHOLD_GOOD:
        return "Good"
    elif agent_success_pct >= THRESHOLD_FAIR:
        return "Fair"
    elif agent_success_pct >= THRESHOLD_POOR:
        return "Poor"
    return "Unacceptable"


def validate(classification: str) -> str:
    if classification in ("Excellent", "Good"):
        return "PASS"
    if classification == "Fair":
        return "CONDITIONAL PASS"
    return "FAIL"


def run_proxy_validator(yardstick_rows: list[dict]) -> dict:
    """
    Classify and validate each row from calculate_yardstick().

    Returns:
        {
            "rows":             list[dict]  — all rows with classification + validation
            "pass":             list[dict]
            "conditional_pass": list[dict]
            "fail":             list[dict]
            "counts":           {"pass": int, "conditional_pass": int, "fail": int, "total": int}
        }
    """
    rows = []
    for row in yardstick_rows:
        cls = classify(row["agent_success"])
        val = validate(cls)
        rows.append({**row, "classification": cls, "validation_status": val})

    pass_rows        = [r for r in rows if r["validation_status"] == "PASS"]
    conditional_rows = [r for r in rows if r["validation_status"] == "CONDITIONAL PASS"]
    fail_rows        = [r for r in rows if r["validation_status"] == "FAIL"]

    return {
        "rows":             rows,
        "pass":             pass_rows,
        "conditional_pass": conditional_rows,
        "fail":             fail_rows,
        "counts": {
            "pass":             len(pass_rows),
            "conditional_pass": len(conditional_rows),
            "fail":             len(fail_rows),
            "total":            len(rows),
        },
    }
