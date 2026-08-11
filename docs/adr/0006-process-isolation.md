# ADR 0006 — Eine Engineinstanz pro Prozess mit versioniertem IPC

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

DevilutionX-Instanzen laufen pro Actor in separaten Prozessen. Python kommuniziert über ein lokales versioniertes Protokoll; kein ctypes-Zugriff auf globale Enginevariablen im Learnerprozess.

## Begründung

Prozessisolation begrenzt Crash-, Leak- und global-state Risiken und erlaubt reproduzierbare Neustarts.

## Konsequenzen

- Handshake mit Protocol-, Adapter- und Upstreamversion.
- Request IDs, Step IDs und Episode IDs verhindern stale Commands.
- Shared Memory darf später als Transportoptimierung dienen, ändert aber den logischen Vertrag nicht.
