# Prompt de Arquitectura y Desarrollo — Nexo (Django + Vue + PostgreSQL)

> Copia este documento completo como prompt inicial para Claude Code, otro asistente de IA, o como especificación técnica para tu equipo. Está escrito para que un asistente pueda generar el scaffolding completo del proyecto sin ambigüedad.

---

## 1. Contexto del sistema

Estoy reconstruyendo un sistema de gestión de campañas y leads, hoy llamado **DataKloud** y que en su nueva versión se llamará **Nexo**. Vive hoy como una app monolítica en Google Apps Script (frontend HTML+jQuery+Vue mezclado, backend en clases `.gs`, datos en Google Sheets + BigQuery vía stored procedures). El sistema permite:

- Cargar bases de datos de contactos ("leads") asociadas a campañas de productos.
- Asignar esos leads a usuarios ejecutivos, organizados en una jerarquía de roles.
- Que los ejecutivos "tipifiquen" (clasifiquen) cada contacto con categoría/subcategoría y dejen un comentario de gestión.
- Generar oportunidades comerciales derivadas de la gestión de un lead.
- Ver dashboards de resultados por campaña, filtrados según el alcance del rol.

Quiero migrarlo a una arquitectura moderna, segura y mantenible: **Django (backend/API) + Vue 3 (frontend SPA) + PostgreSQL (base de datos relacional)**, corriendo en Docker Compose.

## 2. Modelo de roles y jerarquía (a preservar y formalizar)

| Rol | Alcance de datos | Notas |
|---|---|---|
| `ADMIN` | Global | Acceso total, gestión de usuarios |
| `GERENTE` | Global | Solo lectura/gestión amplia, sin administración de usuarios |
| `SUPERVISOR` | Por distrito (`dist`) | Ve/asigna dentro de su distrito |
| `JEFE` / `SUBJEFE` | Por agencia (`codAge`) | Ve/asigna dentro de su agencia |
| `EJECUTIVO` | Solo sus propios leads asignados | Tipifica, no asigna |

Este scoping territorial (`dist`, `codAge`) debe modelarse como **relaciones reales** (tablas `Territorio`/`Agencia`), no como campos sueltos, y los permisos deben aplicarse a nivel de queryset en cada endpoint — nunca confiar en que el frontend oculte columnas.

**Cambio importante respecto al sistema actual — Jefe multi-agencia:**
Hoy un `JEFE`/`SUBJEFE` tiene una sola `codAge` (relación 1 a 1 con su agencia). El nuevo sistema debe soportar que **un mismo jefe supervise varias agencias simultáneamente**. Esto es un cambio de cardinalidad (de FK a many-to-many) que toca todo lo que hoy asume "un jefe = una agencia":

- La tabla de asignación usuario↔agencia debe ser una relación **M2M con tabla intermedia explícita** (`UserAgencia`: usuario FK, agencia FK, fecha_asignación, activo), no un M2M directo de Django sin metadata — así puedes auditar cuándo se le agregó/quitó una agencia a un jefe.
- Todo permiso o queryset que hoy filtraría por `usuario.codAge == X` debe cambiar a `agencia IN usuario.agencias.all()`. Esto afecta: listado de ejecutivos visibles, leads visibles, dashboards filtrados, y reglas de asignación (un jefe solo puede asignar leads dentro de alguna de sus agencias).
- Un `EJECUTIVO`, en cambio, sigue perteneciendo a **una sola agencia** (no hereda la multiplicidad) — solo los roles de supervisión (`JEFE`, `SUBJEFE`, y opcionalmente `SUPERVISOR` con varios distritos) necesitan esta relación M2M. Confirma con el negocio si `SUPERVISOR` también debe poder tener varios distritos; si es así, aplica el mismo patrón a `Territorio`.
- Antes de implementar, pide al asistente que te muestre **todos los lugares del backend donde se filtraría por agencia/distrito** (endpoints de leads, dashboards, asignación, reportes) como checklist, para verificar que ninguno quedó con lógica de "una sola agencia" sin actualizar. Este es el punto donde más fácil se cuela un bug de permisos (un jefe viendo o asignando fuera de su alcance real).

## 3. Stack técnico obligatorio

