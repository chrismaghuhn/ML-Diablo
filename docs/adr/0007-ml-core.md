# ADR 0007 — BC → Candidate-R2D2/R2D3 ist der primäre ML-Pfad

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Der erste lernende Pfad ist recurrent Behavior Cloning, gefolgt von rekurrentem Off-Policy Double-Q-Learning mit priorisiertem Sequenz-Replay. Demonstrationen werden im R2D3-Stil weiter beigemischt.

## Begründung

- Rekurrenz: partielle Beobachtbarkeit.
- Replay: teure Engineerfahrung mehrfach nutzen.
- Demonstrationen: harte Exploration und frühe Kompetenz.
- Q-Lernen: Demonstrator kann übertroffen werden.

## Pflichtablationen

Scripts, BC, recurrent PPO, R2D2 ohne Demos und R2D3.

## Konsequenzen

Dies ist eine überprüfbare Hypothese, kein Dogma. Ein Pivot erfolgt anhand von Engine-Schritten, Testleistung und Stabilität.
