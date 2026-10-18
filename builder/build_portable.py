#!/usr/bin/env python3
"""Build a GitHub Desktop portable package from an official full NuGet release.

Safe defaults: stable exact version, published upstream asset, GitHub API sha256,
and no writes to an existing user Data directory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import urllib.error
import urllib.request
import zipfile

UPSTREAM = "desktop/desktop"
# Published official 3.6.7 Windows x64 SHA-256 (from GitHub release-3.6.7 asset list).
PINNED_SHA256 = {("3.6.7", "x64"): "9790523cad902da2bb695e29125bf0b97142834df9d0434bb5dedbf0705ca9a3"}


def api_json(url: str, token: str | None = None) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "GitHubDesktopPortableBuilder/1.0", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def select_asset(release: dict, version: str, architecture: str) -> dict:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Only numeric stable versions are supported, e.g. 3.6.7")
    if architecture not in ("x64", "arm64"):
        raise ValueError("Architecture must be x64 or arm64")
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != "release-" + version:
        raise ValueError("Release is missing, draft, prerelease, or version does not match")
    expected_name = f"GitHubDesktop-{version}-{architecture}-full.nupkg"
    assets = [a for a in release.get("assets", []) if a.get("name") == expected_name]
    if len(assets) != 1:
        raise ValueError(f"Expected exactly one official {expected_name} release asset; found {len(assets)}")
    asset = assets[0]
    pinned = PINNED_SHA256.get((version, architecture))
    digest = asset.get("digest") or ("sha256:" + pinned if pinned else "")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError(f"No official GitHub API SHA-256 digest for {expected_name}; refusing unverified download")
    if pinned and digest.split(":", 1)[1].lower() != pinned:
        raise ValueError("Published GitHub asset checksum changed unexpectedly; stopping for review")
    asset = dict(asset, digest=digest)
    if not asset.get("browser_download_url", "").startswith("https://github.com/desktop/desktop/releases/download/"):
        raise ValueError("Unexpected release asset URL")
    return asset


def download_verified(asset: dict, destination: Path, token: str | None = None) -> None:
    url = asset["browser_download_url"]
    headers = {"User-Agent": "GitHubDesktopPortableBuilder/1.0", "Accept": "application/octet-stream"}
    # Public release assets do not require token, avoids auth header across redirects.
    req = urllib.request.Request(url, headers=headers)
    h = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(req, timeout=120) as resp, destination.open("wb") as dst:
        while True:
            data = resp.read(1024 * 1024)
            if not data:
                break
            h.update(data)
            dst.write(data)
            total += len(data)
    got = h.hexdigest()
    expected = asset["digest"].split(":", 1)[1].lower()
    if got != expected:
        destination.unlink(missing_ok=True)
        raise ValueError(f"Official release SHA-256 mismatch: expected {expected}, got {got}")
    if asset.get("size") and total != asset["size"]:
        raise ValueError(f"Release package size mismatch: expected {asset['size']}, got {total}")
    print(f"Verified {destination.name}: SHA-256 {got}, {total} bytes")


def extract_app(package: Path, app_path: Path) -> None:
    app_path.mkdir(parents=True, exist_ok=True)
    root = "lib/net45/"
    with zipfile.ZipFile(package) as z:
        files = [item for item in z.infolist() if item.filename.startswith(root) and not item.is_dir()]
        if not files:
            raise ValueError("No lib/net45 folder in official Windows full NuGet package")
        for item in files:
            name = item.filename[len(root):]
            rel = PurePosixPath(name)
            if not name or rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name:
                raise ValueError(f"Unsafe file path in NuGet package: {item.filename}")
            target = app_path.joinpath(*rel.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as inp, target.open("wb") as out:
                shutil.copyfileobj(inp, out)
    exe = app_path / "GitHubDesktop.exe"
    if not exe.is_file():
        raise RuntimeError("Missing GitHubDesktop.exe after extraction")
    if not (app_path / 'resources').is_dir():
        raise RuntimeError("Missing resources folder in extracted GitHub Desktop app")
    print(f"Extracted official Windows application into {app_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="3.6.7")
    parser.add_argument("--architecture", choices=["x64", "arm64"], default="x64")
    parser.add_argument("--output", default="stage/GitHubDesktopPortable")
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists():
        raise RuntimeError(f"Destination already exists; refusing to overwrite: {out}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        raise ValueError("Use an official stable version like 3.6.7")
    token = os.environ.get("GITHUB_TOKEN")
    release = api_json(f"https://api.github.com/repos/{UPSTREAM}/releases/tags/release-{args.version}", token)
    asset = select_asset(release, args.version, args.architecture)
    out.mkdir(parents=True)
    package = out.parent / asset["name"]
    try:
        download_verified(asset, package, token)
        extract_app(package, out / "App" / "GitHubDesktop")
    finally:
        package.unlink(missing_ok=True)
    for folder in ("Data/Roaming", "Data/Local", "Data/Home", "Data/Git", "Data/Repositories", "Data/Temp", "Data/Cache", "Other/Source"):
        (out / folder).mkdir(parents=True, exist_ok=True)
    (out / "Data" / "README.txt").write_text("KEEP THIS DATA FOLDER during every application update. It stores portable settings, local Git config, caches and optional cloned repositories.\n", encoding="utf-8")
    # Preserve upstream license and trademark notice with this community repack.
    license_url = f"https://raw.githubusercontent.com/desktop/desktop/release-{args.version}/LICENSE"
    license_req = urllib.request.Request(license_url, headers={"User-Agent": "GitHubDesktopPortableBuilder/1.0"})
    with urllib.request.urlopen(license_req, timeout=60) as response:
        license_text = response.read().decode("utf-8")
    if "MIT License" not in license_text and "Permission is hereby granted" not in license_text:
        raise RuntimeError("Upstream license content unexpected; refusing distribution")
    (out / "Other" / "Source" / "LICENSE.txt").write_text(license_text, encoding="utf-8")
    (out / "Other" / "Source" / "build-info.txt").write_text(f"Source: https://github.com/desktop/desktop/releases/tag/release-{args.version}\nAsset: {asset['name']}\nSHA-256: {asset['digest']}\nArchitecture: {args.architecture}\nCommunity portable repack; not endorsed by GitHub.\n", encoding="utf-8")
    print(f"Staging ready at {out}; compile launcher then package it")


if __name__ == "__main__":
    main()
