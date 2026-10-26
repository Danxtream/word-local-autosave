import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var statusLabel: NSTextField!
    var server: Process?
    let fm = FileManager.default
    var support: URL { fm.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Local AutoSave Test", isDirectory: true) }
    var resources: URL { Bundle.main.resourceURL! }
    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Show Local AutoSave", action: #selector(show), keyEquivalent: "0").target = self
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit Local AutoSave Test", action: #selector(quit), keyEquivalent: "q").target = self
        let item = NSMenuItem(); item.submenu = appMenu; menu.addItem(item); NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 590, height: 790), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Local AutoSave · Test v0.1"
        window.isReleasedWhenClosed = false
        let stack = NSStackView(); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 28), stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -28), stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 28)])
        let title = NSTextField(labelWithString: "Local AutoSave"); title.font = .systemFont(ofSize: 28, weight: .bold); stack.addArrangedSubview(title)
        addText("A test add-in for local Word documents. Enable automatic mode once: a small background watcher starts the local server when Word opens and stops it when Word quits. You can then close this setup app.", to: stack)
        button("1. Install Word test add-in", #selector(install), stack)
        button("2. Open localhost certificate in Keychain Access", #selector(certificate), stack)
        addText("In Keychain Access, add the certificate to login. Find Local AutoSave localhost, double-click it, expand Trust, and set Secure Sockets Layer (SSL) to Always Trust. Leave the other trust purposes unchanged. Close the certificate window and authenticate if asked. This certificate is generated only on this Mac.", to: stack, size: 12)
        button("3. Enable automatic server with Word", #selector(start), stack)
        button("Disable automatic server", #selector(disableAutomatic), stack)
        button("4. Enable automatic certificate renewal", #selector(enableRenewal), stack)
        addText("One-time macOS approval is required. Trust is restricted to SSL for localhost; server certificates then renew automatically. Your existing certificate stays in use until setup succeeds.", to: stack, size: 12)
        statusLabel = NSTextField(wrappingLabelWithString: "Automatic mode follows Word after it is enabled. It does not confirm that a document is protected."); stack.addArrangedSubview(statusLabel)
        button("Open installation and testing guide", #selector(guide), stack)
        window.center(); window.makeKeyAndOrderFront(nil)
    }
    func addText(_ text: String, to stack: NSStackView, size: CGFloat = 13) {
        let label = NSTextField(wrappingLabelWithString: text); label.font = .systemFont(ofSize: size)
        label.preferredMaxLayoutWidth = 530; stack.addArrangedSubview(label)
        label.widthAnchor.constraint(equalToConstant: 530).isActive = true
    }
    func button(_ title: String, _ action: Selector, _ stack: NSStackView) {
        let button = NSButton(title: title, target: self, action: action); button.bezelStyle = .rounded; stack.addArrangedSubview(button)
    }
    func alert(_ text: String) { let a = NSAlert(); a.messageText = "Local AutoSave Test"; a.informativeText = text; a.runModal() }
    @objc func show() { window.makeKeyAndOrderFront(nil) }
    @objc func install() {
        do {
            let folder = fm.homeDirectoryForCurrentUser.appendingPathComponent("Library/Containers/com.microsoft.Word/Data/Documents/wef", isDirectory: true)
            try fm.createDirectory(at: folder, withIntermediateDirectories: true)
            let destination = folder.appendingPathComponent("local-autosave-test.xml")
            let data = try Data(contentsOf: resources.appendingPathComponent("manifest.xml"))
            try data.write(to: destination, options: .atomic)
            alert("Installed the test manifest. After certificate setup and starting the server, save your open work and restart Word yourself. Then open a disposable local .docx file and choose Home → Add-ins → Local AutoSave. The app does not close Word or change your documents.")
        } catch { alert("Installation failed: \(error.localizedDescription)") }
    }
    func prepareCertificate() throws {
        try fm.createDirectory(at: support, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        let certificate = support.appendingPathComponent("localhost.crt")
        let key = support.appendingPathComponent("localhost.key")
        if fm.fileExists(atPath: certificate.path) && fm.fileExists(atPath: key.path) { return }
        let configuration = """
        [req]
        distinguished_name=dn
        x509_extensions=extensions
        prompt=no
        [dn]
        CN=Local AutoSave localhost
        [extensions]
        basicConstraints=critical,CA:FALSE
        keyUsage=critical,digitalSignature,keyEncipherment
        extendedKeyUsage=serverAuth
        subjectAltName=DNS:localhost,IP:127.0.0.1
        """
        let config = support.appendingPathComponent("openssl.cnf")
        try configuration.write(to: config, atomically: true, encoding: .utf8)
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/openssl")
        process.arguments = ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "90", "-keyout", key.path, "-out", certificate.path, "-config", config.path]
        process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
        try process.run(); process.waitUntilExit()
        guard process.terminationStatus == 0 else { throw NSError(domain: "LocalAutoSave", code: 1, userInfo: [NSLocalizedDescriptionKey: "Could not generate the localhost certificate."]) }
        try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: key.path)
    }
    @objc func certificate() {
        do { try prepareCertificate(); NSWorkspace.shared.open(support.appendingPathComponent("localhost.crt")) }
        catch { alert(error.localizedDescription) }
    }
    func manageAutomatic(disable: Bool) {
        do {
            if !disable { try prepareCertificate() }
            if let process = server, process.isRunning { process.terminate(); process.waitUntilExit(); server = nil }
            let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            var arguments = [resources.appendingPathComponent("manage-watcher.py").path, "--resources", resources.path]
            if disable { arguments.append("--disable") }
            process.arguments = arguments
            let output = Pipe(); process.standardOutput = output; process.standardError = output
            try process.run(); process.waitUntilExit()
            let message = String(data: output.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            guard process.terminationStatus == 0 else { throw NSError(domain: "LocalAutoSave", code: 2, userInfo: [NSLocalizedDescriptionKey: message]) }
            statusLabel.stringValue = message
        } catch { alert(error.localizedDescription) }
    }
    @objc func start() { manageAutomatic(disable: false) }
    @objc func disableAutomatic() { manageAutomatic(disable: true) }
    @objc func enableRenewal() {
        let notice = NSAlert()
        notice.messageText = "Enable automatic certificate renewal?"
        notice.informativeText = "This creates a private local signing certificate on this Mac and asks macOS to trust it only for SSL connections to localhost. The signing key stays on this Mac. New server certificates are valid for 825 days and renewed 30 days early. The signing certificate lasts approximately 100 years; this intentionally prioritizes convenience for your personal local setup. Your current certificate stays active if setup fails or you cancel."
        notice.addButton(withTitle: "Enable renewal"); notice.addButton(withTitle: "Cancel")
        guard notice.runModal() == .alertFirstButtonReturn else { return }
        statusLabel.stringValue = "Waiting for certificate setup and macOS approval…"
        let manager = resources.appendingPathComponent("certificates.py").path
        let directory = support.path
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = [manager, "--support", directory, "--enable-trust"]
            let output = Pipe(); process.standardOutput = output; process.standardError = output
            do {
                try process.run()
                let data = output.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                let message = String(data: data, encoding: .utf8) ?? "Certificate setup failed."
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    if process.terminationStatus == 0 { self.manageAutomatic(disable: false); self.alert("Automatic renewal is enabled. The local server has been restarted with the renewable certificate. Your documents were not changed.") }
                    else { self.statusLabel.stringValue = "Renewal setup did not complete. Existing certificate kept."; self.alert(message) }
                }
            } catch { DispatchQueue.main.async { self?.alert(error.localizedDescription) } }
        }
    }
    @objc func guide() { NSWorkspace.shared.open(resources.appendingPathComponent("web/help.html")) }
    @objc func quit() { NSApp.terminate(nil) }
    func applicationWillTerminate(_ notification: Notification) { if let process = server, process.isRunning { process.terminate() } }
}
let app = NSApplication.shared
app.setActivationPolicy(.regular)
let delegate = AppDelegate(); app.delegate = delegate
app.run()
