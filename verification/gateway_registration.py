"""
Automated payment gateway merchant registration.
Ported from gatewayRegistration.ts.
Registers merchants with MoonPay, Transak, Simplex, Ramp Network in priority order.
Includes OTP extraction and submission logic.
"""
import re
import asyncio
import httpx
from typing import Optional

GATEWAY_PRIORITY = ["moonpay", "transak", "simplex", "ramp_network"]

# Gateway API endpoints
GATEWAY_ENDPOINTS: dict[str, dict] = {
    "moonpay": {
        "register":   "https://api.moonpay.com/v1/merchants",
        "verify_otp": "https://api.moonpay.com/v1/merchants/{id}/verify-otp",
    },
    "transak": {
        "register":   "https://api.transak.com/api/v1/merchants",
        "verify_otp": "https://api.transak.com/api/v1/merchants/{id}/verify-otp",
    },
    "simplex": {
        "register":   "https://api.simplex.com/api/v1/merchants",
        "verify_otp": "https://api.simplex.com/api/v1/merchants/{id}/verify-otp",
    },
    "ramp_network": {
        "register":   "https://api.ramp.network/v1/merchants",
        "verify_otp": "https://api.ramp.network/v1/merchants/{id}/verify-otp",
    },
}

# Field names each gateway uses for merchant ID in response
MERCHANT_ID_FIELDS: dict[str, str] = {
    "moonpay":      "id",
    "transak":      "merchantId",
    "simplex":      "merchantId",
    "ramp_network": "merchantId",
}


async def _register_with_gateway(
    gateway_name: str,
    payload: dict,
) -> dict:
    """
    POST merchant registration to a single gateway.
    Returns standardised result dict.
    """
    endpoint = GATEWAY_ENDPOINTS[gateway_name]["register"]
    id_field = MERCHANT_ID_FIELDS[gateway_name]

    body = {
        "name":               payload["company_name"],
        "email":              payload["email"],
        "country":            payload["country"],
        "website":            payload.get("website"),
        "businessType":       payload.get("business_type"),
        "registrationNumber": payload.get("registration_number"),
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(endpoint, json=body)

        data = resp.json()
        merchant_id = data.get(id_field)

        if resp.status_code in (200, 201) and merchant_id:
            return {
                "gateway":          gateway_name,
                "success":          True,
                "merchant_id":      merchant_id,
                "account_status":   data.get("status"),
                "verification_level": data.get("verificationLevel", 0),
                "requires_otp":     data.get("requiresOTP", False),
                "otp_email":        payload["email"],
                "raw_response":     data,
            }

        return {
            "gateway":  gateway_name,
            "success":  False,
            "error":    data.get("message") or data.get("error") or f"HTTP {resp.status_code}",
        }

    except httpx.ConnectError:
        return {
            "gateway": gateway_name,
            "success": False,
            "error":   "Connection refused — gateway unreachable (sandbox may be down)",
        }
    except Exception as e:
        return {
            "gateway": gateway_name,
            "success": False,
            "error":   str(e),
        }


async def register_with_all_gateways(payload: dict) -> list[dict]:
    """
    Register merchant with all gateways in priority order.
    Adds 500 ms delay between requests to avoid rate limiting.
    """
    results = []
    for gateway_name in GATEWAY_PRIORITY:
        result = await _register_with_gateway(gateway_name, payload)
        results.append(result)
        if gateway_name != GATEWAY_PRIORITY[-1]:
            await asyncio.sleep(0.5)
    return results


async def register_with_single_gateway(gateway_name: str, payload: dict) -> dict:
    if gateway_name not in GATEWAY_ENDPOINTS:
        return {"gateway": gateway_name, "success": False, "error": "Unknown gateway"}
    return await _register_with_gateway(gateway_name, payload)


# ─── OTP Handling ─────────────────────────────────────────────────────────────

OTP_PATTERNS = [
    re.compile(r"\b(\d{4,6})\b.*(?:OTP|code|verification|verify)", re.I),
    re.compile(r"(?:OTP|code|verification|verify).*\b(\d{4,6})\b", re.I),
    re.compile(r"\b(\d{6})\b"),
    re.compile(r"\b(\d{4})\b"),
]


def extract_otp_from_email(email_body: str) -> Optional[str]:
    """Extract OTP code from email body text using regex patterns."""
    for pattern in OTP_PATTERNS:
        match = pattern.search(email_body)
        if match:
            return match.group(1)
    return None


def validate_otp_format(otp: str) -> bool:
    return bool(re.match(r"^\d{4,6}$", otp.strip()))


async def submit_otp_to_gateway(
    gateway_name: str,
    merchant_id: str,
    otp: str,
) -> bool:
    """Submit OTP to a gateway for email verification."""
    endpoints = GATEWAY_ENDPOINTS.get(gateway_name, {})
    endpoint_template = endpoints.get("verify_otp")
    if not endpoint_template:
        return False

    endpoint = endpoint_template.format(id=merchant_id)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(endpoint, json={"otp": otp})
        return resp.status_code == 200 or resp.json().get("success") is True
    except Exception as e:
        print(f"[gateway_registration] OTP submit error ({gateway_name}): {e}")
        return False
