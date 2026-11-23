"""Serve the remote UI and send learned infrared commands to a Broadlink blaster."""

import argparse
import ipaddress
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import broadlink
from broadlink.exceptions import BroadlinkException, ReadError

ROOT = Path(__file__).resolve().parent
CODES = ROOT / "codes.local.json"
KEYS = (
    "power", "mute", "volume_down", "volume_up", "bluetooth", "optical", "aux",
    "rca", "usb", "movie", "dialog", "music", "bass_down", "bass_up",
    "treble_down", "treble_up", "previous", "next",
)
ASSETS = {
    "/": ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/remote.css": ("remote.css", "text/css"),
    "/remote.js": ("remote.js", "text/javascript"),
}


def connect(address):
    device = broadlink.hello(address, timeout=2)
    if not hasattr(device, "send_data") or not device.auth():
        raise ValueError("Could not authenticate with an IR-capable Broadlink device.")
    return device


def load_codes():
    if not CODES.exists():
        return {}
    return {key: bytes.fromhex(value) for key, value in json.loads(CODES.read_text()).items()
            if key in KEYS}


def learn(address, key):
    codes = load_codes()
    device = connect(address)
    device.enter_learning()
    print(f"Point the physical remote at the blaster and press {key}.", flush=True)
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        time.sleep(0.35)
        try:
            packet = device.check_data()
        except ReadError:
            continue
        if packet and packet[0] == 0x26:
            codes[key] = packet
            temporary = CODES.with_suffix(".tmp")
            temporary.write_text(json.dumps({name: data.hex() for name, data in codes.items()}, indent=2))
            temporary.replace(CODES)
            print(f"Learned {key}.")
            return
    raise ValueError("No infrared signal received. Run the learning command again.")


class RemoteHandler(BaseHTTPRequestHandler):
    def respond(self, status, content, mime="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.headers.get("Host") != self.server.authority:
            self.respond(403, b'{"error":"Invalid host"}')
        elif self.path == "/api/status":
            self.respond(200, json.dumps({"learned": sorted(self.server.codes)}).encode())
        elif self.path in ASSETS:
            filename, mime = ASSETS[self.path]
            self.respond(200, (ROOT / "docs" / filename).read_bytes(), mime)
        else:
            self.respond(404, b'{"error":"Not found"}')

    def do_POST(self):
        if self.path != "/api/send":
            self.respond(404, b'{"error":"Not found"}')
            return
        if (self.headers.get("Host") != self.server.authority
                or self.headers.get("Origin") != self.server.origin
                or self.headers.get_content_type() != "application/json"):
            self.respond(403, b'{"error":"Same-origin JSON required"}')
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 128:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            key = payload["key"]
            if not isinstance(key, str):
                raise ValueError("Invalid key")
        except (ValueError, KeyError, TypeError):
            self.respond(400, b'{"error":"Invalid command"}')
            return
        if key not in self.server.codes:
            self.respond(409, b'{"error":"Button has not been learned"}')
            return
        try:
            if self.server.device is None:
                self.server.device = connect(self.server.blaster)
            self.server.device.send_data(self.server.codes[key])
        except (BroadlinkException, OSError, ValueError) as error:
            self.server.device = None
            self.log_error("IR command failed: %s", error)
            self.respond(502, b'{"error":"Blaster transmission failed"}')
            return
        self.respond(200, b'{"sent":true}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blaster", type=ipaddress.IPv4Address, required=True)
    modes = parser.add_subparsers(dest="mode", required=True)
    learn_parser = modes.add_parser("learn")
    learn_parser.add_argument("key", choices=KEYS)
    serve_parser = modes.add_parser("serve")
    serve_parser.add_argument("--listen", type=ipaddress.IPv4Address, default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    try:
        if args.mode == "learn":
            learn(str(args.blaster), args.key)
            return
        if args.listen.is_unspecified:
            parser.error("Use the computer's specific LAN IP for --listen.")
        with HTTPServer((str(args.listen), args.port), RemoteHandler) as server:
            server.timeout = 5
            server.authority = f"{args.listen}:{server.server_port}"
            server.origin = f"http://{server.authority}"
            server.blaster = str(args.blaster)
            server.codes = load_codes()
            server.device = None
            print(f"Open {server.origin}", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return
    except (ValueError, OSError, BroadlinkException) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
