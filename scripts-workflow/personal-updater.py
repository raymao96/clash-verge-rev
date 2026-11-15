import argparse
import base64
from datetime import datetime, timezone
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

parser = argparse.ArgumentParser()
parser.add_argument('release')
parser.add_argument('--signature-dir', type=Path)
parser.add_argument('--allow-missing', action='store_true')
parser.add_argument('--allow-draft', action='store_true')
args = parser.parse_args()

with open(args.release, encoding='utf-8') as file:
    release = json.load(file)

config = json.loads((Path(__file__).resolve().parents[1] / 'src-tauri/tauri.conf.json').read_text())
public_key = base64.b64decode(config['plugins']['updater']['pubkey']).decode().splitlines()[1]
key_id = base64.b64decode(public_key)[2:10]

repository = os.environ['GITHUB_REPOSITORY']
tag = release['tag_name']
if repository != 'raymao96/clash-verge-rev' or (release['draft'] and not args.allow_draft) or release['prerelease'] or not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
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
        if not matches and args.allow_missing:
            print(f'Skipping {platform}: asset missing', file=sys.stderr)
            continue
        if len(matches) != 1:
            raise SystemExit(f'Expected one {platform} asset, found {matches}')
        name = matches[0]
        signature = assets.get(name + '.sig')
        if not signature:
            if args.allow_missing:
                print(f'Skipping {platform}: signature missing', file=sys.stderr)
                continue
            raise SystemExit(f'Missing signature for {name}')
        url = assets[name]['browser_download_url']
        sig_url = signature['browser_download_url']
        prefix = f'https://github.com/{repository}/releases/download/{tag}/'
        if release['draft'] and args.signature_dir:
            url = prefix + quote(name, safe='')
            sig_url = prefix + quote(name + '.sig', safe='')
        elif not url.startswith(prefix) or not sig_url.startswith(prefix):
            raise SystemExit(f'Unexpected asset URL for {name}')
        if args.signature_dir:
            sig = (args.signature_dir / (name + '.sig')).read_text().strip()
        else:
            with urlopen(sig_url) as response:
                sig = response.read().decode('utf-8').strip()
        try:
            signature_key_id = base64.b64decode(base64.b64decode(sig).decode().splitlines()[1])[2:10]
        except (ValueError, IndexError, UnicodeDecodeError) as error:
            raise SystemExit(f'Invalid signature for {name}: {error}') from error
        if signature_key_id != key_id:
            raise SystemExit(f'Signature key does not match configured public key: {name}')
        entries[platform] = {'signature': sig, 'url': url}
    if not entries:
        raise SystemExit(f'No signed platforms for {filename}')
    for platform, entry in list(entries.items()):
        if platform.startswith('darwin-'):
            entries[platform + '-app'] = entry
        elif platform.startswith('windows-'):
            entries[platform + '-nsis'] = entry
        elif platform.endswith('-deb'):
            entries[platform[:-4]] = entry
    manifest = {'version': tag[1:], 'notes': release.get('body') or '',
                'pub_date': release['published_at'] or datetime.now(timezone.utc).isoformat(), 'platforms': entries}
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

create_manifest(platforms, 'latest.json')
create_manifest(fixed, 'latest-fixed-webview2.json')
