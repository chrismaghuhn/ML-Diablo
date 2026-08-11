# 22 — Glossar

**Action Candidate** — Eine aktuell legale semantische Aktion inklusive Parametern. Ihre ID gilt nur für eine Observation.

**Actor** — Prozess, der mit einer Environmentinstanz interagiert und Erfahrung erzeugt.

**BC / Behavior Cloning** — Überwachtes Lernen der demonstrierten Aktion aus Beobachtungen.

**Burn-in** — Sequenzanfang, der nur zur Rekonstruktion des rekurrenten Hidden States unrolled wird, ohne dort den Hauptloss anzuwenden.

**Candidate-Q** — Q-Funktion, die einen Zustands-/History-Embedding und einen einzelnen Aktionskandidaten gemeinsam bewertet.

**Contract Version** — Stabile Semantik von Observation, Action, Transition oder Protocol.

**Decision Boundary** — Zeitpunkt, an dem der Agent eine neue semantische Entscheidung treffen darf/muss.

**Demonstration Replay** — Separater Replaypuffer mit menschlichen oder scripted Trajektorien.

**DQN** — Value-basierter RL-Ansatz für diskrete Aktionen mit Q-Netz und Replay.

**DQfD** — Deep Q-learning from Demonstrations.

**Engine Tick** — Interner Simulationsschritt; mehrere Ticks können einem Agent-Step entsprechen.

**Entity** — Sichtbares Monster, Item, Objekt, NPC, Missile oder Stairs mit episode-lokaler ID.

**Environment Fault** — Crash, Timeout oder Contractfehler; kein normaler Spielterminal.

**Extrinsischer Reward** — Taskreward aus der Umgebung.

**Hidden Information Leak** — Beobachtung enthält Wissen, das ein regelkonformer Spieler nicht haben dürfte.

**Intrinsic Reward** — Zusatzsignal für Exploration; zählt nicht zur finalen Taskmetrik.

**Learner** — Prozess, der Batches sampled, Gradienten berechnet und Gewichte aktualisiert.

**Off-policy** — Lernen aus Erfahrung, die von älteren oder anderen Policies erzeugt wurde.

**Option/Skill** — Zeitlich ausgedehnte Policy mit Start-/Terminationbedingung.

**POMDP** — Partially Observable Markov Decision Process.

**PPO** — On-policy Actor-Critic-Verfahren, hier primär als Baseline.

**Prioritized Experience Replay** — Sampling nach Lernrelevanz/TD-Fehler statt gleichverteilt.

**R2D2** — Recurrent Replay Distributed DQN.

**R2D3** — R2D2-artiges rekurrentes Off-policy-Lernen mit separaten Demonstrationen.

**Replay Sequence** — Zusammenhängender Episodenausschnitt mit Burn-in- und Learningteil.

**SMDP** — Semi-Markov Decision Process; Aktionen/Options können unterschiedlich lange dauern.

**Structured Observation** — Enginebasierte player-observable Daten statt gerenderter Pixel.

**Task Fixture** — Reproduzierbare Setupdefinition eines kontrollierten Trainings-/Testtasks.

**Truncated** — Episode endet wegen externer Grenze, nicht natürlichem Taskterminal.

**World Model** — Gelerntes Modell von Übergängen/Rewards zur Imagination oder Planung.
