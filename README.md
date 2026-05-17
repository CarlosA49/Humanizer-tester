# Humanizer-tester

An **AI Humanizer**: it rewrites machine-sounding text into a chosen human
**tone** while measuring and improving the three signals AI-text detectors
care about most — **perplexity**, **burstiness**, and **lexical diversity**.

Pure Python, **standard library only** (no models, no network, no installs).

## What it does

| Signal | What it means | What the humanizer does |
|---|---|---|
| **Perplexity** | How (un)predictable the word choices are. Machine text is *low* (smooth, expected). | Swaps bland words for varied, tone-flavoured vocabulary -> raises perplexity. |
| **Burstiness** | How much sentence length varies. Humans write long-then-short; machines are uniform. | Splits run-ons, merges short lines, drops in punchy fragments. |
| **Lexical** | Vocabulary richness (type/token, MATTR). | Tone dictionaries + variety-aware substitution avoid repetition. |

It runs its **own pipeline rules** (ordered, configurable) and ships large
**per-tone dictionaries** (~235–250 synonyms each, plus sentence starters,
interjections, connectors and fragments) that paraphrase the text or add
phrasing drawn from the active tone.

## Tones

`academic`, `casual`, `confident`, `empathetic`, `friendly`, `persuasive`,
`professional`, `storytelling`, `witty`.

```
python3 -m humanizer --list-tones
```

## Pipeline rules

Run in order; each rule is independent and swappable:

1. `strip_ai_tells` — removes giveaways ("it is important to note that",
   "in conclusion", "delve into", …).
2. `lexical_substitution` — tone-aware, variety-preserving paraphrasing
   (single words **and** phrases).
3. `adjust_contractions` — contract / expand to match the tone's register.
4. `vary_sentence_length` — split, merge, fragment → burstiness.
5. `inject_discourse_markers` — tone starters & asides → human texture.

A final pass repairs `a`/`an` after substitutions.

## CLI

```bash
# Inline text
python3 -m humanizer --tone casual --strength 0.8 "It is important to note that AI is very good."

# From a file, with before/after metrics + change log
python3 -m humanizer --tone academic --strength 0.7 --file examples/sample.txt --metrics --changes

# From stdin
echo "We should use it because it is important." | python3 -m humanizer --tone persuasive

# Reproducible output
python3 -m humanizer --tone witty --seed 42 "..."
```

Options: `--tone/-t`, `--strength/-s` (0.0–1.0), `--seed`, `--file/-f`,
`--metrics`, `--changes`, `--list-tones`.

## Library

```python
from humanizer import Humanizer

h = Humanizer(tone="professional", strength=0.6, seed=7)
r = h.humanize("It is important to note that this is a very good idea.")

print(r.text)        # rewritten text
print(r.summary())   # perplexity / burstiness / lexical before -> after
print(r.changes)     # list of every edit made
```

Custom pipeline (subset / reordered rules):

```python
from humanizer import Humanizer, Pipeline

h = Humanizer(tone="academic", pipeline=Pipeline(rules=["strip_ai_tells",
                                                        "lexical_substitution"]))
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Layout

```
humanizer/
  lexicon.py    embedded frequency table -> perplexity proxy
  metrics.py    perplexity / burstiness / lexical (TTR, MATTR)
  tones.py      tone definitions + large dictionaries
  pipeline.py   the rule engine + the 5 rules
  core.py       Humanizer API + before/after metrics
  cli.py        command-line interface
tests/          unittest suite
examples/       sample input
```

> Note: this nudges text toward human-typical statistics; it is a writing
> aid, not a guarantee against any specific detector.
