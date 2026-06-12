import hashlib
import hmac
import importlib
import json

import config


def reload_moonpay(monkeypatch, webhook_secret="test_shared_token"):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MOONPAY_WEBHOOK_SECRET", webhook_secret)

    reloaded_config = importlib.reload(config)

    import providers.moonpay as moonpay_module

    return reloaded_config, importlib.reload(moonpay_module)


def test_moonpay_commerce_webhook_verifies_x_signature_and_bearer(monkeypatch):
    _, moonpay_module = reload_moonpay(monkeypatch)

    raw_body = b'{"event":"CREATED","transactionObject":{"id":"txn_123"}}'
    signature = hmac.new(
        b"test_shared_token",
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    try:
        provider = moonpay_module.MoonPayProvider()

        assert provider.verify_webhook(
            raw_body,
            signature_header=signature,
            authorization_header="Bearer test_shared_token",
        )
        assert not provider.verify_webhook(
            raw_body,
            signature_header=signature,
            authorization_header="Bearer wrong_token",
        )
    finally:
        importlib.reload(config)


def test_moonpay_commerce_paylink_payload_maps_status_and_payment_id(monkeypatch):
    _, moonpay_module = reload_moonpay(monkeypatch)

    payload = {
        "event": "CREATED",
        "transactionObject": {
            "id": "txn_123",
            "paylinkId": "paylink_456",
            "meta": {
                "transactionStatus": "SUCCESS",
                "transactionSignature": "chain_sig_789",
                "additionalJSON": json.dumps({"payment_id": "payment_abc"}),
                "tokenQuote": {
                    "toAmountDecimal": "42.5",
                },
            },
        },
    }

    try:
        event = moonpay_module.MoonPayProvider().parse_webhook(payload)

        assert event["payment_id"] == "payment_abc"
        assert event["provider_order_id"] == "paylink_456"
        assert event["provider_tx_id"] == "txn_123"
        assert event["status"] == "completed"
        assert event["crypto_amount"] == "42.5"
        assert event["raw_status"] == "SUCCESS"
    finally:
        importlib.reload(config)


def test_moonpay_commerce_deposit_payload_maps_confirmed_status(monkeypatch):
    _, moonpay_module = reload_moonpay(monkeypatch)

    payload = {
        "event": "DEPOSIT_TX_CONFIRMED",
        "depositId": "dep_123",
        "customerId": "payment_abc",
        "amount": "35328965",
        "originalAmountInUSD": "3072627",
    }

    try:
        event = moonpay_module.MoonPayProvider().parse_webhook(payload)

        assert event["payment_id"] == "payment_abc"
        assert event["provider_order_id"] == "dep_123"
        assert event["provider_tx_id"] == "dep_123"
        assert event["status"] == "completed"
        assert event["crypto_amount"] == "35328965"
        assert event["raw_status"] == "DEPOSIT_TX_CONFIRMED"
    finally:
        importlib.reload(config)
