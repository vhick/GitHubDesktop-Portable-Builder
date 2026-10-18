# GitHub Desktop Portable Builder — Final Consolidated Kit

**What this is:** the complete source for the user's successfully tested GitHub Desktop portable ZIP builder. This is **not** the application executable. Upload these builder files to your existing GitHub repository and run the manual GitHub Action to generate a portable app ZIP. The package contains the final October 18, 2026 browser-login callback fix.

**Important status:** The user confirmed on Windows that the final browser-login fix works. The offline test suite passes 12 tests. No claim is made that all Windows-managed traces or temporary registry registrations are absent in every situation.

## Contents

```text
.github/workflows/build-github-desktop-portable.yml
builder/GitHubDesktopPortable.cs   (FINAL browser-login fix)
builder/build_portable.py          (download and verify official Windows release)
builder/build_windows.ps1          (compile launcher and make ZIP)
builder/verify_zip.py             (check packaged layout)
tests/test_builder.py             (12 offline regression tests)
README.md
START-HERE.txt
```

No PAF workflow, no old versions, no login diagnostic, no installers. The GitHub workflow is **manual only**, not automatic.

## If you already have a working builder

You do **not** need a new repository or another build to keep your current application working. This ZIP is your **complete backup** of the successful builder source.

To update your builder repository from this backup:

1. Extract this ZIP on Windows.
2. Open your existing `GitHubDesktop-Portable-Builder` repository on GitHub.
3. Replace the files in `builder/` and `tests/` with the matching files in this kit. Keep the exact names.
4. Replace `.github/workflows/build-github-desktop-portable.yml` with the matching workflow file in this kit.
   - If your browser will not upload a folder starting with a dot, open `.github/workflows` **inside GitHub** and upload only the YAML file. No new folder needs to be uploaded.
5. Replace `README.md` and `START-HERE.txt` if you want the up-to-date documentation.
6. Commit changes to your default branch (usually `main`).
7. In **Actions**, select **Build GitHub Desktop Portable ZIP (Manual)** -> **Run workflow**. Run a **new** build; do not re-run an old failed run because re-runs use the old commit.
8. Use version `3.6.7` and architecture `x64` for the previously verified source version. Newer releases require their own compatibility test.
9. After a green checkmark, download the artifact, extract the GitHub ZIP wrapper and then the portable ZIP itself.

**If this repository is already up to date, you may skip these upload steps.**

## Expected portable application ZIP (after GitHub Actions succeeds)

```text
GitHubDesktopPortable/
├── GitHubDesktopPortable.exe     <- always launch this
├── App/
│   ├── GitHubDesktop/          <- program files
│   └── AppInfo/                <- app metadata and official-app icon
├── Data/                       <- KEEP during updates
│   ├── Roaming/
│   ├── Local/
│   ├── Git/
│   ├── Home/
│   ├── Repositories/
│   ├── Cache/
│   ├── Temp/
│   └── README.txt
└── Other/Source/               <- source and license information
```

GitHub Desktop's icon is extracted from its official executable. The launcher temporarily handles GitHub Desktop's browser login protocol registration and restores earlier registrations when it exits normally. Authentication uses Windows-specific credentials; logging in again after formatting Windows is expected.

## Safe application updates

1. **Close all GitHub Desktop windows and background processes.**
2. **Make a backup of your existing `Data` folder**, including any local repositories stored in `Data/Repositories`.
3. Build the desired official stable release using a NEW GitHub Actions run. The workflow checks the release asset's SHA-256 before packaging. Changes to the upstream executable can require further testing.
4. Extract the fresh app ZIP into a *different* folder.
5. In your **existing** portable installation, replace `App/` and `GitHubDesktopPortable.exe` from the new version. Do not replace/delete `Data/`.
6. Launch the root `GitHubDesktopPortable.exe`. Confirm that settings, saved repositories and Git operations remain available.

Cloned repositories **outside** the portable folder are not automatically included in `Data` and must be backed up separately. Absolute repository paths may need checking after moving folders/drives.

## Caveats

- This is an unofficial community repack; the official project is https://github.com/desktop/desktop .
- The browser callback fix is confirmed by the user on their Windows computer, not independently tested on other computers or all releases.
- The launcher makes **temporary per-user Windows URL protocol registrations** for browser sign-in. An abnormal shutdown may leave a registration behind. It is therefore not a guarantee of zero Windows registry traces.
- Git credentials may rely on Windows protection and may require a fresh login after reinstalling Windows.
- This builder only generates a ZIP, **not** a `.paf.exe`. The workflow does not build or upload automatically.
- Do not open the inner `App/GitHubDesktop/GitHubDesktop.exe` directly. That bypasses the portable launcher and can write to host `%APPDATA%`.
- Existing `%APPDATA%/GitHub Desktop` content from older tests should not be deleted without reviewing/backing it up.

## References

- Official source: https://github.com/desktop/desktop
- GitHub Actions manual workflows: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
