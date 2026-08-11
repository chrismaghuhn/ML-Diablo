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

## RNG

Jede relevante RNG-Quelle muss entweder:

1. aus dem Runseed deterministisch abgeleitet werden; oder
2. im Manifest separat gespeichert werden.

Seedable heißt nicht automatisch deterministisch. Plattform-/Compiler-/Threadabhängigkeit wird durch Cross-run-Tests geprüft.

## Test

Mindestens 100 Seeds, je zweimal, mit derselben Scriptpolicy. Hashabweichung erzeugt einen Blocker. Ein erlaubter Unterschied benötigt eine neue Contractversion oder explizite Normalisierung.
