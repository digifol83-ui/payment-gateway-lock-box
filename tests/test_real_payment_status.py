import asyncio

import real_payment_status as readiness


def test_redact_masks_provider_tokens():
    value = (
        "sk_live_abc123 apiKey=pk_live_abc123&sessionId=session_123 "
        "access-token: eyJ.secret api-secret=supersecret whsec_abc123"
    )

    redacted = readiness._redact(value)

    assert "abc123" not in redacted
    assert "session_123" not in redacted
    assert "supersecret" not in redacted
    assert "eyJ.secret" not in redacted
    assert "REDACTED" in redacted


def test_transak_readiness_reports_partner_access_rejection(monkeypatch):
    import providers.transak as transak_module

    async def fake_create_widget_url(self, payment):
        raise ValueError(
            "Transak session error: {'statusCode': 401, "
            "'message': 'Invalid or missing access-token.', 'errorCode': 1002}"
        )

    monkeypatch.setattr(readiness, "_is_production", lambda provider_id: provider_id == "transak")
    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)

    result = asyncio.run(readiness.check_transak_real_payment())

    assert result["provider_id"] == "transak"
    assert result["configured"] is True
    assert result["ready_for_real_payment"] is False
    assert result["status"] == "provider_access_rejected"
    assert "partner access" in result["detail"]


def test_transak_readiness_reports_blank_exceptions_by_type(monkeypatch):
    import providers.transak as transak_module

    async def fake_create_widget_url(self, payment):
        raise TimeoutError()

    monkeypatch.setattr(readiness, "_is_production", lambda provider_id: provider_id == "transak")
    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)

    result = asyncio.run(readiness.check_transak_real_payment())

    assert result["ready_for_real_payment"] is False
    assert result["status"] == "checkout_error"
    assert "TimeoutError" in result["detail"]


def test_real_payment_status_aggregates_ready_and_blocked_providers(monkeypatch):
    async def fake_stripe():
        return readiness._provider_result(
            "stripe",
            "fiat-only",
            configured=True,
            ready=False,
            status="api_error",
            detail="Stripe API returned 401",
        )

    async def fake_transak():
        return readiness._provider_result(
            "transak",
            "fiat-to-crypto",
            configured=True,
            ready=True,
            status="ready",
            detail="Transak session created",
        )

    async def fake_moonpay():
        return readiness._provider_result(
            "moonpay",
            "fiat-to-crypto",
            configured=False,
            ready=False,
            status="not_configured",
            detail="MoonPay production credentials are not configured",
        )

    monkeypatch.setattr(readiness, "check_stripe_real_payment", fake_stripe)
    monkeypatch.setattr(readiness, "check_transak_real_payment", fake_transak)
    monkeypatch.setattr(readiness, "check_moonpay_real_payment", fake_moonpay)

    result = asyncio.run(readiness.real_payment_status())

    assert result["ready_for_real_payment"] is True
    assert result["ready_providers"] == ["transak"]
    assert {row["provider_id"] for row in result["blockers"]} == {"stripe", "moonpay"}


def test_api_real_payment_status_uses_readiness_probe(monkeypatch):
    async def fake_report():
        return {"ready_for_real_payment": False, "checks": []}

    monkeypatch.setattr(readiness, "real_payment_status", fake_report)

    from server import api_real_payment_status

    result = asyncio.run(api_real_payment_status())

    assert result == {"ready_for_real_payment": False, "checks": []}
