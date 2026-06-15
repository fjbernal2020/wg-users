# WireGuard Users Manager

Script en Python para crear y gestionar usuarios de WireGuard de forma sencilla desde consola.

Permite crear redes WireGuard, añadir usuarios, generar sus configuraciones, mostrar sus ficheros `.conf`, enviarlos por correo y eliminar usuarios existentes.

## Características

- Creación de una nueva red WireGuard.
- Generación automática de claves del servidor.
- Alta de usuarios/clientes.
- Generación automática de claves por usuario.
- Creación del fichero `.conf` de cada cliente.
- Listado de usuarios por red.
- Visualización de la configuración de cada usuario.
- Envío de la configuración por correo electrónico.
- Eliminación de usuarios y limpieza del peer correspondiente en el servidor.
- Modo test si no se ejecuta como `root`.
- Sin acceso entre clientes por defecto.
- Cada cliente solo puede comunicar con el servidor WireGuard.

## Modelo de red

El script está pensado para un escenario donde los clientes WireGuard **solo deben comunicarse con el servidor VPN**, no entre ellos ni con toda la red VPN.

Por ejemplo, si el servidor tiene la IP:

```ini
10.0.0.1
```

Y un cliente tiene la IP:

```ini
10.0.0.11
```

La configuración del cliente se genera de forma similar a:

```ini
[Interface]
Address = 10.0.0.11/32
PrivateKey = CLAVE_PRIVADA_DEL_CLIENTE

[Peer]
PublicKey = CLAVE_PUBLICA_DEL_SERVIDOR
Endpoint = vpn.midominio.com:58120
AllowedIPs = 10.0.0.1/32
PersistentKeepalive = 25
```

Esto significa que el cliente solo instalará una ruta hacia:

```ini
10.0.0.1/32
```

Es decir, únicamente hacia el servidor WireGuard.

En el servidor, cada cliente queda registrado como:

```ini
[Peer]
# nombre_usuario
PublicKey = CLAVE_PUBLICA_DEL_CLIENTE
AllowedIPs = 10.0.0.11/32
```

## Requisitos

- Python 3.
- WireGuard instalado.
- Comando `wg` disponible.
- Comando `wg-quick` disponible.
- Permisos de `root` para modificar `/etc/wireguard`.
- Opcionalmente, configuración SMTP para enviar ficheros por correo.

En Debian/Ubuntu:

```bash
sudo apt update
sudo apt install wireguard python3
```

## Instalación

Clona el repositorio:

```bash
git clone https://github.com/usuario/wireguard-users-manager.git
cd wireguard-users-manager
```

Da permisos de ejecución al script:

```bash
chmod +x wg_users_mejorado.py
```

Ejecuta el script:

```bash
sudo ./wg_users_mejorado.py
```

O también:

```bash
sudo python3 wg_users_mejorado.py
```

## Modo test

Si el script no se ejecuta como `root`, no usará `/etc/wireguard`.

En su lugar, trabajará sobre el directorio actual:

```bash
python3 wg_users_mejorado.py
```

En este modo se mostrará el texto:

```text
MODO TEST
```

Esto permite probar la creación de redes y usuarios sin tocar la configuración real del sistema.

## Uso

Al iniciar el script aparece un menú principal desde el que se puede:

```text
1.- Crear nueva red
2.- red_existente
3.- otra_red
```

Al seleccionar una red existente se muestran opciones como:

```text
1.- Listar usuarios
2.- Añadir usuario
3.- Mostrar usuario
4.- Enviar por correo
5.- Eliminar usuario
6.- Ver datos de red
7.- Reiniciar red
```

## Crear una nueva red

El script solicita:

- Nombre de la red.
- Endpoint del servidor.
- Puerto de escucha.
- Dirección IP del servidor dentro de la VPN.
- Máscara de red.

Ejemplo:

```text
Nombre de la nueva red wireguard: wg0
Endpoint: vpn.midominio.com
Puerto de escucha: 58120
Dirección IP del servidor en la VPN: 10.0.0.1
Netmask: 255.255.255.0
```

Esto genera una estructura similar a:

```text
/etc/wireguard/
├── wg0.conf
└── wg0/
    ├── config
    ├── ip_counter
    ├── privatekey
    ├── publickey
    └── users/
```

El fichero principal del servidor sería:

```text
/etc/wireguard/wg0.conf
```

Y la carpeta interna de gestión de la red sería:

```text
/etc/wireguard/wg0/
```

## Añadir un usuario

Al añadir un usuario, el script:

1. Genera una clave privada para el usuario.
2. Genera su clave pública.
3. Asigna una IP disponible.
4. Crea el fichero `.conf` del cliente.
5. Añade el peer al fichero del servidor.
6. Sincroniza WireGuard mediante `wg syncconf`.

La configuración del usuario se guarda en:

```text
/etc/wireguard/NOMBRE_RED/users/NOMBRE_USUARIO/NOMBRE_RED.conf
```

Ejemplo:

```text
/etc/wireguard/wg0/users/paco/wg0.conf
```

## Configuración generada para el cliente

Ejemplo de configuración de cliente:

