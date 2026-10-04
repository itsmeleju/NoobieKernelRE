#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPOS = {
    "ZyCromerZ": "ZyCromerZ/Clang",
    "Neutron": "Neutron-Toolchains/clang-build-catalogue",
}

ARCHIVES = (".tar.gz", ".tar.xz", ".tar.zst", ".tar", ".zip")

def die(message):
    print(f"::error::{message}")
    raise SystemExit(1)

def api(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "NoobieKernelRE-setup-clang",
        },
    )
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        die(f"GitHub API request failed: HTTP {exc.code} for {url}")
    except urllib.error.URLError as exc:
        die(f"GitHub API request failed: {exc.reason}")


def resolve(toolchain, requested):
    if toolchain not in REPOS:
        die(
            f"Unsupported toolchain: {toolchain}. "
            "Use ZyCromerZ or Neutron."
        )

    repo = REPOS[toolchain]

    if requested:
        url = (
            f"https://api.github.com/repos/{repo}/"
            f"releases/tags/{requested}"
        )
    else:
        url = f"https://api.github.com/repos/{repo}/releases/latest"

    data = api(url)

    version = str(data.get("tag_name", "")).strip()
    if not version:
        die(f"GitHub returned no release tag for {toolchain}.")

    assets = data.get("assets") or []
    if not assets:
        die(
            f"No release assets found for "
            f"{toolchain} release {version}."
        )

    candidates = []

    for asset in assets:
        name = str(asset.get("name", ""))
        lower = name.lower()

        if (
            any(lower.endswith(ext) for ext in ARCHIVES)
            and "source" not in lower
        ):
            candidates.append(asset)

    if not candidates:
        die(
            f"No usable archive asset found for "
            f"{toolchain} release {version}."
        )

    candidates.sort(
        key=lambda asset: (
            "clang" not in asset.get("name", "").lower(),
            "toolchain" not in asset.get("name", "").lower(),
            len(asset.get("name", "")),
        )
    )

    return data, candidates[0]


def sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def download(url, destination, expected_digest):
    print(f"[Clang] Download URL: {url}")
    print(f"[Clang] Archive: {destination.name}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NoobieKernelRE-setup-clang",
        },
    )

    try:
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            destination.open("wb") as output,
        ):
            if response.status != 200:
                die(
                    f"Toolchain download returned "
                    f"HTTP {response.status}."
                )

            shutil.copyfileobj(
                response,
                output,
                1024 * 1024,
            )

    except urllib.error.HTTPError as exc:
        die(
            f"Toolchain download failed: "
            f"HTTP {exc.code} for {url}"
        )
    except urllib.error.URLError as exc:
        die(
            f"Toolchain download failed: "
            f"{exc.reason}"
        )

    if not destination.is_file():
        die(f"Downloaded archive does not exist: {destination}")

    if destination.stat().st_size == 0:
        die(f"Downloaded archive is empty: {destination}")

    actual = sha256(destination)

    print(f"[Clang] Downloaded archive SHA256: {actual}")

    if expected_digest:
        expected = expected_digest.split(":", 1)[-1].strip()

        if actual.lower() != expected.lower():
            die(
                "Archive SHA256 mismatch: "
                f"expected {expected}, got {actual}"
            )

        print(
            "[Clang] Archive SHA256 verified "
            "against GitHub release metadata."
        )


def safe_member_path(root, name):
    root = root.resolve()
    target = (root / name).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        die(f"Unsafe archive path rejected: {name}")

    return target


def extract(archive, destination):
    if destination.exists():
        shutil.rmtree(destination)

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        if archive.name.lower().endswith(".zip"):
            with zipfile.ZipFile(archive) as archive_file:
                bad = archive_file.testzip()

                if bad:
                    die(f"Corrupt ZIP member: {bad}")

                for member in archive_file.infolist():
                    safe_member_path(
                        destination,
                        member.filename,
                    )

                archive_file.extractall(destination)

            return

        with tarfile.open(archive, "r:*") as tar:
            for member in tar.getmembers():
                safe_member_path(
                    destination,
                    member.name,
                )

                if member.issym() or member.islnk():
                    link_target = Path(member.linkname)

                    if link_target.is_absolute():
                        die(
                            "Unsafe absolute symlink rejected: "
                            f"{member.name}"
                        )

                    link_parent = (
                        destination / member.name
                    ).parent.resolve()

                    link_path = (
                        link_parent / link_target
                    ).resolve()

                    try:
                        link_path.relative_to(destination.resolve())
                    except ValueError:
                        die(
                            "Unsafe symlink escaping archive "
                            f"root rejected: {member.name}"
                        )

            tar.extractall(destination)

    except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
        die(
            f"Toolchain archive extraction failed: {exc}"
        )


def find_bin(root):
    root = root.resolve()
    matches = []

    for path in root.rglob("clang"):
        if not path.is_file():
            continue

        if not os.access(path, os.X_OK):
            continue

        if path.parent.name != "bin":
            continue

        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue

        matches.append(path.parent)

    if not matches:
        die(
            "Extracted toolchain does not contain an "
            f"executable clang under a bin directory: {root}"
        )

    matches.sort(
        key=lambda path: (
            len(path.parts),
            str(path),
        )
    )

    return matches[0]


