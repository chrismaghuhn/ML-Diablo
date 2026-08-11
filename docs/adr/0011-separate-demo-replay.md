# ADR 0011 — Demonstrations- und Agent-Replay bleiben getrennt

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Demonstrationssequenzen und Agentensequenzen werden in unabhängigen priorisierten Puffern gehalten. Der Demoanteil wird pro Batchelement stochastisch gewählt und gesweept.

## Begründung

Getrennte Puffer erlauben unabhängige Prioritäten, Schutz vor Verdrängung und sehr kleine Mischraten.

## Konsequenzen

Startwert `1/128`; Pflichtsweep von `0` bis mindestens `1/16`. Demoqualität und Provenienz werden gespeichert.
