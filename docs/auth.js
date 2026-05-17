/* Free user accounts via Supabase (email + password).
 * Profile (plan / trial words / unlock / devices) is the source of truth
 * when signed in and is synced across devices. All mutations go through
 * server-side SECURITY DEFINER functions (see supabase/schema.sql), so the
 * browser cannot tamper with the word count, unlock flag or device list.
 *
 * If Supabase keys are absent the app keeps working as the localStorage MVP.
 */
(function () {
  "use strict";
  var CFG = window.HUMANIZER_CONFIG;
  var sb = null, session = null, profile = null;
  var listeners = [];

  var ready = !!(CFG.SUPABASE_URL && CFG.SUPABASE_ANON_KEY &&
                 window.supabase && window.supabase.createClient);
  if (ready) {
    sb = window.supabase.createClient(CFG.SUPABASE_URL, CFG.SUPABASE_ANON_KEY);
  }

  function emit() { listeners.forEach(function (f) { try { f(); } catch (e) {} }); }
  function signedIn() { return !!(session && session.user); }
  function email() { return signedIn() ? session.user.email : ""; }

  async function refreshProfile() {
    if (!signedIn()) { profile = null; return null; }
    var res = await sb.from("profiles").select("*")
      .eq("id", session.user.id).single();
    profile = res.data || null;
    return profile;
  }

  async function signUp(em, pw) {
    var r = await sb.auth.signUp({ email: em, password: pw });
    if (r.error) throw r.error;
    return r.data;
  }
  async function signIn(em, pw) {
    var r = await sb.auth.signInWithPassword({ email: em, password: pw });
    if (r.error) throw r.error;
    return r.data;
  }
  async function signOut() { await sb.auth.signOut(); }
  async function resetPassword(em) {
    var r = await sb.auth.resetPasswordForEmail(em);
    if (r.error) throw r.error;
  }

  async function consumeWords(n) {
    var r = await sb.rpc("consume_words", { n: Math.max(0, n | 0) });
    if (!r.error && r.data) profile = r.data;
    return profile;
  }
  async function redeemCoupon(code) {
    var r = await sb.rpc("redeem_coupon", { code: code });
    if (r.error) return { ok: false, msg: "Could not reach the server." };
    await refreshProfile();
    return r.data;
  }
  async function registerDevice(device, cap) {
    var r = await sb.rpc("register_device", { device: device, cap: cap });
    if (r.error) {
      if (String(r.error.message || "").indexOf("device_limit_reached") >= 0)
        return { ok: false, limit: true };
      return { ok: false };
    }
    profile = r.data;
    return { ok: true };
  }
  async function forgetOthers(keep) {
    var r = await sb.rpc("forget_other_devices", { keep: keep });
    if (!r.error && r.data) profile = r.data;
    return !r.error;
  }

  if (ready) {
    sb.auth.getSession().then(function (r) {
      session = r.data ? r.data.session : null;
      refreshProfile().then(emit);
    });
    sb.auth.onAuthStateChange(function (_e, s) {
      session = s;
      refreshProfile().then(emit);
    });
  }

  window.Account = {
    ready: ready,
    signedIn: signedIn,
    email: email,
    profile: function () { return profile; },
    onChange: function (f) { listeners.push(f); },
    signUp: signUp, signIn: signIn, signOut: signOut,
    resetPassword: resetPassword,
    consumeWords: consumeWords, redeemCoupon: redeemCoupon,
    registerDevice: registerDevice, forgetOthers: forgetOthers,
  };
})();