```ini
[Interface]
Address = 10.0.0.11/32
PrivateKey = CLAVE_PRIVADA_DEL_CLIENTE

[Peer]
PublicKey = CLAVE_PUBLICA_DEL_SERVIDOR
Endpoint = vpn.midominio.com:58120
AllowedIPs = 10.0.0.1/32
PersistentKeepalive = 25
```

Puntos importantes:

- `Address = 10.0.0.11/32` asigna una IP individual al cliente.
- `AllowedIPs = 10.0.0.1/32` hace que el cliente solo enrute tráfico hacia el servidor.
- No se configura `AllowedIPs = 10.0.0.0/24`, por lo que el cliente no usa toda la red VPN.
- No se configura `AllowedIPs = 0.0.0.0/0`, por lo que no se usa la VPN como salida general a Internet.

## Configuración generada para el servidor

Por cada usuario añadido, el script añade un bloque similar a este en el fichero del servidor:

```ini
[Peer]
# paco
PublicKey = CLAVE_PUBLICA_DEL_CLIENTE
AllowedIPs = 10.0.0.11/32
```

Esto indica al servidor que la IP `10.0.0.11` pertenece a ese cliente concreto.

## Mostrar configuración de usuario

Desde el menú de la red:

```text
3.- Mostrar usuario
```

El script permite seleccionar un usuario y muestra por pantalla su fichero `.conf`.

## Enviar configuración por correo

El script puede enviar el fichero `.conf` del usuario por email.

Para ello necesita un fichero `app.conf` en el directorio desde el que se ejecuta el script.

Si no existe, el script crea una plantilla:

```ini
[email_server]
server: mail.server.com:587
sender: account@server.com
login: account@server.com:password
tls: True
ssl: False
```

Ejemplo de configuración:

```ini
[email_server]
server: smtp.midominio.com:587
sender: vpn@midominio.com
login: vpn@midominio.com:password
tls: True
ssl: False
```

El fichero `app.conf` contiene credenciales, por lo que no debería subirse al repositorio.

## Eliminar usuario

Desde el menú de la red:

```text
5.- Eliminar usuario
```

El script:

1. Elimina la carpeta del usuario.
2. Elimina sus ficheros de configuración y claves.
3. Borra el bloque `[Peer]` correspondiente del fichero del servidor.
4. Sincroniza de nuevo la configuración de WireGuard.

## Reiniciar red

Desde el menú de la red:

```text
7.- Reiniciar red
```

Esta opción debe usarse con cuidado.

El reinicio de red puede borrar usuarios, claves y configuraciones asociadas a esa red.

## Sincronización de WireGuard

Después de añadir o eliminar usuarios, el script intenta aplicar los cambios con:

```bash
wg syncconf NOMBRE_RED <(wg-quick strip NOMBRE_RED)
```

Ejemplo:

```bash
wg syncconf wg0 <(wg-quick strip wg0)
```

Esto permite actualizar la configuración sin tener que reiniciar completamente la interfaz WireGuard.

## Seguridad

Recomendaciones importantes:

- Ejecutar el script como `root` solo cuando sea necesario.
- Proteger los ficheros de claves privadas.
- No subir al repositorio ficheros generados con claves reales.
- No subir `app.conf` si contiene credenciales reales.
- Revisar los permisos de `/etc/wireguard`.
- Hacer copia de seguridad antes de reiniciar una red existente.
- Revisar manualmente la configuración generada antes de usarla en producción.

## Aislamiento de clientes

Este proyecto está diseñado para que los clientes no tengan acceso a toda la red VPN.

Cada cliente recibe:

```ini
AllowedIPs = IP_DEL_SERVIDOR/32
```

Por ejemplo:

```ini
AllowedIPs = 10.0.0.1/32
```

Por tanto, el cliente solo enruta tráfico hacia el servidor VPN.

Si se quisiera permitir acceso a toda la red VPN, habría que cambiarlo manualmente a algo como:

```ini
AllowedIPs = 10.0.0.0/24
```

Pero ese no es el comportamiento por defecto de este script.

## Salida a Internet

El script no configura la VPN como salida general a Internet.

Para enviar todo el tráfico del cliente por la VPN se usaría algo como:

```ini
AllowedIPs = 0.0.0.0/0
```

Este proyecto no usa esa configuración por defecto.

## Estructura recomendada del repositorio

```text
wireguard-users-manager/
├── wg_users_mejorado.py
├── README.md
├── LICENSE
└── .gitignore
```

## `.gitignore` recomendado

```gitignore
# Configuración local
app.conf

# WireGuard generated files
*.conf
privatekey
publickey
ip_counter
users/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Entornos virtuales
venv/
.env
```

## Archivos que no deberían subirse a GitHub

No subas al repositorio:

- Claves privadas.
- Claves públicas reales si no quieres exponer información de la instalación.
- Ficheros `.conf` generados.
- Ficheros `app.conf` con credenciales SMTP.
- Directorios reales de usuarios.
- Copias de `/etc/wireguard`.

## Licencia

GPL.

## Autor

Francisco Javier Bernal Domínguez.

## Estado del proyecto

Script en evolución para facilitar la administración básica de usuarios WireGuard.

Pensado especialmente para instalaciones sencillas donde:

- Hay uno o varios servidores WireGuard.
- Se crean clientes de forma manual.
- Cada cliente debe poder acceder solo al servidor.
- No se desea enrutar toda la red VPN ni todo Internet por el túnel.
