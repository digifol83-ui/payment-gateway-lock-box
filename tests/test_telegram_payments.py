import asyncio

import telegram_payments as tg


def test_create_stars_invoice_link_uses_empty_provider_token(monkeypatch):
    captured = {}

    async def fake_post(method, payload=None):
        captured["method"] = method
        captured["payload"] = payload
        return {"ok": True, "result": "https://t.me/invoice/test"}

    monkeypatch.setattr(tg, "_telegram_post", fake_post)

    link = asyncio.run(tg.create_invoice_link(
        title="BeastPay Stars",
        description="Readiness",
        payload="beastpay:payment_123",
        amount=1,
        currency="XTR",
    ))

    assert link == "https://t.me/invoice/test"
    assert captured["method"] == "createInvoiceLink"
    assert captured["payload"]["currency"] == "XTR"
    assert captured["payload"]["prices"] == [{"label": "BeastPay Stars", "amount": 1}]
    assert captured["payload"]["provider_token"] == ""


def test_create_fiat_invoice_link_uses_telegram_provider_token(monkeypatch):
    captured = {}

    async def fake_post(method, payload=None):
        captured["payload"] = payload
        return {"ok": True, "result": "https://t.me/invoice/fiat"}

    monkeypatch.setattr(tg, "_telegram_post", fake_post)
    monkeypatch.setattr(tg.config, "TELEGRAM_PAYMENT_PROVIDER_TOKEN", "provider_token_value")
    monkeypatch.setattr(tg.config, "STRIPE_PROVIDER_TOKEN", "")

    asyncio.run(tg.create_invoice_link(
        title="BeastPay Gateway",
        description="Readiness",
        payload="beastpay:payment_123",
        amount=1.23,
        currency="USD",
    ))

    assert captured["payload"]["prices"] == [{"label": "BeastPay Gateway", "amount": 123}]
    assert captured["payload"]["provider_token"] == "provider_token_value"


