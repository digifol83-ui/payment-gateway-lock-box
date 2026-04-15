"""
Seed script: UAE SME Client List
Source: Comprehensive Project Report — UAE SME Payment Gateway Optimization

Adds 10 UAE SME companies as merchants + merchant_profiles.
Report metadata (sector, compliance, risk, agent strategy, yardstick, proxy validator)
is stored in the company_data JSON field on merchant_profiles.

Run: python3 seed_uae_clients.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import database as db
import json

UAE_SME_CLIENTS = [
    {
        "company_name":          "Little Majlis",
        "business_email":        "admin@littlemajlis.ae",
        "website":               "https://littlemajlis.ae",
        "business_type":         "Gifting / Artisan Marketplace",
        "country":               "UAE",
        "registration_number":   "AE-LM-2019-001",
        "sector":                "Gifting/Artisan",
        "compliance":            "Medium-High",
        "risk":                  "Low",
        "bottleneck":            "Manual document collection from various artisans/vendors",
        "agent_strategy":        "Implement an automated vendor onboarding portal for document submission, with AI-driven parsing and verification of vendor credentials and product compliance.",
        "baseline_success":      37.5,
        "agent_success":         86.2,
        "improvement_pct":       129.8,
        "yardstick_pct":         107.7,
        "classification":        "Excellent",
        "validation_status":     "PASS",
    },
    {
        "company_name":          "Kibsons",
        "business_email":        "admin@kibsons.com",
        "website":               "https://kibsons.com",
        "business_type":         "Fresh Produce E-commerce",
        "country":               "UAE",
        "registration_number":   "AE-KB-2015-002",
        "sector":                "Fresh Produce",
        "compliance":            "High",
        "risk":                  "Low",
        "bottleneck":            "High volume of low-value transactions requiring robust fraud detection",
        "agent_strategy":        "Deploy advanced fraud detection algorithms with ML to analyze transaction velocity, customer behaviour, and geolocation data in real-time, minimising false positives and chargebacks.",
        "baseline_success":      47.6,
        "agent_success":         74.4,
        "improvement_pct":       56.4,
        "yardstick_pct":         93.0,
        "classification":        "Good",
        "validation_status":     "PASS",
    },
    {
        "company_name":          "The Giving Movement",
        "business_email":        "admin@thegivingmovement.com",
        "website":               "https://thegivingmovement.com",
        "business_type":         "Sustainable Fashion Retail",
        "country":               "UAE",
        "registration_number":   "AE-TGM-2020-003",
        "sector":                "Sustainable Fashion",
        "compliance":            "High",
        "risk":                  "Low",
        "bottleneck":            "Global shipping and cross-border payment complexities",
        "agent_strategy":        "Utilise dynamic payment routing to select optimal payment processors based on transaction currency, country, and cost-efficiency. Automate FX rate optimisation.",
        "baseline_success":      42.1,
        "agent_success":         78.5,
        "improvement_pct":       86.2,
        "yardstick_pct":         98.1,
        "classification":        "Good",
        "validation_status":     "PASS",
    },
    {
        "company_name":          "Laundry",
        "business_email":        "admin@laundry.ae",
        "website":               "https://laundry.ae",
        "business_type":         "On-demand Laundry Service",
        "country":               "UAE",
        "registration_number":   "AE-LN-2018-004",
        "sector":                "On-demand Service",
        "compliance":            "Medium",
        "risk":                  "Low-Medium",
        "bottleneck":            "Service-based model with potential for chargebacks due to delays",
        "agent_strategy":        "Integrate with the service delivery tracking system to provide proof of service completion to the payment gateway. Automate dispute resolution workflows by providing relevant evidence.",
        "baseline_success":      25.5,
        "agent_success":         56.2,
        "improvement_pct":       120.3,
        "yardstick_pct":         70.2,
        "classification":        "Poor",
        "validation_status":     "FAIL",
    },
    {
        "company_name":          "Waj",
        "business_email":        "admin@waj.io",
        "website":               "https://waj.io",
        "business_type":         "SaaS / B2B Software",
        "country":               "UAE",
        "registration_number":   "AE-WJ-2021-005",
        "sector":                "SaaS/B2B",
        "compliance":            "High",
        "risk":                  "Low",
        "bottleneck":            "Subscription-based billing with recurring payment failures",
        "agent_strategy":        "Implement a smart dunning management system that uses AI to predict optimal retry times and methods for failed recurring payments, and communicates proactively with customers.",
        "baseline_success":      46.8,
        "agent_success":         79.8,
        "improvement_pct":       70.6,
        "yardstick_pct":         99.7,
        "classification":        "Good",
        "validation_status":     "PASS",
    },
    {
        "company_name":          "Flow48",
        "business_email":        "admin@flow48.com",
        "website":               "https://flow48.com",
        "business_type":         "Fintech / Revenue-based Financing",
        "country":               "UAE",
        "registration_number":   "AE-F48-2022-006",
        "sector":                "Fintech/Financing",
        "compliance":            "Very High",
        "risk":                  "Medium",
        "bottleneck":            "Complex regulatory compliance and KYC for SME financing",
        "agent_strategy":        "Automate the collection and verification of financial documents (bank statements, tax returns) using AI. Integrate with credit bureaus and regulatory databases for enhanced due diligence.",
        "baseline_success":      39.9,
        "agent_success":         64.9,
        "improvement_pct":       62.6,
        "yardstick_pct":         81.1,
        "classification":        "Fair",
        "validation_status":     "CONDITIONAL PASS",
    },
    {
        "company_name":          "Mobimatter",
        "business_email":        "admin@mobimatter.com",
        "website":               "https://mobimatter.com",
        "business_type":         "Digital eSIM Marketplace",
        "country":               "UAE",
        "registration_number":   "AE-MM-2020-007",
        "sector":                "Digital eSIM",
        "compliance":            "High",
        "risk":                  "Medium",
        "bottleneck":            "High risk of friendly fraud and chargebacks for digital goods",
        "agent_strategy":        "Deploy chargeback prevention tools with device fingerprinting and purchase velocity checks. Automate digital delivery proofs and integrate with card network dispute APIs.",
        "baseline_success":      33.9,
        "agent_success":         57.3,
        "improvement_pct":       69.3,
        "yardstick_pct":         71.6,
        "classification":        "Poor",
        "validation_status":     "FAIL",
    },
    {
        "company_name":          "Alpheya",
        "business_email":        "admin@alpheya.com",
        "website":               "https://alpheya.com",
        "business_type":         "Wealth Management Platform",
        "country":               "UAE",
        "registration_number":   "AE-AL-2019-008",
        "sector":                "Wealth Management",
        "compliance":            "Very High",
        "risk":                  "Medium-High",
        "bottleneck":            "Strict regulatory requirements for investor onboarding and KYC",
        "agent_strategy":        "Automate multi-tier investor KYC with Sumsub integration, ADGM/DIFC regulatory checks, and AML screening. Provide real-time onboarding status updates to advisors.",
        "baseline_success":      30.7,
        "agent_success":         50.0,
        "improvement_pct":       63.0,
        "yardstick_pct":         62.5,
        "classification":        "Poor",
        "validation_status":     "FAIL",
    },
    {
        "company_name":          "Souqalmal",
        "business_email":        "admin@souqalmal.com",
        "website":               "https://souqalmal.com",
        "business_type":         "Financial Comparison Platform",
        "country":               "UAE",
        "registration_number":   "AE-SQ-2012-009",
        "sector":                "Financial Comparison",
        "compliance":            "High",
        "risk":                  "Low-Medium",
        "bottleneck":            "Handling sensitive financial data and lead generation compliance",
        "agent_strategy":        "Implement PCI-DSS compliant data handling pipelines, automated consent management, and real-time data masking. Integrate with CBUAE data protection guidelines.",
        "baseline_success":      33.3,
        "agent_success":         57.7,
        "improvement_pct":       73.2,
        "yardstick_pct":         72.1,
        "classification":        "Poor",
        "validation_status":     "FAIL",
    },
    {
        "company_name":          "Ziina",
        "business_email":        "admin@ziina.com",
        "website":               "https://ziina.com",
        "business_type":         "P2P Fintech / Payments",
        "country":               "UAE",
        "registration_number":   "AE-ZN-2020-010",
        "sector":                "Fintech/Payments",
        "compliance":            "Very High",
        "risk":                  "Medium",
        "bottleneck":            "High scrutiny from traditional gateways due to P2P payment nature",
        "agent_strategy":        "Build a regulatory narrative package (CBUAE licence summary, AML policy docs, transaction flow diagrams) for gateway onboarding. Automate ongoing compliance reporting to partner gateways.",
        "baseline_success":      31.3,
        "agent_success":         83.6,
        "improvement_pct":       167.0,
        "yardstick_pct":         104.5,
        "classification":        "Excellent",
        "validation_status":     "PASS",
    },
]


def seed():
    db.init_db()
    print("\n─── BeastPay | UAE SME Client Seeding ───\n")

    created = 0
    skipped = 0

    for sme in UAE_SME_CLIENTS:
        # Check if merchant already exists
        with db.get_conn() as conn:
            exists = conn.execute(
                "SELECT id FROM merchants WHERE email=?", (sme["business_email"],)
            ).fetchone()

        if exists:
            print(f"  SKIP  {sme['company_name']} (already exists)")
            skipped += 1
            continue

        # 1. Create merchant account
        merchant = db.create_merchant(
            name=sme["company_name"],
            email=sme["business_email"],
            webhook_url=f"{sme['website']}/webhooks/beastpay",
        )

        # 2. Create merchant profile with full report metadata
        company_data = {
            "sector":            sme["sector"],
            "compliance":        sme["compliance"],
            "risk":              sme["risk"],
            "bottleneck":        sme["bottleneck"],
            "agent_strategy":    sme["agent_strategy"],
            "report_metrics": {
                "baseline_success_pct": sme["baseline_success"],
                "agent_success_pct":    sme["agent_success"],
                "improvement_pct":      sme["improvement_pct"],
                "yardstick_pct":        sme["yardstick_pct"],
                "classification":       sme["classification"],
                "validation_status":    sme["validation_status"],
            },
        }

        profile = db.create_merchant_profile({
            "merchant_id":         merchant["id"],
            "company_name":        sme["company_name"],
            "country":             sme["country"],
            "business_email":      sme["business_email"],
            "registration_number": sme["registration_number"],
            "business_type":       sme["business_type"],
            "website":             sme["website"],
        })

        # Store metadata in company_data field
        db.update_merchant_profile(profile["id"], {
            "company_data": json.dumps(company_data),
        })

        status_icon = {
            "PASS":             "✓",
            "CONDITIONAL PASS": "~",
            "FAIL":             "✗",
        }.get(sme["validation_status"], "?")

        print(
            f"  {status_icon}  {sme['company_name']:<22} "
            f"| {sme['sector']:<24} "
            f"| Agent: {sme['agent_success']}% "
            f"| {sme['validation_status']:<16} "
            f"| API key: {merchant['api_key']}"
        )
        created += 1

    print(f"\n─── Done: {created} created, {skipped} skipped ───\n")

    # Summary table
    print("Proxy Validator Summary:")
    print(f"{'Company':<24} {'Agent%':>7} {'Yardstick%':>11} {'Class':<12} {'Status'}")
    print("─" * 75)
    for sme in UAE_SME_CLIENTS:
        print(
            f"  {sme['company_name']:<22} "
            f"{sme['agent_success']:>6.1f}% "
            f"{sme['yardstick_pct']:>10.1f}% "
            f"  {sme['classification']:<12} "
            f"{sme['validation_status']}"
        )
    print()


if __name__ == "__main__":
    seed()
