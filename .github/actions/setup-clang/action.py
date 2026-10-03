#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

DEFAULTS = {
    "ZyCromerZ": ("ZyCromerZ", "Clang-16.0.6-20260510-release"),
    "Neutron": ("Neutron-Toolchains", "06092026"),
}
REPOS = {
    "ZyCromerZ": "ZyCromerZ/Clang",
    "Neutron": "Neutron-Toolchains/clang-build-catalogue",
}
ARCHIVES = (".tar.gz", ".tar.xz", ".tar.zst", ".tar", ".zip")

def die(message):
    print(f"::error::{message}")
    raise SystemExit(1)

def api(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "NoobieKernelRE-setup-clang",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        die(f"GitHub API request failed: HTTP {exc.code} for {url}")
    except urllib.error.URLError as exc:
        die(f"GitHub API request failed: {exc.reason}")

def resolve(toolchain, requested):
    if toolchain not in REPOS:
        die(f"Unsupported toolchain: {toolchain}. Use ZyCromerZ or Neutron.")
    default_version = DEFAULTS[toolchain][1]
    version = requested or default_version
    repo = REPOS[toolchain]
    if requested:
        data = api(f"https://api.github.com/repos/{repo}/releases/tags/{requested}")
    else:
        data = api(f"https://api.github.com/repos/{repo}/releases/tags/{version}")
    if not data.get("assets"):
        die(f"No release assets found for {toolchain} release {version}.")
    candidates = []
    for asset in data["assets"]:
        name = asset.get("name", "")
        lower = name.lower()
        if any(lower.endswith(ext) for ext in ARCHIVES) and "source" not in lower:
            candidates.append(asset)
    if not candidates:
        die(f"No usable archive asset found for {toolchain} release {data.get('tag_name', version)}.")
    candidates.sort(key=lambda a: (
        "clang" not in a.get("name", "").lower(),
        "toolchain" not in a.get("name", "").lower(),
        len(a.get("name", "")),
    ))
    asset = candidates[0]
    return data, asset

def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url, destination, expected_digest):
    print(f"[Clang] Download URL: {url}")
    print(f"[Clang] Archive: {destination.name}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NoobieKernelRE-setup-clang"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response, destination.open("wb") as out:
            if response.status != 200:
                die(f"Toolchain download returned HTTP {response.status}.")
            shutil.copyfileobj(response, out, 1024 * 1024)
    except urllib.error.HTTPError as exc:
        die(f"Toolchain download failed: HTTP {exc.code} for {url}")
    except urllib.error.URLError as exc:
        die(f"Toolchain download failed: {exc.reason}")
    if not destination.is_file() or destination.stat().st_size == 0:
        die(f"Downloaded archive is empty: {destination}")
    actual = sha256(destination)
    print(f"[Clang] Downloaded archive SHA256: {actual}")
    if expected_digest:
        expected = expected_digest.split(":", 1)[-1]
        if actual.lower() != expected.lower():
            die(f"Archive SHA256 mismatch: expected {expected}, got {actual}")
        print("[Clang] Archive SHA256 verified against GitHub release metadata.")

def extract(archive, destination):
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    try:
        if archive.name.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(archive) as z:
                bad = z.testzip()
                if bad:
                    die(f"Corrupt ZIP member: {bad}")
                z.extractall(destination)
        else:
            with tarfile.open(archive, "r:*") as t:
                t.extractall(destination, filter="data")
    except (tarfile.TarError, OSError, ValueError) as exc:
        die(f"Toolchain archive extraction failed: {exc}")

def find_bin(root):
    matches = []
    for path in root.rglob("clang"):
        if path.is_file() and os.access(path, os.X_OK) and path.parent.name == "bin":
            matches.append(path.parent)
    if not matches:
        die(f"Extracted toolchain does not contain an executable clang under a bin directory: {root}")
    return sorted(matches, key=lambda p: len(str(p)))[0]

def verify(bin_dir):
    required = ("clang", "llvm-ar", "llvm-nm", "llvm-objcopy", "llvm-strip")
    for name in required:
        if not (bin_dir / name).is_file():
            die(f"Required LLVM binary is missing: {bin_dir / name}")
    if not ((bin_dir / "ld.lld").is_file() or (bin_dir / "ld").is_file()):
        die(f"Required linker is missing from {bin_dir}: expected ld.lld or ld")
    try:
        version = subprocess.check_output(
            [str(bin_dir / "clang"), "--version"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"clang --version failed: {exc}")
    print("[Clang] clang --version:")
    print(version.strip())
    print(f"[Clang] LLVM bin: {bin_dir}")

def main():
    toolchain = os.environ.get("TOOLCHAIN", "")
    requested = os.environ.get("VERSION_CLANG", "").strip()
    root = Path(os.environ.get("TOOLCHAIN_ROOT", "")).resolve()
    if not root:
        die("TOOLCHAIN_ROOT is not set.")
    data, asset = resolve(toolchain, requested)
    version = data["tag_name"]
    install = root / toolchain / version
    complete = install / ".noobie-complete"
    print(f"[Clang] Toolchain: {toolchain}")
    print(f"[Clang] Selected release: {version}")
    print(f"[Clang] Release page: {data.get('html_url', '')}")
    print(f"[Clang] Installation path: {install}")
    install.mkdir(parents=True, exist_ok=True)

    bin_dir = None
    if complete.is_file():
        try:
            bin_dir = find_bin(install)
            verify(bin_dir)
            print("[Clang] Cache hit: existing verified toolchain will be reused.")
        except SystemExit:
            raise
        except Exception:
            bin_dir = None

    if bin_dir is None:
        archive = Path(tempfile.gettempdir()) / asset["name"]
        if archive.exists():
            archive.unlink()
        download(asset["browser_download_url"], archive, asset.get("digest", ""))
        extract_dir = Path(tempfile.mkdtemp(prefix="noobie-clang-"))
        try:
            extract(archive, extract_dir)
            source_bin = find_bin(extract_dir)
            if install.exists():
                shutil.rmtree(install)
            shutil.copytree(source_bin.parent.parent, install)
            bin_dir = find_bin(install)
            verify(bin_dir)
            complete.touch()
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
            archive.unlink(missing_ok=True)

    print(f"[Clang] Installation verified: {install}")
    github_env = os.environ.get("GITHUB_ENV")
    github_path = os.environ.get("GITHUB_PATH")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_path:
        with open(github_path, "a", encoding="utf-8") as f:
            f.write(f"{bin_dir}\n")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write("LLVM=1\nLLVM_IAS=0\n")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"version={version}\n")
            f.write(f"clang_path={bin_dir}\n")

if __name__ == "__main__":
    main()
