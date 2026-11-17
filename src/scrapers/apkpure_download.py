#!/usr/bin/env python3
"""Download a version-pinned single APK from APKPure.net.

This resolver is intentionally download-only: the build pipeline obtains the
expected package/version from its configured metadata source, and the central
signature check remains responsible for accepting or rejecting the file.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from curl_cffi import requests

SLUGS = {
    "com.google.android.youtube": "youtube",
    "com.google.android.apps.youtube.music": "youtube-music",
}


def main() -> int:
    if len(sys.argv) != 5:
        print("Usage: apkpure-dl.py PACKAGE VERSION ARCH OUTPUT", file=sys.stderr)
        return 2

    package, version, _arch, output = sys.argv[1:]
    slug = SLUGS.get(package)
    if not slug:
        print(f"APKPure: no app slug mapping for {package}", file=sys.stderr)
        return 1

    session = requests.Session(impersonate="chrome", timeout=120)
    page_url = f"https://apkpure.net/{slug}/{package}/download/{version}"
    try:
        page = session.get(page_url, headers={"Referer": "https://apkpure.net/"})
        if page.status_code != 200:
            raise RuntimeError(f"download page returned HTTP {page.status_code}")

        match = re.search(r'id="download_link"[^>]*href="([^"]+)"', page.text)
        if not match:
            match = re.search(
                r'href="(https?://d[.]apkpure[.]net/b/APK/[^"]+)"',
                page.text,
            )
        if not match:
            raise RuntimeError("no direct base-APK link found (possibly XAPK-only)")
        download_url = html.unescape(match.group(1))
        if "/b/XAPK/" in download_url:
            raise RuntimeError("APKPure resolved an XAPK bundle; refusing it")

        response = session.get(
            download_url,
            headers={"Referer": page_url},
            stream=True,
        )
        if response.status_code != 200:
            raise RuntimeError(f"APK download returned HTTP {response.status_code}")

        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with destination.open("wb") as stream:
            for chunk in response.iter_content(1 << 16):
                if chunk:
                    stream.write(chunk)
                    size += len(chunk)
        if size == 0:
            destination.unlink(missing_ok=True)
            raise RuntimeError("downloaded file is empty")
        with destination.open("rb") as downloaded:
            if downloaded.read(2) != b"PK":
                destination.unlink(missing_ok=True)
                raise RuntimeError("download response is not a ZIP/APK archive")

        print(f"APKPure downloaded {package} {version}: {size} bytes", file=sys.stderr)
        return 0
    except Exception as exc:
        Path(output).unlink(missing_ok=True)
        print(f"APKPure error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
