# Forschungsquellen und Ableitung

Stand der Prüfung: **2026-08-11**. Diese Liste dokumentiert die Quellen, aus denen die Architekturentscheidung abgeleitet wurde. Sie ist eine belastbare Startbibliografie, aber keine Behauptung einer vollständigen systematischen Literaturübersicht.

## DevilutionX und Integrationsrealität

### DevilutionX Upstream

- Repository: <https://github.com/diasurgical/DevilutionX>
- Festgehaltener Commit: `07385842840437cc9a785b195f5b40b121eaeb1c`
- Release-Liste: <https://github.com/diasurgical/DevilutionX/releases>
- Im geprüften Stand beobachtete Lizenz: Sustainable Use License 1.0
- Relevante Dateien:
  - `Source/headless_mode.hpp`
  - `Source/diablo.h`
  - `Source/diablo.cpp`
  - `Source/engine/demomode.h`

**Was daraus folgt:**

1. Ein interner Headless-Schalter existiert bereits für Tests; das ersetzt aber keine ML-Environment-API.
2. `game_loop(bool)` und die semantischen Engine-Kommandos liefern einen besseren Hook als Maus-/Tastaturautomation.
3. Demo-Aufzeichnung, Playback und simulierte Zeit sind wertvolle Determinismusbausteine.
4. Der aktuelle Upstream ist nicht als uneingeschränkt kommerziell nutzbare MIT-/Apache-Abhängigkeit zu behandeln.
5. Originale Diablo-Daten werden für das volle Spiel benötigt; dieses Scaffold enthält keine davon.

## Kernverfahren

### R2D2 — Recurrent Experience Replay in Distributed Reinforcement Learning

- Steven Kapturowski et al., ICLR 2019
- OpenReview: <https://openreview.net/forum?id=r1lyTjAqYX>

**Relevanz:** R2D2 untersucht rekurrentes Q-Learning aus verteiltem priorisiertem Replay. Besonders wichtig sind Sequenz-Replay, Burn-in beziehungsweise gespeicherte recurrent states sowie der Umgang mit Actor-/Learner-Lag.

**Übernahme:** LSTM/GRU-Gedächtnis, Sequenzen statt isolierter Transitions, Burn-in, n-Step Double-Q, priorisiertes Replay und getrennte Actor-Prozesse.

**Nicht blind übernommen:** Atari-Architektur, Actor-Anzahl, feste Aktionsmenge und publizierte Hyperparameter sind keine Diablo-Garantie.

### R2D3 — Making Efficient Use of Demonstrations to Solve Hard Exploration Problems

- Tom Le Paine et al., ICLR 2020
- arXiv: <https://arxiv.org/abs/1909.01387>

**Relevanz:** Das Papier adressiert genau die Kombination aus harten/sparsamen Rewards, partieller Beobachtbarkeit und stark variierenden Startbedingungen. Es kombiniert rekurrentes Off-Policy-Q-Learning mit einem separaten Demonstrations-Replay.

**Wichtige Originaldetails:**

- separates Agent- und Demo-Replay;
- stochastischer Demoanteil pro Batchelement;
- im Papier n-Step `n=5`;
- Sequenzlänge `80`, Überlappung `40`, Burn-in `40`;
- kleiner, aber nicht nuller Demoanteil war in den untersuchten Tasks entscheidend.

**Übernahme:** Das ist das Startprinzip dieses Projekts, angepasst auf dynamische semantische Kandidaten und kleine lokale Slices.

**Caveat:** R2D3 wurde mit erheblich mehr Compute und vielen Actors evaluiert. Das Scaffold behandelt die Zahlen als Startpunkte und fordert Sweeps/Ablationen.

### DQfD — Deep Q-learning from Demonstrations

- Todd Hester et al., AAAI 2018
- DOI/Proceedings: <https://ojs.aaai.org/index.php/AAAI/article/view/11757>
- arXiv: <https://arxiv.org/abs/1704.03732>

**Relevanz:** DQfD zeigt, wie TD-Lernen und ein supervised Demonstrationssignal kombiniert werden können und dass ein Agent Demonstratoren übertreffen kann.

**Übernahme:** Behavior-Cloning-/Margin-Loss als Warmstart oder Auxiliary Loss; Demonstrationen erhalten Schutz vor sofortigem Vergessen.

**Caveat:** Das klassische Verfahren ist feed-forward und auf feste Atari-Aktionen zugeschnitten. Unsere rekurrente Candidate-Variante ist eine Projektadaption, keine wortgetreue DQfD-Reproduktion.

## Vergleichsdomäne: lange Dungeon-Spiele

### The NetHack Learning Environment

- Heinrich Küttler et al., NeurIPS 2020
- arXiv: <https://arxiv.org/abs/2006.13760>
- Code: <https://github.com/facebookresearch/nle>

**Relevanz:** NetHack ist prozedural, stochastisch, langhorizontig, partiell beobachtbar und reich an Skills. Die Arbeit positioniert Exploration, Planung, Skill Acquisition und Generalisierung als zentrale Probleme.

