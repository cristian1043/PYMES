# PYMESOFT — Ecosistema Empresarial Multiempresa (Multi-Tenant)

Sistema integral de gestión empresarial, facturación, inventario Kardex, pasarelas de pago y portal web de clientes para múltiples empresas independientes con aislamiento estricto de datos.

```text
PYMES/
├── PYMES_BE/          -> Backend y API REST Multiempresa (Python 3, Flask, SQLAlchemy 2, MySQL/SQLite, JWT, Fernet — Puerto 5000)
├── PYMES_FE/          -> Frontend Administrativo Empresarial (Python Flask, Jinja2, Bootstrap 4, APIClient — Puerto 5001)
├── PYMES_CLIENTES/    -> Nuevo Frontend Portal de Clientes Externos (Python Flask, Jinja2, Bootstrap 5 — Puerto 5002)
├── pymesoft-movil/    -> Aplicación Móvil Híbrida (Ionic 8, Angular 20, Capacitor 8)
└── DOCUMENTACION_TECNICA.md -> Documentación arquitectónica, ER, diccionario de datos, seguridad y despliegue
```

---

## 📂 Componentes del Ecosistema

| Componente | Puerto | Tecnologías | Propósito y Responsabilidades |
| :--- | :---: | :--- | :--- |
| **`PYMES_BE`** | `5000` | Python 3.11+, Flask 3, SQLAlchemy 2, Flask-JWT-Extended, Flask-Limiter, PyMySQL / SQLite, Cryptography (Fernet) | API RESTful multi-tenant con aislamiento estricto por `id_empresa` (`@tenant_required`), RBAC contextual por empresa (`@roles_required`), separación criptográfica de identidades (`admin` vs `cliente`), migraciones versionadas (`schema_migrations`), pasarelas de pago (Bold POS, Wompi, Sandbox) y módulos completos del Portal de Clientes |
| **`PYMES_FE`** | `5001` | Python 3.11+, Flask 3, Jinja2, Requests, Bootstrap 4, Gunicorn | Panel administrativo interno para dueños, administradores, vendedores y almacenistas de cada empresa. Incluye ventas/facturación, compras, inventario, proveedores, terminales POS, membresía empresarial (\$19.900 COP/mes) y la sección **🌐 Portal de Clientes** |
| **`PYMES_CLIENTES`** | `5002` | Python 3.11+, Flask 3, Jinja2, Requests, Bootstrap 5, Gunicorn | Portal web público y área privada para los clientes externos de cada empresa (`/e/<slug>`). Incluye catálogo de productos y servicios, carrito validado en servidor, checkout, agendamiento de citas, seguimiento/pago de pedidos, consulta de facturas verificadas por OTP y PQRS |
| **`pymesoft-movil`** | `8080` | Ionic 8, Angular 20, TypeScript, Capacitor 8 | Cliente móvil complementario para operación en campo |

---

## 🚀 Ejecución Rápida en Entorno Local

### 1. Backend (`PYMES_BE` — Puerto `5000`)
```bash
cd PYMES_BE
pip install -r requirements.txt
# Opcional: poblar datos de demostración en entorno de desarrollo
python scripts/seed_demo.py
# Iniciar servidor API
python -m src.app
```

### 2. Frontend Administrativo (`PYMES_FE` — Puerto `5001`)
```bash
cd PYMES_FE
pip install -r requirements.txt
python -m src.app
```

### 3. Portal Web de Clientes (`PYMES_CLIENTES` — Puerto `5002`)
```bash
cd PYMES_CLIENTES
pip install -r requirements.txt
python -m src.app
```

---

## 🧪 Ejecución de Pruebas Automatizadas

La suite integral de pruebas verifica aislamiento multiempresa (pruebas negativas cross-tenant), separación de identidades (`admin` vs `cliente`), seguridad de recuperación de contraseñas sin fuga de OTP, privacidad del catálogo público, carrito/pedidos con descuento y reverso transaccional de stock, agendamiento anti-doble-reserva y simulación de pagos:

```bash
cd PYMES_BE
pytest tests/test_pymesoft_integral.py -v
```

---

## 📖 Documentación Técnica Detallada

Consulta el archivo [`DOCUMENTACION_TECNICA.md`](./DOCUMENTACION_TECNICA.md) para revisar:
- Arquitectura general y modelo de aislamiento Multi-Tenant.
- Diagrama Entidad-Relación (Mermaid) y diccionario de datos completo.
- Catálogo de endpoints REST (`PYMES_BE`) y rutas de `PYMES_FE` y `PYMES_CLIENTES`.
- Controles de ciberseguridad implementados y guía de despliegue en producción.