def verify(bin_dir):
    required = (
        "clang",
        "clang++",
        "llvm-ar",
        "llvm-nm",
        "llvm-objcopy",
        "llvm-objdump",
        "llvm-readelf",
        "llvm-size",
        "llvm-strip",
    )

    for name in required:
        path = bin_dir / name

        if not path.is_file():
            die(
                f"Required LLVM binary is missing: {path}"
            )

    linker = None

    for name in ("ld.lld", "ld"):
        candidate = bin_dir / name

        if candidate.is_file():
            linker = candidate
            break

    if linker is None:
        die(
            f"Required linker is missing from {bin_dir}: "
            "expected ld.lld or ld"
        )

    try:
        version = subprocess.check_output(
            [
                str(bin_dir / "clang"),
                "--version",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        die(f"clang --version failed: {exc}")

    print("[Clang] clang --version:")
    print(version.strip())
    print(f"[Clang] LLVM bin: {bin_dir}")
    print(f"[Clang] Linker: {linker.name}")

    return version.strip()


def write_output(name, value):
    output = os.environ.get("GITHUB_OUTPUT", "")

    if not output:
        return

    with open(output, "a", encoding="utf-8") as stream:
        stream.write(f"{name}={value}\n")


def main():
    toolchain = os.environ.get("TOOLCHAIN", "").strip()
    requested = os.environ.get(
        "VERSION_CLANG",
        "",
    ).strip()

    root_value = os.environ.get(
        "TOOLCHAIN_ROOT",
        "",
    ).strip()

    if not root_value:
        die("TOOLCHAIN_ROOT is not set.")

    if not toolchain:
        die("TOOLCHAIN is not set.")

    root = Path(root_value).resolve()

    data, asset = resolve(
        toolchain,
        requested,
    )

    version = str(
        data.get("tag_name", "")
    ).strip()

    if not version:
        die("Selected Clang release has no tag.")

    install = (
        root
        / toolchain
        / version
    )

    marker = install / ".noobie-complete"

    print(f"[Clang] Toolchain: {toolchain}")
    print(f"[Clang] Selected release: {version}")
    print(
        f"[Clang] Release page: "
        f"{data.get('html_url', '')}"
    )
    print(f"[Clang] Installation path: {install}")

    bin_dir = None

    if marker.is_file():
        try:
            bin_dir = find_bin(install)
            verify(bin_dir)

            print(
                "[Clang] Verified cached toolchain "
                "will be reused."
            )
        except SystemExit:
            raise
        except Exception as exc:
            print(
                "[Clang] Cached toolchain verification "
                f"failed: {exc}"
            )

            shutil.rmtree(
                install,
                ignore_errors=True,
            )

            bin_dir = None

    if bin_dir is None:
        archive = (
            Path(tempfile.gettempdir())
            / asset["name"]
        )

        extract_dir = Path(
            tempfile.mkdtemp(
                prefix="noobie-clang-"
            )
        )

        try:
            archive.unlink(missing_ok=True)

            download(
                asset["browser_download_url"],
                archive,
                asset.get("digest", ""),
            )

            extract(
                archive,
                extract_dir,
            )

            source_bin = find_bin(
                extract_dir
            )

            source_root = source_bin.parent.resolve()

            try:
                source_root.relative_to(
                    extract_dir.resolve()
                )
            except ValueError:
                die(
                    "Clang extraction path escaped "
                    "the temporary extraction directory."
                )

            if source_root == Path("/"):
                die(
                    "Refusing to copy invalid "
                    "Clang extraction root."
                )

            if install.exists():
                shutil.rmtree(
                    install,
                    ignore_errors=True,
                )

            install.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copytree(
                source_root,
                install,
                symlinks=True,
                dirs_exist_ok=False,
            )

            bin_dir = find_bin(install)
            verify(bin_dir)

            marker.write_text(
                f"version={version}\n"
                f"clang_path={bin_dir}\n",
                encoding="utf-8",
            )

        finally:
            shutil.rmtree(
                extract_dir,
                ignore_errors=True,
            )
            archive.unlink(
                missing_ok=True
            )

    print(
        f"[Clang] Installation verified: "
        f"{install}"
    )

    github_path = os.environ.get(
        "GITHUB_PATH",
        "",
    )

    if github_path:
        with open(
            github_path,
            "a",
            encoding="utf-8",
        ) as stream:
            stream.write(f"{bin_dir}\n")

    github_env = os.environ.get(
        "GITHUB_ENV",
        "",
    )

    if github_env:
        with open(
            github_env,
            "a",
            encoding="utf-8",
        ) as stream:
            stream.write("LLVM=1\n")
            stream.write("LLVM_IAS=0\n")

    write_output(
        "version",
        version,
    )
    write_output(
        "clang_path",
        str(bin_dir),
    )


if __name__ == "__main__":
    main()
