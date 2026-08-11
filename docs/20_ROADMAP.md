# 20 — Roadmap

## Sequenz

```text
M0 Contract Foundation
  ↓
M1 Single Melee Combat
  ↓
M2 Room Combat
  ├──────────────┐
  ↓              ↓
M3 Exploration   M4 Loot/Equipment
  └──────┬───────┘
         ↓
M5 Town Loop
         ↓
M6 Integrated Floor
         ↓
M7 Multi-Level Run
         ↓
M8 Warrior Full Run
         ↓
M9 Generalization / Research Branches
```

## M0 — Contract Foundation

### Ziel

Eine echte DevilutionX-Instanz kann deterministisch resetten, semantische legale Candidates ausgeben, eine Auswahl ausführen und replaybare Trajektorien schreiben.

### Deliverables

- gepinnter Upstreambuild;
- separater AI-Environment-Binary;
- Health/Reset/Step IPC;
- `bridge.v1`, `observation.v1`, `action.v1`;
- initialer Combatfixture;
- State-/Observationhash;
- JSONL Recorder/Reader;
- Pythonclient;
- determinism/observability/legality tests;
- throughput benchmark;
- Lizenz-/Assetaudit.

### Nicht enthalten

- neural policy;
- breites Inventar-/Towninterface;
- Full-Run-Saves;
- Pixelobs.

### M0-Slice-Reihenfolge

Der Contract-Foundation-Milestone wird in kleinen Engine-Grenzen abgearbeitet:

```text
M0.1  gepinnter Upstream-Build und Headless-Smoke
  |
M0.2  echte read-only Observation
  |
M0.3  legale Candidates, candidate_id und ein semantischer Step
  |
M0.4  Decision-Boundary-, State-Hash- und Replay-Gates
  |
M0.5  echte Trajektorie gegen die versionierten Datenvertraege
```

M0.2 ist dabei noch kein Abschluss des globalen M0. Es beweist nur, dass der
Engine-Prozess reproduzierbar initialisiert und ein begrenztes
player-observable JSON erzeugt werden kann. ML-Training beginnt erst nach den
folgenden Action-, Reset-, Legalitaets- und Replay-Gates.

### Exit

Alle Gates in `21_MILESTONE_ACCEPTANCE.md` M0 bestehen.

## M1 — Single Melee Combat

### Ziel

Lern- und Baselinepipeline auf einem kontrollierten echten Engine-Task.

### Deliverables

- Taskfixture `combat.single_melee.v0`;
- Random/Safe/Aggressive Scripts;
- 300+ diverse Demoepisoden als Start;
- recurrent BC;
- recurrent PPO Baseline;
- Candidate-R2D2;
- Candidate-R2D3 Demo-Ratio-Sweep;
- Evaluation auf 128 Testseeds;
- Q-/Action-/Failurediagnostik;
- kleiner Demo-Viewer/Trajectory Inspector.

### Forschungshypothese

Demos reduzieren Zeit bis zur robusten Erfolgsrate; R2D3 übertrifft BC in Recoveryzuständen und R2D2 bei frühem Lernen.

## M2 — Room Combat

### Ziel

Mehrere Gegner, Targetauswahl, Retreat, Potion Timing und gemischte Gegnerprofile.

### Deliverables

- parametrische Difficulty;
- Kandidaten für mehrere Targets;
- safety/recovery Demos;
- Entity-Setencoder;
- Death-Risk/Threatdiagnostik;
- Ablation LSTM vs. feed-forward;
- optionale distributional Q-Vorstudie.

### Gate

Erfolg nicht nur gegen einen memorisierten Gegnertyp; Performance nach Gegnerfamilie reporten.

## M3 — Exploration

### Ziel

Unbekannten Dungeon systematisch erkunden und Treppe finden.

### Deliverables

