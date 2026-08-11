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
- Protobuf-Entwurf, JSON Schemas, CI und Runbooks.

## M0.1 lokal geprueft

- DevilutionX auf dem Commit aus `upstream.lock.toml` ausgecheckt und sauber
  reproduzierbar als Release-Build erzeugt;
- Debug-Testtargets mit aktiviertem `HeadlessMode` gebaut;
- 23 datenunabhaengige Headless-Testfaelle bestanden;
- `--help` und `--version` des gepinnten Binaries mit Exit-Code 0 gestartet.

Die vollstaendige Upstream-Testmatrix bleibt ohne Diablo-MPQs und Originaldaten
bewusst datenbegrenzt. Eine echte Observation-/Action-Bridge ist weiterhin nicht
implementiert.

## Noch nicht implementiert

- echte DevilutionX-Bridge;
- automatischer Fixturebau im Upstream;
- Human-Demo-Recorder;
- BC-Trainingsloop;
- verteilte Actors/Learner;
- vollständiger R2D2/R2D3-Learner;
- recurrent PPO-Baseline;
- Exploration/Loot/Town/Full-Run-Tasks.

## Aussagegrenze

Dieses ZIP ist ein ausführbares **Forschungs- und Integrationsscaffold**. Es enthält keinen bereits trainierten Diablo-Agenten und beweist noch nicht, dass das empfohlene Verfahren Diablo besiegt. Es reduziert die größten frühen Risiken: falsche Schnittstelle, Hidden-State-Leaks, nicht reproduzierbare Daten, inkonsistente Aktionsräume und eine vorschnelle Algorithmuswette.
