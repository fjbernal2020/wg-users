#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Gestor sencillo de usuarios WireGuard.'''

from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from pathlib import Path
# ---------------------------
__author__ = 'Francisco Javier Bernal Domínguez'
__license__ = 'GPL-3.0'
__version__ = '1.0.0'
__status__ = 'Production'
# ---------------------------
HEAD = 'Wireguard users v1.0'
WG_PATH = Path('/etc/wireguard') if os.geteuid() == 0 else Path.cwd()
APP_CONF = Path('app.conf')
SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9_.-]+$')
DEFAULT_PORT = 58120
DEFAULT_ADDRESS = '10.0.0.1'
DEFAULT_NETMASK = '255.255.255.0'
# ---------------------------
if os.geteuid() != 0:
    HEAD += ' MODO TEST'
# ---------------------------
class AppError(Exception):
    '''Error controlado para mostrar al usuario.'''
# ---------------------------
def ensure_environment() -> None:
    if not WG_PATH.is_dir():
        raise AppError('WireGuard parece no estar instalado')

    if not APP_CONF.is_file():
        APP_CONF.write_text(
            '[email_server]\n'
            'server: mail.server.com:587\n'
            'sender: account@server.com\n'
            'login: account@server.com:password\n'
            'tls: True\n'
            'ssl: False\n',
            encoding='utf-8',
        )
        raise AppError('El correo no está configurado, use el fichero app.conf')
# ---------------------------
def clear_screen() -> None:
    os.system('clear' if os.name != 'nt' else 'cls')
# ---------------------------
def ask_option(submenu: str, msg: str = '', red_name: str | None = None) -> str:
    clear_screen()
    print(HEAD)
    print()
    print(f"Red seleccionada: {red_name or 'ninguna'}")
    print(submenu)
    if msg:
        print(f"\n{msg}\n")
    return input('Enter para salir: ').strip()
# ---------------------------
def confirm(prompt: str) -> bool:
    return input(prompt).strip().lower() == 's'
# ---------------------------
def validate_name(name: str, label: str = 'nombre') -> str:
    name = name.strip()
    if not name:
        raise AppError(f"El {label} no puede estar vacío")
    if not SAFE_NAME_RE.fullmatch(name):
        raise AppError(
            f"El {label} solo puede contener letras, números, guion, punto y guión bajo"
        )
    return name
# ---------------------------
def network_dir(red_name: str) -> Path:
    return WG_PATH / red_name
# ---------------------------
def users_dir(red_name: str) -> Path:
    return network_dir(red_name) / 'users'
# ---------------------------
def server_conf_path(red_name: str) -> Path:
    return WG_PATH / f"{red_name}.conf"
# ---------------------------
def list_networks() -> list[str]:
    return sorted(p.stem for p in WG_PATH.glob('*.conf') if p.is_file())
# ---------------------------
def list_users(red_name: str) -> list[str]:
    udir = users_dir(red_name)
    if not udir.is_dir():
        return []
    return sorted(p.name for p in udir.iterdir() if p.is_dir())
