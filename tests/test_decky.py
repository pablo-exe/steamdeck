import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('decky', Path(__file__).resolve().parents[1] / 'scripts/decky.py')
decky = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decky)


class ArtifactTests(unittest.TestCase):
    def test_reject_path_traversal_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, mode in [('Plugin/../../outside', 0), ('/absolute', 0),
                               ('Other/plugin.json', 0), ('Plugin/link', 0o120777)]:
                with self.subTest(name=name):
                    archive = root / 'bad.zip'
                    with zipfile.ZipFile(archive, 'w') as bundle:
                        info = zipfile.ZipInfo(name)
                        info.external_attr = mode << 16
                        bundle.writestr(info, 'payload')
                    with self.assertRaises(ValueError):
                        decky.extract_plugin({'directory': 'Plugin'}, archive, root / 'staging')
            self.assertFalse((root / 'outside').exists())

    def test_reject_mismatched_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('Plugin/plugin.json', json.dumps({'name': 'Different'}))
                bundle.writestr('Plugin/package.json', json.dumps({'version': '1.0'}))
            with self.assertRaisesRegex(ValueError, 'Identidad'):
                decky.extract_plugin({'directory': 'Plugin', 'name': 'Expected', 'version': '1.0'}, archive, root / 'staging')

    def test_wrong_download_hash_never_enters_cache(self):
        import io
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            artifact = {'sha256': '0' * 64, 'url': 'https://example.org/plugin.zip'}
            with patch.object(decky.urllib.request, 'urlopen', return_value=io.BytesIO(b'corrupt')):
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    decky.fetch(artifact, cache)
            self.assertEqual(list(cache.iterdir()), [])

    def test_matching_version_with_corrupt_binary_is_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'package.json').write_text('{"version":"1.0"}')
            (root / 'dist').mkdir()
            (root / 'dist/index.js').touch()
            (root / 'bin').mkdir()
            (root / 'bin/tool').write_bytes(b'wrong')
            plugin = {'version': '1.0', 'remote_binaries': [{'name': 'tool', 'sha256': hashlib.sha256(b'right').hexdigest()}]}
            self.assertFalse(decky.matches(plugin, root))


class RecoveryTests(unittest.TestCase):
    def test_conforming_install_does_not_replace_files_or_make_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / 'cache'
            cache.mkdir()
            (cache / 'unit').write_text('official unit')
            unit = root / 'plugin_loader.service'
            unit.write_text('official unit')
            marker = root / '.steam/steam/.cef-enable-remote-debugging'
            marker.parent.mkdir(parents=True)
            marker.touch()
            user = SimpleNamespace(pw_dir=str(root))
            lock = {'loader': {'service': {'sha256': 'unit'}}}
            with patch.object(decky, 'check', return_value=True), \
                    patch.object(decky, 'snapshot') as snapshot, \
                    patch.object(decky, 'systemctl') as systemctl, \
                    patch.object(decky, 'wait_loader'):
                decky.install(lock, cache, root / 'staging', root / 'homebrew', user, unit_path=unit)
            snapshot.assert_not_called()
            systemctl.assert_called_once_with('enable', '--now', 'plugin_loader')
            self.assertEqual(unit.read_text(), 'official unit')

    def test_failed_start_restores_previous_plugins_loader_and_service(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            homebrew = root / 'homebrew'
            old = homebrew / 'plugins/OldFolder'
            old.mkdir(parents=True)
            (old / 'plugin.json').write_text('{"name":"Plugin"}')
            (old / 'original').write_text('original')
            services = homebrew / 'services'
            services.mkdir()
            (services / 'PluginLoader').write_text('old loader')
            (services / '.loader.version').write_text('v-old')
            staging = root / 'staging'
            source = staging / 'NewFolder'
            source.mkdir(parents=True)
            (source / 'plugin.json').write_text('{"name":"Plugin"}')
            (source / 'new').write_text('new')
            cache = root / 'cache'
            cache.mkdir()
            (cache / 'binary').write_text('new loader')
            (cache / 'unit').write_text('ExecStart=${HOMEBREW_FOLDER}/services/PluginLoader')
            unit = root / 'plugin_loader.service'
            unit.write_text('old unit')
            (root / '.steam/steam').mkdir(parents=True)
            user = SimpleNamespace(pw_dir=str(root), pw_uid=1000, pw_gid=1000)
            lock = {'plugins': [{'name': 'Plugin', 'directory': 'NewFolder'}], 'remove_plugins': [],
                    'loader': {'sha256': 'binary', 'version': 'v-new', 'service': {'sha256': 'unit'}}}
            with patch.object(decky, 'check', return_value=False), \
                    patch.object(decky, 'snapshot'), patch.object(decky, 'own_plugin'), \
                    patch.object(decky.os, 'chown'), \
                    patch.object(decky, 'systemctl', return_value=SimpleNamespace(returncode=0)), \
                    patch.object(decky, 'wait_loader', side_effect=RuntimeError('failed start')):
                with self.assertRaisesRegex(RuntimeError, 'failed start'):
                    decky.install(lock, cache, staging, homebrew, user, unit_path=unit)
            self.assertEqual((old / 'original').read_text(), 'original')
            self.assertFalse((homebrew / 'plugins/NewFolder').exists())
            self.assertEqual((services / 'PluginLoader').read_text(), 'old loader')
            self.assertEqual((services / '.loader.version').read_text(), 'v-old')
            self.assertEqual(unit.read_text(), 'old unit')


if __name__ == '__main__':
    unittest.main()
