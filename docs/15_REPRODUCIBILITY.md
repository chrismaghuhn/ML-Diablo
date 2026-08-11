# 15 — Reproduzierbarkeit

## Reproduzierbarkeitsebenen

### Environment

- gepinnte DevilutionX-Revision;
- Buildfingerprint;
- Assetmodus;
- Task-/Contractversion;
- Seed;
- semantische Actions;
- deterministische Uhr.

### Daten

- Episode manifest;
- JSONL SHA-256;
- Datasetmanifest mit Episodehashes;
- unveränderliche Rohdaten;
- explizite Migrationen.

### Training

- vollständige Config und Hash;
- Codecommit;
- Python-/PyTorch-/CUDA-Version;
- RNG-Zustände;
- Actoranzahl/Epsilon;
- Replayparameter;
- Checkpointmanifest.

### Evaluation

- feste Seeds;
- greedy/stochastic Mode;
- exact checkpoint hash;
- Enginebuild;
- Reportcodeversion.

## Run-Verzeichnis

Empfohlen:

```text
runs/<run_id>/
  run_manifest.json
  resolved_config.yaml
  environment.json
  dataset_manifest.json
  logs/
  checkpoints/
  evaluation/
  diagnostics/
```

`run_id` ist nicht nur ein frei gewählter Name; es kombiniert Timestamp, Codecommit und kurzen Confighash.

## Seedhierarchie

Ein Masterseed wird deterministisch in Streams aufgeteilt:

- task/reset seed;
- actor exploration seed;
- network initialization;
- replay sampling;
- augmentation;
- evaluation seedset.

Keine globale implizite RNG-Nutzung. Jeder Prozess erhält seinen Stream.

## Enginebuild-Fingerprint

Mindestens:

- Upstream commit;
- Adapter commit;
- CMake options;
- Compilername/-version;
- Plattform/Architektur;
- relevante Dependencyversionen;
- hash des Environment-Binary;
- Licensefile hash.

## Konfigurationsauflösung

Training speichert die vollständig aufgelöste Config nach Defaults/Overrides. Nur CLI-Argumente zu speichern ist unzureichend.

## Deterministische GPU-Limits

Ein bitweises Trainingsergebnis über Hardware ist nicht immer realistisch. Daher unterscheiden wir:

- bitweiser Environment Replay;
- deterministischer CPU-Unit-Test;
- numerisch tolerante Modelltests;
- statistische Reproduktion über Trainingsseeds.

Abweichungen werden nicht verschwiegen, sondern im Runmanifest markiert.

## Upstream-Upgrades

Ein Upgrade erzeugt:

1. neuen Lock-Eintrag;
2. Build-/Lizenzprüfung;
3. Contracttest;
4. golden Seed replays;
5. Observationdiff;
6. Performancebenchmark;
7. neue Engine Compatibility ID.

Alte und neue Engineversionen werden nicht in demselben Replaybuffer gemischt, bevor Übergangskompatibilität bewiesen ist.

## Golden Trajectories

Für jeden Milestone existieren kleine, assetrechtlich zulässige oder lokal generierte Golden-Manifeste. In einer echten DevilutionX-Integration können Hashes/semantische Zustände lokal gehalten werden, falls öffentliche Artefakte problematisch wären.

## Experimentvorregistrierung

Für wichtige Vergleiche wird vor dem Test festgelegt:

- Hypothese;
- Methoden/Hyperparametersweep;
- Seedzahl;
- Primärmetrik;
- Stopkriterium;
- Statistik;
- Ausschlusskriterien.

Dies reduziert nachträgliches Cherry Picking.
