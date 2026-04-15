"""
Sumsub KYC integration for BeastPay-OpenClaw.
Docs: https://docs.sumsub.com/reference

Flow:
  1. Customer initiates a payment > KYC_SUMSUB_LIMIT
  2. Gateway calls create_applicant() → gets applicant_id
  3. Gateway calls get_sdk_token() → gets short-lived token
  4. Customer redirected to Sumsub WebSDK URL with that token
  5. Customer completes identity verification (passport/ID + selfie)
  6. Sumsub sends webhook → applicantReviewed event
  7. KYC record updated → payment allowed to proceed

Setup:
  dashboard.sumsub.com → Developers → App tokens → create token
  Copy App Token + Secret Key
  Set SUMSUB_LEVEL_NAME to your verification flow name

Env vars:
  SUMSUB_APP_TOKEN=your_app_token
  SUMSUB_SECRET_KEY=your_secret_key
  SUMSUB_LEVEL_NAME=basic-kyc-level
"""
import hmac
import hashlib
import time
import json
import httpx
from datetime import datetime
from config import (
    SUMSUB_APP_TOKEN, SUMSUB_SECRET_KEY,
    SUMSUB_ENABLED, SUMSUB_LEVEL_NAME, BASE_URL,
)

_API_BASE = "https://api.sumsub.com"

REVIEW_RESULT_MAP = {
    "GREEN":  "approved",
    "YELLOW": "pending_review",
    "RED":    "rejected",
}


class SumsubKYC:

    def _sign(self, method: str, path: str, body: bytes = b"") -> dict:
        """Generate Sumsub HMAC-SHA256 request signature headers."""
        ts = str(int(time.time()))
        payload = ts.encode() + method.upper().encode() + path.encode() + body
        sig = hmac.new(
            SUMSUB_SECRET_KEY.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return {
            "X-App-Token":      SUMSUB_APP_TOKEN,
            "X-App-Access-Sig": sig,
            "X-App-Access-Ts":  ts,
            "Content-Type":     "application/json",
        }

    async def create_applicant(self, external_user_id: str, email: str = None) -> dict:
        """
        Create a Sumsub applicant for a customer.
        external_user_id: your internal ID (e.g. payment_id or customer email)
        Returns: {applicant_id, ...}
        """
        path = f"/resources/applicants?levelName={SUMSUB_LEVEL_NAME}"
        body_data = {"externalUserId": external_user_id}
        if email:
            body_data["email"] = email
        body = json.dumps(body_data).encode()
        headers = self._sign("POST", path, body)

        async with httpx.AsyncClient(timeout=15, base_url=_API_BASE) as client:
            resp = await client.post(path, content=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {
                "applicant_id":    data["id"],
                "external_user_id": data.get("externalUserId"),
                "status":          "created",
                "review_status":   data.get("review", {}).get("reviewStatus"),
            }

    async def get_sdk_token(self, applicant_id: str) -> str:
        """
        Get a short-lived WebSDK access token for the customer to complete KYC.
        Token expires in ~10 minutes.
        """
        path = f"/resources/accessTokens?userId={applicant_id}&levelName={SUMSUB_LEVEL_NAME}"
        headers = self._sign("POST", path)
        async with httpx.AsyncClient(timeout=15, base_url=_API_BASE) as client:
            resp = await client.post(path, headers=headers)
            resp.raise_for_status()
            return resp.json().get("token", "")

    def get_websdk_url(self, sdk_token: str) -> str:
        """Build the Sumsub WebSDK URL for customer redirect."""
        return (
            f"https://in.sumsub.com/websdk/p/basic-kyc?"
            f"access_token={sdk_token}"
            f"&lang=en"
        )

    async def get_applicant_status(self, applicant_id: str) -> dict:
        """Check current KYC review status of an applicant."""
        path = f"/resources/applicants/{applicant_id}/requiredIdDocsStatus"
        headers = self._sign("GET", path)
        async with httpx.AsyncClient(timeout=10, base_url=_API_BASE) as client:
            resp = await client.get(path, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_applicant_review(self, applicant_id: str) -> dict:
        """Get final review result for an applicant."""
        path = f"/resources/applicants/{applicant_id}/one"
        headers = self._sign("GET", path)
        async with httpx.AsyncClient(timeout=10, base_url=_API_BASE) as client:
            resp = await client.get(path, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            review = data.get("review", {})
            answer = review.get("reviewResult", {}).get("reviewAnswer", "")
            return {
                "applicant_id":  applicant_id,
                "kyc_status":    REVIEW_RESULT_MAP.get(answer, "pending"),
                "review_status": review.get("reviewStatus"),
                "review_answer": answer,
                "reject_labels": review.get("reviewResult", {}).get("rejectLabels", []),
            }

    def verify_webhook(self, raw_body: bytes, digest: str) -> bool:
        """Verify Sumsub webhook HMAC-SHA256 digest."""
        if not SUMSUB_SECRET_KEY:
            return True
        computed = hmac.new(
            SUMSUB_SECRET_KEY.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, digest)

    def parse_webhook(self, payload: dict) -> dict | None:
        """
        Parse Sumsub webhook into internal KYC update.
        Key events: applicantReviewed, applicantPending, applicantOnHold
        """
        event = payload.get("type", "")
        applicant = payload.get("applicantId", "")
        ext_id    = payload.get("externalUserId", "")
        review    = payload.get("reviewResult", {})
        answer    = review.get("reviewAnswer", "")

        kyc_status_map = {
            "applicantReviewed":    REVIEW_RESULT_MAP.get(answer, "pending"),
            "applicantPending":     "pending",
            "applicantOnHold":      "on_hold",
            "applicantPersonalInfoChanged": "pending",
        }

        return {
            "event":          event,
            "applicant_id":   applicant,
            "external_user_id": ext_id,
            "kyc_status":     kyc_status_map.get(event, "pending"),
            "review_answer":  answer,
            "reject_labels":  review.get("rejectLabels", []),
        }

    def is_configured(self) -> dict:
        return {
            "enabled":     SUMSUB_ENABLED,
            "app_token":   f"{SUMSUB_APP_TOKEN[:8]}…" if SUMSUB_APP_TOKEN else "NOT SET",
            "level_name":  SUMSUB_LEVEL_NAME,
            "kyc_trigger": f">${500} USD",
        }
