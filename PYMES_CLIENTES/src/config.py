import os
from dotenv import load_dotenv

load_dotenv()

is_prod = (
    os.getenv("FLASK_ENV", "").lower() == "production"
    or os.getenv("APP_ENV", "").lower() == "production"
)
secret_key = os.getenv("SECRET_KEY")
if is_prod and (not secret_key or secret_key == "portal-clientes-secret"):
    raise RuntimeError("SECRET_KEY segura es obligatoria en producción para PYMES_CLIENTES.")


class Config:
    SECRET_KEY = secret_key or "portal-clientes-dev-secret-2026"
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000/api")
    DEFAULT_EMPRESA_SLUG = os.getenv("DEFAULT_EMPRESA_SLUG", "")
