# Manual Técnico del Sistema — PymeSoft (FacturApp)

> [!IMPORTANT]
> **Documento Oficial de Ingeniería y Arquitectura**
> Este manual documenta la arquitectura, el modelo de datos, la API RESTful, los mecanismos de seguridad y los procedimientos de despliegue del ecosistema **PymeSoft** en su estado actual de desarrollo.

---

## 1. Ficha Técnica y Alcance del Sistema

| Atributo | Especificación |
| :--- | :--- |
| **Nombre del Sistema** | **PymeSoft** (núcleo backend identificado como *FacturApp*) |
| **Propósito** | Ecosistema integral multi-empresa (*multi-tenant*) para la gestión comercial, facturación POS, cobros electrónicos (Datáfono y Link de Pago/QR), control de inventario, compras a proveedores y analítica de negocio para PYMES. |
| **Arquitectura General** | Arquitectura distribuida en 3 capas desacopladas mediante submódulos Git: API RESTful Central (`PYMES_BE`), Aplicación Web SSR (`PYMES_FE`) y Aplicación Móvil Híbrida / SPA (`pymesoft-movil`). |
| **Motor de Base de Datos** | **SQLAlchemy 2.0 ORM** compatible de forma transparente con **MySQL 8.x** (producción) y **SQLite 3** (`pymes.db` local/contingencia) con motor de auto-migración al arranque. |
| **Seguridad y Cumplimiento** | Autenticación JWT con revocación instantánea (`sesion_version`), control de acceso basado en roles por empresa (RBAC Multi-Tenant), cifrado simétrico **Fernet (AES-128-CBC + HMAC-SHA256)** para secretos de pasarelas, limitación de tasa (*Rate Limiting*) y sanitización automática **PCI-DSS**. |
| **Integraciones de Pago** | **Bold API** (terminales Smart POS / datáfonos físicos), **Wompi API** (links de pago, QR, PSE, Nequi, tarjetas) y **Motor Simulado Sandbox** integrado para pruebas y capacitación sin credenciales bancarias reales. |

---

## 2. Arquitectura de Software y Diseño del Sistema

### 2.1 Diagrama de Arquitectura de Alto Nivel

```mermaid
flowchart TB
    subgraph Clientes["Capa de Presentación (Clientes)"]
        FE["💻 PYMES_FE (Web SSR)\nFlask 3.0 + Jinja2 + Bootstrap 4\nPuerto: 5001"]
        MOV["📱 pymesoft-movil (App Híbrida / PWA)\nAngular 22 + Ionic 9 + Capacitor 8.5\nPuerto: 8100 / Nginx: 8080 / Android APK"]
    end

    subgraph Backend["Capa de Negocio y Servicios — PYMES_BE (Puerto: 5000)"]
        API["🛡️ API Gateway / Blueprints Flask (18 Rutas /api/*)\nCORS + Flask-Limiter + JWT Verification"]
        SEC["🔐 Middleware de Seguridad y Multi-Tenancy\n@jwt_required | @roles_required | @tenant_required\nResolución de cabecera X-Empresa-ID"]
        CTRL["⚙️ Controladores de Dominio (15 Controladores)\nFacturación, Inventario, Compras, CRM, Reportes, Usuarios"]
        PAG["💳 Subsistema de Pagos Electrónicos (src/services/pagos/)\ncobros_service.py + cifrado.py (Fernet)"]
        MIG["🔄 Auto-Migrador e Inicializador\nmigrations.py (Esquema, Semillas y Limpieza PCI-DSS)"]
    end

    subgraph Persistencia["Capa de Datos"]
        DB[("🗄️ Base de Datos Relacional\nSQLite (pymes.db) / MySQL 8\n16 Tablas Normalizadas")]
    end

    subgraph Externos["Pasarelas de Pago Externas"]
        BOLD["📟 Bold API\nSmart POS / Datáfonos\n(HMAC-SHA256 Webhook)"]
        WOMPI["🔗 Wompi API\nLinks de Pago / PSE / Nequi\n(SHA256 Event Checksum)"]
    end

    FE -->|"HTTP REST + Bearer JWT\n+ Header X-Empresa-ID"| API
    MOV -->|"HTTP REST + Bearer JWT\n+ Header X-Empresa-ID"| API
    API --> SEC
    SEC --> CTRL
    SEC --> PAG
    CTRL --> DB
    PAG --> DB
    MIG --> DB
    PAG <-->|"REST API / Webhooks"| BOLD
    PAG <-->|"REST API / Webhooks"| WOMPI
```

### 2.2 Arquitectura Multi-Tenant (Multi-Empresa)

PymeSoft implementa un modelo **Multi-Tenant por discriminador de columna (`id_empresa`)** con vinculación muchos-a-muchos entre usuarios y empresas a través de la tabla `usuario_empresas`:

