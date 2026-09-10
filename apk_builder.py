#!/usr/bin/env python3
"""Build a real installable .apk (WebView wrapper) from user HTML without Java.

Uses prebuilt amd64 linux build-tools (aapt + zipalign) committed under apk_tools/,
the WebView classes.dex, and signs with a pure-python v1 (JAR) signer built on
`cryptography`. No JDK / apksigner is required at runtime.
"""
import base64
import datetime
import hashlib
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
import zlib

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apk_tools")

TOOLS = {
    "aapt": os.path.join(TOOLS_DIR, "aapt"),
    "zipalign": os.path.join(TOOLS_DIR, "zipalign"),
    "framework": os.path.join(TOOLS_DIR, "android-framework.jar"),
    "dex": os.path.join(TOOLS_DIR, "classes.dex"),
    "cert": os.path.join(TOOLS_DIR, "signing_cert.pem"),
    "key": os.path.join(TOOLS_DIR, "signing_key.pem"),
    "icon": os.path.join(TOOLS_DIR, "default_icon.png"),
}

MODULE_LOGGER = None


def set_logger(logger):
    global MODULE_LOGGER
    MODULE_LOGGER = logger


def _log(msg, exc_info=False):
    if MODULE_LOGGER:
        MODULE_LOGGER.error(msg, exc_info=exc_info)


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def png_bytes(width, height, rgb):
    """Minimal valid PNG encoder (no third-party deps)."""
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def build_manifest(entries):
    main = b"Manifest-Version: 1.0\r\n\r\n"
    parts = [main]
    for name in entries:
        parts.append(("Name: %s\r\n" % name).encode("utf-8"))
        parts.append(b"SHA-256-Digest: " + _b64(hashlib.sha256(entries[name]).digest()).encode("ascii") + b"\r\n\r\n")
    return b"".join(parts)


def build_sf(manifest_bytes):
    mh = hashlib.sha256(manifest_bytes).digest()
    sf = (
        b"Signature-Version: 1.0\r\n"
        b"Created-By: 1.0 (Hosting2X)\r\n"
        b"SHA-256-Digest-Manifest: " + _b64(mh).encode("ascii") + b"\r\n\r\n"
    )
    lines = manifest_bytes.split(b"\r\n")
    i = 0
    while i < len(lines):
        if lines[i].startswith(b"Name: "):
            block = [lines[i]]
            j = i + 1
            while j < len(lines) and lines[j] != b"":
                block.append(lines[j]); j += 1
            block.append(b"")
            sec = b"\r\n".join(block) + b"\r\n"
            sf += b"Name: " + block[0][6:] + b"\r\n"
            sf += b"SHA-256-Digest: " + _b64(hashlib.sha256(sec).digest()).encode("ascii") + b"\r\n\r\n"
            i = j + 1
        else:
            i += 1
    return sf


def _pkcs7(cert, key, signed_bytes):
    from cryptography.hazmat.primitives.serialization import pkcs7 as p7
    builder = (
        p7.PKCS7SignatureBuilder()
        .set_data(signed_bytes)
        .add_signer(cert, key, hashes.SHA256())
        .add_certificate(cert)
    )
    return builder.sign(serialization.Encoding.DER, [p7.PKCS7Options.NoAttributes])


def sign_apk(pairs, cert, key, out_path, signer_name="CERT"):
    """pairs: list of (filename, bytes) in desired zip order (excluding META-INF)."""
    names = [n for n, _ in pairs]
    entries = {n: b for n, b in pairs}
    names.sort()
    manifest = build_manifest(entries)
    sf = build_sf(manifest)
    rsa = _pkcs7(cert, key, sf)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zout:
        zout.writestr("META-INF/MANIFEST.MF", manifest)
        zout.writestr("META-INF/" + signer_name + ".SF", sf)
        zout.writestr("META-INF/" + signer_name + ".RSA", rsa)
        for n in names:
            zout.writestr(n, entries[n])
    return out_path


def _pkg_from_user(user_id, app_name):
    raw = f"{user_id}:{app_name}".encode("utf-8")
    tag = hashlib.md5(raw).hexdigest()[:10]
    return f"com.hosting2x.app{tag}"


def _xml_escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def _write_mipmap(res_dir, png_data):
    for d in ("mipmap", "mipmap-hdpi", "mipmap-mdpi"):
        dpath = os.path.join(res_dir, d)
        os.makedirs(dpath, exist_ok=True)
        with open(os.path.join(dpath, "ic_launcher.png"), "wb") as f:
            f.write(png_data)


