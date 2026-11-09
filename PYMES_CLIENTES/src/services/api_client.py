import requests
from flask import current_app, session, flash


class PortalAPIClient:
    """
    Cliente HTTP para PYMES_CLIENTES.
    Consume exclusivamente los endpoints públicos (/api/portal/publico/...) y
    de clientes externos (/api/portal/cliente/...) de PYMES_BE.
    """

    @classmethod
    def _base_url(cls):
        return current_app.config.get("API_BASE_URL", "http://127.0.0.1:5000/api").rstrip("/")

    @classmethod
    def _headers(cls):
        headers = {}
        token = session.get("cliente_access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @classmethod
    def _parse_error(cls, response, exc):
        try:
            if response is not None:
                data = response.json()
                if isinstance(data, dict):
                    return data.get("mensaje") or data.get("msg") or data.get("error") or str(exc)
        except Exception:
            pass
        return str(exc)

    @classmethod
    def get(cls, endpoint, params=None):
        url = f"{cls._base_url()}{endpoint}"
        try:
            res = requests.get(url, params=params, headers=cls._headers(), timeout=6)
            if res.status_code == 401 and session.get("cliente_access_token"):
                session.pop("cliente_access_token", None)
                session.pop("cliente_cuenta", None)
                flash("Tu sesión de cliente ha expirado. Inicia sesión nuevamente.", "warning")
            res.raise_for_status()
            return res.json(), None
        except requests.exceptions.RequestException as exc:
            return None, cls._parse_error(getattr(exc, "response", None), exc)

    @classmethod
    def post(cls, endpoint, data=None):
        url = f"{cls._base_url()}{endpoint}"
        try:
            res = requests.post(url, json=data or {}, headers=cls._headers(), timeout=6)
            res.raise_for_status()
            return res.json(), None
        except requests.exceptions.RequestException as exc:
            return None, cls._parse_error(getattr(exc, "response", None), exc)

    @classmethod
    def put(cls, endpoint, data=None):
        url = f"{cls._base_url()}{endpoint}"
        try:
            res = requests.put(url, json=data or {}, headers=cls._headers(), timeout=6)
            res.raise_for_status()
            return res.json(), None
        except requests.exceptions.RequestException as exc:
            return None, cls._parse_error(getattr(exc, "response", None), exc)

    @classmethod
    def delete(cls, endpoint):
        url = f"{cls._base_url()}{endpoint}"
        try:
            res = requests.delete(url, headers=cls._headers(), timeout=6)
            res.raise_for_status()
            return res.json(), None
        except requests.exceptions.RequestException as exc:
            return None, cls._parse_error(getattr(exc, "response", None), exc)
