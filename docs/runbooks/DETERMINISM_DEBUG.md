# Runbook — Determinismusabweichung debuggen

1. ersten unterschiedlichen Step per kanonischem Diff finden.
2. Observation, Candidates, Events und RNG-Counter getrennt vergleichen.
3. Build, Locale, Zeitzone, Threadcount und Assets fingerprinten.
4. Demo-/simulierte Zeit gegen echte Uhr prüfen.
5. nicht deterministische Iterationsreihenfolge/Pointerwerte/Hashmaps suchen.
6. RNG-Aufrufreihenfolge instrumentieren.
7. minimalen Fixtureseed reproduzieren.
8. Fix mit Regressionstest; Unterschied niemals nur aus Hashvergleich herausfiltern, ohne Semantik zu verstehen.
