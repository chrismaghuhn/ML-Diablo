# 10 — ML-Strategie

## Empfehlung in einem Satz

> Nutze **Behavior Cloning als Warmstart und Baseline**, danach **rekurrentes, priorisiertes Off-Policy-Q-Learning mit getrenntem Demonstrations- und Agent-Replay im Stil von R2D2/R2D3**, eingebettet in eine **stufenweise eingeführte Skill-Hierarchie**.

Das ist eine projektspezifische Adaption, keine Behauptung, das originale R2D3-Paper unverändert zu reproduzieren.

## Problemformulierung

Diablo wird als partiell beobachtbarer Semi-Markov-Entscheidungsprozess modelliert:

- Observation `o_t`: player-observable strukturierter Zustand;
- History/Memory `h_t`: LSTM plus später explizite Karte;
- Candidate Set `A(o_t)`: variable Menge legaler semantischer Aktionen;
- gewählter Candidate `a_t`;
- interne Dauer `Δ_t`: Zahl Engine-Ticks bis zur nächsten Grenze;
- Reward `r_t`;
- natürlicher oder externer Abschluss.

Das Modell approximiert zunächst:

```text
Q(h_t, a_t)
```

für jeden legalen Candidate. Bei späteren Makro-Skills wird daraus ein SMDP-Q-Wert mit Dauerdiscount.

## Warum R2D2/R2D3 als Kern

### Teilbeobachtbarkeit

Der Agent sieht nicht jederzeit die gesamte Karte, alle Gegner oder frühere Entscheidungen. R2D2 trainiert rekurrente Q-Netze aus Sequenz-Replay und adressiert dabei stale recurrent state durch Burn-in.

### Teure Erfahrung

Off-Policy-Replay kann Engine-Übergänge mehrfach nutzen. PPO verwirft Erfahrung nach wenigen Epochen und verlangt typischerweise mehr frische Simulation.

### Demonstrationen

R2D3 ergänzt R2D2 um ein getrenntes Demonstrations-Replay. Das passt zu Diablo, weil sichere Skriptbots und menschliche Runs früh erfolgreiche Teilsequenzen liefern können, während zufällige Exploration einen Full Run praktisch nie entdeckt.

### Variable Startbedingungen

Die R2D3-Arbeit zielt explizit auf sparse rewards, partial observability und variierende initial conditions. Diablo besitzt dieselbe qualitative Kombination, auch wenn Observation und Aktionsraum anders sind.

### Online-Verbesserung

Behavior Cloning imitiert Daten und leidet außerhalb ihrer Zustandsverteilung. Off-Policy-RL kann eigene Fehlerzustände lernen und Demonstratoren übertreffen.

## Evidenz—und ihre Grenzen

- **R2D2** zeigt, wie rekurrente Agenten mit priorisiertem Replay und Burn-in stabiler trainiert werden können.
- **R2D3** mischt wenige Demonstrationssequenzen in rekurrentes Off-Policy-Q-Lernen. Die Arbeit berichtet, dass ein kleiner, aber nicht-null Demoanteil entscheidend sein kann.
- **DQfD** zeigt bereits früher, dass Demonstrationen die Anfangsleistung und Exploration von Q-Learning stark verbessern können.
- **NetHack is Hard to Hack** ist besonders relevant: In einem langen Dungeon-Spiel halfen Aktionshierarchie sowie die Kombination aus Imitation und RL; bloßes Skalieren neuronaler Policies schloss die Lücke zu symbolischen Agents nicht.

Aber: R2D3 nutzte sehr große verteilte Trainingsbudgets. Dieses Projekt darf daraus nicht ableiten, dass acht lokale Akteure automatisch einen Full Run lösen. Der Nutzen der Methode wird deshalb in kleinen Slices empirisch gegen PPO, BC und R2D2 geprüft.

## Projektspezifische Adaption: Candidate-R2D3

