#!/usr/bin/env python3
"""Exercise keystore restore and failure cleanup with a real disposable key."""

import base64
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("android_signing.py")


class SigningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            keystore = Path(directory) / "test.keystore"
            subprocess.run([
                "keytool", "-genkeypair", "-keystore", str(keystore),
                "-storepass", "test-only-password", "-keypass", "test-only-password",
                "-alias", "test-key", "-keyalg", "RSA", "-validity", "1",
                "-dname", "CN=Disposable test certificate",
            ], capture_output=True, check=True)
            cert = subprocess.run([
                "keytool", "-exportcert", "-keystore", str(keystore),
                "-storepass", "test-only-password", "-alias", "test-key",
            ], capture_output=True, check=True).stdout
            cls.raw = keystore.read_bytes()
            cls.secrets = {
                "ANDROID_KEYSTORE_BASE64": base64.b64encode(cls.raw).decode(),
                "ANDROID_KEYSTORE_PASSWORD": "test-only-password",
                "ANDROID_KEY_ALIAS": "test-key",
                "ANDROID_KEY_PASSWORD": "test-only-password",
                "ANDROID_SIGNING_CERT_SHA256": hashlib.sha256(cert).hexdigest(),
            }

    def restore(self, changes, succeeds):
        with tempfile.TemporaryDirectory() as directory:
            envfile = Path(directory) / "github-env"
            env = dict(os.environ, **self.secrets)
            env.update(RUNNER_TEMP=directory, GITHUB_ENV=str(envfile), GITHUB_RUN_NUMBER="103")
            env.update(changes)
            result = subprocess.run(["python3", str(SCRIPT), "prepare"], env=env,
                                    capture_output=True, text=True)
            output = result.stdout + result.stderr
            self.assertNotIn(self.secrets["ANDROID_KEYSTORE_BASE64"], output)
            self.assertNotIn(self.secrets["ANDROID_KEYSTORE_PASSWORD"], output)
            keys = list(Path(directory).rglob("*.keystore"))
            if succeeds:
                self.assertEqual(result.returncode, 0, output)
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0].read_bytes(), self.raw)
                self.assertEqual(keys[0].stat().st_mode & 0o777, 0o600)
                self.assertIn("ANDROID_VERSION_CODE=100103\n", envfile.read_text())
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(keys, [])
                self.assertFalse(envfile.exists())

    def test_fixed_key_and_formatted_fingerprint(self):
        digest = self.secrets["ANDROID_SIGNING_CERT_SHA256"]
        self.restore({"ANDROID_SIGNING_CERT_SHA256": ":".join(
            digest[i:i+2].upper() for i in range(0, len(digest), 2))}, True)

    def test_rejects_incomplete_or_wrong_credentials(self):
        for changes in (
            {"ANDROID_KEYSTORE_BASE64": ""},
            {"ANDROID_KEYSTORE_BASE64": "not base64!"},
            {"ANDROID_KEYSTORE_PASSWORD": "wrong-password"},
            {"ANDROID_KEY_ALIAS": "missing-alias"},
            {"ANDROID_KEY_PASSWORD": ""},
            {"ANDROID_SIGNING_CERT_SHA256": "0" * 64},
            {"GITHUB_RUN_NUMBER": "invalid"},
        ):
            with self.subTest(fields=list(changes)):
                self.restore(changes, False)


if __name__ == "__main__":
    unittest.main()
