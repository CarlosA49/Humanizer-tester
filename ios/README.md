# iOS App (App Store) — scaffold & plan

This folder is a **future App Store path**. The free, working-now option is
the **PWA**: open the site in Safari → Share → **Add to Home Screen**. That
already gives an app icon, full‑screen launch, offline use, and delete/re‑add
— no Apple account, no review. See the main README.

The files here turn that same web app into a native wrapper you can submit to
the App Store. **You need a Mac with Xcode and a paid Apple Developer
account** to build/submit it — that part can't be automated from here.

## What's provided

- `HumanizerApp/HumanizerApp.swift` — SwiftUI app entry point.
- `HumanizerApp/ContentView.swift` — full‑screen `WKWebView` that loads the
  live site (`https://carlosa49.github.io/Humanizer-tester/`), with a loading
  state and an offline retry screen. Swipe back/forward enabled.

It's a *thin wrapper*: the actual humanizer logic stays in the web app, so
the iOS app updates automatically whenever the site updates — no resubmission
needed for content changes.

## Prerequisites

1. A **Mac** with the latest **Xcode** (free from the Mac App Store).
2. An **Apple Developer Program** membership — **$99/year**
   (https://developer.apple.com/programs/). Required to put an app on real
   iPhones beyond your own and to use TestFlight / the App Store.
3. The web app live (repo public + GitHub Pages on), or a custom domain.

## Build steps (on the Mac)

1. Xcode → **File ▸ New ▸ Project… ▸ iOS ▸ App**.
   - Product Name: `Humanizer`
   - Interface: **SwiftUI**, Language: **Swift**
   - Set your **Team** (your Apple Developer account) and a unique
     **Bundle Identifier**, e.g. `com.carlosa49.humanizer`.
2. Delete the auto‑generated `ContentView.swift` / `…App.swift` and **drag in**
   the two files from `HumanizerApp/` here.
3. App icon: open **Assets.xcassets ▸ AppIcon** and drop in your
   **1024×1024 PNG** (and the smaller sizes Xcode asks for, or use a single
   1024 with "Single Size"). Use the same artwork you give for the PWA icon.
4. (Optional) Launch screen: set the background to `#0E1117` to match.
5. Run on the Simulator / your iPhone (**Product ▸ Run**).

## Distribute

- **TestFlight (easiest for testers):** Xcode → **Product ▸ Archive** →
  **Distribute App ▸ App Store Connect ▸ Upload**. In App Store Connect add
  testers; they install the **TestFlight** app and your build. Builds expire
  after 90 days. Good for "let people try it" without full review.
- **Public App Store:** same upload, then submit for **App Review** in App
  Store Connect (screenshots, description, privacy info — there's no data
  collection here, declare "Data Not Collected").

## App Review note (important)

Apple guideline **4.2 (Minimum Functionality)** can reject apps that are just
a website. Mitigations already in our favor: the app is a genuine offline
tool (works without a connection after first load via the PWA service
worker), not just a webpage. To be safe you can also add native touches in
the wrapper later (Share sheet for the result, haptics, a native settings
screen). Mention the offline humanizing capability in the review notes.

## Updating

Content/feature changes: just update the website — the app picks them up.
You only resubmit when changing native code, the icon, or app metadata.
