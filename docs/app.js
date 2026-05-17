"use strict";

const REPO = "https://github.com/carlosa49/Humanizer-tester";
const SAMPLE =
  "It is important to note that artificial intelligence is a very good " +
  "technology in today's world. It is important to note that it can help " +
  "people in many different ways and it can make things easy and it can make " +
  "things fast. In conclusion, artificial intelligence is a very important " +
  "tool that we should use because it is a very good thing.";

const $ = (id) => document.getElementById(id);
const boot = $("boot"), bootMsg = $("bootMsg");
let pyodide, run, suggest;

$("repoLink").href = REPO;

function fail(msg) {
  boot.innerHTML =
    '<p class="err">' + msg + "</p>" +
    '<p><a style="color:#3b82f6" href="' + REPO + '">Open the source repo</a></p>';
}

async function loadHumanizer() {
  bootMsg.textContent = "Downloading Python runtime…";
  pyodide = await loadPyodide();

  bootMsg.textContent = "Loading the humanizer package…";
  const listResp = await fetch("./humanizer/__files__.json", { cache: "no-cache" });
  if (!listResp.ok) throw new Error("Could not load package manifest.");
  const files = await listResp.json();

  try { pyodide.FS.mkdir("/pkg"); } catch (e) {}
  try { pyodide.FS.mkdir("/pkg/humanizer"); } catch (e) {}

  for (const name of files) {
    const r = await fetch("./humanizer/" + name, { cache: "no-cache" });
    if (!r.ok) throw new Error("Missing package file: " + name);
    pyodide.FS.writeFile("/pkg/humanizer/" + name, await r.text());
  }

  bootMsg.textContent = "Initializing…";
  await pyodide.runPythonAsync(`
import sys, json
if "/pkg" not in sys.path:
    sys.path.insert(0, "/pkg")
from humanizer import Humanizer, list_tones, suggest_synonyms

def _run(text, tone, strength, seed, restructure, citations, sources,
         academic, acronyms):
    s = None if seed in (None, "", "None") else int(seed)
    src = [ln.strip() for ln in (sources or "").splitlines() if ln.strip()]
    acro = {}
    for ln in (acronyms or "").splitlines():
        if "=" in ln:
            k, _, v = ln.partition("=")
            if k.strip() and v.strip():
                acro[k.strip()] = v.strip()
    r = Humanizer(
        tone=tone, strength=float(strength), seed=s,
        restructure=(str(restructure) != "off"),
        citations=citations or "off",
        sources=src,
        academic_style=(str(academic) == "on"),
        acronyms=acro,
    ).humanize(text)
    return json.dumps({
        "text": r.text,
        "changes": r.changes,
        "humanity_before": r.humanity_before,
        "humanity_after": r.humanity_after,
        "before": r.metrics_before.as_dict(),
        "after": r.metrics_after.as_dict(),
    })

def _suggest(word, tone):
    return json.dumps(suggest_synonyms(word, tone, 12))
`);

  const tones = pyodide.runPython("list_tones()").toJs();
  const sel = $("tone");
  sel.innerHTML = "";
  for (const t of tones) {
    const o = document.createElement("option");
    o.value = t; o.textContent = t;
    if (t === "casual") o.selected = true;
    sel.appendChild(o);
  }
  sel.disabled = false;
  run = pyodide.globals.get("_run");
  suggest = pyodide.globals.get("_suggest");
}

// ---- clickable output + double-click synonym popover ---------------------- #
const _esc = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Render text as a run of word spans interleaved with verbatim separators so
// each word is individually targetable for the double-click feature.
function renderClickable(text) {
  const out = $("output");
  out.innerHTML = "";
  const re = /([A-Za-z]+(?:[-'][A-Za-z]+)*)|([^A-Za-z]+)/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m[1]) {
      const sp = document.createElement("span");
      sp.className = "w";
      sp.textContent = m[1];
      out.appendChild(sp);
    } else {
      out.appendChild(document.createTextNode(m[2]));
    }
  }
}

const _A_VOWEL = /^[aeiou]/i;
const _AN_EXC = /^(hour|honest|honou?r|heir)/i;
const _A_EXC = /^(uni|use|user|one|once|euro|ufo)/i;

function fixArticleBefore(span, word) {
  // If the preceding word is "a"/"an", correct it for the new word's sound.
  let n = span.previousSibling;
  while (n && n.nodeType === 3 && !n.textContent.trim()) n = n.previousSibling;
  if (!n || !n.classList || !n.classList.contains("w")) return;
  const prev = n.textContent;
  if (!/^(a|an|A|An|AN)$/.test(prev)) return;
  let vowel = _A_VOWEL.test(word);
  if (_AN_EXC.test(word)) vowel = true;
  else if (_A_EXC.test(word)) vowel = false;
  const base = vowel ? "an" : "a";
  n.textContent =
    prev[0] === prev[0].toUpperCase()
      ? base[0].toUpperCase() + base.slice(1)
      : base;
}

function matchCase(src, repl) {
  if (src.length > 1 && src === src.toUpperCase()) return repl.toUpperCase();
  if (src[0] === src[0].toUpperCase())
    return repl[0].toUpperCase() + repl.slice(1);
  return repl;
}

function closePopover() {
  const p = $("synPop");
  if (p) p.remove();
}

function openPopover(span) {
  closePopover();
  const original = span.textContent;
  let list;
  try {
    list = JSON.parse(suggest(original, $("tone").value));
  } catch (e) {
    list = [];
  }
  const pop = document.createElement("div");
  pop.id = "synPop";
  pop.className = "synpop";
  if (!list.length) {
    pop.innerHTML = '<div class="synempty">No synonyms for “' +
      _esc(original) + '”</div>';
  } else {
    list.forEach((s) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "synchip";
      b.textContent = s;
      b.addEventListener("click", () => {
        const repl = matchCase(original, s);
        span.textContent = repl;
        fixArticleBefore(span, s.replace(/^\W+/, ""));
        closePopover();
        $("copyBtn").hidden = !$("output").textContent.trim();
      });
      pop.appendChild(b);
    });
  }
  document.body.appendChild(pop);
  const r = span.getBoundingClientRect();
  pop.style.top = window.scrollY + r.bottom + 6 + "px";
  pop.style.left =
    window.scrollX +
    Math.min(r.left, window.innerWidth - pop.offsetWidth - 12) +
    "px";
}

