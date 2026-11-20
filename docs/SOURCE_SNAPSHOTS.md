# Pinned upstream source snapshots

Both codebases are fetched from a commit-specific GitHub source archive, *not* cloned with Git. They are placed directly into `external/` and can be committed as regular source files in this repository.

| Local directory | Upstream | Pinned commit | Upstream commit timestamp |
|---|---|---|---|
| `external/3dsrecomp` | https://github.com/fearkov/3dsrecomp | `4b6de5d884b0d8bc337e16c07b84a0824e55a0e1` | 2026-11-17 02:54 UTC |
| `external/zakuro` | https://github.com/fearkov/zakuro | `fdf67b29b6398a7ad0dc2309b09ea4c03c45e9d8` | 2026-11-17 03:35 UTC |

The Cargo manifests are changed only to replace three upstream Git dependencies with local sibling-path dependencies:

- `3dsrecomp/Cargo.toml`: `zakuro-cpu` -> `../zakuro/crates/zakuro-cpu`
- `zakuro/Cargo.toml`: `recomp-abi` -> `../3dsrecomp/abi`
- `zakuro/crates/zakuro/Cargo.toml`: `recomp3ds` -> `../../../3dsrecomp`

`.github/workflows` from upstream is intentionally omitted. No Git submodules or upstream `.git` metadata are imported. The generated `SOURCE_MANIFEST.json` records the source ZIP SHA-256 digests.

Zakuro is distributed under the MIT License; see `external/zakuro/LICENSE` after pulling. 3dsrecomp declares MIT licensing in its `Cargo.toml`; its upstream snapshot currently does not include a standalone root `LICENSE` file. Keep copyright and attribution intact.

**Scope of independence:** no Git remotes, submodules, or Cargo *Git* dependencies are required after import. This is **not a fully offline Cargo dependency vendor**: crates.io dependencies may need to download on the first build. The generated port must be created using `PORT_LOCAL.bat`, which supplies `--zakuro <local checkout>` to stop the port generator from defaulting to the public GitHub repository.