def test_telegram_gateway_status_verifies_stars_invoice(monkeypatch):
    async def fake_get(method):
        if method == "getMe":
            return {"ok": True, "result": {"username": "beastpay_bot"}}
        if method == "getWebhookInfo":
            return {"ok": True, "result": {"url": "https://example.test/telegram/incoming", "pending_update_count": 0}}
        raise AssertionError(method)

    async def fake_create_invoice_link(**kwargs):
        return "https://t.me/invoice/test"

    monkeypatch.setattr(tg.config, "TELEGRAM_ENABLED", True)
    monkeypatch.setattr(tg.config, "TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(tg.config, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(tg.config, "TELEGRAM_WEBHOOK_SECRET", "secret-value")
    monkeypatch.setattr(tg.config, "TELEGRAM_PAYMENT_PROVIDER_TOKEN", "")
    monkeypatch.setattr(tg.config, "STRIPE_PROVIDER_TOKEN", "")
    monkeypatch.setattr(tg, "_telegram_get", fake_get)
    monkeypatch.setattr(tg, "create_invoice_link", fake_create_invoice_link)

    result = asyncio.run(tg.telegram_gateway_status(probe_invoice=True))

    assert result["provider_id"] == "telegram"
    assert result["ready_for_real_payment"] is True
    assert result["evidence"]["invoice_modes_verified"] == ["telegram_stars"]
    assert result["evidence"]["webhook_url_configured"] is True
    assert result["evidence"]["webhook_secret_present"] is True


def test_telegram_gateway_status_without_invoice_probe_reports_bot_reachable(monkeypatch):
    async def fake_get(method):
        if method == "getMe":
            return {"ok": True, "result": {"username": "beastpay_bot"}}
        if method == "getWebhookInfo":
            return {"ok": True, "result": {"url": "", "pending_update_count": 0}}
        raise AssertionError(method)

    async def fail_create_invoice_link(**kwargs):
        raise AssertionError("invoice probe should not run")

    monkeypatch.setattr(tg.config, "TELEGRAM_ENABLED", True)
    monkeypatch.setattr(tg.config, "TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(tg.config, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(tg.config, "TELEGRAM_PAYMENT_PROVIDER_TOKEN", "")
    monkeypatch.setattr(tg.config, "STRIPE_PROVIDER_TOKEN", "")
    monkeypatch.setattr(tg, "_telegram_get", fake_get)
    monkeypatch.setattr(tg, "create_invoice_link", fail_create_invoice_link)

    result = asyncio.run(tg.telegram_gateway_status(probe_invoice=False))

    assert result["ready_for_real_payment"] is False
    assert result["status"] == "bot_reachable"
    assert result["detail"] == "Telegram bot is reachable; invoice probe was not requested."
    assert result["evidence"]["invoice_modes_verified"] == []


def test_telegram_get_retries_transient_timeout(monkeypatch):
    attempts = []

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"ok": True, "result": {"username": "beastpay_bot"}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            attempts.append(url)
            if len(attempts) == 1:
                raise tg.httpx.ConnectTimeout("connect timed out")
            return FakeResponse()

    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(tg.config, "TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(tg.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(tg.asyncio, "sleep", fake_sleep)

    result = asyncio.run(tg._telegram_get("getMe"))

    assert result["ok"] is True
    assert len(attempts) == 2


def test_telegram_webhook_secret_validation():
    assert tg.telegram_webhook_secret_valid("", None) is True
    assert tg.telegram_webhook_secret_valid("secret-value", "secret-value") is True
    assert tg.telegram_webhook_secret_valid("secret-value", "wrong-value") is False
    assert tg.telegram_webhook_secret_valid("secret-value", None) is False


def test_non_stripe_gateway_status_excludes_stripe_and_transak(monkeypatch):
    async def fake_telegram(probe_invoice=True):
        return tg._result("telegram", "telegram-payments", configured=True, ready=True, status="ready", detail="ok")

    async def fake_direct_wallet():
        return tg._result("direct_wallet", "crypto-direct", configured=True, ready=True, status="ready", detail="ok")

    async def fake_nowpayments():
        return tg._result("nowpayments", "crypto-invoice", configured=False, ready=False, status="not_configured", detail="missing")

    async def fake_coinremitter():
        return tg._result("coinremitter", "crypto-invoice", configured=False, ready=False, status="not_configured", detail="missing")

    monkeypatch.setattr(tg, "telegram_gateway_status", fake_telegram)
    monkeypatch.setattr(tg, "_direct_wallet_status", fake_direct_wallet)
    monkeypatch.setattr(tg, "_nowpayments_status", fake_nowpayments)
    monkeypatch.setattr(tg, "_coinremitter_status", fake_coinremitter)
    monkeypatch.setattr(tg, "_guardarian_status", lambda: tg._result("guardarian", "fiat-to-crypto", configured=False, ready=False, status="not_configured", detail="missing"))
    monkeypatch.setattr(tg, "_plisio_status", lambda: tg._result("plisio", "crypto-invoice", configured=False, ready=False, status="not_configured", detail="missing"))

    result = asyncio.run(tg.non_stripe_gateway_status())

    assert result["excluded"] == ["stripe", "transak"]
    assert "telegram" in result["ready_providers"]
    assert "direct_wallet" in result["ready_providers"]
    assert all(row["provider_id"] not in {"stripe", "transak"} for row in result["checks"])


def test_handle_telegram_pre_checkout_query_answers(monkeypatch):
    calls = []

    async def fake_post(method, payload=None):
        calls.append((method, payload))
        return {"ok": True, "result": True}

    monkeypatch.setattr(tg, "_telegram_post", fake_post)

    update = {
        "pre_checkout_query": {
            "id": "pre_123",
            "invoice_payload": "beastpay:payment_123",
        }
    }
    result = asyncio.run(tg.handle_telegram_payment_update(update, db=None))

    assert result == {"handled": True, "type": "pre_checkout_query", "accepted": True}
    assert calls == [("answerPreCheckoutQuery", {"pre_checkout_query_id": "pre_123", "ok": True})]


def test_handle_successful_payment_updates_database(monkeypatch):
    class DummyDB:
        def __init__(self):
            self.calls = []

        async def execute(self, query, params):
            self.calls.append((query, params))

    db = DummyDB()
    update = {
        "message": {
            "successful_payment": {
                "invoice_payload": "beastpay:payment_123",
                "currency": "XTR",
                "total_amount": 1,
                "telegram_payment_charge_id": "tg_charge_123",
                "provider_payment_charge_id": "provider_charge_123",
            }
        }
    }

    result = asyncio.run(tg.handle_telegram_payment_update(update, db=db))

    assert result["handled"] is True
    assert result["type"] == "successful_payment"
    assert result["payment_id"] == "payment_123"
    assert db.calls
    assert db.calls[0][1][0] == "completed"
    assert db.calls[0][1][1] == "tg_charge_123"
