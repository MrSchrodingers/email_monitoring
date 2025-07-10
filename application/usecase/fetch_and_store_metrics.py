from __future__ import annotations

import structlog
from typing import List, Optional

from application.dto.email_dto import EmailDTO
from application.dto.folder_dto import FolderDTO
from config.settings import (
    EMAIL_ACCOUNTS,
    IGNORED_RECIPIENT_PATTERNS,
    SENT_FOLDER_NAME,
    SUBJECT_FILTER,
)
from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from domain.service.email_metrics_service import EmailMetricsService
from ports.graph_client import GraphClientPort
from ports.persistence import EmailRepositoryPort, MetricsRepositoryPort

logger = structlog.get_logger(__name__).bind(use_case="fetch_and_store_metrics")


class FetchAndStoreMetrics:
    """
    Executa coleta + persistência para todas as contas listadas
    em `EMAIL_ACCOUNTS`.
    """

    def __init__(
        self,
        graph_client: GraphClientPort,
        email_repo: EmailRepositoryPort,
        metrics_repo: MetricsRepositoryPort,
        metrics_service: EmailMetricsService,
    ) -> None:
        self.graph_client = graph_client
        self.email_repo = email_repo
        self.metrics_repo = metrics_repo
        self.metrics_service = metrics_service

    # ------------------------------------------------------------------ #
    #  API pública                                                       #
    # ------------------------------------------------------------------ #
    def execute(self) -> List[EmailMetrics]:
        all_metrics: list[EmailMetrics] = []

        for account in EMAIL_ACCOUNTS:
            log = logger.new(account=account)
            log.info("start")

            try:
                # 1️⃣  Pasta “Itens Enviados”
                folders = self.graph_client.fetch_mail_folders(account)
                sent_folder = self._find_sent_folder(folders)
                if not sent_folder:
                    log.warning("sent_folder.not_found")
                    continue

                # 2️⃣  Mensagens enviadas
                raw_dto = self.graph_client.fetch_messages_in_folder(
                    account, sent_folder.id
                )

                subj_filtered = [
                    d
                    for d in raw_dto
                    if any(expr.lower() in (d.subject or "").lower() for expr in SUBJECT_FILTER)
                ]
                
                test_pattern = "oportunidade de acordo: - parte:"
                prod_dto = [
                    d for d in subj_filtered
                    if test_pattern not in (d.subject or "").lower()
                ]

                def _ignored(dto: EmailDTO) -> bool:
                    recip = " ".join(dto.to_addresses).lower()
                    return any(p in recip for p in IGNORED_RECIPIENT_PATTERNS)

                filtered_dto = [d for d in prod_dto if not _ignored(d)]
                emails = [self._to_domain(dto) for dto in filtered_dto]

                # 3️⃣  Métricas (também marca flags nos objetos)
                metrics = self.metrics_service.calculate_daily_metrics(emails, account)

                # 4️⃣  UPSERT e-mails
                if emails:
                    self.email_repo.save_all(account, emails)
                    log.info("emails.persisted", total=len(emails))

                # 5️⃣  INSERT métricas
                self.metrics_repo.save(metrics, account)
                log.info("metrics.persisted", **metrics.to_dict())

                all_metrics.append(metrics)

            except Exception:
                log.exception("execute.error")

            finally:
                log.info("finish")

        return all_metrics

    # ------------------------------------------------------------------ #
    #  Helpers                                                           #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_sent_folder(folders: List[FolderDTO]) -> Optional[FolderDTO]:
        return next(
            (f for f in folders if f.display_name.strip().lower() == SENT_FOLDER_NAME),
            None,
        )

    @staticmethod
    def _to_domain(dto: EmailDTO) -> Email:
        """ Mapeia o internet_message_id para o objeto de domínio. """
        return Email(
            message_id=dto.id, 
            internet_message_id=dto.internet_message_id, 
            subject=dto.subject,
            sent_datetime=dto.sent_datetime,
            is_read=dto.is_read,
            conversation_id=dto.conversation_id,
            has_attachments=dto.has_attachments,
            to_addresses=dto.to_addresses,
            importance=dto.importance,
            is_read_receipt_requested=dto.is_read_receipt_requested,
        )
