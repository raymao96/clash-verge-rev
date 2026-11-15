import json
import os
import re
import sys
from urllib.request import urlopen

with open(sys.argv[1], encoding='utf-8') as file:
    release = json.load(file)

repository = os.environ['GITHUB_REPOSITORY']
tag = release['tag_name']
if repository != 'raymao96/clash-verge-rev' or release['draft'] or release['prerelease'] or not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
    raise SystemExit('Update manifests require a published personal stable release')

assets = {asset['name']: asset for asset in release['assets']}
platforms = {
    'darwin-x86_64': '_x64.app.tar.gz',
    'darwin-aarch64': '_aarch64.app.tar.gz',
    'windows-x86_64': '_x64-setup.exe',
    'windows-aarch64': '_arm64-setup.exe',
    'linux-x86_64-deb': '_amd64.deb',
    'linux-x86_64-rpm': '.x86_64.rpm',
    'linux-aarch64-deb': '_arm64.deb',
    'linux-aarch64-rpm': '.aarch64.rpm',
    'linux-armv7-deb': '_armhf.deb',
    'linux-armv7-rpm': '.armhfp.rpm',
}
fixed = {
    'windows-x86_64': '_x64_fixed_webview2-setup.exe',
    'windows-aarch64': '_arm64_fixed_webview2-setup.exe',
}

def create_manifest(mapping, filename):
    entries = {}
    for platform, suffix in mapping.items():
        matches = [name for name in assets if name.endswith(suffix)]
        if len(matches) != 1:
            raise SystemExit(f'Expected one {platform} asset, found {matches}')
        name = matches[0]
        signature = assets.get(name + '.sig')
        if not signature:
            raise SystemExit(f'Missing signature for {name}')
        url = assets[name]['browser_download_url']
        sig_url = signature['browser_download_url']
        prefix = f'https://github.com/{repository}/releases/download/{tag}/'
        if not url.startswith(prefix) or not sig_url.startswith(prefix):
            raise SystemExit(f'Unexpected asset URL for {name}')
        with urlopen(sig_url) as response:
            sig = response.read().decode('utf-8').strip()
        if not sig:
            raise SystemExit(f'Empty signature for {name}')
        entries[platform] = {'signature': sig, 'url': url}
    for platform, entry in list(entries.items()):
        if platform.startswith('darwin-'):
            entries[platform + '-app'] = entry
        elif platform.startswith('windows-'):
            entries[platform + '-nsis'] = entry
        elif platform.endswith('-deb'):
            entries[platform[:-4]] = entry
    manifest = {'version': tag[1:], 'notes': release.get('body') or '',
                'pub_date': release['published_at'], 'platforms': entries}
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

create_manifest(platforms, 'latest.json')
create_manifest(fixed, 'latest-fixed-webview2.json')
