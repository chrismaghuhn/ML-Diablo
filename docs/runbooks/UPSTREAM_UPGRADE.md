# Runbook — Upstream-Upgrade

1. neuen Commit in temporärem Checkout prüfen;
2. Lizenzdiff und README-Legalabschnitt prüfen;
3. relevante Hooks (`headless_mode`, `game_loop`, demomode, commands) vergleichen;
4. unveränderten Upstream bauen/testen;
5. Adapter rebasen;
6. alle Contract-/Determinismus-/Leaktests ausführen;
7. Trajektoriendiffs klassifizieren;
8. ADR/Contractversion bei semantischer Änderung;
9. erst danach `upstream.lock.toml` aktualisieren.
