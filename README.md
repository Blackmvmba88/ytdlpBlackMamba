# MambaFlow · Emission

<p align="center">
  <img src="docs/mambaflow-icon.svg" alt="MambaFlow BlackMamba icon" width="240">
</p>

<p align="center"><strong>Busca · descarga · escucha · visualiza.</strong></p>

Busca una canción o artista en YouTube, guarda MP3 o video y escucha tu colección con un visualizador que reacciona al audio. Fondo inmersivo de color con vúmetro de 48 bandas. Interfaz local en español, basada en el Emission Engine de BlackMamba: shaders de emisión, bloom y reflejos con una paleta verde neón, rosa, rojo, violeta y cian.

![MambaFlow](docs/desktop.png)

## Instalación rápida

### Mac · Apple Silicon

Abre la sección de **Releases**, descarga el DMG más reciente, arrastra **MambaFlow.app** a Aplicaciones y ábrelo.

<p align="center">
  <a href="https://github.com/Blackmvmba88/ytdlpBlackMamba/releases">
    <img src="docs/install-qr.svg" alt="QR para abrir las releases de MambaFlow" width="230">
  </a>
</p>

El QR apunta a la página permanente de releases del proyecto, así que no necesita cambiar cuando salga una versión nueva. El empaquetado también genera `MambaFlow-latest-arm64.dmg`, un nombre estable pensado para enlaces directos y distribución por QR cuando se publique la primera release.

> Estado actual: todavía no hay una release pública publicada en GitHub. El QR ya queda listo y empezará a servir como punto de instalación en cuanto exista la primera release.

## Abrir en Mac

Abre **MambaFlow.app**. El lanzador inicia una sola instancia en un puerto local libre y abre la interfaz en tu navegador. No necesitas localizar la carpeta del proyecto. Los archivos se guardan en `~/Downloads/MambaFlow/{audio,video}`; historial y logs en `~/Library/Application Support/MambaFlow`.

La aplicación empaqueta Python y sus dependencias. Esta versión requiere **ffmpeg instalado** (`brew install ffmpeg`) para convertir audio y combinar video. El DMG es una compilación para Apple Silicon, todavía sin firma Developer ID ni notarización.

## Desarrollo

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
bin/mambaflow
```

Validado con Python 3.14 en macOS arm64. El archivo lock registra el entorno exacto de compilación. `requirements.txt` expresa dependencias generales.

```sh
.venv/bin/python -m pytest -q
./packaging/build.sh --dmg
```

Puedes definir la versión del DMG sin editar el script:

```sh
MAMBAFLOW_VERSION=0.3.0 ./packaging/build.sh --dmg
```

El build produce tanto el archivo versionado como el alias estable:

```text
dist/MambaFlow-0.3.0-arm64.dmg
dist/MambaFlow-latest-arm64.dmg
```

## Uso

1. Escribe una canción o artista y pulsa Buscar.
2. Elige MP3 o Video. La cola muestra progreso y permite cancelar.
3. La colección de la pantalla principal se actualiza automáticamente al terminar. Pulsa Escuchar o Ver video. Los archivos existentes se reutilizan por ID y formato, incluso después de reiniciar.
4. Pausa el movimiento cuando quieras. La preferencia del sistema de reducir movimiento se respeta al iniciar.

Los archivos locales se reproducen en el navegador; no se suben. La búsqueda consulta YouTube; sus miniaturas pueden cargarse desde servidores de YouTube. El botón Activar micrófono solicita permiso al navegador. Su señal se analiza localmente, sin grabarla, subirla ni enviarla a los altavoces. Apagar micrófono detiene la captura.

Usa MambaFlow únicamente con contenido que tengas derecho a descargar o procesar y respeta los términos aplicables de cada servicio.

## Límites de esta versión

- Admite enlaces HTTPS de YouTube; la cola se limita a 100 trabajos pendientes y 20 enlaces por trabajo.
- Búsquedas de hasta 200 caracteres, ocho resultados y caché de dos minutos. Las búsquedas se serializan fuera del bucle del servidor.
- Historial atómico de hasta 1.000 entradas; cola pendiente no persistente entre reinicios.
- Cancelar es cooperativo: una operación de red o conversión activa puede tardar en detenerse.
- El formato solicitado para video es MP4; algunos códecs originales podrían no reproducirse en todos los navegadores.
- YouTube puede exigir autenticación o cambiar sus mecanismos. No se garantiza la descarga de todo contenido.
- El navegador sigue siendo la ventana de la interfaz. Cerrar su pestaña no detiene el servidor; se puede terminar MambaFlow desde Monitor de Actividad.

## Publicación

Consulta el [roadmap](ROADMAP.md), la [preparación de release](docs/RELEASE.md), la [validación](docs/VALIDATION.md) y la [arquitectura](docs/ARCHITECTURE.md).

Para que el QR se convierta en instalación real solo falta publicar la primera release con el DMG generado por `packaging/build.sh`. Mantener el alias `MambaFlow-latest-arm64.dmg` permite añadir después un enlace directo permanente sin regenerar material impreso ni cambiar documentación.

## Repositorio

Repositorio oficial: `Blackmvmba88/ytdlpBlackMamba`, rama principal `main`.
