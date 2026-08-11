# 00 — Executive Summary

## Die Entscheidung

Das Projekt soll **nicht** als „PPO spielt Diablo aus Screenshots“ beginnen. Die empfohlene Kernmethode ist:

> **Hierarchisches, rekurrentes Off-Policy-Value-Learning aus Demonstrationen, technisch an R2D2/R2D3 angelehnt.**

Praktisch bedeutet das:

1. DevilutionX wird zu einer deterministischen, headless ausführbaren Umgebung mit semantischen Entscheidungsgrenzen erweitert.
2. Zunächst werden regelbasierte und menschliche Demonstrationen im exakt gleichen Aktionsraum gesammelt.
3. Ein rekurrenter Candidate-Scorer wird per Behavior Cloning vortrainiert.
4. Derselbe oder ein kompatibler Encoder/LSTM-Kern wird mit n-Step Double-Q-Learning und priorisiertem Sequenz-Replay online verbessert.
5. Agent- und Demonstrationsdaten bleiben in getrennten Replay-Puffern; ein kleiner, zu sweepender Demo-Anteil wird beim Online-Lernen beigemischt.
6. Kampf, Navigation, Loot und Stadt starten als klar abgegrenzte Skills. Erst wenn sie einzeln funktionieren, lernt ein Manager, wann welcher Skill aktiv ist.
7. Intrinsische Exploration und World Models sind spätere Forschungszweige, keine Voraussetzung für v1.

## Warum diese Richtung zu Diablo passt

Diablo ist kein kurzer, voll beobachtbarer Atari-Task. Relevante Eigenschaften sind:

- prozedural variierende Level und Gegnerkonfigurationen;
- nur lokal sichtbare Weltinformationen;
- lange Folgen von Entscheidungen und verzögerte Konsequenzen;
- ein variabler, parametrisierter Aktionsraum;
- klare Teilkompetenzen wie Positionierung, Flucht, Tranknutzung, Lootbewertung und Stadtökonomie;
- kostspielige Simulation im Vergleich zu kleinen RL-Benchmarks;
- verfügbare Skript- und Humandemonstrationen;
- kein natürlicher Self-Play-Gegner im Einzelspielermodus.

Rekurrenz adressiert unvollständige Beobachtbarkeit. Off-Policy-Replay nutzt teure Engine-Erfahrung mehrfach. Demonstrationen lösen das „noch nie Erfolg gesehen“-Problem früher als zufällige Exploration. Semantische Skills verkürzen den effektiven Horizont.

## Das erste echte Ziel

Nicht „Diablo besiegen“, sondern:

> **M0: Ein Seed erzeugt bei identischer Aktionsfolge bitweise dieselbe kanonische Trajektorie; jede angebotene Aktion ist legal; keine Beobachtung enthält versteckte Informationen; ein aufgezeichneter Lauf lässt sich vollständig replayen.**

Ohne dieses Gate ist jeder ML-Erfolg wissenschaftlich unbrauchbar, weil Bugs, Leaks oder nondeterministische Übergänge fälschlich als Lernen erscheinen können.

## Erste vertikale Scheibe

`combat.single_melee.v0`:

- Warrior mit festem Loadout;
- ein Nahkampfgegner;
- begrenzte Arena;
- Bewegen, Angreifen, Trank aufnehmen und verwenden;
- Erfolg: Gegner tot, Spieler lebt;
- feste Train-/Validation-/Test-Seeds;
- Baselines: Random, Safe Script, Aggressive Script, BC, Recurrent PPO, R2D2 ohne Demos, R2D3-Stil.

Diese Scheibe ist klein genug, um Bridge, Observation, Kandidatenaktionen, Recorder, Replay, Modell und Evaluation vollständig durchzutesten.

## Was das ZIP bereits enthält

- ausführbare Python-Verträge und deterministischen Mock;
- JSONL-Trajektorien mit Manifest und SHA-256-Integritätsprüfung;
- priorisierte Sequenz-Replays und getrennten Demo-/Agent-Sampler;
- R2D3-Startkonfiguration mit Sequenz-Burn-in;
- rekurrentes dueling Candidate-Q-Netz in PyTorch;
- Feature-Referenzencoder;
- C++20-Bridge-Vertrag mit Contract-Test;
- logisches Protobuf-Protokoll;
- JSON Schemas und Validierungsskripte;
- Task-Curriculum, Evaluation, ADRs, Risiken und genaue Abnahmekriterien.

## Was bewusst fehlt

- keine kopierte DevilutionX-Quelle;
- keine Diablo-Assets oder MPQs;
- keine behauptete fertige Engine-Bridge;
- kein vollwertiger verteilter Learner;
- keine Pixel-Pipeline;
- kein Full-Run-Agent;
- keine kommerzielle Nutzungserlaubnis.

Diese Lücken sind keine versteckten TODOs, sondern klar abgegrenzte Milestones.
