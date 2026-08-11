# 05 — Environment-Vertrag

## API

```python
observation = env.reset(seed=seed, task_id=task_id)
result = env.step(candidate_id)
env.close()
```

Die kleine API ist bewusst enger als Gymnasium. Wrapper können später Gym-/RLlib-Kompatibilität anbieten; der Kernvertrag bleibt unabhängig.

## Reset-Semantik

`reset(seed, task_id)` muss:

- eine neue `episode_id` erzeugen;
- genau den angeforderten Task initialisieren;
- alle taskrelevanten RNG-Quellen kontrollieren;
- den Zustand bis zur ersten Entscheidungsgrenze stabilisieren;
- eine validierte Observation mit `step_id=0` liefern;
- keine vorherige Episode beeinflussen lassen;
- bei fehlenden Assets oder Setupfehlern explizit fehlschlagen.

Der gleiche Seed muss nicht auf jeder zukünftigen Upstream-Version dieselbe Welt erzeugen. Innerhalb einer gepinnten Engine-/Task-/Contract-Version ist er jedoch reproduzierbar.

## Step-Semantik

`step(candidate_id)`:

1. akzeptiert nur eine ID der zuletzt gelieferten Observation;
2. führt genau die zugehörige semantische Aktion aus;
3. lässt die Engine bis zur nächsten Entscheidungsgrenze laufen;
4. erhöht `step_id` exakt um eins;
5. darf `engine_tick` um eine variable positive Zahl erhöhen;
6. liefert Reward, `terminated`, `truncated` und Diagnostik;
7. darf nach Terminal nicht erneut aufgerufen werden.

## Terminated und Truncated

- `terminated=true`: natürlicher Taskabschluss, zum Beispiel Erfolg oder Tod.
- `truncated=true`: externe Grenze, zum Beispiel maximale Entscheidungen oder Watchdog-Abbruch ohne Enginefehler.
- Infrastrukturfehler werden als Exceptions/Fehlercodes behandelt und nicht als Truncation kaschiert.
- Beide Flags dürfen nicht gleichzeitig wahr sein.

## Entscheidungstakt

Ein zu feiner Takt erzeugt tausende triviale Wiederholungsentscheidungen. Ein zu grober Takt nimmt dem Agenten Reaktionsmöglichkeiten. V1 verwendet semantische Grenzen:

- Spieler ist aktionsbereit;
- Ziel-/Item-/Store-/Stat-Auswahl nötig;
- Levelwechsel abgeschlossen;
- Terminalzustand.

Für Aktionen mit Dauer gilt eine Interrupt-Policy. Beispielsweise kann `MOVE_TO_TILE` beendet werden, wenn:

- Ziel erreicht;
- Weg blockiert;
- sichtbarer Gegner in einen konfigurierten Gefahrenradius tritt;
- HP/Status kritisch geändert wird;
- Terminal eintritt;
- Ticklimit überschritten wird.

Diese Policy ist Teil des Action-Vertrags und muss versioniert sein.

## Determinismusklassen

### D0 — Seedbarer Reset

Gleicher Seed erzeugt gleichen initialen kanonischen Zustand.

### D1 — Action Replay

Gleicher Seed plus gleiche semantische Aktionsfolge erzeugt gleiche Übergänge.

### D2 — Plattformstabilität

Gleiche Resultate über Compiler/OS. Das ist schwieriger und kein sofortiger M0-Zwang; Unterschiede werden gemessen und dokumentiert.

M0 verlangt D1 innerhalb derselben Buildidentität.

## Kanonischer State-Hash

Der Hash darf keine instabilen Daten enthalten:

- keine Pointer;
- keine Wandzeit;
- keine unordered-Iteration ohne Sortierung;
- keine UI-Positionen;
- keine uninitialisierten Bytes;
- keine fließenden Renderinterpolationen.

Enthalten sein sollen taskrelevante Zustände, darunter RNG-Zustand, Spieler, aktive Entities, Level, Inventar, Quests und Engine-Tick. Der vollständige privilegierte Hash bleibt im Engine-Test; der öffentliche Trajektorienhash basiert nur auf dem versionierten Datenvertrag.

## Legalitätsgarantie

Eine Observation darf nur Kandidaten enthalten, die zum Erzeugungszeitpunkt legal sind. Zwischen Observation und Step darf die Engine nicht autonom weiterticken. Der Adapter muss daher entweder:

- die Engine an der Grenze einfrieren; oder
- Kandidat und State-Version atomar validieren.

V1 friert zwischen Requests logisch ein.

## Keine versteckten Autoaktionen

Eine Engine-Autoaktion, die strategische Wahl enthält, muss sichtbar gemacht werden. Reine mechanische Ausführung darf intern bleiben. Beispiele:

- Weg entlang eines bereits gewählten Ziels: intern möglich, mit Interrupts;
- automatisch „bestes Item“ wählen: nicht erlaubt;
- automatisch Trank bei niedrigen HP nutzen: nicht erlaubt;
- Inventargeometrie für eine bereits gewählte Platzierung lösen: als klarer Controller möglich, aber dokumentieren.

## Timeouts

Jeder Step besitzt:

- maximales Engine-Tickbudget;
- IPC-Deadline;
- Prozess-Watchdog;
- eindeutigen Fehlercode;
- Crash-/State-Dump ohne proprietäre Assetkopie.

Timeouts werden nach Task, Build und Plattform metrisch ausgewertet.

## Environment-Metadaten

Health/Reset sollen mindestens melden:

```text
engine revision
engine build fingerprint
upstream license fingerprint
protocol version
observation version
action version
task registry version
platform/compiler
asset mode (shareware/full/hellfire), ohne Assetbytes
```

Diese Metadaten fließen in Run- und Checkpoint-Manifeste.
