# 16 — Teststrategie

## Testpyramide

### Unit Tests

- Dataclassvalidierung;
- Candidate requirements;
- kanonische Serialisierung;
- Featuredimensionen;
- n-Step Return;
- Replayprioritäten;
- Masking im Candidate-Q-Netz;
- Taskseed-Trennung.

### Contract Tests

- dense Candidate IDs;
- stale Step rejection;
- Step-ID-Inkrement;
- keine Action nach Terminal;
- Transition Round-trip;
- Manifestchecksum und traversal-sicherer Trajektorienpfad;
- abgebrochene Episode erzeugt kein ingestierbares Manifest;
- striktes JSON ohne `NaN`/`Inf`;
- Protocol-/Schema-Versionen.

### Determinism Tests

- zwei Mock-/Engineinstanzen, gleicher Seed und Actions;
- Reset nach vorheriger Episode;
- Replay nach Prozessneustart;
- Hashvergleich;
- Demo-Mode-Referenz.

### Observability Tests

Gezielte Fixtures:

- Gegner hinter Wand/außer Sicht;
- Item unerforscht;
- nicht identifiziertes Item;
- Store geschlossen;
- unsichtbare Missile;
- verstecktes Questflag.

Test prüft nicht nur, dass Entity fehlt, sondern dass Tile occupancy, Event, Candidatefeatures und Attribute den State nicht indirekt verraten.

### Integration Tests

- echter Environment-Binary startet headless;
- Health/Reset/Step;
- Taskfixture;
- 1.000 Steps ohne Crash;
- Timeoutkill/restart;
- mehrere parallele Prozesse;
- Trajektorie validiert.

### Soak Tests

- 10.000+ Episoden;
- Speicherwachstum;
- File descriptor leaks;
- Crash-/Timeoutquote;
- Resetkontamination;
- Durchsatzverteilung.

## Property Tests

Auch ohne Hypothesis können randomisierte Tests erzeugen:

- beliebige legale Candidatewahl crasht nicht;
- illegaler ID-Bereich wird abgelehnt;
- Candidatepermutation permutiert Modelloutputs;
- Serialisierung ist idempotent;
- Replaysequenzen kreuzen keine Episode;
- Importanceweights liegen in `(0,1]`.

## Modelltests

- Shapes für variable Candidatezahlen;
- Paddingmasken;
- kein NaN/Inf;
- Gradientflow;
- LSTM Hidden Shapes;
- all-invalid mask wirft Fehler;
- deterministischer Forward unter Seed;
- Checkpoint load/save;
- Overfit auf winzigen Demonstrationsbatch.

Ein „overfit one batch“-Test ist besonders wertvoll: Schafft BC dies nicht, ist das Training falsch, nicht die Datenmenge.

## Learner-Integration

- synthetischer MDP mit bekanntem Optimum;
- Mock Combat Lernkurve;
- Targetbootstrapping an Terminal/Truncation;
- Demo-Ratio tatsächlich erreicht;
- Priority Update korrekt;
- Resume reproduziert nächsten Step;
- Actorweights atomar.

## CI-Stufen

```text
PR:       format/lint + unit + schema + C++ contract
Nightly:  torch model + determinism + smoke episodes
Weekly:   real local engine integration/soak (asset-dependent, privat)
Release:  full contract matrix + benchmark + license audit
```

Öffentliche CI darf keine proprietären Assets voraussetzen. Assetabhängige Tests laufen lokal oder in einer rechtlich geeigneten privaten Umgebung.

## Failure Policy

- Illegal Action: harter Testfehler;
- Hidden-info violation: harter Testfehler;
- Checksum mismatch: Datenquarantäne;
- Engine timeout/crash: Episode ungültig, Incidentbundle;
- Training NaN: Checkpoint nicht veröffentlichen;
- Testseed leakage: Experiment verwerfen.
