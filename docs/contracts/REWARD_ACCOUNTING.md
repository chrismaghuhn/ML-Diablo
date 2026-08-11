# Reward- und Outcome-Vertrag

## Grundsatz

Taskerfolg ist eine boolesche Enginebedingung. Reward ist ein Lernsignal und darf Erfolg nicht umdefinieren.

## Komponenten

Jeder Step speichert ein Dictionary aus benannten Komponenten. Die Summe muss exakt dem skalaren Reward entsprechen.

Beispiel Combat v1:

```text
success terminal
 death terminal
 damage_dealt delta
 damage_taken delta
 resource_use cost
 living/decision cost
 potential progress (optional, policy-invariant prüfen)
```

## Verboten

- zukünftige Information;
- versteckte Gegner-/Lootdistanz;
- Reward für reine UI-/Tickaktivität;
- unbeschränkter positiver Farmreward;
- wechselnde Skalierung ohne Rewardversion.

## Evaluation

Primärmetriken sind Success, Überleben, Engineentscheidungen, Ressourcenverbrauch und Generalisierung. Trainingsreturn wird separat berichtet.
