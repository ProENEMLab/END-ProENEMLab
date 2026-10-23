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

from app_factory import create_app

app = create_app()

if __name__ == "__main__":
    print("API ProENEM Lab -> http://localhost:5000/api")
    app.run(host="127.0.0.1", port=5000, debug=True)
