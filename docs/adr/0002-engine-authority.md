# ADR 0002 — DevilutionX ist alleinige Regelinstanz

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Legalität, RNG, Bewegung, Treffer, Schaden, Inventar, Shops, Levelübergänge, Tod und Erfolg werden ausschließlich aus dem Enginezustand abgeleitet. Python oder das ML-Modell duplizieren keine Spielregeln.

## Begründung

Regelduplikation erzeugt unvermeidlich Drift und ermöglicht Aktionen, die im echten Spiel nicht gelten. Ein Agent würde dann den Wrapper statt Diablo lernen.

## Konsequenzen

- Die Engine erzeugt die vollständige Liste legaler Candidates.
- Invalid Actions sind Contractfehler, keine normale Trainingsaktion.
- Rewardkomponenten beruhen auf autoritativen Zustands-/Eventdeltas.
- Classical planning darf bekannte Geometrie verwenden, aber keine Regeln erfinden.
