# Validación · 2026-09-05

- 17 pruebas pasan: URLs, modos, origen, host, traversal y symlinks, rutas de Finder, escape HTML, errores de búsqueda, caché, historial concurrente, cancelación pendiente y selección de archivos finales.
- JavaScript de interfaz y efecto pasa `node --check`.
- Render de escritorio 1440 px y móvil 390 px: sin errores JavaScript ni desbordamiento horizontal. WebGL visible y control de pausa probado. Capturas: desktop.png y mobile.png.
- Búsqueda real de “BlackMamba Records”: ocho resultados desde YouTube.
- Bundle PyInstaller arm64 ejecutado independientemente del entorno Python del proyecto: endpoint health responde versión 0.2.0 y ffmpeg disponible.
- No se realizó una descarga completa de YouTube ni se probó la app en un Mac limpio. No se ha verificado firma Developer ID/notarización.
- El entorno de pruebas emite avisos de deprecación de dependencias y datetime UTC; no son fallos de las pruebas.

Micrófono simulado: activación, apagado con pistas detenidas, reactivación y permiso denegado comprobados. Colección: aparición automática, audio y video reproducidos, archivo existente reutilizado sin nueva descarga. Sin errores JS ni desbordamiento móvil. El micrófono físico no se activó durante estas pruebas.
