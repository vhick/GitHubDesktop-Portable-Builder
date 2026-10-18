import importlib.util
from pathlib import Path
import unittest
import zipfile
import tempfile
import json

src=Path(__file__).parents[1]/'builder'/'build_portable.py'
spec=importlib.util.spec_from_file_location('build_portable', src)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class BuilderTests(unittest.TestCase):
    def release(self):
        name='GitHubDesktop-3.6.7-x64-full.nupkg'
        return {'tag_name':'release-3.6.7','prerelease':False,'draft':False,'assets':[{'name':name,'digest':'sha256:'+'9790523cad902da2bb695e29125bf0b97142834df9d0434bb5dedbf0705ca9a3','browser_download_url':'https://github.com/desktop/desktop/releases/download/release-3.6.7/'+name}]}
    def test_select(self):
        self.assertTrue(mod.select_asset(self.release(),'3.6.7','x64'))
    def test_reject_beta(self):
        r=self.release();r['prerelease']=True
        with self.assertRaises(ValueError):mod.select_asset(r,'3.6.7','x64')
    def test_pinned_hash_when_api_digest_absent(self):
        r=self.release();r['assets'][0]['digest']=None
        self.assertEqual(mod.select_asset(r,'3.6.7','x64')['digest'], 'sha256:'+mod.PINNED_SHA256[('3.6.7','x64')])
    def test_mismatch_pinned_hash_rejected(self):
        r=self.release();r['assets'][0]['digest']='sha256:'+'a'*64
        with self.assertRaises(ValueError):mod.select_asset(r,'3.6.7','x64')
    def test_reject_wrong_arch(self):
        with self.assertRaises(ValueError):mod.select_asset(self.release(),'3.6.7','arm64')
    def test_windows_launcher_source_path_is_explicit(self):
        # Regression: GitHub Actions previously failed with CSC error CS1504
        # because the source was passed as an ambiguous relative filename.
        build_script = (Path(__file__).parents[1] / 'builder' / 'build_windows.ps1').read_text(encoding='utf-8')
        self.assertIn("Join-Path $PSScriptRoot 'GitHubDesktopPortable.cs'", build_script)
        self.assertIn('Resolve-Path -LiteralPath $launcherSource', build_script)
        self.assertIn(' /reference:System.Windows.Forms.dll $launcherSource', build_script)
        self.assertNotIn("/reference:System.Windows.Forms.dll 'builder/GitHubDesktopPortable.cs'", build_script)
        self.assertTrue((Path(__file__).parents[1] / 'builder' / 'GitHubDesktopPortable.cs').is_file())

    def test_extract(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.nupkg'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('lib/net45/GitHubDesktop.exe',b'MZtest')
                z.writestr('lib/net45/resources/ok',b'ok')
            out=Path(d)/'App'
            mod.extract_app(p,out)
            self.assertEqual((out/'GitHubDesktop.exe').read_bytes(),b'MZtest')
    def test_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.nupkg'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('lib/net45/../../evil.txt',b'bad')
            with self.assertRaises(ValueError):mod.extract_app(p,Path(d)/'App')

if __name__=='__main__':unittest.main()


class PortableOAuthTests(unittest.TestCase):
    def test_browser_callback_uses_portable_launcher(self):
        source = (Path(__file__).parents[1] / 'builder' / 'GitHubDesktopPortable.cs').read_text(encoding='utf-8')
        self.assertIn('x-github-desktop-auth', source)
        self.assertIn('protocols.Claim()', source)
        self.assertIn('ProtocolLauncherFlag = "--protocol-launcher"', source)
        self.assertIn('if (callback) CheckCallback(args)', source)
        self.assertIn('info.EnvironmentVariables["APPDATA"]', source)
        self.assertIn('info.EnvironmentVariables["LOCALAPPDATA"]', source)
        self.assertIn('info.EnvironmentVariables["GIT_CONFIG_GLOBAL"]', source)
        self.assertIn('TemporaryProtocols(launcher)', source)

    def test_registry_cleanup_and_no_oauth_url_logging(self):
        source = (Path(__file__).parents[1] / 'builder' / 'GitHubDesktopPortable.cs').read_text(encoding='utf-8')
        self.assertIn('originals[scheme] = key == null ? null : Snapshot(key);', source)
        self.assertIn('Registry.CurrentUser.DeleteSubKeyTree', source)
        self.assertIn('Restore(key, previous)', source)
        self.assertIn('GetCommand(scheme)', source)
        self.assertIn('if (protocols != null) protocols.Dispose()', source)
        self.assertNotIn('Console.WriteLine(arg)', source)
        self.assertIn('primaryMutex', source)


class BrowserCallbackRegressionTests(unittest.TestCase):
    def test_all_url_handlers_must_finish_registering_before_claim(self):
        code=(Path(__file__).parents[1]/'builder'/'GitHubDesktopPortable.cs').read_text(encoding='utf-8')
        self.assertIn('AreAllAppHandlersRegistered(exe)',code)
        self.assertIn('if (GetCommand(scheme).IndexOf(appExe, StringComparison.OrdinalIgnoreCase) < 0)',code)
        self.assertIn('if (!protocols.AllPointToLauncher())',code)
        self.assertNotIn('if (protocols.IsAppRegistered(exe))',code)
    def test_later_registration_is_reclaimed_without_overriding_other_apps(self):
        code=(Path(__file__).parents[1]/'builder'/'GitHubDesktopPortable.cs').read_text(encoding='utf-8')
        self.assertIn('while (!child.WaitForExit(250))',code)
        self.assertIn('protocols.AnyPointToInnerExe(exe)',code)
        self.assertIn('protocols.Claim();',code)
        self.assertIn('if (!claimed.Contains(scheme)) claimed.Add(scheme);',code)
        self.assertIn('if (protocols != null) protocols.Dispose()',code)
