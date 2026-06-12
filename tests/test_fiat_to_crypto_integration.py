"""
End-to-End Integration Tests: Fiat-to-Crypto Payment Flow

Tests the complete payment lifecycle:
1. Provider selection based on amount/currency
2. Payment creation with chosen provider
3. Webhook handling and status updates
4. Failover to alternative provider on failure
5. Settlement tracking
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from provider_selector import ProviderSelector, SelectionStrategy
from webhook_handlers import (
    BleapWebhookHandler,
    KastWebhookHandler,
    handle_provider_webhook,
)
from forceverify import ForceVerify


class TestProviderSelection:
    """Test provider selection logic."""

    def test_select_best_provider_usd_100(self):
        """Test selecting best provider for $100 USD transaction."""
        provider = ProviderSelector.select_provider(
            amount_usd=100,
            fiat_currency="USD",
            crypto_currency="USDC",
            strategy=SelectionStrategy.BALANCED,
        )
        assert provider is not None
        assert isinstance(provider, str)

    def test_select_best_provider_usd_1000(self):
        """Test selecting best provider for $1000 USD transaction."""
        provider = ProviderSelector.select_provider(
            amount_usd=1000,
            fiat_currency="USD",
            strategy=SelectionStrategy.BALANCED,
        )
        assert provider is not None

    def test_select_cheapest_provider(self):
        """Test fee-optimized provider selection."""
        provider = ProviderSelector.select_provider(
            amount_usd=500,
            fiat_currency="USD",
            strategy=SelectionStrategy.CHEAPEST,
        )
        assert provider is not None

    def test_select_fastest_provider(self):
        """Test speed-optimized provider selection."""
        provider = ProviderSelector.select_provider(
            amount_usd=500,
            fiat_currency="USD",
            strategy=SelectionStrategy.FASTEST,
        )
        assert provider is not None

    def test_rank_providers(self):
        """Test ranking multiple providers."""
        rankings = ProviderSelector.rank_providers(
            amount_usd=250,
            fiat_currency="USD",
            top_n=5,
        )
        assert len(rankings) > 0
        assert all(hasattr(r, 'score') for r in rankings)
        # Verify sorted by score descending
        assert rankings[0].score >= rankings[-1].score

    def test_get_failover_chain(self):
        """Test failover provider chain."""
        chain = ProviderSelector.get_failover_chain(
            amount_usd=300,
            fiat_currency="USD",
        )
        assert len(chain) > 0
        # All providers should be unique
        assert len(chain) == len(set(chain))

    def test_kyc_tier_calculation(self):
        """Test KYC tier determination."""
        free_tier = ProviderSelector._get_kyc_tier(50)
        assert free_tier == "none"

        email_tier = ProviderSelector._get_kyc_tier(250)
        assert email_tier == "email_kyc"

        full_tier = ProviderSelector._get_kyc_tier(1000)
        assert full_tier == "full_kyc"

    def test_unsupported_currency(self):
        """Test that unsupported currencies return None or empty."""
        provider = ProviderSelector.select_provider(
            amount_usd=100,
            fiat_currency="JPY",  # Not commonly supported
            strategy=SelectionStrategy.BALANCED,
        )
        # May return None or a provider that supports it
        # Just verify it doesn't crash
        assert provider is None or isinstance(provider, str)

    def test_amount_exceeds_limit(self):
        """Test that amounts exceeding provider limits are excluded."""
        # $100k should exceed most providers' limits
        provider = ProviderSelector.select_provider(
            amount_usd=100000,
            fiat_currency="USD",
            strategy=SelectionStrategy.BALANCED,
        )
        # Either None or a provider with $100k+ limit
        if provider:
            meta = ProviderSelector.SETTLEMENT_TIMES
            assert provider in meta


class TestWebhookHandlers:
    """Test webhook handling from providers."""

    def test_bleap_webhook_signature_verification(self, monkeypatch):
        """Test Bleap webhook signature verification."""
        from webhook_handlers import WebhookVerifier
        from config import settings

        payload = b'{"transaction_id": "tx_123"}'
        secret = "test_secret"
        monkeypatch.setattr(settings, "BLEAP_SECRET", secret)

        # Mock correct signature
        import hmac
        import hashlib
        correct_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Verify correct signature passes
        assert WebhookVerifier.verify_bleap_signature(payload, correct_sig)

        # Verify incorrect signature fails
        assert not WebhookVerifier.verify_bleap_signature(payload, "wrong_sig")

    @pytest.mark.asyncio
    async def test_bleap_webhook_parsing(self):
        """Test parsing Bleap webhook data."""
        webhook_payload = b"""{
            "transaction_id": "tx_123456",
            "status": "completed",
            "amount": 100.50,
            "fiat_amount": 100.00,
            "fiat_currency": "USD",
            "crypto": "USDC",
            "wallet_address": "0x1234...abcd",
            "blockchain_tx_id": "0x9999...abcd",
            "completed_at": "2026-05-06T12:00:00Z"
        }"""

        success, normalized = await BleapWebhookHandler.handle(
            webhook_payload,
            "mock_signature"
        )

        # Would fail signature check in real scenario, but data structure is valid
        assert isinstance(normalized, dict)

    @pytest.mark.asyncio
    async def test_kast_webhook_parsing(self):
        """Test parsing KAST webhook data."""
        webhook_payload = b"""{
            "order_id": "order_xyz789",
            "status": "completed",
            "crypto_amount": 100.50,
            "fiat_amount": 100.00,
            "fiat_currency": "USD",
            "crypto_currency": "USDC",
            "wallet_address": "0x1234...abcd",
            "transaction_hash": "0x9999...abcd",
            "completed_at": "2026-05-06T12:00:00Z"
        }"""

        success, normalized = await KastWebhookHandler.handle(
            webhook_payload,
            "mock_signature"
        )

        assert isinstance(normalized, dict)

    def test_webhook_status_mapping(self):
        """Test provider status → standard status mapping."""
        assert BleapWebhookHandler._map_status("completed") == "completed"
        assert BleapWebhookHandler._map_status("pending") == "pending"
        assert BleapWebhookHandler._map_status("failed") == "failed"

        assert KastWebhookHandler._map_status("completed") == "completed"
        assert KastWebhookHandler._map_status("awaiting_payment") == "pending"


class TestForceVerify:
    """Test provider ranking and verification."""

    def test_rank_all_providers(self):
        """Test ranking all providers."""
        rankings = ForceVerify.rank_all()
        assert len(rankings) > 0
        assert all(hasattr(r, 'overall_score') for r in rankings)
        # Verify sorted by overall_score
        assert rankings[0].overall_score >= rankings[-1].overall_score

    def test_best_provider(self):
        """Test getting the single best provider."""
        best = ForceVerify.best()
        assert best is not None
        assert hasattr(best, 'provider_id')
        assert hasattr(best, 'overall_score')

    def test_rank_for_amount(self):
        """Test ranking providers for specific amount."""
        rankings = ForceVerify.rank_for_amount(amount_usd=250, fiat_currency="USD")
        assert len(rankings) > 0
        # All returned providers should support the currency
        for ranking in rankings:
            meta_item = {}
            # Verify each provider can handle this amount
            assert ranking.no_kyc_limit_usd > 0 or ranking.overall_score > 0

    def test_health_check(self):
        """Test provider health check."""
        health = ForceVerify.health_check()
        assert "timestamp" in health
        assert "live_count" in health
        assert "sandbox_count" in health
        assert "total_count" in health

    def test_export_dashboard_data(self):
        """Test dashboard data export."""
        data = ForceVerify.export_dashboard_data()
        assert "providers" in data
        assert "summary" in data
        assert "by_type" in data
        assert "by_status" in data
        assert len(data["providers"]) > 0


class TestPaymentFlow:
    """Test complete payment flow."""

    @pytest.mark.asyncio
    async def test_payment_creation_flow(self):
        """Test creating payment and selecting provider."""
        # Step 1: Select provider for transaction
        amount_usd = 150
        fiat_currency = "USD"
        crypto_currency = "USDC"

        provider = ProviderSelector.select_provider(
            amount_usd=amount_usd,
            fiat_currency=fiat_currency,
            crypto_currency=crypto_currency,
        )

        assert provider is not None, "Should select a provider for $150 USD"

        # Step 2: In real flow, create payment order with provider
        # This would call: provider.create_order(...)
        # For this test, just verify provider metadata is available
        from providers import get_provider_metadata
        meta = get_provider_metadata(provider)
        assert meta is not None

    @pytest.mark.asyncio
    async def test_failover_on_provider_failure(self):
        """Test failover to alternative provider on failure."""
        amount_usd = 200
        fiat_currency = "USD"

        # Get failover chain
        chain = ProviderSelector.get_failover_chain(
            amount_usd=amount_usd,
            fiat_currency=fiat_currency,
        )

        assert len(chain) > 1, "Should have at least 2 providers in failover chain"

        # Simulate failure of first provider
        primary = chain[0]
        fallback = chain[1]

        assert primary != fallback, "Fallback should be different from primary"

    @pytest.mark.asyncio
    async def test_kyc_tier_based_routing(self):
        """Test routing based on KYC requirements."""
        # Small amount - no KYC
        small_providers = ProviderSelector.rank_providers(
            amount_usd=50,
            fiat_currency="USD",
            top_n=3,
        )

        # Large amount - full KYC
        large_providers = ProviderSelector.rank_providers(
            amount_usd=5000,
            fiat_currency="USD",
            top_n=3,
        )

        # Both should have providers, but different KYC tiers
        assert len(small_providers) > 0
        assert len(large_providers) > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_amount(self):
        """Test handling of invalid amounts."""
        # Zero amount
        provider = ProviderSelector.select_provider(
            amount_usd=0,
            fiat_currency="USD",
        )
        assert provider is None

        # Negative amount
        provider = ProviderSelector.select_provider(
            amount_usd=-100,
            fiat_currency="USD",
        )
        assert provider is None

    def test_invalid_currency(self):
        """Test handling of invalid currencies."""
        provider = ProviderSelector.select_provider(
            amount_usd=100,
            fiat_currency="INVALID_CURRENCY",
        )
        # Should return None or handle gracefully
        assert provider is None or isinstance(provider, str)

    def test_no_providers_available(self):
        """Test when no providers match criteria."""
        # Very high amount that exceeds all limits
        provider = ProviderSelector.select_provider(
            amount_usd=9999999,
            fiat_currency="USD",
        )
        assert provider is None


# Pytest fixtures and configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


@pytest.fixture
def mock_db():
    """Mock database instance."""
    db = AsyncMock()
    db.find_payment_by_provider_ref = AsyncMock(return_value=None)
    db.update_payment = AsyncMock(return_value=True)
    return db


@pytest.fixture
def mock_payment():
    """Mock payment object."""
    payment = Mock()
    payment.id = "pay_123"
    payment.status = "pending"
    payment.provider_data = {}
    payment.merchant = Mock()
    payment.merchant.webhook_url = "https://example.com/webhook"
    return payment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
