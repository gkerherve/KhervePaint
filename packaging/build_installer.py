"""Package the built app into a setup.exe and a portable .zip.

Assumes the PyInstaller one-folder build already exists at
``dist/KhervePaint`` (run ``pyinstaller packaging/KhervePaint.spec
--noconfirm`` first). Produces, in ``dist/``:

* ``KhervePaint-Setup-<version>.exe`` — an NSIS per-user installer
  (Start Menu + Desktop shortcuts, uninstaller). Needs ``makensis``.
* ``KhervePaint-<version>-portable.zip`` — the same folder zipped, for
  people who would rather copy-and-run than install.

    python packaging/build_installer.py

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import re
import shutil
import subprocess
import sys
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_DIST = os.path.join(_ROOT, "dist")
_APPDIR = os.path.join(_DIST, "KhervePaint")


def write_version() -> str:
    """Write ``khervepaint/VERSION`` from git; return the numeric part.

    The file holds the full ``0.1.N+sha`` string (what the title bar and
    the About box show); the number alone names the artifacts and the tag.

    The previous build's ``VERSION`` is deleted before resolving, because
    ``get_version()`` reads that file *first* — it has to, so the frozen
    app can report a version with no ``.git`` beside it. Left in place it
    answers with the version it was written for, and every later build
    ships the first one's number. That is not hypothetical: v0.1.139 was
    published from a tree at commit ~150 and labelled 139 because this
    file was stale.

    Called from ``KhervePaint.spec`` rather than from ``main()`` here, so
    the stamp is correct whichever way the freeze is started — the
    documented flow runs PyInstaller *before* this module.
    """
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from khervepaint._version import get_version

    version_file = os.path.join(_ROOT, "khervepaint", "VERSION")
    if os.path.exists(version_file):
        os.remove(version_file)
    get_version.cache_clear()
    full = get_version()
    if full == "0.1.0":
        raise SystemExit(
            "refusing to build: version resolved to the 0.1.0 placeholder — "
            "is this a git checkout with git on PATH?")
    with open(version_file, "w", encoding="utf-8") as fh:
        fh.write(full + "\n")
    return re.match(r"[0-9.]+", full).group(0)


def _version() -> str:
    """The numeric app version (``0.1.N``), dropping the +sha suffix
    that would be illegal in a filename / VIProductVersion.

    Re-resolves rather than reading the file the spec just wrote: the git
    state cannot have moved between the freeze and here, so the answer is
    the same, and a stale file can never leak into an artifact name."""
    return write_version()


def _find_makensis():
    exe = shutil.which("makensis")
    if exe:
        return exe
    for base in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files")):
        cand = os.path.join(base, "NSIS", "makensis.exe")
        if os.path.isfile(cand):
            return cand
    return None


def build_zip(version: str) -> str:
    """Zip dist/KhervePaint so its top-level entry is ``KhervePaint/``."""
    out = os.path.join(_DIST, f"KhervePaint-{version}-portable.zip")
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6) as zf:
        for root, _dirs, files in os.walk(_APPDIR):
            for name in files:
                full = os.path.join(root, name)
                arc = os.path.join("KhervePaint",
                                   os.path.relpath(full, _APPDIR))
                zf.write(full, arc)
    return out


def build_installer(version: str) -> str:
    makensis = _find_makensis()
    if makensis is None:
        raise SystemExit(
            "makensis not found — install NSIS (https://nsis.sourceforge.io) "
            "or add it to PATH.")
    out = os.path.join(_DIST, f"KhervePaint-Setup-{version}.exe")
    cmd = [
        makensis,
        f"/DAPP_VERSION={version}",
        f"/DSRC_DIR={_APPDIR}",
        f"/DOUT_FILE={out}",
        f"/DLICENSE_FILE={os.path.join(_ROOT, 'LICENSE')}",
        f"/DICON_FILE={os.path.join(_HERE, 'khervepaint.ico')}",
        os.path.join(_HERE, "installer.nsi"),
    ]
    subprocess.run(cmd, check=True)
    return out


def main():
    if not os.path.isfile(os.path.join(_APPDIR, "KhervePaint.exe")):
        raise SystemExit(
            "dist/KhervePaint/KhervePaint.exe not found — run "
            "`pyinstaller packaging/KhervePaint.spec --noconfirm` first.")
    version = _version()
    print(f"KhervePaint {version}")
    zip_path = build_zip(version)
    print("wrote", zip_path,
          f"({os.path.getsize(zip_path) / 1e6:.0f} MB)")
    exe_path = build_installer(version)
    print("wrote", exe_path,
          f"({os.path.getsize(exe_path) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
