# Nexo

Sistema de gestión de campañas y leads: Django + Vue + PostgreSQL, corriendo en Docker Compose.

## Instalar en una computadora nueva (Windows)

La primera instalación tarda entre 20 y 30 minutos y **necesita internet**, porque Docker descarga imágenes e instala dependencias. Hazla con tiempo, no el mismo día que la vas a usar.

### 1. Revisa que la computadora cumpla los requisitos

- Windows 10 (versión 22H2) o Windows 11.
- **Virtualización activada.** Ábrelo en *Administrador de tareas → Rendimiento → CPU* y busca *Virtualización: Habilitado*. Si dice *Deshabilitado*, hay que activarla en la BIOS.
- Permisos de administrador para instalar programas.
- Unos 6 GB libres en disco.

### 2. Instala Git

Descárgalo de <https://git-scm.com/download/win> e instálalo con las opciones por defecto.

### 3. Instala Docker Desktop

1. Descárgalo de <https://www.docker.com/products/docker-desktop/> e instálalo.
2. Durante la instalación, deja marcada la opción **Use WSL 2 instead of Hyper-V**. WSL 2 es el subsistema Linux que Docker necesita, y el instalador lo prepara solo. No hace falta instalar Ubuntu ni otra distribución.
3. Reinicia la computadora si te lo pide.
4. Abre Docker Desktop y espera a que abajo a la izquierda diga **Engine running**.

Si Docker avisa que WSL no está instalado o está desactualizado, abre PowerShell **como administrador** y ejecuta uno de estos comandos. Después reinicia.

```powershell
wsl --install --no-distribution   # si WSL no está instalado
wsl --update                      # si ya estaba pero es viejo
```

### 4. Descarga el proyecto

Abre PowerShell (no hace falta que sea como administrador):

```powershell
cd $HOME\Desktop
git clone https://github.com/cjdominguez91/nexo-leads-management.git Nexo
cd Nexo
```

### 5. Crea el archivo de configuración

```powershell
copy .env.example .env
```

Para usarlo en una sola computadora no hay que cambiar nada. El login es con usuario y contraseña, y el login con Google está desactivado.

> El `.env` nunca se sube a GitHub. No copies el de otra computadora: créalo siempre desde `.env.example`.

### 6. Levanta el sistema

```powershell
docker compose up -d --build
```

La primera vez tarda (10–20 min). Cuando termine, verifica que todo esté corriendo:

```powershell
docker compose ps
```

Deben aparecer `backend`, `frontend`, `postgres`, `redis`, `celery-worker` y `celery-beat` en estado *running*.

### 7. Crea las tablas y carga los datos de demo

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

`seed_demo` carga datos **100 % ficticios**: dos divisiones (Banca Persona y Banca Empresas), distritos, agencias, un usuario por rol, campañas, leads y gestiones. Solo corre sobre una base vacía, así que nunca se mezcla con datos reales.

### 8. Entra al sistema

Abre **<http://localhost:5173>** en el navegador y entra con:

- Usuario: `admin@demo.nexo`
- Contraseña: `Demo2026!`

Todos los usuarios demo usan esa misma contraseña. La lista completa, qué puede hacer cada uno y un guion para presentar el sistema están en **[DEMO.md](DEMO.md)**.

## Uso diario

Docker Desktop tiene que estar abierto antes de correr estos comandos.

| Para… | Ejecuta, dentro de la carpeta `Nexo` |
|---|---|
| Encender el sistema | `docker compose up -d` |
| Apagarlo (los datos se conservan) | `docker compose down` |
| Traer los últimos cambios de GitHub | `git pull`, y luego `docker compose up -d --build` y `docker compose exec backend python manage.py migrate` |
| Ver errores del backend | `docker compose logs -f backend` |
| Ver errores del frontend | `docker compose logs -f frontend` |
| Borrar todos los datos y empezar de cero | `docker compose down -v`, luego los pasos 6 y 7 |

`docker compose down -v` **borra la base de datos completa**. Úsalo solo cuando de verdad quieras empezar de cero.

## Direcciones útiles

| Dirección | Qué es |
|---|---|
| <http://localhost:5173> | La aplicación |
| <http://localhost:8000/api/docs/> | Documentación de la API (Swagger) |
| <http://localhost:8000/admin/> | Admin de Django (con `admin@demo.nexo`) |

## Si algo falla

| Síntoma | Solución |
|---|---|
| `error during connect` o `cannot find the file specified` | Docker Desktop no está abierto. Ábrelo, espera a que diga *Engine running* y repite. |
| `port is already allocated` (5432, 6379, 8000 o 5173) | Otro programa usa ese puerto, por ejemplo un PostgreSQL instalado en Windows. Ciérralo o detén ese servicio. |
| La página no carga justo después de encender | El frontend tarda unos segundos en compilar. Revisa con `docker compose logs -f frontend`. |
| `seed_demo` dice que la base ya tiene leads | Los datos demo ya están cargados, así que entra directamente. Para recargarlos de cero, usa `docker compose down -v` y repite los pasos 6 y 7. |
| `relation ... does not exist` | Faltan las tablas. Corre `docker compose exec backend python manage.py migrate`. |
| Docker no arranca y menciona WSL o virtualización | Revisa el paso 1 (virtualización) y los comandos `wsl` del paso 3. |

## Tests

```powershell
docker compose exec backend python -m pytest
```
