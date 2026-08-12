# M0.4 Prozess- und IPC-Vertrag

M0.4 definiert die lokale, autoritative Prozessgrenze als `dxai.process.v1`.
Die Transportserialisierung ist strikt eine UTF-8-JSON-Line pro Nachricht. Das
bestehende Protobuf in `protocol/` bleibt unverändert und ist nicht die
autoritative M0.4-Wire-Oberfläche.

## Zustandsautomat

```text
READY --Reset--> EPISODE_ACTIVE --Step--> EPISODE_ACTIVE
  |                     |
  +--fatal protocol/engine failure--> FAULTED
```

Ein Worker akzeptiert genau ein erfolgreiches Reset. `FAULTED` ist terminal
für diesen Prozess; Python verwirft ihn und startet für die Wiederherstellung
einen frischen Worker. Ein Reset ist deshalb ein Cold Reset mit
Prozess-/Runtime-Isolation, kein unbewiesenes Leeren von DevilutionX-Globals.

## Framing und geschlossene Nachrichten

- Eine physische Zeile enthält genau ein JSON-Objekt und endet mit LF; CRLF
  wird beim Lesen akzeptiert.
- Die UTF-8-Bodygröße ist auf `1 * 1024 * 1024` Bytes begrenzt.
- Leere Zeilen, ungültiges UTF-8, JSON nach dem Objekt, unbekannte Felder,
  fehlende Felder, Duplikate, falsche Typen und unbekannte Nachrichtentypen
  werden abgelehnt.
- stdout enthält ausschließlich Response-JSON-Lines. Native Diagnostik gehört
  nach stderr; Assetpfade und proprietäre Inhalte werden nicht als Healthdaten
  übertragen.

Requests besitzen exakt diese Felder:

```text
health_request {type, protocol_version, request_id}
reset_request  {type, protocol_version, request_id, seed, task_id}
step_request   {type, protocol_version, request_id, episode_id,
                expected_step_id, candidate_id, candidate_set_sha256}
```

`request_id`, `seed`, `expected_step_id` und `candidate_id` sind unsigned
Ganzzahlen; `candidate_set_sha256` ist ein lowercase SHA-256-Digest.

## Health-Response und Kompatibilität

`health_request` liefert:

```text
type, protocol_version, request_id, process_state,
adapter_revision, devilutionx_revision, build_fingerprint,
observation_version, action_version, supported_task_versions,
supported_features, pid
```

Der Python-Client akzeptiert nur die exakt erwarteten Werte:

```text
protocol_version       = dxai.process.v1
adapter_revision       = m0.4
devilutionx_revision   = 07385842840437cc9a785b195f5b40b121eaeb1c
observation_version    = dxai.observation.v1
action_version         = dxai.action.v1
task                   = combat.single_melee.v0
feature                = MOVE_TO_TILE, cold_reset, request_idempotency
```

## Reset und Step

Ein erfolgreiches Reset antwortet mit `reset_response` und:

```text
type, protocol_version, request_id, process_state=EPISODE_ACTIVE,
episode_id, observation, candidate_set_sha256
```

Die Observation startet bei `step_id=0`; ihre `episode_id` muss der
Response-ID entsprechen. Die Episode-ID enthält einen Prozess-/Nonce-Anteil
und ist nicht nur aus dem Seed abgeleitet.

Ein erfolgreicher Step antwortet mit `step_response` und:

```text
type, protocol_version, request_id, process_state=EPISODE_ACTIVE,
episode_id, previous_step_id, applied_action,
previous_candidate_set_sha256, observation, candidate_set_sha256
```

Vor jeder nativen Mutation werden Episode-ID, erwartete Step-ID,
Candidate-Set-Digest und die observation-lokale `candidate_id` geprüft. Die
Candidate-Liste wird ausschließlich über die bestehenden M0.3-Funktionen und
native `CanStep`/`PosOkPlayer`-Semantik erzeugt. M0.4 fügt keine Action-Art
hinzu: unterstützt ist nur `MOVE_TO_TILE`.

Erfolgreiche M0.4-Responses enthalten ausdrücklich weder `reward` noch
`terminated` noch `truncated`. Reward-, Terminal- und Learner-Verträge sind
spätere, getrennte Milestones.

## Request-Idempotenz

Der Worker hält die letzten 128 abgeschlossenen Requests. Jeder Cacheeintrag
enthält Request-Fingerprint und die vollständig serialisierte Response.

- Ein exakter Duplicate liefert bytegleich dieselbe Response ohne erneute
  Engine-Mutation.
- Eine Wiederverwendung derselben ID mit anderem Payload ist
  `REQUEST_ID_REUSE`.
- Eine nach Eviction zu alte ID ist `REQUEST_ID_EXPIRED`; sie darf nicht als
  neue Mutation wiederverwendet werden.
- Python retryt keinen Timeout-Step. Nach Timeout, EOF, Crash oder malformed
  Response ist der Worker unbrauchbar und benötigt `reset()`.

## Fehler und Diagnose

Protocol-/Enginefehler werden als `error_response` mit `error_code` und
`error_message` ausgegeben. Ein Fehler vor dem erfolgreichen Parsen kann
`request_id=null` tragen. Ein fataler Framing- oder nativer Invariantfehler
setzt `process_state=FAULTED`; gewöhnliche stale/invalid-Candidate-Ablehnungen
mutieren den aktiven Zustand nicht.

Der vollständige Betriebsablauf und die lokalen Verifikationsbefehle stehen in
[`docs/runbooks/M04_PERSISTENT_ENVIRONMENT.md`](../runbooks/M04_PERSISTENT_ENVIRONMENT.md).
