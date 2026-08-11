# DevilutionX AI Lab

Gründliches, nicht-kommerzielles Forschungs-Scaffold für einen lernenden Diablo-1-Agenten auf Basis einer **externen** DevilutionX-Engine.

> **Aktueller Status:** Die Verträge, der deterministische Mock, Trajektorienaufzeichnung, Replay-Grundlagen, ein dynamisches rekurrentes Candidate-Q-Netz, Tests und ein separat kompilierbarer C++-Bridge-Vertrag sind implementiert. Die echte DevilutionX-Bridge und der vollständige R2D3-Learner sind absichtlich noch nicht als fertig markiert.

## Ziel

Ein Agent soll mit einem frischen Charakter autonom lernen:

```text
kämpfen → erkunden → Beute bewerten → Inventar verwalten
→ Stadt nutzen → Charakter entwickeln → Diablo besiegen
```

Kein LLM, keine Screenshot-Klickautomatisierung und kein versteckter Engine-State. DevilutionX bleibt die Regelinstanz; ML sieht ausschließlich eine versionierte, spielerbeobachtbare Zustandsansicht und eine Liste legaler semantischer Aktionskandidaten.

## Empfohlenes ML-Prinzip

```text
regelbasierte und menschliche Demonstrationen
                 ↓
       Behavior-Cloning-Warmstart
                 ↓
rekurrentes Off-Policy-Q-Learning mit Replay
          im Stil von R2D2/R2D3
  (Demo-Replay + Agent-Replay + Burn-in)
                 ↓
 feste Skills: Kampf / Navigation / Loot / Stadt
                 ↓
       gelernter Skill-Manager
                 ↓
 optionale Exploration- oder World-Model-Forschung
```

Die zentrale Entscheidung steht in [`docs/10_ML_STRATEGY.md`](docs/10_ML_STRATEGY.md) und wird in [`docs/23_ML_DECISION_MATRIX.md`](docs/23_ML_DECISION_MATRIX.md) gegen Alternativen geprüft.

## Repository-Struktur

```text
configs/           versionierte Startkonfigurationen für Tasks und Training
docs/              Architektur, ML-Entscheidung, Verträge, ADRs und Roadmap
engine_adapter/    eigenständiger C++-Bridge-Vertrag; kein Upstream-Code
protocol/          logisches Protobuf-/IPC-Protokoll
schemas/           JSON Schemas für Observation, Transition und Checkpoint
scripts/           Setup, Validierung, Smoke-Run und Upstream-Helfer
src/dxai/          ausführbarer Python-Scaffold
tests/             Contract-, Determinismus-, Daten-, Replay- und Modelltests
third_party/       leerer Zielordner für einen lokalen DevilutionX-Checkout
```

Einstieg: [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) → [`docs/INDEX.md`](docs/INDEX.md) → [`docs/00_EXECUTIVE_SUMMARY.md`](docs/00_EXECUTIVE_SUMMARY.md) → [`docs/20_ROADMAP.md`](docs/20_ROADMAP.md).

Weitere Statusgrenzen: [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Lokaler Smoke-Run

Python 3.11 oder neuer:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev,ml]"
python -m dxai smoke --episodes 3 --agent heuristic
pytest
```

Der Standardbibliotheks-Pfad funktioniert ohne ML-Abhängigkeiten:

```bash
PYTHONPATH=src python -m dxai smoke --episodes 2 --agent heuristic
```

Trajektorien landen versioniert unter `artifacts/smoke/`.

## Separater C++-Contract-Test

```bash
cmake -S engine_adapter -B build/bridge -DCMAKE_BUILD_TYPE=Release
cmake --build build/bridge --config Release
ctest --test-dir build/bridge -C Release --output-on-failure
```

Dieser Test linkt DevilutionX noch nicht. Er prüft, dass die künftige Adaptergrenze eigenständig und streng typisiert ist.

## Upstream lokal holen

DevilutionX und Diablo-Daten sind **nicht** enthalten. Der untersuchte Upstream-Stand ist in `upstream.lock.toml` festgehalten.

```bash
./scripts/fetch_devilutionx.sh
# PowerShell:
./scripts/fetch_devilutionx.ps1
```

Vor Änderungen: [`docs/04_DEVILUTIONX_INTEGRATION.md`](docs/04_DEVILUTIONX_INTEGRATION.md) und [`docs/18_SECURITY_PRIVACY_LEGAL.md`](docs/18_SECURITY_PRIVACY_LEGAL.md).

## Nicht verhandelbare Regeln

1. Die Engine entscheidet über Legalität, RNG, Schaden, Bewegung, Inventar, Shops und Terminalzustände.
2. ML erhält an jeder Entscheidungsgrenze mindestens einen legalen Kandidaten und darf keine beliebigen Engine-Kommandos senden.
3. `candidate_id` ist nur innerhalb einer Observation gültig; Trajektorien speichern zusätzlich die semantische Aktion.
4. Unsichtbare Karte, nicht sichtbare Gegner, zukünftiger RNG und interne KI-Zustände dürfen nicht in Beobachtungen gelangen.
5. Train-, Validierungs- und Test-Seeds bleiben disjunkt und versioniert.
6. Keine MPQs, Originalgrafiken, Musik, Videos, Saves oder sonstige proprietäre Spieldaten werden committed.
7. Vor ML-Training müssen Determinismus-, Legalitäts-, Observability- und Replay-Gates bestehen.

## Lizenzgrenze

Der originäre Scaffold-Code steht unter Apache-2.0. DevilutionX ist eine externe Abhängigkeit und wurde am festgehaltenen Stand unter der **Sustainable Use License 1.0** mit nicht-kommerziellen Einschränkungen veröffentlicht. Diablo-Daten bleiben proprietär. Details: [`NOTICE.md`](NOTICE.md).

Dieses Projekt ist weder mit Blizzard Entertainment noch mit den DevilutionX-Maintainern verbunden oder von ihnen unterstützt.
