# Einstieg und lokaler Entwicklungsfluss

Dieses Dokument führt durch den Scaffold, nicht durch die noch ausstehende echte DevilutionX-Integration.

## Voraussetzungen

Minimal:

- Python 3.11+
- Git

Vollständige lokale Checks:

- CMake 3.20+
- ein C++20-Compiler
- optional PyTorch für Modelltests

## 1. Umgebung anlegen

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,ml]"
```

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,ml]"
```

Ohne PyTorch reicht für den Contract-/Mock-Pfad:

```bash
python -m pip install -e ".[dev]"
```

## 2. Mock-Umgebung ausführen

```bash
python -m dxai smoke --episodes 5 --agent heuristic --base-seed 0
python -m dxai smoke --episodes 20 --agent random --base-seed 0
python -m dxai tasks
python -m dxai ml-plan
```

Der Heuristiklauf ist ein Integrations-Smoke, kein ML-Ergebnis. Die Random-Baseline liefert eine erste untere Referenz.

## 3. Trajektorie inspizieren

Der Smoke-Befehl schreibt standardmäßig nach `artifacts/smoke/<timestamp>/`.

```bash
python -m dxai inspect artifacts/smoke/<timestamp>/episodes/<episode-id>
```

Das Lesen schlägt fehl, wenn der SHA-256-Hash oder die manifestierte Schrittzahl nicht stimmt.

## 4. Tests ausführen

```bash
pytest
python scripts/validate_artifacts.py
python scripts/check_no_assets.py
```

C++-Vertrag:

```bash
cmake -S engine_adapter -B build/bridge -DCMAKE_BUILD_TYPE=Release
cmake --build build/bridge --config Release
ctest --test-dir build/bridge --output-on-failure -C Release
```

Gesamtcheck:

```bash
make check
```

## 5. DevilutionX separat auschecken

```bash
./scripts/fetch_devilutionx.sh
```

oder:

```powershell
.\scripts\fetch_devilutionx.ps1
```

Der Checkout wird auf den Commit aus `upstream.lock.toml` gepinnt. Das Skript lädt keine MPQs oder Originalassets herunter.

## 6. Erster echter Implementierungsschritt

Nicht sofort ein neuronales Netz trainieren. Zuerst M0:

1. Adaptertarget im lokalen DevilutionX-Fork anlegen.
2. Reset eines kontrollierten Fixtures implementieren.
3. `Observation` aus ausschließlich spielerbeobachtbarem State exportieren.
4. Legal Candidates aus Engine-Prüfungen erzeugen.
5. genau einen Candidate über vorhandene semantische Kommandowege ausführen.
6. bis zur nächsten Entscheidungsgrenze ticken.
7. Determinismus-/Replay-Tests auf mindestens 100 Seeds bestehen.

Die genauen Gates stehen in `21_MILESTONE_ACCEPTANCE.md`.

## Häufige Fehlstarts

- Eingaben per Bildschirmkoordinate statt semantischer Engineaktion senden.
- ein einzelner `step()` entspricht immer genau einem Renderframe.
- vollständige Dungeonkarte oder unsichtbare Monster exportieren.
- Reward aus Heuristiken erzeugen, die der Agent später einfach farmt.
- Training starten, bevor Seed, Versionen und Action Candidates aufgezeichnet werden.
- DevilutionX- und ML-Code untrennbar in ein einziges Python/C++-Binary linken.