def _pick_icon(logo_bytes, has_pil):
    if logo_bytes and logo_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return logo_bytes
    if logo_bytes:
        try:
            if has_pil:
                from PIL import Image
                import io
                im = Image.open(io.BytesIO(logo_bytes))
                if im.mode not in ("RGBA", "RGB"):
                    im = im.convert("RGBA")
                im.thumbnail((192, 192), Image.LANCZOS)
                bg = Image.new("RGBA", im.size, (0, 0, 0, 0))
                if im.mode == "RGBA":
                    bg.paste(im, (0, 0), im)
                else:
                    bg = im.convert("RGBA")
                buf = io.BytesIO()
                bg.save(buf, "PNG")
                return buf.getvalue()
        except Exception as e:
            _log(f"icon pil convert failed: {e}")
    if os.path.exists(TOOLS["icon"]):
        with open(TOOLS["icon"], "rb") as f:
            return f.read()
    return png_bytes(192, 192, (16, 16, 24))


def _sanitize_label(name):
    label = "".join(ch for ch in str(name) if ch.isalnum() or ch in " ._-")
    return label[:40] or "Hosting2X"


def build_webview_apk(html, logo_bytes, user_id, app_name, out_path, asset_dir=None):
    """Build real APK from raw html + optional logo.
    If asset_dir is given, all its files are copied into assets/ (multi-file sites)."""
    for t in TOOLS.values():
        if not os.path.exists(t):
            _log(f"missing apk tool: {t}")
            return None
    has_pil = False
    try:
        from PIL import Image
        has_pil = Image is not None
    except Exception:
        has_pil = False
    pkg = _pkg_from_user(user_id, app_name)
    label = _xml_escape(_sanitize_label(app_name))
    icon = _pick_icon(logo_bytes, has_pil)
    work = tempfile.mkdtemp(prefix="h2xapk_")
    try:
        res_dir = os.path.join(work, "res")
        values_dir = os.path.join(res_dir, "values")
        os.makedirs(values_dir, exist_ok=True)
        with open(os.path.join(values_dir, "strings.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                    '<resources>\n'
                    f'  <string name="app_name">{label}</string>\n'
                    '</resources>\n')
        _write_mipmap(res_dir, icon)
        assets_dir = os.path.join(work, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        if asset_dir and os.path.isdir(asset_dir):
            for root2, _dirs, files2 in os.walk(asset_dir):
                for fn2 in files2:
                    full = os.path.join(root2, fn2)
                    rel = os.path.relpath(full, asset_dir)
                    dst = os.path.join(assets_dir, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(full, dst)
        with open(os.path.join(assets_dir, "index.html"), "wb") as f:
            f.write(html.encode("utf-8", "ignore") if isinstance(html, str) else html)
        manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg}" android:versionCode="1" android:versionName="1.0">
  <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="29" />
  <uses-permission android:name="android.permission.INTERNET" />
  <application
      android:label="@string/app_name"
      android:icon="@mipmap/ic_launcher"
      android:hardwareAccelerated="true"
      android:usesCleartextTraffic="true">
    <activity android:name="com.hosting2x.webapp.MainActivity" android:exported="true"
        android:configChanges="orientation|screenSize|keyboardHidden">
      <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
      </intent-filter>
    </activity>
  </application>
</manifest>
'''
        with open(os.path.join(work, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
            f.write(manifest)
        base_apk = os.path.join(work, "base.apk")
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = TOOLS_DIR + ":" + env.get("LD_LIBRARY_PATH", "")
        r = subprocess.run(
            [TOOLS["aapt"], "package", "-f", "-M", os.path.join(work, "AndroidManifest.xml"),
             "-S", res_dir, "-A", assets_dir, "-I", TOOLS["framework"], "-F", base_apk],
            capture_output=True, text=True, env=env, timeout=120,
        )
        if r.returncode != 0:
            _log(f"aapt failed: {r.stderr[:800]}")
            return None
        raw_pairs = []
        with zipfile.ZipFile(base_apk) as z:
            for i in z.infolist():
                if not i.filename.startswith("META-INF/"):
                    raw_pairs.append((i.filename, z.read(i.filename)))
        raw_pairs.append(("classes.dex", open(TOOLS["dex"], "rb").read()))
        unaligned = os.path.join(work, "unaligned.apk")
        cert = x509.load_pem_x509_certificate(open(TOOLS["cert"], "rb").read())
        key = serialization.load_pem_private_key(open(TOOLS["key"], "rb").read(), password=None)
        sign_apk(raw_pairs, cert, key, unaligned)
        r = subprocess.run([TOOLS["zipalign"], "-f", "4", unaligned, out_path],
                           capture_output=True, text=True, env=env, timeout=60)
        if r.returncode != 0:
            _log(f"zipalign failed: {r.stderr[:400]}")
            return None
        return out_path
    except Exception as e:
        _log(f"apk build exception: {e}", exc_info=True)
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)