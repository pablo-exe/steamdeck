# Decky reproducible

`config/decky.lock.json` fija Decky Loader, el servicio systemd, los ZIPs de plugins y sus dependencias `remote_binary`. Cada descarga incluye URL y SHA-256. Instalar reproduce esas versiones, sin resolver `latest` durante el despliegue.

## Versiones seleccionadas el 2026-10-10

| Componente | Versión |
| --- | --- |
| Decky Loader | v3.2.10 |
| Animation Changer | 1.3.2 |
| Battery Tracker | 0.2.0 |
| CSS Loader | 2.1.2 |
| Decky Sunshine | 2025.10.27-dddf365 |
| Decky-Framegen | 0.17 |
| Decky LSFG-VK | 0.14.4 |
| Decky Ludusavi | 1.2.2 |
| HLTB for Deck | 2.0.12 |
| MagicBlack | 2.0.0 |
| Pause Games | 1.0.2-4bf4b4e |
| PlayTime | 3.3.1 |
| SteamGridDB | 1.8.1 |

Se contrastaron la [tienda estable](https://plugins.deckbrew.xyz/plugins) y las publicaciones de los autores. Se eligieron publicaciones estables más recientes que la tienda para [Framegen](https://github.com/xXJSONDeruloXx/Decky-Framegen/releases/tag/v0.17), [LSFG-VK](https://github.com/xXJSONDeruloXx/decky-lsfg-vk/releases/tag/v0.14.4), [PlayTime](https://github.com/0u73r-h34v3n/SDH-PlayTime/releases/tag/v3.3.1), [HLTB](https://github.com/morwy/hltb-for-deck/releases/tag/v2.0.12) y [Pause Games](https://github.com/wynn1212/SDH-PauseGames/releases/tag/20260723060434). Para los otros plugins se fijó la versión de la tienda, que en algunos casos supera las releases de GitHub.

«Lossless Scaling» 0.8.1 se retira por decisión del usuario: su repositorio redirige a Decky LSFG-VK, que ya estaba instalado. `__MACOSX` no es un plugin y no se incluye en el manifiesto.

## Instalación

```bash
./scripts/install-decky.sh
```

El instalador prepara todo antes de detener Decky. Verifica hashes, nombre y versión de cada plugin, frontend compilado, dependencias declaradas y rutas del ZIP. Instala el binario y el [servicio oficial de v3.2.10](https://github.com/SteamDeckHomebrew/decky-loader/blob/v3.2.10/dist/plugin_loader-release.service), activa la depuración CEF requerida por Decky y habilita el servicio.

Conserva `homebrew/settings`, `homebrew/data` y `homebrew/themes`; los directorios de código de los plugins se reemplazan por los artefactos fijados. Antes de cambiar archivos crea una copia local. Si falla el despliegue, recupera los directorios originales de plugins, el binario, el archivo de versión y el servicio. Si todo coincide y el servicio/CEF están configurados, una nueva ejecución no reemplaza archivos.

Una instalación nueva podría requerir reiniciar Steam para que lea el marcador CEF.

## Actualizaciones sobre un Decky existente

```bash
python3 scripts/decky.py live-update
python3 scripts/decky.py check
```

`live-update` requiere `aiohttp`, disponible en este equipo. Usa la API autenticada local del Decky existente y su propio instalador, que actualiza y carga los plugins sin pedir sudo. Crea una copia antes de modificar nada y verifica los plugins cargados. Solo elimina el plugin antiguo después de verificar las actualizaciones. Este modo no instala ni actualiza el binario de Decky Loader y no ofrece rollback automático: conserva la copia y detiene el proceso ante un fallo. La instalación completa usa únicamente la biblioteca estándar de Python.

## Copias y caché

- Copias privadas: `~/.local/state/steamdeck/decky-backups/<timestamp>.tar.gz`, con permisos 600. Incluyen plugins, settings, data, services y una copia de la unidad systemd. No se suben a Git.
- Caché por SHA-256: `~/.cache/steamdeck/decky/`. Se comprueba el hash al reutilizar un archivo.

Las copias contienen ajustes privados; mantenerlas fuera del repositorio. Para una reinstalación, el repositorio reproduce el código de Decky y los plugins. La recuperación de ajustes, temas, partidas, Ludusavi y las herramientas que los plugins instalan o modifican en juegos requiere gestionar esos datos por separado.

## Cambiar versiones

Consultar tienda y releases oficiales, descargar los ZIPs candidatos y comprobar su `plugin.json` y `package.json`. Actualizar URL, versión, directorio, SHA-256 y dependencias en el manifiesto. Ejecutar `prepare`, las pruebas y, después, aplicar y comprobar. Registrar el resultado en `memoria/` y subir los cambios.

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/install-decky.sh
```

GitHub Actions ejecuta estas comprobaciones y valida el manifiesto en cada push y pull request. El despliegue se ejecuta localmente en la Steam Deck; no hay un runner remoto con acceso al dispositivo.
