# 09 — Reward Design

## Leitprinzip

Reward ist ein Taskvertrag, kein Ersatz für fehlende Architektur. Dichte Signale dürfen Lernen beschleunigen, aber sie müssen:

- aus player-observablen oder taskdefinierten Ereignissen ableitbar sein;
- einzeln geloggt werden;
- versioniert und ablierbar sein;
- nicht die Engine-Wahrheit überschreiben;
- nachweislich mit echter Taskleistung korrelieren.

## Drei Ebenen

### 1. Terminal Reward

Beispiel M1:

- `+1.0` Zielgegner besiegt und Spieler lebt;
- `-1.0` Spieler stirbt;
- `0.0` bei Zeitlimit, zusätzlich Diagnose.

Terminal Reward bleibt die primäre Lern- und Evaluationsdefinition.

### 2. Potential-basiertes oder lokales Shaping

Mögliche Komponenten:

- beobachtbarer Schaden am Ziel;
- negativer eigener Schaden;
- geringe Entscheidungskosten;
- Exploration neuer Tiles;
- sinnvolle Ressourcenereignisse.

Solche Komponenten sind für frühe Slices erlaubt, aber nicht automatisch für den Full Run. Ein Combat-Agent kann sonst „Schaden farmen“, statt sicher zu gewinnen.

### 3. Diagnosemetriken ohne Reward

Viele wichtige Größen sollten nur gemessen werden:

- Overkill;
- verschwendete Tränke;
- unnötige Stadtfahrten;
- Backtracking;
- Inventarwert;
- Zeit in Gefahr;
- Zahl abgebrochener Pfade;
- illegal action attempts;
- Skillwechsel.

Nicht jede Metrik gehört in die Optimierungsfunktion.

## Reward-Beispiel für M1

```text
r_t =
  -0.001 pro Entscheidung
  +0.02  pro beobachtbarem Schadenspunkt am Ziel
  -0.02  pro eigenem Schadenspunkt
  +1.0   bei Erfolg
  -1.0   bei Tod
```

Der Mock enthält zusätzlich winzige Exploration-/Pickup-Komponenten, um Datenpfade zu testen. Diese sind keine behaupteten finalen Diablo-Hyperparameter.

## Full-Run Reward

Für den späteren Run sollte die Hierarchie unterschiedliche Zeitskalen nutzen:

- Skill-Level: lokale Taskrewards;
- Manager-Level: Floorfortschritt, Überleben, Ressourcenlage und langfristiger Runerfolg;
- globale Evaluation: Diablo-Killrate und Runqualität.

Lokale Rewards dürfen den Manager nicht dazu bringen, endlos leichte Gegner zu farmen. Fortschritts- und Zeitbudgets müssen explizit sein.

## Truncation und Bootstrap

Bei natürlichem Tod/Erfolg wird nicht gebootstrapped. Bei einem reinen Zeitlimit kann Value-Bootstrap korrekt sein, sofern der Zustand nicht als echter MDP-Terminal gilt. Der Datensatz speichert `terminated` und `truncated` getrennt.

## Reward Hacking Tests

Für jede neue Komponente:

1. adversarial scenario bauen;
2. prüfen, ob die Komponente ohne Taskfortschritt maximierbar ist;
3. Scriptbot mit absichtlich schlechtem Verhalten evaluieren;
4. Rewardkomponenten und Erfolg scatterplotten;
5. Agentvideos/Trajektorien der höchsten Returns auditieren;
6. Komponente ablatieren.

Beispiele:

- Schadenreward → heilt/regeneriert der Gegner und erlaubt Farming?
- Explorationreward → rotiert Agent durch harmlose Karte und ignoriert Ziel?
- Lootreward → nimmt wertlosen Müll auf und wirft ihn wieder ab?
- Goldreward → vermeidet notwendige Käufe?

## Reward-Versionierung

`combat.reward.v1` ist Teil von Task, Trajektorie und Checkpoint. Änderungen an Gewicht oder Semantik erzeugen `v2`; alte Runs werden nicht still unter neuer Definition verglichen.

## Evaluation ohne Shaping

Die Rangfolge von Checkpoints basiert auf externen Taskmetriken, nicht auf dem trainierten Return allein. Ein Modell mit höherem shaped Return, aber niedrigerer Killrate, ist schlechter.
