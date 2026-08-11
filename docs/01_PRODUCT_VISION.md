# 01 — Projektvision

## Forschungsfrage

Kann ein nicht-sprachbasiertes ML-System aus spielerbeobachtbaren Zuständen, Demonstrationen und eigener Erfahrung eine robuste Diablo-Strategie lernen, die über einzelne Seeds, Räume, Gegnergruppen, Ausrüstungskombinationen und schließlich Charakterklassen generalisiert?

## Der Demo-Hook

Die verständliche Außendarstellung lautet:

> „Ein frischer Diablo-Charakter lernt selbständig kämpfen, erkunden, Loot verwalten, die Stadt nutzen und am Ende Diablo besiegen.“

Die wissenschaftlich präzisere Aussage lautet:

> „Ein hierarchischer, rekurrenter Agent lernt in einer partiell beobachtbaren, prozedural variierenden, langhorizontigen Umgebung mit dynamischem semantischem Aktionsraum aus Demonstrationen und Off-Policy-Erfahrung.“

Beide Aussagen müssen wahr bleiben. Eine beeindruckende Demo darf nicht durch versteckten State, handgeskriptete Full-Run-Logik oder einen einzigen memorisierten Seed erkauft werden.

## Produktprinzipien

### Beobachtbares Verhalten vor abstraktem Modellscore

Jeder Milestone endet mit einem sichtbaren Verhalten: ein Raum wird überlebt, eine Karte wird systematisch erkundet, ein schlechter Gegenstand wird liegen gelassen, eine Stadtfahrt wird sinnvoll ausgelöst. Loss-Kurven allein sind kein Erfolg.

### Messbare Generalisierung

Training, Validierung und Test verwenden getrennte Seeds. Später werden zusätzlich Gegnerfamilien, Itemverteilungen, Dungeon-Level und Charakterklassen zurückgehalten.

### Engine-Wahrheit statt Parallelregeln

Der ML-Stack implementiert keine zweite Diablo-Regelengine. Alle Effekte werden von DevilutionX ausgeführt. Python darf Zustände kodieren, Kandidaten bewerten und Daten speichern, aber keine Schäden, Dropchancen oder Shoppreise simulieren und als Wahrheit behandeln.

### Erst strukturierter State, später Pixel

Strukturierte Beobachtungen testen die Entscheidungsintelligenz und reduzieren Wahrnehmungsrauschen. Eine spätere Pixel-Variante ist eine eigene Forschungsfrage und muss gegen die strukturierte Obergrenze verglichen werden.

### Hybrid statt Reinheitsdogma

Pathfinding, Legalitätsprüfung, Inventarplatzierung und andere exakt lösbare Teilprobleme dürfen klassische Algorithmen verwenden. ML wird dort eingesetzt, wo Unsicherheit, langfristiger Wert, Generalisierung oder Strategieauswahl entscheidend sind.

## Langfristige Erfolgsstufen

1. **Contract-valid:** deterministisch, replaybar, ohne Leaks.
2. **Skill-valid:** einzelne Skills schlagen Skriptbaselines auf unbekannten Seeds.
3. **Integrated:** ein Manager kombiniert Skills ohne handgeschriebene Full-Run-Sequenz.
4. **Robust:** Erfolg über breite Seeds und Startbedingungen.
5. **General:** Transfer zwischen Loadouts, Gegnern und Klassen.
6. **Scientific:** Ablationen erklären, welche Komponenten tatsächlich helfen.
7. **Demo-ready:** Läufe, Kartenmemory, Q-Werte und Skillwechsel sind visualisierbar.

## Nicht die Vision

Das Projekt ist kein Speedrun-Bot, kein Tool zum Cheaten in Multiplayer-Partien, kein LLM-Agent, kein Auto-Clicker und kein kommerzielles Diablo-Produkt. Es ist eine nicht-kommerzielle Game-AI-Forschungsplattform.