Das originale DQN-Setting hat einen festen diskreten Aktionskopf. Hier wird stattdessen jeder Candidate mit gemeinsamen Gewichten bewertet:

```text
state/history encoder → recurrent state z_t
candidate encoder(a_i) → c_i
Q_i = dueling_scorer(z_t, c_i)
```

Vorteile:

- variable Zahl sichtbarer Ziele und Items;
- neue Entity-IDs benötigen keinen neuen Output-Neuron;
- Parameter wie Position, Spell oder Slot sind explizit;
- Kandidatenreihenfolge kann permutiert werden;
- Legalität ist eingebaut.

## Trainingsphasen

### Phase A — Daten- und Baselinefähigkeit

Noch kein RL:

- Random- und Scriptbots;
- Trajektorienvalidierung;
- human/script demonstration collector;
- recurrent Behavior Cloning;
- Offline-Evaluation auf festen Seeds.

BC muss funktionieren, bevor R2D3 debuggt wird. Sonst ist unklar, ob Encoder, Labels oder RL falsch sind.

### Phase B — R2D2 ohne Demonstrationen

- Agent-Replay only;
- n-Step Double-Q;
- Target Network;
- Dueling Candidate Scorer;
- priorisierte Sequenzen;
- Burn-in;
- Epsilonfamilie über Akteure.

Dies isoliert den Effekt des Off-Policy-Kerns.

### Phase C — R2D3-Stil

- separater unveränderlicher Demo-Store;
- separate Prioritäten;
- stochastische Auswahl pro Batchelement;
- Sweep sehr kleiner Demo-Ratios;
- optional kleiner, abklingender BC-Auxiliary-Loss nur auf Demo-Samples.

Wichtig: Nicht pauschal 25–50 % Demos mischen. Hohe Ratios können das Lernen an suboptimale Demonstratoren binden. Start-Sweep:

```text
0, 1/512, 1/256, 1/128, 1/64, 1/32
```

### Phase D — Feste Skill-Hierarchie

Ein deterministischer Router wählt den aktiven Skill nach Context, nicht nach „optimaler“ Handstrategie. Beispiele:

- sichtbare unmittelbare Bedrohung → Combat;
- kein Gegner, wertvolles sichtbares Item → Loot;
- sonst → Explore;
- kritische Ressourcen und Portal verfügbar → Town/Retreat.

Jeder Skill hat eigenes Tasktraining, kann aber Encoder teilen. Der Router ist eine Integrationshilfe und eine starke Baseline.

### Phase E — Gelernter Manager

Erst jetzt wird Skillwahl gelernt. Manager-Aktionen dauern mehrere Primitive-Steps. Manager-Replay speichert:

```text
manager observation
selected option
cumulative discounted reward
duration
termination reason
next manager observation
```

Der Manager darf vorhandene Skills wählen, aber nicht direkt primitive Aktionen mischen, bis ein entsprechendes Experiment dies begründet.

### Phase F — Exploration

Wenn Demonstrationen plus Curriculum neue Floor-/Runfortschritte nicht ausreichend erschließen:

- episodischer Novelty-Bonus im Stil von NGU;
- mehrere Explorationsgrade über Akteure;
- Frontier-/Map-Coverage-Auxiliary;
- Self-Imitation erfolgreicher Agentsequenzen.

Intrinsischer Reward wird nie für die finale Evaluation gezählt.

### Phase G — World Model oder Search

Erst nach einer starken model-free Baseline:

- Dynamics-Modell für lokale Combatfolgen;
- Unsicherheitskalibrierung;
- kurze rollouts oder candidate reranking;
- Vergleich gegen echte Engineplanung.

DreamerV3 oder MuZero sind Forschungszweige, keine Voraussetzung für Full-Run-v1.

## Start-Hyperparameter

Die Dateien unter `configs/training/` enthalten nachvollziehbare Startpunkte:

