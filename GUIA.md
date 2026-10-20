# Guía de ajustes para una Samsung lenta

<!-- Generado con `python3 tools/samsungtv.py guia --markdown > GUIA.md`; edita GUIDE en tools/samsungtv.py, no este archivo. -->

Lo que la tele no deja cambiar por la red se cambia con el mando. Ve en orden: los primeros pasos son los que más ayudan. Los nombres de los menús pueden variar un poco según el modelo y la versión del software.

`python3 tools/samsungtv.py guia` te lleva paso a paso y salta lo que tu tele no tiene.

## 1. Actualiza el software de la tele

*Impacto: alto*

Samsung sigue corrigiendo fallos de memoria y de las apps de vídeo años después de la venta. Una tele que nunca se ha actualizado arrastra errores que ya están resueltos.

- **Teles de 2016:** Configuración > Soporte > Actualización de software > Actualizar ahora. Activa también «Actualización automática».
- **Teles de 2017 a 2021:** Configuración > Soporte > Actualización de software > Actualizar ahora. Activa también «Actualización automática».
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > Soporte > Actualización de software > Actualizar ahora.

## 2. Haz un reinicio en frío (y repítelo cada semana)

*Impacto: alto*

Apagar con el mando no apaga la tele: queda en reposo con la memoria llena de lo que tenías abierto («Inicio instantáneo»). Tras semanas así se vuelve lenta y las apps se quedan cargando. Un reinicio de verdad lo vacía todo.

- **Teles de 2016:** Con la tele encendida, mantén pulsado el botón de encendido del mando hasta que la pantalla se apague y vuelva a salir el logo de Samsung (unos 5 segundos). Si no funciona, desenchúfala 1 minuto.
- **Teles de 2017 a 2021:** Con la tele encendida, mantén pulsado el botón de encendido del mando hasta que la pantalla se apague y vuelva a salir el logo de Samsung (unos 5 segundos). Si no funciona, desenchúfala 1 minuto.
- **Teles de 2022 en adelante:** Igual: mantén pulsado el botón de encendido hasta ver el logo de Samsung, o desenchúfala 1 minuto.

La herramienta lo intenta con `python3 tools/samsungtv.py reiniciar`.

## 3. Que no se abran apps solas al encender

*Impacto: medio*

Por defecto la tele arranca Smart Hub, la última app que usaste y a veces Samsung TV Plus en cuanto se enciende, y todas compiten por la poca memoria que tiene.

- **Teles de 2016:** Configuración > Sistema > Configuración experta: desactiva «Ejecución automática de Smart Hub» y «Ejecutar automáticamente la última aplicación».
- **Teles de 2017 a 2021:** Configuración > General > Funciones inteligentes: desactiva «Ejecución automática de Smart Hub», «Ejecutar automáticamente la última aplicación» y, si aparece, «Ejecución automática de Samsung TV Plus».
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > General y privacidad > Opciones de la pantalla de inicio (o «Funciones inteligentes»): desactiva el inicio automático de Smart Hub, de la última aplicación y de Samsung TV Plus.

## 4. Apaga el seguimiento y la publicidad en segundo plano

*Impacto: medio*

«Servicios de información de visualización» analiza continuamente lo que sale en pantalla (también por HDMI) para enviárselo a Samsung y sus anunciantes. Gasta procesador y red, y no te aporta nada.

- **Teles de 2016:** Configuración > Soporte > Términos y política: desactiva «Servicios de información de visualización» (en algunos modelos se llama «SyncPlus y Marketing») y, si aparecen, «Anuncios basados en intereses» y los servicios de reconocimiento de voz.
- **Teles de 2017 a 2021:** Configuración > Soporte > Términos y privacidad > Configuración de privacidad (o «Términos y políticas»): desactiva «Servicios de información de visualización» y «Anuncios basados en intereses». Si no hablas a la tele, desactiva también los servicios de reconocimiento de voz.
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > General y privacidad > Términos y privacidad: desactiva «Servicios de información de visualización» y «Anuncios basados en intereses». En General y privacidad > Voz desactiva «Activación por voz» si no usas Bixby/Alexa.

## 5. Borra las apps que no usas

*Impacto: medio*

Muchas teles traen unas 2-4 GB de almacenamiento y menos de 2 GB de memoria. Con el almacenamiento casi lleno las apps no pueden guardar su caché y cargan todo de nuevo cada vez.

- **Teles de 2016:** Inicio > Apps (el icono de tres cuadrados) > marca la app > mantén pulsado el botón central del mando > Eliminar > Sí.
- **Teles de 2017 a 2021:** Inicio > Apps > Configuración (rueda arriba a la derecha) > selecciona la app > Eliminar.
- **Teles de 2022 en adelante:** Inicio > Apps > Configuración de apps (rueda) > selecciona la app > Eliminar.

`python3 tools/samsungtv.py apps` lista lo que tienes instalado.

## 6. Pasa el «Cuidado del dispositivo»

*Impacto: medio · teles de 2020 en adelante*

