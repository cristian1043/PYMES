# DOCUMENTACIÓN TÉCNICA INTEGRAL — PYMESOFT

## 1. Arquitectura General del Sistema

**PYMESOFT** está diseñado bajo una arquitectura desacoplada de tres capas principales orientadas a múltiples empresas independientes (**Multi-Tenant**):

```mermaid
flowchart LR
    subgraph Frontends["Capas de Presentación (Desacopladas)"]
        FE["PYMES_FE (Puerto 5001)\nPanel Administrativo Empresarial"]
        CL["PYMES_CLIENTES (Puerto 5002)\nPortal Público y Área de Clientes (/e/<slug>)"]
        MV["pymesoft-movil\nApp Móvil Híbrida"]
    end

    subgraph Backend["PYMES_BE (Puerto 5000) — API REST & Lógica de Negocio"]
        MW["Middleware de Seguridad\nJWT + @tenant_required + @roles_required + @cliente_jwt_required"]
        CTRL["Controladores y Servicios\nAuth, Empresas, Facturas, Compras, PortalController, CobrosService"]
        ORM["Capa de Persistencia SQLAlchemy 2.0\nMigraciones Versionadas (schema_migrations)"]
    end

    subgraph DB["Motor de Base de Datos"]
        MYSQL[("MySQL 8.x (Producción)\nSQLite (Desarrollo / Testing)")]
    end

    FE -->|"Bearer JWT (admin) + X-Empresa-ID"| MW
    CL -->|"API Pública + Bearer JWT (cliente)"| MW
    MV -->|"Bearer JWT (admin) + X-Empresa-ID"| MW
    MW --> CTRL --> ORM --> MYSQL
```

---

## 2. Arquitectura Multiempresa (Multi-Tenant) y Control de Acceso

1. **Aislamiento por `id_empresa`**:
   - Todas las entidades operativas (`clientes`, `categorias`, `productos`, `proveedores`, `facturas`, `compras`, `movimientos_inventario`, `metodos_pago`, `terminales`, `transacciones_pago`, `pagos_membresia`, `configuracion_portal`, `servicios`, `pedidos`, `reservas`, `notificaciones`, `solicitudes_cliente`) están vinculadas mediante clave foránea a `empresas.id`.
   - El decorador `@tenant_required` en `PYMES_BE/src/utils/security.py` resuelve la empresa activa y verifica en base de datos (`usuario_empresas`) que el usuario autenticado tenga una vinculación `Activo` con dicha empresa antes de ejecutar cualquier controlador.
   - Todo acceso a un recurso por ID (`GET/PUT/DELETE /api/<recurso>/<id>`) verifica que `recurso.id_empresa == empresa_activa_id`. Si pertenece a otra empresa, responde `404` o `403`.
2. **Autorización Contextual por Empresa (`RBAC + ABAC`)**:
   - Un usuario puede pertenecer a múltiples empresas con roles distintos a través de `usuario_empresas` (`rol_id`: `1 = Administrador`, `2 = Vendedor`, `3 = Almacenista`).
   - El rol global de la tabla `usuarios` no otorga permisos sobre empresas ajenas. Únicamente la bandera explícita `usuarios.es_super_admin = 1` identifica a un operador global de plataforma.
   - El decorador `@roles_required` consulta el rol efectivo del usuario **en la empresa activa** (`obtener_rol_en_empresa`), impidiendo escaladas de privilegios cuando un usuario es Administrador en la Empresa A pero Vendedor en la Empresa B.
3. **Separación Criptográfica de Identidades (`admin` vs `cliente`)**:
   - Los usuarios internos (`usuarios`) reciben tokens JWT con el claim `"identity_type": "admin"`.
   - Los clientes externos del portal (`cuentas_clientes`) reciben tokens JWT con el claim `"identity_type": "cliente"`.
   - `@tenant_required` y `@roles_required` rechazan con `403` cualquier token con `identity_type == "cliente"`.
   - `@cliente_jwt_required` rechaza con `403` cualquier token administrativo en las rutas privadas de clientes (`/api/portal/cliente/...`).

---

## 3. Diagrama Entidad-Relación (ER)

