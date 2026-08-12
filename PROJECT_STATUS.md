# Projektstatus des Scaffolds

Version: `0.1.0`

## Implementiert und lokal prüfbar

- strukturierte Observation-/Action-/Step-Verträge;
- Legal-Candidate-Sortierung und Validierung;
- deterministischer partiell beobachtbarer Mock-Slice;
- Random- und Heuristik-Agent;
- atomare JSONL-Trajektorien mit Manifest, Hashprüfung und Abbruchquarantäne;
- strikte JSON-/Payload-/Finite-Value-Verträge;
- Taskregistry mit getrennten Seedbereichen;
- priorisiertes Sequenz-Replay;
- separater Demonstrations-/Agent-Sampler;
- R2D3-Startkonfiguration;
- PyTorch Candidate-Q-Referenzmodell;
- C++20-Bridge-Contract;
- persistenter M0.4-Worker mit `dxai.process.v1`, Cold-Reset-Manager,
  Lifecycle-/Idempotenztests und kanonischem Trace-Hash;
- M0.5 `dxai.engine_replay.v1`, semantischer Replay-Auflösung,
  Prozess-Vektor-Manager sowie Soak-/Durchsatz-Harness und Diagnostik;
- Protobuf-Entwurf, JSON Schemas, CI und Runbooks.

## M0.1 lokal geprueft

- DevilutionX auf dem Commit aus `upstream.lock.toml` ausgecheckt und sauber
  reproduzierbar als Release-Build erzeugt;
- Debug-Testtargets mit aktiviertem `HeadlessMode` gebaut;
- 23 datenunabhaengige Headless-Testfaelle bestanden;
- `--help` und `--version` des gepinnten Binaries mit Exit-Code 0 gestartet.

Die vollstaendige Upstream-Testmatrix bleibt ohne Diablo-MPQs und Originaldaten
bewusst datenbegrenzt. Eine vollstaendige Observation-/Action-Bridge ist noch
nicht implementiert.

## M0.2 lokal geprueft

- read-only C++-Probe gegen den gepinnten Upstream-Release-Build gebaut;
- GOG-Datenpfad und lose DevilutionX-Core-Assets als getrennte Eingaben
  verwendet;
- echte `dxai.observation.v1` mit Player-State, 121 lokalen Tiles und 6
  Inventareintraegen erzeugt;
- Sichtbarkeitsfilter fuer Entities und begrenztes Tilefenster aktiv;
- gleiche Seed-Ausfuehrungen byte-identisch geprueft;
- fehlender Assetpfad als strukturierter `ASSET_DATA_UNAVAILABLE`-Fehler
  geprueft;
- rohe Probeausgabe gegen die lokale JSON-Schema-Registry validiert.

Die Probe ist absichtlich noch kein Environment: Candidate-Ausfuehrung,
`step`, Decision-Boundary-Fortschritt, IPC und echte Transition-/Replay-Gates
folgen in M0.3/M0.

## M0.4 lokal geprueft

- striktes `dxai.process.v1` JSON-Lines-Framing mit 1 MiB Limit;
- geschlossene Health-/Reset-/Step-/Error-Verträge ohne Reward oder Terminal;
- `READY`, `EPISODE_ACTIVE` und `FAULTED` Lifecycle-Gates;
- 128-entry Request-Cache mit exact duplicate replay, Payload-Reuse- und
  Eviction-Schutz;
- Python-Manager mit Health-vor-Reset, Worker-Ersetzung bei Cold Reset,
  Timeout-/EOF-/Malformed-Response-Isolation und idempotentem Close;
- kanonischer Trace-Hash, der nur Lifecycle-Metadaten normalisiert;
- native und Python Contract-/Lifecycle-Tests sowie Release-Build der Probe.

### M0.4 Real-Asset Acceptance Gate (2026-08-12)

- Health/Handshake gegen den gepinnten DevilutionX-Release bestanden;
  `dxai.process.v1`, Adapter `m0.4`, Observation/Action `v1` und
  `combat.single_melee.v0` wurden bestätigt;
