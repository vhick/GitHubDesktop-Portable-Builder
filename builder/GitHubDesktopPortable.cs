using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

// Community launcher for the Windows GitHub Desktop portable package.
// Keeps Electron settings in Data and routes OAuth browser callbacks through
// this launcher, so the callback inherits the same process-local environment.
// Temporarily claims HKCU URL associations, restores pre-existing keys on exit.
// Do NOT run the inner GitHubDesktop.exe directly. Windows testing is required.
internal static class GitHubDesktopPortable
{
    private const string ProtocolLauncherFlag = "--protocol-launcher";
    private static readonly string[] Schemes = {
        "x-github-desktop-auth", "x-github-client", "github-windows"
    };
    private const string RegistryBase = @"Software\Classes\";
    private const uint SHCNE_ASSOCCHANGED = 0x08000000;

    [DllImport("shell32.dll")]
    private static extern void SHChangeNotify(uint eventId, uint flags, IntPtr item1, IntPtr item2);

    private sealed class SavedValue
    {
        public object Data;
        public RegistryValueKind Kind;
    }
    private sealed class SavedKey
    {
        public readonly Dictionary<string, SavedValue> Values =
            new Dictionary<string, SavedValue>(StringComparer.OrdinalIgnoreCase);
        public readonly Dictionary<string, SavedKey> Children =
            new Dictionary<string, SavedKey>(StringComparer.OrdinalIgnoreCase);
    }

    private sealed class TemporaryProtocols : IDisposable
    {
        private readonly string launcher;
        private readonly string desiredCommand;
        private readonly Dictionary<string, SavedKey> originals =
            new Dictionary<string, SavedKey>(StringComparer.OrdinalIgnoreCase);
        private readonly List<string> claimed = new List<string>();
        private bool disposed;

