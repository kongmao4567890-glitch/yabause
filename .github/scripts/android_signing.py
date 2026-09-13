#!/usr/bin/env python3
"""Restore a private CI keystore and verify the identity of published APKs."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def required(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing {name}. Configure fixed signing secrets; see docs/android-signing.md.")
    return value


def fingerprint(value):
    value = value.replace(":", "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("ANDROID_SIGNING_CERT_SHA256 must contain the certificate SHA-256 fingerprint.")
    return value


def prepare():
    # Check everything before writing any key material. Never generate a key in CI.
    encoded = required("ANDROID_KEYSTORE_BASE64")
    for name in ("ANDROID_KEYSTORE_PASSWORD", "ANDROID_KEY_ALIAS", "ANDROID_KEY_PASSWORD"):
        required(name)
    expected = fingerprint(required("ANDROID_SIGNING_CERT_SHA256"))
    raw = base64.b64decode("".join(encoded.split()), validate=True)
    if not raw:
        raise ValueError("The signing keystore is empty.")
    directory = Path(required("RUNNER_TEMP")) / "yabause-signing"
    directory.mkdir(mode=0o700, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".keystore", dir=directory)
    keyfile = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        # Binary DER export avoids locale-dependent keytool fingerprint output.
        cert = subprocess.run([
            "keytool", "-exportcert", "-keystore", str(keyfile),
            "-storepass:env", "ANDROID_KEYSTORE_PASSWORD",
            "-alias", required("ANDROID_KEY_ALIAS"),
        ], capture_output=True, check=True).stdout
        if hashlib.sha256(cert).hexdigest() != expected:
            raise ValueError("Signing certificate mismatch. Refusing to change the APK signing identity.")
        version = 100000 + int(required("GITHUB_RUN_NUMBER"))
        if not 100000 < version <= 2100000000:
            raise ValueError("Invalid CI version code.")
        with open(required("GITHUB_ENV"), "a", encoding="utf-8") as stream:
            stream.write(f"ANDROID_KEYSTORE_PATH={keyfile}\nANDROID_VERSION_CODE={version}\n")
        print("Fixed signing certificate verified; CI versionCode:", version)
    except BaseException:
        keyfile.unlink(missing_ok=True)
        raise


def verify():
    expected = fingerprint(required("ANDROID_SIGNING_CERT_SHA256"))
    output = Path("yabause/src/android/app/build/outputs/apk/debug")
    metadata = json.loads((output / "output-metadata.json").read_text())
    package = "org.devmiyax.yabasanshioro2.debug"
    if metadata["applicationId"] != package:
        raise ValueError("APK package name changed; overwrite installation would fail.")
    elements = metadata["elements"]
    if not elements:
        raise ValueError("No APK outputs to verify.")
    report = [f"Package: {package}", f"Certificate SHA-256: {expected}"]
    for element in elements:
        if element["versionCode"] != int(required("ANDROID_VERSION_CODE")):
            raise ValueError("Unexpected APK versionCode.")
        apk = output / element["outputFile"]
        checked = subprocess.run([
            str(Path(required("ANDROID_HOME")) / "build-tools/34.0.0/apksigner"),
            "verify", "--verbose", "--print-certs", str(apk),
        ], capture_output=True, text=True, check=True).stdout
        certs = re.findall(r"^Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)$", checked, re.MULTILINE)
        if [value.lower() for value in certs] != [expected]:
            raise ValueError("Built APK signer does not match the fixed certificate.")
        report.extend([
            f"APK: {apk.name}", f"Version code: {element['versionCode']}",
            f"Version name: {element['versionName']}",
            f"APK SHA-256: {hashlib.sha256(apk.read_bytes()).hexdigest()}",
        ])
    (output / "apk-info.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("All APK signatures, package IDs and version codes verified.")


if __name__ == "__main__":
    try:
        {"prepare": prepare, "verify": verify}[sys.argv[1]]()
    except subprocess.CalledProcessError:
        # Tool diagnostics can contain aliases and paths: do not copy them into CI logs.
        print("::error::Signing tool failed. Check the keystore, passwords and APK signature.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError, IndexError, OSError) as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
