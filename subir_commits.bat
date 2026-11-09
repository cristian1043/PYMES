@echo off
chcp 65001 > nul
echo ============================================================================
echo  GUARDANDO Y SUBIENDO COMMITS EN PYMES_BE, PYMES_FE Y REPOSITORIO RAIZ PYMES
echo ============================================================================

echo.
echo [1/3] Subiendo cambios del Backend (PYMES_BE)...
cd /d "%~dp0PYMES_BE"
git add .
git commit -m "feat(backend): reingenieria multi-tenant, seguridad JWT/OTP, modulos portal de clientes, migraciones versionadas y suite pytest" -m "- Aislamiento multi-tenant estricto por id_empresa (@tenant_required y @roles_required contextual)" -m "- Separacion criptografica de identidades admin vs cliente y persistencia SHA-256 de OTP/tokens en tokens_seguridad" -m "- Nuevos modelos y API REST para Portal de Clientes (ConfiguracionPortal, Servicios, CuentasClientes, Pedidos, Reservas, SolicitudesCliente, Notificaciones)" -m "- Integracion de cobros para pedidos en CobrosService y migraciones versionadas en schema_migrations" -m "- Suite integral de pruebas automatizadas en tests/test_pymesoft_integral.py"
git push origin main

echo.
echo [2/3] Subiendo cambios del Frontend Administrativo (PYMES_FE)...
cd /d "%~dp0PYMES_FE"
git add .
git commit -m "feat(admin-fe): nuevo modulo Portal de Clientes, publicacion de catalogo y mejoras multi-empresa" -m "- Nuevo blueprint y servicio PortalAdminService (/portal_clientes) con 9 vistas administrativas" -m "- Gestion de configuracion visual, productos publicados, servicios, pedidos, agenda de reservas, clientes del portal, PQRS y notificaciones" -m "- Soporte de razon_social en empresas y campos de publicacion de portal en formularios de productos" -m "- Eliminacion de exposicion de codigo OTP en vista de recuperacion de contrasena"
git push origin main

echo.
echo [3/3] Subiendo cambios del Repositorio Principal (PYMES + PYMES_CLIENTES)...
cd /d "%~dp0"
git add PYMES_BE PYMES_FE PYMES_CLIENTES README.md DOCUMENTACION_TECNICA.md docker-compose.yml .gitignore subir_commits.bat
git commit -m "feat(pymesoft): nuevo frontend independiente PYMES_CLIENTES, actualizacion de submodulos y documentacion tecnica integral" -m "- Creacion del nuevo frontend independiente PYMES_CLIENTES (Flask + Bootstrap 5 en puerto 5002) con soporte multi-empresa por slug (/e/<slug>)" -m "- Actualizacion de referencias de submodulos PYMES_BE y PYMES_FE" -m "- Actualizacion de docker-compose.yml, README.md y creacion de DOCUMENTACION_TECNICA.md"
git push origin main

echo.
echo ============================================================================
echo  PROCESO COMPLETADO EXITOSAMENTE
echo ============================================================================
pause
