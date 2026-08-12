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

## M0.4 Evidence checkpoint

The repository now contains a persistent one-episode native worker and Python
cold-reset manager. The `--env-stdio` mode exposes strict
`dxai.process.v1` JSON-Lines with a 1 MiB body limit, explicit `READY`,
`EPISODE_ACTIVE` and `FAULTED` states, Health/Reset/Step/Error responses,
process-unique episode IDs, step/candidate identity checks, a bounded 128-entry
request cache, and stdout/stderr separation. The worker reuses the M0.3
initialization, candidate generation, semantic `MakePlrPath` execution,
decision-boundary advancement and observation serialization paths.

The Python manager replaces the worker for every Reset and treats timeout,
EOF, crash and malformed responses as unusable-worker conditions. M0.4 does
not add rewards, terminal flags, learner paths, warm reset, broader actions,
parallel workers or replay storage. The repository-only tests and builds are
verifiable, and the M0.4 real-asset evidence is recorded in
`PROJECT_STATUS.md` and `RELEASE_VALIDATION.md`. See
[`docs/runbooks/M04_PERSISTENT_ENVIRONMENT.md`](runbooks/M04_PERSISTENT_ENVIRONMENT.md).

## M0.5 — Durchsatz und Replay

M0.5 implements the environment-reproducibility slice without redefining
M0.4:

1. registered `dxai.engine_replay.v1` artifacts with full closed semantic
   actions, atomic manifest-last publication and strict validation;
2. replay by current candidate-set resolution, with first-step
   `REPLAY_DIVERGENCE` and fail-closed playback;
3. cold-reset, legal-step, long-worker and throughput harness modes, including
   startup, Health, Reset, Step and 1/2/4-slot process-isolation measurements;
4. a synchronous vector manager composed from existing M0.4 environments and
   observational resource/failure diagnostics.

Warm reset, rewards, terminal/truncation flags and engine-event derivation
remain deferred. The real 100-recording/1,000-playback, 10,000-Step,
1,000-episode and parallel-worker gates require external user-owned inputs and
are reported as pending when those inputs are absent. See
[`docs/runbooks/M05_REPLAY_SOAK_THROUGHPUT.md`](runbooks/M05_REPLAY_SOAK_THROUGHPUT.md).

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
