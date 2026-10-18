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
