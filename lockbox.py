"""
Lockbox — AI-powered payment field parser + card validator
Python port of the TypeScript Lockbox backend.

Uses Claude AI to extract card data from unstructured text,
then validates each field independently.
"""
import re
import json
import httpx
from datetime import datetime
from typing import Optional
from config import ANTHROPIC_API_KEY


# ─── Luhn Algorithm ──────────────────────────────────────────────────────────

def _luhn_check(number: str) -> bool:
    """Return True if number passes the Luhn checksum."""
    total = 0
    reverse = number[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_card_number(card_number: str) -> dict:
    cleaned = re.sub(r"[\s\-]", "", card_number)
    if not cleaned.isdigit():
        return {"isValid": False, "errors": ["Card number must contain only digits"]}
    if not (13 <= len(cleaned) <= 19):
        return {"isValid": False, "errors": [f"Card number must be 13-19 digits (got {len(cleaned)})"]}
    if not _luhn_check(cleaned):
        return {"isValid": False, "errors": ["Card number failed Luhn validation"]}
    return {"isValid": True, "errors": []}


def validate_expiry_date(expiry: str) -> dict:
    m = re.match(r"^(\d{2})/(\d{2})$", expiry.strip())
    if not m:
        return {"isValid": False, "errors": ["Expiry date must be in MM/YY format"]}
    month, year = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12):
        return {"isValid": False, "errors": [f"Invalid month: {month} (must be 01-12)"]}
    now = datetime.utcnow()
    current_year = now.year % 100
    current_month = now.month
    if year < current_year:
        return {"isValid": False, "errors": [f"Card expired (year {year} is in the past)"]}
    if year == current_year and month < current_month:
        return {"isValid": False, "errors": [f"Card expired ({month:02d}/{year} is in the past)"]}
    return {"isValid": True, "errors": []}


def validate_cvv(cvv: str) -> dict:
    cleaned = cvv.strip().replace(" ", "")
    if not cleaned.isdigit():
        return {"isValid": False, "errors": ["CVV must contain only digits"]}
    if not (3 <= len(cleaned) <= 4):
        return {"isValid": False, "errors": [f"CVV must be 3-4 digits (got {len(cleaned)})"]}
    return {"isValid": True, "errors": []}


def validate_cardholder_name(name: str) -> dict:
    trimmed = name.strip()
    if not trimmed:
        return {"isValid": False, "errors": ["Cardholder name is required"]}
    parts = [p for p in trimmed.split() if p]
    if len(parts) < 2:
        return {"isValid": False, "errors": ["Cardholder name must include at least first and last name"]}
    if not re.match(r"^[a-zA-Z\s\-']+$", trimmed):
        return {"isValid": False, "errors": ["Cardholder name contains invalid characters"]}
    return {"isValid": True, "errors": []}


def validate_address_field(field: str, value: str) -> dict:
    trimmed = value.strip()
    if not trimmed:
        return {"isValid": False, "errors": [f"{field} is required"]}
    if len(trimmed) < 2:
        return {"isValid": False, "errors": [f"{field} is too short (minimum 2 characters)"]}
    if len(trimmed) > 100:
        return {"isValid": False, "errors": [f"{field} is too long (maximum 100 characters)"]}
    return {"isValid": True, "errors": []}


def validate_card_data(data: dict) -> dict:
    """Comprehensive validation. Returns CardValidationResults-shaped dict."""
    cn = validate_card_number(data.get("cardNumber", ""))
    ex = validate_expiry_date(data.get("expiryDate", ""))
    cv = validate_cvv(data.get("cvv", ""))
    nm = validate_cardholder_name(data.get("cardholderName", ""))
    addr = data.get("billingAddress", {})
    ba = {
        "street":  validate_address_field("Street",   addr.get("street", "")),
        "city":    validate_address_field("City",     addr.get("city", "")),
        "state":   validate_address_field("State",    addr.get("state", "")),
        "zipCode": validate_address_field("Zip Code", addr.get("zipCode", "")),
        "country": validate_address_field("Country",  addr.get("country", "")),
    }
    all_valid = (
        cn["isValid"] and ex["isValid"] and cv["isValid"] and nm["isValid"]
        and all(v["isValid"] for v in ba.values())
    )
    all_errors = (
        cn["errors"] + ex["errors"] + cv["errors"] + nm["errors"]
        + [e for v in ba.values() for e in v["errors"]]
    )
    return {
        "cardNumber":     cn,
        "expiryDate":     ex,
        "cvv":            cv,
        "cardholderName": nm,
        "billingAddress": ba,
        "overall":        {"isValid": all_valid, "errors": all_errors},
    }


def mask_card_number(card_number: str) -> str:
    cleaned = re.sub(r"[\s\-]", "", card_number)
    if len(cleaned) < 4:
        return "*" * len(cleaned)
    last4 = cleaned[-4:]
    masked = "*" * (len(cleaned) - 4)
    parts = [masked[i:i+4] for i in range(0, len(masked), 4)]
    parts.append(last4)
    return " ".join(parts)


# ─── Claude AI Parser ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert payment data parser. Extract payment information from raw, unstructured input strings.

Extract:
- Card Number (16 digits, may be formatted with spaces or dashes)
- Expiry Date (MM/YY format)
- CVV (3-4 digits)
- Cardholder Name
- Billing Address (street, city, state, zip code, country)

Return ONLY a JSON object with this exact structure:
{
  "cardNumber": "digits only no spaces",
  "expiryDate": "MM/YY",
  "cvv": "3-4 digits",
  "cardholderName": "full name",
  "billingAddress": {
    "street": "street address",
    "city": "city",
    "state": "state/province",
    "zipCode": "postal code",
    "country": "country"
  },
  "confidence": {
    "cardNumber": 0.95,
    "expiryDate": 0.90,
    "cvv": 0.85,
    "cardholderName": 0.98,
    "billingAddress": 0.88
  },
  "anomalies": ["list of suspicious patterns or missing data"]
}

Confidence scores: 0.0–1.0 reflecting certainty of each extraction.
If a field is missing or unclear, set confidence to 0 and add to anomalies.
Be strict — flag anything suspicious."""

USER_TEMPLATE = "Parse this payment input and extract all fields:\n\n{raw_input}"


async def parse_payment_input(raw_input: str) -> dict:
    """
    Call Claude AI to extract structured payment data from unstructured text.
    Returns ParsedPaymentData-shaped dict with confidence scores and anomalies.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    payload = {
        "model": "claude-opus-4-6",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": USER_TEMPLATE.format(raw_input=raw_input)}
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )

    if not resp.is_success:
        raise RuntimeError(f"Claude API error {resp.status_code}: {resp.text}")

    data = resp.json()
    # Extract text from response
    content_blocks = data.get("content", [])
    text = ""
    for block in content_blocks:
        if block.get("type") == "text":
            text += block.get("text", "")

    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    parsed = json.loads(text.strip())

    # Add reasoning summary
    conf = parsed.get("confidence", {})
    parsed["rawAiReasoning"] = (
        f"Parsed via Claude AI — confidence: "
        f"Card {conf.get('cardNumber', 0):.0%}, "
        f"Expiry {conf.get('expiryDate', 0):.0%}, "
        f"CVV {conf.get('cvv', 0):.0%}, "
        f"Name {conf.get('cardholderName', 0):.0%}, "
        f"Address {conf.get('billingAddress', 0):.0%}"
    )
    return parsed


async def test_claude_connection() -> bool:
    """Return True if Claude API is reachable with the configured key."""
    if not ANTHROPIC_API_KEY:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Reply: connected"}],
                },
            )
        return resp.is_success
    except Exception:
        return False
