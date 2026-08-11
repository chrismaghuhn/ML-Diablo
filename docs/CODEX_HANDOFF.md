# Codex-Handoff: Umsetzung der echten DevilutionX-Bridge

Diese Datei ist als operative Arbeitsanweisung für einen Coding-Agenten gedacht. Architekturautorität sind die ADRs und die Vertragsdokumente.

## Auftrag

Implementiere **nur M0/M0.5**: eine deterministische, headless, prozessisolierte DevilutionX-Environment-Bridge für kontrollierte Fixtures. Implementiere noch kein RL.

## Harte Nicht-Ziele

- kein PPO, DQN, R2D2, R2D3 oder neuronales Training;
- keine Pixelpipeline;
- kein vollständiger Run;
- keine Quest-/Shop-/Inventory-Automation außerhalb des gewählten Fixtures;
- keine Maus-/Tastatur-Simulation;
- keine Diablo-Assets committen;
- keine Änderung des vorgemerkten Datenvertrags ohne ADR.

## Vor Beginn

1. Lies `README.md`, `docs/04_DEVILUTIONX_INTEGRATION.md`, `docs/contracts/*` und alle akzeptierten ADRs.
2. Prüfe `upstream.lock.toml` und checke exakt diesen Upstream-Commit aus.
3. Erstelle einen sauberen Git-Checkpoint.
4. Baue und teste Upstream unverändert.
5. Dokumentiere Plattform, Compiler, CMake-Flags und Testresultat.

## Ziel-API

Die Bridge muss logisch Folgendes anbieten:

```text
Reset(seed, task_id) -> Observation
Step(episode_id, expected_step_id, candidate_id) -> StepResult
Close()
```

Jede Anfrage besitzt `request_id` und `protocol_version`. Stale, doppelte oder fremde Requests werden deterministisch abgelehnt.

## Integration in DevilutionX

Bevorzugte Anknüpfungspunkte im geprüften Stand:

- `HeadlessMode` für UI-freie Tests;
- `game_loop(bool)`/Game-Logic-Grenze;
- vorhandene Netzwerk-/Command-Pfade wie Walk, Attack und Operate;
- Dungeon-/Level-Seeds;
- Demomode für Timing/Replay-Vergleich.

Kein direkter Mutationszugriff aus Python auf globale Enginearrays. Der Adapter darf intern C++-State lesen, exportiert aber nur den freigegebenen Observation-Vertrag.

## Fixture `combat.single_melee.v0`

Minimaler kontrollierter Slice:

- Singleplayer;
- Warrior mit fixem Loadout;
- kleine begehbare Region;
- ein deterministisch platzierter Nahkampfgegner;
- optional ein Heiltrank;
- Aktionen: WAIT, MOVE_TO_TILE, ATTACK_ENTITY, PICK_UP_ITEM, USE_BELT_SLOT;
- Ende: Monster tot, Spieler tot oder Decision-Limit.

Falls das Fixture mit Standard-Dungeon-Generierung nicht stabil isolierbar ist, darf ein Testfixture im Adapterlayer konstruiert werden. Es darf keine allgemeinen Spielregeln duplizieren.

## Abnahmetests

Pflicht:

1. gleiche Engineversion + Fixtureversion + Seed + semantische Aktionsfolge → gleicher kanonischer Trajektorienhash;
2. mindestens 100 Seeds, je zweimal ausgeführt;
3. Candidate IDs dicht und deterministisch sortiert;
4. jeder angebotene Candidate wird entweder akzeptiert oder der Test schlägt fehl;
5. nicht angebotene Candidate IDs werden ohne Stateänderung abgelehnt;
6. kein unsichtbarer Gegner/Item/Occupancy-Leak;
7. Terminalzustand bietet nur Terminal-no-op oder lehnt weitere Schritte eindeutig ab;
8. Crash/Timeout erzeugt einen klassifizierten Enginefehler;
9. Prozess kann nach Fehler vollständig neu gestartet werden;
10. keine MPQ-/Assetdatei in Gitstatus oder Buildartefakten des Scaffold-Repos.

## Lieferumfang

- Adaptercode im DevilutionX-Fork oder sauberer Patchsatz;
- Contract-/Integrationstests;
- Kompatibilitätsnotiz mit Upstream-Commit;
- Beispieltrajektorie ohne proprietäre expressive Inhalte;
- aktualisiertes `docs/04_DEVILUTIONX_INTEGRATION.md` nur bei bestätigten Erkenntnissen;
- keine unmarkierten Annahmen.

## Stop-Regeln

Stoppe die Implementierung und dokumentiere einen Architekturkonflikt, wenn:

- ein erforderlicher State nur durch Hidden-State-Leak exportierbar wäre;
- ein semantic command keine stabile Enginegrenze besitzt;
- deterministische Seeds nicht alle relevanten RNG-Quellen kontrollieren;
- die Upstream-Lizenz oder Assetgrenze unklar wird;
- eine Vertragsänderung nötig ist.
