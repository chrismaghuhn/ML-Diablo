# ADR 0010 — Versiegelte Seedsets und Pflichtbaselines

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Train-, Validation- und Testseeds sind disjunkt. Hyperparameter und Curricula dürfen Testresultate nicht sehen. Releases werden gegen Scripts, Random, BC, recurrent PPO und R2D2 verglichen.

## Konsequenzen

- Mittelwert allein reicht nicht; Median, Streuung und Konfidenzintervalle werden berichtet.
- Videos sind qualitative Evidenz, keine Erfolgsmessung.
- Ein einzelner glücklicher Full Run ist kein bestandener Milestone.