```mermaid
erDiagram
    EMPRESAS ||--o{ USUARIO_EMPRESAS : "vincula empleados"
    USUARIOS ||--o{ USUARIO_EMPRESAS : "pertenece con rol"
    ROLES ||--o{ USUARIO_EMPRESAS : "define permisos"

    EMPRESAS ||--o| CONFIGURACION_PORTAL : "personaliza portal"
    EMPRESAS ||--o{ CATEGORIAS : "clasifica"
    EMPRESAS ||--o{ PROVEEDORES : "abastece"
    EMPRESAS ||--o{ PRODUCTOS : "inventario"
    EMPRESAS ||--o{ SERVICIOS : "catálogo servicios"
    EMPRESAS ||--o{ CLIENTES : "directorio comercial"

    CUENTAS_CLIENTES ||--o{ DIRECCIONES_CLIENTES : "libreta direcciones"
    CUENTAS_CLIENTES ||--o{ VINCULACIONES_CLIENTES : "vincula por empresa"
    EMPRESAS ||--o{ VINCULACIONES_CLIENTES : "verifica titularidad"
    CLIENTES ||--o{ VINCULACIONES_CLIENTES : "ficha comercial"

    EMPRESAS ||--o{ PEDIDOS : "recibe"
    CUENTAS_CLIENTES ||--o{ PEDIDOS : "realiza"
    CLIENTES ||--o{ PEDIDOS : "asocia"
    PEDIDOS ||--|{ DETALLE_PEDIDOS : "contiene snapshot"
    PEDIDOS ||--|{ HISTORIAL_PEDIDOS : "audita estados"
    PEDIDOS ||--o| FACTURAS : "genera opcionalmente"

    EMPRESAS ||--o{ RESERVAS : "agenda"
    SERVICIOS ||--o{ RESERVAS : "programa"
    CUENTAS_CLIENTES ||--o{ RESERVAS : "solicita"

    EMPRESAS ||--o{ FACTURAS : "emite"
    FACTURAS ||--|{ DETALLE_FACTURAS : "detalla"
    FACTURAS ||--o{ TRANSACCIONES_PAGO : "cobra"
    PEDIDOS ||--o{ TRANSACCIONES_PAGO : "cobra online"

    EMPRESAS ||--o{ SOLICITUDES_CLIENTE : "atiende PQRS"
    EMPRESAS ||--o{ NOTIFICACIONES : "alerta"
```

---

## 4. Diccionario de Datos de Nuevas Entidades y Tablas Fortalecidas

| Tabla | Propósito | Columnas Clave |
| :--- | :--- | :--- |
| `schema_migrations` | Control versionado e idempotente de migraciones aplicadas | `version` (PK), `description`, `applied_at` |
| `tokens_seguridad` | Almacenamiento persistente con hash SHA-256 de códigos OTP y tokens (recuperación de clave, eliminación 2FA, vinculación de clientes) | `id`, `tipo`, `identidad_tipo`, `identidad_id`, `id_empresa`, `codigo_hash`, `token_hash`, `intentos`, `max_intentos`, `usado`, `expires_at` |
| `configuracion_portal` | Configuración multi-tenant del Portal de Clientes por empresa | `id`, `id_empresa` (UNIQUE), `slug` (UNIQUE), `activo`, `nombre_publico`, `eslogan`, `descripcion`, `logo_url`, `portada_url`, `color_primario`, `color_secundario`, `telefono_contacto`, `email_contacto`, `whatsapp`, `horario_atencion`, `redes_sociales`, `mostrar_catalogo`, `mostrar_precios`, `permitir_pedidos`, `mostrar_servicios`, `permitir_reservas`, `modalidades_entrega`, `costo_envio_base`, `condiciones_servicio` |
| `servicios` | Catálogo de servicios publicados y agendables por empresa | `id`, `id_empresa`, `codigo`, `nombre`, `descripcion`, `categoria`, `precio`, `duracion_minutos`, `estado`, `publicado`, `disponible`, `requiere_reserva` |
| `cuentas_clientes` | Cuentas autenticadas de clientes externos (separadas de `usuarios`) | `id`, `tipo_documento`, `documento`, `nombre`, `apellido`, `email` (UNIQUE), `telefono`, `direccion_principal`, `ciudad`, `password_hash`, `estado`, `sesion_version` |
| `direcciones_clientes` | Libreta de direcciones de entrega de cada cuenta de cliente | `id`, `id_cuenta_cliente`, `alias`, `direccion`, `ciudad`, `departamento`, `referencia`, `telefono_contacto`, `es_principal` |
| `vinculaciones_clientes` | Relación verificada entre una `CuentaCliente` y su ficha comercial `Clientes` en cada empresa | `id`, `id_cuenta_cliente`, `id_empresa`, `id_cliente`, `estado_verificacion` (`Pendiente`, `Verificado`, `Rechazado`), `metodo_verificacion`, `verified_at` |
| `pedidos` | Pedidos realizados en el Portal de Clientes (separados de `facturas`) | `id`, `numero`, `id_empresa`, `id_cuenta_cliente`, `id_cliente`, `estado`, `modalidad_entrega`, `direccion_entrega`, `ciudad_entrega`, `subtotal`, `iva`, `descuento`, `costo_envio`, `total`, `id_metodo_pago`, `estado_pago`, `id_factura`, `inventario_descontado` |
| `detalle_pedidos` | Instantánea histórica de productos y precios al momento del pedido | `id`, `id_pedido`, `id_producto`, `codigo_producto`, `nombre_producto`, `cantidad`, `precio_unitario`, `subtotal` |
| `historial_pedidos` | Bitácora de auditoría de transiciones de estado del pedido | `id`, `id_pedido`, `estado_anterior`, `estado_nuevo`, `comentario`, `actor_tipo`, `actor_id`, `created_at` |
| `reservas` | Citas y reservas de servicios con control anti-solapamiento horario | `id`, `numero`, `id_empresa`, `id_servicio`, `id_cuenta_cliente`, `id_cliente`, `fecha_reserva`, `hora_inicio`, `hora_fin`, `profesional`, `estado`, `notas_cliente`, `notas_empresa` |
| `solicitudes_cliente` | Consultas, reclamos, sugerencias y soporte (PQRS) por empresa | `id`, `radicado`, `id_empresa`, `id_cuenta_cliente`, `id_pedido`, `id_reserva`, `tipo`, `asunto`, `mensaje`, `estado`, `respuesta`, `respondido_por` |
| `notificaciones` | Alertas internas para la empresa (`destinatario_tipo='empresa'`) y para el cliente (`destinatario_tipo='cliente'`) | `id`, `id_empresa`, `id_cuenta_cliente`, `destinatario_tipo`, `tipo`, `titulo`, `mensaje`, `referencia_id`, `leida` |

