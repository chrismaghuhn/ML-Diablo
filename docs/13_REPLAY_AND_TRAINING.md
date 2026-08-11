# 13 — Replay und Training

## Zwei Replay-Puffer

```text
Agent Replay          Demonstration Replay
mutable                kuratiert/versioniert
hoher Durchsatz        kleiner
agent priorities       eigene priorities
          \             /
           stochastic mix per batch element
                       ↓
                    Learner
```

Die Trennung verhindert, dass seltene Demonstrationen durch große Agentdatenmengen verdrängt werden, und erlaubt unabhängige Priorisierung.

## Sequenzen

Standardstart:

- Länge 80 Decisions;
- 40 Burn-in;
- 40 Learning;
- Overlap 40;
- keine Episodengrenzen;
- später Skillgrenzen als Metadaten.

Kurze Episoden dürfen kürzere Sequenzen liefern, solange mindestens ein Learning-Step bleibt und Paddingmasken korrekt sind.

## Burn-in

Der LSTM-State im Replay ist potenziell stale, weil Gewichte seit Datenerzeugung geändert wurden. Daher wird der Kern auf dem Burn-in-Teil unrolled, ohne TD-Loss anzuwenden. Das rekonstruiert einen aktuellen Hidden State für den Learning-Teil.

## Priorität

Referenz:

```text
priority = η * max(|TD error|)
         + (1-η) * mean(|TD error|)
         + ε
```

Max betont überraschende Einzelsteps, Mean verhindert, dass der Rest der Sequenz ignoriert wird. Importance Sampling korrigiert den Samplingbias zunehmend.

## Targets

Start:

- n-Step Return mit `n=5`;
- Double-Q Action Selection;
- Target Network;
- Dueling Candidate-Q;
- signed hyperbolic value rescaling;
- Terminal und Truncation getrennt.

Bei variabler Actiondauer wird Discount später tick-/dauerbasiert.

## Demo-Mix

Der Demoanteil wird stochastisch pro Batchelement gewählt, nicht als feste Mindestanzahl pro Batch. So sind Ratios kleiner als `1/batch_size` möglich. Pflichtsweep:

```text
0
1/512
1/256
1/128
1/64
1/32
```

Zusätzlich werden BC-only und R2D2-only trainiert.

## Replay-Warmup

- Demo-Replay kann vor Training gefüllt sein.
- Agent-Replay benötigt eine minimale Sequenzzahl.
- BC-Checkpoint initialisiert Encoder/LSTM/Candidate Head.
- Target Network startet identisch.
- Online-Lernen beginnt mit begrenzter Learning-to-Actor-Ratio.

Ein Learner darf nicht tausende Updates auf denselben wenigen Agentsequenzen ausführen, ohne diese Overfittingrate zu loggen.

## Actor Exploration

R2D2/R2D3 nutzen eine Familie von Epsilonwerten. Lokal reichen wenige Akteure mit unterschiedlichen Explorationgraden. Zusätzlich kann ein Script-/Demo-Aktor unabhängig laufen.

Zu loggen:

- Actor epsilon;
- Policyversion/Lag;
- Episodeergebnis;
- State-/Actioncoverage;
- Replay insertion rate;
- stale weight age.

## Learner-Schleife

```text
sample dual replay batch
→ reconstruct recurrent state with burn-in
→ online Q on learning segment
→ target Q for n-step bootstrap
→ TD loss × importance weights
→ optional decaying BC auxiliary on demo elements
→ gradient clip + optimizer
→ update replay priorities
→ periodic target update
→ periodic atomic checkpoint
```

## Parallelität

- Engine-Akteure: CPU Prozesse;
- Learner: GPU oder CPU;
- Replay: zunächst im Learnerprozess oder lokaler Service;
- Evaluator: eigener Prozess und eigene Engine;
- Demonstration Collector: getrennt.

Der Referenz-Replay im Scaffold ist O(N) und nur für Tests/kleine Runs. Skalierung braucht Segment Tree oder Reverb-ähnlichen Service.

## Backpressure

Wenn Actors schneller sind als der Learner:

- Replay wächst bis Kapazität;
- oldest agent sequences werden verdrängt;
- Demos bleiben separat;
- insertion/sample ratio wird gemessen.

Wenn Learner schneller ist:

- Update-to-data ratio begrenzen;
- auf frische Agentdaten warten oder ältere Samples bewusst wiederverwenden;
- nicht still in extremes Overtraining laufen.

## Checkpoints

Ein atomarer Checkpoint enthält:

- online/target weights;
- optimizer/scheduler;
- RNG states;
- learner step;
- Feature-/Contractversion;
- Config und Hash;
- Upstreamrevision;
- Baseline-/Evalmetriken;
- optional Replay-Snapshot-Referenzen.

Resume muss in einem Test denselben nächsten Learnerstep erzeugen wie ein ununterbrochener Lauf, soweit deterministische GPU-Operationen dies erlauben.

## Numerische Stabilität

- NaN/Inf Checks auf Inputs, Q, Targets und Gradients;
- Gradientnorm loggen/clippen;
- Reward/Value rescaling;
- Huber Loss statt unbeschränkter MSE als Start;
- Q-Verteilung pro ActionKind;
- Target/Online drift;
- terminal bootstrap audit.

## Offline Vortraining

BC ist v1. Später können Replaydaten für Offline Q-Learning genutzt werden, aber erst wenn Behavior Coverage, Out-of-Distribution Actions und Dataset Bias gemessen sind. Candidate Legalität allein verhindert keine Q-Extrapolation auf seltene semantische Entscheidungen.
