# 18 — Sicherheit, Datenschutz und rechtliche Grenze

> Dieses Dokument ist eine Engineering-Risikoanalyse, keine Rechtsberatung.

## DevilutionX-Lizenz

Am in `upstream.lock.toml` dokumentierten Stand veröffentlicht DevilutionX den Source unter der **Sustainable Use License 1.0** und beschreibt den Source als nicht-kommerziell nutzbar. Das ist nicht mit einer klassischen OSI-Open-Source-Lizenz gleichzusetzen.

Konsequenzen für dieses Projekt:

- keine kommerzielle Nutzung oder Vermarktung aus dem Scaffold ableiten;
- Lizenztext des konkreten Upstream-Stands vor jeder Distribution erneut prüfen;
- DevilutionX nicht in dieses ZIP vendoren;
- einen gepinnten lokalen Checkout verwenden;
- Adapteränderungen, die in DevilutionX kompiliert werden, als Teil einer lizenzpflichtigen Derivative behandeln;
- keine Behauptung, Apache-2.0 des Scaffolds überschreibe Upstreambedingungen.

## Diablo-Assets

DevilutionX benötigt Original- oder Shareware-Daten. Das Scaffold enthält und lädt keine MPQs automatisch herunter. Nutzer müssen selbst rechtmäßig auf benötigte Daten zugreifen.

Nicht committen:

- `DIABDAT.MPQ`, `spawn.mpq` oder Hellfire-MPQs;
- Grafiken, Sounds, Musik, Videos;
- extrahierte vollständige Tabellen/Texte, sofern deren Veröffentlichung nicht geklärt ist;
- Savegames mit eingebetteten proprietären Inhalten;
- Screenshots als Testfixtures ohne gesonderte Prüfung.

`.gitignore` enthält defensive Muster; sie ersetzen keinen Review.

## Marken und Außendarstellung

- „Diablo“ und „Blizzard“ nur beschreibend verwenden;
- keine offiziellen Logos;
- keine Verwechslungsgefahr mit einem offiziellen Produkt;
- Disclaimer beibehalten;
- Projektname darf nicht wie ein offizieller DevilutionX-/Blizzard-Release wirken.

## Datensatzveröffentlichung

Strukturierte Trajektorien sind abgeleitete Daten, können aber Typnamen, Werte und Spielstruktur enthalten. Vor öffentlicher Veröffentlichung eines großen Datensatzes sind Lizenz-, Urheber- und Vertragsfragen separat zu prüfen. Das Scaffold garantiert keine freie Redistributierbarkeit solcher Daten.

## Lokale IPC-Sicherheit

Der Environment-Dienst ist nicht für untrusted remote access gedacht.

Pflichten:

- nur Unix Socket/Named Pipe oder Loopback;
- zufälliger Endpunkt und restriktive Dateirechte;
- Messagegrößenlimit;
- Request-/Step-ID;
- timeouts;
- parser validation;
- keine beliebigen Dateipfade/Commands aus Requests;
- Environmentprozess mit minimalen Rechten;
- keine automatische Portfreigabe.

## Untrusted Artefakte

### Checkpoints

Python-/PyTorch-Pickle kann Code ausführen. Fremde `.pt`/`.pth`-Dateien werden nicht ungeprüft geladen. Bevorzugt:

- `safetensors` für Gewichte;
- `torch.load(..., weights_only=True)` wo möglich;
- Hash/Signatur und Herkunft;
- getrennte, vertrauenswürdige Optimizerzustände;
- isolierter Prozess für Fremdartefakte.

### Trajektorien und Configs

- JSON/YAML safe loader;
- Schema und Größenlimit;
- keine YAML object tags;
- keine Pfadtraversal aus Episode IDs;
- Hashverifikation;
- Quarantäne bei Fehlern.

### Protobuf/IPC

- bounded repeated fields;
- recursion/message limits;
- unknown version reject;
- fuzzing des Parsers;
- stale request reject.

## Datenschutz bei Humandemos

- pseudonyme Contributor-ID;
- keine Audio-/Webcam-/Desktopaufnahme standardmäßig;
- nur gamebezogene semantische Inputs;
- dokumentierte Einwilligung;
- Zweck und Veröffentlichungsstatus;
- Löschprozess;
- keine E-Mail/Realname im öffentlichen Manifest.

## Secrets

Das Projekt benötigt grundsätzlich keine Cloudtokens. Falls später Tracking/Storage angebunden wird:

- `.env` ignorieren;
- least privilege;
- keine Secrets in Config, Log, Checkpoint oder ZIP;
- Secret Scanning in CI;
- Rotation nach Leak.

## Multiplayer und Cheating

Der Scope ist lokales Singleplayer-Research. Keine Schnittstelle wird für Live-Multiplayer-Automation, Gegnerausspähung oder Regelumgehung bereitgestellt. Netzwerkfeatures des Spiels werden im Environment-Build deaktiviert, soweit möglich.

## Veröffentlichungsgate

Vor einem öffentlichen Release prüfen:

1. Upstream-Lizenz am gepinnten Commit;
2. keine Upstreamquelle versehentlich im ZIP;
3. keine Assets/MPQs/Saves/Screenshots;
4. keine privaten Demonstratorinformationen;
5. Dependencylizenzen;
6. Trademark-Disclaimer;
7. Hash-/SBOM-/Source-Audit;
8. klare Kennzeichnung unfertiger Bridge/Modelle.
