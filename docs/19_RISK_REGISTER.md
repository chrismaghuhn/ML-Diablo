# 19 — Risikoregister

Skala: Wahrscheinlichkeit (W) und Auswirkung (A) von 1–5. Score = W×A.

| ID | Risiko | W | A | Score | Frühindikator | Gegenmaßnahme |
|---|---|---:|---:|---:|---|---|
| R1 | Bridge ist nondeterministisch | 4 | 5 | 20 | gleiche Replayactions ergeben Hashdiff | M0 vor ML; RNG/Uhr/Globals auditieren |
| R2 | Observation leakt Hidden State | 3 | 5 | unrealistisch perfekte Reaktion | Observability fixtures, Feldprovenienz |
| R3 | Environment zu langsam | 4 | 4 | < Zielsteps/s, GPU idle | Headless profiling, Prozessparallelität |
| R4 | Full Run ist zu sparse | 5 | 5 | kein Fortschritt trotz Mio. Steps | Curriculum, Demos, Hierarchie |
| R5 | BC kollabiert off-distribution | 5 | 3 | gute Offlineaccuracy, schlechte Runs | Recoverydemos, online RL |
| R6 | Q-Learning instabil | 3 | 4 | Q explosion/NaN | small slices, target, clipping, PPO baseline |
| R7 | Demo-Ratio bindet an schlechte Demos | 3 | 4 | R2D3 schlechter als R2D2 | Ratio sweep, decay, quality diversity |
| R8 | Skills funktionieren einzeln, nicht integriert | 4 | 4 | Routerloops/oscillation | manager tasks, option termination tests |
| R9 | Reward Hacking | 4 | 4 | hoher Return ohne Erfolg | external metrics, adversarial fixtures |
| R10 | Reset kontaminiert Episoden | 3 | 5 | Ergebnis hängt von vorherigem Run ab | alternating-seed soak tests |
| R11 | Upstream-Upgrade bricht Hooks | 4 | 3 | Compile/Golden diff | pin, adapter isolation, upgrade runbook |
| R12 | Lizenz verhindert geplante Distribution | 3 | 5 | kommerzieller/öffentlicher Plan | nicht-kommerziell, klare Grenze, Rechtsprüfung |
| R13 | Assets gelangen ins Repo | 2 | 5 | große Binärdateien/MPQ | ignore, CI scanner, release audit |
| R14 | Replay frisst RAM/Storage | 4 | 3 | OOM, TB JSON | capacity, compression, columnar migration |
| R15 | Testseed Leakage | 3 | 5 | wiederholtes manuelles Tuning | sealed split, run registry |
| R16 | Modell lernt Candidateposition | 2 | 4 | Permutation ändert Semantik | shared scorer, permutation tests |
| R17 | Recurrent Memory reicht nicht | 4 | 4 | kurze Tasks gut, lange Memorytasks schlecht | explicit map memory, longer hierarchy |
| R18 | Featureengineering dominiert Ergebnis | 3 | 3 | neuronale Ablation ohne Effekt | feature ablations, script baseline |
| R19 | Menschendemos zu wenig/divers | 4 | 3 | hohe BC train acc, schlechte val | script styles, active data collection |
| R20 | Projektumfang eskaliert | 5 | 4 | viele unfertige Actionfamilien | milestone gates, scope freeze |
| R21 | Enginecrashes verfälschen Reward | 2 | 5 | Deaths korrelieren mit faults | faults separat, Episode ungültig |
| R22 | Variable Actiondauer verzerrt Discount | 3 | 4 | lange Makros bevorzugt | SMDP duration discount |
| R23 | World Model exploitet Modellfehler | 3 | 4 | imagined gain, real failure | uncertainty + real-engine validation |
| R24 | Checkpoint ist unsicher | 2 | 5 | fremde pickle files | safetensors/weights_only/hash |

## Top-Risiken und konkrete Gates

### R1/R10 — Determinismus und Reset

**Gate:** 1.000 wiederholte Golden-Replays plus alternierende Seedfolge ohne Hashabweichung.

### R2 — Hidden-State-Leak

**Gate:** jede neue Observationquelle besitzt Pro­venienz, Visibilityrule und negatives Fixture. Kein Training vor Audit.

### R3 — Durchsatz

**Gate:** M0 benchmarkt median/p95. Architekturentscheidungen zu Actorzahl erst nach Messung.

### R4/R20 — Horizont und Scope

**Gate:** kein neuer Full-Run-Subsystemcode, bevor aktueller Slice seine Abnahme erfüllt.

### R6/R7 — ML-Stabilität

**Gate:** synthetischer MDP, one-batch-overfit, BC, PPO, R2D2 und Demo-Ratio-Ablation.

### R12/R13 — Recht/Assets

**Gate:** Release-Script listet Binärdateien und sucht Assetmuster; Upstream bleibt außerhalb des ZIPs.

## Risk Review

Bei jedem Milestone:

- Score aktualisieren;
- neue Risiken aufnehmen;
- geschlossene Risiken mit Evidenz markieren;
- Trigger und Owner festlegen;
- Roadmap bei Score ≥15 anpassen.
