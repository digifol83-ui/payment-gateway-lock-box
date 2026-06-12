#!/usr/bin/env python3
"""
Secure Credentials Vault
AES-256 encryption for all sensitive gateway credentials
"""
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from datetime import datetime
import hashlib

class SecureVault:
    """Encrypted credential storage"""

    def __init__(self, vault_file: str = ".secure_vault.json"):
        self.vault_file = Path(vault_file)
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key_file = Path(".vault_key")

        if key_file.exists():
            return key_file.read_bytes()

        # Generate new key
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Read-only by owner
        print(f"✅ Generated encryption key: {key_file}")
        return key

    def _load_vault(self) -> dict:
        """Load vault from disk"""
        if not self.vault_file.exists():
            return {"credentials": {}, "metadata": {}}

        content = self.vault_file.read_text()
        return json.loads(content)

    def _save_vault(self, vault: dict):
        """Save vault to disk"""
        self.vault_file.write_text(json.dumps(vault, indent=2))
        self.vault_file.chmod(0o600)  # Read-only by owner

    def store_credential(self, gateway: str, api_key: str, secret: str = None, **kwargs):
        """Store encrypted credentials"""
        vault = self._load_vault()

        # Encrypt values
        encrypted_key = self.cipher.encrypt(api_key.encode()).decode()
        encrypted_secret = self.cipher.encrypt(secret.encode()).decode() if secret else None

        credential = {
            "gateway": gateway,
            "api_key": encrypted_key,
            "secret": encrypted_secret,
            "stored_at": datetime.utcnow().isoformat(),
            "metadata": kwargs,
        }

        vault["credentials"][gateway] = credential

        # Save
        self._save_vault(vault)
        print(f"✅ Stored encrypted credentials for {gateway}")

    def retrieve_credential(self, gateway: str) -> dict:
        """Retrieve and decrypt credentials"""
        vault = self._load_vault()

        if gateway not in vault["credentials"]:
            raise ValueError(f"No credentials for {gateway}")

        cred = vault["credentials"][gateway]

        # Decrypt
        decrypted_key = self.cipher.decrypt(cred["api_key"].encode()).decode()
        decrypted_secret = None
        if cred.get("secret"):
            decrypted_secret = self.cipher.decrypt(cred["secret"].encode()).decode()

        return {
            "api_key": decrypted_key,
            "secret": decrypted_secret,
            "stored_at": cred.get("stored_at"),
            "metadata": cred.get("metadata", {}),
        }

    def list_credentials(self):
        """List stored gateways (without secrets)"""
        vault = self._load_vault()

        print("\n" + "=" * 70)
        print("  STORED CREDENTIALS")
        print("=" * 70 + "\n")

        if not vault["credentials"]:
            print("  (No credentials stored)")
            return

        for gateway, cred in vault["credentials"].items():
            stored_at = cred.get("stored_at", "N/A")
            has_secret = "✅" if cred.get("secret") else "❌"
            print(f"  {gateway:<15} stored: {stored_at}")
            print(f"    Secret: {has_secret}")
            print()

    def export_to_env(self, gateway: str):
        """Export credentials to .env format"""
        cred = self.retrieve_credential(gateway)

        if gateway.lower() == "ziina":
            return f"""ZIINA_API_TOKEN={cred['api_key']}
ZIINA_WEBHOOK_SECRET={cred['secret']}
ZIINA_ENV=production"""

        elif gateway.lower() == "transak":
            return f"""TRANSAK_API_KEY={cred['api_key']}
TRANSAK_ACCESS_TOKEN={cred['secret']}
TRANSAK_ENV=production"""

        elif gateway.lower() == "moonpay":
            return f"""MOONPAY_API_KEY={cred['api_key']}
MOONPAY_SECRET={cred['secret']}
MOONPAY_ENV=production"""

        else:
            return f"""{gateway.upper()}_API_KEY={cred['api_key']}
{gateway.upper()}_SECRET={cred['secret']}"""

    def delete_credential(self, gateway: str):
        """Delete stored credentials"""
        vault = self._load_vault()

        if gateway in vault["credentials"]:
            del vault["credentials"][gateway]
            self._save_vault(vault)
            print(f"✅ Deleted credentials for {gateway}")
        else:
            print(f"❌ No credentials found for {gateway}")


def main():
    """CLI interface"""
    import sys

    vault = SecureVault()

    if len(sys.argv) < 2:
        print("""
Usage:
  python3 secure_vault.py store <gateway> <api_key> <secret>
  python3 secure_vault.py get <gateway>
  python3 secure_vault.py list
  python3 secure_vault.py export <gateway>
  python3 secure_vault.py delete <gateway>

Examples:
  python3 secure_vault.py store ziina zk_live_xxx webhook_secret_yyy
  python3 secure_vault.py get ziina
  python3 secure_vault.py list
""")
        return

    command = sys.argv[1].lower()

    if command == "store" and len(sys.argv) >= 4:
        gateway = sys.argv[2]
        api_key = sys.argv[3]
        secret = sys.argv[4] if len(sys.argv) > 4 else None
        vault.store_credential(gateway, api_key, secret)

    elif command == "get" and len(sys.argv) >= 3:
        gateway = sys.argv[2]
        try:
            cred = vault.retrieve_credential(gateway)
            print(f"\n✅ Retrieved credentials for {gateway}:")
            print(f"  API Key: {cred['api_key'][:20]}...")
            if cred["secret"]:
                print(f"  Secret: {cred['secret'][:20]}...")
            print(f"  Stored: {cred['stored_at']}")
        except ValueError as e:
            print(f"❌ {e}")

    elif command == "list":
        vault.list_credentials()

    elif command == "export" and len(sys.argv) >= 3:
        gateway = sys.argv[2]
        try:
            env_format = vault.export_to_env(gateway)
            print(f"\n{env_format}")
            print("\n✅ Copy above lines to .env")
        except ValueError as e:
            print(f"❌ {e}")

    elif command == "delete" and len(sys.argv) >= 3:
        gateway = sys.argv[2]
        confirm = input(f"Delete {gateway}? (y/N): ").strip().lower()
        if confirm == "y":
            vault.delete_credential(gateway)

    else:
        print("❌ Invalid command")


if __name__ == "__main__":
    main()
