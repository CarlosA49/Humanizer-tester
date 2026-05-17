# Humanizer-tester

An **AI Humanizer**: it rewrites machine-sounding text into a chosen human
**tone** while measuring and improving the three signals AI-text detectors
care about most — **perplexity**, **burstiness**, and **lexical diversity**.

Pure Python, **standard library only** (no models, no network, no installs).

### Try it in your browser

**▶ https://carlosa49.github.io/Humanizer-tester/**

A full web app that runs the humanizer **entirely in your browser** (Python
via Pyodide/WASM) — no server, nothing uploaded. First visit downloads a
~6 MB runtime, then it's instant. Source for the app lives in [`docs/`](docs/)
and is deployed by [`.github/workflows/pages.yml`](.github/workflows/pages.yml).

> One-time repo setting to publish it: **Settings → Pages → Build and
> deployment → Source = "GitHub Actions"**. The workflow then deploys on
> every push and prints the live URL in its run summary.

## What it does

| Signal | What it means | What the humanizer does |
|---|---|---|
| **Perplexity** | How (un)predictable word choices are. Machine text is *low* (smooth, expected). | Swaps bland words for varied, tone-flavoured vocabulary; a backoff **bigram** model scores it. |
| **Burstiness** | How much sentence length varies. Humans write long-then-short; machines are uniform. | Splits run-ons, merges short lines, drops in punchy fragments; measured vs a human target. |
| **Lexical** | Vocabulary richness (TTR, MATTR, **MTLD**). | Large tone dictionaries + variety-aware substitution avoid repetition. |

Everything is rolled into a single **humanity score** (0–100), reported
before vs. after.

It runs its **own pipeline rules** (ordered, configurable, per-tone) and
ships large **per-tone dictionaries** (hundreds of synonyms each — run
`--list-tones` for live counts — plus sentence starters, interjections,
connectors, fragments and multi-word phrase banks) that paraphrase the text
or add phrasing drawn from the active tone.

## Tones

`academic`, `casual`, `confident`, `empathetic`, `friendly`, `persuasive`,
`professional`, `storytelling`, `witty`.

```
python3 -m humanizer --list-tones
```

## Pipeline rules

Ten independent, swappable rules. The default order (tones may reorder via
`TONE_PIPELINES`):

1. `strip_ai_tells` — removes giveaways ("it is important to note that",
   "in conclusion", "delve into", …).
2. `prune_redundancy` — cuts padding ("due to the fact that" → "because"),
   doubled intensifiers, adjacent duplicate words.
3. `lexical_substitution` — tone-aware, variety-preserving paraphrasing of
   single words **and** multi-word phrases.
4. `adjust_contractions` — contract / expand to match the tone's register.
5. `reorder_clauses` — flips leading/trailing subordinate clauses.
6. `soften_passive` — nudges agentless passive toward active.
7. `vary_sentence_length` — split, merge, fragment → burstiness.
8. `inject_hedges_intensifiers` — tone-aware hedges/intensifiers.
9. `vary_openers` — breaks up repeated sentence-opening words.
10. `inject_discourse_markers` — tone starters & asides → human texture.

A final pass repairs `a`/`an` after substitutions.

## CLI

```bash
# Inline text
python3 -m humanizer --tone casual --strength 0.8 "It is important to note that AI is very good."

# From a file, with before/after metrics + change log
python3 -m humanizer --tone academic --strength 0.7 --file examples/academic.in.txt --metrics --changes

# Detailed advanced report (bigram perplexity, MTLD, burstiness profile, humanity score)
python3 -m humanizer --tone persuasive --file examples/persuasive.in.txt --report

# From stdin, reproducible
echo "We should use it because it is important." | python3 -m humanizer --tone witty --seed 42
```

Options: `--tone/-t`, `--strength/-s` (0.0–1.0), `--seed`, `--file/-f`,
`--metrics`, `--report`, `--changes`, `--list-tones`.

## Library

```python
from humanizer import Humanizer

h = Humanizer(tone="professional", strength=0.6, seed=7)
r = h.humanize("It is important to note that this is a very good idea.")

print(r.text)              # rewritten text
print(r.summary())         # perplexity / burstiness / lexical / humanity, before -> after
print(r.humanity_delta)    # change in 0-100 humanity score
print(r.changes)           # every edit made
```

Advanced metrics and custom pipelines:

```python
from humanizer import (Humanizer, Pipeline, humanity_score,
                        bigram_perplexity, mtld, detailed_report)

# Subset / reordered rules
Humanizer(tone="academic",
          pipeline=Pipeline(rules=["strip_ai_tells", "lexical_substitution"]))

humanity_score("some text")          # 0..100
detailed_report("some text")         # dict: bigram_perplexity, mtld, ...
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Layout

```
humanizer/
  lexicon.py          embedded frequency table -> unigram surprisal
  metrics.py          perplexity / burstiness / lexical (TTR, MATTR)
  advanced_metrics.py bigram perplexity, MTLD, humanity score, report
  tones.py            tone definitions; layers in the dictionaries pack
  dictionaries.py     large per-tone vocabulary pack (optional, auto-loaded)
  pipeline.py         the rule engine + core rules + per-tone pipelines
  extra_rules.py      reorder / openers / hedges / prune / passive rules
  core.py             Humanizer API + before/after metrics
  cli.py              command-line interface
tests/                unittest suites (test_humanizer, test_extended)
examples/             per-tone sample inputs
docs/                 in-browser web app (Pyodide): index.html, app.js, styles.css
web/build_site.py     bundles docs/ + live humanizer/ into _site for Pages
.github/workflows/    CI: runs tests, builds & deploys the web app to Pages
```

> Note: this nudges text toward human-typical statistics; it is a writing
> aid, not a guarantee against any specific detector.
