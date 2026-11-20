"""Carga datos 100% ficticios para hacer una demo de Nexo.

Uso (dentro del contenedor):
    docker compose exec backend python manage.py seed_demo

Crea dos divisiones (Banca Persona y Banca Empresas, para poder mostrar el
aislamiento), distritos,
agencias, un usuario por cada rol, catálogos de tipificación, tipos de
campaña con su esquema dinámico, campañas, leads asignados y gestiones con
fechas repartidas en las últimas semanas (para que los tableros de
Tendencia/Efectividad tengan algo que mostrar).

Por seguridad se niega a correr si la base ya tiene leads: está pensado
para una base recién creada, nunca para mezclarse con datos reales. Todos
los nombres, documentos y teléfonos son inventados.
"""

import csv
import io
import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.constants import RoleNames
from apps.accounts.models import Division, Role, User, UserAgencia, UserTerritorio
from apps.campaigns.models import (
    SECCION_DATOS_CLIENTE,
    Campaign,
    CampaignFieldDefinition,
    CampaignSection,
    CampaignType,
    LoteCarga,
    LoteEstado,
)
from apps.geo.models import Agencia, Territorio
from apps.leads.models import Assignment, Category, Lead, LeadEstado, ManagementLog, SubCategory
from apps.leads.services import tipificar_lead
from apps.opportunities.models import Opportunity

PASSWORD = "Demo2026!"

NOMBRES = [
    "Ana", "Luis", "María", "Jorge", "Lucía", "Carlos", "Sofía", "Miguel", "Valeria", "Diego",
    "Camila", "José", "Daniela", "Andrés", "Paula", "Ricardo", "Elena", "Fernando", "Gabriela", "Raúl",
]
APELLIDOS = [
    "Ramírez", "Torres", "Flores", "Castillo", "Mendoza", "Vargas", "Rojas", "Herrera", "Paredes",
    "Salazar", "Quispe", "Navarro", "Cárdenas", "Ríos", "Vega", "Campos", "Aguilar", "Soto",
]
SECTORES = ["Comercio", "Servicios", "Industria", "Agroindustria"]
EMPRESA_RAIZ = [
    "Distribuidora", "Comercial", "Inversiones", "Servicios", "Importadora", "Panificadora",
    "Transportes", "Constructora", "Agroindustrias", "Textiles",
]
EMPRESA_NOMBRE = [
    "El Roble", "Los Pinos", "Del Valle", "Santa Lucía", "Horizonte", "La Cumbre", "Atlántida",
    "San Andrés", "Cuscatlán", "El Progreso", "Las Brisas", "Montecristo",
]


