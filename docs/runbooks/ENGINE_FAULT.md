# Runbook — Engineprozessfehler

Fehlerklassen: startup, protocol, timeout, crash, invalid-state, determinism, asset, fixture.

1. Actor vom Scheduler isolieren.
2. letzte erfolgreiche request/episode/step ID sichern.
3. Prozess beenden; nicht im unbekannten State fortfahren.
4. Logs größenbegrenzt archivieren.
5. identischen Seed/Aktionsprefix in frischer Instanz reproduzieren.
6. wiederholbar → Bugfixture; nicht wiederholbar → Infrastruktur-/Nondeterminismusverdacht.
7. Training darf Faults nicht als negative Rewardtransitions lernen.
