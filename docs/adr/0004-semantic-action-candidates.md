# ADR 0004 — Dynamische semantische Aktionskandidaten

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Jede Observation trägt eine dichte, deterministisch sortierte Liste legaler semantischer Candidates. Das Modell bewertet `Q(history, candidate)` beziehungsweise `π(candidate | history)`.

## Beispiele

`MOVE_TO_TILE(12,7)`, `ATTACK_ENTITY(1042)`, `USE_BELT_SLOT(3)`, `SELL_ITEM(slot=8)`.

## Nicht gewählt

- Bildschirmkoordinaten und Klicks;
- ein riesiger globaler diskreter Index über alle Ziele;
- ein Policyoutput, der ungültige Kombinationen selbst zusammensetzen muss.

## Konsequenzen

`candidate_id` ist observation-lokal. Trajektorien speichern zusätzlich den semantischen Payload. Candidate-Reihenfolge muss deterministisch sein.
