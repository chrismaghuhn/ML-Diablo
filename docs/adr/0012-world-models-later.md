# ADR 0012 — World Models und Search sind spätere Forschungszweige

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Dreamer-, MuZero- oder learned-dynamics Planung wird erst begonnen, wenn ein echter Engine-Slice, starke model-free Baselines und Modellfehler-Metriken existieren.

## Begründung

Seltene irreversible Ereignisse, dynamische Candidates und lange Semantik machen falsche Dynamics besonders gefährlich. Ohne reale Baseline ist nicht erkennbar, ob das Modell echte Planung oder Modellartefakte ausnutzt.

## Konsequenzen

World Models starten lokal, etwa für kurze Combat-Rollouts. Jede imaginierte Verbesserung muss in realen Engine-Rollouts bestätigt werden.