- Sequenzlänge 80;
- Burn-in 40;
- Überlappung 40;
- 5-Step-Returns;
- `gamma=0.997`;
- Batch 64;
- Demo-Ratio initial `1/128`, aber verpflichtender Sweep;
- acht CPU-Akteure als lokaler Start, nicht als Dogma;
- LSTM Hidden 128;
- Gradient Clipping;
- periodisches Target Update.

Sie sind nicht „für Diablo bewiesen“. M1 soll Sensitivität und Durchsatz bestimmen.

## Zeitabhängiger Discount

Solange ein Decision-Step ungefähr gleich lang ist, genügt `gamma` pro Entscheidung. Bei Makroaktionen und stark variablen Deltas gilt:

```text
Discount_t = gamma_tick ** Δ_t
```

oder eine normalisierte Variante. Sonst bevorzugt der Agent lange Aktionen künstlich, weil Zeit nicht korrekt diskontiert wird. `engine_tick` wird deshalb im Vertrag gespeichert.

## Demonstrationsloss

Empfehlung:

1. reines BC-Pretraining;
2. dann TD-Lernen auf beiden Replays;
3. optional kleiner Cross-Entropy-Loss auf Demo-Samples;
4. Auxiliary-Loss abklingen lassen;
5. nie einen harten Margin-Loss dauerhaft erzwingen, ohne Ablation.

Menschliche und skriptbasierte Demonstrationen können suboptimal sein. Das System soll von ihnen starten, nicht an sie gekettet bleiben.

## Recurrent State

Der LSTM-Input umfasst mindestens:

- Observation-Embedding;
- vorherige semantische Aktion;
- vorherigen extrinsischen Reward;
- vorherige Termination/Interruptinformation;
- Task- und Skill-ID.

Replaysequenzen beginnen mit Burn-in. Sequenzen kreuzen keine Episoden und später keine inkompatiblen Contractversionen.

## Verteilte Architektur

V1 kann lokal starten:

```text
2–8 CPU Engine Actors
1 GPU Learner
1 eigener Evaluator
2 Replay Stores
```

Der Evaluator nutzt keine Exploration und keine Trainingsseeds. Gewichte werden versioniert/atomar verteilt. Actor-Lag wird gemessen.

## Klassische Komponenten

Folgende Teile sollen nicht aus Reinheitsgründen neu gelernt werden:

- A*/Dijkstra für bekannte Walkability;
- Kandidatenlegalität;
- deterministische Inventarplatzierung;
- Schema-/Rangevalidierung;
- Taskreset;
- Replayintegrität.

ML entscheidet Ziel, Risiko, Wert und Strategie. Klassische Controller führen eindeutig spezifizierte Mechanik aus.

## Pflichtablationen

Für jeden relevanten Task:

1. Script Baseline;
2. BC;
3. recurrent PPO;
4. R2D2;
5. R2D3 ohne BC-Auxiliary;
6. R2D3 mit Auxiliary;
7. feed-forward statt LSTM;
8. ohne Skill-Hierarchie;
9. ohne priorisiertes Replay;
10. unterschiedliche Demo-Ratios.

Ohne diese Ablationen ist nicht bekannt, ob Demos, Rekurrenz, Replay oder nur bessere Features den Gewinn erzeugten.

## Klare Stop-/Pivot-Kriterien

R2D3 bleibt Hauptpfad, solange:

- R2D2 PPO bei gleicher Engine-Erfahrung mindestens erreicht;
- Demonstrationen die Zeit bis zum ersten Erfolg oder Endleistung verbessern;
- Replaydurchsatz beherrschbar bleibt;
- Q-Werte kalibrierbar und Training stabil sind.

Pivot zu einem actor-critic-Ansatz, wenn Candidate-Q-Lernen trotz sauberer Targets instabil bleibt. Pivot zu model-based/search, wenn lokale Taktik nachweislich Planung benötigt, die Value-Free Policies nicht lernen. Methodentreue ist kein Projektziel.
