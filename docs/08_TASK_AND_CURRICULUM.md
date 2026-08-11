# 08 — Tasks und Curriculum

## Warum ein Curriculum nötig ist

Ein Full Run kombiniert unterschiedliche Fehlerquellen. Scheitert ein End-to-End-Agent, ist unklar, ob Wahrnehmung, Kampf, Navigation, Loot, Ökonomie, Gedächtnis oder Credit Assignment verantwortlich ist. Das Curriculum erzeugt kontrollierte Aufgaben mit eigenen Erfolgskriterien und Seedverteilungen.

## Task-Vertrag

Jeder Task definiert mindestens:

- stabile `task_id` und Version;
- Setup und erlaubte Asset-/Game-Variante;
- Charakterklasse, Level und Loadoutpolicy;
- zulässige Aktionsfamilien;
- Erfolg, Tod, Truncation und Infrastrukturfehler;
- maximales Decision-/Tickbudget;
- Rewardversion;
- Train-, Validation- und Test-Seeds;
- Evaluationsmetriken;
- Promotion-Gate;
- erlaubten oder verbotenen privilegierten Setup-State.

## Curriculum

### M0 — Bridge Contract

**Zweck:** Keine Strategie, nur Infrastruktur.

- deterministischer Reset;
- legaler Step;
- Replay;
- kein Hidden-State-Leak;
- Prozessabsturz- und Timeoutbehandlung.

### M1 — Single Melee Combat

- ein Warrior, festes Loadout;
- ein Nahkampfmonster;
- kleine Arena;
- Bewegung, Angriff, optional ein Trank;
- unbekannte Spawnseeds.

Ziel ist nicht nur Killrate, sondern Überlebens- und Ressourceneffizienz.

### M2 — Room Combat

- mehrere Gegner;
- gemischte HP/Positionen;
- Chokepoints;
- Retreat und Potion Timing;
- später ranged Gegner.

Subtasks werden nach Schwierigkeit parametrisiert, nicht als neue unversionierte Sonderfälle eingebaut.

### M3 — Exploration

- Gegner zunächst deaktiviert oder ungefährlich;
- generierter Floor;
- Türen/Blockaden;
- Treppe finden;
- begrenzte Schritte;
- Memory- und Frontier-Metriken.

### M4 — Loot und Equipment

- kontrollierte Itemauswahl;
- Inventarplatz;
- identifizierte vs. nicht identifizierte Werte;
- Equip/Drop/Pickup;
- downstream Combat-Test zur Bewertung, nicht nur statischer Score.

### M5 — Town Loop

- Verkauf, Einkauf, Reparatur;
- Budget und Inventar;
- Entscheidung, ob sich eine Stadtfahrt lohnt;
- Rückkehr zum richtigen Level.

### M6 — Floor Clear

Erste Integration:

```text
explore ↔ fight ↔ loot ↔ retreat
```

Noch ohne komplette Charakterprogression.

### M7 — Multi-Level Run

- mehrere Floors;
- persistente Ressourcen;
- Stadtfahrten;
- Equipmentänderungen;
- Death-/Restartpolicy.

### M8 — Full Warrior Run

Fresh Warrior, Normal, bis Diablo. Erfolg wird über eine große, vorab festgelegte Testseedmenge gemessen—not cherry-picked videos.

### M9 — Generalisierung

- Rogue/Sorcerer;
- zurückgehaltene Gegnerfamilien;
- neue Loadouts;
- andere Reward-/Difficulty-Konfigurationen;
- optional Hellfire.

## Promotion-Gates

Ein Skill wird erst integriert, wenn:

- mindestens 128 feste Evaluationsepisoden gelaufen sind;
- Erfolgsrate und Konfidenzintervall das Gate erfüllen;
- kein Illegal Action/Engine Fault auftritt;
- Random- und Skriptbaselines geschlagen werden;
- mindestens drei Trainingsseeds/Initialisierungen konsistent sind;
- Generalisierungsleistung nicht nur auf Trainingsseeds steigt;
- Ablation gegen die vorherige Version vorliegt.

## Difficulty Sampling

Curriculum-Level werden nicht ausschließlich linear durchlaufen. Nach Promotion bleibt ein Anteil älterer Tasks im Training, um katastrophales Vergessen zu messen und zu verhindern.

Beispiel:

```text
60 % aktueller Task
25 % vorherige Tasks
10 % nächsthärtere Probeaufgaben
 5 % Diagnose-/Regressionstasks
```

Die Verteilung wird im Runmanifest gespeichert.

## Automatisches Curriculum

Später kann die Taskauswahl nach Lernfortschritt gewichtet werden. V1 verwendet jedoch explizite, nachvollziehbare Stufen. Automatische Auswahl darf nicht gleichzeitig mit einer ungeklärten Basisarchitektur eingeführt werden.

## Task Leakage vermeiden

- Testseeds bleiben aus Replay, Demo- und Debugartefakten heraus.
- keine Modellselektion nach Testresultaten;
- Scenario-Namen dürfen nicht direkt die optimale Aktion kodieren;
- Setup-Parameter werden im Training randomisiert, aber im Test vollständig protokolliert;
- wiederholte menschliche Betrachtung einzelner Testseeds wird als potenzielles Leakage behandelt.
