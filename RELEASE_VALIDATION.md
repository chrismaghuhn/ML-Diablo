# Release validation - 0.1.0 / M0-FIX / M0.1

Validated on **2026-08-11** in the Windows build environment. The archive remains
an independent scaffold release; the local DevilutionX checkout and all generated
build trees are excluded from the release package.

## M0-FIX: standalone scaffold

```text
Python 3.14.5
PyTorch 2.12.1+cu126
NumPy 2.5.0
CMake 4.3.3
MSVC 19.44.35227.0
vcpkg baseline 40f3c709db80acf154ac4b17a1f83c564ebd022e
```

```text
56 Python tests passed with the full ML stack
53 Python tests passed and 1 skipped in the dev-only environment
ruff check src tests scripts: passed
mypy src/dxai: passed for 37 source files
5 JSON Schemas validated
5 static schema examples validated
1 runtime episode / 10 runtime transitions validated
7 YAML files parsed
72 local documentation links validated
3 task contracts validated
asset boundary scan passed
C++20 bridge contract: 1/1 passed in Release
Python compileall passed
ZIP path/CRC/stream validation passed
no source-tree symlinks
```

The C++ bridge contract is built with MSVC `/WX`; the previous C4244 narrowing
warning is removed. The documented Windows CTest commands consistently select the
Release configuration, and the regression test `tests/test_build_contract.py`
passes.

The project was rebuilt as
`devilutionx_ai_lab-0.1.0-py3-none-any.whl`, installed without dependencies in a
fresh virtual environment, and exercised through:

```text
dxai tasks
dxai ml-plan
dxai smoke --episodes 3 --agent heuristic --no-record
```

All three installed-package smoke episodes completed with `SUCCESS`.

## M0.1: pinned DevilutionX build baseline

The repository and commit are read from `upstream.lock.toml`:

```text
https://github.com/diasurgical/DevilutionX.git
07385842840437cc9a785b195f5b40b121eaeb1c
commit title: [Amiga] Disable broken optimizations
LICENSE.md SHA-256:
049382c17367e384c622369abbeda0cab1d65658c28611717e18afead341e586
```

The checkout is detached at the exact commit and clean. The fetch script completed
without downloading Diablo MPQs or original game assets. With the pinned vcpkg
baseline and Visual Studio 17 2022 x64:

```text
Release configure: passed
Release build: passed
Release output: build/devilutionx-vcpkg/Release/devilutionx.exe
Release CTest: 0 tests discovered
Debug configure with BUILD_TESTING=ON and DISABLE_LTO=ON: passed
Debug build including upstream test targets: passed
Debug CTest discovery: 556 test cases
Focused data-independent headless test set: 23/23 passed
devilutionx.exe --help: exit code 0
devilutionx.exe --version: exit code 0
```

The Release CTest result is intentional upstream behavior: the pinned CMake files
disable `BUILD_TESTING` for non-Debug MSVC builds when LTO is enabled. The complete
Debug matrix was not promoted to a pass because the upstream tests that require
game/fixture data are not runnable from this asset-free scaffold checkout. Their
failures are data/path prerequisites, not evidence of a completed AI integration.

## Scope boundary

This validates the standalone scaffold, mock environment, contracts, data path,
reference model, C++ adapter contract and the reproducible pinned upstream build
baseline. It does **not** validate a real DevilutionX observation/action bridge,
controlled Combat fixture, determinism gate, proprietary assets, a completed BC/R2D3
learner or a trained full-run agent.

The next authorized work remains read-only observation extraction after the pinned
build baseline. No raw engine command API or RL loop was added.
