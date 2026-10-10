# Estado del proyecto

## Objetivo

Gestionar la Steam Deck mediante este repositorio y el asistente, con CI/CD reproducible que facilite el mantenimiento, las actualizaciones y la recuperación tras una reinstalación.

## Contexto aportado por el usuario

La configuración actual se ha instalado manualmente. Se quiere conservar el conocimiento que, de otro modo, podría perderse al reinstalar.

## Acuerdos iniciales

- Repositorio: `git@github.com:pablo-exe/steamdeck.git`.
- Workspace local: `/home/deck/steamdeck`.
- Memoria compartida y versionada: `memoria/`.
- Alcance inicial: establecer workspace, memoria y subir la estructura inicial a Git.
- Segundo paso autorizado: actualizar todos los plugins de Decky y automatizar la instalación de Decky Loader y los plugins en el repositorio.
- El usuario decidió eliminar «Lossless Scaling» 0.8.1 y mantener su sucesor Decky LSFG-VK.

## Estado verificado

- Existe un checkout local con rama `main` y remoto `origin` configurado.
- El commit inicial `4e9d7e1` ya está publicado en GitHub. La red funciona en el entorno actual.
- Para Git por SSH usar `GIT_SSH_COMMAND='ssh -F /dev/null -o BatchMode=yes'`: la configuración SSH global falla por permisos. No se modificó la configuración del sistema. La integración de GitHub consultaba el repositorio pero rechazaba escrituras con HTTP 403; el push por SSH sí funciona.
- Decky Loader está activo y coincide con v3.2.10, la última release estable comprobada el 2026-10-10.
- Se actualizaron Decky-Framegen (0.11.15 → 0.17), Decky LSFG-VK (0.12.2 → 0.14.4), PlayTime (3.2.5 → 3.3.1), HLTB for Deck (2.0.10 → 2.0.12) y Pause Games (1.0.2 → 1.0.2-4bf4b4e).
- Se eliminó «Lossless Scaling» mediante el instalador de Decky. Quedan 12 plugins y Decky confirmó que están cargados con las versiones fijadas en `config/decky.lock.json`.
- Los otros 7 plugins ya estaban actualizados según las fuentes comprobadas. `__MACOSX` es un resto de ZIP y se excluye del manifiesto.
- Instalación completa: `./scripts/install-decky.sh`. Preparación y comprobación: `python3 scripts/decky.py prepare` y `python3 scripts/decky.py check`.
- El manifiesto fija versiones, URLs y SHA-256 de Decky, el servicio systemd, los plugins y sus dependencias declaradas. CI valida scripts, manifiesto y pruebas; el despliegue se ejecuta localmente.
- La actualización real se hizo con `python3 scripts/decky.py live-update`, usando la API autenticada de Decky; sudo requiere contraseña en este equipo. La instalación completa con systemd se verificó mediante pruebas simuladas de recuperación; aún no se ha probado en una Steam Deck recién reinstalada.
- Copia anterior a todos los cambios: `~/.local/state/steamdeck/decky-backups/1791660334226870205.tar.gz`. Existe una segunda copia tras actualizar Framegen. Contienen datos privados y permanecen fuera de Git.
- El commit inicial se identifica como `Codex <codex@openai.com>` usando opciones por comando; no se configura la identidad global del usuario.

## Próximo paso propuesto

Gestionar los ajustes y temas de Decky, las dependencias externas (por ejemplo Ludusavi) y las herramientas que los plugins instalan en juegos. El instalador actual reproduce el código y las dependencias declaradas de los plugins; aún no recupera esos datos tras reinstalar. Continuar después con el inventario del resto del equipo.
