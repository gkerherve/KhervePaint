# KhervePaint on macOS

The macOS build is produced by GitHub Actions
(`.github/workflows/macos-build.yml`), not on the Windows machine the
installer comes from: PyInstaller cannot cross-compile, so a `.app` has
to be frozen on a Mac. Two native disk images are built each run —
`arm64` on the `macos-14` runner, `x86_64` on `macos-13` — so neither
kind of Mac has to go through Rosetta.

## Building it

Trigger the workflow from the Actions tab, or push a `macos-v*` tag. On a
Mac with the requirements and PyInstaller installed, the same build runs
locally:

```sh
python packaging/build_macos.py
```

That freezes the app, ad-hoc signs it and seals it into
`dist/KhervePaint-<version>-macOS-<arch>.dmg`. There is no installer to
compile and no portable zip: on macOS a drag-install replaces the whole
bundle atomically, and a `.app` already is a copy-and-run folder.

The version is the same git-commit-count string as everywhere else. The
spec writes `khervepaint/VERSION` itself before freezing, so a bundle
always reports the commit it was built from.

## Signed, but not notarized

The bundle is **ad-hoc signed** (`codesign --sign -`). That is not
optional — Apple Silicon refuses to execute an unsigned Mach-O at all —
but it is not the same as Apple notarization, which needs a paid Apple
Developer account.

The practical consequence is that macOS quarantines anything downloaded
through a browser, and an app that is not notarized is refused rather
than merely warned about. Gatekeeper says *"KhervePaint is damaged and
can't be opened"*, which is misleading: nothing is damaged, the app is
simply not notarized. On first launch, right-click the app and choose
**Open**, then **Open** again — or clear the quarantine flag directly:

```sh
xattr -dr com.apple.quarantine /Applications/KhervePaint.app
```

This is the macOS counterpart of the SmartScreen warning the unsigned
Windows installer produces, and it goes away the same way: by paying for
a certificate.

## Known gap: double-click to open

`CFBundleDocumentTypes` is deliberately **not** declared in the bundle.
Claiming `.kpaint` and `.svg` would put KhervePaint in Finder's *Open
With* menu, but macOS delivers a double-clicked file as a
`QFileOpenEvent` rather than in `argv`, and the app only reads `argv`
(`khervepaint/app.py`). The file types will be claimed once that handler
exists; until then, File ▸ Open.
