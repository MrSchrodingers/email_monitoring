import os
from typing import Optional

# -- helpers ------------------------------------------------------------ #
def _split_list(value: str | None) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []

# Carrega variáveis do ambiente
TENANT_ID     = os.getenv("TENANT_ID")
CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

GRAPH_BASE_URL = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0")
EMAIL_ACCOUNT  = os.getenv("EMAIL_ACCOUNT")

# PostgreSQL
DB_HOST     = os.getenv("POSTGRES_HOST")
DB_PORT     = int(os.getenv("POSTGRES_PORT"))
DB_NAME     = os.getenv("POSTGRES_DB")
DB_USER     = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Extras 
SENT_FOLDER_NAME           = os.getenv("SENT_FOLDER_NAME", "itens enviados").lower()
SUBJECT_FILTER             = _split_list(os.getenv("SUBJECT_FILTER"))
IGNORED_RECIPIENT_PATTERNS = _split_list(os.getenv("IGNORED_RECIPIENT_PATTERNS"))

# String de conexão SQLAlchemy (ou psycopg2)
DB_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

class TokenProvider:
    _token: Optional[str] = None
    _expires_at: Optional[float] = None

    @classmethod
    def get_token(cls) -> str:
        import time
        import requests

        # Reutiliza token se ainda válido
        if cls._token and cls._expires_at and time.time() + 60 < cls._expires_at:
            return cls._token

        url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        data = {
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope":         "https://graph.microsoft.com/.default"
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        body = resp.json()
        cls._token      = body["access_token"]
        cls._expires_at = time.time() + int(body.get("expires_in", 3599))
        return cls._token

TOKEN_PROVIDER = TokenProvider
