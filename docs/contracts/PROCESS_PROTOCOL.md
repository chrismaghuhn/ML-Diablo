# Prozess- und IPC-Vertrag

## Zustandsautomat

```text
STARTING → READY → EPISODE_ACTIVE → TERMINAL → READY
                 ↘ FAULTED → STOPPED
```

## Handshake

Der Prozess meldet:

- protocol version;
- adapter version/commit;
- DevilutionX commit;
- build fingerprint;
- unterstützte Task-/Contractversionen;
- optionale Features;
- PID nur zu Diagnosezwecken.

## Requests

`ResetRequest` und `StepRequest` tragen eindeutige `request_id`. Step trägt zusätzlich `episode_id`, `expected_step_id` und `candidate_id`.

## Idempotenz

- Ein bereits erfolgreich beantworteter Request darf bei Retry dieselbe Antwort liefern oder eindeutig als Duplicate behandelt werden.
- Stale/out-of-order Steps werden abgelehnt.
- Nach Timeout ist der Zustand unbekannt; die Instanz wird nicht blind weiterverwendet, sondern neu gestartet oder über einen sicheren Sync-Mechanismus geprüft.

## Transport

v1 kann stdio, Unix Domain Socket oder Named Pipe nutzen. Das Protobuf in `protocol/` beschreibt die logische Nachricht, nicht zwingend die erste Serialisierung. JSON ist für Bring-up erlaubt, solange Framing und Größenlimits eindeutig sind.

## Limits

- maximale Nachrichtengröße;
- Deadline pro Request;
- Heartbeat/Healthcheck;
- begrenzte Logmenge;
- keine Pfade/Dateileserequests vom Learner an die Engine.
