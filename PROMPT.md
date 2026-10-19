# El prompt

Pega esto en Claude Code (u otro asistente con acceso a la terminal) en un ordenador conectado a
la misma red que la tele, con este repositorio abierto. Sirve para teles Samsung con Tizen
(2016 en adelante). Antes de empezar, enciende la tele y ten el mando a mano.

---

Quiero que mi tele Samsung vuelva a ir fluida: va lenta y se queda pillada cargando vídeos y series.
Mi tele es: <MODELO, p. ej. UE55NU7405, o «no lo sé»>. Usa `tools/samsungtv.py` de este repositorio
(solo necesita Python 3, sin dependencias) y sigue estos pasos. Explícame cada cosa en lenguaje
sencillo y pregúntame antes de lo que dependa de mí.

Conectar
- Ejecuta `python3 tools/samsungtv.py buscar`. Si no la encuentra, pídeme la IP (Configuración > General
  > Red > Estado de red) y usa `--ip`.
- Avísame antes de la primera conexión: la tele mostrará un aviso y tengo que pulsar «Permitir».
- Si la tele es de 2015 o anterior, la herramienta no puede conectarse: salta directamente a la guía.

Diagnosticar
- Ejecuta `info` y `diagnostico`. Resúmeme qué has visto: año, memoria esperable para ese año, Wi-Fi o
  cable, estabilidad de la conexión y apps abiertas.
- Pregúntame qué falla exactamente: ¿toda la tele va lenta, o una app concreta se queda cargando? ¿Al
  empezar el vídeo o a mitad? Lo primero apunta a memoria o caché; a mitad, a la red.

Limpiar
- Ejecuta `limpiar` y dime qué apps ha cerrado.
- Ofréceme el reinicio en frío. Pregúntame antes de lanzar `reiniciar`, porque corta lo que esté viendo.
  Si la tele solo se apaga, explícame cómo hacerlo con el mando.

Ajustes con el mando
- Recorre conmigo los pasos de `GUIA.md` que encajen con mi caso y con el año de mi tele, de uno en
  uno: dime el menú exacto, espera a que te diga que lo he hecho y pasa al siguiente. Empieza por los
  de impacto alto.
- Antes de «Restablecer Smart Hub», avísame de que borra las apps y las sesiones, y pregúntame.
- Para el DNS, explícame la opción de AdGuard (bloquea anuncios de la pantalla de inicio, no los de
  YouTube) y cómo deshacerlo, y déjame elegir.

Comprobar
- Al final, vuelve a ejecutar `diagnostico`, abre con `abrir` la app que me daba problemas y
  pregúntame si ahora carga bien.
- Si la tele es de 2017 o anterior y sigue lenta, dímelo con franqueza: el límite es el hardware, y un
  dispositivo HDMI (Chromecast con Google TV, Fire TV Stick) es la solución definitiva.

---

Calcula unos 15-20 minutos, casi todos con el mando en la mano.
