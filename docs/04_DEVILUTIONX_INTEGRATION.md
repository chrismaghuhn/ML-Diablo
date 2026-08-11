# 04 — DevilutionX-Integration

## Untersuchte Upstream-Anker

Der in `upstream.lock.toml` gepinnte Stand wurde als Integrationsreferenz untersucht. Relevant sind insbesondere:

- `Source/headless_mode.hpp`: vorhandener interner Headless-Modus, laut Kommentar für Tests gedacht;
- `Source/diablo.h`: `game_loop(bool)`, `GameLogicStep`, `PlayerActionType`, Dungeon-/Level-Seeds;
- `Source/engine/demomode.h`: Recording/Playback, Game-Loop-Hooks und simulierte Zeit;
- `Source/diablo.cpp`: semantische Spielbefehle werden über bestehende Command-Pfade wie Walk, Attack und Operate ausgelöst;
- vorhandene C++-Tests und Fixtures als Muster für deterministische, assetarme Szenarien.

Diese Anker machen eine saubere Integration plausibel, sind aber **keine fertige RL-API**. Der aktuelle Headless-Modus allein garantiert weder vollständigen Reset noch kontrolliertes Step-Timing.

## Zielbild

Es soll ein eigener, nicht-interaktiver Environment-Binary entstehen, zum Beispiel:

```text
devilutionx-ai-env
  --listen unix:/tmp/dxai-123.sock
  --task-registry path/to/tasks
  --asset-path <user-owned-data>
  --strict-determinism
```

Der Binary enthält den kleinen Adapter und linkt gegen die lokale DevilutionX-Quelle. Python startet und überwacht ihn. Die normale UI-Anwendung bleibt getrennt.

## M0.2 implementierter Slice: First Real Observation

M0.2 verwendet eine separate `engine_adapter/observation_probe`-Executable.
Sie patcht den Upstream-Checkout nicht und stellt noch keinen dauerhaften
Environment-Prozess bereit. Die Probe initialisiert den aktiven Spieler ueber
die vorhandenen Engine-Initialisierungsroutinen und exportiert genau eine
read-only Observation fuer `combat.single_melee.v0`.

Die Pfadtrennung ist absichtlich:

```text
DiabloDataPath  -> DevilutionX BasePath   -> DIABDAT.MPQ
CoreAssetsPath  -> DevilutionX AssetsPath -> lose Build-Core-Assets
RuntimePath     -> DLL-Suchpfad           -> libdevilutionx_so.dll
```

Der Exporter uebertraegt:

- den aktiven Spieler mit Position, Ressourcen, Attributen und Inventar;
- nur ein begrenztes Tilefenster mit sichtbarkeitsgeprueften Tiles;
- nur sichtbare aktive Monster;
- keine Roh-Engine-Container und keine unbekannten Item-Metadaten.

Das v1-Observation-Schema verlangt eine nicht-leere Candidate-Liste. Bis zur
Candidate-Implementierung liefert die Probe deshalb genau einen `WAIT`-
Placeholder. Dieser ist nicht ausfuehrbar und ersetzt weder M0.3 noch die
spatere IPC-Grenze.

Im gepinnten Upstream ueberspringt `HeadlessMode` die UI, startet aber noch
Levelmusik. Die Probe setzt daher direkt danach `gbMusicOn=false` und
`gbSoundOn=false`, damit die Read-only-Initialisierung kein SDL-Audiogeraet
voraussetzt. Gameplay-Regeln werden dadurch nicht veraendert.

Die M0.2-Build- und Verifikationsschritte stehen in
[`docs/runbooks/M02_OBSERVATION.md`](runbooks/M02_OBSERVATION.md). Die echte
Engine-Ausgabe wird erst nach JSON-Schema- und Determinismuspruefung als
Observation an Python uebergeben.

## Empfohlener Integrationspfad

### Schritt 1 — Upstream sauber pinnen

- Checkout exakt auf `upstream.lock.toml`.
- Lizenzdatei archivieren/hash-en, ohne sie umzuschreiben.
- Build unverändert durchführen.
- vorhandene Tests ausführen.
- Compiler, Plattform und CMake-Optionen protokollieren.

### Schritt 2 — AI-Build-Flag

Ein klarer Build-Schalter, beispielsweise `BUILD_DXAI_ENV`, soll Adaptercode aktivieren. Normale Builds dürfen durch den Adapter weder Verhalten noch Binärgröße verändern.

### Schritt 3 — Szenario-Fixtures

M0/M1 dürfen nicht durch Menüautomation starten. Ein Fixture erzeugt den erforderlichen Charakter, Levelzustand, Gegner und Inventar direkt über dafür freigegebene Test-/Setup-APIs. Setup-State ist privilegiert; nach `reset()` darf die Observation nur player-observable Daten exportieren.

### Schritt 4 — Deterministischer Reset

Reset muss mindestens kontrollieren:

- globalen und levelbezogenen RNG;
- Charakterzustand;
- Dungeon-/Set-Level-Seeds;
- Monster-, Item-, Objekt- und Missile-Container;
- Quests, Stores und Levelübergänge;
- Inputqueue und Netzwerkcommands;
- simulierte Zeit;
- Audio/UI-Nebenwirkungen;
- Save-/Config-Zugriffe.