**Ableitung:** Diablo darf nicht wie ein kurzer Arcade-Task behandelt werden. Task-Slices, beobachtbarer strukturierter State, schnelle Simulatorinstanzen und harte Evaluation sind wichtiger als eine spektakuläre End-to-End-Demo.

### NetHack is Hard to Hack

- Ulyana Piterbarg, Lerrel Pinto, Rob Fergus, NeurIPS 2023
- arXiv: <https://arxiv.org/abs/2305.19240>

**Relevanz:** Die Studie untersucht explizit Aktionshierarchie, Architekturverbesserungen und die Verbindung von Imitation Learning mit RL. Sie berichtet zugleich, dass bloßes Skalieren die Lücke zu starken symbolischen Agenten nicht schließt.

**Ableitung:**

- frühe feste Skills sind legitim und wahrscheinlich produktiver als primitive End-to-End-Aktionen;
- klassische Planung und Regeln sind keine „Cheats“, sondern Baselines und Infrastruktur;
- ML soll dort eingesetzt werden, wo Unsicherheit, Generalisierung und Wertschätzung schwierig sind.

### Learning Combat in NetHack

- Jonathan Campbell, Clark Verbrugge, AIIDE 2017
- Proceedings: <https://ojs.aaai.org/index.php/AIIDE/article/view/12923>

**Relevanz:** Belegt, dass selbst ein isolierter Roguelike-Combat-Slice mit großer Aktionsmenge ein eigenständiges Forschungsproblem ist.

## Spätere Explorationserweiterungen

### Never Give Up (NGU)

- Adrià Puigdomènech Badia et al., 2020
- arXiv: <https://arxiv.org/abs/2002.06038>

**Relevanz:** Episodisches Gedächtnis, kontrollierbarkeitsorientierte Embeddings und eine Familie unterschiedlich explorativer Policies.

**Projektrolle:** erst nach funktionierendem extrinsischem R2D3-Training. Intrinsischer Reward darf nicht Item-Farming oder ungefährliches Herumlaufen belohnen.

### Agent57

- Adrià Puigdomènech Badia et al., 2020
- arXiv: <https://arxiv.org/abs/2003.13350>

**Relevanz:** adaptive Auswahl zwischen explorativen und exploitiven Policies.

**Projektrolle:** mögliche M6+-Erweiterung, nicht M1-Startpunkt.

## World Models und Search

### DreamerV3

- Danijar Hafner et al., 2023
- arXiv: <https://arxiv.org/abs/2301.04104>

**Relevanz:** starkes generalistisches World-Model-Verfahren mit imaginierten Rollouts.

**Warum nicht zuerst:** Die schwierigsten Diablo-Fehler sind seltene, irreversible und semantisch präzise Ereignisse. Ein Modell, das Inventar-, Shop-, Tür-, Quest- oder Todesdynamik nur fast richtig lernt, kann falsche Pläne massiv überbewerten. Dynamische Candidate Sets und lange Macro-Actions erhöhen das Integrationsrisiko.

### MuZero

- Julian Schrittwieser et al., Nature 2020
- arXiv: <https://arxiv.org/abs/1911.08265>

**Relevanz:** Planung mit gelerntem Repräsentations-, Dynamik- und Vorhersagemodell ohne vollständige explizite Regelkenntnis.

**Projektrolle:** späterer lokaler Combat-/Loot-Planner, sofern Engine-Schritte schnell genug und Candidate-Expansion begrenzt sind. Kein Full-Run-v1-Fundament.

## Pflichtbaseline

### Proximal Policy Optimization

- John Schulman et al., 2017
- arXiv: <https://arxiv.org/abs/1707.06347>

**Relevanz:** einfache, robuste On-Policy-Baseline. Eine rekurrente, action-masked PPO-Implementierung ist nötig, um zu prüfen, ob Replay-/Demo-Komplexität tatsächlich Mehrwert bringt.

**Warum nicht Hauptprinzip:** On-Policy-Daten werden nur begrenzt wiederverwendet; teure Engine-Erfahrung und Demonstrationen passen natürlicher zu Off-Policy-Replay.

## Suchbefund zu Diablo-spezifischem ML

Bei der Recherche wurden keine reifen, breit genutzten öffentlichen DevilutionX-Gym-/RL-Benchmarks oder ein etabliertes „Diablo-I bis Endboss“-Verfahren gefunden. Das ist **kein Beweis**, dass keine privaten oder kleineren Experimente existieren. Daher wird Neuheit nicht als Marketingbehauptung verwendet; die wissenschaftliche Leistung muss über reproduzierbare Verträge, Baselines und Ablationen gezeigt werden.

## Entscheidungsregel bei neuen Papieren

Ein neues Verfahren ersetzt den Kernpfad nur, wenn es mindestens eines dieser Probleme nachweislich besser löst:

1. weniger echte Engine-Schritte bis zu gleicher Testleistung;
2. bessere Generalisierung auf versiegelte Seeds;
3. stabileres Lernen bei partieller Beobachtbarkeit;
4. bessere Nutzung suboptimaler Demonstrationen;
5. weniger Engineering-/Compute-Risiko bei gleicher Leistung.

Ein beeindruckender Benchmarkscore ohne übertragbaren Mechanismus reicht nicht.
