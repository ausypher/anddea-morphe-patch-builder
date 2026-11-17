"""GitHub Releases APK source for the Morphe build pipeline."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from src.core.network import NetworkManager
from src.scrapers.base import AppMetadata, BaseScraper, DownloadResult, ScraperError


class GitHubReleaseError(ScraperError):
    pass


class GitHubReleaseScraper(BaseScraper):
    _ARCHES = ("arm64-v8a", "armeabi-v7a", "arm-v7a", "x86_64", "x86", "all")

    def _release_api_url(self, url: str) -> tuple[str, str]:
        match = re.search(
            r"github\.com/([^/]+)/([^/]+)/releases/tags?/([^/?#]+)",
            url,
            flags=re.IGNORECASE,
        )
        if not match:
            raise GitHubReleaseError(
                "GitHub source URL must point to /releases/tag/<package-name>"
            )
        owner, repo, tag = (unquote(part) for part in match.groups())
        return (
            f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}",
            tag,
        )

    def _release(self, url: str) -> tuple[dict, str]:
        api_url, tag = self._release_api_url(url)
        headers = {"Accept": "application/vnd.github+json", **self.net.gh_headers}
        try:
            data = json.loads(self.net.get(api_url, headers=headers))
        except json.JSONDecodeError as exc:
            raise GitHubReleaseError("GitHub returned invalid release metadata") from exc
        if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
            raise GitHubReleaseError(f"GitHub release was not found: {tag}")
        return data, tag

    @staticmethod
    def _asset_version_arch(name: str, package: str) -> tuple[str, str] | None:
        lowered = name.lower()
        if not lowered.endswith((".apk", ".apkm", ".xapk", ".zip")):
            return None
        stem = name.rsplit(".", 1)[0]
        prefix = f"{package}-"
        if not stem.lower().startswith(prefix.lower()):
            return None

        value = stem[len(prefix):]
        arch = "all"
        for candidate in GitHubReleaseScraper._ARCHES:
            suffix = f"-{candidate}"
            if value.lower().endswith(suffix):
                arch = candidate
                value = value[: -len(suffix)]
                break
        return value, arch

    def fetch_metadata(self, url: str) -> AppMetadata:
        release, tag = self._release(url)
        package = tag
        if not re.fullmatch(r"[\w.]+", package):
            package = str(release.get("name") or "")
        if not package:
            raise GitHubReleaseError("Package name could not be determined from release tag")

        versions: list[str] = []
        for asset in release["assets"]:
            parsed = self._asset_version_arch(str(asset.get("name", "")), package)
            if parsed and parsed[0] not in versions:
                versions.append(parsed[0])
        if not versions:
            raise GitHubReleaseError(f"No APK assets were found in GitHub release {tag}")
        return AppMetadata(pkg_name=package, versions=versions)

    def download(
        self,
        url: str,
        version: str,
        dest: Path,
        arch: str,
        dpi: str,
        version_code: str | None = None,
    ) -> DownloadResult:
        del dpi, version_code
        release, tag = self._release(url)
        package = tag
        if not re.fullmatch(r"[\w.]+", package):
            package = str(release.get("name") or "")
        if not package:
            raise GitHubReleaseError("Package name could not be determined")

        wanted_arch = "armeabi-v7a" if arch == "arm-v7a" else arch
        matches: list[tuple[int, dict, bool]] = []
        for asset in release["assets"]:
            name = str(asset.get("name", ""))
            parsed = self._asset_version_arch(name, package)
            if not parsed or parsed[0] != version:
                continue
            asset_version, asset_arch = parsed
            if asset_arch not in (wanted_arch, "all"):
                continue
            priority = 0 if asset_arch == wanted_arch else 1
            matches.append((priority, asset, name.lower().endswith((".apkm", ".xapk", ".zip"))))

        if not matches:
            raise GitHubReleaseError(
                f"No GitHub asset matches version {version} and architecture {arch}"
            )

        _, asset, is_bundle = sorted(matches, key=lambda item: item[0])[0]
        download_url = str(asset.get("browser_download_url") or "")
        if not download_url:
            raise GitHubReleaseError("Matching GitHub asset has no download URL")

        output = dest.with_suffix(".apkm") if is_bundle else dest
        self.net.download(download_url, output)
        with output.open("rb") as downloaded:
            if downloaded.read(2) != b"PK":
                output.unlink(missing_ok=True)
                raise GitHubReleaseError("GitHub asset is not a valid APK archive")

        return DownloadResult(path=output, is_bundle=is_bundle)
