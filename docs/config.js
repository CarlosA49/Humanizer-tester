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

  // Coupon signing secret. MVP-only: visible in client code, so coupons are
  // forgeable by a determined user until the backend validates them.
  // Changing this invalidates previously issued codes.
  COUPON_SECRET: "hmz-launch-v1-mvp-rotate-with-backend",

  // Where customer feedback goes. Get a free endpoint at https://formspree.io
  // (create a form, paste its endpoint like https://formspree.io/f/abcdwxyz).
  // If left blank, the form falls back to opening the user's email app.
  FEEDBACK_FORM_ENDPOINT: "", // TODO(owner): paste Formspree endpoint

  // Contact for manual activation + email fallback.
  CONTACT_EMAIL: "you@example.com", // TODO(owner): your email

  // Payment instructions shown at checkout (manual activation in the MVP).
  PAYMENTS: {
    // PayMongo hosted payment-link URLs per plan (GCash + cards -> your BPI).
    // Create links at dashboard.paymongo.com and paste the URLs here.
    PAYMONGO_LINKS: {
      starter: "", // TODO(owner)
      pro: "",
      unlimited: "",
      annual: "",
      lifetime: "",
    },
    // International: your personal PayPal QR. Drop the image at
    // docs/payments/paypal-qr.png (you'll send it). Optional PayPal.me link:
    PAYPAL_ME: "", // e.g. https://paypal.me/yourname  TODO(owner)
  },

  // Launch pricing (introductory). `was` is the anchor (shown struck through).
  // Amounts in PHP. `period`: mo | yr | once.
  PLANS: [
    {
      id: "starter", name: "Starter", period: "mo",
      was: 999, now: 499, words: "25,000 words / month",
      perks: ["All 9 tones", "Perplexity • burstiness • lexical", "Works offline"],
    },
    {
      id: "pro", name: "Pro", period: "mo", popular: true,
      was: 1599, now: 799, words: "100,000 words / month",
      perks: ["Everything in Starter", "4x the words", "Priority new features"],
    },
    {
      id: "unlimited", name: "Unlimited", period: "mo",
      was: 2999, now: 1499, words: "Unlimited (fair use)",
      perks: ["Everything in Pro", "No monthly word cap", "Best for heavy users"],
    },
    {
      id: "annual", name: "Pro Annual", period: "yr", highlight: "Best value",
      was: 15990, now: 7990, words: "100,000 words / month, billed yearly",
      perks: ["Pro, all year", "≈ ₱666 / month", "2+ months free vs monthly"],
    },
    {
      id: "lifetime", name: "Lifetime", period: "once", highlight: "Pay once",
      was: 19999, now: 9999, words: "Pro features — forever",
      perks: ["One payment, no renewals", "All future updates", "Founder supporter"],
    },
  ],
};
