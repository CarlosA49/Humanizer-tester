import SwiftUI
import WebKit

// The live web app the wrapper loads. Update only if you move the site
// (e.g. to a custom domain).
let kAppURL = URL(string: "https://carlosa49.github.io/Humanizer-tester/")!

struct ContentView: View {
    @State private var isLoading = true
    @State private var failed = false

    var body: some View {
        ZStack {
            Color(red: 0.055, green: 0.067, blue: 0.090).ignoresSafeArea() // #0e1117

            WebView(url: kAppURL, isLoading: $isLoading, failed: $failed)
                .ignoresSafeArea()

            if isLoading && !failed {
                ProgressView("Loading…")
                    .tint(.white)
                    .foregroundStyle(.white)
            }

            if failed {
                VStack(spacing: 12) {
                    Text("No connection")
                        .font(.headline).foregroundStyle(.white)
                    Text("The Humanizer needs the internet on first launch. It works offline afterwards.")
                        .font(.subheadline)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.white.opacity(0.7))
                    Button("Retry") { failed = false; isLoading = true }
                        .buttonStyle(.borderedProminent)
                }
                .padding(32)
            }
        }
    }
}

struct WebView: UIViewRepresentable {
    let url: URL
    @Binding var isLoading: Bool
    @Binding var failed: Bool

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = context.coordinator
        web.allowsBackForwardNavigationGestures = true
        web.scrollView.contentInsetAdjustmentBehavior = .never
        web.isOpaque = false
        web.backgroundColor = .black
        web.load(URLRequest(url: url))
        return web
    }

    func updateUIView(_ web: WKWebView, context: Context) {
        if !isLoading && failed == false && web.url == nil {
            web.load(URLRequest(url: url))
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        let parent: WebView
        init(_ parent: WebView) { self.parent = parent }

        func webView(_ w: WKWebView, didFinish n: WKNavigation!) {
            parent.isLoading = false
        }
        func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) {
            parent.isLoading = false; parent.failed = true
        }
        func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) {
            parent.isLoading = false; parent.failed = true
        }
    }
}
