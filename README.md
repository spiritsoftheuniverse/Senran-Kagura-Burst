# Senran Kagura Burst — independent source starter

This starter prepares a local, modifiable snapshot of **3dsrecomp + Zakuro** for a faithful Windows x64 recompilation of the original Nintendo 3DS game. No ROM, generated game code, or copyrighted game assets are included.

**This download contains a source-fetching bootstrap, not the upstream sources yet.** Run `FETCH_SOURCES.bat` once on your Windows machine to retrieve them. It downloads two **pinned** upstream commits into `external/` with *no upstream Git history, Git remotes, or GitHub Actions*. Their Rust Cargo references to each other are rewritten to local paths. Files in `external/` are ordinary files, not Git submodules.

## First use on Windows 11

1. Extract this ZIP into, for example, `F:\senran-kagura-burst-recomp`.
2. Double-click **`FETCH_SOURCES.bat`** (or run it in CMD or PowerShell to see output).
3. Run **`VERIFY_SOURCES.bat`**. It verifies local source paths and SHA-256 hashes of the downloaded archive backups. You can also run **`RUN_TEST.bat`** to exercise the fetcher against synthetic local archives (no downloads).
4. Optionally run **`INIT_LOCAL_GIT.bat`**. This creates your own local Git repo on `main`, **without adding any upstream remote**, and does not commit or push anything.
5. Later, with Rust stable 1.95+ installed, run **`BUILD_TOOLS.bat`** to compile the two tools. The first build downloads Rust crates from crates.io unless already cached.

No need to supply a ROM to fetch or build the toolchain. All game dumps, archives, build products and generated game code should stay in `local/` or other ignored paths, never in your public source repository.

## Directory structure after fetching

```text
senran-kagura-burst-recomp/
  external/
    3dsrecomp/         # normal local files; NOT a submodule
    zakuro/            # normal local files; NOT a submodule
  scripts/
    fetch_sources.py
  docs/
    SOURCE_SNAPSHOTS.md
  local/               # ignored from Git
    source-archives/   # exact commit ZIP backups, SHA256 in manifest
    ports/             # later, generated per-game port source
  FETCH_SOURCES.bat
  VERIFY_SOURCES.bat
  INIT_LOCAL_GIT.bat
  BUILD_TOOLS.bat
  PORT_LOCAL.bat
  SOURCE_MANIFEST.json  # generated after successful pull
```

## When the ROM is available

Use **`PORT_LOCAL.bat "F:\path\to\Burst.3ds"`** *after* building the tools. This creates a generated per-game port under `local/ports/Burst/` and **explicitly links it to the local Zakuro tree**, not a Git dependency. This command has **not** been run or validated against Burst, so compatibility remains unknown. The generated port and ROM are ignored by Git.

## Notes

- The import refuses to overwrite existing source directories. That protects any local changes you make. Back up or rename `external/` and `SOURCE_MANIFEST.json` before intentionally starting from a fresh snapshot.
- `Cargo.lock` files are retained from upstream. The first Cargo build reconciles them after the local dependency path rewrites; review the resulting changes and commit the updated lockfiles if you want fully pinned Rust package resolution.
- There are **no GitHub Actions or cloud build steps**. All compilation and testing is local.
- `3dsrecomp` and `Zakuro` are under MIT license declarations; keep original licensing information when redistributing any modifications. Review all bundled third-party dependency licenses before shipping binaries.
- Source archives are downloaded using HTTPS from GitHub's codeload service. If networking or TLS fails, no partially extracted sources are installed.

**Upstreams:** [3dsrecomp](https://github.com/fearkov/3dsrecomp), [Zakuro](https://github.com/fearkov/zakuro). Commit pins and rewrite details are in `docs/SOURCE_SNAPSHOTS.md`.
