# Runbook — Hidden-State-Leak

Ein Leak ist ein Datenintegritätsvorfall.

1. Training/Evaluation mit betroffener Contractversion stoppen.
2. betroffene Felder und Versionen identifizieren.
3. Daten-/Checkpointreichweite bestimmen.
4. Artefakte als tainted markieren; nicht still überschreiben.
5. Observationcontract korrigieren und Major/Minorentscheidung dokumentieren.
6. metamorphischen Leaktest hinzufügen.
7. betroffene Ergebnisse zurückziehen und neu trainieren/evaluieren.
8. Incidentbericht mit Ursache und Prävention.
