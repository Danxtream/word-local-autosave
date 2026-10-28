// Copyright (C) 2026 Danxtream.
// Licensed under GPL-3.0-only with an additional term under section 7(b); see LICENSE and NOTICE.md.
import AppKit
import Darwin

func option(_ name: String) -> String? {
    guard let index = CommandLine.arguments.firstIndex(of: name), index + 1 < CommandLine.arguments.count else { return nil }
    return CommandLine.arguments[index + 1]
}
final class WordWatcher {
    let fm = FileManager.default
    let runtime: URL
    let support: URL
    let port: String
    let testState: String?
    var server: Process?
    var observers: [NSObjectProtocol] = []
    var testTimer: Timer?
    var maintenanceTimer: Timer?
    var lastCertificateCheck = Date.distantPast
    var certificatePath: String = ""
    var keyPath: String = ""
    var retry: DispatchWorkItem?
    var signals: [DispatchSourceSignal] = []
    var shuttingDown = false
    var failures = 0
    var starting = false
    init() {
        support = URL(fileURLWithPath: option("--support") ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Local AutoSave Test").path)
        runtime = URL(fileURLWithPath: option("--runtime") ?? support.appendingPathComponent("runtime").path)
        port = option("--port") ?? "43187"
        testState = option("--test-word-state-file")
    }
    var wordRunning: Bool {
        if let path = testState { return (try? String(contentsOfFile: path, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines)) == "open" }
        return NSWorkspace.shared.runningApplications.contains { $0.bundleIdentifier == "com.microsoft.Word" && !$0.isTerminated }
    }
    func status(_ state: String, _ message: String) {
        let payload: [String: Any] = ["state": state, "message": message, "updatedAt": ISO8601DateFormatter().string(from: Date()), "watcherPID": getpid(), "serverPID": server?.processIdentifier ?? 0]
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: support.appendingPathComponent("watcher-status.json"), options: .atomic)
        }
        print("\(state): \(message)"); fflush(stdout)
    }
    func run() {
        let center = NSWorkspace.shared.notificationCenter
        for name in [NSWorkspace.didLaunchApplicationNotification, NSWorkspace.didTerminateApplicationNotification] {
            observers.append(center.addObserver(forName: name, object: nil, queue: .main) { [weak self] note in
                guard let app = note.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication,
                      app.bundleIdentifier == "com.microsoft.Word" else { return }
                self?.failures = 0
                self?.reconcile()
            })
        }
        observers.append(center.addObserver(forName: NSWorkspace.didWakeNotification, object: nil, queue: .main) { [weak self] _ in self?.reconcile() })
        // Test mode substitutes only Word lifecycle detection. It runs the same
        // real server-process management code on a separate test port.
        if testState != nil { testTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in self?.reconcile() } }
        maintenanceTimer = Timer.scheduledTimer(withTimeInterval: 86400, repeats: true) { [weak self] _ in
            guard let self = self, self.wordRunning else { return }
            do {
                if try self.checkCertificates() { self.stop(); self.reconcile() }
            } catch { self.status("certificate-warning", "Renewal failed; existing TLS files kept: \(error.localizedDescription)") }
        }
        maintenanceTimer?.tolerance = 3600
        for number in [SIGTERM, SIGINT] {
            signal(number, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: number, queue: .main)
            source.setEventHandler { [weak self] in self?.shutdown(); exit(0) }
            source.resume(); signals.append(source)
        }
        reconcile()
    }
    func reconcile() {
        guard !shuttingDown else { return }
        if wordRunning {
            if server == nil && retry == nil && !starting { start() }
        } else {
            retry?.cancel(); retry = nil; failures = 0
            if server != nil { stop() }
            else { statusIfWaiting() }
        }
    }
    var waitingReported = false
    func statusIfWaiting() {
        if !waitingReported { status("waiting", "Word is closed; HTTPS server is stopped."); waitingReported = true }
    }
    func start() {
        guard !starting else { return }
        starting = true
        defer { starting = false }
        waitingReported = false
        guard failures < 5 else { return }
        if Date().timeIntervalSince(lastCertificateCheck) > 86400 || certificatePath.isEmpty {
            do { _ = try checkCertificates() }
            catch { failures = 5; status("error", "Certificate check failed: \(error.localizedDescription)"); return }
        }
        guard !shuttingDown, wordRunning else { return }
        guard fm.fileExists(atPath: certificatePath), fm.fileExists(atPath: keyPath) else {
            failures = 5; status("error", "Localhost certificate missing. Open the test app to finish certificate setup."); return
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [runtime.appendingPathComponent("server.py").path, "--root", runtime.appendingPathComponent("web").path, "--cert", certificatePath, "--key", keyPath, "--port", port]
        do {
            let log = support.appendingPathComponent("server.log")
            if !fm.fileExists(atPath: log.path) { fm.createFile(atPath: log.path, contents: nil) }
            let output = try FileHandle(forWritingTo: log); output.seekToEndOfFile()
            process.standardOutput = output; process.standardError = output
            process.terminationHandler = { [weak self] ended in DispatchQueue.main.async {
                guard let self = self, self.server === ended else { return }
                self.server = nil
                guard !self.shuttingDown, self.wordRunning else { self.statusIfWaiting(); return }
                self.failures += 1
                self.status("error", "HTTPS server exited (\(ended.terminationStatus)). See server.log. Retry \(self.failures)/5.")
                guard self.failures < 5 else { return }
                let work = DispatchWorkItem { [weak self] in self?.retry = nil; self?.reconcile() }
                self.retry = work
                DispatchQueue.main.asyncAfter(deadline: .now() + min(pow(2.0, Double(self.failures)), 30), execute: work)
            } }
            try process.run(); server = process
            status("starting", "Word is open; HTTPS server process started. Document save status is shown inside Word.")
        } catch { failures = 5; status("error", "Could not start HTTPS server: \(error.localizedDescription)") }
    }
    func checkCertificates() throws -> Bool {
        certificatePath = support.appendingPathComponent("localhost.crt").path
        keyPath = support.appendingPathComponent("localhost.key").path
        guard fm.fileExists(atPath: support.appendingPathComponent("pki/enabled.json").path) else {
            lastCertificateCheck = Date(); return false
        }
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [runtime.appendingPathComponent("certificates.py").path, "--support", support.path]
        let output = Pipe(); process.standardOutput = output; process.standardError = output
        try process.run()
        let data = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        guard process.terminationStatus == 0,
              let value = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let cert = value["cert"] as? String, let key = value["key"] as? String else {
            throw NSError(domain: "LocalAutoSave", code: 3, userInfo: [NSLocalizedDescriptionKey: String(data: data, encoding: .utf8) ?? "Invalid certificate manager response"])
        }
        certificatePath = cert; keyPath = key; lastCertificateCheck = Date()
        if let warning = value["warning"] as? String, !warning.isEmpty { status("certificate-warning", warning) }
        return value["renewed"] as? Bool ?? false
    }
    func stop() {
        let process = server
        server = nil // Prevent intentional termination from triggering a retry.
        if let process = process, process.isRunning { process.terminate(); process.waitUntilExit() }
        waitingReported = false; statusIfWaiting()
    }
    func shutdown() {
        shuttingDown = true
        retry?.cancel(); retry = nil
        testTimer?.invalidate()
        maintenanceTimer?.invalidate()
        stop()
        status("stopped", "Background watcher stopped.")
    }
}
let watcher = WordWatcher()
watcher.run()
RunLoop.main.run()
