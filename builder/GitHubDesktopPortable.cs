using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Reflection;
using System.Windows.Forms;

// Keeps GitHub Desktop user settings in a portable Data folder without changing
// any global Windows environment variables. Uses the normal Windows account for DPAPI.
internal static class GitHubDesktopPortable {
    static string Quote(string arg) {
        if (arg.Length > 0 && arg.IndexOfAny(new char[]{' ', '\t', '\n', '"'}) < 0) return arg;
        var b = new StringBuilder("\"");
        int bs = 0;
        foreach (char c in arg) {
            if (c == '\\') { bs++; continue; }
            if (c == '"') { b.Append('\\', bs * 2 + 1); b.Append('"'); bs = 0; continue; }
            b.Append('\\', bs); bs = 0; b.Append(c);
        }
        b.Append('\\', bs * 2); b.Append('"');
        return b.ToString();
    }

    [STAThread]
    static int Main(string[] args) {
        try {
            string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string appDir = Path.Combine(root, @"App\GitHubDesktop");
            string exe = Path.Combine(appDir, "GitHubDesktop.exe");
            string data = Path.Combine(root, "Data");
            if (!File.Exists(exe)) {
                MessageBox.Show("Missing App\\GitHubDesktop\\GitHubDesktop.exe. Please extract the complete package.",
                    "GitHub Desktop Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }
            foreach (var sub in new [] {"Roaming", "Local", "Home", "Git", "Repositories", "Temp", "Cache"})
                Directory.CreateDirectory(Path.Combine(data, sub));
            var info = new ProcessStartInfo(exe);
            info.UseShellExecute = false;
            info.WorkingDirectory = appDir;
            info.EnvironmentVariables["APPDATA"] = Path.Combine(data, "Roaming");
            info.EnvironmentVariables["LOCALAPPDATA"] = Path.Combine(data, "Local");
            info.EnvironmentVariables["HOME"] = Path.Combine(data, "Home");
            info.EnvironmentVariables["GIT_CONFIG_GLOBAL"] = Path.Combine(data, @"Git\config");
            info.EnvironmentVariables["XDG_CONFIG_HOME"] = Path.Combine(data, @"Home\.config");
            info.EnvironmentVariables["XDG_CACHE_HOME"] = Path.Combine(data, "Cache");
            info.EnvironmentVariables["TEMP"] = Path.Combine(data, "Temp");
            info.EnvironmentVariables["TMP"] = Path.Combine(data, "Temp");
            // Do not redirect USERPROFILE; Windows identity and credentials depend on it.
            // Electron versions may support this extra switch. APPDATA is primary mechanism.
            var arguments = new StringBuilder();
            arguments.Append(Quote("--user-data-dir=" + Path.Combine(data, @"Roaming\GitHub Desktop")));
            foreach (var arg in args) { arguments.Append(" ").Append(Quote(arg)); }
            info.Arguments = arguments.ToString();
            using (var child = Process.Start(info)) {
                if (child == null) return 3;
                child.WaitForExit();
                return child.ExitCode;
            }
        } catch (Exception ex) {
            MessageBox.Show(ex.ToString(), "GitHub Desktop Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
