# Runbook — Lokales Setup

1. Python-venv anlegen.
2. `pip install -e ".[dev,ml]"`.
3. `python -m dxai smoke --episodes 3`.
4. `pytest`.
5. C++-Contract mit CMake bauen.
6. `python scripts/validate_artifacts.py`.
7. Erst danach Upstream separat auschecken.

Bei Windows lange Pfade aktivieren und Build-/Assetpfade außerhalb synchronisierter Cloudordner bevorzugen.