Desde 2020 la tele trae un limpiador que cierra procesos y libera memoria.

- **Teles de 2017 a 2021:** Configuración > Soporte > Cuidado del dispositivo > Iniciar cuidado del dispositivo.
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Iniciar cuidado del dispositivo.

## 7. Vacía la caché de la app que se queda cargando

*Impacto: alto*

Una caché corrupta es la causa más habitual de que una app concreta (Netflix, YouTube, Prime Video, Disney+...) se quede en la pantalla de carga.

- **Teles de 2016:** No hay botón para vaciar la caché: elimina la app (paso «apps») y vuelve a instalarla desde Apps; al reinstalarla empieza limpia.
- **Teles de 2017 a 2021:** En teles de 2020-2021: Configuración > Soporte > Cuidado del dispositivo > Gestionar almacenamiento > marca la app > Ver detalles > Borrar caché. En 2017-2019 no existe ese botón: elimina la app y vuelve a instalarla desde Apps.
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Gestionar almacenamiento > marca la app > Ver detalles > Borrar caché.

## 8. Mejora la conexión

*Impacto: alto*

Si la serie se para a cargar a mitad, casi siempre es la red y no la tele: el Wi-Fi de las teles es flojo y está detrás del mueble. Netflix pide unos 5 Mbps en HD y 15-25 Mbps en 4K.

- **Teles de 2016:** Si puedes, conecta un cable de red. Si no, acerca el router o pon un repetidor, y usa la red de 5 GHz si tu tele la ve. Comprueba con Configuración > Soporte > Autodiagnóstico > Prueba de conexión de Smart Hub.
- **Teles de 2017 a 2021:** Si puedes, conecta un cable de red. Si no, usa la red de 5 GHz del router y acerca el router o pon un repetidor. Comprueba con Configuración > Soporte > Autodiagnóstico > Prueba de conexión de Smart Hub.
- **Teles de 2022 en adelante:** Si puedes, conecta un cable de red. Si no, usa la red de 5 GHz. Comprueba con Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Autodiagnóstico > Prueba de conexión de Smart Hub.

## 9. Cambia el DNS

*Impacto: medio*

El DNS de muchas operadoras es lento o falla a ratos, y la tele se queda «cargando» antes de empezar a reproducir. Un DNS público suele arreglarlo.

- **Teles de 2016:** Configuración > Red > Estado de red > Configuración IP > Configuración DNS: Introducir manualmente > 1.1.1.1 (o 8.8.8.8) > Aceptar.
- **Teles de 2017 a 2021:** Configuración > General > Red > Estado de red > Configuración IP > Configuración DNS: Introducir manualmente > 1.1.1.1 (o 8.8.8.8) > Aceptar.
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > Conexión > Red > Estado de red > Configuración IP > Configuración DNS: Introducir manualmente > 1.1.1.1 (o 8.8.8.8) > Aceptar.

Opcional: 94.140.14.14 (AdGuard DNS) además bloquea los anuncios y el rastreo de Samsung en la pantalla de inicio. No quita los anuncios de YouTube. Si alguna app deja de funcionar, vuelve a «Obtener automáticamente».

## 10. Si la red no da para más, baja la calidad en la app

*Impacto: bajo*

Con una conexión justa es mejor ver en HD sin cortes que en 4K parándose cada minuto.

- **Teles de 2016:** Dentro de cada app: en Netflix, desde netflix.com > Cuenta > Perfil > Uso de datos; en YouTube, en el vídeo > Configuración > Calidad.
- **Teles de 2017 a 2021:** Dentro de cada app: en Netflix, desde netflix.com > Cuenta > Perfil > Uso de datos; en YouTube, en el vídeo > Configuración > Calidad.
- **Teles de 2022 en adelante:** Igual que en teles anteriores: la calidad se elige dentro de cada app.

## 11. Último recurso: restablece Smart Hub

*Impacto: alto*

Borra todas las apps, sus datos y sesiones, pero no tus canales ni los ajustes de imagen. Arregla la mayoría de teles que siguen lentas después de todo lo anterior.

- **Teles de 2016:** Configuración > Soporte > Autodiagnóstico > Restablecer Smart Hub (PIN por defecto: 0000).
- **Teles de 2017 a 2021:** Configuración > Soporte > Autodiagnóstico > Restablecer Smart Hub (PIN por defecto: 0000).
- **Teles de 2022 en adelante:** Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Autodiagnóstico > Restablecer Smart Hub (PIN por defecto: 0000).

Después tendrás que volver a instalar las apps e iniciar sesión en cada una.

## Y si nada de esto basta

Si tu tele es de 2017 o anterior y sigue lenta después de todo esto, el problema es el hardware: las apps de hoy piden más memoria de la que trae. Un Chromecast con Google TV, un Fire TV Stick o un Google TV Streamer conectado por HDMI (30-100 €) va fluido, y a ese aparato sí se le puede aplicar cleanyourtv (https://github.com/Gathin23/cleanyourtv) para quitarle la publicidad.