**Backend**
- Django 5.x + Django REST Framework
- PostgreSQL 16 (esquema relacional normalizado, con migraciones versionadas)
- Autenticación: JWT (`djangorestframework-simplejwt`) o sesiones + `django-allauth` para SSO con Google Workspace (OAuth2/OIDC), reemplazando la confianza ciega en `Session.getActiveUser()`
- Django Channels + Redis para WebSockets (tiempo real / notificaciones)
- Celery + Redis para tareas asíncronas (carga masiva de leads, envío de notificaciones, generación de reportes)
- `django-guardian` o un sistema de permisos custom para RBAC por objeto/territorio, no solo por rol global

**Frontend**
- Vue 3 (Composition API) + Vite
- Pinia para estado global (usuario autenticado, permisos, notificaciones)
- Vue Router con guards por rol/permiso
- Axios con interceptores (refresh token, manejo global de errores 401/403)
- Componentes de tabla reutilizables (ej. TanStack Table o AG Grid) parametrizados por configuración de columnas según permisos — **una sola vista de campaña, no una por rol**
- WebSocket client (nativo o `socket.io`-equivalente vía Channels) para notificaciones push

**Infraestructura**
- Docker Compose: `backend`, `frontend`, `postgres`, `redis`, `celery-worker`, `celery-beat` (si aplica), `nginx` (proxy en producción)
- Variables de entorno vía `.env` (nunca credenciales hardcodeadas)
- Migraciones y seeds versionados

## 4. Modelo de datos relacional (mínimo viable)

Diseña las siguientes entidades en Postgres, con claves foráneas reales (no strings sueltos como en el sistema actual):

- `User` (extendiendo `AbstractUser`): email, nombre, rol (FK a `Role`), agencia principal (FK, aplica a `EJECUTIVO`), estado activo/inactivo
- `UserAgencia`: tabla intermedia para la relación M2M jefe↔agencias (usuario FK, agencia FK, fecha_asignación, activo) — ver sección de diseño "Jefe multi-agencia" arriba
- `Role`: nombre, nivel jerárquico, permisos asociados
- `Territorio` (distrito) y `Agencia`: jerarquía organizacional — **ambas gestionables por CRUD dentro del sistema** (alta/baja/edición desde la UI de `ADMIN`), no precargadas a mano en la base de datos
- `Campaign`: nombre, fecha inicio/fin, estado (activa/cerrada), producto asociado
- `CampaignType` ("contenedor"/plantilla de campaña): nombre (ej. "Créditos Personales", "Tarjetas de Crédito", "Cobranza Mora Temprana"), `categoria` general (`VENTAS` / `COBROS`, extensible a futuro) — cada `Campaign` referencia un `CampaignType`
- `CampaignFieldDefinition`: campaign_type FK, `field_key` (nombre técnico), `label` (etiqueta visible), `data_type` (texto/número/fecha/booleano/select), `required`, `options` (JSON, solo para tipo select), `orden` (para renderizar el formulario/tabla en el frontend en el orden correcto), `mostrar_en_tabla` (booleano, columna visible en el listado), `mostrar_en_detalle` (booleano, visible en la vista de detalle del registro), `seccion` (texto opcional, para agrupar campos en el detalle, ej. "Datos del cliente" / "Datos de la oferta") — reemplaza las ~37 columnas fijas actuales por un esquema configurable desde la UI de administración, y además controla cómo se renderiza (no solo cómo se captura)
- `Lead` (registro/contacto): datos **core** relacionales (cliente, teléfono, correo, dirección, campaña FK, estado, usuario asignado FK, fecha de asignación, `agencia` FK **esencial/requerido** — siempre se carga desde el archivo origen o del `LoteCarga`, y es lo que determina qué supervisor/jefe lo ve inicialmente; `distrito` FK opcional) — `Lead.agencia` es **mutable**: si un supervisor reasigna el registro a un ejecutivo de otra agencia de su distrito, el sistema debe actualizar `Lead.agencia` para reflejar la nueva agencia dueña, o el jefe origen seguiría viéndolo y el jefe destino nunca lo vería. El campo `atributos JSONB` contiene solo los campos definidos por el `CampaignType` de su campaña (validados server-side contra `CampaignFieldDefinition` al momento de cargar el archivo o crear el lead manualmente)
- `Category` / `SubCategory`: catálogo de tipificación, **gestionable por CRUD dentro del sistema** (hoy vive en hojas de Sheets tipo `Motivos-NA`, `Motivos-NI`, `Categorias Oportunidades`, `Productos` — todo eso pasa a ser catálogo administrable en Postgres vía UI, no hardcodeado ni en spreadsheet)
- `ManagementLog` (gestión/tipificación): lead FK, usuario FK, categoría FK, subcategoría FK, comentario, timestamp — inmutable (append-only)
- `Opportunity`: derivada de un lead, con su propio ciclo de estado y log de seguimiento
- `Assignment`: historial de asignaciones (lead FK, usuario_origen, usuario_destino, `agencia_origen` FK, `agencia_destino` FK — nulo si no hubo cambio de agencia, timestamp, asignado_por FK) — **esto reemplaza la asignación "silenciosa" actual**. Cada reasignación que cambia de agencia debe actualizar `Lead.agencia` al guardar el `Assignment` (transacción atómica: no debe quedar un `Assignment` registrado sin que `Lead.agencia` refleje el cambio). Regla de negocio a validar en el endpoint: un `SUPERVISOR` solo puede reasignar leads entre agencias **dentro de su propio distrito** — la agencia destino debe pertenecer al mismo `Territorio` que el supervisor gestiona, si no, rechazar la operación
- `AuditLog`: modelo genérico de trazabilidad (usuario, acción, modelo afectado, id afectado, datos antes/después en JSON, timestamp, IP) — aplicado vía middleware o signals de Django a **todas** las escrituras relevantes
- `LoteCarga` (lote de carga): campaign FK, usuario que cargó FK, fecha de carga, nombre del archivo original, cantidad de registros, producto (si varía dentro de la misma campaña, ej. hoy "Tarjetas", la próxima semana "Créditos" bajo el mismo contenedor), `agencia_restriccion` FK opcional, `distrito_restriccion` FK opcional (si se define, todos los leads del lote heredan esa agencia/distrito, restringiendo su visibilidad al scoping territorial normal de supervisor/jefe — reutiliza el mismo mecanismo de permisos ya definido, sin lógica nueva) — cada `Lead` referencia su `LoteCarga` de origen (FK), para saber exactamente de qué archivo vino, cuándo y quién lo subió
- `Division`/`Area`: catálogo de unidades de negocio (ej. "Red de Agencias", "Banca Empresas") — gestionable por CRUD igual que `Agencia`/`Territorio`. `User` referencia su `Division` (FK), `Campaign` referencia la `Division` a la que pertenece (FK). El filtro de visibilidad de campañas/leads combina **división del usuario == división de la campaña** AND **alcance territorial del rol** (distrito/agencia, solo aplica a `SUPERVISOR`/`JEFE`/`SUBJEFE`) — esto permite crecer a nuevas divisiones (ej. "Cobranza") sin tocar código, solo creando el registro y sus campañas
- `Notification`: usuario destino, tipo, payload, leído/no leído, timestamp

