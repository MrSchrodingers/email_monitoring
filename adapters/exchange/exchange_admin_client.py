from __future__ import annotations
import structlog
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from ports.exchange_admin_client import ExchangeAdminPort
from application.dto.trace_dto import MessageTraceDTO
from config.settings import TOKEN_PROVIDER

logger = structlog.get_logger(__name__)

# Namespaces do XML para facilitar a busca de elementos
XML_NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
    'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices'
}


class ExchangeAdminClient(ExchangeAdminPort):
    _BASE_URL = "https://reports.office365.com/ecp/reportingwebservice/reporting.svc"
    _API_SCOPE = "https://outlook.office365.com/.default"
    _TIMEOUT = (10, 60)

    def __init__(self) -> None:
        self.session = self._build_session()

    def trace_message_by_id(
        self,
        message_id: str,
        sender_address: str,
        sent_datetime: datetime
    ) -> Optional[MessageTraceDTO]:
        
        log = logger.bind(message_id=message_id, sender=sender_address)
        log.info("exchange_client.trace_message.start")

        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(days=10)
        end_dt = now

        start_date = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        cleaned_message_id = message_id.strip('<>')

        filter_query = (
            f"StartDate eq datetime'{start_date}' and EndDate eq datetime'{end_date}' and "
            f"MessageId eq '{cleaned_message_id}' and SenderAddress eq '{sender_address}'"
        )
        
        url = f"{self._BASE_URL}/MessageTrace?$filter={filter_query}"

        try:
            response_text = self._get_xml_text(url)
            if not response_text:
                log.warn("exchange_client.trace_message.empty_response")
                return None

            root = ET.fromstring(response_text)
            
            entry_element = root.find('atom:entry', XML_NS)
            if entry_element is None:
                log.warn("exchange_client.trace_message.not_found_no_entry")
                return None

            properties_element = entry_element.find('.//m:properties', XML_NS)
            if properties_element is None:
                log.warn("exchange_client.trace_message.not_found_no_properties")
                return None

            trace_data = {
                child.tag.replace(f"{{{XML_NS['d']}}}", ''): child.text
                for child in properties_element
            }
            
            log.info("exchange_client.trace_message.found", status=trace_data.get("Status"))
            return self._trace_from_api_properties(trace_data)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                log.warn("exchange_client.trace_message.api_error_500", url=url, reason=str(e))
            else:
                log.exception("exchange_client.trace_message.http_error", url=url)
            return None
        except ET.ParseError:
            log.exception("exchange_client.trace_message.xml_parse_error", url=url)
            return None
        except Exception:
            log.exception("exchange_client.trace_message.generic_error", url=url)
            return None

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry_cfg = Retry(
            total=2, 
            backoff_factor=0.5,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["GET"]
        )
        session.mount("https://", HTTPAdapter(max_retries=retry_cfg))
        return session
    
    def _get_xml_text(self, url: str) -> str:
        """ Executa a requisição GET e retorna o corpo da resposta como texto. """
        resp = self.session.get(url, headers=self._headers(), timeout=self._TIMEOUT)
        resp.raise_for_status()
        return resp.text

    def _headers(self) -> dict[str, str]:
        """ Cabeçalhos para a API. """
        token = TOKEN_PROVIDER.get_token(scope=self._API_SCOPE)
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _trace_from_api_properties(item: Dict) -> MessageTraceDTO:
        received_str = item.get("Received")
        if received_str:
            received_dt = datetime.fromisoformat(received_str).replace(tzinfo=timezone.utc)
        else:
            received_dt = datetime.now(timezone.utc) 

        return MessageTraceDTO(
            message_id=item.get("MessageId", ""),
            sender_address=item.get("SenderAddress", ""),
            recipient_address=item.get("RecipientAddress", ""),
            received_datetime=received_dt,
            from_ip=item.get("FromIP") 
        )