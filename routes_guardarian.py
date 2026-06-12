"""Guardarian OTP gates: admin OTP for order creation + customer OTP gate
before redirecting to the Guardarian-hosted checkout URL.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr

from database.migrations import AsyncDB
from verification import otp_guardarian as otp
from verification.otp_mailer import deliver_otp
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/guardarian", tags=["guardarian"])


def _get_db():
    # Local resolver to avoid a hard import cycle with server.py
    from server import db_instance
    return db_instance


# ─── Schemas ───────────────────────────────────────────────────────────────

class AdminOtpRequest(BaseModel):
    pass  # no body needed; recipient comes from settings


class AdminOtpVerify(BaseModel):
    code: str


class CustomerOtpRequest(BaseModel):
    payment_id: str


class CustomerOtpVerify(BaseModel):
    payment_id: str
    code: str


# ─── Admin OTP (gates order creation) ──────────────────────────────────────

def _admin_recipient() -> str:
    return (
        getattr(settings, "GUARDARIAN_OTP_RECIPIENT", "")
        or "sichermayorfx@gmail.com"
    )


def _admin_subject() -> str:
    # Bind the OTP to the admin API key so different keys can't share OTPs
    return (settings.ADMIN_API_KEY or "anonymous_admin")[:64]


@router.post("/otp/admin/request")
async def admin_otp_request(
    _: AdminOtpRequest = AdminOtpRequest(),
    x_api_key: str = Header(...),
):
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    db = _get_db()
    recipient = _admin_recipient()
    code = await otp.issue(db, "guardarian_create", _admin_subject(), recipient)
    delivery = await deliver_otp(recipient, code, "Guardarian order creation")
    return {
        "status": "sent",
        "recipient": recipient,
        "delivery": delivery,
        "expires_in_seconds": otp.OTP_TTL_SECONDS,
    }


@router.post("/otp/admin/verify")
async def admin_otp_verify(
    body: AdminOtpVerify,
    x_api_key: str = Header(...),
):
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    db = _get_db()
    bearer = await otp.verify(db, "guardarian_create", _admin_subject(), body.code)
    if not bearer:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    return {
        "status": "ok",
        "otp_token": bearer,
        "expires_in_seconds": otp.BEARER_TTL_SECONDS,
        "use": "Pass as 'otp_token' field on Guardarian /api/checkout/initiate-comprehensive request",
    }


# ─── Customer OTP (gates redirect to Guardarian checkout) ──────────────────

async def _payment_record(db: AsyncDB, payment_id: str) -> dict:
    row = await db.fetchone(
        "SELECT id, customer_email, provider, status FROM payments WHERE id = ?",
        (payment_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    if (row.get("provider") or "").lower() != "guardarian":
        raise HTTPException(status_code=400, detail="Payment is not a Guardarian order")
    return row


async def _redirect_target(db: AsyncDB, payment_id: str) -> Optional[str]:
    row = await db.fetchone(
        "SELECT target_url FROM guardarian_redirects WHERE payment_id = ?",
        (payment_id,),
    )
    return row["target_url"] if row else None


@router.post("/otp/customer/request")
async def customer_otp_request(body: CustomerOtpRequest):
    db = _get_db()
    pay = await _payment_record(db, body.payment_id)
    recipient = pay.get("customer_email")
    if not recipient:
        raise HTTPException(status_code=400, detail="Payment has no customer_email")
    code = await otp.issue(db, "guardarian_redirect", body.payment_id, recipient)
    delivery = await deliver_otp(recipient, code, f"Payment {body.payment_id[:8]}")
    return {
        "status": "sent",
        "recipient_masked": _mask_email(recipient),
        "delivery": {"smtp": delivery["smtp"], "telegram": delivery["telegram"]},
        "expires_in_seconds": otp.OTP_TTL_SECONDS,
    }


@router.post("/otp/customer/verify")
async def customer_otp_verify(body: CustomerOtpVerify):
    db = _get_db()
    await _payment_record(db, body.payment_id)
    bearer = await otp.verify(db, "guardarian_redirect", body.payment_id, body.code)
    if not bearer:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    target = await _redirect_target(db, body.payment_id)
    if not target:
        raise HTTPException(status_code=409, detail="No Guardarian checkout URL cached for this payment")
    return {
        "status": "ok",
        "redirect_url": target,
        "otp_token": bearer,
        "expires_in_seconds": otp.BEARER_TTL_SECONDS,
    }


# ─── Browser-friendly OTP gate page ────────────────────────────────────────

_GATE_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>BeastPay · Guardarian Verification</title>
<style>
body{font-family:system-ui,sans-serif;background:#0c0c0e;color:#eee;display:flex;
     align-items:center;justify-content:center;height:100vh;margin:0}
.card{background:#17171b;padding:32px;border-radius:12px;width:380px;box-shadow:0 8px 32px rgba(0,0,0,.4)}
h1{font-size:20px;margin:0 0 8px}p{color:#9aa;font-size:14px;margin:0 0 18px}
input{width:100%;padding:12px;font-size:18px;letter-spacing:6px;text-align:center;
      background:#0c0c0e;border:1px solid #2a2a30;color:#fff;border-radius:8px;box-sizing:border-box}
button{margin-top:14px;width:100%;padding:12px;background:#5b8def;color:#fff;border:0;
       border-radius:8px;font-size:15px;cursor:pointer}
button.secondary{background:#2a2a30}
.error{color:#ff6363;font-size:13px;margin-top:10px;min-height:18px}
.ok{color:#5fd07b}
</style></head><body><div class="card">
<h1>Verify to continue</h1>
<p>We sent a 6-digit code to <b>__RECIPIENT__</b>. Enter it to proceed to Guardarian checkout.</p>
<input id="code" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" placeholder="000000">
<button id="verify">Verify &amp; continue</button>
<button id="resend" class="secondary">Resend code</button>
<div class="error" id="msg"></div></div>
<script>
const PID="__PAYMENT_ID__";
const msg=document.getElementById("msg");
async function post(url,body){
 const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 return [r.status, await r.json().catch(()=>({}))];
}
document.getElementById("verify").onclick=async()=>{
 msg.textContent="";msg.className="error";
 const code=document.getElementById("code").value.trim();
 if(!/^\\d{6}$/.test(code)){msg.textContent="Enter the 6-digit code.";return;}
 const [st,data]=await post("/v1/guardarian/otp/customer/verify",{payment_id:PID,code});
 if(st===200&&data.redirect_url){msg.className="error ok";msg.textContent="Verified. Redirecting…";location.href=data.redirect_url;}
 else{msg.textContent=data.detail||"Verification failed.";}
};
document.getElementById("resend").onclick=async()=>{
 msg.textContent="Sending…";
 const [st,data]=await post("/v1/guardarian/otp/customer/request",{payment_id:PID});
 msg.textContent=st===200?"New code sent.":data.detail||"Resend failed.";
};
</script></body></html>
"""


def _mask_email(addr: str) -> str:
    try:
        user, dom = addr.split("@", 1)
        if len(user) <= 2:
            return "*" * len(user) + "@" + dom
        return user[0] + "*" * (len(user) - 2) + user[-1] + "@" + dom
    except Exception:
        return "***"


@router.get("/gate/{payment_id}", response_class=HTMLResponse)
async def gate_page(payment_id: str):
    db = _get_db()
    pay = await _payment_record(db, payment_id)
    target = await _redirect_target(db, payment_id)
    if not target:
        raise HTTPException(status_code=409, detail="Guardarian checkout URL not ready for this payment")
    recipient = _mask_email(pay.get("customer_email") or "")
    # Issue an OTP automatically on first hit so the form is usable immediately
    code = await otp.issue(db, "guardarian_redirect", payment_id, pay["customer_email"])
    await deliver_otp(pay["customer_email"], code, f"Payment {payment_id[:8]}")
    html = _GATE_HTML.replace("__RECIPIENT__", recipient).replace("__PAYMENT_ID__", payment_id)
    return HTMLResponse(content=html)
