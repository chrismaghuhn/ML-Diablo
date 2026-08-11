# 02 — Scope und Nicht-Ziele

## Initialer Scope

- Diablo 1 über einen lokal gepinnten DevilutionX-Stand;
- Einzelspieler;
- zunächst Warrior auf Normal;
- strukturierte, player-observable Observation;
- semantische, von der Engine erzeugte Aktionskandidaten;
- synchrones `reset → observation → step → observation`;
- pro Engine-Instanz ein Prozess;
- Seed-basierte Tests und Evaluation;
- Demonstrationen aus Skriptbots und optional Menschen;
- Behavior Cloning, recurrent PPO als Baseline, R2D2 und R2D3-Stil als Hauptvergleich;
- feste Skills vor gelerntem Manager.

## Explizite Nicht-Ziele für v1

### Kein Pixel-only-Agent

Ein Pixel-Agent vermischt Wahrnehmung, UI-Zustand, Steuerung und Strategie. Er ist später sinnvoll, aber als erster Schritt würde er die Ursache jedes Fehlers verschleiern.

### Kein vollständiger Full-Run in M0–M3

Frühe Milestones dürfen keine breite, ungetestete API vorwegnehmen. Jede neue Aktionsfamilie wird mit einem eigenen Slice eingeführt.

### Kein Self-Play

Der Einzelspieler-Run besitzt keinen lernenden strategischen Gegenspieler. Gegner-KI und Welt sind Teil der Engine. Self-Play wäre erst für PvP oder kooperative Multi-Agent-Varianten relevant.

### Kein eigenes Diablo-Regelmodell als Autorität

World Models dürfen später Planungsmodelle sein, aber ihre Vorhersagen ersetzen nie den Engine-Übergang in Trainingsepisoden oder Evaluation.

### Kein endloses Reward Shaping

Dichte Diagnosekomponenten sind erlaubt. Die Hauptmetrik bleibt Task-Erfolg auf zurückgehaltenen Seeds. Jede Shaping-Komponente wird separat geloggt und ablierbar gemacht.

### Kein Upstream-Monorepo im Scaffold

DevilutionX wird lokal unter `third_party/` geholt oder als Schwester-Checkout verwaltet. Seine Lizenz und Assets bleiben klar getrennt.

### Keine kommerzielle Distribution

Die beobachtete Sustainable Use License des Upstreams schränkt Nutzung und Distribution ein. Das Scaffold erteilt keine Rechte an DevilutionX oder Diablo-Inhalten.

## Später mögliche Erweiterungen

- Rogue und Sorcerer;
- Hellfire;
- Pixel- oder multimodale Wahrnehmung;
- model-based Combat Search;
- intrinsische Exploration;
- offline RL aus großen Laufdatensätzen;
- Meta-Learning über Charakterklassen;
- Multiplayer/PvP als separates Projekt;
- procedurally generated Mini-Diablo-Testumgebung ohne proprietäre Assets.

Jede Erweiterung benötigt eine neue Problemdefinition und darf nicht stillschweigend in einen laufenden Milestone rutschen.
