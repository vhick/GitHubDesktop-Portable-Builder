# GitHub Desktop Portable — Browser Callback Registration Fix

This kit is a **revision of the previous OAuth-portable builder**, based on the read-only diagnostic captured October 18, 2026. **The full Windows authentication test has not yet passed.**

## Why this change exists

The diagnostic showed:
- Primary `GitHubDesktop.exe` was started with `--user-data-dir` by the portable launcher.
- Browser callback started a second main `GitHubDesktop.exe` *without* that argument.
- All three URL handlers (`x-github-desktop-auth`, `x-github-client`, and `github-windows`) were pointing at the inner executable, not the launcher.
- Normal `%APPDATA%\GitHub Desktop` had recent writes.

A concrete defect was found in `TemporaryProtocols.IsAppRegistered`: it returned true as soon as **any one** of the three schemes was registered. GitHub Desktop registers schemes in sequence. This can let our launcher claim too early and have its entry overwritten.

## Changes

1. Wait for **all three** handlers to be registered before taking over.
2. Immediately verify that all three handlers now target the portable launcher.
3. While the portable app is open, check periodically whether **this bundled inner executable** took its handler back, and reclaim those handlers (without overriding a different app).
4. Preserve the existing temporary-registry backup and restore mechanism. Existing `App`, `Data`, and `Other` packaging remains unchanged.
5. Retain private callback checks; do **not** log OAuth URLs or tokens.

## How to update your existing builder

Only **one application-builder file** needs to be replaced:

1. Extract the ZIP.
2. Go to your GitHub repository `GitHubDesktop-Portable-Builder` -> `builder`.
3. Replace `GitHubDesktopPortable.cs` with `builder/GitHubDesktopPortable.cs` from this ZIP. Commit to `main`.
4. Go to Actions -> Build GitHub Desktop Portable ZIP (Manual) -> **Run workflow**. Start a **NEW** run, not re-run of an old commit.
5. Extract the newly created ZIP artifact. Close all GitHub Desktop instances, back up your existing `Data`, and **replace `App` and `GitHubDesktopPortable.exe` while keeping your existing `Data` folder**.
6. Launch `GitHubDesktopPortable.exe` **normally**, never elevated, and try one browser sign-in. Stop if a second GitHub Desktop window appears.

All other files (including the working build workflow) are carried in the full kit only for reference. Replacing the one C# file is sufficient.

## Verification / privacy

These are offline static/unit checks, not proof of Windows behavior. GitHub Desktop and Windows can change protocol associations. Do not delete your host `%APPDATA%\GitHub Desktop` folder yet; it can contain settings from previous tests. Back it up before later cleanup. Credentials stored using Windows protection may require re-login after a Windows reinstall.

If this still produces a second main process, do not keep trying login or running more registry-repair variants. The next approach would need a code-level patch to GitHub Desktop's protocol registration / single-instance behavior rather than merely its external launcher.

Sources:
- https://github.com/desktop/desktop/blob/development/app/src/main-process/main.ts
- https://www.electronjs.org/docs/latest/api/app
