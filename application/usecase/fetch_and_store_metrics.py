from __future__ import annotations
from dataclasses import asdict

import structlog
from typing import List, Optional

from ports.graph_client import GraphClientPort
from ports.persistence import EmailRepositoryPort, MetricsRepositoryPort
from domain.service.email_metrics_service import EmailMetricsService
from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from application.dto.folder_dto import FolderDTO
from application.dto.email_dto import EmailDTO
from config.settings import SENT_FOLDER_NAME, SUBJECT_FILTER, IGNORED_RECIPIENT_PATTERNS

logger = structlog.get_logger(__name__).bind(use_case="fetch_and_store_metrics")


class FetchAndStoreMetrics:
    """
    Orquestra a coleta de e-mails, filtro por assunto, persistência bruta e
    cálculo de métricas agregadas.
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
    def execute(self) -> EmailMetrics:
        log = logger.new()
        log.info("start")
        metrics: EmailMetrics | None = None
        
        try:
            folders = self.graph_client.fetch_mail_folders()
            log.info("folders.fetched", total=len(folders))

            sent_folder = self._find_sent_folder(folders)
            if not sent_folder:
                log.warning("sent_folder.not_found")
                raise RuntimeError(f'Pasta "{SENT_FOLDER_NAME}" não encontrada.')

            raw_dto = self.graph_client.fetch_messages_in_folder(sent_folder.id)
            log.info("emails.fetched", total=len(raw_dto))

            # 1️⃣  filtro por assunto (qualquer expressão da lista, case-insensitive)
            subj_filtered = [
                dto
                for dto in raw_dto
                if any(expr.lower() in (dto.subject or "").lower() for expr in SUBJECT_FILTER)
            ]
            log.info("emails.subject_filtered", total=len(subj_filtered))

            # 2️⃣  remove endereços ignorados
            def _has_ignored_recipient(dto: EmailDTO) -> bool:
                recip = " ".join(dto.to_addresses).lower()
                return any(pat in recip for pat in IGNORED_RECIPIENT_PATTERNS)

            filtered_dto = [dto for dto in subj_filtered if not _has_ignored_recipient(dto)]
            log.info("emails.recipient_filtered", total=len(filtered_dto))

            emails = [self._to_domain(dto) for dto in filtered_dto]

            # 🚀  métricas avançadas
            metrics = self.metrics_service.calculate_daily_metrics(emails)
            
            if emails:
                self.email_repo.save_all(emails)
                log.info("emails.persisted", total=len(emails))
            else:
                log.info("emails.persisted.skip", reason="no_emails_after_filter")
                
            self.metrics_repo.save(metrics)
            log.info("metrics.persisted", **asdict(metrics))

            return metrics
        
        except Exception:
            log.exception("execute.error")
            raise                                            # ou return métricas vazias

        finally:
            log.info("finish", ok=metrics is not None)
    # ------------------------------------------------------------------ #
    #  Helpers privados                                                  #
    # ------------------------------------------------------------------ #
    def _find_sent_folder(self, folders: List[FolderDTO]) -> Optional[FolderDTO]:
        """Retorna a pasta 'Itens Enviados' (case-insensitive) ou None."""
        return next(
            (
                f
                for f in folders
                if f.display_name.strip().lower() == self.SENT_FOLDER_NAME
            ),
            None,
        )

    @staticmethod
    def _to_domain(dto: EmailDTO) -> Email:
        """Converte DTO de API para entidade de domínio."""
        return Email(
            dto.id,
            dto.subject,
            dto.sent_datetime,
            dto.is_read,
            dto.conversation_id,
            dto.has_attachments,
        )