# ---------------------------
def run_checked(args: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(args, cwd=str(cwd) if cwd else None, check=True)
    except FileNotFoundError as exc:
        raise AppError(f"No se encuentra el comando: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise AppError(f"Falló el comando: {' '.join(args)}") from exc
# ---------------------------
def generate_keypair(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    # Comando estático, sin datos de usuario interpolados en el shell.
    subprocess.run(
        ['bash', '-lc', 'umask 077 && wg genkey | tee privatekey | wg pubkey > publickey'],
        cwd=str(directory),
        check=True,
    )
# ---------------------------
def sync_wireguard(red_name: str) -> None:
    if os.geteuid() != 0:
        return
    subprocess.run(
        ['bash', '-lc', 'wg syncconf \'$1\' <(wg-quick strip \'$1\')', '_', red_name],
        check=True,
    )
# ---------------------------
def dotted_netmask_to_prefix(netmask: str) -> int:
    try:
        return IPv4Network(f"0.0.0.0/{netmask}").prefixlen
    except ValueError as exc:
        raise AppError(f"Netmask no válida: {netmask}") from exc
# ---------------------------
def read_network_config(red_name: str) -> dict[str, str]:
    cfg_file = network_dir(red_name) / 'config'
    data: dict[str, str] = {}
    for raw_line in cfg_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        data[key.strip()] = value.strip()
    required = {'red_name', 'endpoint', 'listen_port', 'address', 'netmask'}
    missing = required - set(data)
    if missing:
        raise AppError(f"Configuración incompleta. Faltan: {', '.join(sorted(missing))}")
    return data
# ---------------------------
def write_server_conf(red_name: str, content: str, mode: str = 'w') -> None:
    server_conf_path(red_name).open(mode, encoding='utf-8').write(content)
# ---------------------------
def choose_user(red_name: str) -> str | None:
    users = list_users(red_name)
    if not users:
        ask_option('\nRed sin usuarios', red_name=red_name)
        return None

    menu = '\n' + '\n'.join(f"{i + 1}.- {name}" for i, name in enumerate(users))
    user_id = ask_option(menu, red_name=red_name)
    if not user_id:
        return None
    try:
        return users[int(user_id) - 1]
    except (ValueError, IndexError):
        raise AppError('Opción de usuario no válida')
# ---------------------------
def iniciar_red(red_name: str = '') -> str | None:
    redes = list_networks()
    ask_msg = ''

    while not red_name:
        ask_msg = (ask_msg + '\nNombre de la nueva red WireGuard').strip()
        value = ask_option(ask_msg)
        if not value:
            return None
        red_name = validate_name(value, 'nombre de red')
        if red_name in redes:
            ask_msg = 'Ya existe una red con ese nombre\n'
            red_name = ''

    red_name = validate_name(red_name, 'nombre de red')
    endpoint = input('Endpoint, nombre del servidor o IP: ').strip()
    if not endpoint:
        raise AppError('El endpoint no puede estar vacío')

    listen_port = int(input(f"Puerto de escucha ({DEFAULT_PORT}): ").strip() or DEFAULT_PORT)
    address = input(f"Dirección IP del servidor en la VPN ({DEFAULT_ADDRESS}): ").strip() or DEFAULT_ADDRESS
    netmask = input(f"Netmask ({DEFAULT_NETMASK}): ").strip() or DEFAULT_NETMASK

    server_ip = IPv4Address(address)
    prefix = dotted_netmask_to_prefix(netmask)
    vpn_network = IPv4Network(f"{server_ip}/{prefix}", strict=False)

    n_dir = network_dir(red_name)
    if n_dir.exists() and confirm('La red ya tiene directorio. ¿Borrar usuarios y reiniciar? (s/N) '):
        shutil.rmtree(n_dir)

    users_dir(red_name).mkdir(parents=True, exist_ok=True)
    (n_dir / 'ip_counter').write_text('10', encoding='utf-8')
    (n_dir / 'config').write_text(
        '# Fichero de configuración\n\n'
        '# Nombre de la red wireguard\n'
        f"red_name = {red_name}\n\n"
        '# Endpoint, nombre del servidor o IP y puerto\n'
        f"endpoint = {endpoint}\n\n"
        '# Puerto de escucha\n'
        f"listen_port = {listen_port}\n\n"
        '# Dirección IP del servidor en la VPN\n'
        f"address = {server_ip}\n\n"
        '# Netmask\n'
        f"netmask = {netmask}\n\n"
        f"# Red calculada: {vpn_network}\n",
        encoding='utf-8',
    )

    generate_keypair(n_dir)
    server_privatekey = (n_dir / 'privatekey').read_text(encoding='utf-8').strip()

    write_server_conf(
        red_name,
        '[Interface]\n'
        f"Address = {server_ip}/{prefix}\n"
        f"PrivateKey = {server_privatekey}\n"
        f"ListenPort = {listen_port}\n\n",
    )
    return red_name
# ---------------------------
def next_client_ip(red_name: str, server_ip: IPv4Address, prefix: int) -> IPv4Address:
    counter_file = network_dir(red_name) / 'ip_counter'
    counter = int(counter_file.read_text(encoding='utf-8').strip() or '10')
    network = IPv4Network(f"{server_ip}/{prefix}", strict=False)

    while True:
        counter += 1
        candidate = IPv4Address(int(network.network_address) + counter)
        if candidate not in network or candidate == server_ip:
            raise AppError('No quedan direcciones libres en la red VPN')
        if not any(candidate.exploded in p.read_text(encoding='utf-8') for p in users_dir(red_name).glob('*/*.conf')):
            counter_file.write_text(str(counter), encoding='utf-8')
            return candidate
# ---------------------------
def add_user(red_name: str) -> str | None:
    existing_users = list_users(red_name)
    ask_msg = ''
    username = ''

    while not username:
        ask_msg = (ask_msg + '\nNombre del nuevo usuario').strip()
        value = ask_option(ask_msg, red_name=red_name)
        if not value:
            return None
        username = validate_name(value, 'nombre de usuario')
        if username in existing_users:
            ask_msg = 'Ya existe un usuario en la red con ese nombre\n'
            username = ''

    cfg = read_network_config(red_name)
    endpoint = cfg['endpoint']
    listen_port = int(cfg['listen_port'])
    server_ip = IPv4Address(cfg['address'])
    prefix = dotted_netmask_to_prefix(cfg['netmask'])
    vpn_network = IPv4Network(f"{server_ip}/{prefix}", strict=False)

    server_publickey = (network_dir(red_name) / 'publickey').read_text(encoding='utf-8').strip()
    user_path = users_dir(red_name) / username
    user_path.mkdir(parents=True, exist_ok=False)
    generate_keypair(user_path)

    user_privatekey = (user_path / 'privatekey').read_text(encoding='utf-8').strip()
    user_publickey = (user_path / 'publickey').read_text(encoding='utf-8').strip()
    user_ip = next_client_ip(red_name, server_ip, prefix)

    client_conf = (
        '[Interface]\n'
        f"Address = {user_ip}/{prefix}\n"
        f"PrivateKey = {user_privatekey}\n\n"
        '[Peer]\n'
        f"PublicKey = {server_publickey}\n"
        f"Endpoint = {endpoint}:{listen_port}\n"
        f"AllowedIPs = {vpn_network}\n"
        'PersistentKeepalive = 25\n'
    )
    (user_path / f"{red_name}.conf").write_text(client_conf, encoding='utf-8')

    peer_conf = (
        '[Peer]\n'
        f"# {username}\n"
        f"PublicKey = {user_publickey}\n"
        f"AllowedIPs = {user_ip}/32\n\n"
    )
    write_server_conf(red_name, peer_conf, mode="a")
    sync_wireguard(red_name)
    return f"Usuario {username} añadido a la red {red_name} con IP {user_ip}"
# ---------------------------
def show_user_conf(red_name: str) -> None:
    username = choose_user(red_name)
    if username:
        data = (users_dir(red_name) / username / f"{red_name}.conf").read_text(encoding='utf-8')
        ask_option(f"\n{data}", red_name=red_name)
# ---------------------------
def send_user_conf(red_name: str) -> None:
    username = choose_user(red_name)
    if not username:
        return

    user_email_file = users_dir(red_name) / username / 'email'
    old_email = user_email_file.read_text(encoding='utf-8').strip() if user_email_file.is_file() else ''
    prompt = f"\nIntroduzca el correo del usuario ({old_email}): " if old_email else '\nIntroduzca el correo del usuario: '
    email = input(prompt).strip() or old_email
    if not email:
        return

    try:
        from mail import Mail
    except ImportError as exc:
        raise AppError('No se puede importar mail.Mail.') from exc

    conf = configparser.ConfigParser()
    conf.read(APP_CONF)

    mail = Mail()
    mail.settings.server = conf.get('email_server', 'server')
    mail.settings.sender = conf.get('email_server', 'sender')
    mail.settings.login = conf.get('email_server', 'login')
    mail.settings.tls = conf.getboolean('email_server', 'tls')
    mail.settings.ssl = conf.getboolean('email_server', 'ssl')

    user_conf = users_dir(red_name) / username / f"{red_name}.conf"
    result = mail.send(
        to=email,
        subject=f"Wireguard VPN {red_name} para {username}",
        message=f"Adjunto dispone del fichero de configuración para acceder a la red {red_name}",
        attachments=mail.Attachment(str(user_conf), content_id='file'),
    )
    if result:
        user_email_file.write_text(email, encoding='utf-8')
        input('\nEl correo se ha enviado, pulse Enter para continuar ')
    else:
        input('\nEl correo no ha podido enviarse, pulse Enter para continuar ')
# ---------------------------
def del_user(red_name: str) -> str | None:
    username = choose_user(red_name)
    if not username:
        return None

    shutil.rmtree(users_dir(red_name) / username)

    peers = server_conf_path(red_name).read_text(encoding='utf-8').splitlines(keepends=True)
    marker = f"# {username}\n"
    new_peers: list[str] = []
    i = 0
    while i < len(peers):
        if i + 1 < len(peers) and peers[i] == '[Peer]\n' and peers[i + 1] == marker:
            i += 4
            if i < len(peers) and not peers[i].strip():
                i += 1
            continue
        new_peers.append(peers[i])
        i += 1

    server_conf_path(red_name).write_text(''.join(new_peers), encoding='utf-8')
    sync_wireguard(red_name)
    return f"Usuario {username} eliminado de la red {red_name}"
# ---------------------------
def show_conf(red_name: str) -> None:
    data = (network_dir(red_name) / 'config').read_text(encoding='utf-8')
    ask_option(f"\n{data}", red_name=red_name)
# ---------------------------
def main() -> None:
    ensure_environment()
    redes = list_networks()
    msg = ''
    red_name: str | None = None

    while True:
        menu = '\n1.- Crear nueva red'
        if redes:
            menu += '\n' + '\n'.join(f"{i + 2}.- {name}" for i, name in enumerate(redes))
        op = ask_option(menu)
        if not op or op == '0':
            break

        try:
            if op == '1':
                red_name = iniciar_red()
                if red_name:
                    redes = list_networks()
                continue

            red_name = redes[int(op) - 2]
        except (ValueError, IndexError):
            msg = 'Opción no válida'
            continue

        while True:
            menu = (
                '\n1.- Listar usuarios'
                '\n2.- Añadir usuario'
                '\n3.- Mostrar usuario'
                '\n4.- Enviar por correo'
                '\n5.- Eliminar usuario'
                '\n6.- Ver datos de red'
                '\n7.- Reiniciar red'
            )
            op = ask_option(menu, msg, red_name=red_name)
            msg = ''
            if not op or op == '0':
                break

            try:
                if op == '1':
                    users = list_users(red_name)
                    msg = 'Red sin usuarios' if not users else 'Listado de usuarios\n\n' + '\n'.join(users)
                elif op == '2':
                    msg = add_user(red_name) or ''
                elif op == '3':
                    show_user_conf(red_name)
                elif op == '4':
                    send_user_conf(red_name)
                elif op == '5':
                    msg = del_user(red_name) or ''
                elif op == '6':
                    show_conf(red_name)
                elif op == '7':
                    if confirm('¿Está seguro? este proceso reiniciará todos los datos (s/N) ') and confirm(
                        '¿Totalmente seguro? se borrarán los usuarios y todo lo demás (s/N) '
                    ):
                        msg = f'Red reiniciada: {iniciar_red(red_name)}'
                else:
                    msg = 'Opción no válida'
            except AppError as exc:
                msg = str(exc)
# ---------------------------
if __name__ == '__main__':
    try:
        main()
    except AppError as exc:
        print(exc)
# ---------------------------