Ein Reset, der nur ein Savegame neu lädt, ist für M0 nicht automatisch ausreichend: Saveformat, Zeit, globale Caches und nicht serialisierte Zustände müssen geprüft werden.

### Schritt 5 — Observation Exporter

Der Exporter liest Engine-Strukturen, filtert sie aber durch einen expliziten Observability-Vertrag. Er darf beispielsweise nicht alle Monster des Levels exportieren, nur weil der Container zugänglich ist.

Empfohlene Schichten:

```text
Engine globals
  ↓
RawSnapshot (nur im Adapter, privilegiert)
  ↓ VisibilityFilter
ObservableSnapshot
  ↓ ContractMapper
Observation v1
```

Der `RawSnapshot` wird nicht an Python übertragen und nicht in Trainingsartefakten gespeichert.

### Schritt 6 — Legal Candidate Generator

Kandidaten werden aus dem aktuellen Spielzustand erzeugt und gegen dieselben Regeln validiert, die der normale Inputpfad verwendet. Für M1 reichen:

- `WAIT`;
- angrenzendes oder kontrolliert pfadbares `MOVE_TO_TILE`;
- `ATTACK_ENTITY` für gültige Ziele;
- `PICK_UP_ITEM`;
- `USE_BELT_SLOT`.

Neue Aktionsfamilien kommen erst mit eigenen Tests hinzu.

### Schritt 7 — Semantische Ausführung

Der Adapter soll bestehende Engine-Command-Pfade aufrufen, nicht Pixelpositionen vortäuschen. Wo möglich wird derselbe interne Command erzeugt, den normale Eingabe erzeugen würde. Dadurch bleiben Netzwerk-/Commandvalidierung und Gameplaylogik gemeinsam.

### Schritt 8 — Decision Boundary

Die zentrale neue Abstraktion ist:

```cpp
bool IsAgentDecisionBoundary();
Observation BuildObservation();
void SubmitCandidate(uint32_t candidateId);
AdvanceResult AdvanceUntilNextBoundary(uint32_t maxTicks);
```

Eine Grenze kann zum Beispiel erreicht sein, wenn:

- der Spieler eine neue Aktion annehmen kann;
- ein Modal-/Store-Subdialog eine Auswahl verlangt;
- eine Ziel-/Item-/Stat-Auswahl erforderlich ist;
- der Spieler tot ist;
- ein Taskterminal erreicht ist.

Sie darf nicht an jedem Renderframe feuern.

### Schritt 9 — IPC und Watchdog

- lokale Socket- oder Named-Pipe-Verbindung;
- length-prefixed Frames;
- Request-ID und erwartete Step-ID;
- maximale Messagegröße;
- Deadline pro Request;
- Heartbeat/Health;
- Prozesskill und reproduzierbares Crashbundle bei Timeout;
- keine Netzwerkfreigabe nach außen.

## Demo-Mode sinnvoll nutzen

Der vorhandene Demo-Mode ist wertvoll für:

- Vergleich von Timing- und Replayverhalten;
- deterministische Referenzläufe;
- mögliche Aufzeichnung menschlicher Eingaben;
- Regressionstests nach Upstream-Upgrades.

Er ersetzt aber nicht automatisch den semantischen Aktionsvertrag. Demo-Events müssen in gültige Kandidatenlabels aufgelöst werden.

## Reset- und Step-Pseudocode

```cpp
Observation AiEnvironment::Reset(const ResetRequest &request)
{
    ValidateTask(request.taskId);
    ResetAllGlobalState();
    InstallDeterministicClock();
    SeedAllRngStreams(request.seed);
    BuildScenario(request.taskId);
    AdvanceUntilStableInitialBoundary();
    auto observation = BuildObservableObservation();
    ValidateObservation(observation);
    return observation;
}

StepResult AiEnvironment::Step(const StepRequest &request)
{
    RejectStaleRequest(request);
    const auto &candidate = CurrentCandidates().at(request.candidateId);
    ExecuteSemanticCandidate(candidate);
    const auto transition = AdvanceUntilNextBoundary(MaxTicksForTask());
    return BuildValidatedStepResult(transition);
}
```

## Upstream-Diff-Regeln

- kleine, isolierte Dateien unter einem klaren Adapter-Namespace;
- keine breit gestreuten `#ifdef`-Blöcke ohne ADR;
- keine Änderung normaler Gameplayregeln;
- jeder Hook besitzt einen Contract-Test;
- jeder Upstream-Rebase führt Determinismus- und Replay-Tests aus;
- generierte Protokolldateien werden getrennt von handgeschriebenem Code gehalten.

## M0-Abnahme

Die Bridge gilt erst als vorhanden, wenn:

1. derselbe Seed plus dieselbe semantische Aktionsfolge denselben kanonischen Hash ergibt;
2. 10.000 zufällige legale Steps keinen illegalen Engine-Command erzeugen;
3. mutierte/stale Candidate-IDs abgelehnt werden;
4. unsichtbare Monster/Items nicht in Observation oder Events auftauchen;
5. aufgezeichnete Läufe replaybar sind;
6. Reset keine Zustandsreste zwischen Episoden zeigt;
7. Headless-Durchsatz und Crashrate gemessen sind;
8. Assetfehler klar und ohne UI-Dialog gemeldet werden.
