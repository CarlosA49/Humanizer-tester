/* Trial limit, launch pricing, coupons, owner coupon generator, feedback.
 * No-backend MVP: state lives in localStorage; coupons are signed but
 * client-verified. The backend phase moves all enforcement server-side.
 */
(function () {
  "use strict";
  var CFG = window.HUMANIZER_CONFIG;
  var LS_USED = "hmz_used_words";
  var LS_UNLOCK = "hmz_unlock";
  var LS_DEV = "hmz_dev"; // developer no-limit, this device only
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
  // Account is the source of truth when signed in; localStorage otherwise.
  function acct() {
    var A = window.Account;
    return A && A.ready && A.signedIn() ? A : null;
  }
  function prof() { var A = acct(); return A ? A.profile() : null; }
  function getUsed() {
    var p = prof();
    if (p) return p.trial_words | 0;
    return parseInt(localStorage.getItem(LS_USED) || "0", 10) || 0;
  }
  function setUsed(n) { localStorage.setItem(LS_USED, String(n)); }

  // ---- trial -------------------------------------------------------------
  function unlocked() {
    var p = prof();
    if (p) return !!p.unlocked;
    try { return !!JSON.parse(localStorage.getItem(LS_UNLOCK) || "null"); }
    catch (e) { return false; }
  }
  // Developer "no limit" — local to this device, gated by DEV_SHA256.
  function devMode() {
    try { return localStorage.getItem(LS_DEV) === "on"; } catch (e) { return false; }
  }
  function setDevMode(on) {
    try {
      if (on) localStorage.setItem(LS_DEV, "on");
      else localStorage.removeItem(LS_DEV);
    } catch (e) {}
    refreshBanner();
  }
  function tryDevUnlock() {
    if (devMode()) {
      if (confirm("Developer mode is ON. Turn it off on this device?"))
        setDevMode(false);
      return;
    }
    var pass = prompt("Developer password (removes the word limit on this device):");
    if (pass == null || pass === "") return;
    sha256hex(pass).then(function (h) {
      if (h !== CFG.DEV_SHA256) { alert("Incorrect password."); return; }
      setDevMode(true);
      alert("Developer mode ON — word/token limit disabled on this device.");
    });
  }

  function remaining() { return Math.max(0, CFG.TRIAL_WORDS - getUsed()); }
  function allow() { return devMode() || unlocked() || getUsed() < CFG.TRIAL_WORDS; }
  function consume(words) {
    if (devMode() || unlocked()) return;
    var A = acct();
    if (A) { A.consumeWords(words).then(refreshBanner); return; }
    setUsed(getUsed() + Math.max(0, words | 0));
    refreshBanner();
  }
  var deviceLimitHit = false;
  function refreshBanner() {
    var b = el("trialBanner");
    if (!b) return;
    var A = acct(), authReady = window.Account && window.Account.ready;
    var who = A ? '<span class="who">' + window.Account.email() + "</span>" : "";
    var authBtn = !authReady ? ""
      : A ? '<button id="acctOut" class="link">Sign out</button>'
          : '<button id="acctBtn" class="link">Sign in / Create account</button>';

    if (devMode()) {
      b.innerHTML = who +
        '<span class="ok">⚙ Developer mode — word/token limit off ' +
        "(this device)</span>" +
        '<button id="devOff" class="link">Turn off</button>' + authBtn;
      var df = el("devOff");
      if (df) df.onclick = function () { setDevMode(false); };
      var ab0 = el("acctBtn"); if (ab0) ab0.onclick = openAuth;
      var ao0 = el("acctOut");
      if (ao0) ao0.onclick = function () { window.Account.signOut(); };
      return;
    }
    if (deviceLimitHit) {
      var pm = planMeta((prof() && prof().plan) || "");
      b.innerHTML = who +
        '<span class="bad">Device limit reached (' + pm.devices +
        " for " + pm.name + "). </span>" +
        '<button id="useHere" class="link">Use this device (sign out others)</button>' +
        authBtn;
    } else if (unlocked()) {
      var m;
      if (A) { m = planMeta((prof() && prof().plan) || ""); }
      else {
        var u = {};
        try { u = JSON.parse(localStorage.getItem(LS_UNLOCK) || "{}"); } catch (e) {}
        m = planMeta(u.plan || "");
      }
      b.innerHTML = who +
        '<span class="ok">✓ ' + m.name + (A ? " — synced" : " unlocked") +
        "</span>" +
        '<span class="muted">Up to ' + m.devices + " device" +
        (m.devices > 1 ? "s" : "") +
        (A ? " · follows your account" : " · sign in to sync") + "</span>" +
        authBtn;
    } else {
      var r = remaining();
      b.innerHTML = who +
        '<span>Free trial: <strong>' + r + " / " + CFG.TRIAL_WORDS +
        " words</strong> left" + (A ? " · synced" : "") + "</span>" +
        '<button id="seePlans" class="link">See plans</button>' + authBtn;
    }
    var sp = el("seePlans");
    if (sp) sp.onclick = scrollToPricing;
    var ab = el("acctBtn");
    if (ab) ab.onclick = openAuth;
    var ao = el("acctOut");
    if (ao) ao.onclick = function () { window.Account.signOut(); };
    var uh = el("useHere");
    if (uh) uh.onclick = function () {
      window.Account.forgetOthers(deviceId()).then(function () {
        deviceLimitHit = false; onAccount();
      });
    };
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
    var A = acct();
    if (A) {
      var sr = await A.redeemCoupon(raw);
      if (!sr || !sr.ok) return { ok: false, msg: (sr && sr.msg) || "Invalid code." };
      if (sr.free) {
        deviceLimitHit = false;
        await onAccount();
        var fm0 = planMeta(sr.plan);
        return { ok: true, free: true,
          msg: fm0.name + " unlocked on your account — synced across up to " +
            fm0.devices + " device" + (fm0.devices > 1 ? "s" : "") + "." };
      }
      appliedDiscount = { plan: sr.plan, kind: sr.kind, value: sr.value };
      renderPricing();
      if (contextPlanId) renderCheckout(contextPlanId);
      var l0 = sr.kind === "PCT" ? sr.value + "% off" : peso(sr.value) + " off";
      return { ok: true, free: false,
        msg: "Coupon applied: " + l0 + " (" + sr.plan + ")." };
    }
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
      '<div id="ogOut" class="ogout"></div>' +
      '<hr><h3>Developer</h3>' +
      '<p class="muted">No-limit mode on <em>this device</em> only.</p>' +
      '<button id="ogDev" class="ghost"></button>'
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
    var dv = el("ogDev");
    function paint() {
      dv.textContent = devMode()
        ? "Turn OFF developer no-limit" : "Turn ON developer no-limit";
    }
    paint();
    dv.onclick = function () {
      if (devMode()) { setDevMode(false); paint(); return; }
      tryDevUnlock();
      // re-paint shortly after the async password check resolves
      setTimeout(paint, 400);
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

  // ---- accounts (UI) -----------------------------------------------------
  async function onAccount() {
    if (!acct()) { deviceLimitHit = false; refreshBanner(); renderAuth(); return; }
    var cap = unlocked()
      ? planMeta((prof() && prof().plan) || "").devices : 1;
    var res = await window.Account.registerDevice(deviceId(), cap);
    deviceLimitHit = !!(res && res.limit);
    refreshBanner();
    renderAuth();
  }
  function authState() {
    if (!window.Account || !window.Account.ready) return "off";
    return window.Account.signedIn() ? "in" : "out";
  }
  function renderAuth() {
    var body = el("authBody");
    if (!body) return;
    var st = authState();
    if (st === "off") {
      body.innerHTML = "<h3>Accounts</h3><p class=\"muted\">User accounts " +
        "aren't configured yet. Owner: create a free Supabase project, run " +
        "<code>supabase/schema.sql</code>, then add the keys to " +
        "<code>docs/config.js</code>.</p>";
      return;
    }
    if (st === "in") {
      var p = prof() || {}, m = planMeta(p.plan || "");
      var nDev = (p.devices && p.devices.length) || 0;
      body.innerHTML =
        "<h3>Your account</h3>" +
        "<p><strong>" + window.Account.email() + "</strong></p>" +
        '<p class="muted">' +
          (p.unlocked ? m.name + " — full access" :
            "Free trial — " + Math.max(0, CFG.TRIAL_WORDS - (p.trial_words | 0)) +
            " / " + CFG.TRIAL_WORDS + " words left") +
          "<br>Devices: " + nDev + " / " + m.devices +
          " (synced across your devices)</p>" +
        (deviceLimitHit
          ? '<p class="bad">This device is over your plan limit.</p>'
            + '<button id="aForget" class="ghost">Use only this device</button>'
          : "") +
        '<button id="aOut" class="primary">Sign out</button>';
      var ao = el("aOut");
      if (ao) ao.onclick = function () {
        window.Account.signOut().then(function () {
          el("authModal").style.display = "none";
        });
      };
      var af = el("aForget");
      if (af) af.onclick = function () {
        window.Account.forgetOthers(deviceId()).then(function () {
          deviceLimitHit = false; onAccount();
        });
      };
      return;
    }
    body.innerHTML =
      '<h3 id="authTitle">Create your account</h3>' +
      '<p class="muted">Free. Your plan, trial and devices follow your ' +
      "account across browsers and phones.</p>" +
      '<input id="authEmail" type="email" placeholder="Email" autocomplete="email" />' +
      '<input id="authPw" type="password" placeholder="Password (min 6 chars)" autocomplete="current-password" />' +
      '<button id="authGo" class="primary">Create account</button>' +
      '<div class="authrow">' +
        '<button id="authToggle" class="link">Have an account? Sign in</button>' +
        '<button id="authForgot" class="link">Forgot password</button>' +
      "</div>" +
      '<span id="authMsg" class="cmsg"></span>';
    var mode = "signup";
    el("authToggle").onclick = function () {
      mode = mode === "signup" ? "signin" : "signup";
      el("authTitle").textContent =
        mode === "signup" ? "Create your account" : "Sign in";
      el("authGo").textContent =
        mode === "signup" ? "Create account" : "Sign in";
      el("authToggle").textContent =
        mode === "signup" ? "Have an account? Sign in" : "New here? Create account";
    };
    el("authGo").onclick = function () {
      var em = el("authEmail").value.trim(), pw = el("authPw").value;
      var msg = el("authMsg");
      if (!em || pw.length < 6) {
        msg.textContent = "Enter an email and a 6+ character password.";
        msg.className = "cmsg bad"; return;
      }
      msg.textContent = "Please wait…"; msg.className = "cmsg";
      var op = mode === "signup"
        ? window.Account.signUp(em, pw) : window.Account.signIn(em, pw);
      op.then(function () {
        msg.className = "cmsg good";
        msg.textContent = mode === "signup"
          ? "Account created. If email confirmation is on, check your inbox."
          : "Signed in.";
      }).catch(function (e) {
        msg.className = "cmsg bad";
        msg.textContent = (e && e.message) || "Could not complete that.";
      });
    };
    el("authForgot").onclick = function () {
      var em = el("authEmail").value.trim(), msg = el("authMsg");
      if (!em) { msg.textContent = "Enter your email first."; msg.className = "cmsg bad"; return; }
      window.Account.resetPassword(em).then(function () {
        msg.className = "cmsg good";
        msg.textContent = "If that email exists, a reset link was sent.";
      }).catch(function () {
        msg.className = "cmsg bad"; msg.textContent = "Could not send reset email.";
      });
    };
  }
  function openAuth() {
    renderAuth();
    var m = el("authModal");
    if (m) m.style.display = "flex";
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
    renderAuth();
    ["paywallModal", "checkoutModal", "ownerModal", "authModal"]
      .forEach(closeOnClick);
    var ow = el("ownerLink");
    if (ow) ow.onclick = function (e) { e.preventDefault(); openOwner(); };
    var ac = el("accountLink");
    if (ac) ac.onclick = function (e) { e.preventDefault(); openAuth(); };
    var pwBtn = el("paywallPlans");
    if (pwBtn) pwBtn.onclick = function () {
      el("paywallModal").style.display = "none"; scrollToPricing();
    };
    if (window.Account && window.Account.onChange)
      window.Account.onChange(onAccount);
    // Hidden developer entry: open the site with #dev (or run __dev() in
    // the console). Prompts for DEV_SHA256; no visible button on the page.
    function devHash() {
      if ((location.hash || "").toLowerCase() === "#dev") {
        if (history.replaceState)
          history.replaceState(null, "", location.pathname + location.search);
        tryDevUnlock();
      }
    }
    devHash();
    window.addEventListener("hashchange", devHash);
    window.__dev = tryDevUnlock;
    // iOS-friendly hidden trigger: tap the "AI Humanizer" title 7 times
    // within ~1.2s between taps (no console / URL typing needed).
    var tapEl = document.querySelector("header h1");
    if (tapEl) {
      var taps = 0, last = 0;
      tapEl.addEventListener("click", function () {
        var now = Date.now();
        taps = now - last < 1200 ? taps + 1 : 1;
        last = now;
        if (taps >= 7) { taps = 0; tryDevUnlock(); }
      });
    }
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
