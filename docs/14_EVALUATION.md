# 14 — Evaluation

## Grundsatz

Training Return ist Diagnose, nicht Endmetrik. Checkpoints werden auf festen, nie trainierten Seeds unter ausgeschalteter Exploration bewertet.

## Baselines

Jeder Task vergleicht mindestens:

1. Random Legal;
2. Safe Script;
3. Aggressive/Task Script;
4. Behavior Cloning;
5. recurrent PPO;
6. Candidate-R2D2;
7. Candidate-R2D3;
8. gegebenenfalls menschliche Referenz.

Baselines erhalten denselben Observation- und Actionvertrag. Ein Script darf keine privilegierten Daten nutzen, sofern es als faire Baseline zählt. Ein separater „oracle script“ darf als Obergrenze existieren, muss aber so benannt sein.

## Primärmetriken

### Skill Tasks

- Success Rate;
- Survival Rate;
- medianer und mittlerer extrinsischer Return;
- Decisions und Engine-Ticks bis Abschluss;
- Damage dealt/taken;
- Ressourcenverbrauch;
- Illegal Actions;
- Engine Faults.

### Exploration

- Stair Success Rate;
- Map Coverage bei Zeitlimit;
- unique explored tiles pro Decision;
- unnötiges Backtracking;
- Memory-/Frontierfehler;
- Tod/Combatinterrupts.

### Loot/Town

- downstream Combat-/Survival-Verbesserung;
- Inventarwert unter Kapazität;
- Goldnetto und Opportunitätskosten;
- Reparatur-/Potion-Effizienz;
- Zahl sinnloser Transaktionen/Stadtfahrten.

### Full Run

- Diablo-Killrate;
- tiefstes Dungeon-Level;
- Runfortschritts-AUC;
- mediane Überlebenszeit;
- Todesursachen;
- Stadtfahrten, Tränke, Gold, Equipmententwicklung;
- Wallclock und Engine-Ticks;
- Seedgruppen-Performance.

## Statistik

- mindestens 128 Testepisoden pro kleiner Task;
- mehrere unabhängige Trainingsseeds;
- bootstrap Konfidenzintervalle;
- Median und Mean reporten;
- bei gepaarten Seeds gepaarte Differenzen nutzen;
- keine Auswahl des besten einzelnen Trainingsruns ohne Streuung;
- Effektgröße neben p-Wert/CI.

Full Runs können teurer sein; dort wird ein vorab definierter sequenzieller Evaluationsplan verwendet, ohne nach positiven Zwischenergebnissen willkürlich abzubrechen.

## Seedpartitionen

```text
Train       für Actorerfahrung und Demos
Validation  Modellwahl, Early Stopping, Hyperparameter
Test        Abschlussvergleich
Sealed Test seltene finale Prüfung
```

Die konkreten Bereiche stehen im Taskvertrag. Seeds allein reichen langfristig nicht: prozedurale Generatorversion, Gegnerpool und Itempool werden ebenfalls partitioniert.

## Generalisierungsmatrizen

Später:

| Train | Test | Frage |
|---|---|---|
| Warrior fixed loadout | neue Warrior loadouts | Buildrobustheit |
| bekannte Gegner | zurückgehaltene Gegnerfamilie | Gegnertransfer |
| Dungeon 1–4 | Dungeon 5 | Tiefentransfer |
| Warrior | Rogue/Sorcerer | Klassentransfer |
| strukturierter State | reduzierte Statefelder | Abhängigkeit/Leakage |

## Deterministische vs. stochastische Policy

Evaluation nutzt greedy Candidate-Auswahl und deterministische Tiebreaks. Optional wird eine zweite stochastic-policy-Auswertung reportet, aber nicht mit der Hauptmetrik vermischt.

## Checkpointauswahl

Ein Checkpoint ist nur „best“, wenn:

- Validation-Gate erfüllt;
- keine Contract-/Enginefehler;
- Test noch nicht zur Auswahl verwendet;
- Regression auf früheren Tasks unter Grenzwert;
- mindestens ein kompletter Evaluationreport und Manifest existiert.

## Fehleranalyse

Jeder Evaluationslauf erzeugt:

- Outcome-Histogramm;
- Todesursachen;
- ActionKind-Verteilung;
- Skilltransitionen;
- Q-/Policyentropie;
- Top- und Bottom-Episoden;
- replaybare Seeds;
- Contract-/Timeoutfehler.

Mindestens die schlimmsten und überraschend besten Episoden werden semantisch inspiziert. Video ist hilfreich, aber die strukturierte Trajektorie bleibt die Debugquelle.

## Fairer Compute-Vergleich

Methoden werden unter mehreren Budgets verglichen:

- Engine actor steps;
- Learner updates;
- Wallclock;
- CPU-/GPU-Stunden;
- Anzahl Demonstrationen.

BC darf nicht mit „null Engine Steps“ als kostenlos gelten, wenn Demonstrationssammlung teuer war. R2D3 wird sowohl inklusive als auch exklusive Demoerzeugungskosten reportet.

## Erfolgsbehauptungen

Zulässig:

- „90 % Erfolg auf den vorregistrierten 128 Testseeds von Task X.“
- „R2D3 erreichte ersten Erfolg nach Y Engine-Steps; PPO nach Z.“

Nicht ausreichend:

- ein ausgewähltes Video;
- höchster einzelner Return;
- Testseed, der während Entwicklung wiederholt beobachtet wurde;
- shaped Return ohne Taskerfolg;
- Trainingserfolg auf einem Seed.
