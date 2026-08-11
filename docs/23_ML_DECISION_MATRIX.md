# 23 — ML-Entscheidungsmatrix

Bewertung: 1 = schlecht, 5 = sehr passend. Werte sind projektspezifische Engineeringeinschätzungen, keine universelle Rangliste.

| Methode | Partielle Beobachtbarkeit | Sample-Effizienz | Demos | Dynamische Candidates | Long Horizon | Implementierungsrisiko | Rolle |
|---|---:|---:|---:|---:|---:|---:|---|
| Reines Behavior Cloning | 4 | 5 offline | 5 | 5 | 2 | 2 | Warmstart/Baseline |
| Recurrent PPO | 4 | 2 | 2 | 5 | 3 | 2 | Pflichtbaseline |
| R2D2 Candidate-Q | 5 | 4 | 1 | 5 | 4 | 4 | Kernablation |
| R2D3 Candidate-Q | 5 | 4 | 5 | 5 | 4 | 4 | **Hauptempfehlung** |
| DQfD feed-forward | 2 | 4 | 5 | 4 | 2 | 3 | historische Baseline |
| IMPALA/V-trace | 4 | 3 | 2 | 5 | 3 | 4 | Skalierungsalternative |
| Discrete SAC | 3 | 4 | 2 | 4 | 3 | 4 | nicht zuerst |
| DreamerV3 | 4 | 5 potenziell | 2 | 2 | 4 | 5 | späterer World-Model-Zweig |
| MuZero + Search | 4 | 3 | 2 | 3 | 5 | 5 | lokale Planung später |
| Offline RL (IQL/CQL) | 3 | 5 offline | 5 | 4 | 3 | 4 | erst bei großem Datensatz |
| Decision Transformer | 4 | 5 offline | 5 | 3 | 3 | 4 | Forschungsbaseline später |
| Evolution/NEAT | 2 | 1 | 1 | 3 | 2 | 3 | nicht passend |
| Handgeschriebener Bot | 5 | n/a | n/a | 5 | 4 | 3 | Baseline/Demonstrator |

## Reines Behavior Cloning

**Stärken:** einfach zu debuggen, nutzt Demonstrationen direkt, passt hervorragend zu Candidate-Klassifikation und rekurrenten Sequenzen.

**Schwächen:** Distribution Shift. Kleine Fehler führen in Zustände, die in Demos fehlen; das Modell weiß dort nicht, wie es zurückkehrt. Es kann Demonstratoren nicht systematisch übertreffen.

**Entscheidung:** zwingender Warmstart und Baseline, aber kein finales Prinzip.

## Recurrent PPO

**Stärken:** robuste Standardimplementierungen, direkte maskierte Policy, einfacher als verteiltes Q-Replay, gut als Reality Check.

**Schwächen:** on-policy Datenbedarf, alte Engine-Erfahrung kaum wiederverwendbar, Demonstrationen erfordern zusätzliche Verfahren, lange sparse Tasks bleiben schwer.

**Entscheidung:** implementieren, um zu beweisen, dass R2D3-Komplexität Mehrwert liefert; nicht primärer Pfad.

## R2D2

**Stärken:** Rekurrenz plus Experience Replay, geeignet für partielle Beobachtbarkeit und teure Simulation, starke Sequenztechnik mit Burn-in.

**Schwächen:** Q-Learning kann instabil sein; Recurrent Replay, Priority Updates und Actor-Lag erhöhen Engineeringaufwand; keine Demonstrationen im Kern.

**Entscheidung:** zentrale ablationsfähige Basis.

## R2D3

**Stärken:** verbindet R2D2 mit Demonstrationen genau für sparse, partiell beobachtbare und variable Tasks. Agent kann Demonstratorwissen nutzen und online verbessern.

**Schwächen:** empfindlicher Demoanteil; Originalergebnisse basieren auf großem Compute; keine Garantie für Diablo; komplexe Pipeline.

**Entscheidung:** beste Übereinstimmung mit Problemstruktur. In kleinen Slices validieren, nicht sofort Full Run trainieren.

## DQfD

DQfD mischt TD- und supervised Demonstrationssignale, ist aber klassisch feed-forward/fester Aktionsraum. Eine rekurrente Candidate-Adaption wäre möglich, läuft praktisch in Richtung des empfohlenen Systems.

**Entscheidung:** konzeptionelle Quelle und kleinere Baseline, nicht Zielarchitektur.

## IMPALA/V-trace

Geeignet für sehr viele verteilte Akteure und Actor-Lag. Weniger datenwiederverwendend als Replay-Q-Learning und nicht natürlich demo-zentriert.

**Entscheidung:** Alternative, falls Replayinfrastruktur/Off-policy-Stabilität scheitert oder massive Actors wichtiger werden.

## DreamerV3

World Models können aus Erfahrung imaginierte Rollouts erzeugen und zeigen starke domänenübergreifende Resultate. Für dieses Projekt entstehen jedoch Zusatzprobleme:

- variable Candidate Sets;
- multimodale strukturierte Zustände;
- lange diskrete Interaktionsketten;
- Modellfehler bei seltenen tödlichen Ereignissen;
- schwierige Validierung, ob Planung Engine-Realität oder Modellartefakte ausnutzt.

**Entscheidung:** später als kontrollierter Branch, zunächst Combat/Floor-Slice und immer gegen reale Engine-Rollouts validieren.

## MuZero/Search

Search ist für taktische Kämpfe attraktiv. Ein komplettes Diablo-MuZero benötigt aber ein gelerntes Dynamics-Modell und viele Candidate-Expansionen. Langfristige Inventory-/Townentscheidungen sprengen lokales Search schnell.

**Entscheidung:** späterer lokaler Combat Planner oder Candidate Reranker, nicht Full-Run-v1.

## Offline RL

Ein großer Datensatz menschlicher oder scripted Runs könnte IQL/CQL-artige Verfahren ermöglichen. Zu Beginn fehlen aber Coverage, Full-Run-Erfolge und ein stabiler Datensatzvertrag.

**Entscheidung:** BC zuerst; Offline RL erst, wenn Datenmenge und Behavior Coverage gemessen sind.

## Hierarchie

Hierarchie ist keine einzelne Lernmethode, sondern die Struktur über dem Kernagenten. Die NetHack-Erfahrung spricht dafür, lange Dungeon-Aufgaben nicht ausschließlich als flache primitive Policy zu behandeln.

**Entscheidung:** feste Skills früh; gelernter Manager später. End-to-End-Feintuning kann folgen, wenn es eine stabile hierarchische Baseline gibt.

## Endentscheidung

```text
Primär:   BC → Candidate-R2D2 → Candidate-R2D3 → Skill Manager
Baseline: Script, BC, recurrent PPO, R2D2
Später:   NGU/Self-Imitation, Offline RL, Dreamer/Search
Nicht:    sofortige Pixel-PPO- oder Full-Run-MuZero-Wette
```
