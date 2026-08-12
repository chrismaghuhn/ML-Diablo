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

Die user-owned Runtime-/Asset-/Datenpfade waren in der lokalen Umgebung nicht
als `DXAI_M04_*` konfiguriert. Daher sind 32 echte Steps in einem PID,
native Duplicate-Replay und A -> B -> A im echten DevilutionX-Prozess noch
nicht bestätigt.

## Noch nicht implementiert

- globale M0-Abnahme inklusive Real-Asset-32-Step-/Replay-/Reset-Gates;
- automatischer Fixturebau im Upstream;
- Human-Demo-Recorder;
- BC-Trainingsloop;
- verteilte Actors/Learner;
- vollständiger R2D2/R2D3-Learner;
- recurrent PPO-Baseline;
- Exploration/Loot/Town/Full-Run-Tasks.

## Aussagegrenze

Dieses ZIP ist ein ausführbares **Forschungs- und Integrationsscaffold**. Es enthält keinen bereits trainierten Diablo-Agenten und beweist noch nicht, dass das empfohlene Verfahren Diablo besiegt. Es reduziert die größten frühen Risiken: falsche Schnittstelle, Hidden-State-Leaks, nicht reproduzierbare Daten, inkonsistente Aktionsräume und eine vorschnelle Algorithmuswette.
