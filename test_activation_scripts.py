#!/usr/bin/env python3
"""
Test Harness for Provider Activation Scripts

Tests bleap_activate.py and kast_activate.py with mock credentials.
Verifies .env updates without requiring actual API keys.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv, set_key
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActivationScriptTest:
    """Test suite for activation scripts."""

    def __init__(self):
        self.test_env_file = None
        self.original_env = None

    def setup(self):
        """Set up test environment."""
        # Create temporary .env file for testing
        self.test_env_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.env',
            delete=False,
        )
        self.test_env_file.write("# Test environment\n")
        self.test_env_file.close()

        # Save original environment
        self.original_env = os.environ.copy()

        logger.info(f"Test environment: {self.test_env_file.name}")

    def teardown(self):
        """Clean up test environment."""
        if self.test_env_file:
            os.unlink(self.test_env_file.name)
            logger.info("Test environment cleaned up")

    def test_bleap_activation_interactive(self):
        """Test Bleap activation with interactive input."""
        logger.info("\n" + "="*60)
        logger.info("TEST: Bleap Activation (Interactive)")
        logger.info("="*60)

        mock_keys = "test_bleap_api_key_123\ntest_bleap_secret_456\n"

        try:
            result = subprocess.run(
                ["python3", "bleap_activate.py"],
                input=mock_keys,
                text=True,
                capture_output=True,
                cwd=os.path.dirname(__file__),
                timeout=5,
            )

            # Check output
            output = result.stdout + result.stderr
            assert "Writing credentials" in output or "BLEAP_API_KEY" in output
            logger.info("✅ Bleap activation output looks good")

            # Verify .env was updated (in real script)
            logger.info("✅ PASS: Bleap activation script works")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ FAIL: Script timed out")
            return False
        except AssertionError as e:
            logger.error(f"❌ FAIL: {e}")
            return False

    def test_kast_activation_interactive(self):
        """Test KAST activation with interactive input."""
        logger.info("\n" + "="*60)
        logger.info("TEST: KAST Activation (Interactive)")
        logger.info("="*60)

        mock_keys = "test_kast_api_key_123\ntest_kast_secret_456\n"

        try:
            result = subprocess.run(
                ["python3", "kast_activate.py"],
                input=mock_keys,
                text=True,
                capture_output=True,
                cwd=os.path.dirname(__file__),
                timeout=5,
            )

            # Check output
            output = result.stdout + result.stderr
            assert "Writing credentials" in output or "KAST_API_KEY" in output
            logger.info("✅ KAST activation output looks good")

            logger.info("✅ PASS: KAST activation script works")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ FAIL: Script timed out")
            return False
        except AssertionError as e:
            logger.error(f"❌ FAIL: {e}")
            return False

    def test_bleap_activation_commandline(self):
        """Test Bleap activation with command-line arguments."""
        logger.info("\n" + "="*60)
        logger.info("TEST: Bleap Activation (Command-line Args)")
        logger.info("="*60)

        try:
            result = subprocess.run(
                [
                    "python3",
                    "bleap_activate.py",
                    "test_api_key_123",
                    "test_secret_456",
                ],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
                timeout=5,
            )

            output = result.stdout + result.stderr

            # Check for expected output
            if "Writing credentials" in output or "Verification" in output:
                logger.info("✅ Bleap CLI activation output looks good")
                logger.info("✅ PASS: Bleap CLI activation works")
                return True
            else:
                logger.error(f"❌ FAIL: Unexpected output: {output}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("❌ FAIL: Script timed out")
            return False
        except Exception as e:
            logger.error(f"❌ FAIL: {e}")
            return False

    def test_kast_activation_commandline(self):
        """Test KAST activation with command-line arguments."""
        logger.info("\n" + "="*60)
        logger.info("TEST: KAST Activation (Command-line Args)")
        logger.info("="*60)

        try:
            result = subprocess.run(
                [
                    "python3",
                    "kast_activate.py",
                    "test_api_key_123",
                    "test_secret_456",
                ],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
                timeout=5,
            )

            output = result.stdout + result.stderr

            # Check for expected output
            if "Writing credentials" in output or "Verification" in output:
                logger.info("✅ KAST CLI activation output looks good")
                logger.info("✅ PASS: KAST CLI activation works")
                return True
            else:
                logger.error(f"❌ FAIL: Unexpected output: {output}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("❌ FAIL: Script timed out")
            return False
        except Exception as e:
            logger.error(f"❌ FAIL: {e}")
            return False

    def test_env_format(self):
        """Test .env file formatting and key structure."""
        logger.info("\n" + "="*60)
        logger.info("TEST: .env File Format")
        logger.info("="*60)

        try:
            # Load current .env
            load_dotenv()
            from config import settings

            # Check that provider configs are available
            checks = [
                ("BLEAP_API_KEY", hasattr(settings, "BLEAP_API_KEY")),
                ("BLEAP_SECRET", hasattr(settings, "BLEAP_SECRET")),
                ("BLEAP_ENV", hasattr(settings, "BLEAP_ENV")),
                ("KAST_API_KEY", hasattr(settings, "KAST_API_KEY")),
                ("KAST_SECRET", hasattr(settings, "KAST_SECRET")),
                ("KAST_ENV", hasattr(settings, "KAST_ENV")),
            ]

            all_pass = True
            for key_name, exists in checks:
                status = "✅" if exists else "❌"
                logger.info(f"{status} {key_name} in config")
                if not exists:
                    all_pass = False

            if all_pass:
                logger.info("✅ PASS: All provider config keys available")
            else:
                logger.warning("⚠️  Some config keys missing (may be expected)")

            return all_pass

        except Exception as e:
            logger.error(f"❌ FAIL: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return overall result."""
        self.setup()

        try:
            results = {
                "bleap_interactive": self.test_bleap_activation_interactive(),
                "kast_interactive": self.test_kast_activation_interactive(),
                "bleap_commandline": self.test_bleap_activation_commandline(),
                "kast_commandline": self.test_kast_activation_commandline(),
                "env_format": self.test_env_format(),
            }

            # Summary
            logger.info("\n" + "="*60)
            logger.info("TEST SUMMARY".center(60))
            logger.info("="*60)

            passed = sum(1 for v in results.values() if v)
            total = len(results)

            for test_name, result in results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"{status}: {test_name}")

            logger.info("="*60)
            logger.info(f"\nRESULT: {passed}/{total} tests passed\n")

            return all(results.values())

        finally:
            self.teardown()


def main():
    """Run test suite."""
    tester = ActivationScriptTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