class Command(BaseCommand):
    help = "Carga datos ficticios de demostración (solo en una base vacía)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Corre aunque ya existan leads (los datos demo se agregan a lo existente).",
        )

    def handle(self, *args, **options):
        if Lead.objects.exists() and not options["force"]:
            raise CommandError(
                "La base ya tiene leads. seed_demo está pensado para una base vacía; "
                "usa --force solo si sabes que no hay datos reales."
            )

        self.rng = random.Random(2026)  # mismos datos en cada laptop
        self.ahora = timezone.now()
        self.usados_dni = set()

        with transaction.atomic():
            self._crear_estructura()
            self._crear_usuarios()
            self._crear_catalogos()
            self._crear_tipos_y_campanas()
            self._crear_leads_creditos()
            self._crear_leads_empresas()
            self._crear_prospectos()

        self._resumen()

    # ── Estructura organizacional ────────────────────────────────────────
    def _crear_estructura(self):
        self.div_bp, _ = Division.objects.get_or_create(codigo="BP", defaults={"nombre": "Banca Persona"})
        self.div_be, _ = Division.objects.get_or_create(codigo="BE", defaults={"nombre": "Banca Empresas"})

        def territorio(codigo, nombre, division):
            return Territorio.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "division": division})[0]

        def agencia(codigo, nombre, terr):
            return Agencia.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "territorio": terr})[0]

        # Banca Persona: Distrito 1 y 2. Banca Empresas: Distrito 3.
        self.d1 = territorio("D1", "Distrito 1", self.div_bp)
        self.d2 = territorio("D2", "Distrito 2", self.div_bp)
        self.d3 = territorio("D3", "Distrito 3", self.div_be)

        self.a_centro = agencia("1", "Agencia Centro", self.d1)
        self.a_diagonal = agencia("2", "Diagonal Universitaria", self.d1)
        self.a_multiplaza = agencia("3", "Multiplaza", self.d2)
        self.a_merliot = agencia("4", "Merliot", self.d3)

    # ── Usuarios: uno por rol (contraseña común PASSWORD) ─────────────────
    def _crear_usuarios(self):
        roles = {r.nombre: r for r in Role.objects.all()}

        def usuario(email, nombre, apellido, rol, division=None, agencia=None, codigo=None, superuser=False):
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User(email=email)
            user.first_name = nombre
            user.last_name = apellido
            user.role = roles[rol]
            user.division = division
            user.agencia_principal = agencia
            user.codigo_empleado = codigo
            user.is_superuser = superuser
            user.is_staff = superuser
            user.is_active = True
            user.set_password(PASSWORD)
            user.save()
            return user

        self.admin = usuario("admin@demo.nexo", "Admin", "General", RoleNames.ADMIN, codigo="D-0001", superuser=True)
        self.admin_bp = usuario("admin.persona@demo.nexo", "Patricia", "Luna", RoleNames.ADMIN_DIVISION, self.div_bp, codigo="D-0002")
        self.gerente = usuario("gerente@demo.nexo", "Roberto", "Díaz", RoleNames.GERENTE, self.div_bp, codigo="D-0003")
        self.supervisor = usuario("supervisor@demo.nexo", "Mónica", "Prado", RoleNames.SUPERVISOR, self.div_bp, codigo="D-0004")
        self.jefe = usuario("jefe@demo.nexo", "Héctor", "Ortiz", RoleNames.JEFE, self.div_bp, codigo="D-0005")
        self.subjefe = usuario("subjefe@demo.nexo", "Claudia", "Reyes", RoleNames.SUBJEFE, self.div_bp, codigo="D-0006")

        self.ejecutivos_bp = [
            usuario("ejecutivo1@demo.nexo", "Kevin", "Mora", RoleNames.EJECUTIVO, self.div_bp, self.a_centro, "D-0101"),
            usuario("ejecutivo2@demo.nexo", "Rosa", "Calle", RoleNames.EJECUTIVO, self.div_bp, self.a_centro, "D-0102"),
            usuario("ejecutivo3@demo.nexo", "Iván", "Pinto", RoleNames.EJECUTIVO, self.div_bp, self.a_diagonal, "D-0103"),
            usuario("ejecutivo4@demo.nexo", "Nadia", "Suárez", RoleNames.EJECUTIVO, self.div_bp, self.a_multiplaza, "D-0104"),
            usuario("ejecutivo5@demo.nexo", "Óscar", "Lima", RoleNames.EJECUTIVO, self.div_bp, self.a_multiplaza, "D-0105"),
        ]

        self.admin_be = usuario("admin.empresas@demo.nexo", "Teresa", "Gil", RoleNames.ADMIN_DIVISION, self.div_be, codigo="D-0201")
        self.ejecutivos_be = [
            usuario("empresas1@demo.nexo", "Julio", "Benítez", RoleNames.EJECUTIVO, self.div_be, self.a_merliot, "D-0202"),
            usuario("empresas2@demo.nexo", "Inés", "Rivas", RoleNames.EJECUTIVO, self.div_be, self.a_merliot, "D-0203"),
        ]

        # Supervisor: todo el Distrito 1. Jefe multi-agencia: Agencia Centro y
        # Diagonal Universitaria a la vez (el caso nuevo de la v2). Subjefe:
        # solo Multiplaza.
        UserTerritorio.objects.get_or_create(usuario=self.supervisor, territorio=self.d1, activo=True)
        UserAgencia.objects.get_or_create(usuario=self.jefe, agencia=self.a_centro, activo=True)
        UserAgencia.objects.get_or_create(usuario=self.jefe, agencia=self.a_diagonal, activo=True)
        UserAgencia.objects.get_or_create(usuario=self.subjefe, agencia=self.a_multiplaza, activo=True)

    # ── Catálogos de tipificación (uno por división) ─────────────────────
    def _crear_catalogos(self):
        def categoria(nombre, division, subs):
            cat, _ = Category.objects.get_or_create(nombre=nombre, division=division)
            creadas = {}
            for sub_nombre, efecto, proximo in subs:
                creadas[sub_nombre] = SubCategory.objects.get_or_create(
                    category=cat,
                    nombre=sub_nombre,
                    defaults={"efecto": efecto, "requiere_proximo_contacto": proximo},
                )[0]
            return cat, creadas

        self.cat_efectivo = categoria("Contacto Efectivo", self.div_bp, [
            ("Venta Efectiva", "GANADA", False),
            ("Lo Pensará", "ABRE_OPORTUNIDAD", True),
            ("Volver a Llamar", "ABRE_OPORTUNIDAD", True),
            ("No le interesa", "PERDIDA", False),
        ])
        self.cat_no_contacto = categoria("No Contactado", self.div_bp, [
            ("No contesta", "SIN_EFECTO", False),
            ("Buzón de voz", "SIN_EFECTO", False),
            ("Número equivocado", "PERDIDA", False),
        ])
        self.cat_empresa = categoria("Contacto con la empresa", self.div_be, [
            ("Crédito aprobado", "GANADA", False),
            ("En evaluación", "ABRE_OPORTUNIDAD", True),
            ("Solicita propuesta", "ABRE_OPORTUNIDAD", True),
            ("No le interesa", "PERDIDA", False),
        ])
        self.cat_empresa_sin_contacto = categoria("Sin contacto", self.div_be, [
            ("No contesta", "SIN_EFECTO", False),
            ("Representante no disponible", "SIN_EFECTO", False),
        ])

    # ── Tipos de campaña (esquema dinámico) y campañas ───────────────────
    def _tipo(self, nombre, division, categoria, modo, secciones, campos):
        tipo, creado = CampaignType.objects.get_or_create(
            division=division, nombre=nombre, defaults={"categoria": categoria, "modo_carga": modo}
        )
        if not creado:
            return tipo
        secs = {
            SECCION_DATOS_CLIENTE: CampaignSection.objects.create(
                campaign_type=tipo, nombre=SECCION_DATOS_CLIENTE, orden=0, es_obligatoria=True
            )
        }
        for i, sec in enumerate(secciones, start=1):
            secs[sec] = CampaignSection.objects.create(campaign_type=tipo, nombre=sec, orden=i)
        for orden, (key, label, data_type, seccion, extra) in enumerate(campos):
            CampaignFieldDefinition.objects.create(
                campaign_type=tipo,
                field_key=key,
                label=label,
                data_type=data_type,
                seccion=secs[seccion],
                orden=orden,
                **extra,
            )
        return tipo

    def _crear_tipos_y_campanas(self):
        cliente = SECCION_DATOS_CLIENTE
        req = {"required": True}

        self.tipo_creditos = self._tipo(
            "Créditos Personales", self.div_bp, "VENTAS", "MASIVA", ["Datos de la oferta"],
            [
                ("nombre", "Nombre completo", "TEXTO", cliente, {**req, "es_nombre_cliente": True}),
                ("dni", "DNI", "TEXTO", cliente, {**req, "es_documento_identidad": True}),
                ("telefono", "Teléfono", "TEXTO", cliente, {**req, "es_telefono_contacto": True}),
                ("correo", "Correo", "TEXTO", cliente, {"mostrar_en_tabla": False}),
                ("segmento", "Segmento", "SELECT", cliente, {"options": ["Preferente", "Masivo", "Joven"]}),
                ("monto", "Monto ofertado", "NUMERO", "Datos de la oferta", req),
                ("tasa", "Tasa (%)", "NUMERO", "Datos de la oferta", {}),
                ("plazo", "Plazo (meses)", "SELECT", "Datos de la oferta", {"options": ["12", "24", "36", "48"]}),
                ("vence_oferta", "Vence la oferta", "FECHA", "Datos de la oferta", {"mostrar_en_tabla": False}),
            ],
        )
        self.tipo_pyme = self._tipo(
            "Crédito PYME", self.div_be, "VENTAS", "MASIVA", ["Datos de la oferta"],
            [
                ("razon_social", "Razón social", "TEXTO", cliente, {**req, "es_nombre_cliente": True}),
                ("nit", "NIT", "TEXTO", cliente, {**req, "es_documento_identidad": True}),
                ("telefono", "Teléfono", "TEXTO", cliente, {**req, "es_telefono_contacto": True}),
                ("representante", "Representante legal", "TEXTO", cliente, {}),
                ("sector", "Sector", "SELECT", cliente, {"options": SECTORES}),
                ("ventas_anuales", "Ventas anuales", "NUMERO", "Datos de la oferta", {"mostrar_en_tabla": False}),
                ("monto", "Monto ofertado", "NUMERO", "Datos de la oferta", req),
                ("plazo", "Plazo (meses)", "SELECT", "Datos de la oferta", {"options": ["12", "24", "36", "60"]}),
            ],
        )
        self.tipo_prospeccion = self._tipo(
            "Prospección Clientes", self.div_bp, "VENTAS", "INDIVIDUAL", ["Interés"],
            [
                ("nombre", "Nombre completo", "TEXTO", cliente, {**req, "es_nombre_cliente": True}),
                ("dni", "DNI", "TEXTO", cliente, {**req, "es_documento_identidad": True}),
                ("telefono", "Teléfono", "TEXTO", cliente, {**req, "es_telefono_contacto": True}),
                ("producto_interes", "Producto de interés", "SELECT", "Interés",
                 {"options": ["Crédito personal", "Tarjeta de crédito", "Cuenta de ahorros"]}),
            ],
        )

        hoy = timezone.localdate()

        def campana(nombre, tipo, division, producto):
            return Campaign.objects.get_or_create(
                nombre=nombre,
                division=division,
                defaults={
                    "campaign_type": tipo,
                    "fecha_inicio": hoy - timedelta(days=35),
                    "fecha_fin": hoy + timedelta(days=45),
                    "producto_default": producto,
                },
            )[0]

        self.camp_creditos = campana("Créditos Personales — Campaña de fin de año", self.tipo_creditos, self.div_bp, "Crédito personal")
        self.camp_pyme = campana("Crédito PYME — Cierre de año", self.tipo_pyme, self.div_be, "Crédito PYME")
        self.camp_prospeccion = campana("Prospección en agencia", self.tipo_prospeccion, self.div_bp, "")

    # ── Utilidades para leads ─────────────────────────────────────────────
    def _persona(self):
        nombre = f"{self.rng.choice(NOMBRES)} {self.rng.choice(APELLIDOS)} {self.rng.choice(APELLIDOS)}"
        while True:
            dni = f"9{self.rng.randint(1000000, 9999999)}"  # 8 dígitos, prefijo 9: no son DNI reales
            if dni not in self.usados_dni:
                self.usados_dni.add(dni)
                break
        telefono = f"900 {self.rng.randint(100, 999)} {self.rng.randint(100, 999)}"
        return nombre, dni, telefono

    def _empresa(self):
        return f"{self.rng.choice(EMPRESA_RAIZ)} {self.rng.choice(EMPRESA_NOMBRE)}, S.A. de C.V."

    def _nit(self):
        # Formato 0000-000000-000-0, con prefijo 9999: no corresponde a NIT reales.
        while True:
            nit = f"9999-{self.rng.randint(100000, 999999)}-{self.rng.randint(100, 999)}-{self.rng.randint(0, 9)}"
            if nit not in self.usados_dni:
                self.usados_dni.add(nit)
                return nit

    def _hace(self, dias, horas=0):
        return self.ahora - timedelta(days=dias, hours=horas)

    def _lote(self, campaign, usuario, nombre_archivo, filas, producto):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)
        lote = LoteCarga(
            campaign=campaign,
            usuario_carga=usuario,
            nombre_archivo=nombre_archivo,
            cantidad_registros=len(filas),
            producto=producto,
            estado=LoteEstado.COMPLETADO,
        )
        lote.archivo.save(nombre_archivo, ContentFile(buffer.getvalue().encode("utf-8")), save=False)
        lote.save()
        return lote

    def _crear_lead(self, *, campaign, lote, atributos, agencia, creado, monto=None, nombre_key="nombre", documento_key="dni"):
        lead = Lead.objects.create(
            campaign=campaign,
            lote_carga=lote,
            cliente_nombre=atributos[nombre_key],
            telefono=atributos["telefono"],
            documento_identidad=atributos[documento_key],
            agencia=agencia,
            distrito=agencia.territorio,
            estado=LeadEstado.NUEVO,
            atributos=atributos,
            monto_oferta=monto,
        )
        Lead.objects.filter(pk=lead.pk).update(created_at=creado)
        lead.created_at = creado
        return lead

    def _asignar(self, lead, ejecutivo, asignado_por, cuando):
        assignment = Assignment.objects.create(
            lead=lead,
            usuario_origen=None,
            usuario_destino=ejecutivo,
            agencia_origen=lead.agencia,
            agencia_destino=None,
            asignado_por=asignado_por,
        )
        Assignment.objects.filter(pk=assignment.pk).update(timestamp=cuando)
        lead.usuario_asignado = ejecutivo
        lead.fecha_asignacion = cuando
        lead.estado = LeadEstado.ASIGNADO
        lead.save(update_fields=["usuario_asignado", "fecha_asignacion", "estado"])

    def _gestionar(self, lead, usuario, category, subcategory, comentario, cuando):
        proximo = cuando + timedelta(days=3) if subcategory.requiere_proximo_contacto else None
        log, oportunidad = tipificar_lead(
            lead=lead,
            usuario=usuario,
            category=category,
            subcategory=subcategory,
            comentario=comentario,
            fecha_proximo_contacto=proximo,
        )
        # tipificar_lead fecha todo "ahora"; lo movemos al pasado para que
        # la demo tenga historia (Tendencia, tiempo a primera gestión, etc.).
        ManagementLog.objects.filter(pk=log.pk).update(timestamp=cuando)
        Lead.objects.filter(pk=lead.pk).update(fecha_ultima_gestion=cuando)
        lead.fecha_ultima_gestion = cuando
        if oportunidad is not None:
            cambios = {}
            if oportunidad.created_at >= self.ahora - timedelta(minutes=5):
                cambios["created_at"] = cuando
            if oportunidad.fecha_cierre:
                cambios["fecha_cierre"] = cuando
            if cambios:
                Opportunity.objects.filter(pk=oportunidad.pk).update(**cambios)

    # ── Campaña de créditos: el grueso de la demo ────────────────────────
    def _crear_leads_creditos(self):
        _, subs_ef = self.cat_efectivo
        cat_ef = self.cat_efectivo[0]
        cat_nc, subs_nc = self.cat_no_contacto

        reparto = [  # (agencia, ejecutivos de esa agencia, quién asigna)
            (self.a_centro, self.ejecutivos_bp[0:2], self.jefe),
            (self.a_diagonal, self.ejecutivos_bp[2:3], self.jefe),
            (self.a_multiplaza, self.ejecutivos_bp[3:5], self.subjefe),
        ]

        for n_lote, dias_lote in ((1, 30), (2, 14)):
            filas, datos = [], []
            for agencia, _, _ in reparto:
                for _ in range(12 if n_lote == 1 else 8):
                    nombre, dni, telefono = self._persona()
                    monto = float(self.rng.choice([5000, 8000, 12000, 15000, 20000, 30000]))
                    atributos = {
                        "nombre": nombre,
                        "dni": dni,
                        "telefono": telefono,
                        "correo": f"{nombre.split()[0].lower()}.{dni[-4:]}@correo-demo.com",
                        "segmento": self.rng.choice(["Preferente", "Masivo", "Joven"]),
                        "monto": monto,
                        "tasa": float(self.rng.choice([14.9, 17.5, 19.9, 22.0])),
                        "plazo": self.rng.choice(["12", "24", "36", "48"]),
                        "vence_oferta": (date.today() + timedelta(days=60)).isoformat(),
                    }
                    filas.append({**atributos, "agencia": agencia.codigo})
                    datos.append((agencia, atributos, monto))

            lote = self._lote(
                self.camp_creditos, self.admin_bp, f"creditos_lote{n_lote}_demo.csv", filas, "Crédito personal"
            )
            for agencia, atributos, monto in datos:
                creado = self._hace(dias_lote, self.rng.randint(0, 6))
                lead = self._crear_lead(
                    campaign=self.camp_creditos, lote=lote, atributos=atributos, agencia=agencia, creado=creado, monto=monto
                )
                _, ejecutivos, asignador = next(r for r in reparto if r[0] == agencia)

                # ~15% queda sin asignar: así el jefe tiene qué asignar en vivo.
                if self.rng.random() < 0.15:
                    continue
                ejecutivo = self.rng.choice(ejecutivos)
                asignado = creado + timedelta(hours=self.rng.randint(2, 20))
                self._asignar(lead, ejecutivo, asignador, asignado)

                # ~20% asignado pero aún sin gestionar.
                if self.rng.random() < 0.2:
                    continue

                cuando = asignado + timedelta(hours=self.rng.randint(3, 72))
                pasos = self.rng.choices(
                    [
                        [("nc", "No contesta"), ("ef", "Venta Efectiva")],
                        [("ef", "Lo Pensará"), ("ef", "Venta Efectiva")],
                        [("ef", "Volver a Llamar")],
                        [("ef", "Lo Pensará")],
                        [("nc", "No contesta"), ("nc", "Buzón de voz")],
                        [("ef", "No le interesa")],
                        [("nc", "Número equivocado")],
                        [("ef", "Venta Efectiva")],
                    ],
                    weights=[3, 3, 2, 2, 2, 2, 1, 3],
                )[0]
                for i, (cat_key, sub_nombre) in enumerate(pasos):
                    if cuando > self.ahora:
                        break
                    category, subs = (cat_ef, subs_ef) if cat_key == "ef" else (cat_nc, subs_nc)
                    # De vez en cuando interviene el jefe (se ve en la línea de tiempo).
                    gestor = self.jefe if (i > 0 and agencia in (self.a_centro, self.a_diagonal) and self.rng.random() < 0.25) else ejecutivo
                    self._gestionar(lead, gestor, category, subs[sub_nombre], _comentario(sub_nombre), cuando)
                    cuando += timedelta(days=self.rng.randint(1, 4), hours=self.rng.randint(0, 8))

        # Una reasignación entre agencias del mismo distrito, para la "cadena de custodia".
        lead = Lead.objects.filter(campaign=self.camp_creditos, agencia=self.a_centro, usuario_asignado__isnull=False).first()
        if lead:
            cuando = (lead.fecha_asignacion or self.ahora) + timedelta(days=2)
            destino = self.ejecutivos_bp[2]
            assignment = Assignment.objects.create(
                lead=lead,
                usuario_origen=lead.usuario_asignado,
                usuario_destino=destino,
                agencia_origen=self.a_centro,
                agencia_destino=self.a_diagonal,
                asignado_por=self.supervisor,
            )
            Assignment.objects.filter(pk=assignment.pk).update(timestamp=min(cuando, self.ahora))
            Lead.objects.filter(pk=lead.pk).update(
                usuario_asignado=destino, agencia=self.a_diagonal, distrito=self.d1, fecha_asignacion=min(cuando, self.ahora)
            )

    # ── Banca Empresas: otra división, para mostrar el aislamiento ───────
    def _crear_leads_empresas(self):
        cat_e, subs_e = self.cat_empresa
        cat_s, subs_s = self.cat_empresa_sin_contacto
        filas, datos = [], []
        for _ in range(16):
            razon_social = self._empresa()
            nombre, _, telefono = self._persona()
            monto = float(self.rng.choice([25000, 50000, 75000, 100000, 150000]))
            atributos = {
                "razon_social": razon_social,
                "nit": self._nit(),
                "telefono": telefono,
                "representante": nombre,
                "sector": self.rng.choice(SECTORES),
                "ventas_anuales": float(self.rng.randint(3, 40) * 50000),
                "monto": monto,
                "plazo": self.rng.choice(["12", "24", "36", "60"]),
            }
            filas.append({**atributos, "agencia": self.a_merliot.codigo})
            datos.append(atributos)

        lote = self._lote(self.camp_pyme, self.admin_be, "credito_pyme_demo.csv", filas, "Crédito PYME")
        for atributos in datos:
            creado = self._hace(20, self.rng.randint(0, 6))
            lead = self._crear_lead(
                campaign=self.camp_pyme, lote=lote, atributos=atributos, agencia=self.a_merliot, creado=creado,
                monto=atributos["monto"], nombre_key="razon_social", documento_key="nit",
            )
            ejecutivo = self.rng.choice(self.ejecutivos_be)
            asignado = creado + timedelta(hours=4)
            self._asignar(lead, ejecutivo, self.admin_be, asignado)
            cuando = asignado + timedelta(hours=self.rng.randint(5, 96))
            paso = self.rng.choice(
                ["Crédito aprobado", "En evaluación", "Solicita propuesta", "No le interesa", "No contesta", "Representante no disponible"]
            )
            if paso in subs_e:
                self._gestionar(lead, ejecutivo, cat_e, subs_e[paso], _comentario(paso), cuando)
            else:
                self._gestionar(lead, ejecutivo, cat_s, subs_s[paso], _comentario(paso), cuando)

    # ── Prospección (registro individual) ────────────────────────────────
    def _crear_prospectos(self):
        cat_ef, subs_ef = self.cat_efectivo
        for i, ejecutivo in enumerate(self.ejecutivos_bp[:3]):
            for j in range(2):
                nombre, dni, telefono = self._persona()
                atributos = {
                    "nombre": nombre,
                    "dni": dni,
                    "telefono": telefono,
                    "producto_interes": self.rng.choice(["Crédito personal", "Tarjeta de crédito", "Cuenta de ahorros"]),
                }
                creado = self._hace(10 - i * 3 - j, 2)
                lead = self._crear_lead(
                    campaign=self.camp_prospeccion, lote=None, atributos=atributos,
                    agencia=ejecutivo.agencia_principal, creado=creado,
                )
                Lead.objects.filter(pk=lead.pk).update(
                    usuario_asignado=ejecutivo, fecha_asignacion=creado, estado=LeadEstado.ASIGNADO
                )
                lead.refresh_from_db()
                if j == 0:
                    self._gestionar(lead, ejecutivo, cat_ef, subs_ef["Lo Pensará"], _comentario("Lo Pensará"), creado + timedelta(hours=1))

    def _resumen(self):
        self.stdout.write(self.style.SUCCESS("\nDatos demo cargados."))
        self.stdout.write(
            f"  Leads: {Lead.objects.count()}  ·  Gestiones: {ManagementLog.objects.count()}  ·  "
            f"Oportunidades: {Opportunity.objects.count()}\n"
        )
        self.stdout.write(f"Contraseña de todos los usuarios demo: {PASSWORD}\n")
        filas = [
            ("admin@demo.nexo", "Super admin (ve todas las divisiones)"),
            ("admin.persona@demo.nexo", "Admin de división · Banca Persona"),
            ("gerente@demo.nexo", "Gerente · Banca Persona"),
            ("supervisor@demo.nexo", "Supervisor · Distrito 1"),
            ("jefe@demo.nexo", "Jefe multi-agencia · Agencia Centro + Diagonal Universitaria"),
            ("subjefe@demo.nexo", "Subjefe · Multiplaza"),
            ("ejecutivo1@demo.nexo", "Ejecutivo · Agencia Centro"),
            ("admin.empresas@demo.nexo", "Admin de división · Banca Empresas"),
            ("empresas1@demo.nexo", "Ejecutivo · Merliot (Banca Empresas)"),
        ]
        for email, desc in filas:
            self.stdout.write(f"  {email:<26} {desc}")


def _comentario(subcategoria: str) -> str:
    return {
        "Venta Efectiva": "Cliente aceptó la oferta, se coordinó firma en agencia.",
        "Lo Pensará": "Interesado, pide tiempo para revisarlo con su familia.",
        "Volver a Llamar": "Está ocupado, pidió que lo llamen otro día.",
        "No le interesa": "Indica que ya tiene financiamiento vigente con otra entidad.",
        "No contesta": "Se llamó dos veces sin respuesta.",
        "Buzón de voz": "Se dejó mensaje en buzón.",
        "Número equivocado": "El número pertenece a otra persona.",
        "Crédito aprobado": "Comité aprobó la línea; se agenda firma con el representante legal.",
        "En evaluación": "Envió estados financieros, pendiente análisis de riesgo.",
        "Solicita propuesta": "Pide propuesta formal por correo con tasa y plazo.",
        "Representante no disponible": "La recepción indica que el representante está en reunión.",
    }.get(subcategoria, "Gestión registrada.")
