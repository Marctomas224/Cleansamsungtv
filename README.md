# CleanSamsungTV

Haz que una tele Samsung lenta vuelva a ir fluida: que no se quede pillada al abrir apps ni
cargando a mitad de una serie. Desde el ordenador, por Wi-Fi, **sin instalar nada en la tele,
sin modo desarrollador y sin tocar nada que no se pueda deshacer.**

Inspirado en [cleanyourtv](https://github.com/Gathin23/cleanyourtv), que hace lo mismo para
Android TV. Las Samsung usan **Tizen**, que no tiene ADB: no se pueden desactivar paquetes del
sistema ni cambiar el launcher. Lo que sí permiten es controlarlas por la red local (lo que usa
la app SmartThings), y con eso esta herramienta:

- **Diagnostica** la tele: modelo, año, si va por Wi-Fi o cable, la estabilidad de la conexión
  y cuántas apps hay abiertas ocupando memoria. Te dice qué hacer y en qué orden.
- **Limpia** la memoria cerrando las apps que se quedan abiertas en segundo plano.
- **Reinicia en frío** la tele (apagar con el mando no vacía la memoria).
- **Te guía** por los ajustes que solo se cambian con el mando, con los menús de tu año de tele:
  caché de apps, DNS, autoarranque de Smart Hub, seguimiento en segundo plano y más.

## Por qué va lenta una Samsung

1. **Nunca se apaga de verdad.** Con «Inicio instantáneo», el botón de apagar la deja en reposo
   con la memoria tal cual. Tras semanas así, todo va a trompicones.
2. **Poca memoria para las apps de hoy.** Las teles de hace unos años traen 1-1,5 GB. Netflix,
   YouTube o Disney+ piden cada vez más.
3. **Cosas que arrancan solas**: Smart Hub, la última app, Samsung TV Plus y el análisis de lo que
   ves («Servicios de información de visualización»), que corre todo el rato.
4. **Caché corrupta** de una app concreta: la causa típica de que se quede en la pantalla de carga.
5. **La red**: Wi-Fi flojo detrás del mueble o un DNS de la operadora lento al empezar cada vídeo.

## Empezar

Solo necesitas **Python 3.8 o más nuevo** (en Windows, desde [python.org](https://www.python.org/downloads/);
en Mac y Linux ya viene) y un ordenador en la misma red que la tele. Ninguna librería extra.

```bash
git clone https://github.com/marctomas224/cleansamsungtv
cd cleansamsungtv

python3 tools/samsungtv.py buscar        # encuentra la tele y la recuerda
python3 tools/samsungtv.py diagnostico   # qué le pasa y qué hacer
python3 tools/samsungtv.py limpiar       # cierra las apps abiertas en segundo plano
python3 tools/samsungtv.py guia          # paso a paso por los ajustes del mando
```

En Windows escribe `python` en lugar de `python3`.

La primera vez que se conecta, **la tele muestra un aviso: pulsa «Permitir»** con el mando. Solo
pasa una vez; el permiso se guarda en `~/.cleansamsungtv.json`.

Si `buscar` no la encuentra, mira la IP en la tele (Configuración > General > Red > Estado de red)
y pásala con `--ip 192.168.1.50`, o pon `TV_HOST=192.168.1.50` en el entorno.

## Todos los comandos

| Comando | Qué hace |
|---|---|
| `buscar` | Busca teles Samsung en tu red y guarda la IP si solo hay una. |
| `info` | Modelo, año, sistema, resolución, Wi-Fi o cable. `--json` muestra la respuesta completa. |
| `diagnostico` | Revisa la tele y la conexión, y te da los pasos ordenados para tu caso. |
| `apps` | Lista las apps instaladas y marca con `*` las que están abiertas en memoria. |
| `limpiar` | Cierra todas las apps abiertas y vuelve al inicio. |
| `reiniciar` | Reinicio en frío: mantiene pulsado el botón de encendido 5 s. Experimental, ver abajo. |
| `guia` | Guía interactiva de ajustes. `--anyo 2018` si no la detecta; `--markdown` la imprime entera. |
| `abrir <app>` / `cerrar <app>` | Abre o cierra una app por su nombre: `abrir netflix`. |
| `tecla <teclas…>` | Pulsa teclas del mando: `tecla home`, `tecla volup volup`, `tecla KEY_SOURCE`. |

La guía completa, por si prefieres leerla: [GUIA.md](GUIA.md).

## Qué teles funcionan

| Año (letra del modelo) | Herramienta | Guía |
|---|---|---|
| 2018 en adelante (NU, RU, TU, AU, BU, CU, DU; QLED Q…R, Q…T, QN…A…) | Sí, con aviso de «Permitir» la primera vez | Sí |
| 2016-2017 (KU, KS, MU) | Sí, sin aviso | Sí |
| 2015 o anterior (JU, HU…) | No: usan un protocolo antiguo | Sí, con menús parecidos |

El año sale del nombre del modelo, en la etiqueta trasera o en Configuración > Soporte > Acerca de
este TV: en `UE55MU6100` la `M` es 2017; en `UE50RU7105`, la `R` es 2019.

## Lo que no puede hacer (y por qué)

- **Desinstalar o desactivar apps del sistema.** Tizen no lo permite desde fuera; las apps
  que instalaste tú se borran desde la tele (paso «apps» de la guía).
- **Cambiar ajustes** como el DNS o la privacidad. La API de la tele no da acceso a ellos; por eso
  están en la guía.
- **`reiniciar` no funciona en todos los modelos.** En unos, mantener pulsado el encendido
  reinicia la tele; en otros solo la apaga. Si se apaga, enciéndela con el mando y haz el
  reinicio en frío a mano: mantén pulsado el botón de encendido del mando hasta ver el logo de
  Samsung, o desenchúfala un minuto.

Si tu tele es de 2017 o anterior y sigue lenta después de todo, el límite es el hardware. Un
Chromecast con Google TV o un Fire TV Stick por HDMI va fluido, y a ese aparato sí se le puede
aplicar [cleanyourtv](https://github.com/Gathin23/cleanyourtv) para quitarle la publicidad.

## Con Claude Code

Como en cleanyourtv, puedes pegar [PROMPT.md](PROMPT.md) en Claude Code (u otro asistente con
acceso a la terminal) con este repo abierto, y te lleva de principio a fin.

## ¿Es seguro?

- No instala nada en la tele ni activa el modo desarrollador. Habla con la misma API que usa la
  app SmartThings, y solo dentro de tu red.
- La tele usa un certificado autofirmado que ningún ordenador reconoce, así que la herramienta no
  lo verifica. La conexión no sale de tu red local.
- Para quitarle el permiso: Configuración > General > Administrador de dispositivos externos >
  Administrador de conexión de dispositivos > Lista de dispositivos, y borra CleanSamsungTV.
- Lo que cambies con la guía se deshace en el mismo menú. El único paso que borra algo es
  «Restablecer Smart Hub», y te avisa antes.

## Desarrollo

```bash
python3 -m unittest discover -s tests -v
```

Los tests usan una tele simulada (`tests/mock_tv.py`) con la misma API REST y WebSocket que una
Samsung real. La guía vive en `GUIDE` dentro de `tools/samsungtv.py`; si la cambias, regenera
`GUIA.md` con `python3 tools/samsungtv.py guia --markdown > GUIA.md` (un test lo comprueba).
