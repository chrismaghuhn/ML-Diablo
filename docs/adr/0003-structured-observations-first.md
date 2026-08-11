# ADR 0003 — Strukturierte, spielerbeobachtbare Observation zuerst

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Die erste Agentenversion erhält einen strukturierten State, der ausschließlich Informationen enthält, die ein regelkonformer Spieler aktuell sehen oder bereits erinnern könnte. Pixels sind eine spätere Ablation beziehungsweise Auxiliary Modalität.

## Begründung

Die Forschungsfrage ist zunächst sequenzielle Entscheidung, nicht OCR/Spriteerkennung. Strukturierter State senkt Samplebedarf und macht Hidden-State-Leaks testbar.

## Grenzen

Nicht erlaubt: komplette Dungeonkarte, unsichtbare Monster/Items, zukünftige Shoprolls, interne Monsterziele, zukünftiger RNG, exakte unbekannte Itemwerte.

## Konsequenzen

Ein Pixel-only-Ergebnis darf später ergänzt werden, ersetzt aber nicht die strukturierte Baseline.
