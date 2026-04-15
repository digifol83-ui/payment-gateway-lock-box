"""
Company lookup via OpenCorporates API + country-specific registry fallbacks.
Ported from companyLookup.ts.
"""
import asyncio
import httpx
from typing import Optional
from config import OPENCORPORATES_API_TOKEN

OPENCORPORATES_BASE = "https://api.opencorporates.com/v0.4"

# OpenCorporates jurisdiction codes keyed by ISO-2 country code
JURISDICTION_MAP: dict[str, str] = {
    "GB": "gb",
    "IN": "in",
    "AE": "ae",
    "SG": "sg",
    "HK": "hk",
    "AU": "au",
    "DE": "de",
    "FR": "fr",
    "NL": "nl",
    "SA": "sa",
    "ZA": "za",
    "US": "us",
    "CA": "ca",
    "PK": "pk",
    "BD": "bd",
    "MY": "my",
    "NG": "ng",
    "KE": "ke",
    "GH": "gh",
}

# Registration number format validation patterns
REG_PATTERNS: dict[str, str] = {
    "GB": r"^\d{8}$",
    "IN": r"^[A-Z0-9]{21}$",
    "SG": r"^\d{6}[A-Z]$",
    "HK": r"^\d{8}$",
    "AU": r"^\d{9}$",
    "AE": r"^\d{1,6}$",
    "US": r"^[A-Z0-9\-]{1,20}$",
}


def _headers() -> dict:
    h = {"Accept": "application/json"}
    if OPENCORPORATES_API_TOKEN:
        h["X-API-TOKEN"] = OPENCORPORATES_API_TOKEN
    return h


async def search_company(
    company_name: str,
    country_code: str,
) -> Optional[dict]:
    """Search company by name via OpenCorporates. Returns first match or None."""
    jurisdiction = JURISDICTION_MAP.get(country_code.upper())
    if not jurisdiction:
        return None

    params: dict = {"q": company_name, "jurisdiction_code": jurisdiction}
    if OPENCORPORATES_API_TOKEN:
        params["api_token"] = OPENCORPORATES_API_TOKEN

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                f"{OPENCORPORATES_BASE}/companies/search",
                params=params,
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        companies = data.get("results", {}).get("companies", [])
        if not companies:
            return None

        c = companies[0]["company"]
        return {
            "name":               c.get("name"),
            "registration_number": c.get("company_number"),
            "country":            country_code.upper(),
            "jurisdiction":       jurisdiction,
            "incorporation_date": c.get("incorporation_date"),
            "status":             c.get("current_status") or c.get("company_status"),
            "address":            c.get("registered_address_in_full"),
            "directors":          [o["officer"]["name"] for o in (c.get("officers") or [])],
            "source":             "opencorporates",
        }
    except Exception as e:
        print(f"[company_lookup] search error: {e}")
        return None


async def get_company_by_number(
    reg_number: str,
    country_code: str,
) -> Optional[dict]:
    """Fetch company directly by registration number via OpenCorporates."""
    jurisdiction = JURISDICTION_MAP.get(country_code.upper())
    if not jurisdiction:
        return None

    params = {}
    if OPENCORPORATES_API_TOKEN:
        params["api_token"] = OPENCORPORATES_API_TOKEN

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                f"{OPENCORPORATES_BASE}/companies/{jurisdiction}/{reg_number}",
                params=params,
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        c = data.get("results", {}).get("company", {})
        if not c:
            return None

        return {
            "name":               c.get("name"),
            "registration_number": c.get("company_number"),
            "country":            country_code.upper(),
            "jurisdiction":       jurisdiction,
            "incorporation_date": c.get("incorporation_date"),
            "status":             c.get("current_status") or c.get("company_status"),
            "address":            c.get("registered_address_in_full"),
            "directors":          [o["officer"]["name"] for o in (c.get("officers") or [])],
            "shareholders":       [s["shareholder"]["name"] for s in (c.get("shareholders") or [])],
            "source":             "opencorporates",
        }
    except Exception as e:
        print(f"[company_lookup] get_by_number error: {e}")
        return None


async def lookup_company_with_retry(
    company_name: str,
    country_code: str,
    reg_number: Optional[str] = None,
    max_retries: int = 3,
) -> Optional[dict]:
    """
    Try reg number first, fall back to name search.
    Retries up to max_retries with exponential backoff.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            if reg_number:
                result = await get_company_by_number(reg_number, country_code)
                if result:
                    return result
            result = await search_company(company_name, country_code)
            if result:
                return result
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5 ** attempt)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5 ** attempt)

    if last_error:
        print(f"[company_lookup] all retries exhausted: {last_error}")
    return None


def is_configured() -> dict:
    return {
        "enabled":     bool(OPENCORPORATES_API_TOKEN),
        "api_token":   f"{OPENCORPORATES_API_TOKEN[:8]}…" if OPENCORPORATES_API_TOKEN else "NOT SET",
        "jurisdictions": list(JURISDICTION_MAP.keys()),
    }