1. **Aislamiento de Datos Operativos**: Todas las entidades transaccionales y de catálogo (`productos`, `clientes`, `proveedores`, `facturas`, `compras`, `metodos_pago`, `terminales_pago`, `transacciones_pago`) poseen la columna `id_empresa`, garantizando que cada empresa opere sobre su propio inventario, cartera de clientes y numeración consecutiva independiente.
2. **Resolución Dinámica del Tenant (`get_current_tenant()`)**:
   Implementada en `PYMES_BE/src/utils/security.py`:
   - Extrae el identificador de la empresa activa desde la cabecera HTTP `X-Empresa-ID` (o en su defecto del parámetro `empresa_id` / cuerpo JSON `id_empresa`).
   - Verifica en la tabla `usuario_empresas` que el usuario autenticado posea un vínculo con `estado == 'Activo'` para dicha empresa (excepto si el usuario tiene rol global `1` de Superadministrador).
   - El decorador `@tenant_required` bloquea con `HTTP 403` cualquier intento de operar sobre registros sin una empresa activa válida.

### 2.3 Flujo de Autenticación JWT y Revocación Global de Sesiones

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario (Web / Móvil)
    participant C as Cliente (PYMES_FE / pymesoft-movil)
    participant B as Backend API (PYMES_BE)
    participant DB as Base de Datos

    U->>C: Ingresa username y password
    C->>B: POST /api/auth/login
    B->>DB: Consulta Usuarios (username) y UsuarioEmpresas (Activo)
    DB-->>B: Datos de usuario + sesion_version + lista de empresas
    B-->>C: 200 OK {access_token (2h), refresh_token (30d), usuario, empresas}
    C->>C: Guarda JWT y fija empresa_activa (X-Empresa-ID)

    Note over C,B: Peticiones subsecuentes a recursos protegidos
    C->>B: GET /api/productos (Authorization: Bearer JWT, X-Empresa-ID: 1)
    B->>DB: @jwt.token_verification_loader verifica estado=='Activo' y claim 'sv' == usuario.sesion_version
    B->>DB: @roles_required y @tenant_required validan rol en usuario_empresas
    DB-->>B: Registros filtrados por id_empresa = 1
    B-->>C: 200 OK (JSON paginado)

    Note over U,DB: Cierre de Sesión Global en Todos los Dispositivos
    U->>C: Pulsa "Cerrar sesión en todos los dispositivos"
    C->>B: POST /api/auth/logout-global
    B->>DB: Incrementa usuario.sesion_version = sesion_version + 1
    B-->>C: 200 OK (Todos los tokens emitidos previamente quedan inválidos al instante)
```

### 2.4 Subsistema de Cobros Electrónicos y Conciliación

El paquete `PYMES_BE/src/services/pagos/` desacopla la lógica de facturación de los proveedores de pago mediante dos canales principales:

```mermaid
sequenceDiagram
    autonumber
    actor V as Vendedor / Caja
    participant FE as Cliente Web / Móvil
    participant BE as CobrosService (PYMES_BE)
    participant GW as Pasarela (Bold / Wompi / Simulado)
    actor CL as Cliente Comprador

    V->>FE: Crea factura y selecciona método (Datáfono o Link)
    FE->>BE: POST /api/facturas/{id}/cobros {canal, id_metodo_pago, id_terminal}
    BE->>BE: Desencripta API Key con Fernet (cifrado.py)
    alt Canal = datafono (Bold / Simulado)
        BE->>GW: POST /payments/payment-intent (serial terminal, monto, referencia)
        GW-->>CL: Enciende pantalla del datáfono físico con el monto a cobrar
    else Canal = link (Wompi / Simulado)
        BE->>GW: POST /v1/payment_links (monto_centavos, referencia, redirect_url)
        GW-->>BE: Retorna URL de pago (url_pago) y ID externo
        BE-->>FE: Muestra Link / Código QR en pantalla
        FE-->>CL: Cliente escanea QR o abre link (PSE / Nequi / Tarjeta)
    end
    CL->>GW: Autoriza el pago
    par Notificación Asíncrona (Webhook)
        GW->>BE: POST /api/webhooks/bold o /api/webhooks/wompi (Firma criptográfica)
        BE->>BE: Verifica HMAC-SHA256 / SHA256 Checksum
        BE->>BE: Actualiza TransaccionesPago -> APROBADA y Facturas -> Pagada
    and Consulta en Tiempo Real (Polling)
        FE->>BE: GET /api/cobros/{id_transaccion}
        BE->>GW: Consulta estado en vivo si sigue PENDIENTE
        BE-->>FE: Estado actualizado (APROBADA / RECHAZADA)
    end
