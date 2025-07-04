from __future__ import annotations

import structlog
import requests
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime, timezone
from typing import Generator, List

from ports.graph_client import GraphClientPort
from application.dto.folder_dto import FolderDTO
from application.dto.email_dto import EmailDTO
from config.settings import GRAPH_BASE_URL, TOKEN_PROVIDER

logger = structlog.get_logger(__name__)


class GraphApiClient(GraphClientPort):
    """
    Adaptador Microsoft Graph API.
    Todas as requisições passam por sessão com timeout + retries.
    Produz DTOs prontos para a camada de aplicação.
    """

    _TIMEOUT = (3.05, 30)  # (connect, read)

    def __init__(self) -> None:
        self.base_url = GRAPH_BASE_URL.rstrip("/")
        self.session = self._build_session()

    # --------------------------------------------------------------------- #
    #   API pública                                                         #
    # --------------------------------------------------------------------- #
    def fetch_mail_folders(self, account: str) -> List[FolderDTO]:
        log = logger.bind(user=account)
        log.info("graph.fetch_mail_folders.start")

        url = f"{self.base_url}/users/{account}/mailFolders"
        folders = [
            self._folder_from_api(item)
            for page in self._paginate(url, log)
            for item in page.get("value", [])
        ]

        log.info("graph.fetch_mail_folders.success", total=len(folders))
        return folders

    def fetch_messages_in_folder(
        self, account: str, folder_id: str, page_size: int = 50
    ) -> List[EmailDTO]:
        log = logger.bind(user=account, folder_id=folder_id, page_size=page_size)
        log.info("graph.fetch_messages.start")

        url = (
            f"{self.base_url}/users/{account}/mailFolders/{folder_id}/messages"
            f"?$orderby=sentDateTime desc&$top={page_size}"
        )

        emails = [
            self._email_from_api(item)
            for page in self._paginate(url, log)
            for item in page.get("value", [])
        ]

        log.info("graph.fetch_messages.success", emails=len(emails))
        return emails
    
    # ------------------------------------------------------------------ #
    #  Conversa completa (head)                                          #
    # ------------------------------------------------------------------ #
    def fetch_conversation_head(self, account: str, conversation_id: str, top: int = 10) -> List[EmailDTO]:
        """
        Busca até `top` mensagens de qualquer pasta que pertençam à conversa.
        Útil para detectar bounce ou reply sem varrer a mailbox inteira.
        """
        url = (
            f"{self.base_url}/users/{account}/messages?"
            f"$filter=conversationId eq '{conversation_id}'&$top={top}"
            f"&$select=subject,from,conversationId,sentDateTime,isRead,hasAttachments,toRecipients"
        )
        page = self._get(url)
        return [
            self._email_from_api(item)    
            for item in page.get("value", [])
        ]
        
    # --------------------------------------------------------------------- #
    #   Helpers privados                                                    #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry_cfg = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(401, 403, 429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        session.mount("https://", HTTPAdapter(max_retries=retry_cfg))
        return session

    def _headers(self) -> dict[str, str]:
        token = TOKEN_PROVIDER.get_token()
        return {"Authorization": f"Bearer {token}"}

    def _get(self, url: str) -> dict:
        """GET com timeout, retries e logging de erro."""
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=self._TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            logger.exception("graph.request.error", url=url)
            raise

    def _paginate(
        self, first_url: str, log
    ) -> Generator[dict, None, None]:
        """Itera sobre páginas Graph API, evitando loops de nextLink."""
        url = first_url
        page = 0
        seen: set[str] = set()

        while url:
            if url in seen:
                log.error("graph.pagination.loop_detected", url=url)
                break
            seen.add(url)

            page += 1
            log.debug("graph.pagination.page", num=page, url=url)
            data = self._get(url)
            yield data
            url = data.get("@odata.nextLink")

    # -------- converters -------------------------------------------------- #
    @staticmethod
    def _folder_from_api(item: dict) -> FolderDTO:
        return FolderDTO(
            id=item["id"],
            display_name=item["displayName"],
            unread_count=item["unreadItemCount"],
            total_count=item["totalItemCount"],
        )

    @staticmethod
    def _email_from_api(item: dict) -> EmailDTO:
        """
        Converte payload da Graph API em EmailDTO, preenchendo valores
        padrão quando algum campo não foi solicitado no $select.
        """
        to_addresses = [
            r.get("emailAddress", {}).get("address")
            for r in item.get("toRecipients", [])
        ] or []

        return EmailDTO(
            id=item["id"],
            to_addresses=to_addresses,
            subject=item.get("subject", ""),
            sent_datetime=datetime.fromisoformat(
                item["sentDateTime"].replace("Z", "+00:00")
            ).astimezone(timezone.utc),
            is_read=item.get("isRead", False),
            conversation_id=item["conversationId"],
            has_attachments=item.get("hasAttachments", False),
            from_address=item.get("from", {})
            .get("emailAddress", {})
            .get("address", ""),
        )
