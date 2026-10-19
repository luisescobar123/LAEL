from prometheus_client import start_http_server, Counter
import time

# Definir una métrica
requests_total = Counter('lael_requests_total', 'Total de peticiones a LAEL')

# Iniciar servidor de métricas en el puerto 8000
start_http_server(8000)


#!/usr/bin/env python3

"""LAEL - Sistema Empresarial Integral (version de prueba).
Solo biblioteca estandar de Python 3.8+. Ejecutar: python3 server.py  ->  http://localhost:8080
Usuarios iniciales: admin / Admin123!   y   empleado / Empleado123!   (cambiarlos al probar)
HTTPS: si existen cert.pem y key.pem junto a este archivo, el servidor los usa."""
import sqlite3, json, os, hashlib, secrets, time, ssl, re, ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

D = os.path.dirname(os.path.abspath(__file__))
DB, HTML = os.path.join(D, 'lael.db'), os.path.join(D, 'index.html')
COLS = {'products': ['code', 'name', 'price', 'cost', 'stock', 'min_stock'],
        'customers': ['name', 'nit', 'phone', 'email', 'address'],
        'suppliers': ['name', 'nit', 'phone', 'email', 'address']}
SCHEMA = """
create table if not exists users(id integer primary key, username text unique not null, name text, role text not null, salt blob, pw text);
create table if not exists app_settings(key text primary key, value text not null);
create table if not exists devices(id text primary key, user_id integer not null references users(id) on delete cascade, label text not null, created_at text not null default (datetime('now','localtime')), last_seen text not null default (datetime('now','localtime')), revoked_at text, last_ip_address text not null default 'No disponible');
create table if not exists access_log(id integer primary key, user_id integer not null, username text not null, display_name text not null, device_id text not null, device_label text not null, accessed_at text not null default (datetime('now','localtime')), ip_address text not null default 'No disponible');
create table if not exists employee_sessions(session_id text primary key, user_id integer not null, username text not null, display_name text not null, role text not null default 'empleado', device_id text not null default '', device_label text not null, ip_address text not null, started_at text not null default (datetime('now','localtime')), last_seen text not null default (datetime('now','localtime')), ended_at text, duration_seconds integer, end_reason text);
create table if not exists products(id integer primary key, code text unique not null, name text not null, price real default 0 check(price>=0), cost real default 0 check(cost>=0), stock integer default 0 check(stock>=0), min_stock integer default 5);
create table if not exists customers(id integer primary key, name text not null, nit text, phone text, email text, address text);
create table if not exists suppliers(id integer primary key, name text not null, nit text, phone text, email text, address text);
create table if not exists invoices(id integer primary key, number text unique, customer_id integer references customers(id), date text default (datetime('now','localtime')), subtotal real, iva real, total real, user_id integer);
create table if not exists invoice_items(id integer primary key, invoice_id integer references invoices(id), product_id integer, name text, qty integer, price real);
"""
SESS, FAILS, TTL = {}, {}, 1800  # sesiones expiran a los 30 min sin actividad


def db():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('pragma foreign_keys=on')
    return c


def hp(p, s):
    return hashlib.pbkdf2_hmac('sha256', p.encode(), s, 200000).hex()


def add_user(c, u, n, r, p):
    s = secrets.token_bytes(16)
    c.execute('insert into users(username,name,role,salt,pw) values(?,?,?,?,?)', (u, n, r, s, hp(p, s)))


