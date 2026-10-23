from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import os
import subprocess

def _venv_python() -> str | None:
    backend = os.path.dirname(os.path.abspath(__file__))
    win = os.path.join(backend, "venv", "Scripts", "python.exe")
    nix = os.path.join(backend, "venv", "bin", "python")
    if os.path.isfile(win):
        return win
    if os.path.isfile(nix):
        return nix
    return None

def _reexec_venv_if_needed() -> None:
    if os.environ.get("PROENEM_SKIP_VENV_REEXEC") == "1":
        return
    target = _venv_python()
    if not target:
        return
    current = os.path.normcase(os.path.abspath(sys.executable))
    wanted = os.path.normcase(os.path.abspath(target))
    if current == wanted:
        return
    if os.path.normcase(os.path.dirname(current)) == os.path.normcase(os.path.dirname(wanted)):
        return
    raise SystemExit(subprocess.call([target, os.path.abspath(__file__), *sys.argv[1:]]))

if __name__ == "__main__":
    _reexec_venv_if_needed()

from flask import abort, send_from_directory

BACKEND = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BACKEND)
FRONTEND = os.path.join(ROOT, "frontend", "public")

if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app_factory import create_app

app = create_app()

def _send_frontend(*parts: str):
    directory = os.path.join(FRONTEND, *parts[:-1]) if len(parts) > 1 else FRONTEND
    filename = parts[-1]
    if os.path.isdir(os.path.join(directory, filename)):
        directory = os.path.join(directory, filename)
        filename = "index.html"
    full = os.path.normpath(os.path.join(directory, filename))
    root = os.path.normpath(directory)
    if not full.startswith(root) or not os.path.isfile(full):
        abort(404)
    return send_from_directory(directory, filename)

@app.get("/sw.js")
def frontend_service_worker():
    response = send_from_directory(FRONTEND, "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.get("/manifest.webmanifest")
def frontend_manifest():
    return send_from_directory(FRONTEND, "manifest.webmanifest")

@app.get("/")
def frontend_index():
    return send_from_directory(FRONTEND, "index.html")

@app.get("/pages/<path:filename>")
def frontend_pages(filename: str):
    return _send_frontend("pages", filename)

@app.get("/assets/<path:filename>")
def frontend_assets(filename: str):
    return _send_frontend("assets", filename)

if __name__ == "__main__":
    print("ProENEM Lab -> http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
