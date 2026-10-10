#!/usr/bin/env python3
"""Instalar versiones fijadas de Decky y sus plugins; no resolver latest al instalar."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def component(value):
    if not isinstance(value, str) or not value or value in ('.', '..') or '/' in value or '\\' in value or '\n' in value:
        raise ValueError(f'Nombre de archivo inválido: {value!r}')
    return value


def load_lock(path):
    lock = json.loads(path.read_text())
    if lock['schema_version'] != 1:
        raise ValueError('Versión de manifiesto no soportada')
    names, directories = set(), set()
    for plugin in lock['plugins']:
        component(plugin['directory'])
        if plugin['name'] in names or plugin['directory'] in directories:
            raise ValueError('Plugins duplicados en el manifiesto')
        names.add(plugin['name'])
        directories.add(plugin['directory'])
        for binary in plugin['remote_binaries']:
            component(binary['name'])
    if names.intersection(lock['remove_plugins']):
        raise ValueError('Un plugin no puede instalarse y eliminarse a la vez')
    for artifact in artifacts(lock):
        if urllib.parse.urlparse(artifact['url']).scheme != 'https':
            raise ValueError('Los artefactos deben usar HTTPS')
        sha = artifact['sha256']
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('SHA-256 inválido')
    return lock


def artifacts(lock):
    yield lock['loader']
    yield lock['loader']['service']
    for plugin in lock['plugins']:
        yield plugin
        yield from plugin['remote_binaries']


def fetch(artifact, cache):
    target = cache / artifact['sha256']
    if target.is_file() and digest(target) == artifact['sha256']:
        return target
    print(f"Descargando {artifact['url']}", flush=True)
    fd, temporary = tempfile.mkstemp(dir=cache)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as out:
            request = urllib.request.Request(artifact['url'], headers={'User-Agent': 'steamdeck-reproducible/1'})
            with urllib.request.urlopen(request, timeout=120) as response:
                shutil.copyfileobj(response, out)
        if digest(temporary) != artifact['sha256']:
            raise ValueError(f"SHA-256 incorrecto: {artifact['url']}")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def extract_plugin(plugin, archive, staging):
    """Aceptar solo un directorio de plugin, sin enlaces ni rutas fuera de él."""
    folder = plugin['directory']
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            path = PurePosixPath(entry.filename)
            if path.parts and path.parts[0] == '__MACOSX':
                continue
            mode = entry.external_attr >> 16
            if (not path.parts or path.is_absolute() or '..' in path.parts
                    or '\\' in entry.filename or path.parts[0] != folder
                    or stat.S_ISLNK(mode)):
                raise ValueError(f'Ruta ZIP inválida: {entry.filename}')
            target = staging.joinpath(*path.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open('wb') as out:
                    shutil.copyfileobj(source, out)
                target.chmod(0o755 if mode & 0o111 else 0o644)
    target = staging / folder
    meta = json.loads((target / 'plugin.json').read_text())
    package = json.loads((target / 'package.json').read_text())
    if meta['name'] != plugin['name'] or package['version'] != plugin['version']:
        raise ValueError(f"Identidad o versión incorrecta: {plugin['name']}")
    declared = [{'name': b['name'], 'url': b['url'], 'sha256': b['sha256hash']}
                for b in package.get('remote_binary', [])]
    if declared != plugin['remote_binaries']:
        raise ValueError(f"Dependencias diferentes del manifiesto: {plugin['name']}")
    if not (target / 'dist/index.js').is_file():
        raise ValueError(f"Falta el frontend compilado: {plugin['name']}")
    return target


def prepare(lock, cache, staging):
    cache.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda artifact: fetch(artifact, cache), artifacts(lock)))
    for plugin in lock['plugins']:
        target = extract_plugin(plugin, cache / plugin['sha256'], staging)
        for binary in plugin['remote_binaries']:
            (target / 'bin').mkdir(exist_ok=True)
            shutil.copy2(cache / binary['sha256'], target / 'bin' / binary['name'])


def installed(homebrew):
    found = {}
    for meta in (homebrew / 'plugins').glob('*/plugin.json'):
        data = json.loads(meta.read_text())
        if data['name'] in found:
            raise ValueError(f"Plugin duplicado en el equipo: {data['name']}")
        found[data['name']] = meta.parent
    return found


def matches(plugin, path):
    if not path or not (path / 'package.json').is_file():
        return False
    if json.loads((path / 'package.json').read_text())['version'] != plugin['version']:
        return False
    if not (path / 'dist/index.js').is_file():
        return False
    return all((path / 'bin' / b['name']).is_file()
               and digest(path / 'bin' / b['name']) == b['sha256']
               for b in plugin['remote_binaries'])


def check(lock, homebrew):
    found = installed(homebrew)
    ok = True
    for plugin in lock['plugins']:
        good = matches(plugin, found.get(plugin['name']))
        print(f"{'OK' if good else 'PENDIENTE'} {plugin['name']} {plugin['version']}")
        ok &= good
    for name in lock['remove_plugins']:
        if name in found:
            print(f'PENDIENTE eliminar {name}')
            ok = False
    loader = homebrew / 'services/PluginLoader'
    good = loader.is_file() and digest(loader) == lock['loader']['sha256']
    print(f"{'OK' if good else 'PENDIENTE'} Decky Loader {lock['loader']['version']}")
    return ok and good


def snapshot(homebrew, user_home, owner=None):
    directory = user_home / '.local/state/steamdeck/decky-backups'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if owner:
        for path in (user_home / '.local', user_home / '.local/state', directory.parent, directory):
            os.chown(path, owner.pw_uid, owner.pw_gid)
    backup = directory / f'{time.time_ns()}.tar.gz'
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as output, tarfile.open(fileobj=output, mode='w:gz', compresslevel=1) as bundle:
        for name in ('plugins', 'settings', 'data', 'services'):
            path = homebrew / name
            if path.exists():
                bundle.add(path, arcname=name)
        service = Path('/etc/systemd/system/plugin_loader.service')
        if service.exists():
            bundle.add(service, arcname='systemd/plugin_loader.service')
    if owner:
        os.chown(backup, owner.pw_uid, owner.pw_gid)
    print(f'Copia local: {backup}', flush=True)
    return backup


def systemctl(*args, check=True):
    return subprocess.run(['systemctl', *args], check=check, capture_output=True, text=True)


def wait_loader():
    for attempt in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:1337/auth/token', timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError('Decky no responde en localhost:1337')


def own_plugin(path, user):
    meta = json.loads((path / 'plugin.json').read_text())
    uid = 0 if 'root' in meta.get('flags', []) else user.pw_uid
    gid = 0 if uid == 0 else user.pw_gid
    for entry in [path, *path.rglob('*')]:
        os.chown(entry, uid, gid)
    for entry in (path, path / 'plugin.json'):
        os.chown(entry, 0, 0)
        entry.chmod(0o755)


def install(lock, cache, staging, homebrew, user,
            unit_path=Path('/etc/systemd/system/plugin_loader.service')):
    template = (cache / lock['loader']['service']['sha256']).read_text()
    unit = template.replace('${HOMEBREW_FOLDER}', str(homebrew))
    marker = Path(user.pw_dir) / '.steam/steam/.cef-enable-remote-debugging'
    if check(lock, homebrew) and unit_path.is_file() and unit_path.read_text() == unit and marker.is_file():
        systemctl('enable', '--now', 'plugin_loader')
        wait_loader()
        print('Instalación ya conforme; no se reemplazaron archivos.')
        return
    old_unit = unit_path.read_bytes() if unit_path.exists() else None
    was_active = systemctl('is-active', 'plugin_loader', check=False).returncode == 0
    was_enabled = systemctl('is-enabled', 'plugin_loader', check=False).returncode == 0
    found = installed(homebrew)
    for plugin in lock['plugins']:
        destination = homebrew / 'plugins' / plugin['directory']
        if destination.exists() and destination != found.get(plugin['name']):
            raise ValueError(f"Directorio ocupado por otro plugin: {destination}")
    snapshot(homebrew, Path(user.pw_dir), owner=user)
    systemctl('stop', 'plugin_loader', check=was_active)
    # Renombrar dentro del mismo filesystem permite recuperar los directorios originales.
    recovery = Path(tempfile.mkdtemp(prefix='.decky-recovery-', dir=homebrew))
    changes = []
    cleanup = False
    had_marker = marker.exists()

    def replace(source, destination):
        saved = recovery / str(len(changes))
        if destination.exists():
            destination.rename(saved)
        changes.append((destination, saved))
        if source:
            shutil.move(str(source), destination)

    try:
        for name in lock['remove_plugins']:
            if name in found:
                replace(None, found[name])
        for plugin in lock['plugins']:
            destination = homebrew / 'plugins' / plugin['directory']
            destination.parent.mkdir(parents=True, exist_ok=True)
            old = found.get(plugin['name'])
            if old and old != destination:
                replace(None, old)
            source = staging / plugin['directory']
            own_plugin(source, user)
            replace(source, destination)
        services = homebrew / 'services'
        services.mkdir(parents=True, exist_ok=True)
        binary = staging / 'PluginLoader'
        shutil.copy2(cache / lock['loader']['sha256'], binary)
        binary.chmod(0o755)
        replace(binary, services / 'PluginLoader')
        version = staging / '.loader.version'
        version.write_text(lock['loader']['version'] + '\n')
        os.chown(version, user.pw_uid, user.pw_gid)
        replace(version, services / '.loader.version')
        unit_path.write_text(unit)
        steam = Path(user.pw_dir) / '.steam/steam'
        if not steam.is_dir():
            raise RuntimeError('No se encuentra la instalación de Steam en ~/.steam/steam')
        marker.touch(exist_ok=True)
        os.chown(marker, user.pw_uid, user.pw_gid)
        systemctl('daemon-reload')
        systemctl('enable', '--now', 'plugin_loader')
        wait_loader()
        if not check(lock, homebrew):
            raise RuntimeError('La verificación de instalación ha fallado')
        cleanup = True
    except BaseException:
        systemctl('stop', 'plugin_loader', check=False)
        for destination, saved in reversed(changes):
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink(missing_ok=True)
            if saved.exists():
                saved.rename(destination)
        if old_unit is None:
            unit_path.unlink(missing_ok=True)
        else:
            unit_path.write_bytes(old_unit)
        systemctl('daemon-reload', check=False)
        systemctl('enable' if was_enabled else 'disable', 'plugin_loader', check=False)
        if was_active:
            systemctl('start', 'plugin_loader', check=False)
        if not had_marker:
            marker.unlink(missing_ok=True)
        cleanup = True
        raise
    finally:
        if cleanup:
            shutil.rmtree(recovery)
        else:
            print(f'Recuperación incompleta; originales conservados en {recovery}', file=sys.stderr)


async def live_update(lock, cache, homebrew, user_home):
    """Usar el instalador autenticado del Decky existente; aiohttp solo en este modo."""
    import aiohttp
    import asyncio
    found = installed(homebrew)
    pending = [p for p in lock['plugins'] if not matches(p, found.get(p['name']))]
    remove = [name for name in lock['remove_plugins'] if name in found]
    if not pending and not remove:
        print('Los plugins ya coinciden con el manifiesto.')
        return
    snapshot(homebrew, user_home)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=900)) as session:
        async with session.get('http://127.0.0.1:1337/auth/token') as response:
            response.raise_for_status()
            token = await response.text()
        async with session.ws_connect('http://127.0.0.1:1337/ws', params={'auth': token}) as ws:
            call_id = int(time.time() * 1000)

            async def call(route, args, completed=None):
                nonlocal call_id, ws
                call_id += 1
                await ws.send_json({'type': 0, 'id': call_id, 'route': route, 'args': args})
                events = []
                while True:
                    message = await ws.receive(timeout=900)
                    if message.type != aiohttp.WSMsgType.TEXT:
                        if completed is None:
                            raise RuntimeError('Se cerró la conexión con Decky; volver a ejecutar live-update')
                        # La interfaz puede recuperar el único socket de Decky mientras
                        # la llamada sigue ejecutándose. No reenviar una mutación.
                        deadline = time.monotonic() + 900
                        while not completed():
                            if time.monotonic() > deadline:
                                raise RuntimeError('La instalación no terminó tras perder la conexión')
                            await asyncio.sleep(1)
                        await asyncio.sleep(3)
                        await ws.close()
                        ws = await session.ws_connect('http://127.0.0.1:1337/ws', params={'auth': token})
                        return None, events
                    data = json.loads(message.data)
                    if data['type'] == 5:
                        events.append(data)
                    elif data.get('id') == call_id:
                        await ws.send_json({'type': 3, 'id': call_id})
                        if data['type'] == -1:
                            raise RuntimeError(data['error']['message'])
                        return data.get('result'), events

            for plugin in pending:
                print(f"Actualizando {plugin['name']} → {plugin['version']}", flush=True)
                _, events = await call('utilities/install_plugin', [
                    'file://' + str(cache / plugin['sha256']), plugin['name'],
                    plugin['version'], plugin['sha256'], 2])
                prompt = next(e for e in events if e['event'] == 'loader/add_plugin_install_prompt')
                await call('utilities/confirm_plugin_install', [prompt['args'][2]],
                           completed=lambda: matches(plugin, installed(homebrew).get(plugin['name'])))
                if not matches(plugin, installed(homebrew).get(plugin['name'])):
                    raise RuntimeError(f"Decky no instaló correctamente {plugin['name']}; conservar copia local")
            # Eliminar el plugin antiguo solo después de comprobar las actualizaciones.
            for name in remove:
                print(f'Eliminando {name}', flush=True)
                await call('utilities/uninstall_plugin', [name],
                           completed=lambda: name not in installed(homebrew))
                if name in installed(homebrew):
                    raise RuntimeError(f'Decky no eliminó {name}')
            loaded, _ = await call('loader/get_plugins', [])
            loaded = {p['name']: p['version'] for p in loaded}
            for plugin in lock['plugins']:
                if loaded.get(plugin['name']) != plugin['version']:
                    raise RuntimeError(f"Plugin no cargado por Decky: {plugin['name']}")
            await ws.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'install', 'live-update'])
    parser.add_argument('--lock', type=Path, default=REPO / 'config/decky.lock.json')
    parser.add_argument('--user', default=os.environ.get('SUDO_USER') or pwd.getpwuid(os.getuid()).pw_name)
    args = parser.parse_args()
    user = pwd.getpwnam(args.user)
    if user.pw_uid == 0:
        parser.error('Indica el usuario de Steam con --user deck; no usar /root como home')
    user_home = Path(user.pw_dir)
    homebrew = user_home / 'homebrew'
    cache = user_home / '.cache/steamdeck/decky'
    lock = load_lock(args.lock)
    if args.action == 'check':
        return 0 if check(lock, homebrew) else 1
    if args.action == 'install' and os.geteuid() != 0:
        # Descargar y verificar como usuario antes de solicitar sudo.
        with tempfile.TemporaryDirectory(prefix='decky-stage-') as temporary:
            prepare(lock, cache, Path(temporary))
        return subprocess.run(['sudo', sys.executable, str(Path(__file__).resolve()),
                               'install', '--user', args.user, '--lock', str(args.lock.resolve())]).returncode
    with tempfile.TemporaryDirectory(prefix='decky-stage-') as temporary:
        staging = Path(temporary)
        prepare(lock, cache, staging)
        if args.action == 'install':
            homebrew.mkdir(parents=True, exist_ok=True)
            os.chown(homebrew, user.pw_uid, user.pw_gid)
            for path in (user_home / '.cache', cache.parent, cache):
                os.chown(path, user.pw_uid, user.pw_gid)
            install(lock, cache, staging, homebrew, user)
        elif args.action == 'live-update':
            import asyncio
            asyncio.run(live_update(lock, cache, homebrew, user_home))
            return 0 if check(lock, homebrew) else 1
        else:
            print('Artefactos, metadatos y dependencias verificados.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
