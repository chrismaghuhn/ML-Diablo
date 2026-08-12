# 17 — Performance und Skalierung

## Wahrscheinlicher Flaschenhals

Früh ist nicht das neuronale Netz, sondern die Engine-Simulation plus Prozess-/IPC-Overhead der Engpass. Deshalb zuerst messen:

- Resetzeit;
- mediane/p95 Stepzeit;
- Engine-Ticks pro Sekunde;
- Observationbytes;
- Candidatezahl;
- CPU/RAM pro Instanz;
- Crash-/Timeoutquote;
- Recorderdurchsatz.

## Optimierungsreihenfolge

1. Rendering/Audio/UI im Environment-Build deaktivieren;
2. deterministische simulierte Zeit statt realem Sleep;
3. unnötige Asset-/UI-Arbeit vermeiden;
4. Observationdiff/Compact wire encoding;
5. mehrere Prozesse parallel;
6. Batchinference über Actoranfragen;
7. Replayservice optimieren;
8. erst danach Modellquantisierung oder größere GPU.

## Prozessmodell

Eine Engine pro Prozess ist robuster, kostet aber RAM. M0.5 stellt dafür einen
synchronen Vector-Manager mit einem bestehenden M0.4-Worker pro Slot bereit.
Gemessen werden Worker-Start, Health, Cold Reset, Step-Batch, Steps/s und
Ressourcen für 1/2/4 Slots. Warm reset wird nicht als synthetischer
Prozesspoolvorteil benchmarked, solange kein vollständiger nativer
Teardown/Reinit-Pfad bewiesen ist.

## Inference

Optionen:

- jeder Actor besitzt CPU-Modellkopie;
- zentraler GPU-Inferenceserver mit Microbatching;
- hybrider lokaler Encoder + zentraler recurrent Head.

Für kleine Modelle und langsame Engine ist CPU-Inference oft ausreichend. Zentralisierung lohnt erst, wenn Messungen GPU-Batching rechtfertigen.

## Observationgröße

Volle redundante JSON-Trajektorien sind Auditformat, nicht optimaler Onlinetransport. IPC nutzt binäres Protobuf oder ähnlich. Replay kann später komprimierte Arrays/Columnar Storage verwenden.

Kompression darf nicht zu undokumentiertem Quantisierungsverlust führen. Rohwerte und Featureversion bleiben nachvollziehbar.

## Replay

Der Engine-Replay-Pfad ist ein Audit-/Reproduzierbarkeitsformat, kein
Trainingsreplay. Der Resolver scannt die vollständige aktuelle Candidate-Liste
und sendet die neu aufgelöste ID. Produktionsoptionen für den separaten
Trainings-Sampler sind:

- Sum/Segment Tree;
- Reverb-artiger lokaler Service;
- memory-mapped Sequenzblöcke;
- getrennte Agent-/Demo-Tables;
- asynchrone Priority Updates.

Replay muss Backpressure, Eviction und Datasetprovenienz sichtbar machen.

## Skalierungsstufen

### Lokal klein

- 2 Actors;
- CPU Inference;
- ein GPU/CPU Learner;
- in-process Replay;
- M1/M2.

### Workstation

- 8–32 Actors;
- batch inference;
- dedizierter Replayprozess;
- M3–M6.

### Mehrere Maschinen

Erst falls Full-Run-Datenbedarf dies belegt:

- versionierter Actorservice;
- Netzwerksecurity;
- zentrale Artefaktspeicherung;
- deterministische Buildimages;
- Monitoring.

Die Architektur wird providerunabhängig gehalten. Kaggle/Colab können Learnerjobs ausführen, aber die lizenz-/assetabhängigen Engine-Akteure müssen separat und regelkonform betrieben werden.

## Benchmarks

Jeder Performancebericht nennt:

- Hardware;
- OS/Compiler;
- Enginebuild;
- Task;
- Actorzahl;
- Headlessoptionen;
- Modell;
- Median/p95;
- Fehlerquote;
- Observation- und Replayvolumen.

Der M0.5-Report nennt zusätzlich Startup-, Health-, Reset- und Step-Latenzen,
Median/p95/p99, strukturierte Fehlercodes und verfügbare
Ressourcen-/Runtime-Verzeichnis-Samples. Fehlende Plattformmetriken bleiben
`UNAVAILABLE`; es werden keine Schwellenwerte erfunden.

„Steps per second“ ohne Definition der Decision Boundary ist nicht vergleichbar.
