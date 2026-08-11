# 11 — Modellarchitektur

## Zielarchitektur

```text
Observation
 ├─ player scalars ─────────────── MLP ───────────────┐
 ├─ local/known tile grid ─────── CNN/ResNet ─────────┤
 ├─ visible entities ───── Set/Attention/GNN encoder ─┤
 ├─ inventory/equipment ── Set/slot encoder ──────────┤
 ├─ recent events ───────── embedding + pooling ──────┤
 ├─ previous action/reward ─ embeddings ──────────────┤
 └─ task/skill id ───────── embeddings ───────────────┘
                                                       ↓
                                                   fusion MLP
                                                       ↓
                                                      LSTM
                                                       ↓ z_t
             each legal candidate → candidate encoder → c_i
                                                       ↓
                                           shared dueling scorer
                                                       ↓
                                             Q(z_t, candidate_i)
```

## Encodertrennung

### Player Encoder

Rohwerte werden nicht einfach unnormalisiert zusammengeworfen. Empfohlen:

- Quotienten für HP/Mana;
- `log1p` für Gold/XP;
- Embeddings für Klasse, Dungeon-Level, aktive Skill-ID;
- separate Masken für nicht vorhandene Werte;
- keine Daten-normalisierung, die Teststatistik benötigt.

### Grid Encoder

V1 kann einen egozentrischen bekannten Tile-Patch mit Kanälen verwenden:

```text
known
visible
walkable
wall/terrain category
occupied self/monster/item/object
hazard
remembered frontier
```

Ein kleiner ResNet oder ConvNet reicht zunächst. Absolute Spielerkoordinaten und Dungeon-Level werden separat gegeben, damit globale Karte/Backtracking möglich bleibt.

### Entity Encoder

Entityvektoren enthalten Typembedding, relative Position, sichtbare HP/Status und Hostility. Ein permutation-invarianter Set Transformer oder Attentionpool ist flexibler als eine feste Sortierung/Top-K-Kürzung. Für M1 reicht ein kleiner MLP plus Pooling; die Schnittstelle soll später Attention erlauben.

### Inventory Encoder

Inventar ist nicht nur eine Liste von Stats. Wichtige Aspekte:

- Itemtyp und identifizierter Wissensstand;
- Slot/Größe;
- ausgerüstet vs. getragen;
- Haltbarkeit/Charges;
- bekannte Affixe;
- Vergleich zum aktuellen Build;
- Verkaufswert und Opportunitätskosten.

Start: Setencoder plus separate Equipment-Slots. Später kann ein Item-Value-Head auxiliary trainiert werden.

### Event Encoder

Events erhalten stabile IDs und numerische Payloads statt freier Sprache. Ein kurzer Event-Transformer oder GRU ist möglich; für frühe Tasks genügt Embedding + Pooling. Lokalisierte UI-Texte gehören nicht in das Kernmodell.

## Recurrent Core

Ein LSTM ist der robuste Startpunkt. Transformer Memory ist später prüfbar, aber nicht nötig, bevor LSTM-Grenzen gemessen werden.

Replaysequenz:

```text
40 Burn-in Steps → hidden state rekonstruieren
40 Learning Steps → TD/BC Loss
```

Längeres Gedächtnis kann durch längere Sequenzen oder explizite Map Memory ergänzt werden. Eine LSTM-Sequenz von 80 Decisions löst nicht automatisch mehrstöckige Runerinnerung.

## Candidate Encoder

Candidate Features kombinieren:

- ActionKind-Embedding;
- Zielentity-Embedding oder Zielposition;
- relative Richtung/Distanz;
- Spell-/Slot-/Store-/Statparameter;
- relevante sichtbare Zielmerkmale;
- aktuelle Skill-/Modal-ID.

Das Modell darf keine Candidate-Position als semantisches Feature nutzen.

## Dueling Candidate-Q

Für jeden Candidate:

```text
A_i = AdvantageMLP([z_t, c_i])
V   = ValueMLP(z_t)
Q_i = V + A_i - mean_legal(A)
```

Das Scaffold implementiert diese Form in `src/dxai/models/candidate_q.py` und maskiert Paddingkandidaten.

## Multi-Head-Ausgaben

Später sinnvoll:

- Q/Policy Head;
- State Value;
- Behavior-Cloning-Logits;
- nächste Event-/Rewardvorhersage;
- HP-/Death-Risk-Head;
- Skill-Termination;
- Map/Frontier-Auxiliary;
- Item-Outcome-Value.

Auxiliary Heads müssen einen messbaren Nutzen zeigen. Mehr Heads ohne Ablation sind kein Fortschritt.

## Shared vs. Skill-spezifisch

Empfehlung:

- gemeinsamer Basisencoder für Spieler, Grid, Entities;
- skill-spezifischer recurrent core oder Adapter zunächst;
- eigene Candidate-/Value-Heads pro Skill;
- später gemeinsamer LSTM mit Skill-Embedding testen.

Vollständiges Weight Sharing kann negative Interferenz erzeugen; vollständig getrennte Modelle verschenken Transfer. Beide Varianten werden gegen eine Hybridarchitektur evaluiert.

## Manager-Modell

Der Manager sieht gröbere Features:

- Ressourcen und HP;
- Dungeon-/Runfortschritt;
- bekannte Frontiers;
- sichtbare Bedrohungszusammenfassung;
- Inventar-/Townneed;
- letzter Skill, Dauer, Ergebnis;
- langfristige Memoryzusammenfassung.

Actions sind Options, nicht primitive Candidates. Ein kleiner recurrent Q- oder actor-critic Head genügt zunächst.

## Risiko

Diablo hat asymmetrische Kosten: Ein riskanter Zug kann einen langen Run vernichten. Erwartungswert allein kann zu hoher Varianz führen. Spätere Optionen:

- distributional Q (Quantile Regression);
- Death-Risk Auxiliary;
- constrained action filtering in kritischen HP-Bereichen;
- CVaR-artige Evaluation;
- Managerobjective mit Run-Survival.

Nicht vor M6 hinzufügen, sofern M1–M3 keinen klaren Bedarf zeigen.

## Modellgrößen

Start bewusst klein:

- 1–5 Mio. Parameter pro Skill;
- LSTM 128 oder 256;
- Gridencoder 2–4 Convblöcke;
- Entityattention 2 Layer;
- Candidate MLP 2 Layer.

Der Enginedurchsatz, nicht GPU-FLOPs, dürfte früh limitieren. Ein größeres Modell ist kein Ersatz für bessere Taskdaten.

## Referenzimplementation im Scaffold

`FeatureSpec` und `CandidateQNetwork` sind ein ausführbarer Minimalpfad:

- fester kompakter Statevektor;
- ActionKind-One-Hot plus strikter Payload und acht gepaddete Auxiliary-Features;
- LSTM;
- shared Candidate Encoder;
- dueling Q;
- Paddingmaske.

Nicht enthalten sind der finale Grid-/Entity-/Inventoryencoder und ein kompletter Learner. Diese Trennung verhindert, dass ein Demo-Netz fälschlich als Produktionsarchitektur gilt.
