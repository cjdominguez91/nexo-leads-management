# Demo de Nexo en una laptop

Guía para levantar Nexo desde cero en otra computadora y mostrarlo con datos ficticios.

> **Haz los pasos 1 a 4 el día anterior, con internet.** La primera vez Docker descarga imágenes e instala dependencias (10–20 min). El día de la demo solo hace falta el paso 5.

## 1. Instalar Docker Desktop

- Descarga Docker Desktop desde docker.com e instálalo. En Windows pide activar **WSL 2**: acepta y reinicia.
- Requisitos: permisos de administrador, la virtualización activada en la BIOS (casi siempre viene activa) y unos 6 GB libres en disco.
- Abre Docker Desktop y espera a que diga *Engine running*.
- Si es una laptop corporativa, revisa antes que te deje instalarlo. Algunas bloquean WSL o la virtualización.

## 2. Copiar el proyecto

**Opción A, con Git** (si el repo ya está en GitHub como privado):

```bash
git clone https://github.com/cjdominguez91/nexo-leads-management.git
cd nexo-leads-management
```

**Opción B, con USB:** copia la carpeta `Nexo` **sin** estas subcarpetas, que se regeneran solas y pesan mucho:

- `frontend/node_modules`
- `frontend/dist`
- `backend/.venv`
- `backend/media` (archivos subidos en tu máquina)

## 3. Crear el archivo `.env`

Dentro de la carpeta del proyecto:

```powershell
copy .env.example .env
```

Para la demo no hay que tocar nada más: login local activado y Google desactivado.

> No copies el `.env` de tu máquina de desarrollo. Así la laptop de demo no lleva credenciales reales.

## 4. Levantar y cargar los datos demo

```powershell
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

El primero construye y arranca todo. El segundo se asegura de que la base tenga sus tablas (si ya las tiene, no hace nada). El tercero carga datos 100 % inventados. Solo funciona en una base vacía, para no mezclarse nunca con datos reales.

Abre **http://localhost:5173** y prueba entrar con un usuario.

## 5. El día de la demo

1. Abre Docker Desktop y espera a que diga *Engine running*.
2. En la carpeta del proyecto ejecuta `docker compose up -d`.
3. Abre **http://localhost:5173**.

Al terminar, apaga todo con `docker compose down`. Los datos se conservan.

## Usuarios demo

Todos usan la contraseña **`Demo2026!`**.

| Usuario | Rol | Qué mostrar |
|---|---|---|
| `admin@demo.nexo` | Super admin | Ve las dos divisiones y administra divisiones |
| `admin.persona@demo.nexo` | Admin de división (Banca Persona) | Administra solo su división: usuarios, agencias, catálogos |
| `gerente@demo.nexo` | Gerente (Banca Persona) | Tableros de toda su división |
| `supervisor@demo.nexo` | Supervisor (Distrito 1) | Reasigna entre agencias de su distrito |
| `jefe@demo.nexo` | Jefe multi-agencia (Agencia Centro + Diagonal Universitaria) | Ve y asigna en sus dos agencias; hay leads sin asignar |
| `subjefe@demo.nexo` | Subjefe (Multiplaza) | Solo su agencia |
| `ejecutivo1@demo.nexo` | Ejecutivo (Agencia Centro) | Sus leads, tipificación, oportunidades |
| `admin.empresas@demo.nexo` | Admin de división (Banca Empresas) | Otra división: no ve nada de Banca Persona |
| `empresas1@demo.nexo` | Ejecutivo (Merliot, Banca Empresas) | Campaña Crédito PYME con campos de empresa (razón social, NIT, ventas anuales) |

Estructura que crea el script:

```
Banca Persona
├─ Distrito 1
│  ├─ 1 Agencia Centro
│  └─ 2 Diagonal Universitaria
└─ Distrito 2
   └─ 3 Multiplaza
Banca Empresas
└─ Distrito 3
   └─ 4 Merliot
```

## Guion sugerido

1. **Aislamiento por división:** entra como `admin.persona` y luego como `admin.empresas`. Cada uno ve solo lo suyo, aunque es el mismo sistema.
2. **Esquema dinámico:** en *Tipos de campaña* muestra que "Créditos Personales" y "Crédito PYME" tienen campos distintos sin cambiar código.
3. **Tiempo real:** abre dos ventanas, una como `jefe` y otra (en incógnito) como `ejecutivo1`. El jefe asigna un lead nuevo y aparece solo en la lista del ejecutivo, con su notificación.
4. **Bloqueo al reasignar:** con el lead abierto en la ventana del ejecutivo, el jefe se lo reasigna a otro. Cuando el ejecutivo intenta guardar una gestión, el sistema la rechaza y le avisa quién es el nuevo responsable.
5. **Trazabilidad:** en el detalle de un lead, revisa la línea de tiempo de gestiones y la cadena de custodia. Hay un lead que el supervisor movió de Agencia Centro a Diagonal Universitaria.
6. **Tableros:** como `gerente`, revisa efectividad por campaña y la tendencia.

## Si algo falla

| Síntoma | Solución |
|---|---|
| `port is already allocated` (5432, 6379, 8000 o 5173) | Otro programa usa ese puerto (por ejemplo, un PostgreSQL instalado). Ciérralo o detén ese servicio de Windows. |
| La página no carga justo después de `up` | El frontend tarda unos segundos en compilar. Revisa con `docker compose logs -f frontend`. |
| `seed_demo` dice que la base ya tiene leads | Ya se cargó antes. Para empezar de cero: `docker compose down -v` (**borra la base**), luego `up -d` y `seed_demo`. |
| Error raro en el backend | Revisa con `docker compose logs -f backend`. |