        public TemporaryProtocols(string launcherPath)
        {
            launcher = launcherPath;
            desiredCommand = "\"" + launcher + "\" " + ProtocolLauncherFlag + " \"%1\"";
            // Snapshot the existing registrations BEFORE GitHub Desktop starts.
            foreach (string scheme in Schemes)
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RegistryBase + scheme, false))
                    originals[scheme] = key == null ? null : Snapshot(key);
            }
        }

        private static SavedKey Snapshot(RegistryKey key)
        {
            var result = new SavedKey();
            foreach (string name in key.GetValueNames())
            {
                result.Values[name] = new SavedValue {
                    Kind = key.GetValueKind(name),
                    Data = key.GetValue(name, null, RegistryValueOptions.DoNotExpandEnvironmentNames)
                };
            }
            foreach (string name in key.GetSubKeyNames())
            {
                using (RegistryKey sub = key.OpenSubKey(name, false))
                    if (sub != null) result.Children[name] = Snapshot(sub);
            }
            return result;
        }

        private static void Restore(RegistryKey target, SavedKey saved)
        {
            foreach (var value in saved.Values)
                target.SetValue(value.Key, value.Value.Data, value.Value.Kind);
            foreach (var child in saved.Children)
                using (RegistryKey sub = target.CreateSubKey(child.Key))
                    Restore(sub, child.Value);
        }

        private static string GetCommand(string scheme)
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(
                RegistryBase + scheme + @"\shell\open\command", false))
                return key == null ? "" : (key.GetValue("") as string ?? "");
        }

        // Wait until ALL protocols are registered. GitHub Desktop registers
        // them sequentially on app.ready. Reacting to the FIRST one lets
        // Electron overwrite our portable handler with the remaining keys.
        public bool AreAllAppHandlersRegistered(string appExe)
        {
            foreach (string scheme in Schemes)
                if (GetCommand(scheme).IndexOf(appExe, StringComparison.OrdinalIgnoreCase) < 0)
                    return false;
            return true;
        }

        public bool AllPointToLauncher()
        {
            foreach (string scheme in Schemes)
                if (!String.Equals(GetCommand(scheme), desiredCommand,
                                   StringComparison.OrdinalIgnoreCase))
                    return false;
            return true;
        }

        // Reclaim only registrations written by this same bundled app.
        // Never override a different application that took ownership later.
        public bool AnyPointToInnerExe(string appExe)
        {
            foreach (string scheme in Schemes)
                if (GetCommand(scheme).IndexOf(appExe, StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
            return false;
        }

        public void Claim()
        {
            foreach (string scheme in Schemes)
            {
                using (RegistryKey root = Registry.CurrentUser.CreateSubKey(RegistryBase + scheme))
                {
                    root.SetValue("", "URL:" + scheme + " Protocol", RegistryValueKind.String);
                    root.SetValue("URL Protocol", "", RegistryValueKind.String);
                }
                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(
                    RegistryBase + scheme + @"\shell\open\command"))
                    key.SetValue("", desiredCommand, RegistryValueKind.String);
                if (!claimed.Contains(scheme)) claimed.Add(scheme);
            }
            SHChangeNotify(SHCNE_ASSOCCHANGED, 0, IntPtr.Zero, IntPtr.Zero);
        }

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            foreach (string scheme in claimed)
            {
                try
                {
                    // Do not revert a handler another application has subsequently claimed.
                    if (!String.Equals(GetCommand(scheme), desiredCommand,
                                       StringComparison.OrdinalIgnoreCase)) continue;
                    Registry.CurrentUser.DeleteSubKeyTree(RegistryBase + scheme, false);
                    SavedKey previous = originals[scheme];
                    if (previous != null)
                        using (RegistryKey key = Registry.CurrentUser.CreateSubKey(RegistryBase + scheme))
                            Restore(key, previous);
                }
                catch (Exception ex)
                {
                    // Never swallow restoration failure silently.
                    MessageBox.Show("Could not restore the original Windows URL association for " +
                        scheme + ". Review this association in Windows Settings.\n\n" + ex.Message,
                        "GitHub Desktop Portable", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
            if (claimed.Count > 0) SHChangeNotify(SHCNE_ASSOCCHANGED, 0, IntPtr.Zero, IntPtr.Zero);
        }
    }

    private static string Quote(string arg)
    {
        if (arg.Length > 0 && arg.IndexOfAny(new char[] { ' ', '\t', '\n', '"' }) < 0)
            return arg;
        var b = new StringBuilder("\"");
        int backslashes = 0;
        foreach (char c in arg)
        {
            if (c == '\\') { backslashes++; continue; }
            if (c == '"')
            {
                b.Append('\\', backslashes * 2 + 1);
                b.Append('"');
                backslashes = 0;
                continue;
            }
            b.Append('\\', backslashes);
            backslashes = 0;
            b.Append(c);
        }
        b.Append('\\', backslashes * 2);
        b.Append('"');
        return b.ToString();
    }

    private static bool IsBrowserCallback(string[] args)
    {
        foreach (string arg in args)
            if (String.Equals(arg, ProtocolLauncherFlag, StringComparison.OrdinalIgnoreCase))
                return true;
        return false;
    }

    private static void CheckCallback(string[] args)
    {
        int recognizedUrls = 0;
        foreach (string arg in args)
        {
            if (arg.Length > 8192) throw new ArgumentException("Overlong browser callback argument");
            foreach (string scheme in Schemes)
                if (arg.StartsWith(scheme + "://", StringComparison.OrdinalIgnoreCase))
                    recognizedUrls++;
        }
        if (recognizedUrls != 1)
            throw new ArgumentException("Unexpected browser callback format");
    }

    [STAThread]
    private static int Main(string[] args)
    {
        Process child = null;
        TemporaryProtocols protocols = null;
        Mutex primaryMutex = null;
        bool acquired = false;
        try
        {
            string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string exe = Path.Combine(root, @"App\GitHubDesktop\GitHubDesktop.exe");
            string appDir = Path.GetDirectoryName(exe);
            string data = Path.Combine(root, "Data");
            string launcher = Assembly.GetExecutingAssembly().Location;
            if (!File.Exists(exe))
                throw new FileNotFoundException("Missing bundled GitHubDesktop.exe", exe);

            bool callback = IsBrowserCallback(args);
            if (callback) CheckCallback(args); // Never log the OAuth callback URL/token.
            if (!callback)
            {
                // Protocol associations are machine-user-wide. Never let two launcher
                // instances compete to manage and restore the same registry keys.
                primaryMutex = new Mutex(false, @"Local\GitHubDesktopPortable_ProtocolOwner");
                try { acquired = primaryMutex.WaitOne(0); }
                catch (AbandonedMutexException) { acquired = true; }
                if (!acquired)
                    throw new InvalidOperationException("A portable GitHub Desktop session is already running. " +
                        "Use its existing window, and close it before launching another copy.");
            }
            foreach (string dir in new[] { "Roaming", "Local", "Home", "Git", "Repositories", "Temp", "Cache" })
                Directory.CreateDirectory(Path.Combine(data, dir));

            var info = new ProcessStartInfo(exe) {
                UseShellExecute = false, WorkingDirectory = appDir
            };
            info.EnvironmentVariables["APPDATA"] = Path.Combine(data, "Roaming");
            info.EnvironmentVariables["LOCALAPPDATA"] = Path.Combine(data, "Local");
            info.EnvironmentVariables["HOME"] = Path.Combine(data, "Home");
            info.EnvironmentVariables["GIT_CONFIG_GLOBAL"] = Path.Combine(data, @"Git\config");
            info.EnvironmentVariables["XDG_CONFIG_HOME"] = Path.Combine(data, @"Home\.config");
            info.EnvironmentVariables["XDG_CACHE_HOME"] = Path.Combine(data, "Cache");
            info.EnvironmentVariables["TEMP"] = Path.Combine(data, "Temp");
            info.EnvironmentVariables["TMP"] = Path.Combine(data, "Temp");
            // Keep the REAL USERPROFILE. Windows credential encryption relies on identity.
            var commandLine = new StringBuilder();
            commandLine.Append(Quote("--user-data-dir=" + Path.Combine(data, @"Roaming\GitHub Desktop")));
            foreach (string a in args) commandLine.Append(' ').Append(Quote(a));
            info.Arguments = commandLine.ToString();

            // Browser callbacks do not take over registry associations: the original
            // launcher remains active while the existing Electron instance receives it.
            if (!callback) protocols = new TemporaryProtocols(launcher);
            child = Process.Start(info);
            if (child == null) throw new InvalidOperationException("Could not start GitHub Desktop");

            if (!callback)
            {
                // GitHub Desktop re-registers its own inner executable on app.ready.
                // Wait for that registration, then override it with the PORTABLE launcher.
                var watch = Stopwatch.StartNew();
                bool observed = false;
                while (watch.ElapsedMilliseconds < 20000 && !child.HasExited)
                {
                    if (protocols.AreAllAppHandlersRegistered(exe)) { observed = true; break; }
                    Thread.Sleep(250);
                }
                if (!observed)
                {
                    if (!child.HasExited)
                    {
                        try { child.Kill(); child.WaitForExit(5000); } catch { }
                    }
                    throw new InvalidOperationException("GitHub Desktop did not register its " +
                        "browser sign-in handler within 20 seconds. Portable login cannot be guaranteed.");
                }
                protocols.Claim();
                if (!protocols.AllPointToLauncher())
                    throw new InvalidOperationException("Portable browser-login registration " +
                        "did not take effect. The app will not continue with nonportable sign-in.");
            }
            // Some Desktop builds can replace their URL handlers again.
            // While the first portable instance is running, restore ONLY
            // handlers switched back to THIS bundled inner application.
            // Unlike a one-time Claim(), this catches later app registrations.
            while (!child.WaitForExit(250))
            {
                if (!callback && protocols != null && protocols.AnyPointToInnerExe(exe))
                {
                    protocols.Claim();
                }
            }
            return child.ExitCode;
        }
        catch (Exception ex)
        {
            MessageBox.Show("Portable launch failed.\n\n" + ex.Message,
                "GitHub Desktop Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        finally
        {
            if (protocols != null) protocols.Dispose();
            if (child != null) child.Dispose();
            if (primaryMutex != null)
            {
                if (acquired) primaryMutex.ReleaseMutex();
                primaryMutex.Dispose();
            }
        }
    }
}
