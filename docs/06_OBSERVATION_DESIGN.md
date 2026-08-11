# 06 — Observation Design

## Grundsatz

Die Observation entspricht dem, was ein regelkonform spielender Agent zum Entscheidungszeitpunkt wissen darf—nicht allem, was im Engine-Speicher steht.

## V1-Inhalte

### Spielerzustand

- Position in Levelkoordinaten;
- aktuelle/maximale HP und Mana;
- Klasse, Charakterlevel, Erfahrung;
- Dungeon-Level;
- Gold und grobe Ressourcen;
- aktuell bekannte Status-/Resistenz-/Ausrüstungsmerkmale als versionierte Attribute;
- Inventar, Belt, Equipment und bekannte Spells, sobald der jeweilige Milestone sie einführt.

### Räumlicher Zustand

Ein lokales oder bekanntes Tile-Raster:

- relative Position zum Spieler;
- Terrain-ID nur, wenn erkundet;
- sichtbar vs. nur erinnert;
- bekannte Walkability;
- sichtbare aktuelle Occupancy;
- beobachtbare Gefahrenmerkmale.

Unbekannte Tiles verwenden `terrain_id=-1`, `walkable=false`, `occupied=false`.

### Entities

Nur aktuell sichtbare beziehungsweise anderweitig regelkonform bekannte Entities:

- episode-lokale stabile Entity-ID;
- Typfamilie;
- Position;
- beobachtbare HP, falls UI/Regel dies tatsächlich verrät;
- Hostility;
- sichtbare Statusmerkmale.

Eine Engine-ID darf intern wiederverwendet werden; der Adapter muss verhindern, dass dieselbe öffentliche ID in einer Episode zwei semantisch verschiedene Entities bezeichnet.

### Ereignisse

Ein begrenztes Fenster player-observabler Ereignisse, etwa:

- Schaden erhalten/verursacht;
- Item sichtbar aufgenommen;
- Tür geöffnet;
- Levelübergang;
- Spell fehlgeschlagen;
- beobachtbarer Gegner gestorben.

Events dürfen keine unsichtbaren Koordinaten oder internen KI-Modi verraten.

### Legale Kandidaten

Die Kandidatenliste ist Teil der Observation. Dies ist kein Leak, sondern eine explizite Engine-Schnittstelle, ähnlich einem Action Mask. Sie sagt nicht, welche Aktion gut ist, nur welche aktuell ausführbar ist.

## Was nicht exportiert wird

- komplette, noch nicht erkundete Dungeonkarte;
- unsichtbare Monster und Items;
- exakte zukünftige RNG-Zustände oder Dropentscheidungen;
- interne Monsterziele, Pfade oder Cooldownzustände, sofern nicht beobachtbar;
- nicht identifizierte Itemwerte;
- versteckte Questflags ohne sichtbare Konsequenz;
- Engine-„best action“-Heuristiken;
- zukünftige Store-Inventare;
- Privilegien aus Debug- oder Testmodus.

## Gedächtnis

V1 exportiert sichtbare und erkundete lokale Informationen, aber keine perfekte globale Strategiekarte. Gedächtnis entsteht auf zwei Ebenen:

1. **Rekurrenter Kern:** kurzfristiger Verlauf, Gegnerbewegung, Aktionen, Rewards.
2. **Explizites Agent-Memory:** später eine gelernte oder deterministische Karte aus vergangenen Beobachtungen.

Die Engine darf eine bereits erkundete Automap-Information exportieren, wenn sie auch dem Spieler dauerhaft zugänglich ist. Der Vertrag muss genau definieren, was „erkundet“ bedeutet.

## Koordinaten

- Entity- und Spielerpositionen: absolute Level-Tiles, damit persistentes Mapping möglich ist.
- Tile-Patch: relative Koordinaten zum Spieler, damit lokale Encoder translationstolerant bleiben.
- Richtungen und Projektilzustände: explizite diskrete/normalisierte Felder, nicht aus Spriteframes abgeleitet.

## ID- und Typstabilität

IDs und Enums werden nicht aus übersetzten Anzeigenamen gebildet. Typen stammen aus stabilen Engine-Identifiern oder einer projektspezifischen Mappingtabelle. Ein Upstream-Upgrade, das IDs verändert, benötigt eine Contract-Kompatibilitätsprüfung.

## Skalierung und Normalisierung

Rohe Integer bleiben im Artefakt. Normalisierung geschieht im Feature-/Modellcode und ist checkpointversioniert. Dadurch kann ein Datensatz mit einem neuen Encoder erneut verwendet werden.

Beispiele:

- HP als raw `hp`, `hp_max`; Modell nutzt Quotient.
- Gold raw; Modell nutzt `log1p`.
- Position raw; Gridencoder oder relative Projektion entscheidet später.

## Variable Mengen

Entities, Inventory und Kandidaten sind variable Mengen. Keine harte Beschränkung darf still Entities abschneiden. Wenn ein Modell eine Obergrenze benötigt:

- Auswahlregel versionieren;
- abgeschnittene Anzahl loggen;
- niemals strategisch relevante Ziele unbemerkt verlieren;
- Set-/Attention-/Graphencoder bevorzugen.

## Observability-Audit

Für jeden Observation-Field existiert eine Tabelle:

| Feld | Enginequelle | Spieler kann es wissen? | Sichtbarkeitsfilter | Test |
|---|---|---:|---|---|
| Monsterposition | Monstercontainer | nur sichtbar | Vision/Lighting | hidden-monster fixture |
| Itemaffixe | Itemstruktur | nur identifiziert | identification flag | unidentified-item fixture |
| Terrain | Dungeonarray | sichtbar/erkundet | automap policy | unknown-tile fixture |
| Storepreis | Storestate | im Store | modal context | store closed fixture |

Neue Felder benötigen diesen Audit vor Merge.

## Referenzencoder im Scaffold

`src/dxai/models/features.py` enthält bewusst nur einen kleinen Referenzencoder. Er beweist Dimensionen und Candidate-Scoring, ist aber nicht die empfohlene finale Repräsentation. Das Produktionsmodell soll Grid-, Entity-, Inventory- und Eventencoder getrennt behandeln.