- sichtbar/erkundet/unknown Vertrag;
- Door/Object/Stairs Candidates;
- klassischer Pathcontroller;
- Frontier Script Baseline;
- recurrent Explore Skill;
- explizite Map-Memory-Visualisierung;
- memory stress tasks;
- Coverage/Backtrackingmetriken.

### Entscheidung

Nach M3 wird geprüft, ob LSTM plus beobachtete Automap reicht oder explizites neural/symbolic Map Memory nötig ist.

## M4 — Loot und Equipment

### Ziel

Items unter Build-, Inventar- und zukünftiger Kampfrelevanz bewerten.

### Deliverables

- Inventory/Equipment Observation;
- Pickup/Equip/Unequip/Drop Candidates;
- identifiziert/unidentifiziert Audit;
- Itemsetencoder;
- scripted item evaluator baseline;
- supervised outcome/value task;
- downstream Combat Evaluation;
- Inventarplatzierungscontroller.

### Anti-Ziel

Kein isolierter „höchste DPS“-Classifier als endgültiger Lootagent.

## M5 — Town Loop

### Ziel

Autonom entscheiden, wann Stadt nötig ist und dort kaufen, verkaufen und reparieren.

### Deliverables

- modal Store Context;
- Store Candidates;
- Budget-/Repair-/Potiontasks;
- Return-to-level contract;
- Town Script Baselines;
- Managerfeatures für Townneed;
- ökonomische Metriken.

## M6 — Integrated Floor

### Ziel

Fight, Explore, Loot und Retreat/Town werden in einem Floor kombiniert.

### Stufe 1

Fester, regelbasierter Skillrouter als Integrationsbaseline.

### Stufe 2

Gelernter Manager über Options; Skills zunächst gefroren.

### Stufe 3

Kontrolliertes gemeinsames Feintuning.

### Deliverables

- Skill API und Termination Reasons;
- Manager Replay;
- oscillation/loop detector;
- Optionduration discount;
- Integrationsevaluation;
- Ablation learned vs. fixed router.

## M7 — Multi-Level Run

### Ziel

Persistente Charakterentwicklung über mehrere Floors und Stadtfahrten.

### Deliverables

- Runstate/Checkpointing;
- langfristige Memoryzusammenfassung;
- Progression/Stats;
- Death-/Restartpolicy;
- Replay über lange Episoden;
- Runfortschrittsmetriken;
- Curriculum gegen Forgetting.

### Möglicher Explorationzweig

Erst hier, falls nötig: episodischer Noveltybonus/NGU-artige Akteure und Self-Imitation erfolgreicher Runfragmente.

## M8 — Warrior Full Run

### Ziel

Frischer Warrior auf Normal bis Diablo.

### Deliverables

- finaler Taskvertrag;
- Boss-/Quest-/Leveltransition Coverage;
- sealed Testseedset;
- robuste Killrate mit CI;
- Failure taxonomy;
- vollständige Ablationen;
- reproduzierbarer Demo- und Evaluationrelease;
- legal/asset review.

„Ein erfolgreicher Run“ ist ein Zwischenereignis, kein M8-Abschluss.

## M9 — Generalisierung und Forschung

Mögliche unabhängige Branches:

- Rogue/Sorcerer Transfer;
- Multi-task shared encoder;
- Offline RL aus großem Datensatz;
- NGU/Agent57-artige Exploration;
- DreamerV3-artiges lokales World Model;
- MuZero/search für Combat;
- Pixelstudent via Distillation;
- Risk-sensitive/distributional policies;
- procedurally generated open clone testbed.

Jeder Branch benötigt eine eigene Baseline, Hypothese und Stopregel.

## Arbeitsorganisation

Pro Milestone:

```text
Design checkpoint
→ Contract/Schema
→ Tests/Fixtures
→ Baselines
→ Data
→ ML
→ Evaluation/Ablation
→ Acceptance report
→ erst dann nächster Milestone
```

Keine parallele Entwicklung von drei neuen Actionfamilien ohne jeweils grüne Contracttests.
