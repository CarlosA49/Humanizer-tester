# Humanizer-tester

[![Open the app](https://img.shields.io/badge/▶%20Open%20the%20app-Tap%20here-3b82f6?style=for-the-badge)](https://carlosa49.github.io/Humanizer-tester/)
[![Install on iPhone](https://img.shields.io/badge/Install%20on%20iPhone-Add%20to%20Home%20Screen-000000?style=for-the-badge&logo=apple)](https://carlosa49.github.io/Humanizer-tester/)

# 📲 Get the app

**Open this link on your phone, then add it to your Home Screen — it becomes an app.**

### 👉 https://carlosa49.github.io/Humanizer-tester/

| Device | How to install (takes 5 seconds) |
|---|---|
| **iPhone / iPad** | Open the link in **Safari** → tap the **Share** button → **Add to Home Screen** → **Add**. |
| **Android** | Open the link in **Chrome** → menu **⋮** → **Install app**. |
| **Computer** | Open in **Chrome/Edge** → click the **Install** icon in the address bar. |

You get a real app icon, it opens full‑screen, and it **works offline** after
the first open. Delete it like any app and re‑add it from the link anytime.
Nothing is uploaded — it all runs on your device. *(No App Store needed; a
native App Store build is also scaffolded in [`ios/`](ios/).)*

---

An **AI Humanizer**: it rewrites machine-sounding text into a chosen human
**tone** while measuring and improving the three signals AI-text detectors
care about most — **perplexity**, **burstiness**, and **lexical diversity**.

Pure Python, **standard library only** (no models, no network, no installs).

## Plans, trial, coupons & feedback (MVP)

A no‑backend launch MVP is built in: a **500‑word free trial**, an
introductory‑priced plans page with pricing‑psychology framing, a **coupon
system** (%‑off / ₱‑off / 100%‑free), a **password‑gated owner coupon
generator** (footer → "Owner tools"), and an embedded **feedback form**.

| Plan | Launch price | Words | Devices |
|---|---|---|---|
| Starter /mo | ₱499 | 10,000 / mo | 1 |
| Pro /mo ★ | ₱799 | 30,000 / mo | 2 |
| Pro Semi‑Annual (6 mo) | ₱3,990 | 30,000 / mo | 2 |
| Pro Annual | ₱6,990 | 30,000 / mo | 3 |
| Unlimited /mo | ₱5,000 | Unlimited (fair use) | 5 |
| **Lifetime** (code‑only) | not listed | Pro forever | 3 |

**Lifetime is never shown on the page** — issue it from Owner tools (plan
`LIFE`, type `FREE`); redeeming the code unlocks full access on that device.
Device limits are shown to users now and **enforced server‑side in the
backend phase** (client‑side device binding alone is bypassable).

> ⚠️ Without accounts this is a client‑side MVP (bypassable). **Enable the
> free Supabase backend below** and trial counting, coupon redemption and
> device limits become server‑enforced and tamper‑resistant. Payment capture
> stays manual (PayMongo/PayPal proof → manual activation) for now.

**Owner setup — edit [`docs/config.js`](docs/config.js):**
- `FEEDBACK_FORM_ENDPOINT` — paste a free [Formspree](https://formspree.io)
  endpoint (else feedback falls back to email).
- `CONTACT_EMAIL` — your email (manual activation + fallback).
- `PAYMENTS.PAYMONGO_LINKS` — PayMongo payment‑link URLs per plan
  (GCash + cards → your **BPI**).
- `PAYMENTS.PAYPAL_ME` and drop your PayPal QR at
  `docs/payments/paypal-qr.png` (international).
- Prices/word limits/anchors live in `PLANS` — tweak freely.
- The owner password is stored only as a SHA‑256 hash (never plaintext).

### Free accounts (Supabase) — optional, recommended

Adds real signup/login with **email + password** and a per‑user profile
that **syncs plan, trial words and devices across browsers/phones**. Trial
counting, coupon redemption and device limits run as server‑side
`SECURITY DEFINER` functions, so a signed‑in user **cannot tamper** with
their own word count, unlock flag or device list. Free tier, no server to run.

1. Create a free project at <https://supabase.com>.
2. Open **SQL editor → New query**, paste
   [`supabase/schema.sql`](supabase/schema.sql), and **Run**.
3. **Authentication → Providers → Email** = enabled. (For instant signup in
   testing you may disable “Confirm email”; keep it on for production.)
4. **Project Settings → API**: copy the **Project URL** and the **anon
   public** key into `SUPABASE_URL` / `SUPABASE_ANON_KEY` in
   [`docs/config.js`](docs/config.js).
5. Make sure `COUPON_SECRET` in `docs/config.js` **matches** the
   `coupon_secret` value seeded by `schema.sql` (edit the SQL before running
   if you change it).

The anon key is safe to ship publicly — row‑level security restricts each
user to their own row, and all writes go through the server functions.
Leave the keys blank and the app keeps working as the localStorage‑only MVP.

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

Eleven independent, swappable rules. The default order (tones may reorder via
`TONE_PIPELINES`):

1. `strip_ai_tells` — removes giveaways ("it is important to note that",
   "in conclusion", "delve into", …).
2. `strip_ai_red_flags` — scrubs the classic tells of AI writing: em-dash
   overuse, "not just X, it's Y" / "not only X but also Y" parallel
   scaffolds, the rule-of-three list cadence, vague corporate buzzwords
   ("elevate", "robust", "leverage", …), exaggerated impersonal praise,
   forced clichéd analogies and redundant filler preamble.
3. `prune_redundancy` — cuts padding ("due to the fact that" → "because"),
   doubled intensifiers, adjacent duplicate words.
4. `lexical_substitution` — tone-aware, variety-preserving paraphrasing of
   single words **and** multi-word phrases.
5. `adjust_contractions` — contract / expand to match the tone's register.
6. `reorder_clauses` — flips leading/trailing subordinate clauses.
7. `soften_passive` — nudges agentless passive toward active.
8. `vary_sentence_length` — split, merge, fragment → burstiness.
9. `inject_hedges_intensifiers` — tone-aware hedges/intensifiers.
10. `vary_openers` — breaks up repeated sentence-opening words.
11. `inject_discourse_markers` — tone starters & asides → human texture.

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
  extra_rules.py      reorder / openers / hedges / prune / passive /
                      ai-red-flag rules
  core.py             Humanizer API + before/after metrics
  cli.py              command-line interface
tests/                unittest suites (test_humanizer, test_extended)
examples/             per-tone sample inputs
docs/                 installable web app (PWA): index.html, app.js, styles.css,
                      manifest.webmanifest, sw.js (offline), icons/
web/build_site.py     bundles docs/ + live humanizer/ into _site for Pages
.github/workflows/    CI: runs tests, builds & deploys the web app to Pages
ios/                  App Store wrapper scaffold (SwiftUI WKWebView) + plan
```

> Note: this nudges text toward human-typical statistics; it is a writing
> aid, not a guarantee against any specific detector.
