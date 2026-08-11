# ADR 0009 — Trajektorien und Checkpoints sind versionierte immutable Artefakte

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Observation, Action, Transition, Episode Manifest, Task, Reward und Checkpoint besitzen unabhängige Versionskennungen. Geschriebene Rohtrajektorien werden nicht in-place verändert.

## Konsequenzen

- Migration erzeugt neue Dateien und Provenienz.
- Hashes sichern Bytes, nicht nur Dateinamen.
- Ein Checkpoint nennt alle relevanten Contract- und Upstreamversionen.
- Trainingscode lehnt unbekannte Majorversionen ab.
