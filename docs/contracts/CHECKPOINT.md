# Checkpointvertrag

Ein Checkpoint ist mehr als Gewichte. Er besteht aus:

```text
checkpoint/
  manifest.json
  model.safetensors oder model.pt
  optimizer.pt          # optional, intern
  config.resolved.yaml
  metrics.json
```

## Manifestpflichten

- Run ID und Learnerstep;
- Modellklasse und Architekturhash;
- Observation-/Action-/Task-/Rewardversionen;
- Upstream-/Adapterrevision;
- Hashes von Config und Gewichten;
- Trainseed und Datensatz-/Replayprovenienz;
- Metriken auf Validation, niemals nachträglich umetikettiert.

## Laden

Unbekannte Majorversion oder Dimensionsinkompatibilität führt zu einem harten Fehler. Eine automatische partielle Gewichtsübernahme benötigt einen expliziten Migrationsbericht.

## Releasecheckpoint

Ein Releasecheckpoint ist immutable, besitzt eine Evaluation auf versiegelten Seeds und enthält keine proprietären Assets oder Rohtrajektorien.
