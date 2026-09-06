# Preparación para DMG y repositorio

## Compilación

`packaging/build.sh --dmg` genera `dist/MambaFlow.app` y `dist/MambaFlow-0.2.0-arm64.dmg`, con acceso a Applications. La arquitectura actual es arm64; para Intel debe compilarse y probarse en un entorno x86_64. PyInstaller usa firma ad-hoc para ejecución local, no una identidad Developer ID.

## Antes de distribución pública

- Instalar y probar en un Mac limpio; ffmpeg es por ahora un prerrequisito externo.
- Resolver redistribución y licencias de ffmpeg antes de incluirlo en el bundle.
- Firmar con Developer ID, habilitar y probar hardened runtime, notarizar y staplear con credenciales de Apple del propietario.
- Probar descarga real de contenido autorizado, conversión MP3, combinación de video, actualización y desinstalación.
- Revisar las licencias de dependencias y decidir la licencia del código propio.

## Repositorio

Repositorio local independiente en `~/MambaFlow`, rama `main`. La copia de origen permanece dentro de XarvisCore. `packaging/export_source.py` genera un ZIP independiente con lista explícita de archivos; no incluye entornos, cookies, descargas, logs ni la copia anidada histórica. Incluye CI para pruebas y documentación. No se crea ni publica un repositorio remoto automáticamente.

No se han firmado, notarizado ni publicado releases en servicios externos.
