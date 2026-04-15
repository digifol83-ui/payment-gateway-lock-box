"""
uae_sme.data
============
Master dataset: 10 UAE SME company profiles, baseline benchmarks,
and fixed report constants.

Source: Master Project Summary & Technical Specification —
        UAE SME Payment Gateway Optimization
"""

# ── Baseline benchmarks (min, max) per verification stage ─────────────────────
BASELINE_BENCHMARKS: dict[str, tuple[float, float]] = {
    "Initial Company Lookup":   (0.85, 0.95),
    "AI Document Parsing":      (0.70, 0.80),
    "Gateway Registration":     (0.60, 0.75),
    "Final Transaction (Live)": (0.70, 0.85),
}

# ── Yardstick target (80 %) ────────────────────────────────────────────────────
YARDSTICK_TARGET: float = 0.80

# ── Proxy validator thresholds ────────────────────────────────────────────────
THRESHOLDS = {
    "Excellent":   0.80,
    "Good":        0.70,
    "Fair":        0.60,
    "Poor":        0.50,
    # below 0.50 → "Unacceptable"
}

# ── 10 UAE SME company profiles ───────────────────────────────────────────────
SME_COMPANIES: list[dict] = [
    {
        "name":             "Little Majlis",
        "sector":           "Gifting/Artisan",
        "compliance":       "Medium-High",
        "risk":             "Low",
        "bottleneck":       "Manual document collection from various artisans/vendors",
        "agent_strategy":   (
            "Implement an automated vendor onboarding portal for document submission, "
            "with AI-driven parsing and verification of vendor credentials and product compliance."
        ),
        # Fixed report values (used when deterministic output is needed)
        "report": {
            "baseline_success": 37.5,
            "agent_success":    86.2,
            "improvement_pct":  129.8,
            "yardstick_pct":    107.7,
            "classification":   "Excellent",
            "validation":       "PASS",
        },
    },
    {
        "name":             "Kibsons",
        "sector":           "Fresh Produce",
        "compliance":       "High",
        "risk":             "Low",
        "bottleneck":       "High volume of low-value transactions requiring robust fraud detection",
        "agent_strategy":   (
            "Deploy advanced fraud detection algorithms with ML to analyse transaction "
            "velocity, customer behaviour, and geolocation data in real-time, "
            "minimising false positives and chargebacks."
        ),
        "report": {
            "baseline_success": 47.6,
            "agent_success":    74.4,
            "improvement_pct":  56.4,
            "yardstick_pct":    93.0,
            "classification":   "Good",
            "validation":       "PASS",
        },
    },
    {
        "name":             "The Giving Movement",
        "sector":           "Sustainable Fashion",
        "compliance":       "High",
        "risk":             "Low",
        "bottleneck":       "Global shipping and cross-border payment complexities",
        "agent_strategy":   (
            "Utilise dynamic payment routing to select optimal payment processors based on "
            "transaction currency, country, and cost-efficiency. Automate FX rate optimisation."
        ),
        "report": {
            "baseline_success": 42.1,
            "agent_success":    78.5,
            "improvement_pct":  86.2,
            "yardstick_pct":    98.1,
            "classification":   "Good",
            "validation":       "PASS",
        },
    },
    {
        "name":             "Laundry",
        "sector":           "On-demand Service",
        "compliance":       "Medium",
        "risk":             "Low-Medium",
        "bottleneck":       "Service-based model with potential for chargebacks due to delays",
        "agent_strategy":   (
            "Integrate with the service delivery tracking system to provide proof of service "
            "completion to the payment gateway. Automate dispute resolution workflows by "
            "providing relevant evidence."
        ),
        "report": {
            "baseline_success": 25.5,
            "agent_success":    56.2,
            "improvement_pct":  120.3,
            "yardstick_pct":    70.2,
            "classification":   "Poor",
            "validation":       "FAIL",
        },
    },
    {
        "name":             "Waj",
        "sector":           "SaaS/B2B",
        "compliance":       "High",
        "risk":             "Low",
        "bottleneck":       "Subscription-based billing with recurring payment failures",
        "agent_strategy":   (
            "Implement a smart dunning management system that uses AI to predict optimal "
            "retry times and methods for failed recurring payments, and communicates "
            "proactively with customers."
        ),
        "report": {
            "baseline_success": 46.8,
            "agent_success":    79.8,
            "improvement_pct":  70.6,
            "yardstick_pct":    99.7,
            "classification":   "Good",
            "validation":       "PASS",
        },
    },
    {
        "name":             "Flow48",
        "sector":           "Fintech/Financing",
        "compliance":       "Very High",
        "risk":             "Medium",
        "bottleneck":       "Complex regulatory compliance and KYC for SME financing",
        "agent_strategy":   (
            "Automate the collection and verification of financial documents (bank statements, "
            "tax returns) using AI. Integrate with credit bureaus and regulatory databases "
            "for enhanced due diligence."
        ),
        "report": {
            "baseline_success": 39.9,
            "agent_success":    64.9,
            "improvement_pct":  62.6,
            "yardstick_pct":    81.1,
            "classification":   "Fair",
            "validation":       "CONDITIONAL PASS",
        },
    },
    {
        "name":             "Mobimatter",
        "sector":           "Digital eSIM",
        "compliance":       "High",
        "risk":             "Medium",
        "bottleneck":       "High risk of friendly fraud and chargebacks for digital goods",
        "agent_strategy":   (
            "Deploy chargeback prevention tools with device fingerprinting and purchase "
            "velocity checks. Automate digital delivery proofs and integrate with card "
            "network dispute APIs."
        ),
        "report": {
            "baseline_success": 33.9,
            "agent_success":    57.3,
            "improvement_pct":  69.3,
            "yardstick_pct":    71.6,
            "classification":   "Poor",
            "validation":       "FAIL",
        },
    },
    {
        "name":             "Alpheya",
        "sector":           "Wealth Management",
        "compliance":       "Very High",
        "risk":             "Medium-High",
        "bottleneck":       "Strict regulatory requirements for investor onboarding and KYC",
        "agent_strategy":   (
            "Automate multi-tier investor KYC with Sumsub integration, ADGM/DIFC regulatory "
            "checks, and AML screening. Provide real-time onboarding status updates to advisors."
        ),
        "report": {
            "baseline_success": 30.7,
            "agent_success":    50.0,
            "improvement_pct":  63.0,
            "yardstick_pct":    62.5,
            "classification":   "Poor",
            "validation":       "FAIL",
        },
    },
    {
        "name":             "Souqalmal",
        "sector":           "Financial Comparison",
        "compliance":       "High",
        "risk":             "Low-Medium",
        "bottleneck":       "Handling sensitive financial data and lead generation compliance",
        "agent_strategy":   (
            "Implement PCI-DSS compliant data handling pipelines, automated consent management, "
            "and real-time data masking. Integrate with CBUAE data protection guidelines."
        ),
        "report": {
            "baseline_success": 33.3,
            "agent_success":    57.7,
            "improvement_pct":  73.2,
            "yardstick_pct":    72.1,
            "classification":   "Poor",
            "validation":       "FAIL",
        },
    },
    {
        "name":             "Ziina",
        "sector":           "Fintech/Payments",
        "compliance":       "Very High",
        "risk":             "Medium",
        "bottleneck":       "High scrutiny from traditional gateways due to P2P payment nature",
        "agent_strategy":   (
            "Build a regulatory narrative package (CBUAE licence summary, AML policy docs, "
            "transaction flow diagrams) for gateway onboarding. Automate ongoing compliance "
            "reporting to partner gateways."
        ),
        "report": {
            "baseline_success": 31.3,
            "agent_success":    83.6,
            "improvement_pct":  167.0,
            "yardstick_pct":    104.5,
            "classification":   "Excellent",
            "validation":       "PASS",
        },
    },
]
