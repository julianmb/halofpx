"""Guards against engine-artifact drift between build script and Dockerfiles.

Regression coverage for a real outage: build_engine.sh --prebuilt failed its
SHA256 check because EXPECTED_TARBALL_SHA still held the v1.0.0 digest while
the URL served v1.7.0, and Dockerfile.rocm interpolated ${ENGINE_RELEASE} in
the URL path but hardcoded v1.5.2 in the filename — so bumping the ARG alone
fetched a nonexistent asset.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = ROOT / "scripts" / "build_engine.sh"

VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")
# Matches release asset URLs with either a literal tag or ${ENGINE_RELEASE} in
# the download path; group(1) is the path tag (or ""), group(2) the filename.
URL_RE = re.compile(
    r"https://github\.com/\S+/releases/download/(v\d+\.\d+\.\d+|\$\{ENGINE_RELEASE\})/(\S+?\.tar\.gz)")
STALE_SHA = "bbc7845db0c012b97f1c9b8a2733a7083c6f9a749a453866fbe1994151d3364f"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _engine_urls(text: str, arg_ver: str | None) -> list[tuple[str, str]]:
    """Return (effective_path_version, filename) for each engine asset URL."""
    out = []
    for m in URL_RE.finditer(text):
        path_ver, filename = m.group(1), m.group(2)
        if path_ver == "${ENGINE_RELEASE}":
            assert arg_ver, "URL uses ${ENGINE_RELEASE} but no ARG version found"
            path_ver = arg_ver
        out.append((path_ver, filename))
    return out


class EngineArtifactSyncTests(unittest.TestCase):
    def test_prebuilt_checksum_is_not_stale(self):
        script = _read(BUILD_SCRIPT)
        m = re.search(r'EXPECTED_TARBALL_SHA="([0-9a-f]+)"', script)
        self.assertIsNotNone(m, "EXPECTED_TARBALL_SHA not found in build_engine.sh")
        self.assertNotEqual(m.group(1), STALE_SHA,
                            "checksum still pins the retired v1.0.0 asset")

    def test_release_url_path_and_filename_versions_match(self):
        checked = 0
        files = {
            BUILD_SCRIPT: None,
            ROOT / "Dockerfile": None,
            ROOT / "Dockerfile.rocm": None,
        }
        for path in files:
            text = _read(path)
            arg = re.search(r"(?:ARG )?ENGINE_RELEASE[=:](v\d+\.\d+\.\d+)", text)
            arg_ver = arg.group(1) if arg else None
            for path_ver, filename in _engine_urls(text, arg_ver):
                file_vers = VERSION_RE.findall(filename.replace("${ENGINE_RELEASE}", arg_ver or ""))
                self.assertTrue(file_vers, f"no version in asset filename: {filename}")
                for fv in file_vers:
                    self.assertEqual(
                        fv, path_ver,
                        f"version drift in {path.name}: path {path_ver} vs file {fv}")
                checked += 1
        self.assertGreater(checked, 0, "no release URLs found to check")

    def test_docker_arg_matches_bundled_engine_url(self):
        for dockerfile in [ROOT / "Dockerfile", ROOT / "Dockerfile.rocm"]:
            text = _read(dockerfile)
            arg = re.search(r"ARG ENGINE_RELEASE=(v\d+\.\d+\.\d+)", text)
            self.assertIsNotNone(arg, f"ARG ENGINE_RELEASE missing in {dockerfile.name}")
            urls = _engine_urls(text, arg.group(1))
            self.assertTrue(urls, f"no engine release URL in {dockerfile.name}")
            for path_ver, _ in urls:
                self.assertEqual(path_ver, arg.group(1),
                                 f"{dockerfile.name} bundles {path_ver}, ARG is {arg.group(1)}")

    def test_engine_source_is_maintained_upstream(self):
        script = _read(BUILD_SCRIPT)
        m = re.search(r'REPO_URL="(https://github\.com/\S+?\.git)"', script)
        self.assertIsNotNone(m, "REPO_URL not found in build_engine.sh")
        self.assertIn("ROCmFPX/ROCmFPX", m.group(1),
                      "engine source should be the maintained ROCmFPX org repo, "
                      "not the unmaintained charlie12345 fork (last push 2026-08-22)")


if __name__ == "__main__":
    unittest.main()