**Nota de diseño — esquema dinámico de campañas, sin crear tablas dinámicamente:**
Los campos de oferta varían poco entre productos (datos personales/contacto + datos de oferta, hoy resueltos "de sobra" con columnas casi siempre vacías). La solución es el patrón `CampaignType` + `CampaignFieldDefinition` + `Lead.atributos JSONB` descrito arriba — **nunca** generar tablas de Postgres por campaña vía DDL en tiempo de ejecución (rompe el modelo de migraciones de Django, imposibilita reportes cruzados entre campañas, y satura el catálogo de la base de datos con el tiempo). Detalles de implementación:
- Indexa `Lead.atributos` con un índice GIN (`django.contrib.postgres.indexes.GinIndex`) para poder filtrar/buscar razonablemente rápido sobre campos variables.
- Cualquier campo que sepas que **siempre** se necesita para reporting/dashboards (monto de la oferta, fecha de última gestión, categoría de tipificación) debe quedar como columna relacional real en `Lead`, no dentro del JSONB — el JSONB es solo para lo verdaderamente variable por producto.
- El mismo `CampaignFieldDefinition` que valida la carga de archivos en el backend se expone vía API para que Vue **genere dinámicamente** el formulario de tipificación y las columnas de la tabla de leads — esto también resuelve la duplicación de vistas por rol (`v_campaing_admin` / `v_campaing_jefes` / `v_campaing_ejecutivos`) del sistema actual: pasa a ser un solo componente parametrizado por la definición de campos + los permisos del rol.
- Este mismo mecanismo debe diseñarse pensando en `categoria = COBROS` desde el inicio (no solo `VENTAS`), ya que el usuario planea usarlo también para campañas de cobranza con campos propios (mora, monto adeudado, número de cuenta) sin tocar el modelo de datos.
- **Renderizado dinámico de tabla y detalle, sin constructor visual de pantallas**: el frontend construye un único componente de tabla y uno de detalle que leen `mostrar_en_tabla`, `mostrar_en_detalle`, `seccion` y `orden` desde `CampaignFieldDefinition` vía API, con un formateador por `data_type` (fecha, número, select). **No** implementar un editor visual tipo drag-and-drop para diseñar pantallas — es sobre-ingeniería para el alcance de este proyecto; la configuración por campos (orden, sección, visibilidad) ya da suficiente flexibilidad sin ese costo de desarrollo.

