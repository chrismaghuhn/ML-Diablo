# Task-, Fixture- und Seedvertrag

## Task-ID

Format:

```text
<domain>.<objective>.<variant>.v<major>
```

Beispiel: `combat.single_melee.v0`.

## TaskSpec

Ein Task definiert mindestens:

- Startfixture und zulässige Variation;
- erlaubte Action Kinds;
- Success-/Failurebedingungen;
- Decisionlimit;
- Rewardversion;
- Train-/Validation-/Testseedsets;
- ob privilegierter State ausschließlich für Oraclemetriken erlaubt ist.

## Seedbundle

Ein einzelner sichtbarer Seed kann intern deterministisch in Substreams zerlegt werden:

```text
level_seed
combat_rng_seed
loot_seed
store_seed
fixture_seed
```

Die Ableitung wird versioniert. Änderungen erzeugen eine neue Fixtureversion.

## Sealing

Testseeds werden nicht für Training, Replay, Curriculum, Hyperparameterwahl oder Demoerstellung verwendet. Ein Release öffnet das Testset nur über automatisierte Evaluation.
