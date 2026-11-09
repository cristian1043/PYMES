# PYMES_CLIENTES — Portal Web Multiempresa para Clientes Externos

Frontend independiente del ecosistema **PYMESOFT** orientado exclusivamente a los clientes finales de cada empresa registrada.

## Características Principales
- **Arquitectura Multi-Tenant por Slug (`/e/<empresa_slug>`)**: Cada empresa dispone de su propio portal personalizado (colores corporativos, logo, banner, historia, redes sociales, horarios y políticas).
- **Desacoplamiento Estricto**: Consume únicamente los endpoints públicos (`/api/portal/publico/...`) y de clientes autenticados (`/api/portal/cliente/...`) de `PYMES_BE`. No contiene vistas administrativas ni expone costos o proveedores.
- **Catálogo Comercial y Carrito Validado en Servidor**: Búsqueda, filtros por categoría/precio, validación de stock e importes en el backend antes del checkout.
- **Agendamiento de Servicios**: Reserva de citas con verificación de disponibilidad horaria.
- **Área Privada del Cliente (`Mi Cuenta`)**:
  - Gestión de perfil y libreta de direcciones.
  - Seguimiento de pedidos en tiempo real, pago online / simulador Sandbox y cancelación de pedidos pendientes.
  - Gestión de citas/reservas.
  - Vinculación verificada mediante OTP con el registro comercial de la empresa para consultar facturas emitidas.
  - Centro de notificaciones y envío/seguimiento de consultas, reclamos o solicitudes (PQRS).

## Ejecución Local
```bash
pip install -r requirements.txt
python -m src.app
```
El portal se ejecuta por defecto en `http://127.0.0.1:5002`.
