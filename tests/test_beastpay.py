"""
BeastPay OpenClaw — Test Suite
Run: cd /home/kali/payment-gateway && python3 -m pytest tests/ -v
"""
import sys, os, json, re, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

# ─── Encryption ──────────────────────────────────────────────────────────────
from verification.encryption import encrypt_credential, decrypt_credential, mask_credential

SECRET = "test-secret-key-32chars-padded!!"

class TestEncryption:
    def test_roundtrip(self):
        plain = "sk_live_abc123xyz"
        enc   = encrypt_credential(plain, SECRET)
        assert decrypt_credential(enc, SECRET) == plain

    def test_different_each_time(self):
        enc1 = encrypt_credential("same", SECRET)
        enc2 = encrypt_credential("same", SECRET)
        assert enc1 != enc2  # different salt/iv each time

    def test_wrong_key_fails(self):
        enc = encrypt_credential("secret", SECRET)
        with pytest.raises(Exception):
            decrypt_credential(enc, "wrong-key-entirely-different!!")

    def test_mask_long(self):
        assert mask_credential("sk_live_abc123") == "**********c123"

    def test_mask_short(self):
        assert mask_credential("ab") == "****"

    def test_mask_exactly_4(self):
        # 4 chars → all masked (nothing left to show as suffix)
        assert mask_credential("1234") == "****"


# ─── Lockbox card validation ──────────────────────────────────────────────────
from lockbox import (
    validate_card_number, validate_expiry_date, validate_cvv,
    validate_cardholder_name, mask_card_number, _luhn_check,
)

class TestCardValidation:
    def test_valid_visa(self):
        # Standard Luhn-valid test number
        r = validate_card_number("4111111111111111")
        assert r["isValid"] is True

    def test_invalid_luhn(self):
        r = validate_card_number("4111111111111112")
        assert r["isValid"] is False
        assert any("Luhn" in e for e in r["errors"])

    def test_too_short(self):
        r = validate_card_number("411111")
        assert r["isValid"] is False

    def test_non_digits(self):
        r = validate_card_number("4111-abcd-1111-1111")
        assert r["isValid"] is False

    def test_expiry_valid(self):
        r = validate_expiry_date("12/99")
        assert r["isValid"] is True

    def test_expiry_expired(self):
        r = validate_expiry_date("01/20")
        assert r["isValid"] is False

    def test_expiry_bad_format(self):
        r = validate_expiry_date("1299")
        assert r["isValid"] is False

    def test_cvv_valid_3(self):
        assert validate_cvv("123")["isValid"] is True

    def test_cvv_valid_4(self):
        assert validate_cvv("1234")["isValid"] is True

    def test_cvv_too_short(self):
        assert validate_cvv("12")["isValid"] is False

    def test_cvv_letters(self):
        assert validate_cvv("abc")["isValid"] is False

    def test_name_valid(self):
        assert validate_cardholder_name("John Smith")["isValid"] is True

    def test_name_single_word(self):
        assert validate_cardholder_name("John")["isValid"] is False

    def test_name_empty(self):
        assert validate_cardholder_name("")["isValid"] is False

    def test_mask_16digit(self):
        assert mask_card_number("4111111111111111") == "**** **** **** 1111"

    def test_mask_with_spaces(self):
        assert mask_card_number("4111 1111 1111 1111") == "**** **** **** 1111"


# ─── OTP extraction ──────────────────────────────────────────────────────────
from verification.gateway_registration import extract_otp_from_email, validate_otp_format

class TestOTP:
    def test_extract_after_keyword(self):
        assert extract_otp_from_email("Your verification code is 483920") == "483920"

    def test_extract_before_keyword(self):
        assert extract_otp_from_email("483920 is your OTP") == "483920"

    def test_extract_4digit(self):
        otp = extract_otp_from_email("Use code 1234 to verify")
        assert otp == "1234"

    def test_no_otp(self):
        assert extract_otp_from_email("Hello, welcome to MoonPay!") is None

    def test_validate_format_6(self):
        assert validate_otp_format("123456") is True

    def test_validate_format_4(self):
        assert validate_otp_format("1234") is True

    def test_validate_too_short(self):
        assert validate_otp_format("123") is False

    def test_validate_letters(self):
        assert validate_otp_format("12abc") is False


# ─── Company lookup jurisdiction map ─────────────────────────────────────────
from verification.company_lookup import JURISDICTION_MAP, is_configured

