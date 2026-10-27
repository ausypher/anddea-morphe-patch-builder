# Anddea Morphe Patch Builder

A customized Morphe patch builder that uses **patches maintained by Anddea** and builds separate development (dev) and stable releases of YouTube and YouTube Music.

## APK sources

This project uses the APK acquisition approach from [nvbangg/builder-for-morphe](https://github.com/nvbangg/builder-for-morphe) for **APKMirror**. The relevant Python scraper and bridge components were adapted from that project to retrieve app metadata and download APKs from APKMirror.

The configured source priority is:

1. **Direct** — try the direct source first.
2. **APKMirror** — use the APKMirror scraper/bridge.
3. **Archive** — fall back to the archive source if the earlier sources fail.

APKMirror access may be affected by the website's anti-bot protection, so the archive fallback is retained.

## Patch source

Patches used for builds are maintained by [Anddea](https://github.com/anddea) in the [Anddea ReVanced patches repository](https://github.com/anddea/revanced-patches). This builder also uses Morphe desktop tooling to apply the selected patches.

## Releases

- **Stable releases** are published as regular GitHub releases.
- **Dev releases** are published as GitHub pre-releases and use the `dev-` prefix for APK assets.

Browse the [latest releases](https://github.com/ausypher/anddea-morphe-patch-builder/releases).

## Build workflow

GitHub Actions prepares, builds, and publishes the selected channel. Development and stable builds use separate configurations and release/update paths.

