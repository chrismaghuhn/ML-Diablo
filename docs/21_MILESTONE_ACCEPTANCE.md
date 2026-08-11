# 21 — Milestone-Abnahmekriterien

## Globale Regeln

Ein Milestone ist nur abgeschlossen, wenn:

- Code, Contract und Docs übereinstimmen;
- Tests auf dokumentiertem Build grün sind;
- keine offene kritische Beobachtungs-/Legalitätslücke besteht;
- Daten und Reports Hashes/Manifeste besitzen;
- bekannte Einschränkungen explizit sind;
- Regression auf frühere Tasks geprüft wurde.

## M0 — Contract Foundation

### Build

- [ ] Upstreamcommit und Licensefile hash protokolliert.
- [ ] Normaler DevilutionX-Build bleibt ohne AI-Flag unverändert.
- [ ] AI-Environment-Binary startet ohne UI.
- [ ] fehlende Assets erzeugen strukturierten Fehler, keinen Dialog.

### Reset/Determinismus

- [ ] gleiche Build-ID + Task + Seed → gleicher Initialhash.
- [ ] gleiche Actions → gleicher Transition-/Statehash.
- [ ] 1.000 Golden-Replays ohne Diff.
- [ ] alternierende Seeds zeigen keine Resetkontamination.
- [ ] Uhr und RNG sind dokumentiert.

### Step/Legalität

- [ ] Candidates dicht, eindeutig und deterministisch sortiert.
- [ ] jede angebotene Aktion wird vom Enginepfad akzeptiert.
- [ ] 10.000 Random-Legal-Steps ohne illegalen Command.
- [ ] stale/wrong episode/wrong candidate Requests werden abgelehnt.
- [ ] nach Terminal ist Step verboten.

### Observability

- [ ] hidden monster fixture.
- [ ] hidden item fixture.
- [ ] unknown tile fixture.
- [ ] keine indirekten Leaks über occupancy/events/features.
- [ ] Feldprovenienz dokumentiert.

### Daten

- [ ] Transition Round-trip.
- [ ] Manifest SHA-256.
- [ ] Replay aus Datei reproduziert Run.
- [ ] Schema validator grün.
- [ ] keine proprietären Assets im Artefakt.

### Betrieb

- [ ] Stepdurchsatz median/p95 dokumentiert.
- [ ] 10.000-Episoden-Soak ohne unbounded memory growth.
- [ ] Timeout-/Crashrecovery.
- [ ] parallele Prozessinstanzen isoliert.

## M0.2 — First Real Observation Slice

This is an evidence checkpoint inside M0, not a declaration that the global
M0 contract foundation is complete.

- [x] exact upstream commit checked before the external probe run;
- [x] Release probe builds as a separate executable without tracking
  DevilutionX or proprietary Diablo data;
- [x] player state, bounded visible tiles, visible entities and sanitized
  inventory exported as `dxai.observation.v1`;
- [x] raw probe stdout validates through the repository's local JSON Schema
  registry;
- [x] same seed produces byte-identical stdout across two clean runtime roots;
- [x] missing asset data returns structured `ASSET_DATA_UNAVAILABLE` without a
  UI dialog;
- [x] Python client parses the real probe output and validates the immutable
  observation contract;
- [ ] legal candidate generation and candidate execution;
- [ ] transition to the next decision boundary;
- [ ] full reset/step state hashes, replay and IPC gates.

Evidence from the local run on 2026-08-12: seed `123`, player `(79, 58)`,
121 local tiles, 0 visible entities at the initial spawn and 6 inventory
entries. The identical-output SHA-256 was
`eadf3b0cb4beb8f7c8ca05c0746663de084430d95799908a24ab4b05cd531cb2`.

## M1 — Single Melee

- [ ] Random, Safe und Aggressive Baselines reportet.
- [ ] Demo-Coveragebericht.
- [ ] BC overfit-one-batch und Validation funktionieren.
- [ ] recurrent PPO Report.
- [ ] R2D2 Report.
- [ ] mindestens sechs Demo-Ratios für R2D3.
- [ ] mindestens drei Trainingsseeds pro Hauptmethode.
- [ ] 128 feste Testseeds.
- [ ] keine Illegal Actions/Engine Faults.
- [ ] primäre Hypothese mit CI beantwortet.

Vorgeschlagenes Promotiongate: ≥90 % Success, keine kritische Ressourcenregression, klare Verbesserung über Script-/BC-Baselines oder dokumentierte Pivotentscheidung.

## M2 — Room Combat

- [ ] multiple Targetcandidate correctness.
- [ ] mindestens drei Gegnerprofile.
- [ ] Retreat/Potion Recoveryfälle.
- [ ] Entityencoder-Ablation.
- [ ] LSTM-Ablation.
- [ ] Performance pro Difficulty/Gegnerfamilie.
- [ ] keine einzige dominierende Spawnvorlage.

## M3 — Exploration

- [ ] unbekannte Karte ohne Leak.
- [ ] Frontier Script Baseline.
- [ ] 128 unseen floors.
- [ ] Stair Success, Coverage, Backtracking.
- [ ] memory stress fixture.
- [ ] Map Memory visualisierbar/auditierbar.

## M4 — Loot

- [ ] Itemknowledge respektiert Identification.
- [ ] dynamische Inventory Candidates.
- [ ] downstream Combatwert gemessen.
- [ ] Inventaroverflow korrekt.
- [ ] Item-/Buildsplit verhindert triviales Memorieren.

## M5 — Town

- [ ] modale Contextgrenzen.
- [ ] Budget/Store legality.
- [ ] korrekte Rückkehr.
- [ ] unnötige Transaktionen/Stadtfahrten metrisch.

## M6 — Integration

- [ ] fester Router als Baseline.
- [ ] Optionsvertrag/Termination.
- [ ] gelernter Manager schlägt oder erreicht Router.
- [ ] keine Skilloscillation/Deadlock.
- [ ] duration-aware discount geprüft.
- [ ] frühere Skills regressieren nicht über Gate.

## M7/M8 — Runs

- [ ] persistenter Runstate/replaybar.
- [ ] sealed test protocol.
- [ ] Failuretaxonomy.
- [ ] Full-Run-Success über Seedset, nicht Video.
- [ ] Compute-/Demo-Kosten reportet.
- [ ] Lizenz-/Assetreleaseaudit.
