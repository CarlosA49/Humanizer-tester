/* App configuration. Edit the placeholders marked TODO(owner).
 *
 * SECURITY NOTE: this is a no-backend MVP. Everything here ships to the
 * browser, so client-side gating, coupons and the owner password are
 * tamper-resistant but NOT tamper-proof. Real enforcement arrives in the
 * backend phase (server validates payments, coupons and token limits).
 */
window.HUMANIZER_CONFIG = {
  // Free trial allowance (words). One-time per browser.
  TRIAL_WORDS: 500,

  // SHA-256 of the owner password (plaintext is never stored in the repo).
  // To change it later: run in any console:
  //   crypto.subtle.digest('SHA-256', new TextEncoder().encode('NEWPASS'))
  // then hex-encode. Backend phase replaces this with real auth.
  OWNER_SHA256:
    "3a876015b446d7cee4b04f844bbbc6561fb5df33e633f9b894f022d1e0572fec",

  // Coupon signing secret. Used to sign codes in the owner generator and
  // (when accounts are on) verified server-side. The SAME value must be set
  // as `coupon_secret` in private_config in Supabase (see supabase/schema.sql).
  COUPON_SECRET: "hmz-launch-v1-mvp-rotate-with-backend",

  // Free user accounts (Supabase). Leave blank to keep the localStorage-only
  // MVP. To enable: create a free project at https://supabase.com, run
  // supabase/schema.sql in its SQL editor, enable Email auth, then paste:
  //   Project URL  -> SUPABASE_URL
  //   publishable / anon key (safe to ship; protected by row-level
  //   security + SECURITY DEFINER functions) -> SUPABASE_ANON_KEY
  SUPABASE_URL: "https://flsaixowqtqsxrtyztai.supabase.co",
  SUPABASE_ANON_KEY: "sb_publishable_GZjeZ5OsMpMEUPrba_HNcg_HnH9wgW6",


  // Where customer feedback goes. Get a free endpoint at https://formspree.io
  // (create a form, paste its endpoint like https://formspree.io/f/abcdwxyz).
  // If left blank, the form falls back to opening the user's email app.
  FEEDBACK_FORM_ENDPOINT: "", // TODO(owner): paste Formspree endpoint

  // Contact for manual activation + email fallback.
  CONTACT_EMAIL: "carlosimmanuel.robles@gmail.com",

  // Payment instructions shown at checkout (manual activation in the MVP).
  PAYMENTS: {
    // PayMongo hosted payment-link URLs per plan (GCash + cards -> your BPI).
    // Create links at dashboard.paymongo.com and paste the URLs here.
    PAYMONGO_LINKS: {
      starter: "", // TODO(owner)
      pro: "",
      semiannual: "",
      unlimited: "",
      annual: "",
    },
    // International: your personal PayPal QR. Drop the image at
    // docs/payments/paypal-qr.png (you'll send it). Optional PayPal.me link:
    PAYPAL_ME: "https://paypal.me/CarlosImmanuelRobles",
  },

  // Launch pricing (introductory). `was` is the anchor (shown struck through).
  // Amounts in PHP. `period`: mo | 6mo | yr. `devices`: soft limit shown to
  // users; real per-device binding is enforced in the backend phase.
  PLANS: [
    {
      id: "starter", name: "Starter", period: "mo",
      was: 999, now: 499, words: "10,000 words / month",
      devices: 1, best: "Best for trying it on real work",
      perks: ["All 9 tones", "Perplexity • burstiness • lexical", "Works offline"],
    },
    {
      id: "pro", name: "Pro", period: "mo", popular: true,
      was: 1599, now: 799, words: "30,000 words / month",
      devices: 2, best: "Best for regular writers",
      perks: ["Everything in Starter", "3x the words", "Priority new features"],
    },
    {
      id: "semiannual", name: "Pro Semi-Annual", period: "6mo",
      highlight: "Save 2 months",
      was: 4794, now: 3990, words: "30,000 words / month, billed every 6 months",
      devices: 2, best: "Best for steady users who want a deal",
      perks: ["Pro for 6 months", "≈ ₱665 / month", "Cheaper than monthly"],
    },
    {
      id: "annual", name: "Pro Annual", period: "yr", highlight: "Best value",
      was: 9588, now: 6990, words: "30,000 words / month, billed yearly",
      devices: 3, best: "Best overall — lowest monthly cost",
      perks: ["Pro, all year", "≈ ₱582 / month", "3 months free vs monthly"],
    },
    {
      id: "unlimited", name: "Unlimited", period: "mo",
      was: 8999, now: 5000, words: "Unlimited words (fair use)",
      devices: 5, best: "Best for teams & heavy users",
      perks: ["Everything in Pro", "No monthly word cap", "Most devices"],
    },
  ],

  // Hidden plan — never shown on the page. Granted only via an owner-issued
  // code (Owner tools → plan "LIFE", type "FREE"). Redeeming it unlocks
  // full access on the redeeming device.
  CODE_ONLY: {
    lifetime: {
      name: "Lifetime", devices: 3, words: "Pro features — forever",
    },
  },
};
