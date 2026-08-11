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

Für paarweise Enginezustände, die sich ausschließlich in verborgenem State unterscheiden, muss die exportierte Observation bytegleich sein. Solche Metamorphic Tests werden für Monster, Items, Karte, Türen, Shops und RNG gebaut.
