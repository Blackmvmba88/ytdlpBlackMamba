# Roadmap de MambaFlow

Estado actual: funcional en macOS Apple Silicon, local y en preparación para distribución.

## Terminado

- Búsqueda de canciones y artistas en YouTube.
- Descarga de audio MP3 y video MP4 con cola, progreso y cancelación.
- Colección automática en la pantalla principal al terminar una descarga.
- Reutilización de archivos existentes por ID de YouTube y formato, incluso después de reiniciar.
- Reproductor integrado para audio y video.
- Fondo inmersivo con shaders, bloom, reflejos y vúmetro de 48 bandas.
- Reacción al audio reproducido y al micrófono con compresión de picos.
- Micrófono opcional con análisis local; se detiene al apagarlo o cerrar la página.
- Validación de rutas, límites de entrada, historial atómico y pruebas automatizadas.
- Lanzador de una sola instancia, aplicación `.app` y DMG arm64.
- README, arquitectura, validación y preparación de release.

## Próximo ciclo

1. Guardar el permiso/preferencia del micrófono y ofrecer un interruptor “siempre activo” en Ajustes.
2. Añadir miniatura, duración y metadatos completos a cada elemento de la colección.
3. Incorporar atajos de teclado para reproducir, pausar, avanzar y cambiar volumen.
4. Mejorar el estado de descarga con reintento y mensajes de error accionables.
5. Añadir presets visibles: MP3 320 kbps y video MP4 1080p.

## Biblioteca

- Filtros por artista, título, tipo y fecha.
- Playlists locales y cola de reproducción.
- Importación de carpetas ya existentes en `Descargas/MambaFlow`.
- Detección y reparación de archivos parciales.

## Distribución

- Compilar y probar también una variante Intel x86_64.
- Incluir o documentar ffmpeg según la licencia y el tamaño del paquete.
- Firmar con Developer ID, habilitar hardened runtime y notarizar el DMG.
- Configurar un remoto GitHub cuando el repositorio local esté listo para publicarse.
- Automatizar releases y checksums desde CI.

## No objetivos actuales

- Servidor público, multiusuario o autenticación remota.
- Subir archivos o audio del micrófono a un servicio externo.
- Reproducir contenido no autorizado.
