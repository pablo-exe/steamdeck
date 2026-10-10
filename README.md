# Steam Deck reproducible

Repositorio para gestionar la configuración de mi Steam Deck, conservar el conocimiento de mantenimiento y avanzar hacia una instalación reproducible con CI/CD.

## Workspace

El checkout local en `/home/deck/steamdeck` es el workspace de trabajo del asistente. Los archivos necesarios para reproducir la configuración se guardarán en este repositorio.

## Memoria

- `memoria/estado.md`: contexto vigente, acuerdos y próximos pasos.
- `memoria/avances.md`: registro cronológico de cambios y verificaciones.

Al retomar el trabajo, consultar `AGENTS.md` y la memoria. Actualizar ambos documentos de memoria cuando haya avances relevantes.

## Decky Loader y plugins

Instalar las versiones fijadas en `config/decky.lock.json` desde el modo escritorio:

```bash
cd ~/steamdeck
./scripts/install-decky.sh
```

El script descarga y verifica los artefactos como usuario y solicita `sudo` para instalar el servicio y los plugins. Requiere Steam instalado en `~/.steam/steam`, Linux con systemd y Python 3.11 o posterior. Si se ejecuta desde root, indicar `./scripts/install-decky.sh --user deck`.

Comprobar el estado o preparar las descargas sin instalar:

```bash
python3 scripts/decky.py check
python3 scripts/decky.py prepare
```

Consultar [la documentación de Decky](docs/decky.md) para las versiones, las copias locales y el procedimiento de actualización.

El inventario del resto del equipo y su automatización quedan pendientes.
