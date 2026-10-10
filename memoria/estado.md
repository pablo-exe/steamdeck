# Estado del proyecto

## Objetivo

Gestionar la Steam Deck mediante este repositorio y el asistente, con CI/CD reproducible que facilite el mantenimiento, las actualizaciones y la recuperación tras una reinstalación.

## Contexto aportado por el usuario

La configuración actual se ha instalado manualmente. Se quiere conservar el conocimiento que, de otro modo, podría perderse al reinstalar.

## Acuerdos iniciales

- Repositorio: `git@github.com:pablo-exe/steamdeck.git`.
- Workspace local: `/home/deck/steamdeck`.
- Memoria compartida y versionada: `memoria/`.
- Alcance de esta primera sesión: establecer workspace, memoria y subir la estructura inicial a Git.

## Estado verificado

- Existe un checkout local con rama `main` y remoto `origin` configurado.
- Al inicio de esta sesión, el checkout no contenía archivos de proyecto ni commits.
- Se ha creado la documentación inicial; todavía no se ha inventariado ni automatizado la configuración del equipo.
- La subida a GitHub está pendiente: SSH falla por permisos de una configuración del sistema y, al omitir esa configuración, por resolución DNS. La integración de GitHub permite consultar el repositorio, pero devuelve HTTP 403 (`Resource not accessible by integration`) al crear archivos.
- El commit inicial se identifica como `Codex <codex@openai.com>` usando opciones por comando; no se configura la identidad global del usuario.

## Próximo paso propuesto

Inventariar la configuración actual del equipo y decidir qué debe reproducirse. Este trabajo queda para una siguiente sesión.