```

---

## 3. Stack Tecnológico y Dependencias

### 3.1 Backend (`PYMES_BE`)
- **Lenguaje y Entorno**: Python 3.11 (`python:3.11-slim` en contenedor Docker).
- **Framework Web**: `Flask >= 3.0.0`.
- **ORM y Persistencia**: `SQLAlchemy >= 2.0.0` (compatible con `SQLite3` nativo y `MySQL` mediante `PyMySQL` / `mysql-connector-python`).
- **Seguridad y Autenticación**:
  - `Flask-JWT-Extended >= 4.6.0` (emisión y verificación de tokens JWT de acceso y refresco).
  - `Werkzeug >= 3.0.0` (hashing criptográfico de contraseñas con `pbkdf2:sha256`).
  - `cryptography >= 42.0.0` (cifrado simétrico Fernet para llaves de API y secretos de webhooks).
  - `Flask-Limiter >= 3.5.0` (protección contra ataques de fuerza bruta y denegación de servicio).
  - `Flask-CORS >= 4.0.0` (habilitación de políticas CORS para cabeceras `Authorization` y `X-Empresa-ID`).

### 3.2 Frontend Web de Escritorio (`PYMES_FE`)
- **Framework**: `Flask 3.0.0` con renderizado del lado del servidor (**SSR**) mediante plantillas **Jinja2**.
- **Cliente HTTP**: Clase centralizada `APIClient` sobre `requests 2.31.0`, que inyecta automáticamente `Authorization: Bearer <token>` y `X-Empresa-ID`, e intercepta respuestas `HTTP 401` para renovar transparentemente el token mediante `/api/auth/refresh`.
- **Interfaz Gráfica**: Bootstrap 4.0, FontAwesome 5.15.4, jQuery 3.2.1 y Popper.js.
- **Servidor WSGI de Producción**: `gunicorn 21.2.0`.

### 3.3 Aplicación Móvil Híbrida y Web SPA (`pymesoft-movil`)
- **Framework SPA**: `Angular 22.0.1` + `TypeScript 6.0` + `RxJS 7.8.0`.
- **Componentes UI Móviles**: `@ionic/angular 9.0.0` + `ionicons 8.1.0`.
- **Runtime Nativo Multiplataforma**: `Capacitor 8.5.0` (`appId: com.pymesoft.app`, `appName: PYMESOFT`).
- **Plugins Nativos Integrados**:
  - `@capacitor/camera` (`^8.2.4`): Captura fotográfica desde cámara o galería con redimensionamiento automático a JPEG Base64 (`600px`) en productos y perfil de usuario.
  - `@capacitor/app` (`8.1.1`): Control del botón físico "Atrás" en Android.
  - `@capacitor/status-bar` (`8.0.3`): Personalización de la barra de estado nativa (`#2563eb`).
  - `@capgo/capacitor-updater` (`^8.51.18`): Soporte para actualizaciones OTA (*Over-The-Air*).
- **Servidor Web en Contenedor**: `nginx:alpine` (construcción multi-etapa con `node:20-alpine`).

---

## 4. Estructura del Proyecto y Directorios

```text
PYMES/
├── .gitmodules                         # Definición de los 3 submódulos Git
├── docker-compose.yml                  # Orquestación de contenedores (Backend 5000 + Móvil/Web 8080)
├── docs/                               # Documentación oficial del sistema
│   ├── MANUAL_TECNICO.md
│   ├── MANUAL_DE_USUARIO.md
│   └── PLAN_DE_CAPACITACION.md
│
├── PYMES_BE/                           # SUBMÓDULO 1: Backend API RESTful
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pymes.db                        # Base de datos SQLite local autogestionada
│   └── src/
│       ├── app.py                      # Punto de entrada Flask, CORS, JWT, RateLimiter y Blueprints
│       ├── models/                     # 16 Modelos ORM SQLAlchemy
│       ├── controllers/                # 15 Controladores de lógica de negocio
│       ├── routes/                     # 18 Blueprints REST (/api/*)
│       ├── services/pagos/             # Integraciones Bold, Wompi, Simulado y Conciliación
│       └── utils/                      # security.py, cifrado.py, migrations.py, pagination.py
│
├── PYMES_FE/                           # SUBMÓDULO 2: Frontend Web de Escritorio (Flask SSR)
│   ├── requirements.txt
│   └── src/
│       ├── __init__.py                 # Fábrica create_app() y procesadores de contexto
│       ├── app.py                      # Servidor web en puerto 5001
│       ├── config/config.py            # Configuración de SECRET_KEY y API_BASE_URL
│       ├── utils/decorators.py         # Decorador @requiere_rol(*roles)
│       ├── services/                   # APIClient y 12 servicios consumidores de PYMES_BE
│       ├── routes/                     # 10 Blueprints de vistas web
│       └── templates/                  # Plantillas HTML Jinja2 por módulo
│
└── pymesoft-movil/                     # SUBMÓDULO 3: App Móvil Android y Web SPA (Ionic + Angular)
    ├── Dockerfile                      # Build Node 20 -> Nginx Alpine
    ├── package.json                    # Scripts ng serve, build y build:apk
    ├── capacitor.config.ts             # Configuración nativa Capacitor
    ├── android/                        # Proyecto nativo Android (Gradle)
    └── src/
        ├── environments/               # Resolución inteligente de URL del API (LAN / Emulador / Prod)
        └── app/
            ├── app-routing.module.ts   # Rutas lazy-loaded protegidas por AuthGuard y RoleGuard
            ├── guards/                 # auth.guard.ts y role.guard.ts
            ├── services/auth.service.ts# Gestión de sesión, JWT, X-Empresa-ID y helpers de rol
            └── pages/                  # 13 páginas modulares (login, inicio, facturas, productos, etc.)
```