## 5. Funcionalidades clave a implementar

0. **Administración de usuarios y catálogos, todo dentro de la plataforma**
   - CRUD completo de usuarios (alta, edición, desactivación — no borrado físico) con asignación de rol, agencia(s) y distrito desde la propia UI, reemplazando el mantenimiento manual en la hoja "Usuarios".
   - CRUD de `Agencia` y `Territorio`/distrito.
   - CRUD de `Category`/`SubCategory` de tipificación, motivos de "No Aplica", motivos de "No Interesado", categorías de oportunidades y catálogo de productos — todo lo que hoy vive disperso en pestañas de Sheets (`Categorias`, `SubCategorias`, `Motivos-NA`, `Motivos-NI`, `Categorias Oportunidades`, `Productos`) se convierte en catálogos administrables desde el sistema.
   - Solo `ADMIN` (y opcionalmente `GERENTE` en modo lectura) accede a esta administración; queda registrada en `AuditLog`.

1. **Autenticación y autorización — con switch por variable de entorno entre Google OAuth y login local**
   - **Costo**: la autenticación vía "Sign in with Google" (OAuth2/OIDC) es gratuita, sin importar el volumen de logins — solo requiere un proyecto de Google Cloud (el personal del usuario es suficiente) y un OAuth Client ID registrado en la consola. **No** requiere pagar ni administrar Google Workspace de la organización; esa suscripción la paga el empleador para sus correos/Drive, no tiene relación con poder autenticar contra esas cuentas vía OAuth.
   - **No depender de la API de Admin Directory** (`AdminDirectory.Users.get()` del sistema actual) — esa API sí requiere ser super-admin del Workspace de la organización, algo que no está disponible para un desarrollo personal/portafolio. En su lugar, usar los claims estándar del token OIDC (`email`, `name`, `picture`) que Google ya entrega al autenticar — no requiere permisos administrativos de ningún tipo.
   - **Diseño con switch de proveedor**: implementar dos backends de autenticación intercambiables, controlados por variables de entorno (ej. `AUTH_GOOGLE_ENABLED=true/false` y `AUTH_LOCAL_ENABLED=true/false`, pudiendo ambos estar activos a la vez):
     - `POST /api/auth/login/google/`: recibe el ID token que el frontend obtiene vía Google Identity Services (librería JS de Google en Vue), lo verifica server-side contra las llaves públicas de Google, opcionalmente valida el claim `hd` contra `GOOGLE_WORKSPACE_DOMAIN` (variable de entorno) si se quiere restringir a un dominio corporativo, y crea/actualiza el `User` local.
     - `POST /api/auth/login/local/`: login tradicional usuario/contraseña contra el sistema de auth de Django, para cuando Google OAuth esté deshabilitado o no aplique (ej. mientras se prueba el proyecto de forma independiente).
     - Ambos endpoints devuelven el mismo formato de JWT interno — el resto del sistema (permisos, endpoints protegidos) es agnóstico a qué proveedor autenticó al usuario.
   - `User` guarda un campo `auth_provider` (`google` / `local`) para trazabilidad de cómo entró cada quien.
   - El frontend consulta un endpoint público de configuración (o variable de entorno de build) para decidir qué botón de login mostrar, en vez de tenerlo hardcodeado.
   - Permisos granulares por endpoint (DRF permission classes), no solo por rol sino por scope territorial calculado en cada request.
   - Opción de habilitar MFA a futuro (dejar el modelo de usuario preparado).

