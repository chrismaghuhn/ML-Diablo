# ADR 0008 — Feste Skills vor einem gelernten Manager

- Status: Accepted
- Datum: 2026-08-11

## Entscheidung

Combat, Navigation, Loot/Inventory und Town werden zuerst als isolierbare Skills mit expliziten Start-/Endverträgen gebaut. Ein Manager lernt erst später ihre Auswahl.

## Begründung

Ein Full Run hat einen extrem langen, heterogenen Horizont. Die NetHack-Literatur und starke symbolische Baselines sprechen gegen eine sofortige flache Primitive-Policy.

## Konsequenzen

- Skills besitzen eigene Tasks, Daten und Gates.
- Der Manager wird als SMDP behandelt.
- End-to-End-Feintuning bleibt eine spätere Ablation.
