@echo off
chcp 65001 >nul
echo ========================================================
echo   SUBIENDO CAMBIOS A GITHUB (PYMES_BE, PYMES_FE, MOVIL)
echo ========================================================

echo [1/4] Subiendo PYMES_BE...
cd /d "%~dp0PYMES_BE"
git add -A
git commit -m "fix: resolver id_empresa automatico y automatizacion de pagos Bold/Wompi/Simulado"
git push

echo [2/4] Subiendo PYMES_FE...
cd /d "%~dp0PYMES_FE"
git add -A
git commit -m "fix: incluir id_empresa en compras/facturas y agregar modulo de ventas y terminales"
git push

echo [3/4] Subiendo pymesoft-movil...
cd /d "%~dp0pymesoft-movil"
git add -A
git commit -m "fix: resolver id_empresa en compras y habilitar modulo de ventas y terminales"
git push

echo [4/4] Actualizando repositorio contenedor PYMES...
cd /d "%~dp0"
git add -A
git commit -m "chore: actualizar submodulos con correccion de compras, ventas y pasarelas"
git push

echo.
echo ========================================================
echo   CAMBIOS SUBIDOS EXITOSAMENTE A GITHUB / RENDER
echo ========================================================
pause
