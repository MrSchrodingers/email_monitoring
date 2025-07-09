import os
import time
from typing import Optional, Dict

import requests

# --- Configurações ---
def _split_list(value: str | None) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GRAPH_BASE_URL = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0")
EMAIL_ACCOUNTS: list[str] = _split_list(os.getenv("EMAIL_ACCOUNTS"))
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = int(os.getenv("POSTGRES_PORT"))
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
SENT_FOLDER_NAME = os.getenv("SENT_FOLDER_NAME", "itens enviados").lower()
SUBJECT_FILTER = _split_list(os.getenv("SUBJECT_FILTER"))
IGNORED_RECIPIENT_PATTERNS = _split_list(os.getenv("IGNORED_RECIPIENT_PATTERNS"))
IGNORE_SUBJECT_PREFIXES = ["RES:", "ENC:", "FW:", "FWD:"]
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
MAX_MIME_WORKERS=10
MIME_TIMEOUT_SEC=30

class TokenProvider:
    """
    Um provedor de tokens que armazena em cache e pode obter tokens para diferentes APIs (escopos).
    """
    _token_cache: Dict[str, Dict] = {}
    
    # Escopo padrão para a API principal do Microsoft Graph
    DEFAULT_SCOPE = "https://graph.microsoft.com/.default"

    def get_token(self, scope: Optional[str] = None) -> str:
        """
        Obtém um token de acesso para o escopo especificado.
        Se nenhum escopo for fornecido, usa o padrão do Graph.
        """
        target_scope = scope or self.DEFAULT_SCOPE
        
        # Verifica se já existe um token válido no cache para este escopo
        if target_scope in self._token_cache:
            cached_token = self._token_cache[target_scope]
            if time.time() < cached_token.get("expires_at", 0):
                return cached_token["access_token"]

        # Se não houver token em cache, adquire um novo
        url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": target_scope
        }
        
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        token_data = resp.json()

        # Calcula o tempo de expiração com uma margem de 60 segundos
        expires_at = time.time() + int(token_data.get("expires_in", 3599)) - 60
        
        # Armazena o novo token e o seu tempo de expiração no cache
        self._token_cache[target_scope] = {
            "access_token": token_data["access_token"],
            "expires_at": expires_at
        }
        
        return token_data["access_token"]

TOKEN_PROVIDER = TokenProvider()