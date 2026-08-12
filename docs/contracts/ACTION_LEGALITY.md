# Legalitäts- und Candidate-Vertrag

## Erzeugung

Die Engine erzeugt alle und nur die Aktionen, die an der aktuellen Entscheidungsgrenze akzeptiert werden können. Der Adapter sortiert sie deterministisch nach semantischem Schlüssel und vergibt danach IDs `0..N-1`.

## Gültigkeit

Eine `candidate_id` ist nur gültig für exakt:

```text
episode_id + step_id + observation/action contract version
```

Ein Candidate aus einem früheren Step ist stale, selbst wenn dieselbe ID erneut vorkommt.

## Atomarität

Ein Candidate repräsentiert eine einzelne semantische Spielerentscheidung, nicht zwingend einen Engineframe. Beispiele:

- `MOVE_TO_TILE(target)`;
- `ATTACK_ENTITY(target)`;
- `USE_BELT_SLOT(slot)`;
- `SELL_ITEM(inventory_slot)`.

## Anforderungen

- mindestens ein Candidate pro nicht fehlerhaftem Decision State;
- keine semantischen Duplikate;
- alle benötigten Parameter explizit;
- nicht zur ActionKind gehörende Payload-Felder zwingend `null`;
- Candidatefeatures endlich, begrenzt und ohne versteckte Information;
- Ausführung entweder erfolgreich oder als Contractfehler klassifiziert;
- ungültige IDs verändern den State nicht.

## Candidate Explosion

Bei großen Mengen wird nicht willkürlich abgeschnitten. Zulässige Verfahren:

1. sichere engine-seitige Dominanz-/Reachability-Prüfung;
2. hierarchische Entscheidung in getrennte atomare Grenzen;
3. dokumentiertes Top-k nur als experimentelle Variante mit Oracle-Coverage-Messung.

## M0.3 Candidate-Lifetime und Step-Grenze

Im ersten realen DevilutionX-Slice ist `MOVE_TO_TILE` die einzige exponierte
ActionKind. Die acht lokalen Nachbarn werden engine-seitig mit `CanStep`,
`PosOkPlayer` und der sichtbarkeitsgebundenen Adapterprojektion geprüft. Die
Probe akzeptiert von außen nur `candidate_id`; Koordinaten, Mausereignisse,
Monsterindizes und rohe Enginecommands sind keine API.

Die IDs sind nur für die ausgebende Entscheidung gültig. Vor `MakePlrPath`
regeneriert der Native-Adapter die vollständige geordnete Candidate-Liste und
vergleicht `candidate_id`, `kind`, Payload und Contractversionen kanonisch. Ein
anderer `episode_id + step_id`-Kontext, ein anderer Candidate-Hash oder ein
ungültiger Index wird vor der Mutation als stale/state-mismatch abgelehnt.

Der Step endet an der ersten folgenden kontrollierbaren Boundary, nicht
zwangsläufig am angeforderten Ziel. Für die kontrollierte Nachbar-Fixture wird
Zielerreichung separat behauptet und getestet; sie ist kein allgemeiner
Legalitätsvertrag.

## Strikte Payload-Matrix

Jede ActionKind besitzt einen geschlossenen Payload-Vertrag. `WAIT` und
`RETURN_TO_TOWN` tragen beispielsweise keine Ziel-/Slotparameter;
`CAST_SPELL_AT_ENTITY` trägt exakt `target_entity_id + spell_id`. Ein Feld wird nicht
ignoriert, nur weil es für den aktuellen Kind bedeutungslos wäre. Python, JSON Schema
und C++-Bridge prüfen denselben Grundsatz.

`features` ist ein optionaler, geordneter Auxiliary-Vektor mit höchstens 64 endlichen
Werten. Seine Semantik gehört zur versionierten Feature-Spezifikation. Der
Referenzencoder nutzt höchstens die ersten acht Werte, wendet `tanh` an und paddet auf
feste Länge; ein produktiver Adapter muss die Positionen zusätzlich dokumentieren.
