# Trajektorienvertrag

## Layout

```text
episode-directory/
  manifest.json
  transitions.jsonl
```

`transitions.jsonl` wird zunächst temporär geschrieben, `fsync`-fähig geschlossen
und atomar umbenannt. Das Manifest wird ebenfalls über eine temporäre Datei und
atomaren Rename veröffentlicht. Erst ein vollständiges `manifest.json` macht den
Ordner zu einem gültigen Episode-Artefakt.

## Transition

Eine Transition enthält:

- vollständige Observation vor der Entscheidung;
- gewählten Candidate inklusive Semantik;
- Reward und Komponenten/Info;
- nächste Observation;
- terminated/truncated;
- Behavior-Metadaten, etwa Policyversion und epsilon.

`dxai.engine_replay.v1` ist davon getrennt. Ein Engine-Replay-Schritt enthält
keine Reward-, Terminal-, Truncation-, Behavior- oder TD-Felder und darf nicht
als Trainingstransition oder Prioritäts-Replaybuffer-Eintrag ingestiert werden.

## Invarianten

- Step IDs beginnen bei null und sind lückenlos;
- Action ist in der vorherigen Observation legal und identisch;
- Episode-/Task-/Seedfelder stimmen durchgehend überein;
- keine Transition nach Terminal;
- Summe der Rewards entspricht Manifest;
- Hash stimmt;
- Rohdaten werden nicht in-place editiert.

## Provenienz

Manifest nennt Datenquelle `AGENT`, `SCRIPTED`, `HUMAN` oder `DEMONSTRATION`, Engine-/Adapterstand und Contractversionen. Human-Daten dürfen zusätzliche Consent-/Sessionmetadaten separat tragen.

## Abbruchsemantik

Ein Exception-, Crash- oder Contractfehler publiziert keine Teiltrajektorie. Der
Recorder schließt und verwirft temporäre/finale Dateien, sofern noch kein gültiges
Manifest veröffentlicht wurde. Collector und Replay dürfen ausschließlich Ordner mit
validiertem Manifest und passendem SHA-256 ingestieren. `NaN` und `Inf` sind in JSON,
Rewards, Features und Metriken verboten.