2. **Carga de leads dentro del sistema**
   - Reemplazar la carga manual a BigQuery por un endpoint de carga de archivos (CSV/Excel) con validación de esquema, deduplicación y procesamiento asíncrono vía Celery (con feedback de progreso).
   - Registrar en `AuditLog` quién cargó qué base y cuándo.

3. **Asignación de leads con actualización en tiempo real (no solo notificación)**
   - Al asignar (individual o masiva) un lead a un usuario, crear registro en `Assignment` (con `agencia_origen`/`agencia_destino` si aplica), generar `Notification`, y **emitir evento por WebSocket** con dos efectos distintos, no uno solo:
     - Un aviso tipo notificación (badge/toast), para que el usuario se entere aunque no esté viendo esa pantalla.
     - Un evento de datos que **actualiza directamente el store de Vue (Pinia)** — si el ejecutivo tiene abierta su lista de leads asignados, el registro nuevo debe aparecer solo, sin recargar la página. Lo mismo al revés: si le quitan un lead, debe desaparecer de su lista en vivo.
   - **Control de propiedad al momento de escribir (no solo al cargar la pantalla)**: si un jefe reasigna un lead que el ejecutivo tenía abierto y este intenta guardar una gestión sobre él, el backend debe **rechazar la escritura** validando en ese instante que `request.user` sigue siendo el `usuario_asignado` actual del lead (o tiene permiso de scope vigente) — no basta con que el frontend oculte el botón. Si la validación falla, responder con un error específico (ej. HTTP 409) que incluya quién es el nuevo responsable, para que el frontend muestre una alerta clara ("Este registro ya no te pertenece, fue reasignado a X") y refresque el estado local.
   - Reglas de asignación deben respetar el scope del rol que asigna (un `JEFE` no puede asignar fuera de su agencia; un `SUPERVISOR` no puede reasignar fuera de su distrito, ver regla en `Assignment`).

4. **Tipificación / gestión de contactos**
   - Formulario único reutilizable (no duplicado por rol) que filtra categorías/subcategorías desde catálogo en BD.
   - **No es exclusivo de `EJECUTIVO`**: `SUPERVISOR` y `JEFE`/`SUBJEFE` también deben poder gestionar directamente cualquier lead dentro de su scope (útil cuando necesitan intervenir un caso), quedando registrados en el mismo `ManagementLog` igual que si lo hiciera el ejecutivo.
   - Cada tipificación crea un `ManagementLog` inmutable y actualiza el estado del `Lead`.
   - **Vista de evolución del lead**: en el detalle de cada registro debe verse la línea de tiempo completa de `ManagementLog` (quién gestionó, cuándo, con qué categoría/comentario), visible para cualquier rol que tenga acceso a ese lead según su scope — no solo quien lo gestionó.

5. **Oportunidades**
   - CRUD de oportunidades ligadas a un lead o creadas de forma independiente, con su propio historial de seguimiento y prioridad.
   - **Creación manual desde la vista**: cualquier ejecutivo/jefe debe poder registrar una oportunidad nueva directamente desde la interfaz (no solo como derivado automático de tipificar un lead), capturando cliente, producto, monto, tasa, plazo, categoría y fecha de próximo contacto — igual que el flujo `crearOportunidad` del sistema actual, pero validado por serializer en vez de concatenado a mano.

6. **Trazabilidad / auditoría**
   - Todo cambio relevante (asignaciones, tipificaciones, altas/bajas de usuarios, cambios de catálogo) debe quedar en `AuditLog` consultable por `ADMIN`/`GERENTE` con filtros por usuario, fecha, entidad.
   - **Pantalla de "cadena de custodia" del lead**: no basta con guardar el dato, tiene que ser una vista accesible dentro del detalle de cada lead (y a nivel de campaña/lote de carga, filtrable) que muestre el historial completo de `Assignment` — quién lo asignó, a quién, cuándo, y si cruzó de agencia. Debe ser visible no solo para `ADMIN`, sino para `SUPERVISOR`/`JEFE` dentro de su propio scope, ya que son quienes normalmente necesitan reconstruir "se nos perdió el track de quién asignó qué".

7. **Notificaciones**
   - In-app vía WebSocket, con dos tipos de payload: notificación visual (badge/toast) y evento de actualización de datos (agregar/quitar de la lista en vivo) — ver punto 3.
   - Diseñar el modelo para poder añadir email (Celery) como canal adicional después, sin rehacer el core.

