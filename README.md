# GitHub Desktop Portable Builder — Windows (Community Edition)

**This is a build kit, not the application itself.** Use a standalone GitHub repository and the manual GitHub Actions workflow to create a portable ZIP.

**Initial target:** GitHub Desktop **3.6.7**, the latest confirmed official stable release as of October 18, 2026. **Windows x64** is recommended. ARM64 is only an option when the official release actually provides a Windows ARM64 full `.nupkg` (the 3.6.7 release currently lists x64, not ARM64).

## What this builder actually does

- Downloads the official published stable Windows **full `.nupkg`** from `desktop/desktop` on GitHub Releases. It does *not* need to install GitHub Desktop or compile the huge Electron project from source.
- Accepts **only** the exact stable `release-X.Y.Z` GitHub release tag and expected x64/arm64 `full.nupkg` asset. Rejects previews/betas.
- Verifies the package's SHA-256 checksum against the digest published by the official GitHub Releases API. Version 3.6.7 x64 is also pinned to the verified official SHA-256 (`9790523c...ca9a3`) so a missing API digest does not break the initial build. For other releases a missing digest causes a **safe failure** instead of downloading unverified bytes.
- Extracts the official app program files directly from `lib/net45/` without invoking a Windows installer.
- Compiles a small `GitHubDesktopPortable.exe` using the Windows .NET Framework C# compiler. Extracts the **authentic official icon** from the downloaded GitHub Desktop executable.
- Creates an `App / Data / Other / GitHubDesktopPortable.exe` layout. Sets process-local environment paths to keep main app settings, caches and Git configuration in `Data`, without permanently setting Windows environment variables.
- Ships upstream licensing and version metadata. Keeps builds manual, without an automatic sync or PAF workflow.

## 1. Create the repository (one-time setup)

1. Open https://github.com/new .
2. Repository name: **`GitHubDesktop-Portable-Builder`**.
3. Choose **Public** and leave **Add a README**, **.gitignore**, and **License** set to None/off.
4. Click **Create repository**.

## 2. Add the build kit

1. Download the builder ZIP that came with these instructions, and **Extract All**.
2. Upload these extracted items to the new GitHub repo and commit changes: `builder`, `tests`, `README.md`, `START-HERE.txt`. **Do not upload the ZIP itself.**
3. If you cannot upload `.github` (Windows sometimes hides dot folders), first create a file from the GitHub website using **Add file → Create new file** and this exact file name: `.github/workflows/README.md` . Put `Workflow folder` in its body and commit.
4. On GitHub open `.github` → `workflows` and upload the **individual** `build-github-desktop-portable.yml` file from the extracted ZIP's `.github/workflows`. Commit it.

## 3. Build your portable ZIP

1. Open **Actions** in the builder repository. Enable Actions if GitHub asks for your approval.
2. Select **Build GitHub Desktop Portable ZIP (Manual)**, then click **Run workflow**.
3. Use branch `main`, `release_version: 3.6.7`, `architecture: x64`.
4. Click **Run workflow** again to start the build.
5. After the run finishes successfully (green check mark), open **Artifacts** and download `GitHubDesktopPortable-3.6.7-x64`.
6. Extract that GitHub artifact ZIP, then extract the enclosed `GitHubDesktop-v3.6.7-x64-Portable.zip`.
7. Open the `GitHubDesktopPortable` folder and **only run the root `GitHubDesktopPortable.exe`**. The inner `App/GitHubDesktop/GitHubDesktop.exe` bypasses our portable-data redirection.

The builder can fail if the upstream assets have been renamed, the published GitHub release has no SHA-256 digest, or Windows compilation/packaging requirements change. In that case do not disable verification; check the failed job step.

## Expected structure

```text
GitHubDesktopPortable/
  GitHubDesktopPortable.exe    <-- only start here
  App/
    GitHubDesktop/
      GitHubDesktop.exe
      resources/
      ...bundled application and Git...
    AppInfo/
      appinfo.ini
      appicon.ico              <-- extracted from the OFFICIAL Windows EXE
  Data/                        <-- preserve during ALL updates
    README.txt
    Roaming/GitHub Desktop/     <-- main app preferences, databases and logs, created at first run
    Local/                     <-- isolated Windows-local app data, created at first run
    Git/config                 <-- optional portable Git configuration
    Home/                      <-- home for Git child processes
    Repositories/              <-- optional location to clone your repos
    Cache/
    Temp/
  Other/Source/
    LICENSE.txt
    build-info.txt
```

