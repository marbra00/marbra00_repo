# SPDX-License-Identifier: GPL-3.0-or-later
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('builder', ROOT / 'tools/build_repository.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class RepositoryBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT / 'repository.marbra00_repo', self.root / 'repository.marbra00_repo')
        shutil.copy2(ROOT / 'LICENSE', self.root / 'LICENSE')
        (self.root / 'packages.json').write_bytes(b'[]\n')

    def test_install_zip_and_index_match_and_rebuild_is_reproducible(self):
        records = builder.build(self.root)
        index = (self.root / 'docs/addons.xml').read_bytes()
        checksum = (self.root / 'docs/addons.xml.sha256').read_text().strip()
        self.assertEqual(checksum, hashlib.sha256(index).hexdigest())
        entries = ET.fromstring(index)
        self.assertEqual([entry.get('id') for entry in entries], ['repository.marbra00_repo'])
        package = self.root / records[0]['zip']
        original_zip = package.read_bytes()
        with ZipFile(package) as archive:
            for path in (self.root / 'repository.marbra00_repo').rglob('*'):
                if path.is_file():
                    self.assertEqual(archive.read(path.relative_to(self.root).as_posix()), path.read_bytes())
        self.assertEqual(builder.build(self.root), records)
        self.assertEqual(package.read_bytes(), original_zip)
        self.assertEqual((self.root / 'docs/addons.xml').read_bytes(), index)

    def test_changed_existing_version_is_rejected_without_overwriting_zip(self):
        record = builder.build(self.root)[0]
        package = self.root / record['zip']
        original_zip = package.read_bytes()
        original_index = (self.root / 'docs/addons.xml').read_bytes()
        with (self.root / 'repository.marbra00_repo/README.md').open('ab') as stream:
            stream.write(b'\nChanged content\n')
        with self.assertRaisesRegex(ValueError, 'Existing version differs'):
            builder.build(self.root)
        self.assertEqual(package.read_bytes(), original_zip)
        self.assertEqual((self.root / 'docs/addons.xml').read_bytes(), original_index)

    def test_selected_package_with_wrong_checksum_is_rejected(self):
        package = self.root / 'docs/plugin.video.example/plugin.video.example-1.0.0.zip'
        package.parent.mkdir(parents=True)
        package.write_bytes(b'invalid package')
        (self.root / 'packages.json').write_text(json.dumps([{
            'path': package.relative_to(self.root).as_posix(), 'sha256': '0' * 64,
            'source': 'https://example.com/source'}]), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum differs'):
            builder.build(self.root)
        self.assertFalse((self.root / 'docs/addons.xml').exists())

    def test_selected_addon_is_indexed_and_nested_artwork_is_preserved(self):
        package = self.root / 'docs/plugin.video.example/plugin.video.example-1.0.0.zip'
        package.parent.mkdir(parents=True)
        manifest = b'''<addon id="plugin.video.example" version="1.0.0" name="Example" provider-name="Example">
            <extension point="xbmc.python.pluginsource" library="default.py" />
            <extension point="xbmc.addon.metadata"><license>GPL-3.0-or-later</license>
                <assets><icon>resources/images/icon.png</icon></assets>
            </extension></addon>'''
        with ZipFile(package, 'w') as archive:
            archive.writestr('plugin.video.example/addon.xml', manifest)
            archive.writestr('plugin.video.example/default.py', b'# Example\n')
            archive.writestr('plugin.video.example/resources/images/icon.png', b'example artwork')
        original_zip = package.read_bytes()
        (self.root / 'packages.json').write_text(json.dumps([{
            'path': package.relative_to(self.root).as_posix(),
            'sha256': hashlib.sha256(original_zip).hexdigest(),
            'source': 'https://example.com/source'}]), encoding='utf-8')
        records = builder.build(self.root)
        self.assertEqual([record['id'] for record in records],
                         ['repository.marbra00_repo', 'plugin.video.example'])
        self.assertEqual(package.read_bytes(), original_zip)
        self.assertEqual((package.parent / 'resources/images/icon.png').read_bytes(), b'example artwork')
        index = ET.parse(self.root / 'docs/addons.xml').getroot()
        self.assertEqual([entry.get('id') for entry in index],
                         ['repository.marbra00_repo', 'plugin.video.example'])

    def test_package_outside_publication_folder_is_rejected(self):
        (self.root / 'outside.zip').write_bytes(b'not a zip')
        (self.root / 'packages.json').write_text(json.dumps([{
            'path': 'outside.zip', 'sha256': '0' * 64, 'source': 'https://example.com/source'}]),
            encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'inside docs'):
            builder.build(self.root)

    def test_zip_traversal_and_absolute_artwork_are_rejected(self):
        manifest = deepcopy(ET.parse(ROOT / 'repository.marbra00_repo/addon.xml').getroot())
        for unsafe_name in ['repository.marbra00_repo/../outside.txt',
                            'repository.marbra00_repo//outside.txt']:
            buffer = io.BytesIO()
            with ZipFile(buffer, 'w') as archive:
                archive.writestr('repository.marbra00_repo/addon.xml', ET.tostring(manifest))
                archive.writestr(unsafe_name, b'outside')
            with self.assertRaises(ValueError):
                builder.inspect_package(buffer.getvalue())
        manifest.find("extension[@point='xbmc.addon.metadata']/assets/icon").text = '/outside.png'
        buffer = io.BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('repository.marbra00_repo/addon.xml', ET.tostring(manifest))
        with self.assertRaisesRegex(ValueError, 'Unsafe artwork path'):
            builder.inspect_package(buffer.getvalue())


if __name__ == '__main__':
    unittest.main()
