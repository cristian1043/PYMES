"""Pruebas E2E mínimas de acceso del frontend web PYMES.SOFT.

Requiere que PYMES_BE y PYMES_FE estén configurados y ejecutándose localmente.
No usa credenciales válidas ni modifica registros.
"""
import os
import re
from playwright.sync_api import Page, expect

BASE_URL = os.getenv("PYMES_FE_URL", "http://127.0.0.1:5001").rstrip("/")


def test_login_page_loads(page: Page):
    response = page.goto(f"{BASE_URL}/login")
    assert response is not None, "No se recibió una respuesta del frontend"
    assert response.status == 200, f"Se esperaba HTTP 200 y llegó {response.status}"
    expect(page.locator("#identificador")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()


def test_protected_clients_route_redirects_without_session(page: Page):
    page.goto(f"{BASE_URL}/clientes/")
    expect(page).to_have_url(re.compile(r".*/login/?$"))
    expect(page.locator("#identificador")).to_be_visible()


def test_login_inputs_are_required(page: Page):
    page.goto(f"{BASE_URL}/login")
    expect(page.locator("#identificador")).to_have_attribute("required", "")
    expect(page.locator("#password")).to_have_attribute("required", "")
