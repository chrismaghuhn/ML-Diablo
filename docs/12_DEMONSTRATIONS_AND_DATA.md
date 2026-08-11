# 12 — Demonstrationen und Daten

## Datenquellen

### Scriptbots

Vorteile:

- beliebig reproduzierbar;
- Taskabdeckung gezielt steuerbar;
- erzeugen Recovery- und Failurefälle;
- keine manuelle Annotation;
- Policyversion kann im Manifest stehen.

Nachteile:

- spiegeln handgeschriebene Heuristiken;
- können systematische blinde Flecken haben;
- zu perfekte deterministische Skripts reduzieren Zustandsvielfalt.

Mindestens drei Stile sind sinnvoll:

- `safe`: konservativ, früh heilen/retreaten;
- `aggressive`: hoher Damagefokus;
- `exploratory`: diverse, aber legale Entscheidungen.

### Menschliche Demonstrationen

Menschen liefern Strategien, Timing und ungewöhnliche Recovery. Der Collector muss Eingaben in denselben semantischen Candidate Space auflösen. Nicht jedes Inputevent entspricht einer Entscheidung; nur an Decision Boundaries wird ein Trainingslabel gespeichert.

### Agent-Selbstdemonstrationen

Erfolgreiche oder besonders informative Agentläufe können in einen kuratierten Self-Imitation-Store kopiert werden. Sie bleiben als `AGENT_SUCCESS` markiert und werden nicht als menschliche Expertise ausgegeben.

## Mindestmetadaten

Jede Episode speichert:

- Schema- und Contractversionen;
- Engine-/Upstreamrevision und Buildfingerprint;
- Task/Rewardversion;
- Seed;
- Demonstrator/Policy-ID und Stil;
- human/script/agent source;
- Erfolg/Return/Steps;
- raw semantische Actions;
- SHA-256;
- optional Qualitätslabel und Kommentar;
- Collectorversion.

## Erfolgsdaten allein reichen nicht

Ein robustes Modell braucht:

- erfolgreiche Standardläufe;
- suboptimale, aber recoverbare Verläufe;
- gefährliche Zustände;
- knappe Ressourcen;
- Fehlentscheidungen mit anschließender Korrektur;
- alternative Strategien;
- echte Failures mit korrekten Terminalflags.

Nur perfekte Demos erzeugen BC-Policies, die bei eigenem Fehler kollabieren.

## Datensatz-Splits

Split primär nach Seed und Scenariofamilie, nicht zufällig nach Transition. Sonst landen nahezu identische Zustände derselben Episode in Train und Validation.

```text
train:      freigegebene Trainingsseeds
validation: eigene Seeds, für Modellwahl
public test: feste Regressionseeds
sealed test: selten betrachtete Abschlussseeds
```

Demonstrationen auf Testseeds sind verboten.

## Qualität und Gewichtung

Qualität ist mehrdimensional:

- Taskerfolg;
- Überleben/HP;
- Ressourceneffizienz;
- Decisions/Zeit;
- Strategievielfalt;
- Recoverywert;
- Regelkonformität.

Ein schneller Run ist nicht automatisch die beste Demo. Demo-Sampling darf Qualität nutzen, muss aber Vielfalt erhalten.

## Datensatzformat

V1 verwendet pro Episode:

```text
episode_id/
  manifest.json
  transitions.jsonl
```

Jede Transition enthält volle aktuelle und nächste Observation. Das ist redundant, aber einfach zu auditieren. Eine spätere komprimierte Columnar-Version darf erst eingeführt werden, wenn Round-trip- und Migrationswerkzeuge existieren.

## Datenschutz

- keine echten Namen im Demonstratorfeld;
- pseudonyme Contributor-ID;
- keine Audio-/Videoaufnahme standardmäßig;
- keine Tastatureingaben außerhalb des Spiels;
- klare Einwilligung für veröffentlichte menschliche Daten;
- Löschbarkeit anhand Contributor-/Episode-ID.

## Proprietäre Inhalte

Trajektorien können abgeleitete strukturierte Zustände enthalten. Trotzdem werden keine Grafiken, Musik, MPQ-Inhalte, lokalisierte Texte oder vollständigen Spieldateien eingebettet. Vor öffentlicher Datensatzveröffentlichung ist eine eigene rechtliche Prüfung erforderlich; die Scaffold-Lizenz deckt das nicht automatisch ab.

## Demonstrationssammlung pro Milestone

Startziel—not Dogma:

| Task | erfolgreiche Demos | Failure/Recovery | Stile |
|---|---:|---:|---:|
| M1 single melee | 200 | 100 | 3+ |
| M2 room combat | 500 | 300 | 4+ |
| M3 exploration | 300 | 200 | 3+ |
| M4 loot | 1.000 Decisions | 500 | mehrere Builds |
| M5 town | 500 Loops | 200 | Budgetlagen |

Wichtiger als Menge ist Coverage. Coverageberichte zeigen Zustands-, ActionKind-, Gegner-, HP- und Seedverteilung.

## Datenvalidierung

Vor Training:

- Schema validieren;
- Hash prüfen;
- Schritte lückenlos;
- Candidate semantisch in Observation vorhanden;
- keine Episodegrenzen in Sequenzen;
- Contractversion kompatibel;
- Terminalflag konsistent;
- keine NaN/Inf;
- keine Testseeds;
- keine versteckten Observationfelder;
- ActionKind-Coverage reporten.

## Migration

Ein neuer Observationvertrag migriert alte Daten nur durch einen expliziten Konverter. Felder werden nicht still defaulted, wenn dies Semantik verändert. Originaldaten bleiben unverändert; Migration erzeugt neues Datasetmanifest und neue Hashes.
