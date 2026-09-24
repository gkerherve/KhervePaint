"""Auto-update: find a newer KhervePaint build and install it.

Two kinds of install, two ways to update:

* **Frozen builds** (Windows installer, macOS .app) look at the GitHub
  releases. Windows and macOS are published as separate releases
  (``v0.1.N`` with ``KhervePaint-Setup-0.1.N.exe``, ``macos-v0.1.N`` with
  ``KhervePaint-0.1.N-macOS-<arch>.dmg``), so "latest release" is not
  enough: we scan the recent releases for the newest asset built for
  *this* platform and compare its build number N with ours. Installing
  downloads it, then runs the Windows installer (and quits so it can
  replace the files) or opens the DMG for the drag to Applications.
* **Source checkouts** (``python KhervePaint.py`` in a git clone) fetch
  the tracking branch and fast-forward it — ``git pull --ff-only``, which
  refuses rather than merging or clobbering local changes.

The network half is plain urllib/subprocess with no Qt, so it is tested
without a window. `UpdateManager` puts it on a worker thread: a silent
check at start-up (at most once a day, Help ▸ Automatically check for
updates) and Help ▸ Check for Updates… on demand.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = "gkerherve/KhervePaint"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases?per_page=20"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
CHECK_INTERVAL = 24 * 3600          # seconds between automatic checks
_ROOT = Path(__file__).resolve().parent.parent

_BUILD_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


# ─────────────────────────────────────────────────────────── versions
def build_number(version: str):
    """The build number N of ``0.1.N[+sha]`` (or of any ``a.b.N`` inside a
    tag or file name), or None."""
    m = _BUILD_RE.search(str(version or ""))
    return int(m.group(3)) if m else None


def current_version() -> str:
    from . import __version__
    return __version__


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_source_checkout() -> bool:
    return not is_frozen() and (_ROOT / ".git").exists()


def platform_key(system=None, machine=None):
    """'windows', 'macos-arm64', 'macos-x86_64' or None (no binaries)."""
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos-arm64" if machine in ("arm64", "aarch64") \
            else "macos-x86_64"
    return None


def asset_matches(name: str, key: str) -> bool:
    name = name.lower()
    if key == "windows":
        return name.startswith("khervepaint-setup") and name.endswith(".exe")
    if key and key.startswith("macos-"):
        arch = key.split("-", 1)[1]
        return name.endswith(f"-macos-{arch}.dmg")
    return False


def newest_asset(releases, key):
    """From a GitHub releases list, the newest downloadable asset for
    platform *key*: ``{"build", "name", "url", "size", "page", "notes"}``
    or None. Drafts and pre-releases are skipped; the build number comes
    from the asset name, falling back to the release tag (the unversioned
    ``KhervePaint-Setup.exe``)."""
    best = None
    for rel in releases or []:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        for asset in rel.get("assets") or []:
            name = asset.get("name", "")
            if not asset_matches(name, key):
                continue
            build = build_number(name) or build_number(rel.get("tag_name"))
            if build is None:
                continue
            versioned = build_number(name) is not None
            rank = (build, versioned)
            if best is None or rank > best[0]:
                best = (rank, {
                    "build": build, "name": name,
                    "url": asset.get("browser_download_url"),
                    "size": asset.get("size", 0),
                    "page": rel.get("html_url") or RELEASES_PAGE,
                    "notes": (rel.get("body") or "").strip(),
                    "tag": rel.get("tag_name", ""),
                })
    return best[1] if best else None


def ssl_context():
    """A verifying TLS context that also works where Python ships without
    CA certificates — the python.org macOS build and frozen apps: certifi
    when it is installed, else the system bundle macOS keeps at
    /etc/ssl/cert.pem. Verification is never switched off."""
    import ssl
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    for bundle in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.isfile(bundle):
            try:
                ctx.load_verify_locations(bundle)
            except Exception:
                pass
    return ctx


def _open(req, timeout):
    if isinstance(req, urllib.request.Request) and \
            req.full_url.startswith("https:"):
        return urllib.request.urlopen(req, timeout=timeout,
                                      context=ssl_context())
    return urllib.request.urlopen(req, timeout=timeout)


def _get_json(url, timeout=10):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "KhervePaint-updater"})
    with _open(req, timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────────────────────── checking
def check(timeout=10) -> dict:
    """Look for an update. Always returns a dict with ``"status"``:

    * ``"update"`` — ``kind`` "binary" (``asset`` …) or "git"
      (``behind`` commits on ``branch``), plus ``current`` / ``latest``;
    * ``"current"`` — already up to date;
    * ``"unsupported"`` — nothing to update from (no binaries for this OS
      and not a git checkout);
    * ``"error"`` — ``message`` says what went wrong (offline, …).
    """
    current = current_version()
    try:
        if is_source_checkout():
            return _check_git(current, timeout)
        key = platform_key()
        if key is None:
            return {"status": "unsupported", "current": current,
                    "message": "No prebuilt downloads for this system — "
                               "update with git pull."}
        asset = newest_asset(_get_json(RELEASES_API, timeout), key)
        mine = build_number(current) or 0
        if asset and asset["build"] > mine:
            return {"status": "update", "kind": "binary", "asset": asset,
                    "current": current, "latest": f"0.1.{asset['build']}"}
        return {"status": "current", "current": current}
    except Exception as exc:                     # offline, rate-limited…
        return {"status": "error", "current": current,
                "message": f"Could not check for updates: {exc}"}


def _git(*args, timeout=60):
    # never block on a credentials prompt from a background thread
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git", *args], cwd=_ROOT, capture_output=True,
                          text=True, timeout=timeout, env=env)


def _check_git(current, timeout):
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    upstream = _git("rev-parse", "--abbrev-ref", "@{u}").stdout.strip()
    if not upstream:
        return {"status": "unsupported", "current": current,
                "message": f"Branch {branch!r} tracks no remote branch."}
    fetch = _git("fetch", "--quiet", timeout=max(timeout, 30))
    if fetch.returncode != 0:
        return {"status": "error", "current": current,
                "message": "git fetch failed: " + fetch.stderr.strip()}
    behind = _git("rev-list", "--count", "HEAD..@{u}").stdout.strip()
    behind = int(behind or 0)
    if behind <= 0:
        return {"status": "current", "current": current}
    log = _git("log", "--oneline", "--no-decorate", "-15",
               "HEAD..@{u}").stdout.strip()
    latest = build_number(current)
    return {"status": "update", "kind": "git", "branch": branch,
            "upstream": upstream, "behind": behind, "current": current,
            "latest": f"0.1.{latest + behind}" if latest else upstream,
            "notes": log}


# ─────────────────────────────────────────────────────────── installing
def download(url, dest: Path, progress=None, timeout=30):
    """Stream *url* to *dest*; *progress(done, total)* after each chunk.
    Written to a ``.part`` file first, so a broken download never looks
    like a finished installer."""
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={
        "User-Agent": "KhervePaint-updater"})
    with _open(req, timeout) as resp, \
            open(part, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress is not None and progress(done, total) is False:
                raise InterruptedError("Download cancelled.")
    if total and done != total:
        raise IOError(f"Download incomplete ({done} of {total} bytes).")
    os.replace(part, dest)
    return dest


def download_dir() -> Path:
    d = Path(tempfile.gettempdir()) / "KhervePaint-update"
    d.mkdir(parents=True, exist_ok=True)
    return d


def launch_installer(path: Path):
    """Start the downloaded installer. Returns True when the app should
    quit so the installer can replace it (Windows)."""
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)                       # noqa: the NSIS wizard
        return True
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])         # mounts the DMG in Finder
        return False
    subprocess.Popen(["xdg-open", path])
    return False


def git_pull():
    """Fast-forward a source checkout. Returns (ok, output)."""
    res = _git("pull", "--ff-only", timeout=120)
    return res.returncode == 0, (res.stdout + res.stderr).strip()


def due(last_check: float, now=None) -> bool:
    now = time.time() if now is None else now
    return not last_check or now - float(last_check) >= CHECK_INTERVAL