---

## 5. Catálogo de Endpoints del Backend (`PYMES_BE`)

### 5.1. Autenticación y Administración Interna (`/api/...`)
- `POST /api/auth/login` — Inicio de sesión administrativo (`identity_type="admin"`).
- `POST /api/auth/refresh` — Renovación de `access_token` verificando `token_version`.
- `POST /api/auth/logout-global` — Revocación inmediata de todas las sesiones del usuario.
- `POST /api/auth/cambiar-password` — Cambio de contraseña validando política de complejidad.
- `POST /api/auth/recuperar-password-solicitar` — Solicitud de recuperación con respuesta genérica anti-enumeración y envío de OTP por correo (sin exponer el código en HTTP).
- `POST /api/auth/recuperar-password-confirmar` — Confirmación de código OTP o token persistido en `tokens_seguridad`.
- `GET/POST/PUT /api/empresas/`, `/api/usuarios/`, `/api/usuario_empresas/`, `/api/categorias/`, `/api/productos/`, `/api/proveedores/`, `/api/clientes/`, `/api/facturas/`, `/api/compras/`, `/api/terminales/`, `/api/metodos_pago/`, `/api/cobros/`, `/api/membresias/`, `/api/reportes/` — Protegidos por `@jwt_required()`, `@tenant_required()` y `@roles_required(...)`.

### 5.2. Administración del Portal de Clientes (`/api/portal/admin/...`)
- `GET /api/portal/admin/resumen` — Métricas e indicadores del portal de la empresa activa.
- `GET/PUT /api/portal/admin/configuracion` — Configuración general, visual, redes sociales, horarios y módulos del portal.
- `GET /api/portal/admin/productos` y `PUT /api/portal/admin/productos/<id>/portal` — Publicación, precio público y destacado de productos.
- `GET/POST/PUT/DELETE /api/portal/admin/servicios` — CRUD de servicios publicados por la empresa.
- `GET /api/portal/admin/pedidos`, `GET /api/portal/admin/pedidos/<id>`, `PUT /api/portal/admin/pedidos/<id>/estado` — Gestión de pedidos, reverso automático de stock al cancelar y emisión controlada de factura comercial.
- `GET /api/portal/admin/reservas` y `PUT /api/portal/admin/reservas/<id>` — Agenda y gestión de reservas de servicios.
- `GET /api/portal/admin/clientes` y `PUT /api/portal/admin/clientes/<vinc_id>/verificar` — Clientes registrados desde el portal y verificación comercial.
- `GET /api/portal/admin/solicitudes` y `PUT /api/portal/admin/solicitudes/<id>` — Gestión y respuesta de PQRS.
- `GET /api/portal/admin/notificaciones` y `POST /api/portal/admin/notificaciones/leer` — Centro de alertas de la empresa.

### 5.3. Portal Público por Empresa (`/api/portal/publico/...`)
- `GET /api/portal/publico/empresas` — Directorio de empresas activas con portal habilitado.
- `GET /api/portal/publico/<slug_o_id>` — Presentación pública, configuración visual, destacados y métodos de pago.
- `GET /api/portal/publico/<slug_o_id>/productos` y `GET /api/portal/publico/<slug_o_id>/productos/<id>` — Catálogo público (omite estrictamente `costo`, `id_proveedor` y `proveedor_nombre`).
- `GET /api/portal/publico/<slug_o_id>/servicios` y `GET /api/portal/publico/<slug_o_id>/servicios/<id>/horarios` — Servicios publicados y disponibilidad de horarios por fecha.
- `POST /api/portal/publico/<slug_o_id>/carrito/validar` — Validación en servidor de stock, precios, pertenencia a la empresa y costos de entrega.
- `POST /api/portal/publico/<slug_o_id>/contacto` — Registro público de consultas o solicitudes PQRS.

