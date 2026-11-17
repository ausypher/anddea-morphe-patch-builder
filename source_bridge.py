#!/usr/bin/env python3
"""CLI bridge for additional APK sources used by utils.sh."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.core.network import NetworkManager
from src.scrapers.github_release import GitHubReleaseScraper


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: source_bridge.py <github> <metadata|download> URL "
            "[VERSION OUTPUT ARCH DPI]",
            file=sys.stderr,
        )
        return 2

    provider, action, url = sys.argv[1:4]
    scrapers = {
        "github": GitHubReleaseScraper,
    }
    scraper_type = scrapers.get(provider)
    if scraper_type is None:
        print(f"Unknown APK source: {provider}", file=sys.stderr)
        return 2

    try:
        with NetworkManager() as net:
            scraper = scraper_type(net)
            if action == "metadata":
                metadata = scraper.fetch_metadata(url)
                print(json.dumps({
                    "pkg_name": metadata.pkg_name,
                    "versions": metadata.versions,
                }))
                return 0

            if action == "download":
                if len(sys.argv) != 8:
                    print(
                        "download requires URL VERSION OUTPUT ARCH DPI",
                        file=sys.stderr,
                    )
                    return 2
                _, _, _, _, version, output, arch, dpi = sys.argv
                result = scraper.download(
                    url, version, Path(output), arch, dpi
                )
                print(json.dumps({
                    "path": str(result.path),
                    "is_bundle": result.is_bundle,
                }))
                return 0

            print(f"Unknown action: {action}", file=sys.stderr)
            return 2
    except Exception as exc:
        print(
            f"{provider} source error: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
