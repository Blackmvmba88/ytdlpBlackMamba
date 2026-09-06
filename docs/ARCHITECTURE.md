# Arquitectura y límites

`launcher.py` reserva el socket antes del arranque y usa un bloqueo de archivo para evitar instancias duplicadas. Nunca mata procesos basándose únicamente en el puerto. FastAPI sirve HTML, assets locales y medios contenidos en la carpeta de descargas.

`shared/security.py` valida URLs de YouTube. Las rutas de reproducción y Finder se resuelven antes de comprobar pertenencia al directorio; no se usa comparación de prefijos. TrustedHost y validación de Origin/Sec-Fetch-Site protegen la interfaz local de solicitudes web cruzadas. Esto no protege frente a otros procesos maliciosos del mismo usuario y no es un servicio para exponer a Internet.

`shared/search.py` consulta metadatos planos fuera del event loop, serializa búsquedas y mantiene una caché acotada. `DownloadManager` limita la cola, gestiona workers y escribe historial mediante reemplazo atómico. Los nombres incluyen el ID del video para evitar colisiones y no se fuerzan sobrescrituras.

`emission.js` adapta los shaders aportados en preview.html: render a textura, bloom y tone mapping. El mismo MediaElementSource se reutiliza al cambiar de archivo. El micrófono opcional tiene un analizador independiente que nunca se conecta a los altavoces; detenerlo o salir de la página cierra sus pistas. Render limitado a aproximadamente 30 fps y DPR 1.25; las pestañas ocultas no dibujan. Sin WebGL se conserva el fondo CSS y la aplicación sigue disponible.

Referencias técnicas: [PyInstaller](https://pyinstaller.org/en/stable/usage.html), [yt-dlp](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp).

La escena inmersiva sustituye los interruptores de la referencia por cintas de luz a pantalla completa y 48 columnas de frecuencia con reflexión. Sin audio muestra movimiento ambiental; durante reproducción usa el espectro FFT del reproductor.

La colección se lee del disco y se refresca cada tres segundos sin interrumpir la reproducción. Identidad canónica de YouTube + modo permite reutilizar archivos y evitar trabajos iguales. Un bloqueo por contenido protege descargas simultáneas de lotes solapados.