8. **Dashboards**
   - Mantener el concepto de reportes filtrados por rol/campaña, pero evaluar si se sirven embebidos (Looker Studio, como hoy) o se migran a endpoints agregados propios + gráficas en Vue. Decide con el usuario cuál prefiere antes de implementar.

9. **Diseño visual y experiencia de usuario**
   - Layout con **sidebar de navegación fijo y colapsable** (reemplaza el `Sidebar.html` actual, pero con un sistema de diseño moderno, no Bootstrap 4 + jQuery). La navegación del sidebar refleja la jerarquía de módulos (Campañas, Oportunidades, Administración) y se filtra dinámicamente según los permisos del rol — un `EJECUTIVO` no ve la opción de Administración, por ejemplo.
   - Diseño **minimalista y consistente**: Tailwind CSS + una librería de componentes accesibles (ej. shadcn-vue o Headless UI) en vez de reconstruir botones/modales/tablas desde cero, para lograr un look moderno sin inflar el tiempo de desarrollo.
   - El mismo sistema de diseño debe aplicarse a los componentes **dinámicos** (tabla y detalle generados desde `CampaignFieldDefinition`) — que no se vean como una tabla genérica improvisada, sino parte coherente del resto de la interfaz.
   - Modo claro/oscuro como plus, no como requisito bloqueante del MVP.

## 6. Requisitos no funcionales

- **Seguridad**: todas las queries vía ORM de Django (elimina el riesgo de inyección SQL del sistema actual); validación de entrada con serializers DRF; rate limiting en endpoints sensibles; CORS configurado explícitamente; secretos solo en variables de entorno.
- **Testing**: pytest + pytest-django para backend (mínimo cobertura de modelos de permisos y lógica de asignación, que es la parte más delicada del diseño); Playwright para pruebas end-to-end de los flujos completos (login, carga de base, asignación, actualización en tiempo real, bloqueo de escritura al reasignar) — se usa Playwright en vez de pruebas unitarias de componentes Vue porque ya es una herramienta que domina el desarrollador y cubre mejor justo los flujos críticos de tiempo real del sistema.
- **Documentación**: OpenAPI/Swagger autogenerado (drf-spectacular) para la API.
- **Migraciones de datos**: script de migración desde las Sheets/BigQuery actuales hacia el nuevo esquema Postgres (a diseñar como fase separada, no bloqueante para el MVP).

## 7. Cómo quiero que trabajes

1. Empieza proponiendo el **modelo de datos completo** (diagrama ER o lista de modelos Django con campos y relaciones) para que lo revise antes de generar código.
2. Luego propone la **estructura de carpetas** del backend (apps de Django) y del frontend (estructura de Vue/Pinia/Router).
3. Implementa por fases: (1) autenticación y modelo de usuarios/roles, (2) campañas y leads con asignación + auditoría, (3) tipificación y oportunidades, (4) notificaciones en tiempo real, (5) dashboards.
4. En cada fase, explica las decisiones que tomaste y por qué — no soy solo el receptor del código, este proyecto es también para aprender a fondo Django, Vue y los patrones de diseño usados (JSONB dinámico, scoping territorial, WebSockets). Señala en particular las decisiones de seguridad o de permisos, dado que este sistema maneja datos personales y financieros de clientes, pero no te limites a eso.
5. Al cerrar cada fase, dame un resumen breve de qué se construyó y pregúntame si tengo dudas antes de avanzar a la siguiente — prefiero ir entendiendo sobre la marcha en vez de recibir todo el proyecto de un jalón al final.
6. Si algo del sistema original es ambiguo (por ejemplo, reglas exactas de cuándo una oportunidad se cierra), pregúntame en vez de asumir.

---

### Contexto de referencia del sistema actual (para quien lea este prompt)

El sistema legado tiene: autenticación implícita vía Google Workspace, roles leídos de una hoja de cálculo, datos operativos en BigQuery vía stored procedures llamados con SQL concatenado desde Apps Script, vistas HTML duplicadas por rol (jQuery + DataTables + SweetAlert2, con una vista ya migrada a Vue 3), y dashboards de Looker Studio embebidos con parámetros por rol. No existe trazabilidad general de acciones ni notificaciones en tiempo real — ambas son requisitos nuevos explícitos para la v2.