"""
Module 3 — Automated Payment Gateway Merchant Verification
Ported from TypeScript to Python for BeastPay/OpenClaw.

Components:
  company_lookup        — OpenCorporates API + country registry search
  document_parser       — Claude AI document extraction
  gateway_registration  — Auto-register with MoonPay/Transak/Simplex/Ramp
  encryption            — AES-256-GCM credential storage
  email_monitor         — OTP auto-extraction from verification emails
"""
