import Cocoa
import FlutterMacOS

class MainFlutterWindow: NSWindow {
  // Store the activity to keep it alive for the app lifetime
  var backgroundActivity: NSObjectProtocol?

  override func awakeFromNib() {
    // Disable App Nap to ensure background scraping/status updates continue
    backgroundActivity = ProcessInfo.processInfo.beginActivity(
        options: [.userInitiated, .latencyCritical, .background],
        reason: "Active Scraping and Downloading"
    )

    let flutterViewController = FlutterViewController()
    let windowFrame = self.frame
    self.contentViewController = flutterViewController
    self.setFrame(windowFrame, display: true)

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()
  }
}
