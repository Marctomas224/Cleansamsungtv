# Samsung UE32K5570SUXXC

| | |
|---|---|
| Tele | 32", Full HD, serie K5500 (K5570 es la variante de la serie para España) |
| Año | 2016 |
| Sistema | Tizen (generación de 2016) |
| Conexión con la herramienta | Puerto 8001 sin cifrar. Puede que no pida «Permitir». |
| Lista de apps por la red | Puede que no la dé: entonces `limpiar` revisa las apps habituales (Netflix, YouTube, Prime Video, Disney+…) |

Los menús de 2016 son distintos a los de 2017 en adelante: no hay apartado «General». Las rutas de
abajo son las de 2016. Si alguna no coincide con lo que ves en la tele, anótalo aquí.

## Qué esperar

Es una tele de gama de entrada de hace diez años. Las apps de hoy piden bastante más memoria que
cuando salió, así que va a seguir siendo más lenta que una tele nueva. Lo de abajo le quita todo lo
que le sobra, y muchas veces basta para que deje de quedarse pillada. Si después de todo sigue
igual, mira el último paso.

## El plan, en orden

Desde el ordenador, en la carpeta del repositorio:

```bash
python3 tools/samsungtv.py buscar
python3 tools/samsungtv.py diagnostico
```

1. **Actualiza el software.** Configuración > Soporte > Actualización de software > Actualizar ahora,
   y activa «Actualización automática». Un usuario con la UE32K5500, la misma serie, contaba en el foro de
   Samsung que el menú dejó de ir lento al pasar a una versión más nueva del software
   ([hilo](https://eu.community.samsung.com/t5/smart-tv/samsung-ue32k5500-nuovo-firmware-1201-6/td-p/241027)).
2. **Reinicio en frío.** Mantén pulsado el botón de encendido del mando hasta que salga el logo de
   Samsung, o desenchúfala un minuto. Hazlo cada semana: apagar con el mando no vacía la memoria.
   Puedes probar `python3 tools/samsungtv.py reiniciar`, aunque en algunos modelos solo apaga la tele.
3. **Cierra lo que se queda abierto:** `python3 tools/samsungtv.py limpiar`.
4. **Que no arranque nada solo.** Configuración > Sistema > Configuración experta: desactiva
   «Ejecución automática de Smart Hub» y «Ejecutar automáticamente la última aplicación».
5. **Fuera el seguimiento.** Configuración > Soporte > Términos y política: desactiva «Servicios de
   información de visualización» (o «SyncPlus y Marketing») y, si aparecen, «Anuncios basados en
   intereses» y el reconocimiento de voz.
6. **Borra lo que no uses y reinstala la app que se queda cargando.** Inicio > Apps > marca la app >
   mantén pulsado el botón central > Eliminar. En 2016 no hay botón de «Borrar caché»: eliminar la
   app que se queda pillada y volver a instalarla es la forma de empezar de cero.
7. **Red y DNS.** Si puedes, cable de red. Si no, acerca el router o pon un repetidor. Luego,
   Configuración > Red > Estado de red > Configuración IP > Configuración DNS > Introducir manualmente
   > `1.1.1.1`. Para comprobarlo: Configuración > Soporte > Autodiagnóstico > Prueba de conexión de
   Smart Hub.
8. **Si sigue lenta: restablece Smart Hub.** Configuración > Soporte > Autodiagnóstico > Restablecer
   Smart Hub (PIN `0000`). Borra las apps y sus sesiones, pero no los canales ni la imagen.
9. **Si ni así:** el límite es el hardware. Un Chromecast con Google TV o un Fire TV Stick por HDMI
   va fluido, y a ese aparato sí se le puede aplicar
   [cleanyourtv](https://github.com/Gathin23/cleanyourtv) para quitarle la publicidad.

La guía interactiva hace lo mismo paso a paso: `python3 tools/samsungtv.py guia --anyo 2016`.

## Notas de esta tele

Todavía no probado con la tele real. Al pasar el plan, apunta aquí qué menús tenían otro nombre,
si salió el aviso de «Permitir», si `limpiar` vio la lista completa de apps y si `reiniciar` la
reinició o solo la apagó.
