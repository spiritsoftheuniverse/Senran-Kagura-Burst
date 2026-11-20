"""Offline regression tests: synthetic source ZIPs, no network or ROM required."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


HERE = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("fetch_sources", HERE / "scripts" / "fetch_sources.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SnapshotBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.orig = (mod.ROOT, mod.EXTERNAL, mod.LOCAL, mod.SNAPSHOTS, mod.MANIFEST)
        self.addCleanup(self.restore)
        mod.ROOT = self.root
        mod.EXTERNAL = self.root / "external"
        mod.LOCAL = self.root / "local"
        mod.SNAPSHOTS = mod.LOCAL / "source-archives"
        mod.MANIFEST = self.root / "SOURCE_MANIFEST.json"
        mod.SNAPSHOTS.mkdir(parents=True)
        for name, info in mod.SOURCES.items():
            with zipfile.ZipFile(mod.source_archive(name, info), "w") as z:
                top = f"{name}-{info['commit']}"
                z.writestr(f"{top}/README.md", "testing")
                z.writestr(f"{top}/.github/workflows/build.yml", "should not copy")
                if name == "3dsrecomp":
                    z.writestr(f"{top}/Cargo.toml", '[dependencies]\nzakuro-cpu = { git = "https://github.com/fearkov/zakuro", optional = true }\n')
                    z.writestr(f"{top}/abi/Cargo.toml", '[package]\nname = "recomp-abi"\n')
                else:
                    z.writestr(f"{top}/Cargo.toml", '[workspace.dependencies]\nrecomp-abi = { git = "https://github.com/fearkov/3dsrecomp" }\n')
                    z.writestr(f"{top}/crates/zakuro/Cargo.toml", '[dependencies]\nrecomp3ds = { git = "https://github.com/fearkov/3dsrecomp" }\n')
                    z.writestr(f"{top}/crates/zakuro-cpu/Cargo.toml", '[package]\nname = "zakuro-cpu"\n')

    def restore(self):
        mod.ROOT, mod.EXTERNAL, mod.LOCAL, mod.SNAPSHOTS, mod.MANIFEST = self.orig

    def test_fetch_and_verify_offline(self):
        mod.fetch()
        mod.verify()
        self.assertFalse((mod.EXTERNAL / "zakuro/.github/workflows").exists())
        self.assertFalse((mod.EXTERNAL / "3dsrecomp/.git").exists())
        self.assertIn('path = "../../../3dsrecomp"', (mod.EXTERNAL / "zakuro/crates/zakuro/Cargo.toml").read_text())
        self.assertEqual(len(json.loads(mod.MANIFEST.read_text())["snapshots"]), 2)

    def test_second_import_refuses_overwrite(self):
        mod.fetch()
        with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite"):
            mod.fetch()

    def test_rejects_bad_zip_path(self):
        archive = mod.source_archive("3dsrecomp", mod.SOURCES["3dsrecomp"])
        with zipfile.ZipFile(archive, "a") as z:
            z.writestr("../escape.txt", "evil")
        with self.assertRaisesRegex(RuntimeError, "Unexpected ZIP member"):
            mod.fetch()
        self.assertFalse((mod.EXTERNAL / "3dsrecomp").exists())


if __name__ == "__main__":
    unittest.main()
