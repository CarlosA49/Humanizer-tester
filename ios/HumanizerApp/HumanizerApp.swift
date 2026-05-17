import SwiftUI

// Entry point for the native iOS wrapper. This is a thin shell around the
// already-deployed web app (PWA). Build it in Xcode on a Mac; see ../README.md.
@main
struct HumanizerApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .ignoresSafeArea()
        }
    }
}
