import sys,zipfile
p=sys.argv[1]
with zipfile.ZipFile(p) as z:
    names=set(z.namelist())
    root='GitHubDesktopPortable/'
    expected={root+'GitHubDesktopPortable.exe',root+'App/GitHubDesktop/GitHubDesktop.exe',root+'App/AppInfo/appicon.ico',root+'App/AppInfo/appinfo.ini',root+'Data/README.txt',root+'Other/Source/build-info.txt',root+'Other/Source/LICENSE.txt'}
    missing=expected-names
    if missing: raise RuntimeError('Missing required package files: '+str(missing))
    if any('GitHubDesktopSetup' in n or n.lower().endswith('.nupkg') for n in names):
        raise RuntimeError('Installer artifacts mistakenly included')
print('Portable ZIP layout verification passed.')
