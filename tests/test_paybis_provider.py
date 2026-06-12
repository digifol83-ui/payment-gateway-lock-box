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

        if "/v2/quote" in url:
            return FakeResponse({"quoteId": "quote_abc123", "rate": "3.67"})
        if "/v3/request" in url:
            return FakeResponse({"requestId": "req_xyz789", "status": "created"})
        return FakeResponse({}, 404)

    async def get(self, url, headers=None, params=None):
        self.calls.append({"method": "GET", "url": url, "headers": headers, "params": params})

        if "/v2/transactions" in url:
            return FakeResponse(
                {
                    "data": [
                        {
                            "id": "tx_456",
                            "requestId": "req_xyz789",
                            "status": "completed",
                            "partnerTransactionId": params.get("partnerTransactionId", ""),
                        }
                    ]
                }
            )
        return FakeResponse({}, 404)


def test_create_order_returns_redirect_url(monkeypatch):
    """PayBis create_order should return a widget redirect URL."""
    import providers.paybis as paybis_module

    FakeAsyncClient.calls = []
    monkeypatch.setattr(paybis_module.httpx, "AsyncClient", FakeAsyncClient)

    provider = paybis_module.PayBisProvider(
        partner_id="partner_123",
        hmac_key="aGVsbG9fd29ybGRfMTIzNDU2Nzg5MA==",  # base64("hello_world_1234567890")
        env="sandbox",
        api_base="https://widget-api.sandbox.paybis.com",
        public_base_url="https://merchant.test",
    )

    result = asyncio.run(
        provider.create_order(
            {
                "amount": 100.00,
                "currency": "AED",
                "reference": "pay_456",
                "customer_email": "buyer@example.com",
                "wallet_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "crypto_currency": "USDT",
                "user_ip": "1.2.3.4",
            }
        )
    )

    # Check the request call was made
    assert len(FakeAsyncClient.calls) >= 2  # quote + request
    request_call = FakeAsyncClient.calls[-1]
    assert request_call["url"] == "https://widget-api.sandbox.paybis.com/v3/request"
    assert request_call["json"]["partnerUserId"] == "pay_456"
    assert request_call["json"]["partnerTransactionId"] == "pay_456"
    assert request_call["json"]["email"] == "buyer@example.com"
    assert request_call["json"]["cryptoWalletAddress"]["address"].startswith("0x")

    # Check the returned checkout URL
    assert result["order_id"] == "req_xyz789"
    assert "widget.paybis.com" in result["url"]
    assert "partnerId=partner_123" in result["url"]
    assert "requestId=req_xyz789" in result["url"]
    assert result["status"] == "pending"


def test_get_status_returns_normalized_status(monkeypatch):
    """PayBis get_status should normalize transaction status."""
    import providers.paybis as paybis_module

    FakeAsyncClient.calls = []
    monkeypatch.setattr(paybis_module.httpx, "AsyncClient", FakeAsyncClient)

    provider = paybis_module.PayBisProvider(
        partner_id="partner_123",
        hmac_key="aGVsbG9fd29ybGRfMTIzNDU2Nzg5MA==",
        env="sandbox",
    )

    result = asyncio.run(provider.get_status("pay_456"))

    assert result["status"] == "completed"
    assert result["provider_order_id"] == "tx_456"
    assert result["raw_status"] == "completed"


def test_verify_webhook_signature():
    """PayBis webhook should verify HMAC signature."""
    from providers.paybis import PayBisProvider

    raw_body = b'{"event_id":"evt_123","transaction_id":"tx_456","status":"completed"}'
    signature = hmac.new(b"webhook_secret", raw_body, hashlib.sha256).hexdigest()

    provider = PayBisProvider(
        partner_id="partner_123",
        hmac_key="aGVsbG9fd29ybGRfMTIzNDU2Nzg5MA==",
        webhook_secret="webhook_secret",
    )

    assert provider.verify_webhook(raw_body, signature) is True
    assert provider.verify_webhook(raw_body, "bad-sig") is False
    assert provider.verify_webhook(raw_body, None) is False


def test_parse_webhook_normalizes_status():
    """PayBis webhook parser should extract and normalize status."""
    from providers.paybis import PayBisProvider

    provider = PayBisProvider(
        partner_id="partner_123",
        hmac_key="aGVsbG9fd29ybGRfMTIzNDU2Nzg5MA==",
    )

    normalized = provider.parse_webhook(
        {
            "event_id": "evt_123",
            "transaction_id": "tx_456",
            "status": "completed",
            "partnerTransactionId": "pay_789",
            "digital_amount_sent": {"amount": "27.25", "currency": "USDT"},
        }
    )

    assert normalized == {
        "payment_id": "pay_789",
        "provider_order_id": "tx_456",
        "status": "completed",
        "raw_status": "completed",
    }


def test_parse_webhook_infers_completed_from_digital_amount():
    """PayBis webhook with digital_amount_sent but no status field → completed."""
    from providers.paybis import PayBisProvider

    provider = PayBisProvider(
        partner_id="partner_123",
        hmac_key="aGVsbG9fd29ybGRfMTIzNDU2Nzg5MA==",
    )

    normalized = provider.parse_webhook(
        {
            "event_id": "evt_456",
            "transaction_id": "tx_789",
            "digital_amount_sent": {"amount": "50.00", "currency": "BTC"},
        }
    )

    assert normalized["status"] == "completed"


def test_is_configured_detects_missing_keys():
    """PayBis is_configured should return false when keys missing."""
    from providers.paybis import PayBisProvider

    provider = PayBisProvider(partner_id="", hmac_key="", env="sandbox")
    status = provider.is_configured()
    assert status["enabled"] is False

    provider2 = PayBisProvider(partner_id="pid_123", hmac_key="key_abc", env="production")
    status2 = provider2.is_configured()
    assert status2["enabled"] is True
    assert status2["mode"] == "live"
