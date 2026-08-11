# ADR 0001 — DevilutionX bleibt externe, gepinnte Abhängigkeit

- Status: Accepted
- Datum: 2026-08-11

## Kontext

DevilutionX ist ein eigenständiges großes C++-Projekt und steht im geprüften Upstream unter einer nicht-kommerziellen Sustainable Use License. Originale Diablo-Daten sind separat geschützt.

## Entscheidung

Dieses Repository vendort weder DevilutionX-Quellcode noch Assets. Ein lokaler Checkout wird über `upstream.lock.toml` auf einen geprüften Commit gepinnt. Adapteränderungen leben in einem separaten Fork/Patchzweig und werden mit Upstreamrevision und Lizenzhinweisen dokumentiert.

## Konsequenzen

- Das Scaffold kann unter Apache-2.0 stehen, ohne die Upstreambedingungen umzudefinieren.
- Builds sind zweistufig.
- Upgrades benötigen einen expliziten Kompatibilitätsreview.
- Keine Aussage über kommerzielle Nutzbarkeit des kombinierten Systems.
