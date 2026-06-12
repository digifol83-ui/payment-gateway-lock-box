import asyncio
import hashlib
import hmac


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []

    def __init__(self, timeout=10):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append({"method": "POST", "url": url, "headers": headers, "json": json})
        return FakeResponse(
            {
                "id": "pi_123",
                "account_id": "acct_123",
                "amount": json["amount"],
                "currency_code": json["currency_code"],
                "status": "requires_payment_instrument",
                "redirect_url": "https://pay.ziina.com/pi_123",
            }
        )


def test_create_order_uses_payment_intent_api_and_returns_checkout_fields(monkeypatch):
    import providers.ziina as ziina_module

    FakeAsyncClient.calls = []
    monkeypatch.setattr(ziina_module.httpx, "AsyncClient", FakeAsyncClient)

    provider = ziina_module.ZiinaProvider(
        api_token="zk_live_test",
        env="production",
        api_base="https://ziina.test/api",
        public_base_url="https://merchant.test",
    )

    result = asyncio.run(
        provider.create_order(
            {
                "amount": 12.34,
                "currency": "AED",
                "reference": "pay_123",
                "customer_email": "buyer@example.com",
                "description": "Beast AI credits",
            }
        )
    )

    call = FakeAsyncClient.calls[0]
    assert call["url"] == "https://ziina.test/api/payment_intent"
    assert call["headers"]["Authorization"] == "Bearer zk_live_test"
    assert call["json"]["amount"] == 1234
    assert call["json"]["currency_code"] == "AED"
    assert call["json"]["message"] == "Beast AI credits"
    assert call["json"]["test"] is False
    assert call["json"]["success_url"].startswith("https://merchant.test/pay/success/pay_123")
    assert result["order_id"] == "pi_123"
    assert result["session_id"] == "https://pay.ziina.com/pi_123"
    assert result["url"] == "https://pay.ziina.com/pi_123"


def test_verify_webhook_signature_uses_hmac_sha256():
    from providers.ziina import ZiinaProvider

    raw_body = b'{"event":"payment_intent.status.updated","data":{"id":"pi_123"}}'
    signature = hmac.new(b"secret", raw_body, hashlib.sha256).hexdigest()

    provider = ZiinaProvider(api_token="zk_live_test", webhook_secret="secret")

    assert provider.verify_webhook(raw_body, signature) is True
    assert provider.verify_webhook(raw_body, "bad-signature") is False


def test_parse_webhook_normalizes_payment_intent_status():
    from providers.ziina import ZiinaProvider

    provider = ZiinaProvider(api_token="zk_live_test")

    normalized = provider.parse_webhook(
        {
            "event": "payment_intent.status.updated",
            "data": {
                "id": "pi_123",
                "status": "completed",
                "metadata": {"payment_id": "pay_123"},
            },
        }
    )

    assert normalized == {
        "payment_id": "pay_123",
        "provider_order_id": "pi_123",
        "status": "completed",
        "raw_status": "completed",
    }
