# Observability- und Hidden-State-Vertrag

## Grundsatz

Der Agent darf nur erhalten, was ein regelkonformer Spieler aktuell wahrnehmen oder aus eigener früherer Wahrnehmung erinnern könnte.

## Erlaubt in v1

- sichtbare Tiles und bekannte frühere Geometrie als `explored`;
- sichtbare Entitäten und öffentlich sichtbare Attribute;
- eigene HP, Mana, Stats, Ausrüstung, Inventar und Gold;
- aktuell verfügbare UI-/Interaktionsoptionen;
- vergangene öffentliche Events;
- legale Candidates, sofern ihre Existenz keine verborgene Information verrät.

## Nicht erlaubt

- unsichtbare Entitäten oder aktuelle Occupancy auf nicht sichtbaren Tiles;
- vollständige generierte Karte;
- interne Monsterziele, Pathfindingstate oder Aggrostatus, falls nicht sichtbar;
- unbekannte Itemaffixe oder exakte Werte vor Identifikation;
- zukünftige Händlerangebote, Lootdrops oder RNG;
- Quest-/Triggerzustand, den der Spieler nicht ableiten kann;
- Rewardbestandteile, die zukünftige Information enthalten.

## Known Map

Die Engine darf `explored=true` für früher gesehene Tiles liefern. Aktuelle Occupancy bleibt bei `visible=false` immer verborgen. Alternativ kann Memory vollständig im Agenten geführt werden; beide Varianten sind zu abladieren.

## Leak-Test

## M0.3 Candidate-Leak-Audit

Eine legale Engine-Aktion darf nur dann als Candidate erscheinen, wenn ihre
Existenz ebenfalls spielerbeobachtbar ist. Im M0.3-Nachbarslice werden deshalb
Ziel- und kardinale Corner-Tiles nur angeboten, wenn sie in `dxai.observation.v1`
sichtbar, erkundet, nicht solide und nicht belegt sind. Die Belegungsprojektion
prüft Spieler-, Monster-, Item- und Objektfelder; damit kann ein verstecktes
oder inaktives Entity keinen Candidate erzeugen oder unterdrücken. Der native
`CanStep`-/`PosOkPlayer`-Check bleibt die Legalitätsinstanz; der Python-Test
prüft nur, dass ein Candidate nicht durch ein nicht sichtbares Tile erklärt
werden kann.

Pathfinding-Future-State ist für die Boundary ausgeschlossen (`future == tile`),
weil er in v1 nicht beobachtbar ist. Bei einer späteren Erweiterung muss jede
weitere native Legality-Abhängigkeit entweder in die Observation aufgenommen
oder aus dem Candidate-Slice ausgeschlossen werden.

Für paarweise Enginezustände, die sich ausschließlich in verborgenem State unterscheiden, muss die exportierte Observation bytegleich sein. Solche Metamorphic Tests werden für Monster, Items, Karte, Türen, Shops und RNG gebaut.
