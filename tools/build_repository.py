#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build an explicit Kodi package index from local files; no network or Git writes."""
from copy import deepcopy
import hashlib
from html import escape
import io
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'repository.marbra00_repo'
SITE = ROOT / 'docs'
BASE = 'https://marbra00.github.io/marbra00_repo/'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def immutable_write(path, content):
    if path.exists():
        require(path.read_bytes() == content, 'Existing version differs: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)


def package_source(source):
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob('*')):
            if not path.is_file():
                continue
            require(not path.is_symlink(), 'Source contains a symbolic link.')
            require(not {'.git', '__pycache__'}.intersection(path.relative_to(source).parts)
                    and path.suffix.lower() not in {'.pyc', '.pyo', '.log'}, 'Unexpected source file.')
            entry = ZipInfo((Path(source.name) / path.relative_to(source)).as_posix(),
                            date_time=(2026, 10, 10, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes(), compresslevel=9)
    return buffer.getvalue()


def inspect_package(content):
    with ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        require(names and len(names) == len(set(names)), 'Empty package or duplicate ZIP paths.')
        for entry in entries:
            path = PurePosixPath(entry.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in entry.filename
                    and ':' not in entry.filename, 'Unsafe ZIP path.')
            require(entry.filename.rstrip('/') == path.as_posix(), 'Non-canonical ZIP path.')
            require((entry.external_attr >> 16) & 0o170000 != 0o120000, 'ZIP contains a symbolic link.')
        roots = {PurePosixPath(name).parts[0] for name in names}
        require(len(roots) == 1, 'Package must have one addon root folder.')
        addon_id = roots.pop()
        require(re.fullmatch(r'[a-z0-9_.-]+', addon_id) is not None, 'Invalid addon ID.')
        require(addon_id + '/addon.xml' in names, 'Missing addon.xml.')
        require(archive.testzip() is None, 'ZIP integrity check failed.')
        addon = ET.fromstring(archive.read(addon_id + '/addon.xml'))
        require(addon.tag == 'addon' and addon.get('id') == addon_id, 'Folder and addon ID differ.')
        require(all(addon.get(key) for key in ('version', 'name', 'provider-name')), 'Missing addon metadata.')
        require(re.fullmatch(r'[0-9A-Za-z._~+-]+', addon.get('version')) is not None, 'Invalid version.')
        require(addon.find("extension[@point='xbmc.addon.metadata']") is not None, 'Missing Kodi metadata.')
        for asset in addon.findall("extension[@point='xbmc.addon.metadata']/assets/*"):
            require(asset.text is not None, 'Empty artwork path.')
            asset_path = PurePosixPath(asset.text)
            require(not asset_path.is_absolute() and '..' not in asset_path.parts
                    and '\\' not in asset.text and ':' not in asset.text,
                    'Unsafe artwork path.')
            require(addon_id + '/' + asset.text in names, 'Declared artwork is missing.')
        return addon, {name[len(addon_id) + 1:]: archive.read(name) for name in names
                      if name.startswith(addon_id + '/') and not name.endswith('/')}


def build(root=ROOT):
    source = root / SOURCE.name
    site = root / 'docs'
    repository_bytes = package_source(source)
    repository, _ = inspect_package(repository_bytes)
    require(repository.get('id') == SOURCE.name and repository.get('name') == 'marbra00_repo',
            'Repository identity differs.')
    repo_dir = repository.find("extension[@point='xbmc.addon.repository']/dir")
    require(repo_dir is not None and repo_dir.findtext('info') == BASE + 'addons.xml'
            and repo_dir.findtext('checksum') == BASE + 'addons.xml.sha256'
            and repo_dir.find('checksum').get('verify') == 'sha256'
            and repo_dir.findtext('datadir') == BASE, 'Repository URLs differ.')
    require((source / 'LICENSE').read_bytes() == (root / 'LICENSE').read_bytes(), 'Repository licence differs.')
    selected = [(repository, repository_bytes, None)]
    selected_ids = {repository.get('id')}
    for item in json.loads((root / 'packages.json').read_text(encoding='utf-8')):
        path = (root / item['path']).resolve()
        require(site.resolve() in path.parents and path.suffix == '.zip', 'Package must be a ZIP inside docs/.')
        content = path.read_bytes()
        require(hashlib.sha256(content).hexdigest() == item['sha256'], 'Selected package checksum differs.')
        require(item.get('source', '').startswith('https://'), 'Package source link is missing.')
        addon, _ = inspect_package(content)
        require(addon.get('id') not in selected_ids, 'Duplicate selected addon ID.')
        selected_ids.add(addon.get('id'))
        expected = site / addon.get('id') / (addon.get('id') + '-' + addon.get('version') + '.zip')
        require(path == expected.resolve(), 'Package filename does not match addon ID and version.')
        selected.append((addon, content, item['source']))

    # Validate every package before writing index files or publishing any ZIP.
    root_xml = ET.Element('addons')
    records = []
    rows = []
    for addon, content, source_url in selected:
        addon_id, version = addon.get('id'), addon.get('version')
        folder = site / addon_id
        filename = addon_id + '-' + version + '.zip'
        digest = hashlib.sha256(content).hexdigest()
        immutable_write(folder / filename, content)
        immutable_write(folder / (filename + '.sha256'), (digest + '\n').encode('ascii'))
        _, files = inspect_package(content)
        # Artwork remains at the paths declared in addon.xml, relative to the addon folder.
        for asset in addon.findall("extension[@point='xbmc.addon.metadata']/assets/*"):
            asset_target = folder / asset.text
            asset_target.parent.mkdir(parents=True, exist_ok=True)
            asset_target.write_bytes(files[asset.text])
        if 'changelog.txt' in files:
            immutable_write(folder / ('changelog-' + version + '.txt'), files['changelog.txt'])
        root_xml.append(deepcopy(addon))
        records.append({'id': addon_id, 'version': version, 'sha256': digest,
                        'zip': (folder / filename).relative_to(root).as_posix(), 'source': source_url})
        rows.append('<tr><td>' + escape(addon.get('name')) + '</td><td>' + escape(version) +
                    '</td><td><a href="' + escape(addon_id + '/' + filename, quote=True) + '">ZIP</a></td></tr>')
    ET.indent(root_xml, space='    ')
    xml_bytes = ET.tostring(root_xml, encoding='utf-8', xml_declaration=True) + b'\n'
    site.mkdir(parents=True, exist_ok=True)
    (site / '.nojekyll').write_bytes(b'')
    (site / 'addons.xml').write_bytes(xml_bytes)
    (site / 'addons.xml.sha256').write_bytes((hashlib.sha256(xml_bytes).hexdigest() + '\n').encode('ascii'))
    page = '''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>marbra00_repo – Kodi Repository</title>
<style>body{max-width:48rem;margin:3rem auto;padding:0 1rem;font:1rem/1.6 system-ui,sans-serif;color:#172634;background:#f7fafc}a{color:#075985}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.75rem;border-bottom:1px solid #cbd5e1}code{overflow-wrap:anywhere}section{margin:2rem 0}</style>
</head><body><h1>marbra00_repo</h1>
<p>Kodi-Repository für Addons und Updates. / Kodi repository for addons and updates.</p>
<section><h2>Installation</h2><p>Repository-ZIP herunterladen und in Kodi über <strong>Add-ons → Paket-Symbol → Aus ZIP-Datei installieren</strong> auswählen. Danach <strong>Aus Repository installieren → marbra00_repo</strong> öffnen.</p>
<p lang="en">Download the repository ZIP and select it in Kodi via <strong>Add-ons → package icon → Install from ZIP file</strong>. Then open <strong>Install from repository → marbra00_repo</strong>.</p></section>
<h2>Downloads</h2><table><thead><tr><th>Name</th><th>Version</th><th>Download</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table>
<p><a href="https://github.com/marbra00/marbra00_repo">Anleitung und Quellcode / Guide and source code</a></p>
<p>Inoffizielles Projekt, nicht mit Team Kodi verbunden. / Unofficial project, not affiliated with Team Kodi.</p>
</body></html>
'''
    (site / 'index.html').write_bytes(page.encode('utf-8'))
    return records


if __name__ == '__main__':
    print(json.dumps({'packages': build()}, ensure_ascii=False, indent=2))
