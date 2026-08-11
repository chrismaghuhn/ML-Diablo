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

Eine Engine pro Prozess ist robuster, kostet aber RAM. Start mit 2–8 Instanzen. Multiprocessing-Startmethode und CPU-Affinity werden gemessen. Ein Prozesspool kann nach Episode wiederverwendet werden, sofern Resetsoak sauber ist.

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

Der Scaffold-Sampler ist O(N). Produktionsoptionen:

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

„Steps per second“ ohne Definition der Decision Boundary ist nicht vergleichbar.
