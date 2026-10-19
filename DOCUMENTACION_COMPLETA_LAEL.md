# Documentación completa de LAEL

**Sistema Empresarial Integral · Prototipo de prueba local**  
Propiedad indicada en la interfaz: Luis Ángel Escobar Leiva  
Versión mostrada por la aplicación: 0.1

> Esta guía describe el código y el comportamiento del prototipo actual. No es
> una especificación de un servicio comercial, asesoría jurídica, certificación
> fiscal ni garantía de seguridad. No introduzcas datos personales, financieros
> ni información real de clientes o empleados.

## Contenido

1. [Resumen y alcance](#1-resumen-y-alcance)
2. [Archivos del proyecto](#2-archivos-del-proyecto)
3. [Requisitos e inicio](#3-requisitos-e-inicio)
4. [Uso desde la misma red Wi-Fi](#4-uso-desde-la-misma-red-wi-fi)
5. [Sitio público](#5-sitio-público)
6. [Acceso y roles](#6-acceso-y-roles)
7. [Funciones de la aplicación](#7-funciones-de-la-aplicación)
8. [Usuarios, equipos, red y asistencia](#8-usuarios-equipos-red-y-asistencia)
9. [Datos y reglas de negocio](#9-datos-y-reglas-de-negocio)
10. [API local](#10-api-local)
11. [Arquitectura y almacenamiento](#11-arquitectura-y-almacenamiento)
12. [Seguridad, privacidad y límites](#12-seguridad-privacidad-y-límites)
13. [Copias de la base de prueba](#13-copias-de-la-base-de-prueba)
14. [Solución de problemas](#14-solución-de-problemas)
15. [Documentos relacionados](#15-documentos-relacionados)

## 1. Resumen y alcance

LAEL es una aplicación web servida desde una computadora Windows. El navegador
recibe una página HTML con JavaScript; un servidor Python atiende la API y
guarda los registros en una base SQLite local.

La versión actual permite probar:

- Una página pública de presentación con secciones informativas.
- Inicio de sesión administrativo y acceso del personal mediante una contraseña
  compartida configurada por el administrador.
- Un panel de resumen.
- Inventario, clientes y proveedores.
- Ventas internas de demostración, descuento de existencias y comprobantes
  imprimibles.
- Administración básica de cuentas, equipos autorizados y redes permitidas.
- Historial de accesos y sesiones aproximadas de empleados.
- Exportación CSV de los listados de inventario, clientes y proveedores, e
  informes PDF de sesiones.

No es un SaaS ni separa varias empresas. No cuenta con facturación electrónica
autorizada, pagos, suscripciones ni respaldo administrado. Los comprobantes no
tienen validez fiscal y el impuesto que muestran es solo una simulación.

## 2. Archivos del proyecto

| Archivo | Propósito |
|---|---|
| `index.html` | Página pública, inicio de sesión, aplicación y lógica del navegador. |
| `server.py` | Servidor HTTP, autenticación, API, reglas de negocio y creación inicial de la base. |
| `lael.db` | Base SQLite persistente, situada junto a `server.py`. |
| `INICIAR_LAEL_WIFI.bat` | Inicia el servidor escuchando en las interfaces de red; usa el entorno virtual del proyecto si está disponible y, si no, intenta `python`. |
| `LEEME.txt` | Instrucciones rápidas y datos/configuración particulares de esta instalación. |
| `MANUAL_LAEL.txt` | Guía de uso para el operador. |
| `POLITICAS_LAEL_BORRADOR.txt` | Borradores informativos pendientes de revisión profesional. |
| `HOJA_DE_RUTA_LAEL.txt` | Brechas conocidas y arquitectura futura propuesta. |

El archivo de base de datos contiene los registros de esta instalación. No lo
publiques ni lo compartas: incluso una base de demostración puede contener
información introducida por sus usuarios.

## 3. Requisitos e inicio

### Requisitos

- Python 3.8 o superior.
- Navegador web actualizado.
- Para acceso desde otros dispositivos, una red local compartida y reglas de
  firewall/router que permitan conectarse a la computadora servidor.

### Inicio recomendado en Windows

Abre `INICIAR_LAEL_WIFI.bat` con doble clic y deja abierta la ventana mientras
uses la aplicación. El script cambia a su propia carpeta y ejecuta `server.py`.
Primero intenta `..\.venv\Scripts\python.exe`; si ese intérprete no existe, intenta usar
`python` disponible en Windows.

El servidor escucha en el puerto **8080**. En la computadora servidor abre:

- `http://127.0.0.1:8080`

Para iniciar manualmente solo en esta computadora, abre PowerShell en la
carpeta `lael` que contiene `server.py` y ejecuta:

```powershell
python server.py
```

El inicio manual usa `127.0.0.1` por defecto. Para detener el servidor iniciado
en esa consola, presiona **Ctrl+C**. Si se inició con el archivo BAT, cierra su
ventana o presiona **Ctrl+C** en ella.

### Credenciales iniciales

En una base nueva, el servidor crea las cuentas iniciales descritas en
`LEEME.txt`. La cuenta de administrador de demostración es `admin` con la clave
inicial `Admin123!`; cámbiala antes de permitir que otras personas prueben el
sistema. El acceso compartido de empleados **no** tiene una clave inicial: el
administrador debe configurarla desde **Usuarios**.

Las cuentas iniciales y los datos de ejemplo solo se crean cuando la base no
tiene ningún usuario. Si `lael.db` ya contiene usuarios, el servidor no
restablece sus contraseñas ni recrea los datos iniciales.

## 4. Uso desde la misma red Wi-Fi

1. En la computadora que alojará la demo, ejecuta `INICIAR_LAEL_WIFI.bat`.
2. Conecta los otros dispositivos a la misma red Wi-Fi privada.
3. Averigua la dirección IPv4 actual de la computadora servidor con `ipconfig`.
4. En otro dispositivo abre `http://<IPv4-del-servidor>:8080`.
5. Mantén la ventana del servidor abierta. Al cerrarla, LAEL deja de responder.

La dirección puede cambiar al reconectar la computadora o el router. La
dirección anotada para esta instalación en `LEEME.txt` es información local y
puede dejar de ser válida. El control de red de Windows y el router también
deben permitir las conexiones dentro de la red privada. El aislamiento de
clientes o una red Wi-Fi de invitados puede impedir la comunicación entre
dispositivos.

El BAT establece `HOST=0.0.0.0`, que permite que el servidor escuche en todas
las interfaces de red. Esto **no** convierte la demo en un sitio público: no
configures reenvío de puertos ni la expongas a Internet. Para cambiar el puerto,
el servidor lee la variable de entorno `PORT`; si no se define, usa `8080`.

El servidor usa HTTP si no encuentra ambos archivos `cert.pem` y `key.pem`
junto a `server.py`. Si encuentra los dos, intenta habilitar TLS. La prueba
Wi-Fi descrita en los archivos de instalación usa HTTP.

## 5. Sitio público

La portada se sirve desde `index.html` y también puede consultarse sin iniciar
sesión. Presenta el estado del producto como prototipo y no habilita una
contratación.

### Navegación y secciones

- **Funciones:** presenta módulos disponibles en la demo y separa las funciones
  existentes de las planificadas o pendientes.
- **Planes:** muestra propuestas sin precio, pago ni suscripción habilitados.
- **Políticas:** presenta borradores de privacidad y términos, no documentos
  legales aprobados.
- **Preparación:** informa sobre tareas pendientes antes de considerar un
  producto comercial.
- **Probar demo / Explorar demo:** abre el formulario de acceso.
- **Tema:** alterna el tema visual claro u oscuro y guarda la preferencia en el
  navegador actual.

La portada contiene enlaces informativos a entidades externas. Estos enlaces
no significan que LAEL esté afiliado, certificado o autorizado por ellas.

### Catálogo de funciones presentado

La sección **Funciones** distingue las funciones que existen en la demo de las
que son ideas futuras:

| Función presentada | Estado indicado en la portada |
|---|---|
| Inventario | Disponible en demo. |
| Clientes y proveedores | Disponible en demo. |
| Ventas internas | Disponible en demo. |
| Usuarios y acceso | Disponible en demo. |
| Facturación electrónica | Por desarrollar. |
| Varias empresas y sucursales | Por diseñar. |
| BI y análisis | Planificado. |
| CRM y proyectos | Planificado. |
| Monedas e idiomas | Planificado. |
| Pagos y bancos | Integración pendiente. |
| Alertas y contabilidad | Integración pendiente. |
| Recursos humanos | Por diseñar. |

### Planes, políticas y preparación

- **Planes:** presenta Básico, Estándar y Premium como propuestas. No hay
  precios, pagos, suscripciones ni contratación. Los botones de cada plan
  explican que todavía no está disponible.
- **Políticas:** incluye resúmenes desplegables de privacidad, términos de uso
  de la demo y almacenamiento/red; añade una lista de normas para validación y
  enlaces oficiales. Responsable, contacto, retención y procedimientos siguen
  pendientes. El documento de referencia es
  `POLITICAS_LAEL_BORRADOR.txt`.
- **Preparación:** enumera tareas previas a vender: facturación electrónica,
  protección de datos, comercio/consumidor, marca y propiedad intelectual,
  infraestructura SaaS, escalabilidad/seguridad, MFA/auditoría, copias y
  continuidad, normas internacionales, soporte y actualizaciones. Son brechas,
  no funciones activadas ni certificaciones.

### Ventana de acceso

Permite seleccionar uno de dos modos:

- **Empleado · contraseña compartida:** solicita nombre declarado y contraseña
  común; puede incluir una etiqueta opcional para el equipo.
- **Administrador · cuenta privada:** solicita usuario y contraseña privados;
  también admite una etiqueta de equipo opcional.

Un nombre escrito por el empleado no verifica su identidad. La contraseña
compartida se configura en el módulo **Usuarios**. El botón para volver regresa
a la portada. El botón de políticas abre el borrador informativo.

## 6. Acceso y roles

### Administrador

Puede usar todos los módulos, gestionar cuentas y equipos, establecer la clave
compartida, administrar la lista de redes IP permitidas, consultar el historial
de accesos y abrir **Asistencia**. Las cuentas administrativas son privadas e
individuales.

### Empleado

Entra con la contraseña compartida y el nombre que escribe al iniciar sesión.
Puede consultar y crear/editar registros operativos y ventas de demostración.
No ve **Usuarios** ni **Asistencia** y no puede eliminar registros operativos.

La cuenta interna con rol `empleado` es necesaria para habilitar el tipo de
acceso compartido; el personal no introduce las credenciales de esa cuenta.
El nombre de usuario compartido aparece como cuenta base en algunos registros,
mientras que el nombre escrito queda como nombre declarado.

### Reglas de autenticación

- Las contraseñas de cuentas se guardan como derivaciones PBKDF2-HMAC-SHA256
  con sal aleatoria. La clave compartida también se guarda derivada con sal;
  LAEL no permite recuperarla desde la interfaz, pero el administrador puede
  cambiarla.
- Tras cinco intentos fallidos se aplica una espera de cinco minutos. El
  control se mantiene en memoria del servidor y se pierde al reiniciarlo.
- El token de sesión se conserva en memoria del servidor y en el almacenamiento
  de sesión del navegador. La sesión vence tras 30 minutos sin peticiones
  válidas; la aplicación envía un aviso de actividad cada 15 segundos.
- Reiniciar el servidor interrumpe las sesiones activas.
- Al cambiar la clave compartida se cierran las sesiones activas de empleados.
- No existe recuperación automatizada de contraseña.

## 7. Funciones de la aplicación

### 7.1 Panel

Muestra:

- Ventas de hoy y del mes, calculadas a partir de los registros internos.
- Número de productos y clientes.
- Gráfica con las ventas registradas en los últimos siete días.
- Productos con existencias iguales o inferiores al mínimo.
- Productos con mayores cantidades vendidas.
- Accesos rápidos a ventas, inventario y clientes.

Los importes y gráficos son resúmenes internos de la base. No son contabilidad,
pronóstico ni reporte fiscal.

### 7.2 Inventario

Cada producto tiene:

| Campo | Descripción |
|---|---|
| Código | Obligatorio y único. |
| Nombre | Obligatorio. |
| Precio | Valor numérico no negativo utilizado en ventas. |
| Costo | Valor numérico no negativo. |
| Stock | Cantidad entera no negativa disponible. |
| Stock mínimo | Umbral para mostrar alertas de bajo inventario. |

El formulario **Guardar** crea un producto o actualiza el seleccionado con
**Editar**. **Limpiar** vacía el formulario. **Buscar** filtra la tabla en el
navegador. **Exportar CSV** descarga el listado completo cargado, no solo las
filas visibles después del filtro. Los registros con stock igual o inferior al
mínimo se resaltan. Solo el administrador puede eliminar.

### 7.3 Clientes

Campos: nombre (obligatorio), NIT/DUI, teléfono, correo y dirección. Se puede
crear, editar, buscar, exportar a CSV y, con rol administrador, eliminar.
Los datos deben ser ficticios en esta demo.

### 7.4 Proveedores

Usa los mismos campos de contacto que Clientes: nombre (obligatorio), NIT,
teléfono, correo y dirección. Admite creación, edición, búsqueda, exportación
CSV y eliminación por el administrador.

### 7.5 Ventas de demostración

1. Selecciona un cliente registrado o **Consumidor final**.
2. Agrega uno o más productos con existencias.
3. Ajusta la cantidad; debe ser un entero positivo y no exceder el stock.
4. Revisa subtotal, impuesto de prueba del 13 % y total.
5. Selecciona **Emitir factura** para guardar la operación interna.
6. Abre **Ver comprobante demo** para consultarlo; desde allí puedes imprimir o
   guardar como PDF con las opciones de impresión del navegador.

El servidor vuelve a validar producto, cantidad y stock antes de registrar. La
venta guarda el nombre y precio del producto en el detalle y descuenta las
existencias. El número generado tiene formato `F-000001`. El listado muestra
hasta 200 registros recientes. No hay anulación fiscal ni reversión automática
de stock.

El comprobante es únicamente demostrativo: no es factura electrónica ni
documento tributario autorizado.

### 7.6 Usuarios

Solo para administradores. Incluye:

- **Contraseña única del personal:** configura o cambia una clave compartida
  con mínimo de ocho caracteres. Debe confirmarse dos veces en la pantalla.
- **Control de red del local:** muestra la IP que observa el servidor y permite
  autorizar hasta 50 direcciones o rangos CIDR (máximo 2,048 caracteres). La
  pantalla requiere incluir la IP actual del administrador al activar la lista.
  Una lista vacía desactiva la restricción, pero no el registro de IP.
- **Cuentas administrativas:** crea cuentas con nombre de usuario único,
  nombre, rol `admin` o `empleado` y clave de al menos ocho caracteres.
  No se permite eliminar la cuenta propia ni la última cuenta interna de
  empleado.
- **Límite de equipos:** muestra el total configurado y los perfiles registrados.
  El valor inicial del código es 40; se puede cambiar entre 1 y 10,000, sin
  quedar por debajo de los equipos activos.
- **Equipos autorizados:** muestra etiqueta, cuenta asociada, IP reciente,
  registro, última actividad y estado. Revocar desconecta el equipo y libera
  el cupo. No se puede revocar desde la sesión que se está usando; hazlo desde
  otra sesión administradora.
- **Historial de accesos:** muestra hasta 500 inicios correctos con fecha/hora
  local del servidor, nombre declarado, usuario base, IP observada y equipo.
  No incluye intentos fallidos.

El cupo cuenta perfiles de navegador, no computadoras físicas verificadas.
Borrar el almacenamiento del navegador o usar otro perfil puede registrarse
como otro equipo.

### 7.7 Asistencia

Solo para administradores. Presenta sesiones creadas por accesos de empleados,
un resumen de actividad, sesiones recientes y botones para descargar PDFs
completos o por nombre declarado.

- La lista se actualiza automáticamente cada 10 segundos.
- Un empleado se muestra **En línea** si la última petición se recibió dentro
  de los 45 segundos anteriores.
- La vista muestra inicio, última actividad, duración aproximada, equipo e IP.
- La tabla presenta hasta 5,000 sesiones recientes. El PDF incluye todos los
  registros que coincidan con el filtro.
- **Salir** cierra la sesión de forma explícita. Si se cierra el navegador o se
  pierde conexión, puede quedar inactiva hasta su expiración.
- El nombre es autodeclarado y la clave compartida no permite atribuir con
  certeza qué persona inició sesión. No es GPS ni seguimiento fuera de LAEL.

### 7.8 Ayuda, recursos, información y tema

- **Ayuda:** presenta instrucciones locales para el módulo abierto y atajos;
  no es un asistente de IA ni envía consultas.
- **Recursos:** ofrece enlaces externos de consulta.
- **Información:** muestra propietario indicado, versión de prueba y avisos.
- **Políticas:** abre los borradores informativos.
- **Tema:** guarda la apariencia en el almacenamiento local del navegador;
  no se sincroniza entre equipos.
- **Salir:** solicita cerrar la sesión y vuelve a la portada.

## 8. Usuarios, equipos, red y asistencia

### Perfil de navegador

En el primer inicio, el navegador crea un identificador aleatorio y lo guarda
en su almacenamiento local. El servidor calcula una huella derivada de ese
identificador y la registra como equipo. No es una huella de hardware. Una
persona puede borrar el almacenamiento local, usar otro navegador o perfil y
obtener un identificador nuevo.

La etiqueta del equipo puede escribirse en la pantalla de acceso (por ejemplo,
“Caja 1”). Si se deja vacía, se asigna “Navegador sin nombre”.

### Restricción por IP

El servidor toma la dirección IP de la conexión recibida directamente. No
confía en cabeceras reenviadas como `X-Forwarded-For`. Detrás de un proxy puede
registrarse la IP del proxy. VPN, NAT, redes móviles y redes compartidas pueden
alterar o hacer que varias personas compartan una IP.

Una lista configurada aplica a inicios de sesión y peticiones de la aplicación.
Usa direcciones individuales o CIDR, por ejemplo `192.168.1.0/24`; confirma el
rango correcto con quien administra el router. Una lista incorrecta puede
bloquear conexiones. La IP no demuestra identidad ni ubicación física.

### Duración y cierre de sesiones

Las sesiones expiran tras 30 minutos sin petición autenticada. La interfaz
manda una señal cada 15 segundos mientras permanece abierta y autenticada.
Asistencia usa 45 segundos como ventana para mostrar “En línea”. El valor de
duración es aproximado; usa **Salir** para cerrar el registro al terminar.

El historial no tiene una política de eliminación automática. Cambiar la clave
compartida, revocar un equipo o eliminar su cuenta puede cerrar sesiones.
Al iniciar el servidor, las sesiones que quedaron abiertas por la ejecución
anterior se cierran con motivo de reinicio.

## 9. Datos y reglas de negocio

La base `lael.db` contiene las tablas siguientes:

| Tabla | Contenido principal |
|---|---|
| `users` | Nombre de usuario, nombre mostrado, rol y derivación de contraseña con sal. |
| `app_settings` | Límite de equipos, rangos permitidos y parámetros de contraseña compartida. |
| `devices` | Identificador del perfil, cuenta asociada, etiqueta, fechas, estado de revocación e IP reciente. |
| `access_log` | Inicios correctos, nombre declarado, cuenta, equipo, hora e IP. |
| `employee_sessions` | Inicio, última actividad, cierre, duración y motivo de cierre de sesiones de empleados. |
| `products` | Código, nombre, precio, costo, existencias y stock mínimo. |
| `customers` | Nombre y datos de contacto del cliente. |
| `suppliers` | Nombre y datos de contacto del proveedor. |
| `invoices` | Número, cliente, fecha, subtotal, impuesto, total y cuenta que registró la venta. |
| `invoice_items` | Productos vendidos, cantidad, nombre y precio unitario guardados al emitir. |

Al crear una base vacía, se insertan cuentas y registros de muestra. La
inicialización agrega algunas columnas nuevas cuando faltan y marca como
finalizadas las sesiones que quedaron abiertas antes del reinicio. Los valores
de configuración existentes se conservan; por eso una base ya usada puede
tener ajustes diferentes a los predeterminados del código.

### Cálculos de ventas

- Subtotal: suma de precio × cantidad.
- Impuesto ilustrativo: 13 % del subtotal, redondeado a dos decimales.
- Total: subtotal más impuesto.
- La cantidad se descuenta de `products.stock`.

Estos cálculos no constituyen reglas fiscales ni contables aprobadas.

## 10. API local

La API se encuentra bajo `/api/`. Excepto el inicio de sesión, las rutas
requieren el encabezado `Authorization: Bearer <token>`. Las solicitudes que
envían datos usan JSON. La API está pensada para la interfaz del prototipo, no
es una API pública con versión y contrato de compatibilidad.

| Método y ruta | Permiso | Función |
|---|---|---|
| `POST /api/login` | Público | Inicia sesión administrativa o compartida; devuelve token. |
| `GET /api/me` | Sesión | Devuelve identidad y rol de la sesión actual. |
| `POST /api/logout` | Sesión | Cierra la sesión actual. |
| `POST /api/session-heartbeat` | Sesión | Renueva actividad y expiración de la sesión. |
| `GET /api/dashboard` | Sesión | Devuelve resumen, alertas, top de ventas y ventas de siete días. |
| `GET /api/products` | Sesión | Lista inventario. |
| `POST /api/products` | Sesión | Crea producto. |
| `PUT /api/products/{id}` | Sesión | Actualiza producto. |
| `DELETE /api/products/{id}` | Administrador | Elimina producto. |
| `GET /api/customers` | Sesión | Lista clientes. |
| `POST /api/customers` | Sesión | Crea cliente. |
| `PUT /api/customers/{id}` | Sesión | Actualiza cliente. |
| `DELETE /api/customers/{id}` | Administrador | Elimina cliente. |
| `GET /api/suppliers` | Sesión | Lista proveedores. |
| `POST /api/suppliers` | Sesión | Crea proveedor. |
| `PUT /api/suppliers/{id}` | Sesión | Actualiza proveedor. |
| `DELETE /api/suppliers/{id}` | Administrador | Elimina proveedor. |
| `GET /api/invoices` | Sesión | Lista hasta 200 ventas recientes. |
| `GET /api/invoices/{id}` | Sesión | Devuelve una venta con sus renglones. |
| `POST /api/invoices` | Sesión | Valida stock, registra la venta y descuenta existencias. |
| `GET /api/users` | Administrador | Lista cuentas. |
| `POST /api/users` | Administrador | Crea cuenta administrativa o de empleado. |
| `DELETE /api/users/{id}` | Administrador | Elimina cuenta, respetando las reglas de cuenta propia y último empleado. |
| `GET /api/devices` | Administrador | Devuelve límite, equipos, estado de clave compartida e IP actual. |
| `PUT /api/devices` | Administrador | Cambia el límite de equipos. |
| `DELETE /api/devices/{id}` | Administrador | Revoca un equipo que no sea la sesión actual. |
| `PUT /api/staff-password` | Administrador | Configura o cambia la clave común; cierra sesiones de empleados. |
| `GET /api/network-access` | Administrador | Muestra IP observada y rangos permitidos. |
| `PUT /api/network-access` | Administrador | Cambia lista de IP/rangos CIDR. |
| `GET /api/access-log` | Administrador | Devuelve hasta 500 accesos correctos recientes. |
| `GET /api/employee-sessions` | Administrador | Devuelve hasta 5,000 sesiones de empleados. |
| `GET /api/employee-session-report` | Administrador | Descarga todas las sesiones o las de `?employee=<nombre>` como PDF. |

La página pública fuera de `/api/` se devuelve como HTML para solicitudes GET.
El servidor acepta los métodos GET, POST, PUT y DELETE.

Respuestas comunes incluyen `400` para datos inválidos, `401` para credenciales
incorrectas o sesión vencida, `403` para permisos/red/equipo/cupo, `404` para
recurso inexistente, `405` para operación no permitida, `429` tras demasiados
intentos y `503` si el administrador aún no configuró la clave compartida.
La respuesta suele incluir una propiedad JSON `error` con explicación.

## 11. Arquitectura y almacenamiento

1. **Navegador:** `index.html` contiene HTML, CSS y JavaScript sin proceso de
   compilación. Envía solicitudes a rutas relativas `/api/`.
2. **Servidor:** `server.py` usa bibliotecas estándar de Python:
   `http.server`, `sqlite3`, `hashlib`, `secrets`, `ssl` y otras. No requiere
   instalar paquetes externos para el funcionamiento descrito.
3. **Persistencia:** `lael.db` se abre junto al servidor. Cada petición crea
   una conexión SQLite y usa transacciones para operaciones relevantes.
4. **Sesiones:** los tokens válidos y los bloqueos temporales por intentos se
   mantienen en memoria del proceso. Al reiniciar el servidor se pierden y se
   requiere iniciar sesión nuevamente.
5. **Exportaciones:** CSV se genera en el navegador; los PDF de asistencia se
   generan en el servidor. El comprobante de venta usa impresión del navegador.

El almacenamiento del navegador incluye el identificador del perfil, la
preferencia de tema, el token de sesión y el contador visual de duración. El
token y el contador están en almacenamiento de sesión; el identificador y el
tema quedan en almacenamiento local.

## 12. Seguridad, privacidad y límites

- Usa solo datos ficticios. Esta versión no está preparada para información
  personal, laboral, financiera, tributaria o de clientes.
- No publiques el servidor en Internet ni uses la clave de demostración.
- El modo Wi-Fi escucha en `0.0.0.0`; limita el uso a una red privada de prueba
  y configura el firewall con criterio. La aplicación por sí sola no ofrece
  aislamiento de red ni protección de producción.
- La clave compartida y el nombre autodeclarado no permiten saber con certeza
  qué persona usó el sistema.
- Los rangos IP restringen el origen de red, no comprueban ubicación física.
- Los perfiles de navegador no verifican hardware ni son licencias resistentes
  a manipulación.
- El historial de IP, accesos, sesiones y datos de prueba no tiene borrado
  automático. Limita acceso y define retención antes de cualquier uso que no
  sea una prueba local.
- No hay respaldos administrados, recuperación de datos, monitoreo,
  disponibilidad garantizada ni auditoría inmutable.
- La interfaz muestra borradores informativos. Completa y revisa profesionalmente
  privacidad, términos, obligaciones fiscales y estado de la marca antes de
  cualquier publicación o uso comercial.
- No se han certificado requisitos legales, fiscales, de privacidad ni de
  seguridad para producción.

## 13. Copias de la base de prueba

La base está en `lael.db` junto a `server.py`. Si necesitas conservar datos de
prueba, detén primero el servidor y copia el archivo a una ubicación privada
con acceso restringido. Comprueba que la copia exista y tenga un tamaño
razonable antes de hacer cambios. No compartas la copia: puede incluir
credenciales derivadas, IP, registros de actividad y datos ingresados.

Esta instrucción no sustituye un sistema de copias de seguridad. LAEL no
administra respaldos ni garantiza la recuperación. Antes de restaurar una copia
sobre la base activa, detén el servidor y conserva una copia de seguridad de la
base actual; una restauración reemplaza los datos presentes.

## 14. Solución de problemas

| Síntoma | Causa posible | Qué comprobar |
|---|---|---|
| Windows indica que no encuentra `python` | Python no está en PATH y no hay entorno virtual en la ubicación esperada. | Ejecuta el BAT incluido. Comprueba que exista `..\.venv\Scripts\python.exe` o instala Python y habilita su comando. |
| El navegador no conecta | El servidor está detenido, arrancó en otra carpeta o usa otro puerto. | Deja abierta la ventana del servidor y revisa `http://127.0.0.1:8080`. |
| La página carga, pero no permite iniciar sesión | Se abrió `index.html` como archivo o el servidor no atiende la API. | Usa la URL HTTP local, no el archivo directamente. Reinicia desde la carpeta que contiene `server.py`. |
| No abre desde otro equipo | IP cambió, firewall/router bloquea, red invitada o aislamiento Wi-Fi. | Confirma la misma red privada, la IPv4 actual, el puerto 8080 y las reglas del firewall/router. |
| Mensaje de red no autorizada | La lista CIDR configurada no contiene la IP actual. | Desde otro administrador autorizado, corrige el rango. No guardes rangos desconocidos. |
| No se puede entrar como empleado | No se configuró clave compartida, está equivocada o no existe cuenta interna de empleado. | Entra como administrador y configura la clave; verifica que haya una cuenta con rol empleado. |
| Se indica que el cupo está lleno | Se alcanzó el límite de perfiles registrados. | El administrador debe liberar un equipo no usado o aumentar el límite. |
| La sesión venció | Pasaron 30 minutos sin solicitudes válidas o se reinició el servidor. | Inicia sesión nuevamente. |
| La venta no se emite | Cantidad inválida, producto inexistente o stock insuficiente. | Revisa la cantidad entera y el stock disponible. |
| Una clave no funciona tras cambiarla | El cambio invalida sesiones del personal. | Inicia sesión con la nueva clave compartida. |

### Diagnóstico rápido del puerto en PowerShell

```powershell
Get-NetTCPConnection -LocalPort 8080 -State Listen
```

Si aparece una conexión escuchando, el puerto está ocupado. No detengas un
proceso desconocido; identifica primero qué aplicación lo usa.

## 15. Documentos relacionados

- [LEEME.txt](LEEME.txt): instrucciones breves de inicio y configuración local.
- [MANUAL_LAEL.txt](MANUAL_LAEL.txt): guía operativa de uso.
- [POLITICAS_LAEL_BORRADOR.txt](POLITICAS_LAEL_BORRADOR.txt): borradores de
  privacidad y términos pendientes de completar y revisar.
- [HOJA_DE_RUTA_LAEL.txt](HOJA_DE_RUTA_LAEL.txt): brechas y propuesta para una
  arquitectura futura.

Mantén estos documentos sincronizados con el código cuando cambien pantallas,
permisos, endpoints, reglas de ventas o forma de inicio.