- Reset mit Seed `123` auf `EPISODE_ACTIVE`, `step_id=0`, Position `(79,58)`,
  `engine_tick=0` und acht nativen `MOVE_TO_TILE`-Kandidaten bestanden;
- 32 erfolgreiche Steps im selben nativen Worker bestanden: `0 -> 32`,
  monotoner Engine-Tick `0 -> 320`, Position `(79,58) -> (75,58)`;
- Duplicate-Exactly-Once bestanden: identische Antwort, einmaliger Schritt,
  einmalige Engine-Tick-/Positionsänderung; geänderte Payload mit derselben
  Request-ID wurde als `REQUEST_ID_REUSE` abgewiesen;
- `STALE_STEP`- und `INVALID_CANDIDATE`-Reject-Oracles bestanden, jeweils mit
  identischem Kontroll-Hash nach dem folgenden gültigen Schritt;
- stale Episode, neue Same-Seed-Episode-IDs, A -> B -> A Cold-Reset und
  unabhängige Same-Seed-32-Step-Traces bestanden;
- nicht-sensitive kanonische Evidenz: 32-Step
  `4e906aa70e2ad64ec790074d55a15802192aae8b1508708551a65a476825d336`,
  A1/A2 `92b4939801f88937fecaea40c0d172aca36b98fa0ec27cd8f0deea5b603cc33a`,
  Reject-Oracle `533715ff5eb3f81c547ac6e3569fae1621526ce1f73ccb0fc5b007c72f2f7589`;
- stdout enthielt ausschließlich Protocol-Frames, stderr keine sensiblen
  Pfade, Worker wurden bei Cold Reset und idempotentem Close beendet;
- externe Originaldaten, Core-Assets, Runtime-DLLs und temporäre Spielausgaben
  blieben außerhalb des Repositories.

## M0.5 implementiert, Realabnahme ausstehend

Die Repository-Implementierung umfasst das geschlossene
`dxai.engine_replay.v1`-Format, zentrale Schema-/Validator-Registrierung,
atomare manifest-lastige Veröffentlichung, fail-closed Playback mit
semantischer Candidate-Auflösung, den synchronen 1/2/4-Slot-
Prozessmanager sowie beobachtende Soak-/Durchsatzmetriken. Rewards,
Terminal-/Truncation-Flags, Engine-Events und Warm Reset bleiben außerhalb
des Scopes.

Die Real-Gates (100 Aufzeichnungen, 1.000 Playbacks, 10.000 gültige Steps,
1.000 Cold-Reset-Episoden und parallele Real-Worker) werden nur mit externen
Benutzerinputs ausgeführt. In der aktuellen Session fehlen diese Inputs; der
Harness meldet daher `PENDING_EXTERNAL_INPUTS` und `real_acceptance=NOT_RUN`.
M0.5 ist damit implementiert, aber noch nicht vollständig real akzeptiert.

## Noch nicht implementiert

- globale M0-Abnahme und M0.5-Real-Gates mit vollständigem externem
  Replay-/Reset-/Soak-/Throughput-Lauf;
- automatischer Fixturebau im Upstream;
- Human-Demo-Recorder;
- BC-Trainingsloop;
- verteilte Actors/Learner;
- vollständiger R2D2/R2D3-Learner;
- recurrent PPO-Baseline;
- Exploration/Loot/Town/Full-Run-Tasks.

## Aussagegrenze

Dieses ZIP ist ein ausführbares **Forschungs- und Integrationsscaffold**. Es enthält keinen bereits trainierten Diablo-Agenten und beweist noch nicht, dass das empfohlene Verfahren Diablo besiegt. Es reduziert die größten frühen Risiken: falsche Schnittstelle, Hidden-State-Leaks, nicht reproduzierbare Daten, inkonsistente Aktionsräume und eine vorschnelle Algorithmuswette.
