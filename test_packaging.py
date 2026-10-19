"""Verify the built archive, including QGIS's case-sensitive metadata names."""
import configparser
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


class PackagingTest(unittest.TestCase):
    def test_release_preserves_metadata_keys(self):
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('tools/package.py', 'metadata.txt', 'LICENSE',
                         '__init__.py', 'i18n/en.json'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, target)
            subprocess.run([sys.executable, str(root / 'tools/package.py'),
                            '--release'], check=True, capture_output=True)
            with zipfile.ZipFile(next((root / 'dist').glob('*.zip'))) as archive:
                metadata = configparser.ConfigParser()
                metadata.optionxform = str
                metadata.read_string(archive.read(
                    'prese_fotografiche/metadata.txt').decode('utf-8'))
                values = metadata['general']
                for key in ('name', 'description', 'about', 'version', 'author',
                            'email', 'repository', 'qgisMinimumVersion',
                            'qgisMaximumVersion', 'hasProcessingProvider'):
                    self.assertTrue(values[key], key)
                self.assertNotIn('qgisminimumversion', values)
                self.assertEqual(values['author'], 'Riccardo Casoli')
                self.assertNotIn('/', values['author'])
                self.assertIn('prese_fotografiche/__init__.py', archive.namelist())
                self.assertNotIn('prese_fotografiche/tools/package.py', archive.namelist())
                self.assertFalse(any(Path(n).name.startswith(('test_', 'smoke_test_'))
                                     for n in archive.namelist()))