document.addEventListener("click", (e) => {
  if (!e.target.closest("#synPop") && !e.target.closest("#output .w"))
    closePopover();
});
$("output").addEventListener("dblclick", (e) => {
  const sp = e.target.closest(".w");
  if (sp && suggest) {
    e.preventDefault();
    openPopover(sp);
  }
});

function metricCard(key, before, after, better) {
  const d = after - before;
  const good = better === "up" ? d > 0 : better === "down" ? d < 0 : d !== 0;
  const cls = d === 0 ? "" : good ? "up" : "down";
  const sign = d >= 0 ? "+" : "";
  const fmt = (n) => (Math.abs(n) >= 100 ? n.toFixed(0) : n.toFixed(2));
  return (
    '<div class="metric"><div class="k">' + key + "</div>" +
    '<div class="v">' + fmt(after) + "</div>" +
    '<div class="d ' + cls + '">' + fmt(before) + " → " + sign + fmt(d) + "</div></div>"
  );
}

function render(res) {
  if (res.text) renderClickable(res.text);
  else $("output").textContent = "(no output)";
  $("copyBtn").hidden = !res.text;

  const b = res.before, a = res.after;
  $("metrics").innerHTML =
    metricCard("Humanity /100", res.humanity_before, res.humanity_after, "up") +
    metricCard("Perplexity", b.perplexity, a.perplexity, "up") +
    metricCard("Burstiness", b.burstiness, a.burstiness, "up") +
    metricCard("Lexical (MATTR)", b.mattr, a.mattr, "up");
  $("metrics").hidden = false;

  const ul = $("changes");
  ul.innerHTML = "";
  res.changes.forEach((c) => {
    const li = document.createElement("li");
    li.textContent = c;
    ul.appendChild(li);
  });
  $("changeCount").textContent = res.changes.length;
  $("changesWrap").hidden = res.changes.length === 0;
}

function wireUI() {
  const input = $("input"), runBtn = $("run");

  const updCount = () => ($("inCount").textContent = input.value.length + " chars");
  input.addEventListener("input", updCount);
  updCount();

  $("strength").addEventListener("input", (e) => {
    $("strengthVal").textContent = (+e.target.value).toFixed(2);
  });

  const citSel = $("citations");
  citSel.addEventListener("change", () => {
    $("sourcesRow").hidden = citSel.value !== "numbered";
  });
  const acaSel = $("academic");
  acaSel.addEventListener("change", () => {
    $("acronymRow").hidden = acaSel.value !== "on";
  });

  $("sampleBtn").addEventListener("click", () => {
    input.value = SAMPLE; updCount(); input.focus();
  });

  $("copyBtn").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("output").textContent);
    $("copyBtn").textContent = "Copied";
    setTimeout(() => ($("copyBtn").textContent = "Copy"), 1500);
  });

  runBtn.addEventListener("click", () => {
    const text = input.value.trim();
    if (!text) { input.focus(); return; }
    const T = window.Trial;
    const words = T ? T.wordCount(text) : 0;
    if (T && !T.allow()) { T.showPaywall(); return; }
    runBtn.disabled = true;
    runBtn.textContent = "Humanizing…";
    setTimeout(() => {
      try {
        const seed = $("seed").value;
        const json = run(
          text,
          $("tone").value,
          $("strength").value,
          seed,
          $("restructure").value,
          $("citations").value,
          $("sources").value,
          $("academic").value,
          $("acronyms").value
        );
        render(JSON.parse(json));
        if (T) T.consume(words);
      } catch (err) {
        $("output").innerHTML = '<span class="err">Error: ' +
          String(err).replace(/</g, "&lt;") + "</span>";
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = "Humanize";
      }
    }, 10);
  });

  runBtn.disabled = false;
  runBtn.textContent = "Humanize";
}

if ("serviceWorker" in navigator) {
  // Auto-update the installed Home Screen app (Android + iOS) whenever a
  // new version is deployed: when a fresh service worker takes control,
  // reload once so the latest HTML/JS/CSS is shown. Guarded so it never
  // loops and never reloads on the very first install.
  let swRefreshing = false;
  const hadController = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (swRefreshing || !hadController) return;
    swRefreshing = true;
    window.location.reload();
  });
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").then((reg) => {
      const check = () => reg.update().catch(() => {});
      check();
      // Re-check when the app is reopened/foregrounded (installed PWAs
      // often resume from background without a full navigation).
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") check();
      });
      setInterval(check, 60 * 60 * 1000);
    }).catch(() => {});
  });
}

(async () => {
  try {
    await loadHumanizer();
    wireUI();
    boot.style.display = "none";
  } catch (e) {
    fail("Failed to start: " + String(e));
  }
})();
