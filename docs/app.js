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
let pyodide, run;

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
from humanizer import Humanizer, list_tones

def _run(text, tone, strength, seed):
    s = None if seed in (None, "", "None") else int(seed)
    r = Humanizer(tone=tone, strength=float(strength), seed=s).humanize(text)
    return json.dumps({
        "text": r.text,
        "changes": r.changes,
        "humanity_before": r.humanity_before,
        "humanity_after": r.humanity_after,
        "before": r.metrics_before.as_dict(),
        "after": r.metrics_after.as_dict(),
    })
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
}

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
  $("output").textContent = res.text || "(no output)";
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
    runBtn.disabled = true;
    runBtn.textContent = "Humanizing…";
    setTimeout(() => {
      try {
        const seed = $("seed").value;
        const json = run(text, $("tone").value, $("strength").value, seed);
        render(JSON.parse(json));
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

(async () => {
  try {
    await loadHumanizer();
    wireUI();
    boot.style.display = "none";
  } catch (e) {
    fail("Failed to start: " + String(e));
  }
})();
