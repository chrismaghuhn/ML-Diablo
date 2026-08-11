# 07 — Action Design

## Warum Kandidaten statt festem Aktionsindex

Diablo-Aktionen sind parametriert:

```text
MOVE_TO_TILE(x, y)
ATTACK_ENTITY(entity_id)
CAST_SPELL_AT_ENTITY(spell_id, entity_id)
USE_BELT_SLOT(slot)
BUY_ITEM(store_item_id)
```

Ein riesiger globaler Aktionsvektor wäre überwiegend illegal, würde IDs schlecht generalisieren lassen und bei neuen Entities seine Bedeutung ändern. Daher erzeugt die Engine pro Observation eine variable Liste legaler **Action Candidates**.

Der Agent berechnet:

```text
Q(observation, candidate_i)
```

für jeden Kandidaten und wählt den besten legalen Eintrag.

## Kandidatenidentität

`candidate_id`:

- dicht von `0..N-1`;
- deterministisch nach semantischem Schlüssel sortiert;
- nur für eine Observation gültig;
- nicht über Steps gespeichert oder vorhergesagt.

Trajektorien speichern zusätzlich Art und Parameter. Dadurch bleibt ein Label verständlich, auch wenn Kandidaten anders nummeriert werden.

## V1-Aktionsfamilien

### M0/M1

- `WAIT`
- `MOVE_TO_TILE`
- `ATTACK_ENTITY`
- `PICK_UP_ITEM`
- `USE_BELT_SLOT`

### Spätere Combat-Slices

- `CAST_SPELL_AT_ENTITY`
- `CAST_SPELL_AT_TILE`
- Wechsel/Equip relevanter Items
- kontrollierter Retreat über Movementkandidaten

### Loot/Inventory

- `EQUIP_ITEM`
- `UNEQUIP_ITEM`
- `DROP_ITEM`

### Stadt

- `BUY_ITEM`
- `SELL_ITEM`
- `REPAIR_ITEM`
- `ALLOCATE_STAT`
- `RETURN_TO_TOWN`

### Exploration

- `OPERATE_OBJECT`
- `TAKE_STAIRS`

## Movement-Abstraktion

Drei Varianten sind denkbar:

1. **Primitive Nachbartiles:** maximale Kontrolle, sehr langer Horizont.
2. **Beliebiges sichtbares/erkanntes Zieltile:** kürzerer Horizont, klassischer Pfadcontroller.
3. **High-level Orte/Frontiers:** sehr kurz, aber stärker handgebaut.

Empfehlung:

- M1 nutzt Nachbartiles, um Combatpositionierung sauber zu testen.
- Exploration verwendet später `MOVE_TO_TILE` zu pfadbaren Frontiers mit definierten Interrupts.
- Der öffentliche ActionKind bleibt gleich; `movement_policy_version` beschreibt Reichweite und Ausführung.

## Makroaktionen und Skills

Ein Skill ist nicht einfach ein besonders großer Candidate. Skills besitzen eigene interne Policy, Termination und Observation. Der Manager wählt zum Beispiel:

```text
FIGHT(target_cluster)
EXPLORE(frontier)
LOOT(item)
RETREAT(safe_region)
TOWN(objective)
```

Der Skill erzeugt mehrere Environment-Steps. Replay muss Manager- und Skill-Level klar trennen. V1 lernt zunächst auf Primitivebene pro Task; Integration startet mit festen Skill-Routern.

## Legalität und Race Conditions

Zwischen Erzeugung und Ausführung darf kein autonomer Engine-Tick den Kandidaten veralten lassen. Step-Requests enthalten daher `episode_id` und `expected_step_id`. Eine alte ID wird hart abgelehnt.

## Candidate Features

Der Engine-Vertrag enthält semantische Parameter; modellnahe Features werden bevorzugt im Python-Encoder berechnet. Einige günstige, nicht privilegierte Features dürfen beigefügt werden, etwa:

- relative Richtung/Distanz;
- ob Ziel im Nahkampfbereich ist;
- bekannte Ressourcenanforderung;
- Slottyp;
- sichtbare Ziel-HP-Fraktion.

Kein Feature darf den zukünftigen Outcome der Aktion oder versteckte
Engine-Bewertungen enthalten. Der v1-Vertrag begrenzt den Vektor auf 64 endliche
Werte. Der ausführbare Referenzencoder liest acht Auxiliary-Positionen, begrenzt sie
mit `tanh` und paddet deterministisch; ihre Bedeutung muss mit der Feature-Version
festgeschrieben werden.

Payload-Felder sind strikt kindgebunden. Zusätzliche, scheinbar harmlose Felder werden
als Contractfehler abgelehnt, damit Replaydaten keine mehrdeutige Semantik bekommen.

## Action Masking

Da ausschließlich legale Candidates übermittelt werden, ist die Liste selbst die Maske. Beim Batching werden Kandidaten gepaddet; `candidate_mask=false` markiert Padding. Das Modell setzt deren Q-Werte auf den kleinstmöglichen Wert.

## Ordnung und Permutationsrobustheit

Die Engine sortiert für Reproduzierbarkeit. Das Modell darf Kandidaten trotzdem nicht aufgrund ihrer Listenposition bewerten. Der Candidate-Scorer teilt Gewichte über alle Kandidaten. Ein Test permutiert die Reihenfolge und prüft, dass semantische Q-Werte entsprechend permutieren.

## Sicherheitsgrenzen

- maximale Kandidatenzahl pro Context mit explizitem Overflowfehler;
- keine beliebigen Console-/Debugcommands;
- keine Dateipfade oder Strings aus dem Modell;
- IDs und Slots range-checken;
- modale ActionKinds nur im passenden Context;
- `WAIT` als Fallback nur, wenn es regelkonform und nicht terminalproblematisch ist.
