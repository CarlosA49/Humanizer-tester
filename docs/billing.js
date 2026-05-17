/* Trial limit, launch pricing, coupons, owner coupon generator, feedback.
 * No-backend MVP: state lives in localStorage; coupons are signed but
 * client-verified. The backend phase moves all enforcement server-side.
 */
(function () {
  "use strict";
  var CFG = window.HUMANIZER_CONFIG;
  var LS_USED = "hmz_used_words";
  var LS_UNLOCK = "hmz_unlock";
  var appliedDiscount = null; // {planId|'all', kind:'PCT'|'AMT', value}

  // ---- helpers -----------------------------------------------------------
  function peso(n) { return "₱" + Number(n).toLocaleString("en-PH"); }
  function el(id) { return document.getElementById(id); }
  function wordCount(t) {
    t = (t || "").trim();
    return t ? t.split(/\s+/).length : 0;
  }
  async function sha256hex(s) {
    var b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
    return Array.from(new Uint8Array(b))
      .map(function (x) { return x.toString(16).padStart(2, "0"); }).join("");
  }
  function getUsed() { return parseInt(localStorage.getItem(LS_USED) || "0", 10) || 0; }
  function setUsed(n) { localStorage.setItem(LS_USED, String(n)); }

  // ---- trial -------------------------------------------------------------
  function unlocked() {
    try { return !!JSON.parse(localStorage.getItem(LS_UNLOCK) || "null"); }
    catch (e) { return false; }
  }
  function remaining() { return Math.max(0, CFG.TRIAL_WORDS - getUsed()); }
  function allow() { return unlocked() || getUsed() < CFG.TRIAL_WORDS; }
  function consume(words) {
    if (unlocked()) return;
    setUsed(getUsed() + Math.max(0, words | 0));
    refreshBanner();
  }
  function refreshBanner() {
    var b = el("trialBanner");
    if (!b) return;
    if (unlocked()) {
      var u = {};
      try { u = JSON.parse(localStorage.getItem(LS_UNLOCK) || "{}"); } catch (e) {}
      var m = planMeta(u.plan || "");
      b.innerHTML =
        '<span class="ok">✓ ' + m.name +
        " unlocked on this device — thank you!</span>" +
        '<span class="muted">Up to ' + m.devices + " device" +
        (m.devices > 1 ? "s" : "") +
        " · multi-device sync activates with accounts</span>";
      return;
    }
    var r = remaining();
    b.innerHTML =
      '<span>Free trial: <strong>' + r + " / " + CFG.TRIAL_WORDS +
      ' words</strong> left</span>' +
      '<button id="seePlans" class="link">See plans</button>';
    var sp = el("seePlans");
    if (sp) sp.onclick = function () { scrollToPricing(); };
  }
  function scrollToPricing() {
    var p = el("pricing");
    if (p) p.scrollIntoView({ behavior: "smooth" });
  }
  function showPaywall() {
    var m = el("paywallModal");
    if (m) m.style.display = "flex";
  }

  // ---- coupons -----------------------------------------------------------
  // Code: PLAN-KIND-VALUE-EXP-SIG  (EXP = epoch-days, 0 = never)
  var PLAN_TOKEN = {
    STARTER: "starter", PRO: "pro", SEMI: "semiannual", UNLI: "unlimited",
    ANNUAL: "annual", LIFE: "lifetime", ALL: "all",
  };
  var TOKEN_FOR = {
    starter: "STARTER", pro: "PRO", semiannual: "SEMI", unlimited: "UNLI",
    annual: "ANNUAL", lifetime: "LIFE", all: "ALL",
  };
  function periodLabel(p) {
    return p === "mo" ? "/mo" : p === "6mo" ? " /6 mo"
         : p === "yr" ? "/yr" : " one-time";
  }
  function deviceId() {
    var d = localStorage.getItem("hmz_device_id");
    if (!d) {
      d = (crypto.randomUUID ? crypto.randomUUID()
            : String(Date.now()) + Math.random()).slice(0, 18);
      localStorage.setItem("hmz_device_id", d);
    }
    return d;
  }
  function planMeta(planId) {
    var p = CFG.PLANS.filter(function (x) { return x.id === planId; })[0];
    if (p) return { name: p.name, devices: p.devices };
    var c = (CFG.CODE_ONLY || {})[planId];
    if (c) return { name: c.name, devices: c.devices };
    return { name: planId, devices: 1 };
  }
  function epochDays() { return Math.floor(Date.now() / 86400000); }

  async function signPayload(plan, kind, value, exp) {
    var sig = await sha256hex(
      CFG.COUPON_SECRET + "|" + plan + "|" + kind + "|" + value + "|" + exp
    );
    return sig.slice(0, 8).toUpperCase();
  }
  async function makeCode(plan, kind, value, exp) {
    var sig = await signPayload(plan, kind, value, exp);
    return [plan, kind, value, exp, sig].join("-");
  }
  async function validateCode(raw) {
    var code = (raw || "").trim().toUpperCase().replace(/\s+/g, "");
    var p = code.split("-");
    if (p.length !== 5) return { ok: false, msg: "Invalid code format." };
    var plan = p[0], kind = p[1], value = parseInt(p[2], 10),
        exp = parseInt(p[3], 10), sig = p[4];
    if (!PLAN_TOKEN[plan] || ["PCT", "AMT", "FREE"].indexOf(kind) < 0 ||
        isNaN(value) || isNaN(exp)) {
      return { ok: false, msg: "Invalid code." };
    }
    var good = await signPayload(plan, kind, value, exp);
    if (good !== sig) return { ok: false, msg: "Invalid or tampered code." };
    if (exp !== 0 && epochDays() > exp) return { ok: false, msg: "This code has expired." };
    return { ok: true, plan: PLAN_TOKEN[plan], kind: kind, value: value };
  }

  async function applyCoupon(raw, contextPlanId) {
    var r = await validateCode(raw);
    if (!r.ok) return r;
    if (r.kind === "FREE") {
      localStorage.setItem(LS_UNLOCK, JSON.stringify({
        plan: r.plan, code: raw.trim().toUpperCase(),
        ts: Date.now(), device: deviceId(),
      }));
      refreshBanner();
      var fm = planMeta(r.plan);
      return { ok: true, free: true,
        msg: fm.name + " unlocked on this device — enjoy! (up to " +
          fm.devices + " device" + (fm.devices > 1 ? "s" : "") + ")" };
    }
    appliedDiscount = { plan: r.plan, kind: r.kind, value: r.value };
    renderPricing();
    if (contextPlanId) renderCheckout(contextPlanId);
    var label = r.kind === "PCT" ? r.value + "% off" : peso(r.value) + " off";
    return { ok: true, free: false,
      msg: "Coupon applied: " + label + " (" + r.plan + ")." };
  }
  function discountedPrice(plan) {
    var price = plan.now;
    if (appliedDiscount &&
        (appliedDiscount.plan === "all" || appliedDiscount.plan === plan.id)) {
      if (appliedDiscount.kind === "PCT") {
        price = Math.round(price * (1 - appliedDiscount.value / 100));
      } else {
        price = Math.max(0, price - appliedDiscount.value);
      }
    }
    return price;
  }

  // ---- pricing UI --------------------------------------------------------
  function planCard(plan) {
    var dp = discountedPrice(plan);
    var per = periodLabel(plan.period);
    var hasDisc = dp !== plan.now;
    return (
      '<div class="plan' + (plan.popular ? " popular" : "") + '">' +
      (plan.popular ? '<div class="tag">★ Most popular</div>' : "") +
      (plan.highlight ? '<div class="tag alt">' + plan.highlight + "</div>" : "") +
      "<h3>" + plan.name + "</h3>" +
      '<div class="best">' + plan.best + "</div>" +
      '<div class="price">' +
        '<span class="was">' + peso(plan.was) + "</span> " +
        '<span class="now">' + peso(dp) + "</span>" +
        '<span class="per">' + per + "</span>" +
      "</div>" +
      (hasDisc ? '<div class="couponed">coupon applied</div>'
               : '<div class="save">Launch price</div>') +
      '<div class="words">' + plan.words + "</div>" +
      '<div class="devs">🖥 Up to ' + plan.devices + " device" +
        (plan.devices > 1 ? "s" : "") + "</div>" +
      "<ul>" + plan.perks.map(function (p) { return "<li>" + p + "</li>"; }).join("") + "</ul>" +
      '<button class="primary buy" data-plan="' + plan.id + '">Choose ' + plan.name + "</button>" +
      "</div>"
    );
  }
  function renderPricing() {
    var host = el("pricing");
    if (!host) return;
    host.innerHTML =
      '<h2 class="sec">Plans &amp; pricing</h2>' +
      '<p class="introline">🚀 <strong>Introductory launch pricing</strong> — ' +
      "early supporters lock in these rates before they go up. Try " +
      CFG.TRIAL_WORDS + " words free, no signup.</p>" +
      '<div class="plans">' +
      CFG.PLANS.map(planCard).join("") +
      "</div>" +
      '<div class="couponbox">' +
        '<input id="couponIn" placeholder="Have a coupon code?" />' +
        '<button id="couponBtn" class="ghost">Apply</button>' +
        '<span id="couponMsg" class="cmsg"></span>' +
      "</div>";
    Array.prototype.forEach.call(host.querySelectorAll(".buy"), function (b) {
      b.onclick = function () { renderCheckout(b.getAttribute("data-plan")); };
    });
    el("couponBtn").onclick = function () {
      var msg = el("couponMsg");
      msg.textContent = "Checking…";
      applyCoupon(el("couponIn").value).then(function (res) {
        msg.textContent = res.msg;
        msg.className = "cmsg " + (res.ok ? "good" : "bad");
      });
    };
  }

  // ---- checkout modal ----------------------------------------------------
  function renderCheckout(planId) {
    var plan = CFG.PLANS.filter(function (p) { return p.id === planId; })[0];
    if (!plan) return;
    var dp = discountedPrice(plan);
    var link = CFG.PAYMENTS.PAYMONGO_LINKS[plan.id];
    var body = el("checkoutBody");
    body.innerHTML =
      "<h3>" + plan.name + " — " + peso(dp) + periodLabel(plan.period) + "</h3>" +
      '<p class="muted">Usable on up to ' + plan.devices + " device" +
        (plan.devices > 1 ? "s" : "") +
        " (device binding enforced once accounts launch).</p>" +
      (dp !== plan.now ? '<p class="couponed">Coupon discount applied.</p>' : "") +
      '<ol class="paysteps">' +
        "<li><strong>GCash / card (Philippines)</strong> via PayMongo → settles to the owner's BPI." +
          (link
            ? ' <a class="paybtn" href="' + link + '" target="_blank" rel="noopener">Pay ' + peso(dp) + "</a>"
            : ' <span class="muted">(payment link coming — contact the owner)</span>') +
        "</li>" +
        "<li><strong>International</strong> — pay via PayPal QR" +
          (CFG.PAYMENTS.PAYPAL_ME
            ? ' or <a href="' + CFG.PAYMENTS.PAYPAL_ME + '" target="_blank" rel="noopener">PayPal.me</a>'
            : "") + ":" +
          '<div class="qrwrap"><img src="./payments/paypal-qr.png" alt="PayPal QR" ' +
            "onerror=\"this.outerHTML='<span class=&quot;muted&quot;>PayPal QR will be added by the owner.</span>'\" /></div>" +
        "</li>" +
        "<li>After paying, email proof to <a href=\"mailto:" + CFG.CONTACT_EMAIL +
          "\">" + CFG.CONTACT_EMAIL + "</a>. Access is activated manually " +
          "(instant automation comes with the accounts/backend).</li>" +
      "</ol>" +
      '<div class="couponbox">' +
        '<input id="coCoupon" placeholder="Coupon code (optional)" />' +
        '<button id="coCouponBtn" class="ghost">Apply</button>' +
        '<span id="coCouponMsg" class="cmsg"></span>' +
      "</div>";
    el("coCouponBtn").onclick = function () {
      var m = el("coCouponMsg");
      m.textContent = "Checking…";
      applyCoupon(el("coCoupon").value, planId).then(function (res) {
        m.textContent = res.msg;
        m.className = "cmsg " + (res.ok ? "good" : "bad");
        if (res.free) { var pm = el("paywallModal"); if (pm) pm.style.display = "none"; }
      });
    };
    el("checkoutModal").style.display = "flex";
  }

  // ---- owner coupon generator -------------------------------------------
  function ownerPanelHTML() {
    return (
      "<h3>Owner — coupon generator</h3>" +
      '<p class="muted">Codes are reusable in this MVP (single-use needs the backend).</p>' +
      '<label>Plan<select id="ogPlan">' +
        Object.keys(TOKEN_FOR).map(function (k) {
          return '<option value="' + TOKEN_FOR[k] + '">' + k + "</option>";
        }).join("") +
      "</select></label>" +
      '<label>Type<select id="ogKind">' +
        '<option value="FREE">FREE (100% — unlocks access)</option>' +
        '<option value="PCT">Percent off</option>' +
        '<option value="AMT">Peso off</option>' +
      "</select></label>" +
      '<label>Value <input id="ogVal" type="number" value="100" min="1" /></label>' +
      '<label>Expires in days (0 = never) <input id="ogExp" type="number" value="0" min="0" /></label>' +
      '<button id="ogGen" class="primary">Generate code</button>' +
      '<div id="ogOut" class="ogout"></div>'
    );
  }
  function wireOwnerPanel() {
    el("ogGen").onclick = function () {
      var plan = el("ogPlan").value, kind = el("ogKind").value;
      var val = kind === "FREE" ? 100 : Math.max(1, parseInt(el("ogVal").value, 10) || 0);
      var days = Math.max(0, parseInt(el("ogExp").value, 10) || 0);
      var exp = days === 0 ? 0 : epochDays() + days;
      makeCode(plan, kind, val, exp).then(function (code) {
        el("ogOut").innerHTML =
          '<code>' + code + "</code>" +
          '<button id="ogCopy" class="ghost">Copy</button>';
        el("ogCopy").onclick = function () {
          navigator.clipboard.writeText(code);
          el("ogCopy").textContent = "Copied";
        };
      });
    };
  }
  function openOwner() {
    var pass = prompt("Owner password:");
    if (pass == null) return;
    sha256hex(pass).then(function (h) {
      if (h !== CFG.OWNER_SHA256) { alert("Incorrect password."); return; }
      var body = el("ownerBody");
      body.innerHTML = ownerPanelHTML();
      wireOwnerPanel();
      el("ownerModal").style.display = "flex";
    });
  }

  // ---- feedback ----------------------------------------------------------
  function wireFeedback() {
    var host = el("feedback");
    if (!host) return;
    host.innerHTML =
      '<h2 class="sec">Feedback</h2>' +
      '<p class="introline">Tell us what to improve — it shapes the roadmap.</p>' +
      '<div class="fbform">' +
        '<div id="stars" class="stars" role="radiogroup" aria-label="Rating">' +
          [1,2,3,4,5].map(function (n) {
            return '<button type="button" class="star" data-n="' + n + '">★</button>';
          }).join("") + "</div>" +
        '<textarea id="fbMsg" placeholder="Your feedback…" rows="4"></textarea>' +
        '<input id="fbEmail" type="email" placeholder="Email (optional, for a reply)" />' +
        '<button id="fbSend" class="primary">Send feedback</button>' +
        '<span id="fbMsgOut" class="cmsg"></span>' +
      "</div>";
    var rating = 0;
    Array.prototype.forEach.call(host.querySelectorAll(".star"), function (s) {
      s.onclick = function () {
        rating = parseInt(s.getAttribute("data-n"), 10);
        Array.prototype.forEach.call(host.querySelectorAll(".star"), function (x) {
          x.classList.toggle("on", parseInt(x.getAttribute("data-n"), 10) <= rating);
        });
      };
    });
    el("fbSend").onclick = function () {
      var msg = el("fbMsg").value.trim();
      var out = el("fbMsgOut");
      if (!msg) { out.textContent = "Please write something first."; out.className = "cmsg bad"; return; }
      var payload = { rating: rating, message: msg, email: el("fbEmail").value.trim(),
                      source: "humanizer-web" };
      var ep = CFG.FEEDBACK_FORM_ENDPOINT;
      if (ep) {
        out.textContent = "Sending…"; out.className = "cmsg";
        fetch(ep, { method: "POST", headers: {
          "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload) })
          .then(function (r) {
            if (r.ok) { out.textContent = "Thank you! 🙏"; out.className = "cmsg good";
              el("fbMsg").value = ""; }
            else throw new Error();
          })
          .catch(function () { out.textContent = "Couldn't send — please try again later.";
            out.className = "cmsg bad"; });
      } else {
        var body = encodeURIComponent(
          "Rating: " + (rating || "-") + "\n\n" + msg +
          (payload.email ? "\n\nReply to: " + payload.email : ""));
        window.location.href = "mailto:" + CFG.CONTACT_EMAIL +
          "?subject=" + encodeURIComponent("AI Humanizer feedback") + "&body=" + body;
        out.textContent = "Opening your email app…"; out.className = "cmsg good";
      }
    };
  }

  // ---- init --------------------------------------------------------------
  function closeOnClick(modalId) {
    var m = el(modalId);
    if (!m) return;
    m.addEventListener("click", function (e) {
      if (e.target === m || e.target.classList.contains("xclose"))
        m.style.display = "none";
    });
  }
  function init() {
    renderPricing();
    wireFeedback();
    refreshBanner();
    ["paywallModal", "checkoutModal", "ownerModal"].forEach(closeOnClick);
    var ow = el("ownerLink");
    if (ow) ow.onclick = function (e) { e.preventDefault(); openOwner(); };
    var pwBtn = el("paywallPlans");
    if (pwBtn) pwBtn.onclick = function () {
      el("paywallModal").style.display = "none"; scrollToPricing();
    };
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();

  window.Trial = {
    allow: allow, consume: consume, remaining: remaining,
    unlocked: unlocked, showPaywall: showPaywall,
    wordCount: wordCount, refreshBanner: refreshBanner,
  };
})();
