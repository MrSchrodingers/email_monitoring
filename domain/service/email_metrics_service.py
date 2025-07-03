from __future__ import annotations

from dataclasses import asdict
import re
from datetime import date
from typing import List

import structlog
from ports.graph_client import GraphClientPort
from domain.model.email import Email
from domain.model.metrics import EmailMetrics

logger = structlog.get_logger(__name__).bind(service="email_metrics")

_BOUNCE_SUBJECT_RE = re.compile(r"(undeliverable|falha de entrega|delivery has failed)", re.I)
_POSTMASTER_RE = re.compile(r"postmaster|mailer-daemon", re.I)


class EmailMetricsService:
    """
    Deriva métricas de campanha a partir dos e-mails enviados (Sent Items)
    consultando a Graph API para detectar bounce e respostas.
    """

    def __init__(self, graph_client: GraphClientPort) -> None:
        self.graph = graph_client

    # ------------------------------------------------------------------ #
    #  API pública                                                       #
    # ------------------------------------------------------------------ #
    def calculate_daily_metrics(self, sent_emails: List[Email]) -> EmailMetrics:
        log = logger.new(total_sent=len(sent_emails))
        log.info("metrics.calc.start")

        bounced = replied = 0

        for idx, email in enumerate(sent_emails, start=1):
            conv_id = email.conversation_id
            log.debug("metrics.thread.fetch", n=idx, conversation_id=conv_id)

            try:
                thread = self.graph.fetch_conversation_head(conv_id)
            except Exception:
                log.exception("metrics.thread.error", conversation_id=conv_id)
                continue

            if any(
                _BOUNCE_SUBJECT_RE.search(m.subject or "")
                or _POSTMASTER_RE.search(m.from_address or "")
                for m in thread
            ):
                bounced += 1
                if not getattr(email, "is_bounced", False):
                    email.is_bounced = True
                log.debug("metrics.bounce.detected", conversation_id=conv_id)
                continue

            if any(m.from_address.lower() != self.graph.user.lower() for m in thread):
                replied += 1
                if not getattr(email, "is_replied", False):
                    email.is_replied = True
                log.debug("metrics.reply.detected", conversation_id=conv_id)

        delivered = len(sent_emails) - bounced
        metrics = EmailMetrics(
            date=sent_emails[0].sent_datetime.date() if sent_emails else date.today(),
            total_sent=len(sent_emails),
            total_delivered=delivered,
            total_bounced=bounced,
            total_replied=replied,
            total_no_reply=delivered - replied,
        )

        log.info(
            "metrics.calc.success",
            **asdict(metrics), 
            delivery_rate=metrics.delivery_rate,
            reply_rate=metrics.reply_rate,
        )
        return metrics