---

## 5. Modelo de Base de Datos y Diccionario de Datos

### 5.1 Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : "asigna rol global"
    ROLES ||--o{ USUARIO_EMPRESAS : "asigna rol por empresa"
    USUARIOS ||--o{ USUARIO_EMPRESAS : "pertenece a"
    EMPRESAS ||--o{ USUARIO_EMPRESAS : "vincula"

    EMPRESAS ||--o{ PRODUCTOS : "posee"
    EMPRESAS ||--o{ CLIENTES : "posee"
    EMPRESAS ||--o{ PROVEEDORES : "posee"
    EMPRESAS ||--o{ FACTURAS : "emite"
    EMPRESAS ||--o{ COMPRAS : "registra"
    EMPRESAS ||--o{ METODOS_PAGO : "configura"
    EMPRESAS ||--o{ TERMINALES_PAGO : "vincula"

    CATEGORIAS ||--o{ PRODUCTOS : "clasifica"
    PROVEEDORES ||--o{ PRODUCTOS : "suministra"
    PROVEEDORES ||--o{ COMPRAS : "abastece"

    CLIENTES ||--o{ FACTURAS : "compra"
    USUARIOS ||--o{ FACTURAS : "vendedor"
    METODOS_PAGO ||--o{ FACTURAS : "medio de pago"
    FACTURAS ||--|{ DETALLE_FACTURAS : "contiene líneas"
    PRODUCTOS ||--o{ DETALLE_FACTURAS : "producto vendido"

    USUARIOS ||--o{ COMPRAS : "comprador"
    COMPRAS ||--|{ DETALLE_COMPRAS : "contiene líneas"
    PRODUCTOS ||--o{ DETALLE_COMPRAS : "producto comprado"

    PRODUCTOS ||--o{ MOVIMIENTOS_INVENTARIO : "registra kardex"
    USUARIOS ||--o{ MOVIMIENTOS_INVENTARIO : "ejecuta"

    FACTURAS ||--o{ TRANSACCIONES_PAGO : "procesa cobro"
    TERMINALES_PAGO ||--o{ TRANSACCIONES_PAGO : "cobra en datáfono"
    METODOS_PAGO ||--o{ TRANSACCIONES_PAGO : "usa pasarela"
```

### 5.2 Especificación de las 16 Tablas del Sistema

| # | Tabla | Archivo Modelo | Clave Primaria | Columnas Principales y Reglas de Negocio |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `roles` | `src/models/roles.py` | `id` (INT) | `nombre` (UNIQUE: `1=Administrador`, `2=Vendedor`, `3=Almacenista`), `descripcion`. |
| 2 | `usuarios` | `src/models/usuarios.py` | `id` (INT) | `tipo_documento`, `documento` (UNIQUE), `nombre`, `apellido`, `email` (UNIQUE), `username` (UNIQUE, autogenerado `nombre.apellido`), `password_hash` (`pbkdf2:sha256`), `id_rol` (FK `roles.id`), `estado` (`Activo`/`Inactivo`), datos bancarios (`banco`, `tipo_cuenta`, `numero_cuenta`), datos demográficos, `sesion_version` (INT, revocación JWT), `foto` (Base64). |
| 3 | `empresas` | `src/models/empresas.py` | `id` (INT) | `nombre`, `nit` (UNIQUE), `direccion`, `telefono`, `email`, `estado` (`Activo`/`Inactivo`). |
| 4 | `usuario_empresas` | `src/models/usuario_empresas.py` | `id` (INT) | `usuario_id` (FK `usuarios.id`), `empresa_id` (FK `empresas.id`), `rol_id` (FK `roles.id`), `estado` (`Activo` / `Desvinculado`). Define el rol específico del usuario dentro de cada empresa. |
| 5 | `categorias` | `src/models/categorias.py` | `id` (INT) | `nombre` (VARCHAR 100, NOT NULL). |
| 6 | `proveedores` | `src/models/proveedores.py` | `id` (INT) | `codigo` (UNIQUE: `PROV-E{emp}-{03d}`), `nit` (UNIQUE), `nombre`, `contacto`, `telefono`, `direccion`, `email`, `detalle_servicios`, `estado`, `id_empresa`. |
| 7 | `productos` | `src/models/productos.py` | `id` (INT) | `codigo` (UNIQUE: `PROD-E{emp}-{03d}`), `nombre`, `descripcion`, `unidad_medida` (`UND`, `KG`, `LB`, `LT`, `MT`, `CAJA`, `PAQ`), `precio` (FLOAT), `costo` (FLOAT, default 70% del precio), `stock` (INT), `id_categoria` (FK), `id_proveedor` (FK nullable), `estado`, `imagen` (Base64), `id_empresa`. |
| 8 | `clientes` | `src/models/clientes.py` | `id` (INT) | `codigo` (UNIQUE: `CLI-E{emp}-{03d}`), `tipo_documento`, `documento` (UNIQUE), `nombre`, `apellido`, `direccion`, `telefono`, `email`, `estado`, `created_at`, `id_empresa`. |
| 9 | `metodos_pago` | `src/models/metodos_pago.py` | `id` (INT) | `nombre`, `descripcion`, `tipo` (`Efectivo`, `Transferencia`, `Tarjeta`, `Pasarela`), `banco`, `numero_cuenta`, `titular`, `id_empresa` (`NULL` = global), `estado`, `pasarela` (`ninguna`, `wompi`, `bold`, `simulado`), `api_key_publica`, `api_key_privada` (cifrada `enc:`), `webhook_secret` (cifrada `enc:`), `integrity_secret` (cifrada `enc:`), `modo` (`sandbox`/`produccion`). |
| 10 | `facturas` | `src/models/facturas.py` | `id` (INT) | `numero` (UNIQUE: `FAC-E{emp}-{03d}`), `fecha`, `subtotal`, `iva`, `descuento`, `total`, `id_cliente` (FK), `id_usuario` (FK), `id_metodo_pago` (FK), `estado` (`Emitida`, `Pagada`, `Cancelada`), `id_empresa`, `pasarela`, `referencia_pago`. |
| 11 | `detalle_facturas` | `src/models/detalle_facturas.py` | `id` (INT) | `id_factura` (FK), `id_producto` (FK), `cantidad` (INT), `precio_unitario` (FLOAT), `subtotal` (FLOAT). |
| 12 | `compras` | `src/models/compras.py` | `id` (INT) | `numero` (UNIQUE: `COMP-E{emp}-{03d}`), `fecha`, `subtotal`, `iva`, `descuento`, `total`, `id_proveedor` (FK), `id_usuario` (FK), `id_metodo_pago`, `metodo_pago`, `referencia_pago`, `estado` (`Completada`, `Cancelada`), `id_empresa`. |
| 13 | `detalle_compras` | `src/models/detalle_compras.py` | `id` (INT) | `id_compra` (FK), `id_producto` (FK), `cantidad` (INT), `costo_unitario` (FLOAT), `subtotal` (FLOAT). |
| 14 | `movimientos_inventario` | `src/models/movimiento_inventario.py` | `id` (INT) | `tipo_movimiento` (`ENTRADA` / `SALIDA`), `cantidad`, `fecha`, `observacion`, `id_producto` (FK), `id_usuario` (FK). |
| 15 | `terminales_pago` | `src/models/terminales.py` | `id` (INT) | `id_empresa`, `nombre`, `proveedor` (`bold` / `simulado`), `id_metodo_pago`, `terminal_serial`, `terminal_model` (ej. `N86`), `email_usuario`, `estado` (`Activo`/`Inactivo`), `created_at`. |
| 16 | `transacciones_pago` | `src/models/transacciones_pago.py` | `id` (INT) | `id_factura`, `id_empresa`, `id_terminal`, `id_metodo_pago`, `id_usuario`, `canal` (`datafono` / `link`), `proveedor` (`bold`, `wompi`, `simulado`), `referencia` (UNIQUE `PYM{id_fac}-{ts}-{hex}`), `id_externo`, `monto`, `monto_centavos`, `moneda` (`COP`), `estado` (`PENDIENTE`, `APROBADA`, `RECHAZADA`, `ANULADA`, `ERROR`, `EXPIRADA`), `url_pago`, `mensaje`, `payload` (JSON auditoría), `created_at`, `updated_at`. |

### 5.3 Motor de Migraciones Automáticas (`DatabaseMigrations`)
Al iniciar `PYMES_BE/src/app.py`, la clase `DatabaseMigrations` ejecuta de manera idempotente:
1. Creación de tablas faltantes (`Base.metadata.create_all`).
2. Adición de nuevas columnas (`ALTER TABLE`) si la base de datos proviene de una versión anterior.
3. **Limpieza PCI-DSS**: Anula automáticamente cualquier dato sensible heredado en columnas antiguas de tarjetas en `clientes`.
4. **Semillas Iniciales (*Seed Data*)**: Garantiza la existencia de los 3 roles base (`1: Administrador`, `2: Vendedor`, `3: Almacenista`), métodos de pago por defecto (incluyendo pasarela simulada) y terminales POS simuladas (`SIM-E1-001`) para cada empresa activa.

---

## 6. Catálogo Completo de Endpoints de la API REST (`PYMES_BE`)

| Blueprint | Endpoint | Método | Permisos / Decoradores | Descripción Funcional |
| :--- | :--- | :---: | :--- | :--- |
| **Auth** (`auth_api.py`) | `/api/auth/login` | `POST` | Público (`10/min` Rate Limit) | Autentica `username` y `password`. Retorna `access_token`, `refresh_token`, perfil y empresas activas. |
| | `/api/auth/refresh` | `POST` | `@jwt_required(refresh=True)` | Genera un nuevo `access_token` de 2 horas. |
| | `/api/auth/me` | `GET` | `@jwt_required()` | Retorna datos del usuario actual y sus empresas vinculadas. |
| | `/api/auth/cambiar-password` | `POST` | `@jwt_required()` | Actualiza contraseña validando `password_actual`. |
| | `/api/auth/recuperar-password-solicitar` | `POST` | Público | Verifica identidad combinando `username`, `documento` y `email`. |
| | `/api/auth/recuperar-password-confirmar` | `POST` | Público | Establece nueva contraseña tras verificación de identidad. |
| | `/api/auth/logout-global` | `POST` | `@jwt_required()` | Incrementa `sesion_version` invalidando todos los JWT activos del usuario. |
| **Roles** (`roles_api.py`) | `/api/roles` y `/api/roles/<id>` | `GET` | `@jwt_required()` | Lista o consulta los roles del sistema. |
| | `/api/roles` / `/api/roles/<id>` | `POST`, `PUT`, `DELETE` | `@roles_required(1)` | Gestión administrativa de roles. |
| **Usuarios** (`usuarios_api.py`) | `/api/usuarios` | `GET` | `@roles_required(1)` | Lista paginada con búsqueda (`?q=`), filtro (`?filtro=`) y enriquecimiento de rol por `empresa_id`. |
| | `/api/usuarios/check-username/<u>` | `GET` | Público | Verifica disponibilidad de nombre de usuario en tiempo real. |
| | `/api/usuarios` | `POST` | Público / `@jwt_required()` | Registro público (asigna `id_rol=2` independiente) o creación por Admin con vínculo directo a su empresa. |
| | `/api/usuarios/<id>` | `GET`, `PUT` | Admin (`1`) o Propio Usuario | Consulta o actualiza datos personales, bancarios y foto en Base64. |
| | `/api/usuarios/<id>/estado` | `PATCH`, `DELETE` | `@roles_required(1)` | Activa/Inactiva usuario globalmente. |
| **Empresas** (`empresas_api.py`) | `/api/empresas` | `GET`, `POST` | `@jwt_required()` | Lista empresas del usuario o crea una nueva empresa (vinculando al creador como `rol_id=1`). |
| | `/api/empresas/<id>` | `GET`, `PUT` | Admin de la empresa | Consulta o edita datos fiscales (`nit`, `nombre`, `direccion`, `telefono`, `email`, `estado`). |
| **Vínculos** (`usuario_empresas_api.py`) | `/api/usuario_empresas/vinculacion` | `GET`, `PUT` | Admin de la empresa | Vincula o desvincula un usuario a la empresa activa y le asigna su rol (`1`, `2` o `3`). |
| **Categorías** (`categorias_api.py`) | `/api/categorias` | `GET`, `POST`, `PUT`, `DELETE` | `GET`: Todos; Mutación: Rol `[1]` | Gestión de categorías del catálogo de productos. |
| **Productos** (`productos_api.py`) | `/api/productos` | `GET`, `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Lista paginada por empresa o crea producto con código `PROD-E{emp}-{num}` e imagen Base64. |
| | `/api/productos/siguiente_codigo` | `GET` | `@jwt_required()`, `@tenant_required` | Previsualiza el siguiente código consecutivo de producto para la empresa. |
| | `/api/productos/<id>` | `GET`, `PUT`, `PATCH`, `DELETE` | `PUT`: `[1,2,3]`; `PATCH`/`DELETE`: `[1]` | Edita producto o cambia su estado (`Activo`/`Inactivo`). |
| **Clientes** (`clientes_api.py`) | `/api/clientes` | `GET`, `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Lista clientes de la empresa o registra/actualiza cliente (*upsert* automático por documento). |
| | `/api/clientes/buscar?documento=` | `GET` | `@jwt_required()`, `@tenant_required` | Búsqueda instantánea de cliente por número de documento para el POS. |
| | `/api/clientes/<id>` | `GET`, `PUT`, `PATCH`, `DELETE` | `PUT`: `[1,2,3]`; `PATCH`/`DELETE`: `[1]` | Edita datos de cliente o cambia su estado. |
| **Proveedores** (`proveedores_api.py`) | `/api/proveedores` | `GET`, `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Lista o crea proveedor con código `PROV-E{emp}-{num}`. |
| | `/api/proveedores/<id>` | `GET`, `PUT`, `PATCH`, `DELETE` | `PUT`: `[1,2,3]`; `PATCH`/`DELETE`: `[1]` | Actualiza proveedor o cambia su estado. |
| **Facturas** (`facturas_api.py`) | `/api/facturas` | `GET`, `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Lista facturas o emite nueva factura (`FAC-E{emp}-{num}`), descontando `stock` de cada producto. |
| | `/api/facturas/<id>/cancelar` | `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Anula la factura (`Cancelada`) y reintegra automáticamente las unidades al `stock`. |
| | `/api/facturas/<id>/pagar` | `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Marca manualmente una factura `Emitida` como `Pagada`. |
| | `/api/facturas/<id>/cobros` | `GET`, `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Inicia un cobro electrónico (`canal: datafono | link`) o lista los intentos de pago de la factura. |
| **Compras** (`compras_api.py`) | `/api/compras` | `GET`, `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Lista compras o registra orden de compra (`COMP-E{emp}-{num}`), incrementando `stock` y actualizando `costo`. |
| | `/api/compras/<id>/cancelar` | `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Cancela la compra y revierte (resta) el stock ingresado. |
| **Métodos Pago** (`metodos_pago_api.py`) | `/api/metodos_pago` | `GET`, `POST`, `PUT`, `DELETE` | `GET`: Todos; Mutación: Rol `[1]` | Configura métodos de pago y credenciales de pasarelas (cifradas con Fernet). |
| **Terminales** (`terminales_api.py`) | `/api/terminales` y `/disponibles` | `GET`, `POST`, `PUT`, `DELETE` | `GET`: Todos; Mutación: Rol `[1]` | Consulta datáfonos vinculados en Bold API y administra terminales POS de la empresa. |
| **Cobros** (`cobros_api.py`) | `/api/cobros/<id>` | `GET` | `@jwt_required()`, `@tenant_required` | Consulta estado en vivo de una transacción electrónica. |
| | `/api/cobros/<id>/cancelar` | `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Anula una transacción de cobro en estado `PENDIENTE`. |
| | `/api/cobros/<id>/simular` | `POST` | Roles `[1, 2, 3]`, `@tenant_required` | Fuerza `APROBADA` o `RECHAZADA` en transacciones del proveedor `simulado`. |
| | `/api/cobros/conciliar` | `POST` | `@roles_required(1)`, `@tenant_required` | Ejecuta conciliación masiva contra Bold/Wompi, expira pendientes (`>30 min`) y sincroniza facturas. |
| **Webhooks** (`webhooks_api.py`) | `/api/webhooks/wompi` y `/bold` | `POST` | Público (Firma verificada) | Recibe notificaciones asíncronas de Wompi y Bold. |
| | `/api/webhooks/simulado/checkout` | `GET`, `POST` | Público | Portal interactivo de pago simulado (PSE, Nequi, Tarjeta, QR). |
| **Reportes** (`reportes_api.py`) | `/api/reportes/dashboard`, `/ventas`, `/clientes` | `GET` | `@roles_required(1)`, `@tenant_required` | KPIs ejecutivos, analítica de ventas por rango de fechas y mejores clientes. |
| | `/api/reportes/inventario`, `/top-productos` | `GET` | `@roles_required(1, 3)`, `@tenant_required` | Valorización de inventario, alertas de stock crítico y ranking de productos más vendidos. |

---

## 7. Seguridad de la Información

1. **Protección de Credenciales de Pasarelas (`src/utils/cifrado.py`)**:
   - Las llaves privadas (`api_key_privada`, `webhook_secret`, `integrity_secret`) en la tabla `metodos_pago` nunca se almacenan en texto plano.
   - Se cifran con **Fernet** usando la variable `PAGOS_ENC_KEY` (o una llave derivada en SHA-256 de `JWT_SECRET_KEY`) y se almacenan con el prefijo `enc:`.
   - En las respuestas JSON de la API, los secretos se devuelven enmascarados (`••••••••abcd`) a menos que el Administrador solicite explícitamente su edición.
2. **Validación Criptográfica de Webhooks**:
   - **Wompi**: Verifica el checksum SHA-256 concatenando las propiedades del evento, el `timestamp` y el `webhook_secret` (`X-Event-Checksum`).
   - **Bold**: Verifica la firma `HMAC-SHA256` del cuerpo crudo en Base64 contra la cabecera `x-bold-signature`.
3. **Protección contra Fuerza Bruta (`Flask-Limiter`)**:
   - El blueprint `/api/auth` aplica un límite estricto de **10 peticiones por minuto por IP**, devolviendo un mensaje de bloqueo temporal `HTTP 429` ante intentos repetidos.

---

## 8. Guía de Instalación, Configuración y Despliegue

### 8.1 Variables de Entorno (`.env`)

#### Backend (`PYMES_BE/.env`)
```ini
PORT=5000
FLASK_ENV=development
JWT_SECRET_KEY=pymes-jwt-secret-key-2026-secure-key-32bytes
# Opcional: Si no se define DATABASE_URL, usa automáticamente SQLite local (PYMES_BE/pymes.db)
# DATABASE_URL=mysql+pymysql://usuario:password@localhost:3306/pymes
PAGOS_ENC_KEY=  # Llave Fernet de 32 bytes base64 (opcional, deriva de JWT_SECRET_KEY si se omite)
PAGOS_MINUTOS_EXPIRACION=30
PUBLIC_BASE_URL=http://localhost:5000
```

#### Frontend Web (`PYMES_FE/.env`)
```ini
PORT=5001
SECRET_KEY=clave-secreta-sesion-frontend-web
API_BASE_URL=http://127.0.0.1:5000/api
```

### 8.2 Despliegue Rápido con Docker Compose
Desde la raíz del repositorio (`PYMES`):
```bash
docker compose up --build -d
```
- **API Backend (`pymes_backend`)**: Disponible en `http://localhost:5000/api`
- **App Web/Móvil (`pymes_movil_web` vía Nginx)**: Disponible en `http://localhost:8080`

### 8.3 Ejecución Manual en Entorno de Desarrollo Local

1. **Iniciar el Backend (`PYMES_BE` — Puerto 5000)**:
   ```powershell
   cd PYMES_BE
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   python -m src.app
   ```
2. **Iniciar el Frontend Web de Escritorio (`PYMES_FE` — Puerto 5001)**:
   ```powershell
   cd PYMES_FE
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   python -m src.app
   ```
3. **Iniciar la Aplicación Móvil / Híbrida (`pymesoft-movil` — Puerto 8100)**:
   ```powershell
   cd pymesoft-movil
   npm install
   npm start
   ```

### 8.4 Compilación y Generación del Instalador APK para Android
```powershell
cd pymesoft-movil
npm run build:apk
```
El archivo instalable queda generado en `pymesoft-movil/pymesoft.apk` (y en `android/app/build/outputs/apk/debug/app-debug.apk`).

---

## 9. Mantenimiento, Respaldo y Solución de Problemas (Troubleshooting)

| Caso / Incidencia | Causa Probable | Solución Técnica |
| :--- | :--- | :--- |
| **Error `403 Forbidden: Se requiere seleccionar una empresa activa`** | El cliente no envió la cabecera `X-Empresa-ID` o el usuario fue desvinculado de la empresa en `usuario_empresas`. | Verificar que el usuario tenga al menos un registro `Activo` en `usuario_empresas` o seleccionar una empresa en `/seleccionar-empresa`. |
| **Error `401 Unauthorized` en todas las peticiones tras cambio de seguridad** | Se ejecutó `/api/auth/logout-global`, lo que incrementó `usuarios.sesion_version`. | Iniciar sesión nuevamente para obtener un JWT con el claim `sv` actualizado. |
| **La App Android no conecta con el Backend local** | El dispositivo físico o emulador apunta a una IP distinta de la red LAN del servidor. | En Emulador Android el sistema usa automáticamente `http://10.0.2.2:5000/api`. En dispositivo físico, definir `localStorage.setItem('api_url', 'http://<IP_LAN>:5000/api')` o actualizar `environment.ts`. |
| **Facturas con cobro electrónico quedan en estado `Emitida`** | El cliente cerró la ventana de pago antes de que llegara el webhook o la transacción expiró. | Ingresar como Administrador a **Facturas → Conciliar Cobros** (`POST /api/cobros/conciliar`) para sincronizar estados con Bold/Wompi y expirar intentos mayores a 30 minutos. |
| **Respaldo de Base de Datos Local** | Mantenimiento preventivo. | En SQLite basta con realizar una copia en caliente del archivo `PYMES_BE/pymes.db`. En MySQL ejecutar `mysqldump -u <user> -p pymes > backup_pymes.sql`. |
