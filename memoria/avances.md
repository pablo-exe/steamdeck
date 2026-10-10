# Registro de avances

## 2026-10-10 — Estructura inicial

- Se reutilizó el checkout existente en `/home/deck/steamdeck` como workspace.
- Se creó `memoria/` con el estado del proyecto y este registro.
- Se añadieron `README.md`, instrucciones para futuras sesiones en `AGENTS.md` y exclusiones iniciales en `.gitignore`.
- Se mantuvo el alcance de la sesión en la estructura documental inicial.
- Se verificó por la integración de GitHub que el repositorio es público y está vacío.
- La publicación quedó bloqueada: el acceso SSH no consigue resolver `github.com` al omitir la configuración SSH del sistema que falla por permisos; la escritura mediante la integración de GitHub devuelve HTTP 403.
- Se prepara un commit local con autoría del asistente, sin cambiar la configuración global de Git. La subida queda pendiente hasta disponer de acceso de escritura operativo.

## 2026-10-10 — Decky y plugins

- Con la red habilitada, se publicó por SSH el commit inicial pendiente, omitiendo la configuración SSH global mediante `ssh -F /dev/null`.
- Se inventariaron 13 plugins, se contrastaron tienda estable y releases de sus autores y se verificó que Decky Loader v3.2.10 ya estaba actualizado.
- Por decisión explícita del usuario, se retiró «Lossless Scaling» 0.8.1 y se conservó Decky LSFG-VK.
- Se actualizaron Framegen a 0.17, LSFG-VK a 0.14.4, PlayTime a 3.3.1, HLTB a 2.0.12 y Pause Games a 1.0.2-4bf4b4e. Los otros 7 plugins ya estaban actualizados.
- Se creó `config/decky.lock.json` con 12 plugins, versiones fijas, URLs, hashes SHA-256 y dependencias remotas declaradas por cada paquete.
- Se añadieron `scripts/install-decky.sh`, `scripts/decky.py`, documentación y un workflow de comprobaciones de GitHub Actions.
- La preparación real descargó y verificó todos los artefactos, sus metadatos, frontends compilados y dependencias. La actualización real utilizó el instalador de Decky por su API local autenticada.
- La interfaz de Decky recuperó el socket durante la actualización de Framegen. Se comprobó que la instalación había terminado correctamente y se adaptó el script para verificar el resultado y reconectar sin reenviar la mutación.
- Decky confirmó los 12 plugins cargados; la comprobación local verificó versiones, dependencias y el hash del binario de Decky. Se conservan copias privadas fuera del repositorio.
- Se añadieron pruebas de rutas ZIP, enlaces, identidad del plugin, hash de descarga, dependencias corruptas, idempotencia y recuperación de archivos ante un fallo del servicio. La instalación completa desde cero permanece pendiente de validación en una reinstalación real.