def init():
    c = db()
    c.executescript(SCHEMA)
    for table, column in (('devices', 'last_ip_address'), ('access_log', 'ip_address')):
        if column not in {row['name'] for row in c.execute(f'pragma table_info({table})')}:
            c.execute(f"alter table {table} add column {column} text not null default 'No disponible'")
    session_columns = {row['name'] for row in c.execute('pragma table_info(employee_sessions)')}
    for column, definition in (('role', "text not null default 'empleado'"),
                               ('device_id', "text not null default ''")):
        if column not in session_columns:
            c.execute(f'alter table employee_sessions add column {column} {definition}')
    c.execute("insert or ignore into app_settings(key,value) values('device_limit','40')")
    c.execute("insert or ignore into app_settings(key,value) values('allowed_ip_ranges','')")
    c.execute("""update employee_sessions
        set ended_at=last_seen,
            duration_seconds=max(0,cast(strftime('%s',last_seen)-strftime('%s',started_at) as integer)),
            end_reason='reinicio_servidor'
        where ended_at is null""")
    if not c.execute('select 1 from users').fetchone():
        add_user(c, 'admin', 'Administrador', 'admin', 'Admin123!')
        add_user(c, 'empleado', 'Empleado de prueba', 'empleado', 'Empleado123!')
        c.executemany('insert into products(code,name,price,cost,stock,min_stock) values(?,?,?,?,?,?)', [
            ('P001', 'Cuaderno universitario', 2.50, 1.60, 40, 10), ('P002', 'Lapicero azul', 0.35, 0.18, 120, 30),
            ('P003', 'Resma papel carta', 5.90, 4.20, 6, 8), ('P004', 'Folder manila', 0.20, 0.09, 200, 50)])
        c.executemany('insert into customers(name,nit,phone,email,address) values(?,?,?,?,?)', [
            ('Cliente de prueba S.A. de C.V.', '0614-010101-101-1', '2222-0000', 'cliente@ejemplo.com', 'San Salvador')])
        c.executemany('insert into suppliers(name,nit,phone,email,address) values(?,?,?,?,?)', [
            ('Proveedor de prueba', '0614-020202-102-2', '2233-0000', 'proveedor@ejemplo.com', 'Santa Tecla')])
    c.commit()
    c.close()


def clean(t, b):
    v = []
    for k in COLS[t]:
        x = b.get(k, '')
        if t == 'products' and k in ('price', 'cost', 'stock', 'min_stock'):
            x = float(x or 0) if k in ('price', 'cost') else int(float(x or 0))
        else:
            x = str(x).strip()
        v.append(x)
    return v


def rows(c, q, a=()):
    return [dict(r) for r in c.execute(q, a)]


def client_ip(h):
    try:
        address = ipaddress.ip_address(h.client_address[0])
        return str(getattr(address, 'ipv4_mapped', None) or address)
    except (AttributeError, IndexError, TypeError, ValueError):
        return 'No disponible'


def allowed_networks(c):
    setting = c.execute("select value from app_settings where key='allowed_ip_ranges'").fetchone()
    return [ipaddress.ip_network(value) for value in (setting['value'].splitlines() if setting else []) if value]


def ip_is_allowed(address, networks):
    if address == 'No disponible':
        return False
    client = ipaddress.ip_address(address)
    return not networks or any(client.version == network.version and client in network for network in networks)


def _close_expired_employee_sessions(c):
    c.execute("""update employee_sessions set ended_at=last_seen,
        duration_seconds=max(0,cast(strftime('%s',last_seen)-strftime('%s',started_at) as integer)),
        end_reason='inactividad'
        where role='empleado' and ended_at is null
        and last_seen<datetime('now','localtime',?)""", (f'-{TTL} seconds',))
    c.commit()


def _session_rows(c, employee=None, limit=5000):
    cutoff = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - 45))
    query = """select session_id,display_name,username,device_label,ip_address,started_at,last_seen,
        ended_at,duration_seconds,end_reason,
        case when ended_at is null and last_seen>=? then 1 else 0 end as online,
        case when ended_at is null then max(0,cast(strftime('%s','now','localtime')-strftime('%s',started_at) as integer))
             else coalesce(duration_seconds,0) end as elapsed_seconds
        from employee_sessions where role='empleado'"""
    params = [cutoff]
    if employee is not None:
        query += ' and display_name=?'
        params.append(employee)
    query += ' order by started_at desc,session_id'
    if limit is not None:
        query += ' limit ?'
        params.append(limit)
    return rows(c, query, params)


def _pdf_literal(value):
    encoded = str(value).encode('cp1252', errors='replace')
    return b'(' + encoded.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)').replace(b'\r', b' ').replace(b'\n', b' ') + b')'