### 5.4. Área Privada del Cliente Externo (`/api/portal/cliente/...`)
- `POST /api/portal/cliente/auth/register`, `POST /api/portal/cliente/auth/login`, `POST /api/portal/cliente/auth/recuperar-solicitar`, `POST /api/portal/cliente/auth/recuperar-confirmar`, `POST /api/portal/cliente/auth/logout-global`.
- `GET/PUT /api/portal/cliente/perfil`, `POST /api/portal/cliente/cambiar-password`, `GET/POST/DELETE /api/portal/cliente/direcciones`.
- `POST /api/portal/cliente/<slug>/vincular-solicitar` y `POST /api/portal/cliente/<slug>/vincular-confirmar` — Verificación OTP para consultar facturas históricas.
- `GET/POST /api/portal/cliente/<slug>/pedidos`, `GET /api/portal/cliente/<slug>/pedidos/<id>`, `POST /api/portal/cliente/<slug>/pedidos/<id>/cancelar`.
- `POST /api/portal/cliente/<slug>/pedidos/<id>/cobros` y `POST /api/portal/cliente/<slug>/pedidos/<id>/cobros/<cobro_id>/simular` — Pago en línea y simulador Sandbox para pedidos.
- `GET/POST /api/portal/cliente/<slug>/reservas` y `POST /api/portal/cliente/<slug>/reservas/<id>/cancelar`.
- `GET /api/portal/cliente/<slug>/facturas`, `GET/POST /api/portal/cliente/<slug>/solicitudes`, `GET/POST /api/portal/cliente/<slug>/notificaciones`.

---

## 6. Variables de Entorno Requeridas

### `PYMES_BE/.env`
| Variable | Obligatoria en Prod | Descripción |
| :--- | :---: | :--- |
| `FLASK_ENV` | Sí (`production`) | Entorno de ejecución (`development`, `testing`, `production`). En `production` activa validaciones fail-safe de secretos y BD. |
| `DATABASE_URL` | Sí | Cadena de conexión SQLAlchemy (`mysql+pymysql://user:pass@host:3306/pymes` en producción). |
| `JWT_SECRET_KEY` | Sí | Clave secreta de al menos 32 bytes para firmar tokens JWT. |
| `PAGOS_ENC_KEY` | Sí | Clave maestra para el cifrado Fernet (`AES-128-CBC + HMAC-SHA256`) de credenciales de pasarelas de pago. |
| `CORS_ORIGINS` | Recomendado | Orígenes permitidos separados por coma (`http://localhost:5001,http://localhost:5002`). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` | Opcional | Credenciales SMTP para envío de códigos OTP y notificaciones por correo. |

### `PYMES_FE/.env` y `PYMES_CLIENTES/.env`
| Variable | Componente | Descripción |
| :--- | :---: | :--- |
| `SECRET_KEY` | Ambos | Clave secreta para firmar las cookies de sesión de Flask (obligatoria en producción). |
| `API_BASE_URL` | Ambos | URL base de la API de `PYMES_BE` (`http://127.0.0.1:5000/api`). |
| `PORTAL_CLIENTES_URL` | `PYMES_FE` | URL pública de `PYMES_CLIENTES` (`http://127.0.0.1:5002`). |
| `DEFAULT_EMPRESA_SLUG` | `PYMES_CLIENTES` | Opcional: si se define, redirige la raíz `/` directamente al portal de esa empresa. |

---

## 7. Migraciones Controladas y Semillas de Demostración

- **Migraciones No Destructivas (`PYMES_BE/src/utils/migrations.py`)**:
  - Al iniciar `PYMES_BE`, `ejecutar_migraciones()` inspecciona la estructura real de la base de datos con `sqlalchemy.inspect(engine)` y registra cada versión aplicada en la tabla `schema_migrations` (`20260401_01_core_multitenant_columns`, `20260401_02_portal_and_security_tables`, `20260401_03_proveedores_multitenant_index`, `20260401_04_portal_configs_initial`).
  - Nunca elimina tablas ni trunca registros existentes.
- **Auditoría de Integridad (`auditar_calidad_datos()`)**:
  - Permite diagnosticar registros huérfanos sin `id_empresa` o productos con stock negativo sin alterar datos productivos.
- **Semillas de Desarrollo (`PYMES_BE/scripts/seed_demo.py`)**:
  - La creación de datos de demostración está completamente separada del flujo normal de consultas y se ejecuta únicamente bajo demanda mediante `python scripts/seed_demo.py`.
