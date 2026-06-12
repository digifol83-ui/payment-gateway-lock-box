import importlib
import asyncio
from urllib.parse import parse_qs, urlparse

import pytest

import config
from server import api_provider_test, transak_checkout, transak_checkout_redirect


def test_buy_route_serves_dedicated_transak_checkout_page():
    response = asyncio.run(transak_checkout())
    html = response.body.decode()

    assert response.status_code == 200
    assert "<title>Transak - Convert Fiat to Crypto</title>" in html
    assert "/api/transak/checkout?" in html


def test_config_exports_transak_access_token_from_setting(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TRANSAK_API_KEY", "api_key_value")
    monkeypatch.setenv("TRANSAK_ACCESS_TOKEN", "access_token_value")

    reloaded = importlib.reload(config)

    try:
        assert reloaded.TRANSAK_ACCESS_TOKEN == "access_token_value"
    finally:
        importlib.reload(config)


def test_config_exports_transak_brand_settings(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TRANSAK_EMAIL", "sichermayor@wshu.net")
    monkeypatch.setenv("TRANSAK_BRAND_NAME", "sichermayor")
    monkeypatch.setenv("TRANSAK_COMPANY_NAME", "Sichermayor investment llc")
    monkeypatch.setenv("TRANSAK_WEBSITE", "https://beastpay-api-544494288390.us-central1.run.app")
    monkeypatch.setenv("TRANSAK_THEME", "dark")
    monkeypatch.setenv("TRANSAK_SEND_CUSTOMER_EMAILS", "false")

    reloaded = importlib.reload(config)

    try:
        assert reloaded.TRANSAK_EMAIL == "sichermayor@wshu.net"
        assert reloaded.TRANSAK_BRAND_NAME == "sichermayor"
        assert reloaded.TRANSAK_COMPANY_NAME == "Sichermayor investment llc"
        assert reloaded.TRANSAK_WEBSITE == "https://beastpay-api-544494288390.us-central1.run.app"
        assert reloaded.TRANSAK_THEME == "dark"
        assert reloaded.TRANSAK_SEND_CUSTOMER_EMAILS is False
    finally:
        importlib.reload(config)


def test_transak_widget_url_uses_supported_settings(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BASE_URL", "https://pay.example.test")
    monkeypatch.setenv("TRANSAK_WEBSITE", "https://beastpay-api-544494288390.us-central1.run.app")
    monkeypatch.setenv("TRANSAK_THEME", "dark")

    reloaded_config = importlib.reload(config)

    try:
        import providers.transak as transak_module

        reloaded_transak = importlib.reload(transak_module)
        url = reloaded_transak.TransakProvider().build_widget_url({
            "id": "payment_123",
            "fiat_amount": 50,
            "fiat_currency": "USD",
            "crypto_currency": "USDT",
            "wallet_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        })
        qs = parse_qs(urlparse(url).query)

        assert qs["referrerDomain"] == ["beastpay-api-544494288390.us-central1.run.app"]
        assert qs["colorMode"] == ["DARK"]
        assert "theme" not in qs
        assert "partnerEmail" not in qs
        assert "partnerCompanyName" not in qs
        assert "partnerWebsite" not in qs
    finally:
        importlib.reload(reloaded_config)


def test_transak_production_status_accepts_refresh_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TRANSAK_API_KEY", "api_key_value")
    monkeypatch.setenv("TRANSAK_ACCESS_TOKEN", "")
    monkeypatch.setenv("TRANSAK_SECRET", "api_secret_value")
    monkeypatch.setenv("TRANSAK_ENV", "PRODUCTION")

    reloaded_config = importlib.reload(config)

    try:
        import providers as providers_module

        reloaded_providers = importlib.reload(providers_module)

        assert reloaded_providers._is_production("transak") is True
    finally:
        importlib.reload(reloaded_config)


def test_transak_production_status_requires_token_or_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TRANSAK_API_KEY", "api_key_value")
    monkeypatch.setenv("TRANSAK_ACCESS_TOKEN", "")
    monkeypatch.setenv("TRANSAK_SECRET", "")
    monkeypatch.setenv("TRANSAK_ENV", "PRODUCTION")

    reloaded_config = importlib.reload(config)

    try:
        import providers as providers_module

        reloaded_providers = importlib.reload(providers_module)

        assert reloaded_providers._is_production("transak") is False
    finally:
        importlib.reload(reloaded_config)


def test_transak_checkout_redirect_uses_session_widget_url(monkeypatch):
    import providers.transak as transak_module

    captured = {}

    async def fake_create_widget_url(self, payment):
        captured["payment"] = payment
        return "https://global.transak.com/?sessionId=session_123"

    def fail_direct_widget_url(self, payment):
        raise AssertionError("direct Transak widget URLs are deprecated")

    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)
    monkeypatch.setattr(transak_module.TransakProvider, "build_widget_url", fail_direct_widget_url)

    response = asyncio.run(transak_checkout_redirect(
        amount="50",
        currency="USD",
        crypto="USDT",
        email="buyer@example.test",
        wallet="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    ))

    assert response.status_code == 302
    assert response.headers["location"] == "https://global.transak.com/?sessionId=session_123"
    assert captured["payment"]["fiat_amount"] == 50.0
    assert captured["payment"]["fiat_currency"] == "USD"
    assert captured["payment"]["crypto_currency"] == "USDT"
    assert captured["payment"]["customer_email"] == "buyer@example.test"
    assert captured["payment"]["wallet_address"] == "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


def test_transak_checkout_redirect_reports_partner_access_blocker(monkeypatch):
    import providers.transak as transak_module

    async def fake_create_widget_url(self, payment):
        raise ValueError("Transak session error: {'statusCode': 401, 'message': 'Invalid or missing access-token.', 'errorCode': 1002}")

    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(transak_checkout_redirect(
            amount="50",
            currency="USD",
            crypto="USDT",
            email="buyer@example.test",
            wallet="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        ))

    assert exc_info.value.status_code == 502
    assert "transak_partner_access_token_rejected" in exc_info.value.detail
    assert "whitelist" in exc_info.value.detail.lower()


def test_provider_test_uses_transak_session_widget_url(monkeypatch):
    import providers.transak as transak_module

    async def fake_create_widget_url(self, payment):
        return "https://global.transak.com/?sessionId=session_123"

    def fail_direct_widget_url(self, payment):
        raise AssertionError("direct Transak widget URLs are deprecated")

    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)
    monkeypatch.setattr(transak_module.TransakProvider, "build_widget_url", fail_direct_widget_url)

    response = asyncio.run(api_provider_test({
        "provider_id": "transak",
        "amount": 50,
        "fiat_currency": "USD",
        "crypto_currency": "USDT",
        "wallet_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "customer_email": "buyer@example.test",
    }))

    assert response["provider_id"] == "transak"
    assert response["redirect_url"] == "https://global.transak.com/?sessionId=session_123"


def test_provider_test_reports_transak_session_errors(monkeypatch):
    import providers.transak as transak_module

    async def fake_create_widget_url(self, payment):
        raise ValueError("Transak access token refresh error: invalid api-secret")

    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(api_provider_test({
            "provider_id": "transak",
            "amount": 50,
            "fiat_currency": "USD",
            "crypto_currency": "USDT",
            "wallet_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        }))

    assert exc_info.value.status_code == 502
    assert "Transak access token refresh error" in exc_info.value.detail


def test_mcp_provider_checkout_uses_transak_session_widget_url(monkeypatch):
    import providers.transak as transak_module
    from mcp_beastpay.server import BeastPayMCPServer

    async def fake_create_widget_url(self, payment):
        return "https://global.transak.com/?sessionId=session_123"

    def fail_direct_widget_url(self, payment):
        raise AssertionError("direct Transak widget URLs are deprecated")

    monkeypatch.setattr(transak_module.TransakProvider, "create_widget_url", fake_create_widget_url)
    monkeypatch.setattr(transak_module.TransakProvider, "build_widget_url", fail_direct_widget_url)

    response = asyncio.run(BeastPayMCPServer().test_provider_checkout_link(
        provider_id="transak",
        amount=50,
        fiat_currency="USD",
        crypto_currency="USDT",
        wallet_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        customer_email="buyer@example.test",
    ))

    assert response["provider_id"] == "transak"
    assert response["redirect_url"] == "https://global.transak.com/?sessionId=session_123"


def test_transak_session_refreshes_access_token_when_configured_value_is_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TRANSAK_API_KEY", "api_key_value")
    monkeypatch.setenv("TRANSAK_ACCESS_TOKEN", "api_secret_value")
    monkeypatch.setenv("TRANSAK_SECRET", "api_secret_value")
    monkeypatch.setenv("TRANSAK_ENV", "PRODUCTION")

    reloaded_config = importlib.reload(config)

    try:
        import aiohttp
        import providers.transak as transak_module

        reloaded_transak = importlib.reload(transak_module)
        refreshed_token = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjQ3NDAwMDAwMDB9.signature"
        calls = []

        class FakeResponse:
            def __init__(self, status, body):
                self.status = status
                self._body = body

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def json(self):
                return self._body

            async def text(self):
                return str(self._body)

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def post(self, url, json, headers, timeout):
                calls.append({"url": url, "headers": headers, "json": json})
                if url == "https://api.transak.com/partners/api/v2/refresh-token":
                    return FakeResponse(200, {
                        "data": {
                            "accessToken": refreshed_token,
                            "expiresAt": 4740000000,
                        }
                    })
                if url == "https://api-gateway.transak.com/api/v2/auth/session":
                    if headers["access-token"] != refreshed_token:
                        return FakeResponse(401, {"message": "Invalid or missing access-token."})
                    return FakeResponse(200, {
                        "data": {
                            "widgetUrl": "https://global.transak.com/?sessionId=session_123"
                        }
                    })
                raise AssertionError(f"unexpected url: {url}")

        monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)

        url = asyncio.run(reloaded_transak.TransakProvider().create_widget_url({
            "id": "payment_123",
            "fiat_amount": 50,
            "fiat_currency": "USD",
            "crypto_currency": "USDT",
            "wallet_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        }))

        assert url == "https://global.transak.com/?sessionId=session_123"
        assert [call["url"] for call in calls] == [
            "https://api.transak.com/partners/api/v2/refresh-token",
            "https://api-gateway.transak.com/api/v2/auth/session",
        ]
    finally:
        importlib.reload(reloaded_config)
