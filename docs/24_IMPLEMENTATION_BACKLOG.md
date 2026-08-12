# 24 — Implementierungsbacklog

Die Reihenfolge ist absichtlich environment-first. Ein Item gilt nur als abgeschlossen, wenn Code, Test, Dokumentation und reproduzierbarer Nachweis vorhanden sind.

## P0 — Releasefähigkeit des Scaffolds

- [x] Python-Paket und CLI
- [x] deterministischer Mock
- [x] JSONL-Trajektorie + Manifest + SHA-256
- [x] Candidate-Q-Referenzmodell
- [x] priorisiertes Sequenz-Replay
- [x] separater Demo-/Agent-Sampler
- [x] C++20-Vertragsbibliothek
- [x] JSON Schemas
- [x] ML-/Integrationsdokumentation
- [ ] echte DevilutionX-Bridge
- [ ] echter R2D3-Learner

## M0 — Engine Contract

1. Prozessstart und Healthcheck.
2. gepinnte Engine-/Adapterversion im Handshake.
3. kontrolliertes Fixture laden.
4. Seed-Injektion vor jeglicher relevanter RNG-Nutzung.
5. Observation v1 exportieren.
6. Legal Candidates erzeugen.
7. Candidate anwenden und bis Decision Boundary ticken.
8. Timeout/Crash/Protocol-Failure klassifizieren.
9. kanonischen Trajektorienhash vergleichen.
10. Leak-Tests und invalid-action Tests.

### M0.3 Evidence checkpoint

The first real action loop is implemented for the controlled
`combat.single_melee.v0` fixture: adjacent visible `MOVE_TO_TILE` candidate
generation, deterministic semantic IDs, candidate-set identity checks before
`MakePlrPath`, bounded native advancement to the next controllable boundary,
and the `dxai.probe.step.v1` evidence envelope. Persistent IPC, reset
isolation, replay, multi-step service lifetime, broader action families and
the global M0 gates remain open.

## M0.5 — Durchsatz und Replay

1. 1000 Episoden ohne Ressourcenleck.
2. Warm reset gegen Prozessneustart benchmarken.
3. Replay-Playback gegen aufgezeichnete semantische Aktionen.
4. deterministische Event-/Reward-Ableitung.
5. Batch-/Vector-Environment-Prozessmanager.
6. Speichernutzung und Episoden/s reporten.

## M1 — Combat-Slice

1. Safe-/Aggressive-/Random-Scripts.
2. Humandemo-Aufzeichnung im gleichen Candidate Space.
3. Demoqualitätsmetriken.
4. recurrent BC.
5. recurrent PPO-Baseline.
6. R2D2 ohne Demos.
7. R2D3-Demo-Ratio-Sweep.
8. mindestens fünf Trainingsseeds pro Konfiguration.
9. sealed test evaluation.
10. Video nur ergänzend, niemals Primärmetrik.

## M2 — Combat-Variabilität

- Nah-/Fernkampfgegner;
- mehrere Gegner;
- Engstellen und Türen;
- resistenz-/waffenabhängige Entscheidungen;
- Retreat und Tranktiming;
- Gegner-/Loadout-Generalisation;
- Curriculumregeln ohne Testseedkontakt.

## M3 — Exploration

- persistent bekannte Karte im Agentengedächtnis, nicht als Hidden-State-Leak;
- Frontierbaseline und A*;
- Tür-/Objektinteraktion;
- Dead-end-/Loop-Erkennung;
- Stairs-Erfolg;
- Ablation: LSTM vs externe Karte vs beides.

## M4 — Loot und Inventar

- Itemcandidate-Vertrag;
- regelbasierter Stat-/DPS-Baselinewert;
- learned item utility;
- Slot-/Gewichts-/Gold-Opportunity-Cost;
- sichere Equip-/Drop-/Sell-Aktionen;
- Gegenfaktische Itemevaluation nur über kontrollierte Engineklone.

## M5 — Stadt

- Händlerstate ohne versteckte zukünftige Rerolls;
- kaufen, verkaufen, reparieren;
- Return-to-town-Entscheidung;
- Budget-/Ressourcenplanung;
- Taskabschluss mit Dungeon-Rückkehr.

## M6 — Hierarchie

- feste Skills mit einheitlichem Termination Contract;
- Managerobservations und Optionmasken;
- SMDP-Returns mit Dauerdiscount;
- Manager-BC aus Scriptlabels;
- Manager-RL;
- End-to-End-Feintuning als Ablation.

## M7/M8 — Floors und Full Runs

- Save/restore nur für Trainingseffizienz, nicht als unmarkierter Testvorteil;
- Runmanifest und persistente Seedkette;
- Boss-/Quest-Slices;
- Death-/Recoverypolicy;
- normaler Warrior-Full-Run;
- Rogue/Sorcerer-Transfer erst danach.

## Schuldengrenzen

Nicht aufschieben:

- Vertragsversionen;
- Determinismustests;
- Seed-Splits;
- Reward-Komponenten;
- Lizenz-/Assetchecks;
- Ablationsplan;
- Fehlerklassifikation.

Darf aufgeschoben werden:

- verteilte Replayservices;
- Pixelencoder;
- World Models;
- grafisches Dashboard;
- Cloudorchestrierung;
- Multi-GPU.
