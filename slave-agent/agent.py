"""
PRIVUM DNS Manager - Slave Agent

Lightweight HTTP server that runs on slave DNS nodes. Receives zone CRUD
push from the master and applies it to BIND9 by editing named.conf.local
and running rndc reconfig.

On startup, performs full reconciliation by fetching the current zone list
from the master so a slave that was offline still converges.

Copyright (C) 2024-2026 PRIVUM
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import logging
import os
import re
import subprocess
import sys
import threading
from typing import Optional

import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Configuration (loaded from /opt/dns-manager/slave.conf at startup)
# ---------------------------------------------------------------------------
CONF_PATH = "/opt/dns-manager/slave.conf"
TOKEN_PATH = "/opt/dns-manager/slave-agent.token"
BIND_GROUP = "bind"

DEFAULTS = {
    "MASTER_IP": "",
    "MASTER_URL": "",
    "NAMED_CONF_LOCAL": "/etc/bind/named.conf.local",
    "ZONES_DIR": "/var/lib/bind/zones",
    "AGENT_BIND": "0.0.0.0",
    "AGENT_PORT": "5001",
}


def load_conf() -> dict:
    conf = dict(DEFAULTS)
    if os.path.isfile(CONF_PATH):
        with open(CONF_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip().strip('"').strip("'")
    if not conf["MASTER_URL"] and conf["MASTER_IP"]:
        conf["MASTER_URL"] = f"http://{conf['MASTER_IP']}"
    return conf


def load_token() -> str:
    """Shared secret with the master. Generated on master install and
    distributed to slave via /api/slaves/config during slave install."""
    if not os.path.isfile(TOKEN_PATH):
        logging.error("Token file %s missing — slave-agent refusing to start", TOKEN_PATH)
        sys.exit(2)
    with open(TOKEN_PATH) as f:
        return f.read().strip()


CONF = load_conf()
TOKEN = load_token()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("slave-agent")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def authorized() -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    return auth[len("Bearer "):].strip() == TOKEN


# ---------------------------------------------------------------------------
# BIND config helpers
# ---------------------------------------------------------------------------
ZONE_BLOCK_RE = re.compile(
    r'zone\s+"(?P<name>[^"]+)"\s*\{[^}]*\};\s*',
    re.DOTALL,
)


def _read_named_conf() -> str:
    with open(CONF["NAMED_CONF_LOCAL"]) as f:
        return f.read()


def _write_named_conf(content: str) -> None:
    # Atomic write so a partial write doesn't break BIND on the next reconfig
    tmp = CONF["NAMED_CONF_LOCAL"] + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.chmod(tmp, 0o644)
    try:
        import grp
        gid = grp.getgrnam(BIND_GROUP).gr_gid
        os.chown(tmp, 0, gid)
    except Exception:
        pass
    os.replace(tmp, CONF["NAMED_CONF_LOCAL"])


def _named_checkconf() -> tuple[bool, str]:
    r = subprocess.run(
        ["named-checkconf", CONF["NAMED_CONF_LOCAL"]],
        capture_output=True, text=True,
    )
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def _rndc_reconfig() -> tuple[bool, str]:
    r = subprocess.run(["rndc", "reconfig"], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def zone_block(name: str, zone_file: str) -> str:
    return (
        f'\nzone "{name}" {{\n'
        f'    type slave;\n'
        f'    file "{CONF["ZONES_DIR"]}/{zone_file}";\n'
        f'    primaries {{ {CONF["MASTER_IP"]}; }};\n'
        f'    allow-notify {{ {CONF["MASTER_IP"]}; }};\n'
        f'    allow-transfer {{ none; }};\n'
        f'}};\n'
    )


def add_zone(name: str, zone_file: str) -> tuple[bool, str]:
    content = _read_named_conf()
    if re.search(rf'zone\s+"{re.escape(name)}"\s*\{{', content):
        log.info("zone %s already configured, skip", name)
        return True, "already present"
    content = content.rstrip() + "\n" + zone_block(name, zone_file)
    _write_named_conf(content)
    ok, msg = _named_checkconf()
    if not ok:
        log.error("named-checkconf failed after adding %s: %s", name, msg)
        return False, msg
    ok, msg = _rndc_reconfig()
    if not ok:
        log.error("rndc reconfig failed after adding %s: %s", name, msg)
        return False, msg
    log.info("zone %s added", name)
    return True, "added"


def _find_zone_block(content: str, name: str) -> Optional[tuple[int, int]]:
    """Return (start, end) byte offsets of the `zone "NAME" { ... };` block,
    or None if not found. Handles nested braces (primaries {...}, etc.)."""
    header = re.compile(rf'zone\s+"{re.escape(name)}"\s*\{{')
    m = header.search(content)
    if not m:
        return None
    i = m.end()
    depth = 1
    while i < len(content):
        c = content[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                # Consume the closing `};` and trailing whitespace/newline
                end = i + 1
                if end < len(content) and content[end] == ';':
                    end += 1
                while end < len(content) and content[end] in ' \t':
                    end += 1
                if end < len(content) and content[end] == '\n':
                    end += 1
                return (m.start(), end)
        i += 1
    return None


def remove_zone(name: str) -> tuple[bool, str]:
    content = _read_named_conf()
    span = _find_zone_block(content, name)
    if span is None:
        return True, "not present"
    new_content = content[:span[0]] + content[span[1]:]
    _write_named_conf(new_content)
    ok, msg = _named_checkconf()
    if not ok:
        log.error("named-checkconf failed after removing %s: %s", name, msg)
        return False, msg
    ok, msg = _rndc_reconfig()
    if not ok:
        return False, msg
    # Drop the slave zone DB file so BIND fetches a fresh copy if re-added
    zone_path = os.path.join(CONF["ZONES_DIR"], f"db.{name}")
    if os.path.isfile(zone_path):
        try:
            os.unlink(zone_path)
        except OSError:
            pass
    log.info("zone %s removed", name)
    return True, "removed"


# ---------------------------------------------------------------------------
# Boot-time reconciliation
# ---------------------------------------------------------------------------
def reconcile() -> None:
    """Fetch the master's zone list and converge our slave config to it.
    Runs once at startup; recovers from missed pushes while slave was down."""
    url = f"{CONF['MASTER_URL']}/api/slaves/zones"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        master_zones = r.json().get("zones", [])
    except Exception as exc:
        log.warning("reconcile: cannot fetch master zones: %s", exc)
        return

    content = _read_named_conf()
    local = {m.group("name") for m in ZONE_BLOCK_RE.finditer(content)}
    SYSTEM = {"localhost", "127.in-addr.arpa", "0.in-addr.arpa", "255.in-addr.arpa"}

    master_by_name = {
        z["name"]: z.get("file") or f"db.{z['name']}"
        for z in master_zones
        if z.get("type", "master") == "master"
    }

    to_add = set(master_by_name) - local
    to_remove = (local - set(master_by_name)) - SYSTEM

    for name in sorted(to_add):
        ok, msg = add_zone(name, master_by_name[name])
        if not ok:
            log.warning("reconcile add %s failed: %s", name, msg)
    for name in sorted(to_remove):
        ok, msg = remove_zone(name)
        if not ok:
            log.warning("reconcile remove %s failed: %s", name, msg)

    log.info(
        "reconcile done — added=%d removed=%d unchanged=%d",
        len(to_add), len(to_remove), len(local & set(master_by_name)),
    )


def reconcile_async() -> None:
    threading.Thread(target=reconcile, daemon=True).start()


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok"), 200


@app.route("/zones", methods=["POST"])
def http_add_zone():
    if not authorized():
        return jsonify(error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify(error="name required"), 400
    zone_file = data.get("file") or f"db.{name}"
    ok, msg = add_zone(name, zone_file)
    return (jsonify(zone=name, message=msg), 200) if ok else (jsonify(error=msg), 500)


@app.route("/zones/<name>", methods=["DELETE"])
def http_remove_zone(name: str):
    if not authorized():
        return jsonify(error="unauthorized"), 401
    ok, msg = remove_zone(name)
    return (jsonify(zone=name, message=msg), 200) if ok else (jsonify(error=msg), 500)


@app.route("/reconcile", methods=["POST"])
def http_reconcile():
    if not authorized():
        return jsonify(error="unauthorized"), 401
    reconcile_async()
    return jsonify(status="started"), 202


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Wait a moment for the network/named to be up, then reconcile in bg
    threading.Timer(5.0, reconcile_async).start()
    port = int(CONF["AGENT_PORT"])
    bind = CONF["AGENT_BIND"]
    log.info("slave-agent listening on %s:%d", bind, port)
    app.run(host=bind, port=port, threaded=True)