class TestCompanyLookup:
    def test_gb_jurisdiction(self):
        assert JURISDICTION_MAP["GB"] == "gb"

    def test_us_jurisdiction(self):
        assert JURISDICTION_MAP["US"] == "us"

    def test_all_have_values(self):
        for k, v in JURISDICTION_MAP.items():
            assert len(v) > 0

    def test_is_configured_returns_dict(self):
        result = is_configured()
        assert "enabled" in result
        assert "jurisdictions" in result
        assert isinstance(result["jurisdictions"], list)


# ─── Database helpers ─────────────────────────────────────────────────────────
import database_legacy as db

@pytest.fixture(autouse=True, scope="session")
def init_test_db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("db")
    db.DB_FILE = str(tmp / "test.db")
    db.init_db()

class TestDatabase:
    def test_create_merchant(self):
        m = db.create_merchant("Test Co", "test@example.com")
        assert m["api_key"].startswith("mk_")
        assert m["name"] == "Test Co"

    def test_get_merchant_by_key(self):
        m = db.create_merchant("Acme", "acme@test.com")
        got = db.get_merchant_by_key(m["api_key"])
        assert got is not None
        assert got["name"] == "Acme"

    def test_create_payment_link(self):
        link = db.create_payment_link({
            "wallet_address": "0xABC123",
            "fiat_currency": "USD",
            "crypto_currency": "USDT",
            "amount": 100.0,
        })
        assert link["id"] is not None
        assert link["wallet_address"] == "0xABC123"

    def test_create_payment(self):
        link = db.create_payment_link({"wallet_address": "0xDEF", "fiat_currency": "USD"})
        p = db.create_payment({
            "link_id": link["id"],
            "amount": 50.0,
            "fiat_currency": "USD",
            "crypto_currency": "BTC",
            "wallet_address": "0xDEF",
            "customer_email": "user@test.com",
            "provider": "transak",
        })
        assert p["status"] == "pending"
        assert p["amount"] == 50.0

    def test_update_payment_status(self):
        link = db.create_payment_link({"wallet_address": "0xGHI", "fiat_currency": "GBP"})
        p = db.create_payment({
            "amount": 25.0, "fiat_currency": "GBP", "crypto_currency": "ETH",
            "wallet_address": "0xGHI", "provider": "moonpay",
        })
        db.update_payment_status(p["id"], "completed")
        updated = db.get_payment(p["id"])
        assert updated["status"] == "completed"

    def test_create_merchant_profile(self):
        prof = db.create_merchant_profile({
            "company_name": "OpenClaw Ltd",
            "country": "GB",
            "business_email": "admin@openclaw.io",
        })
        assert prof["onboarding_status"] == "pending"
        assert prof["current_phase"] == 0

    def test_stats_returns_dict(self):
        stats = db.get_stats()
        assert "total_payments" in stats
        assert "total_volume_usd" in stats

    def test_verification_stats(self):
        vstats = db.get_verification_stats()
        assert "total_merchants" in vstats
        assert "verified" in vstats


# ─── Document parser validation ───────────────────────────────────────────────
from verification.document_parser import validate_extracted_data

class TestDocumentParser:
    def test_valid_high_confidence(self):
        data = {
            "company_name": "Test Ltd",
            "registration_number": "12345678",
            "incorporation_date": None,
            "business_address": None,
            "confidence": 85,
        }
        assert validate_extracted_data(data) is True

    def test_invalid_low_confidence(self):
        data = {"company_name": "Test", "confidence": 30}
        assert validate_extracted_data(data) is False

    def test_invalid_no_key_fields(self):
        data = {"confidence": 90}
        assert validate_extracted_data(data) is False


# ─── Gateway registration payload ────────────────────────────────────────────
from verification.gateway_registration import GATEWAY_PRIORITY, GATEWAY_ENDPOINTS

class TestGatewayRegistration:
    def test_priority_order(self):
        assert GATEWAY_PRIORITY[0] == "moonpay"
        assert "transak" in GATEWAY_PRIORITY
        assert "simplex" in GATEWAY_PRIORITY
        assert "ramp_network" in GATEWAY_PRIORITY

    def test_all_gateways_have_endpoints(self):
        for gw in GATEWAY_PRIORITY:
            assert gw in GATEWAY_ENDPOINTS
            assert "register" in GATEWAY_ENDPOINTS[gw]
            assert "verify_otp" in GATEWAY_ENDPOINTS[gw]
