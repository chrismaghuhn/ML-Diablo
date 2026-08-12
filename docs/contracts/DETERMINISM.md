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

## M0.4 Prozesslebensdauer

M0.4 vergleicht kanonische JSON-Traces mit
`src/dxai/env/determinism.py`. Dabei werden ausschließlich
`request_id`, `pid`/`process_id`, `runtime_root`, Zeitstempel und
Prozessstart-Metadaten entfernt. Jede `episode_id` wird durch
`<lifecycle-episode>` ersetzt, weil die Episode-ID pro frischem Worker bewusst
einzigartig sein muss. Seed, Spieler-/Weltzustand, geordnete Candidates,
semantische Aktion, `engine_tick` und Step-Reihenfolge bleiben unverändert und
sind Teil des Hashes.

Die gleiche Seed- und Aktionsfolge darf deshalb über Cold Resets denselben
semantischen Trace-Hash erzeugen, ohne eine globale Episode-ID oder einen
Prozess-Hash künstlich wiederzuverwenden. Der opt-in M0.4-Realtest prüft dies
über mindestens 32 Steps in einem Worker und über einen A -> B -> A Reset.

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
