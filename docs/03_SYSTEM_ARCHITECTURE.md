# 03 — Systemarchitektur

## Überblick

```text
┌──────────────────────────────────────────────────────────────────────┐
│                           Experiment Control                          │
│ configs · seed registry · run manifest · checkpoint registry         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                    spawn / reset / health check
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│                    DevilutionX Environment Process                    │
│                                                                      │
│  scenario fixture → engine state → observable-state exporter         │
│                                 → legal candidate generator          │
│  chosen candidate → semantic engine command → game logic ticks       │
│                                 → next decision boundary             │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ versioned local IPC
┌──────────────────────────────▼───────────────────────────────────────┐
│                         Python Environment Client                     │
│  validation · timeout · request ordering · trajectory hooks          │
└──────────────┬───────────────────────┬────────────────────────────────┘
               │                       │
     ┌─────────▼────────┐    ┌────────▼─────────────────┐
     │ Actor / Evaluator │    │ Demonstration Collector  │
     │ policy + LSTM     │    │ script/human + metadata  │
     └─────────┬────────┘    └────────┬─────────────────┘
               │ sequences             │ sequences
               ▼                       ▼
      ┌─────────────────┐     ┌──────────────────┐
      │ Agent Replay     │     │ Demo Replay      │
      │ prioritized      │     │ separately prio. │
      └────────┬────────┘     └────────┬─────────┘
               └──────────────┬────────┘
                              ▼
                    ┌────────────────────┐
                    │ Learner            │
                    │ BC / R2D2 / R2D3   │
                    │ target network     │
                    └─────────┬──────────┘
                              ▼
                    checkpoint + metrics
```

## Prozessgrenzen

### Eine Engine-Instanz pro Prozess

DevilutionX besitzt umfangreichen globalen Zustand. Mehrere Episodeninstanzen im selben Prozess würden zunächst unnötiges Reentrancy- und Reset-Risiko erzeugen. Daher gilt für v1:

```text
Actor 0 → Engine Process 0
Actor 1 → Engine Process 1
...
Evaluator → eigener Engine Process
```

Skalierung erfolgt durch Prozesse, nicht Threads innerhalb einer Engine. Der Python-Learner darf GPU-gebunden und unabhängig von den CPU-Aktoren laufen.

### Engine und ML sind getrennte Verantwortungsbereiche

**Engine:**

- Levelgenerierung und RNG;
- Bewegung, Kollision, Animation und Timing;
- Kampf, Schaden, Resistenzen und Tod;
- Monster-KI;
- Item-, Inventar- und Shopregeln;
- Quests und Levelübergänge;
- Legalitätsprüfung;
- Terminalzustände.

**ML-Stack:**

- player-observable Kodierung konsumieren;
- Kandidaten einbetten und bewerten;
- Policy-/Value-Lernen;
- Replay und Datensätze;
- Evaluation und Statistik;
- Checkpoints und Experimentprovenienz.

## Kontrollfluss eines Steps

1. Die Engine befindet sich an einer dokumentierten Entscheidungsgrenze.
2. Der Adapter erstellt eine Observation und eine geordnete Kandidatenliste.
3. Python erhält `episode_id`, `step_id` und Kandidaten.
4. Der Agent wählt eine observation-lokale `candidate_id`.
5. Der Client sendet `episode_id`, erwartete `step_id` und `candidate_id`.
6. Der Adapter lehnt stale, doppelte oder illegale Requests ab.
7. Der Adapter übersetzt den Kandidaten in einen existierenden semantischen Engine-Befehl.
8. Die Engine läuft bis zur nächsten Entscheidungsgrenze, Terminalbedingung oder einem Sicherheitslimit.
9. Rewardadapter und Diagnostik werden aus dem Übergang erzeugt.
10. Observation, Reward, Flags und Info werden atomar zurückgegeben.

Ein Step ist damit eher ein **Semi-Markov-Entscheidungsschritt** als exakt ein Renderframe. Die Anzahl interner Game-Ticks wird in `engine_tick` sichtbar gemacht.

## Datenfluss

### Online-Erfahrung

Akteure schreiben keine unversionierten Python-Objekte in den Learner. Jeder Übergang entspricht `dxai.transition.v1`. Sequenzen dürfen Episodengrenzen nicht überqueren.

### Demonstrationen

Demonstrationen verwenden denselben Observation- und Action-Vertrag wie der Agent. Rohes Maus-/Keyboard-Input darf zusätzlich als Auditspur gespeichert werden, ist aber nicht das Trainingslabel. Das Trainingslabel ist der nach Engine-Legalität aufgelöste semantische Kandidat.

### Checkpoints

Ein Checkpoint besteht logisch aus:

- Gewichtsdatei;
- Optimizer-/Scheduler-Zustand;
- Modell- und Feature-Version;
- Observation-/Action-Vertrag;
- Taskliste;
- Upstream-Revision;
- vollständigem Config-Hash;
- Learner-Step und Replay-Provenienz;
- Evaluationsmetriken auf festen Seeds.

Ein Gewichtsblob ohne Manifest ist kein gültiger Checkpoint.

## Komponenten im Scaffold

| Pfad | Zweck | Status |
|---|---|---|
| `src/dxai/contracts` | Python-Datenverträge | ausführbar |
| `src/dxai/env/mock.py` | deterministischer Contract-Mock | ausführbar |
| `src/dxai/data` | JSONL-Trajektorien + Manifest | ausführbar |
| `src/dxai/training/replay.py` | Referenz-PER + Dual Replay | ausführbar, nicht hochskaliert |
| `src/dxai/models/candidate_q.py` | rekurrentes Candidate-Q-Netz | ausführbar mit PyTorch |
| `engine_adapter/` | C++-Vertrag und Validierung | kompilierbar |
| `protocol/` | logisches IPC-Schema | spezifiziert |
| `schemas/` | Artefaktverträge | validierbar |
| echte DevilutionX-Bridge | Engine-Integration | noch zu implementieren |
| voller Learner | verteiltes Training | noch zu implementieren |

## Abhängigkeitsrichtung

```text
contracts ← env / data / models / training / evaluation
     ↑
engine protocol
```

Die Verträge dürfen keine Abhängigkeit auf PyTorch, DevilutionX oder einen Transport haben. Dadurch können Datensätze und Tests gelesen werden, ohne GPU- oder Engine-Abhängigkeiten zu installieren.

## Fehlerklassen

- `PROTOCOL_VERSION_MISMATCH`
- `OBSERVATION_VERSION_MISMATCH`
- `STALE_STEP`
- `ILLEGAL_CANDIDATE`
- `ENGINE_TIMEOUT`
- `ENGINE_CRASH`
- `NONDETERMINISM_DETECTED`
- `SCENARIO_SETUP_FAILED`
- `ASSET_MISSING`
- `UNSUPPORTED_TASK`

Fehler werden nicht in normale Rewards umgewandelt. Ein Engine-Crash ist kein „Death Reward“, sondern ein Infrastrukturfehler und macht den Lauf ungültig.
