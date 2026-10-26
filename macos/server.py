"""Loopback-only static HTTPS server. No document I/O or upload endpoints."""
import argparse
import http.server
import pathlib
import ssl
import urllib.parse

ASSETS = {'taskpane.html', 'style.css', 'engine.js', 'office-host.js', 'taskpane.js',
          'icon-16.png', 'icon-32.png', 'icon-80.png', 'help.html'}

def make_handler(root):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            name = urllib.parse.urlsplit(self.path).path.lstrip('/')
            if name == 'health':
                data, kind = b'Local AutoSave v0.1', 'text/plain'
            elif name in ASSETS:
                file = root / name
                if not file.is_file():
                    self.send_error(404)
                    return
                data = file.read_bytes()
                kind = {'.html':'text/html; charset=utf-8', '.js':'application/javascript',
                        '.css':'text/css', '.png':'image/png'}[file.suffix]
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, *_):
            pass
    return Handler

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--cert', required=True)
    parser.add_argument('--key', required=True)
    parser.add_argument('--port', type=int, default=43187)
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(args.root))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.cert, args.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print('Local AutoSave HTTPS listening on 127.0.0.1:' + str(args.port), flush=True)
    # Process termination is signal-driven; no frequent shutdown-flag polling.
    server.serve_forever(poll_interval=30)
