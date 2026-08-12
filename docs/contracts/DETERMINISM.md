# Determinismusvertrag

## Identität eines Laufs

Ein Run ist nur vergleichbar, wenn mindestens gleich sind:

```text
upstream commit
adapter commit
build fingerprint
asset-set fingerprint (privat, nicht veröffentlichen)
task version
fixture version
reward version
seed bundle
semantic action sequence
protocol/observation/action versions
```

## Muss-Garantie

Für einen kontrollierten Fixture-Slice erzeugt dieselbe Identität dieselbe kanonische Folge aus:

- Observations;
- legalen semantischen Candidates;
- gewählter Aktion;
- Rewardkomponenten;
- Terminalflags und Outcome.

Zeitstempel, Prozess-IDs, Logpfade und Request-IDs werden vor dem Vergleich entfernt.

## M0.3 Candidate-Set-Identität

Der erste reale Step verwendet eine kanonische, geordnete Darstellung:

```text
dxai.observation.v1|dxai.action.v1|
candidate_id;kind;target_entity_id;target_tile;inventory_slot;
equipment_slot;belt_slot;spell_id;store_item_id;stat_id
```

Die Liste ist semantisch dedupliziert, nach absolutem `(x,y)` für
`MOVE_TO_TILE` sortiert und anschließend dicht nummeriert. Label und
Auxiliary-Features verändern diese Identität nicht. Der SHA-256-Digest wird
im `dxai.probe.step.v1`-Envelope für die ausgegebene und die nächste
Candidate-Liste mitgeführt; die Regeneration vor der nativen Mutation muss
kanonisch und digestgleich sein.

Der M0.3-Nachweis vergleicht außerdem kanonische JSON-Hashes der initialen
Observation, der gewählten semantischen Aktion und der nächsten Observation
sowie rohe Probeausgaben. Die zwei frischen Seed-123-Runtime-Wurzeln müssen
alle diese Werte gleich liefern. M0.3 ersetzt nicht die spätere vollständige
Reset-, Replay- und Multi-Seed-Abnahme.

## RNG

Jede relevante RNG-Quelle muss entweder:

1. aus dem Runseed deterministisch abgeleitet werden; oder
2. im Manifest separat gespeichert werden.

Seedable heißt nicht automatisch deterministisch. Plattform-/Compiler-/Threadabhängigkeit wird durch Cross-run-Tests geprüft.

## Test

Mindestens 100 Seeds, je zweimal, mit derselben Scriptpolicy. Hashabweichung erzeugt einen Blocker. Ein erlaubter Unterschied benötigt eine neue Contractversion oder explizite Normalisierung.