The ZIP includes empty Data subfolders at first. On subsequent launches `Data` accumulates settings, logs and history. The original ZIP **does not contain any existing user data**, so do not copy its empty `Data` over a populated `Data` during upgrades.

## 4. How to preserve settings when updating

1. **Close GitHub Desktop completely.** Verify it is not running in the Windows Task Manager.
2. Back up your entire `GitHubDesktopPortable/Data` folder. Also back up repositories located elsewhere (they are separate from application settings).
3. Run the **manual builder** for the new official stable release version (only if the builder passes compatibility and checksum verification).
4. Extract the new archive **to a different temporary folder**.
5. In your existing GitHubDesktopPortable folder, delete the **old `App` folder only**.
6. Copy over the **new `App` folder and `GitHubDesktopPortable.exe`**. You may update `Other` too.
7. **Keep the existing `Data` folder untouched**. Never replace it with the new build's empty Data directory.
8. Launch using `GitHubDesktopPortable.exe` and check settings, repo list, Git configuration and push/pull.

**Important:** GitHub Desktop can advertise or initiate its own **Squirrel auto-updates**. Do **not** use any in-app update-and-restart action for this repack: it can create another installation tree under `Data/Local/GitHubDesktop`. Instead use the manual builder update steps above. This builder does not patch or disable the original updater.

## 5. After formatting or reinstalling Windows

1. Keep your full `GitHubDesktopPortable` folder on a separate drive or restore it from a backup.
2. Restore your repository folders as well (prefer `Data/Repositories` if you want everything stored together).
3. Run `GitHubDesktopPortable.exe` and sign in to GitHub again. Windows/DPAPI credentials or system browser protocol registration may not survive a reinstall.
4. Verify Git author name/email and re-select any external editor or tool paths that changed.
5. If GitHub Desktop's repo list points to a previous drive letter, use **File → Add local repository** to reconnect without recloning.

## 6. Limitations — read before claiming full portability

The launcher sets a process-local `APPDATA`, `LOCALAPPDATA`, `HOME`, `GIT_CONFIG_GLOBAL`, `TEMP`, and `XDG` paths. That should redirect the usual application settings and logs; however, **GitHub Desktop has no official portable mode**. On Windows, GitHub Desktop also registers web-browser authentication handlers and can use Windows-specific credential stores and system paths. We deliberately do not overwrite `USERPROFILE` to avoid breaking Windows identity and sign-in.

**Do not assume perfect isolation until Windows testing passes.** Some background Git or browser processes might still use real home folders; built-in updating is not made portable. The official app may register `x-github-desktop-auth`, `x-github-client`, or similar protocol handlers in the Windows registry. We have not modified these behaviors. Browser sign-in may launch the inner executable once and create host-local remnants. This is an honest **same-computer data-preserving portable candidate**, *not yet a verified true-portable build*.

We recommend a before-and-after audit on Windows:

1. Before first launch note contents of `%APPDATA%\GitHub Desktop`, `%LOCALAPPDATA%\GitHubDesktop`, `%USERPROFILE%\.gitconfig`, and relevant `HKCU\Software\Classes\x-github-desktop-auth` keys.
2. Launch the portable EXE, adjust theme and settings, add a local repository, close, reopen. Confirm `Data/Roaming/GitHub Desktop` grows and settings persist.
3. Test browser login, clone, commit, push, fetch and pull. Confirm `Data/Git/config` receives Git author settings if you edit them in the app.
4. Compare Windows AppData folders and registry before and after; repeat after closing. Login callback and Windows-managed records are expected candidates for host changes.
5. Test a manual `App` upgrade while **preserving Data**. Check whether repository list and preferences remain available.
6. Back up everything before changing Windows or testing upgrade behavior.

### Licensing and source

- Official application: https://github.com/desktop/desktop
- Official releases: https://github.com/desktop/desktop/releases
- Official Windows data locations: https://github.com/desktop/desktop/blob/development/docs/installation.md
- Original application copyright belongs to GitHub and its contributors. The official MIT license includes a separate trademark reservation for GitHub's icons/logos. This is an unofficial community packaging experiment, not endorsed by GitHub.

**Verification status:** Offline Python tests passed, and builder kit ZIP contents were checked. The Windows GitHub Actions run, launcher behavior, real settings preservation and authentication have **NOT** been executed or verified yet.
