# 25 — Experiment- und Ablationsmatrix

## Pflichtmethoden pro Skill-Slice

| ID | Methode | Gedächtnis | Demos | Replay | Zweck |
|---|---|---|---|---|---|
| A0 | Random legal | nein | nein | nein | Untergrenze/Contractstress |
| A1 | Handgeschrieben sicher | explizit | nein | nein | starke Engineeringbaseline |
| B0 | Recurrent BC | ja | ja | offline | Demonstrationsnutzbarkeit |
| B1 | Recurrent BC + DAgger-artige Korrektur | ja | ja | aggregiert | Distribution Shift |
| C0 | Recurrent PPO | ja | optional warm | on-policy | einfache RL-Baseline |
| D0 | Candidate-R2D2 | ja | nein | Agent-PER | Wert von Replay/Rekurrenz |
| D1 | Candidate-R2D3 | ja | ja | Agent+Demo-PER | Hauptverfahren |
| D2 | R2D3 ohne BC-Warmstart | ja | ja | Agent+Demo-PER | Wert des Warmstarts |
| D3 | R2D3 mit einem Replay | ja | ja | gemischt | Wert getrennter Prioritäten |
| D4 | R2D3 ohne Burn-in | ja | ja | Sequenzen | Recurrent-State-Effekt |

## Demo-Ratio-Sweep

Mindestens:

```text
0
1/512
1/256
1/128  ← Startwert, keine Behauptung eines Optimums
1/64
1/32
1/16
```

Bewertet werden nicht nur Endscore, sondern:

- Zeit bis zum ersten Erfolg;
- Engineentscheidungen bis 50/80/90 % Success;
- Stabilität über Seeds;
- Demonstrator-Übertreffen;
- Recovery aus außerhalb der Demo liegenden Zuständen;
- Demo-/Agent-Replayanteil in tatsächlichen Updates.

## Repräsentationsablation

| Variante | Strukturierter State | LSTM | explizite bekannte Karte | Pixels |
|---|---:|---:|---:|---:|
| R0 | ja | nein | nein | nein |
| R1 | ja | ja | nein | nein |
| R2 | ja | ja | ja | nein |
| R3 | ja | ja | ja | ja, auxiliary |
| R4 | nein | ja | nein | ja |

R4 ist bewusst spät: Pixel-only darf nicht die Engine-/Contractarbeit blockieren.

## Aktionsablation

1. primitive Richtungstasten + Buttons;
2. semantische atomare Candidates;
3. semantische Candidates + feste Skills;
4. semantische Candidates + gelernter Manager.

Erwartung, nicht Ergebnis: Semantische Candidates und Skills reduzieren Suchhorizont und Invalid Actions. Das muss gemessen werden.

## Rewardablation

- terminal-only;
- terminal + Schadensdelta;
- terminal + potential-based Progress;
- vollständiger v1-Shapingmix.

Jede Variante wird auf Reward-Hacking geprüft. Eine Variante mit höherem Trainingsreward, aber schlechterer versiegelter Taskleistung gilt als gescheitert.

## Statistisches Protokoll

- mindestens fünf unabhängige Trainingsseeds für frühe Slices;
- 95-%-Bootstrap-Konfidenzintervalle;
- Median und Interquartilsabstand zusätzlich zum Mittelwert;
- feste Evaluationscheckpointfrequenz;
- keine Auswahl des besten Testseeds;
- Hyperparameter nur auf Train/Validation;
- finales Testset einmal pro eingefrorener Releasekonfiguration.

## Stop-/Pivot-Kriterien

R2D3 wird nicht aus Loyalität beibehalten. Pivot prüfen, wenn nach sauberem Tuning:

- R2D2/R2D3 nicht besser als recurrent PPO pro Engineentscheidung ist;
- Q-Werte trotz konservativer Ziele dauerhaft divergieren;
- Demo-PER die Policy systematisch auf suboptimale Pfade fixiert;
- Candidate-Anzahl die Q-Auswertung zum dominanten Bottleneck macht;
- Macro-Dauern SMDP-Lernen instabil machen.

Mögliche Pivots: IMPALA/V-trace, actor-critic mit off-policy Korrektur, Offline-RL bei großem Datensatz oder lokaler Search-Hybrid.
