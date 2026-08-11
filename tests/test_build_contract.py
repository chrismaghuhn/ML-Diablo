from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_DOCUMENTS = (
    Path("README.md"),
    Path("CONTRIBUTING.md"),
    Path("Makefile"),
    Path(".github/workflows/ci.yml"),
    Path("docs/GETTING_STARTED.md"),
)


def _lines_containing(path: Path, token: str) -> list[str]:
    return [
        line.strip()
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if token in line
    ]


def test_bridge_build_commands_select_release_configuration() -> None:
    ctest_lines = [
        line
        for path in BUILD_DOCUMENTS
        for line in _lines_containing(path, "ctest")
    ]
    build_lines = [
        line
        for path in BUILD_DOCUMENTS
        for line in _lines_containing(path, "cmake --build")
    ]

    assert ctest_lines
    assert build_lines
    assert all(re.search(r"(?:^|\s)-C\s+Release(?:\s|$)", line) for line in ctest_lines)
    assert all("--config Release" in line for line in build_lines)


def test_msvc_bridge_build_treats_warnings_as_errors() -> None:
    cmake = (ROOT / "engine_adapter/CMakeLists.txt").read_text(encoding="utf-8")

    assert "/WX" in cmake
