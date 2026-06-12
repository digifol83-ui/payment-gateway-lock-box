import asyncio
import hashlib
import hmac


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls: list = []

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
                "id": "inv_abc123",
                "invoice_id": "inv_abc123",
                "status": "pending",
                "invoice_url": "https://pay.kyrrex.com/inv_abc123",
            }
        )

    async def get(self, url, headers=None, params=None):
        self.calls.append({"method": "GET", "url": url, "headers": headers, "params": params})
        return FakeResponse(
            {
                "id": "inv_abc123",
                "invoice_id": "inv_abc123",
                "status": "paid",
            }
        )


def test_create_order_returns_redirect_url(monkeypatch):
    """Kyrrex create_order should return an invoice redirect URL."""
    import providers.kyrrex as kyrrex_module

    FakeAsyncClient.calls = []
    monkeypatch.setattr(kyrrex_module.httpx, "AsyncClient", FakeAsyncClient)

    provider = kyrrex_module.KyrrexProvider(
        api_key="key_123",
        secret="secret_abc",
        env="sandbox",
        api_base="https://api.sandbox.kyrrex.com",
        public_base_url="https://merchant.test",
    )

    result = asyncio.run(
        provider.create_order(
            {
                "amount": 250.00,
                "currency": "AED",
                "reference": "pay_789",
                "customer_email": "buyer@test.ae",
                "crypto_currency": "USDT",
                "description": "Beast AI credits",
            }
        )
    )

    call = FakeAsyncClient.calls[0]
    assert call["url"] == "https://api.sandbox.kyrrex.com/api/v1/invoice"
    assert call["headers"]["X-API-Key"] == "key_123"
    assert "X-Signature" in call["headers"]
    assert call["json"]["order_id"] == "pay_789"
    assert call["json"]["currency"] == "AED"
    assert call["json"]["crypto_currency"] == "USDT"

    assert result["order_id"] == "inv_abc123"
    assert result["url"] == "https://pay.kyrrex.com/inv_abc123"
    assert result["status"] == "pending"


def test_get_status_returns_normalized(monkeypatch):
    """Kyrrex get_status should normalize invoice status."""
    import providers.kyrrex as kyrrex_module

    FakeAsyncClient.calls = []
    monkeypatch.setattr(kyrrex_module.httpx, "AsyncClient", FakeAsyncClient)

    provider = kyrrex_module.KyrrexProvider(
        api_key="key_123",
        secret="secret_abc",
        env="sandbox",
    )

    result = asyncio.run(provider.get_status("inv_abc123"))

    assert result["status"] == "completed"
    assert result["provider_order_id"] == "inv_abc123"
    assert result["raw_status"] == "paid"


def test_verify_webhook_signature():
    """Kyrrex webhook should verify HMAC signature."""
    from providers.kyrrex import KyrrexProvider

    raw_body = b'{"invoice_id":"inv_123","status":"paid"}'
    signature = hmac.new(b"webhook_secret", raw_body, hashlib.sha256).hexdigest()

    provider = KyrrexProvider(
        api_key="key_123",
        secret="secret_abc",
        webhook_secret="webhook_secret",
    )

    assert provider.verify_webhook(raw_body, signature) is True
    assert provider.verify_webhook(raw_body, "bad-sig") is False


def test_parse_webhook_normalizes_status():
    """Kyrrex webhook parser should extract and normalize status."""
    from providers.kyrrex import KyrrexProvider

    provider = KyrrexProvider(api_key="key_123", secret="secret_abc")

    normalized = provider.parse_webhook(
        {
            "invoice_id": "inv_456",
            "order_id": "pay_789",
            "status": "paid",
        }
    )

    assert normalized == {
        "payment_id": "pay_789",
        "provider_order_id": "inv_456",
        "status": "completed",
        "raw_status": "paid",
    }


def test_is_configured_detects_missing_keys():
    """Kyrrex is_configured should return false when keys missing."""
    from providers.kyrrex import KyrrexProvider

    provider = KyrrexProvider(api_key="", secret="", env="sandbox")
    status = provider.is_configured()
    assert status["enabled"] is False

    provider2 = KyrrexProvider(api_key="key_123", secret="secret_abc", env="production")
    status2 = provider2.is_configured()
    assert status2["enabled"] is True
    assert status2["mode"] == "live"