def session_report_pdf(sessions, employee=None):
    generated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    title = f'LAEL | Registro de sesiones - {employee}' if employee else 'LAEL | Registro de sesiones de empleados'
    lines = [
        title[:105],
        f'Generado: {generated} (hora local del servidor)',
        'Nombre declarado; no verifica identidad. Duracion aproximada; la sesion cuenta hasta salida o inactividad.',
        f'Registros incluidos: {len(sessions)}',
        '-' * 105,
    ]
    for session in sessions:
        duration = max(0, int(session['elapsed_seconds']))
        duration_text = f'{duration // 3600:02d}:{duration % 3600 // 60:02d}:{duration % 60:02d}'
        status = 'EN LINEA' if session['online'] else ('CERRADA' if session['ended_at'] else 'INACTIVA')
        line = ' | '.join((
            session['display_name'], session['started_at'], session['ended_at'] or 'En curso',
            duration_text, status, session['device_label'], session['ip_address']))
        lines.append(line[:145])
    if not sessions:
        lines.append('No hay sesiones registradas.')
    pages = [lines[index:index + 42] for index in range(0, len(lines), 42)]
    object_data = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        2: b'',
        3: b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
    }
    page_ids = []
    for page_number, page_lines in enumerate(pages):
        page_id = 4 + page_number * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        commands = []
        for line_number, line in enumerate(page_lines):
            y = 800 - line_number * 18
            commands.extend((b'BT /F1 8 Tf 1 0 0 1 40 ' + str(y).encode() + b' Tm ',
                             _pdf_literal(line), b' Tj ET\n'))
        stream = b''.join(commands)
        object_data[page_id] = (b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                                b'/Resources << /Font << /F1 3 0 R >> >> /Contents '
                                + str(content_id).encode() + b' 0 R >>')
        object_data[content_id] = b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'endstream'
    object_data[2] = (b'<< /Type /Pages /Kids [' + b' '.join(
        str(page_id).encode() + b' 0 R' for page_id in page_ids) +
        b'] /Count ' + str(len(page_ids)).encode() + b' >>')
    total_objects = max(object_data)
    document = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0] * (total_objects + 1)
    for object_id in range(1, total_objects + 1):
        offsets[object_id] = len(document)
        document.extend(str(object_id).encode() + b' 0 obj\n' + object_data[object_id] + b'\nendobj\n')
    xref_offset = len(document)
    document.extend(b'xref\n0 ' + str(total_objects + 1).encode() + b'\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        document.extend(f'{offset:010d} 00000 n \n'.encode())
    document.extend(b'trailer\n<< /Size ' + str(total_objects + 1).encode() +
                    b' /Root 1 0 R >>\nstartxref\n' + str(xref_offset).encode() + b'\n%%EOF\n')
    return bytes(document)


def route(h, m, p, b, query=None):
    parts = p.strip('/').split('/')[1:]
    t = parts[0] if parts else ''
    remote_ip = client_ip(h)
    if t == 'login' and m == 'POST':
        access_type = str(b.get('access_type', 'admin'))
        display_name = str(b.get('display_name', '')).strip()[:80]
        u = str(b.get('username', '')).strip().lower()
        device_id = str(b.get('device_id', ''))
        if not re.fullmatch(r'[0-9a-f]{64}', device_id):
            return 400, {'error': 'No se pudo identificar este navegador. Recargue la página e intente de nuevo.'}
        device_key = hashlib.sha256(device_id.encode()).hexdigest()
        failure_key = f'employee:{device_key}' if access_type == 'employee' else u
        f = FAILS.get(failure_key, [0, 0])
        if f[0] >= 5 and time.time() < f[1]:
            return 429, {'error': 'Demasiados intentos. Espere 5 minutos.'}
        c = db()
        try:
            if not ip_is_allowed(remote_ip, allowed_networks(c)):
                return 403, {'error': 'Este acceso está fuera de la red IP autorizada por el administrador.'}
            if access_type == 'employee':
                if not display_name:
                    return 400, {'error': 'Escriba el nombre del empleado para registrar el acceso.'}
                salt = c.execute("select value from app_settings where key='staff_password_salt'").fetchone()
                password_hash = c.execute("select value from app_settings where key='staff_password_hash'").fetchone()
                r = c.execute("select * from users where role='empleado' order by id limit 1").fetchone()
                if not salt or not password_hash:
                    return 503, {'error': 'El administrador todavía no configuró la contraseña compartida del personal.'}
                password_ok = bool(salt and password_hash and secrets.compare_digest(
                    hp(str(b.get('password', '')), bytes.fromhex(salt['value'])), password_hash['value']))
                if not r:
                    return 403, {'error': 'El administrador debe crear al menos una cuenta de empleado antes de habilitar el acceso compartido.'}
                u = r['username']
                session_name = display_name
                if not password_ok:
                    FAILS[failure_key] = [f[0] + 1, time.time() + 300]
                    return 401, {'error': 'Nombre o contraseña compartida incorrectos. Solicite la clave vigente al administrador.'}
            elif access_type == 'admin':
                r = c.execute("select * from users where username=? and role='admin'", (u,)).fetchone()
                if not r or not secrets.compare_digest(hp(str(b.get('password', '')), r['salt']), r['pw']):
                    FAILS[failure_key] = [f[0] + 1, time.time() + 300]
                    return 401, {'error': 'Usuario administrador o contraseña incorrectos.'}
                session_name = r['name']
            else:
                return 400, {'error': 'Seleccione un tipo de acceso válido.'}
            if not r:
                FAILS[failure_key] = [f[0] + 1, time.time() + 300]
                return 401, {'error': 'Usuario o contraseña incorrectos'}
            c.execute('begin immediate')
            device = c.execute('select * from devices where id=?', (device_key,)).fetchone()
            if not device or device['revoked_at']:
                limit = int(c.execute("select value from app_settings where key='device_limit'").fetchone()[0])
                active = c.execute('select count(*) from devices where revoked_at is null').fetchone()[0]
                if active >= limit:
                    c.rollback()
                    return 403, {'error': f'El límite de {limit} equipos autorizados está completo. Solicite al administrador que libere un equipo o amplíe el límite.'}
                label = str(b.get('device_name', '')).strip()[:80] or 'Navegador sin nombre'
                if device:
                    c.execute("update devices set user_id=?,label=?,created_at=datetime('now','localtime'),last_seen=datetime('now','localtime'),revoked_at=null,last_ip_address=? where id=?",
                              (r['id'], label, remote_ip, device_key))
                else:
                    c.execute('insert into devices(id,user_id,label,last_ip_address) values(?,?,?,?)',
                              (device_key, r['id'], label, remote_ip))
            else:
                c.execute("update devices set user_id=?,label=?,last_seen=datetime('now','localtime'),last_ip_address=? where id=?",
                          (r['id'], str(b.get('device_name', '')).strip()[:80] or device['label'], remote_ip, device_key))
            device_label = c.execute('select label from devices where id=?', (device_key,)).fetchone()['label']
            c.execute('insert into access_log(user_id,username,display_name,device_id,device_label,ip_address) values(?,?,?,?,?,?)',
                      (r['id'], u, session_name, device_key, device_label, remote_ip))
            c.commit()
        finally:
            c.close()
        tok = secrets.token_urlsafe(32)
        session_key = hashlib.sha256(tok.encode()).hexdigest()
        c = db()
        try:
            c.execute("""insert into employee_sessions(session_id,user_id,username,display_name,role,device_id,device_label,ip_address)
                values(?,?,?,?,?,?,?,?)""",
                      (session_key, r['id'], u, session_name, r['role'], device_key, device_label, remote_ip))
            c.commit()
        finally:
            c.close()
        FAILS.pop(failure_key, None)
        SESS[tok] = {'u': {'id': r['id'], 'username': u, 'name': session_name, 'role': r['role']},
                     'device_id': device_key, 'session_id': session_key, 'exp': time.time() + TTL}
        return 200, {'token': tok}
    tok = (h.headers.get('Authorization') or '')[7:]
    s = SESS.get(tok)
    if not s or s['exp'] < time.time():
        if s:
            c = db()
            try:
                c.execute("""update employee_sessions set ended_at=last_seen,
                    duration_seconds=max(0,cast(strftime('%s',last_seen)-strftime('%s',started_at) as integer)),
                    end_reason='inactividad' where session_id=? and ended_at is null""", (s['session_id'],))
                c.commit()
            finally:
                c.close()
        SESS.pop(tok, None)
        return 401, {'error': 'Sesión vencida. Inicie sesión de nuevo.'}
    c = db()
    if not ip_is_allowed(remote_ip, allowed_networks(c)):
        c.close()
        return 403, {'error': 'Esta sesión solo funciona desde la red IP autorizada por el administrador.'}
    device_active = c.execute('select 1 from devices where id=? and revoked_at is null',
                              (s['device_id'],)).fetchone()
    if not device_active:
        c.execute("""update employee_sessions set ended_at=last_seen,
            duration_seconds=max(0,cast(strftime('%s',last_seen)-strftime('%s',started_at) as integer)),
            end_reason='equipo_revocado' where session_id=? and ended_at is null""", (s['session_id'],))
        c.commit()
        SESS.pop(tok, None)
        c.close()
        return 401, {'error': 'Este equipo ya no está autorizado. Solicite acceso al administrador.'}
    s['exp'] = time.time() + TTL
    c.execute("update devices set last_seen=datetime('now','localtime'),last_ip_address=? where id=?",
              (remote_ip, s['device_id']))
    c.execute("update employee_sessions set last_seen=datetime('now','localtime') where session_id=? and ended_at is null",
              (s['session_id'],))
    c.commit()
    u = s['u']
    admin = u['role'] == 'admin'
    try:
        if t == 'session-heartbeat':
            return 200, {'ok': 1}
        if t == 'logout' and m == 'POST':
            c.execute("""update employee_sessions set ended_at=datetime('now','localtime'),
                duration_seconds=max(0,cast(strftime('%s','now','localtime')-strftime('%s',started_at) as integer)),
                end_reason='salida' where session_id=? and ended_at is null""", (s['session_id'],))
            c.commit()
            SESS.pop(tok, None)
            return 200, {'ok': 1}
        if t == 'employee-sessions':
            if not admin:
                return 403, {'error': 'Solo el administrador puede consultar la actividad del personal'}
            if m == 'GET' and len(parts) == 1:
                _close_expired_employee_sessions(c)
                return 200, {'sessions': _session_rows(c)}
            return 405, {'error': 'Operación de actividad del personal no permitida'}
        if t == 'employee-session-report':
            if not admin:
                return 403, {'error': 'Solo el administrador puede descargar el registro de actividad del personal'}
            if m == 'GET' and len(parts) == 1:
                _close_expired_employee_sessions(c)
                employee = (query or {}).get('employee', [None])[0]
                if employee is not None and len(employee) > 80:
                    return 400, {'error': 'El nombre de empleado no es válido.'}
                sessions = _session_rows(c, employee, limit=None)
                pdf = session_report_pdf(sessions, employee)
                filename_employee = re.sub(r'[^a-zA-Z0-9_-]+', '_', employee or '').strip('_')[:40]
                filename = f"LAEL_sesiones_{filename_employee or 'todos'}_{time.strftime('%Y%m%d')}.pdf"
                return 200, pdf, 'application/pdf', filename
            return 405, {'error': 'Operación de descarga de actividad no permitida'}
        if t == 'me':
            return 200, u
        if t == 'devices':
            if not admin:
                return 403, {'error': 'Solo el administrador puede gestionar equipos autorizados'}
            if m == 'GET' and len(parts) == 1:
                limit = int(c.execute("select value from app_settings where key='device_limit'").fetchone()[0])
                active = c.execute('select count(*) from devices where revoked_at is null').fetchone()[0]
                password_configured = c.execute("select 1 from app_settings where key='staff_password_hash'").fetchone()
                password_updated = c.execute("select value from app_settings where key='staff_password_updated'").fetchone()
                return 200, {'limit': limit, 'active': active, 'current_device': s['device_id'],
                             'shared_password_configured': bool(password_configured),
                             'shared_password_updated': password_updated['value'] if password_updated else None,
                             'devices': rows(c, """select d.id,d.label,d.created_at,d.last_seen,d.revoked_at,d.last_ip_address,
                             u.username,u.name from devices d join users u on u.id=d.user_id
                             order by d.revoked_at is null desc,d.last_seen desc""")}
            if m == 'PUT' and len(parts) == 1:
                limit = int(b.get('limit', 0))
                active = c.execute('select count(*) from devices where revoked_at is null').fetchone()[0]
                if limit < 1 or limit > 10000 or limit < active:
                    return 400, {'error': f'El límite debe ser de 1 a 10000 y no puede ser menor que los {active} equipos activos.'}
                c.execute("update app_settings set value=? where key='device_limit'", (str(limit),))
                c.commit()
                return 200, {'ok': 1, 'limit': limit}
            if m == 'DELETE' and len(parts) == 2:
                device_id = parts[1]
                if not re.fullmatch(r'[0-9a-f]{64}', device_id):
                    return 400, {'error': 'Identificador de equipo inválido'}
                if device_id == s['device_id']:
                    return 400, {'error': 'No puede revocar el equipo desde el que inició sesión. Use otro equipo administrador.'}
                cur = c.execute("update devices set revoked_at=datetime('now','localtime') where id=? and revoked_at is null",
                                (device_id,))
                if not cur.rowcount:
                    return 404, {'error': 'El equipo no existe o ya estaba revocado'}
                c.execute("""update employee_sessions set ended_at=datetime('now','localtime'),
                    duration_seconds=max(0,cast(strftime('%s','now','localtime')-strftime('%s',started_at) as integer)),
                    end_reason='equipo_revocado' where device_id=? and ended_at is null""", (device_id,))
                c.commit()
                for session_token, session in list(SESS.items()):
                    if session.get('device_id') == device_id:
                        SESS.pop(session_token, None)
                return 200, {'ok': 1}
            return 405, {'error': 'Operación de equipos no permitida'}
        if t == 'staff-password':
            if not admin:
                return 403, {'error': 'Solo el administrador puede cambiar la contraseña compartida'}
            if m != 'PUT' or len(parts) != 1:
                return 405, {'error': 'Operación de contraseña compartida no permitida'}
            password = str(b.get('password', ''))
            if len(password) < 8:
                return 400, {'error': 'La contraseña compartida debe tener al menos 8 caracteres.'}
            salt = secrets.token_bytes(16)
            c.execute("insert or replace into app_settings(key,value) values('staff_password_salt',?)",
                      (salt.hex(),))
            c.execute("insert or replace into app_settings(key,value) values('staff_password_hash',?)",
                      (hp(password, salt),))
            c.execute("insert or replace into app_settings(key,value) values('staff_password_updated',datetime('now','localtime'))")
            c.execute("""update employee_sessions set ended_at=datetime('now','localtime'),
                duration_seconds=max(0,cast(strftime('%s','now','localtime')-strftime('%s',started_at) as integer)),
                end_reason='clave_actualizada' where role='empleado' and ended_at is null""")
            c.commit()
            for session_token, session in list(SESS.items()):
                if session['u']['role'] == 'empleado':
                    SESS.pop(session_token, None)
            return 200, {'ok': 1, 'message': 'Contraseña compartida actualizada. Los empleados deberán iniciar sesión con la clave nueva.'}
        if t == 'network-access':
            if not admin:
                return 403, {'error': 'Solo el administrador puede configurar el acceso por red'}
            if m == 'GET' and len(parts) == 1:
                return 200, {'client_ip': remote_ip,
                             'ranges': [str(network) for network in allowed_networks(c)]}
            if m == 'PUT' and len(parts) == 1:
                raw_ranges = str(b.get('ranges', '')).strip()
                if len(raw_ranges) > 2048:
                    return 400, {'error': 'La lista de redes no puede exceder 2048 caracteres.'}
                try:
                    networks = [ipaddress.ip_network(value.strip(), strict=False)
                                for value in re.split(r'[\s,;]+', raw_ranges) if value.strip()]
                except ValueError:
                    return 400, {'error': 'Red o dirección IP inválida. Use direcciones IP o rangos CIDR, por ejemplo 192.168.1.0/24.'}
                if len(networks) > 50:
                    return 400, {'error': 'Se permiten como máximo 50 redes autorizadas.'}
                if networks and not ip_is_allowed(remote_ip, networks):
                    return 400, {'error': f'Incluya la IP actual del administrador ({remote_ip}) para evitar bloquear su propio acceso.'}
                normalized = '\n'.join(dict.fromkeys(str(network) for network in networks))
                c.execute("update app_settings set value=? where key='allowed_ip_ranges'", (normalized,))
                c.commit()
                return 200, {'ok': 1, 'ranges': normalized.splitlines()}
            return 405, {'error': 'Operación de control de red no permitida'}
        if t == 'access-log':
            if not admin:
                return 403, {'error': 'Solo el administrador puede consultar el historial de accesos'}
            if m == 'GET' and len(parts) == 1:
                return 200, rows(c, """select id,display_name,username,device_label,accessed_at,ip_address
                    from access_log order by id desc limit 500""")
            return 405, {'error': 'Operación de historial no permitida'}
        if t == 'dashboard':
            return 200, {
                'today': c.execute("select coalesce(sum(total),0) from invoices where date(date)=date('now','localtime')").fetchone()[0],
                'month': c.execute("select coalesce(sum(total),0) from invoices where strftime('%Y-%m',date)=strftime('%Y-%m','now','localtime')").fetchone()[0],
                'products': c.execute('select count(*) from products').fetchone()[0],
                'customers': c.execute('select count(*) from customers').fetchone()[0],
                'low': rows(c, 'select name,stock,min_stock from products where stock<=min_stock order by stock'),
                'top': rows(c, 'select name,sum(qty) q from invoice_items group by product_id order by q desc limit 5'),
                'sales_7d': rows(c, """select date(date) day,coalesce(sum(total),0) total
                from invoices where date(date)>=date('now','localtime','-6 days')
                and date(date)<=date('now','localtime') group by date(date) order by day""")}
        if t in COLS:
            if m == 'GET':
                return 200, rows(c, f'select * from {t} order by id desc')
            if m in ('POST', 'PUT'):
                if not str(b.get('name', '')).strip() or (t == 'products' and not str(b.get('code', '')).strip()):
                    return 400, {'error': 'Complete los campos obligatorios'}
                v, cols = clean(t, b), COLS[t]
                if m == 'POST':
                    c.execute(f'insert into {t}({",".join(cols)}) values({",".join("?" * len(cols))})', v)
                else:
                    c.execute(f'update {t} set {",".join(k + "=?" for k in cols)} where id=?', v + [int(parts[1])])
            elif m == 'DELETE':
                if not admin:
                    return 403, {'error': 'Solo el administrador puede eliminar'}
                c.execute(f'delete from {t} where id=?', (int(parts[1]),))
            c.commit()
            return 200, {'ok': 1}
        if t == 'invoices':
            if m == 'GET' and len(parts) == 1:
                return 200, rows(c, "select i.*,coalesce(c.name,'Consumidor final') customer from invoices i left join customers c on c.id=i.customer_id order by i.id desc limit 200")
            if m == 'GET':
                i = c.execute("select i.*,coalesce(c.name,'Consumidor final') customer from invoices i left join customers c on c.id=i.customer_id where i.id=?", (int(parts[1]),)).fetchone()
                if not i:
                    return 404, {'error': 'No existe'}
                return 200, {**dict(i), 'items': rows(c, 'select * from invoice_items where invoice_id=?', (i['id'],))}
            if m == 'POST':
                items, sub, lines = b.get('items') or [], 0, []
                if not items:
                    return 400, {'error': 'Agregue al menos un producto'}
                c.execute('begin immediate')
                for it in items:
                    q = int(it.get('qty', 0))
                    pr = c.execute('select * from products where id=?', (int(it['product_id']),)).fetchone()
                    if not pr or q <= 0:
                        return 400, {'error': 'Producto o cantidad inválidos'}
                    if pr['stock'] < q:
                        return 400, {'error': f'Stock insuficiente: {pr["name"]}'}
                    lines.append((pr, q))
                    sub += pr['price'] * q
                iva = round(sub * 0.13, 2)
                sub = round(sub, 2)
                num = 'F-%06d' % (c.execute('select coalesce(max(id),0)+1 from invoices').fetchone()[0])
                cur = c.execute('insert into invoices(number,customer_id,subtotal,iva,total,user_id) values(?,?,?,?,?,?)',
                                (num, b.get('customer_id') or None, sub, iva, round(sub + iva, 2), u['id']))
                for pr, q in lines:
                    c.execute('insert into invoice_items(invoice_id,product_id,name,qty,price) values(?,?,?,?,?)', (cur.lastrowid, pr['id'], pr['name'], q, pr['price']))
                    c.execute('update products set stock=stock-? where id=?', (q, pr['id']))
                c.commit()
                return 200, {'id': cur.lastrowid}
        if t == 'users' and admin:
            if m == 'GET':
                return 200, rows(c, 'select id,username,name,role from users order by id')
            if m == 'POST':
                if b.get('role') not in ('admin', 'empleado') or len(str(b.get('password', ''))) < 8 or not str(b.get('username', '')).strip():
                    return 400, {'error': 'Usuario, rol y contraseña (mínimo 8 caracteres) son obligatorios'}
                add_user(c, b['username'].strip().lower(), b.get('name', ''), b['role'], b['password'])
            elif m == 'DELETE':
                if int(parts[1]) == u['id']:
                    return 400, {'error': 'No puede eliminar su propio usuario'}
                target = c.execute('select id,role from users where id=?', (int(parts[1]),)).fetchone()
                if target and target['role'] == 'empleado':
                    employees = c.execute("select count(*) from users where role='empleado'").fetchone()[0]
                    if employees <= 1:
                        return 400, {'error': 'No puede eliminar al último usuario empleado; es necesario para el acceso compartido del personal.'}
                c.execute("""update employee_sessions set ended_at=datetime('now','localtime'),
                    duration_seconds=max(0,cast(strftime('%s','now','localtime')-strftime('%s',started_at) as integer)),
                    end_reason='cuenta_eliminada' where user_id=? and ended_at is null""", (int(parts[1]),))
                c.execute('delete from users where id=?', (int(parts[1]),))
            c.commit()
            return 200, {'ok': 1}
        return 404, {'error': 'No encontrado'}
    except sqlite3.IntegrityError:
        return 400, {'error': 'Dato duplicado o inválido (revise código o usuario repetido)'}
    except (ValueError, KeyError, TypeError):
        return 400, {'error': 'Datos inválidos'}
    finally:
        c.close()


class H(BaseHTTPRequestHandler):
    def out(self, code, obj, ct='application/json', content_disposition=None):
        d = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        for k, v in (('Content-Type', ct), ('Content-Length', len(d)), ('X-Content-Type-Options', 'nosniff'),
                     ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'no-referrer'), ('Cache-Control', 'no-store'),
                     ('Strict-Transport-Security', 'max-age=31536000')):
            self.send_header(k, str(v))
        if content_disposition:
            self.send_header('Content-Disposition', content_disposition)
        self.end_headers()
        self.wfile.write(d)

    def go(self, m):
        p = self.path.split('?')[0]
        query = parse_qs(self.path.partition('?')[2])
        if not p.startswith('/api/'):
            return self.out(200, open(HTML, 'rb').read(), 'text/html; charset=utf-8') if m == 'GET' else self.out(405, {})
        n = int(self.headers.get('Content-Length') or 0)
        try:
            b = json.loads(self.rfile.read(n)) if n else {}
            assert isinstance(b, dict)
        except Exception:
            return self.out(400, {'error': 'JSON inválido'})
        result = route(self, m, p, b, query)
        if len(result) == 4:
            code, body, content_type, filename = result
            return self.out(code, body, content_type, f'attachment; filename="{filename}"')
        self.out(*result)

    do_GET = lambda s: s.go('GET')
    do_POST = lambda s: s.go('POST')
    do_PUT = lambda s: s.go('PUT')
    do_DELETE = lambda s: s.go('DELETE')

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    init()
    srv = ThreadingHTTPServer((os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', 8080))), H)
    cert, key = os.path.join(D, 'cert.pem'), os.path.join(D, 'key.pem')
    if os.path.exists(cert) and os.path.exists(key):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    print('LAEL en ejecución: %s://%s:%s' % ('https' if os.path.exists(cert) else 'http', *srv.server_address))
    srv.serve_forever()
if __name__ == "__main__":
    # Iniciar servidor de métricas en el puerto 8000
    start_http_server(8000)
