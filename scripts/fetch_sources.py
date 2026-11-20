#!/usr/bin/env python3
"""Fetch exact upstream source snapshots without Git remotes/submodules.

Only Python's standard library is used. Does not build, execute, or include ROMs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL = ROOT / "external"
LOCAL = ROOT / "local"
SNAPSHOTS = LOCAL / "source-archives"
MANIFEST = ROOT / "SOURCE_MANIFEST.json"

SOURCES = {
    "3dsrecomp": {
        "repo": "https://github.com/fearkov/3dsrecomp",
        "commit": "4b6de5d884b0d8bc337e16c07b84a0824e55a0e1",
        "date": "2026-11-17T02:54:33Z",
    },
    "zakuro": {
        "repo": "https://github.com/fearkov/zakuro",
        "commit": "fdf67b29b6398a7ad0dc2309b09ea4c03c45e9d8",
        "date": "2026-11-17T03:35:30Z",
    },
}

# IMPORTANT: These three workspace dependencies must be LOCAL. Paths are
# relative to the Cargo.toml defining the dependency, not the project root.
DEPENDENCY_REWRITES = [
    ("3dsrecomp/Cargo.toml", "zakuro-cpu", "https://github.com/fearkov/zakuro", "../zakuro/crates/zakuro-cpu"),
    ("zakuro/Cargo.toml", "recomp-abi", "https://github.com/fearkov/3dsrecomp", "../3dsrecomp/abi"),
    ("zakuro/crates/zakuro/Cargo.toml", "recomp3ds", "https://github.com/fearkov/3dsrecomp", "../../../3dsrecomp"),
]


def die(message: str) -> None:
    raise RuntimeError(message)


def source_archive(name: str, info: dict[str, str]) -> Path:
    sha = info["commit"]
    return SNAPSHOTS / f"{name}-{sha}.zip"


def fetch_archive(name: str, info: dict[str, str]) -> tuple[Path, str]:
    archive = source_archive(name, info)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        url = f"https://codeload.github.com/fearkov/{name}/zip/{info['commit']}"
        temp = archive.with_suffix(".zip.part")
        print(f"Downloading {name} at {info['commit'][:12]} ...", flush=True)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Burst-Recomp-Local-Snapshot/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response, temp.open("wb") as out:
                length = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    length += len(block)
                    if length > 512 * 1024 * 1024:
                        die(f"Archive {name} exceeds the 512 MB safety threshold")
                    out.write(block)
            temp.replace(archive)
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    else:
        print(f"Using previously downloaded archive: {archive.name}", flush=True)
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return archive, digest.hexdigest()


def extract_safely(archive_path: Path, name: str, commit: str, target: Path) -> int:
    expected_top = f"{name}-{commit}"
    n = 0
    total = 0
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > 100_000:
            die(f"Too many files in {name} archive")
        for member in infos:
            parts = PurePosixPath(member.filename).parts
            if not parts or parts[0] != expected_top or ".." in parts:
                die(f"Unexpected ZIP member in {name}: {member.filename!r}")
            if len(parts) == 1:
                continue
            relative = parts[1:]
            if any(p in (".git", ".gitmodules") for p in relative):
                continue
            # Do not inherit the upstream GitHub Actions configuration.
            if len(relative) >= 2 and relative[0] == ".github" and relative[1] == "workflows":
                continue
            mode = (member.external_attr >> 16) & 0o170000
            if stat.S_ISLNK(mode):
                die(f"Symlinks are not accepted from source ZIPs: {member.filename}")
            total += member.file_size
            if total > 2 * 1024**3:
                die(f"Uncompressed {name} archive exceeds the 2 GB safety limit")
            dst = target.joinpath(*relative)
            if member.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, dst.open("wb") as out:
                    shutil.copyfileobj(source, out, 1024 * 1024)
                n += 1
    if not (target / "Cargo.toml").is_file() or not (target / "README.md").is_file():
        die(f"{name} archive did not produce an expected source tree")
    return n


def patch_local_dependencies(stage: Path) -> None:
    for file_path, package, url, replacement in DEPENDENCY_REWRITES:
        target = stage / file_path
        content = target.read_text(encoding="utf-8")
        # The exact upstream dependency is expected exactly once. The guard
        # prevents silently shipping a disconnected/broken partial rewrite.
        pattern = re.compile(
            rf'(?m)^(\s*{re.escape(package)}\s*=\s*\{{\s*)git\s*=\s*"{re.escape(url)}"'
        )
        content, count = pattern.subn(lambda m: m.group(1) + f'path = "{replacement}"', content)
        if count != 1:
            die(f"Expected exactly one {package} Git dependency in {file_path}; found {count}. Upstream changed?")
        target.write_text(content, encoding="utf-8", newline="\n")


def validate(stage: Path) -> None:
    for name in SOURCES:
        root = stage / name
        if not (root / "Cargo.toml").is_file():
            die(f"Missing {name}/Cargo.toml")
        if (root / ".git").exists() or (root / ".gitmodules").exists():
            die(f"Found upstream Git metadata in {name}")
        if (root / ".github" / "workflows").exists():
            die(f"Found upstream GitHub Actions in {name}")
        for toml in root.rglob("Cargo.toml"):
            content = toml.read_text(encoding="utf-8")
            if re.search(r'\bgit\s*=\s*["\'](?:https?|ssh)://', content):
                die(f"Remote Cargo Git dependency remains: {toml.relative_to(stage)}")
    for file_path, package, _url, relative in DEPENDENCY_REWRITES:
        toml = stage / file_path
        content = toml.read_text(encoding="utf-8")
        expected = f'{package} = {{ path = "{relative}"'
        if expected not in content:
            die(f"Missing local dependency mapping {package} in {file_path}")
        resolved = (toml.parent / relative).resolve()
        if not (resolved / "Cargo.toml").is_file():
            die(f"Broken path dependency from {file_path}: {relative}")


def fetch() -> None:
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    present = [n for n in SOURCES if (EXTERNAL / n).exists()]
    if present or MANIFEST.exists():
        die("Existing vendor sources/manifest detected (" + ", ".join(present) + "). "
            "Refusing to overwrite. Run VERIFY_SOURCES.bat; back up existing sources before a fresh import.")

    with tempfile.TemporaryDirectory(prefix="source-stage-", dir=LOCAL) as tempdir:
        stage = Path(tempdir)
        archives: dict[str, dict[str, str | int]] = {}
        for name, info in SOURCES.items():
            archive, digest = fetch_archive(name, info)
            count = extract_safely(archive, name, info["commit"], stage / name)
            archives[name] = {
                "repo": info["repo"],
                "commit": info["commit"],
                "commit_date": info["date"],
                "archive": str(archive.relative_to(ROOT)).replace("\\", "/"),
                "sha256": digest,
                "extracted_files": count,
                "license": "MIT (declared by upstream)",
            }
            print(f"Extracted {name}: {count} source files", flush=True)
        patch_local_dependencies(stage)
        validate(stage)
        # All downloads, extraction, and local-dependency validation have
        # succeeded before any project source directory is installed.
        for name in SOURCES:
            shutil.move(str(stage / name), str(EXTERNAL / name))
        output = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "snapshots": archives,
            "rewrites": [
                {"manifest": f"external/{p}", "dependency": d, "local_path": local}
                for p, d, _url, local in DEPENDENCY_REWRITES
            ],
            "notes": [
                "No upstream .git metadata, submodules, or GitHub Actions included.",
                "Cargo.lock files originate upstream; Cargo reconciles them on first local build.",
                "Crates.io dependencies still require an initial Cargo download unless cached.",
                "Use PORT_LOCAL.bat to keep the generated port linked to the local Zakuro snapshot.",
            ],
        }
        MANIFEST.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("\nSUCCESS: Independent local snapshots are in external/3dsrecomp and external/zakuro")
    print("No upstream Git remotes, GitHub Actions, builds, or ROMs were installed.")
    print("Next: VERIFY_SOURCES.bat, then BUILD_TOOLS.bat if desired.")


def verify() -> None:
    if not MANIFEST.is_file():
        die("Missing SOURCE_MANIFEST.json. Run FETCH_SOURCES.bat first.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validate(EXTERNAL)
    for name, info in manifest["snapshots"].items():
        archive = ROOT / info["archive"]
        if not archive.is_file():
            die(f"Missing local backup archive: {archive}")
        h = hashlib.sha256()
        with archive.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != info["sha256"]:
            die(f"Source archive changed since import: {archive}")
        print(f"Verified {name} ({info['commit'][:12]}), archive SHA256 {info['sha256'][:16]}...")
    print("PASS: local Cargo paths, no upstream Git remotes in manifests, no GitHub Actions.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Check local snapshot and dependencies")
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        fetch()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
