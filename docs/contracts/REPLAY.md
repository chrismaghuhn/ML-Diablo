# Replayvertrag

## Sequenzen

Rekurrentes Training sampelt zusammenhängende Sequenzen, niemals isolierte zufällige Übergänge. Eine Sequenz darf keine Episodengrenze überschreiten.

Standardstart:

```text
sequence length = 80
burn-in         = 40
learning steps  = 40
overlap          = 40
n-step           = 5
```

Diese Werte stammen aus R2D3 als Startpunkt und müssen gesweept werden.

## Priorität

Priorität kombiniert Maximum und Mittelwert absoluter TD-Fehler plus Epsilon. Importance-Sampling-Gewichte werden protokolliert und Beta wird annealed.

## Zwei Puffer

- Agent replay: veränderlich, kapazitätsbegrenzt;
- Demonstration replay: separat, read-mostly, eigene Prioritäten.

Der Demoanteil wird pro Batchelement stochastisch gewählt. Tatsächliche Quellanteile werden geloggt.

## Recurrent State

v1 nutzt Burn-in mit initialem Nullzustand. Gespeicherte Actor-Hidden-States dürfen später getestet werden, müssen aber Policyversion und Staleness tragen.

## Keine Datenlecks

Replay-Splits folgen Episoden-/Seedgrenzen. Validation/Testtrajektorien gelangen nie in Training oder Prioritätsupdates.
