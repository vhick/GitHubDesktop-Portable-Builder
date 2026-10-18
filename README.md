# GitHub Desktop Portable — OAuth/Browser Login Fix (Windows)

**Status: Candidate fix, not a Windows-verified portable release.** This updates the previously successful ZIP builder without replacing your GitHub Desktop application itself. It addresses the missing browser-login handling in the first community launcher.

## What failed and why

When the browser finishes the GitHub OAuth flow, Windows opens a special `x-github-desktop-auth://` URL. The original GitHub Desktop app automatically registers `App\GitHubDesktop\GitHubDesktop.exe` as its handler. Launching that inner EXE directly **does not inherit the portable environment settings**, so it may create `%APPDATA%\GitHub Desktop` and cause duplicate login windows. This behavior is documented in GitHub Desktop's own source and issues.

The corrected portable launcher:

1. Starts the official `GitHubDesktop.exe` using process-local `APPDATA`, `LOCALAPPDATA`, `HOME`, caches, Git config, and temporary paths under `Data`.
2. Waits for the application to register its Windows browser handlers, then temporarily registers the **root `GitHubDesktopPortable.exe`** for `x-github-desktop-auth`, `x-github-client`, and `github-windows`.
3. When the browser sends its callback, launches the application **with the same portable environment and `--protocol-launcher` arguments** so Electron can forward authentication to the running instance.
4. After normal application exit, attempts to restore the earlier `HKCU\Software\Classes` protocol registrations, rather than leaving ours permanently installed.

### Important limitations

- This **temporarily modifies Windows per-user registry associations**. It is **not** a zero-registry-write application. An abrupt Windows shutdown, forced termination, or simultaneous installed GitHub Desktop session can leave a stale registration or conflict. Do not claim forensic zero-remnant portability.
- Windows itself may retain launch history. Some GitHub credential mechanisms and third-party tools may write outside `Data`.
- Do not run as administrator. Close any regular installed GitHub Desktop and all other portable GitHub Desktop copies before testing.
- Never launch `App\GitHubDesktop\GitHubDesktop.exe` directly; it will bypass the portable launcher.
- Automatic self-updates remain unsupported and could cause non-portable writes. Update using a fresh **manual GitHub Actions ZIP**, replacing only `App` and the root launcher and preserving your existing `Data`.
- We have not exercised this build on Windows; the browser sign-in and registry restore **still require real-world verification**.

## Easiest update to your existing GitHub builder

The complete builder ZIP has the same file structure as the previous GitHubDesktop-Portable-Builder-Corrected.zip. **To apply just this fix:**

1. Extract the `GitHubDesktop-OAuth-One-File-Fix.zip` from the downloads.
2. In your GitHubDesktop-Portable-Builder repository, open the `builder` folder.
3. Replace `builder/GitHubDesktopPortable.cs` with the new file.
4. Commit the change to branch `main`.
5. Open **Actions → Build GitHub Desktop Portable ZIP (Manual) → Run workflow**. Start a **NEW** run using `release_version: 3.6.7`, `architecture: x64`. Do not use Re-run on an old failed or successful run, because GitHub re-runs use the old commit.
6. Download the new Actions artifact, extract both ZIP files into a *separate* temporary folder.
7. Close any running GitHub Desktop processes. Back up your current `GitHubDesktopPortable/Data` folder before updating.
8. In the *existing* portable installation, replace the **entire `App` folder** and **`GitHubDesktopPortable.exe`**, but keep the existing `Data` folder untouched. (You may update `Other` too.)
9. Run **only the root `GitHubDesktopPortable.exe`** as a normal Windows user, without Run as administrator.

## First authentication test

1. Close any previously opened GitHub Desktop. Make sure only your new portable copy will be running.
2. Do not delete any `%APPDATA%\GitHub Desktop` folder yet. It might contain account data from the earlier failed test or from an installed version.
3. Launch `GitHubDesktopPortable.exe`. Wait until the sign-in page appears.
4. Click Sign in and approve once in the browser. The login link should route through the root portable launcher, not the inner EXE.
5. Confirm GitHub Desktop actually displays your GitHub account in Options → Accounts.
6. Change a theme or preference, close the app fully, and relaunch. Check the preference persists.
7. Verify settings and logs are being updated under `GitHubDesktopPortable\Data\Roaming\GitHub Desktop`. A newly created `%APPDATA%\GitHub Desktop` folder or another login loop means this version still is not fully portable: stop using it and share diagnostic information **without sharing the actual OAuth callback URL, tokens, or credentials**.
8. After a normal app exit, the temporary browser URL handler should be restored to its previous state. If Windows was interrupted, the association may require manual repair; see Windows Settings > Apps > Default apps or the official GitHub Desktop installer.

## Included files

- `.github/workflows/build-github-desktop-portable.yml` — existing manual ZIP workflow; unchanged.
- `builder/GitHubDesktopPortable.cs` — **updated**, carries login callback through portable environment and temporary registry integration.
- `builder/build_windows.ps1` — existing corrected C# compilation path; unchanged.
- `builder/build_portable.py`, `builder/verify_zip.py` — existing pinned-release packaging and archive checks; unchanged.
- `tests/test_builder.py` — two additional **static checks** for OAuth routing and restoration logic.
- `README.md`, `START-HERE.txt` — revised instructions.

Offline tests pass but **cannot validate the Windows login flow or registry cleanup**. Real Windows verification is required.

## References

- https://github.com/desktop/desktop/issues/22325 — official issue explaining `x-github-desktop-auth://` redirects and single-instance handoff.
- https://github.com/desktop/desktop/blob/development/app/src/main-process/main.ts — main-process protocol registrations.
- https://www.electronjs.org/docs/latest/tutorial/launch-app-from-url-in-another-app — Electron custom protocol behavior.
- https://github.com/desktop/desktop/blob/development/docs/installation.md — Windows user-data directories.

Community repack, not endorsed by GitHub. Respect the upstream software license and trademark restrictions.
