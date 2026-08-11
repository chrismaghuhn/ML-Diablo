# 26 — Release-Checkliste

Diese Checkliste gilt für Source-ZIPs des Scaffolds. Sie ersetzt nicht die strengeren,
assetabhängigen Gates eines echten DevilutionX-Environment-Builds.

## Quellgrenze

- [ ] kein `third_party/DevilutionX/` im Archiv;
- [ ] keine MPQs, Saves, Screenshots, Audio-, Video- oder extrahierten Spieldateien;
- [ ] keine `.venv`, Buildverzeichnisse, Caches, Smoke-Artefakte oder Checkpoints;
- [ ] `LICENSE`, `NOTICE.md` und `upstream.lock.toml` vorhanden;
- [ ] Projektstatus nennt Bridge und Learner ausdrücklich unfertig.

## Automatische Gates

```bash
make check
python -m compileall -q src tests scripts
bash -n scripts/*.sh
python -m pip wheel --no-deps --no-build-isolation .
```

Erwartet:

- Python-Tests vollständig grün;
- fünf Schemas und Beispiele validiert;
- lokale Dokumentationslinks gültig;
- Assetscanner grün;
- C++20-Contract-Test grün;
- Wheel in frischer virtueller Umgebung installierbar;
- installierter `dxai smoke` erfolgreich.

## Archivprüfung

- [ ] Dateiinventar erzeugt und stichprobenartig geprüft;
- [ ] ZIP kann vollständig getestet werden;
- [ ] SHA-256 neben dem Archiv veröffentlicht;
- [ ] keine Symlinks oder absoluten Pfade;
- [ ] Dateirechte für Shellskripte erhalten;
- [ ] Archivname enthält Version.

## Echte Engine — zusätzlich erforderlich

Vor einem Build, der DevilutionX linkt:

- [ ] konkrete Upstream-Lizenz erneut prüfen;
- [ ] gepinnten Commit unverändert bauen und testen;
- [ ] Adapterdiff separat auditieren;
- [ ] Determinismus-, Hidden-State-, Legalitäts- und Reset-Gates bestehen;
- [ ] proprietäre Daten nur lokal bereitstellen;
- [ ] keine Behauptung kommerzieller Nutzbarkeit ableiten.

## Freigabeaussage

Ein Source-Release darf nur behaupten, ein **Forschungs- und
Integrationsscaffold** zu sein. Er ist weder eine fertige DevilutionX-Bridge noch ein
trainierter Diablo-Agent und belegt keine Full-Run-Leistung.
