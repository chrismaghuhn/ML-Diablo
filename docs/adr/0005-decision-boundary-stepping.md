# ADR 0005 — Ein Environment-Step endet an einer semantischen Entscheidungsgrenze

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

`Step(candidate)` injiziert genau eine semantische Entscheidung und lässt die Engine null bis viele interne Ticks laufen, bis erneut eine Entscheidung des kontrollierten Spielers nötig ist oder ein Terminal-/Timeoutzustand eintritt.

## Begründung

Renderframes sind kein stabiler Entscheidungsraum. Angriffe, Bewegung und Interaktionen dauern unterschiedlich lang.

## Konsequenzen

- `engine_tick` und `step_id` sind getrennt.
- Macro-/Skill-Aktionen benötigen später Dauerinformationen und SMDP-Discounting.
- Timeouts müssen klassifiziert werden.
