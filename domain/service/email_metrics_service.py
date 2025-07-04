from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import List

import structlog

from config.settings import IGNORE_SUBJECT_PREFIXES
from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from ports.graph_client import GraphClientPort

logger = structlog.get_logger(__name__).bind(service="email_metrics")

# ------------------  helpers de detecção  ---------------------------- #
_BOUNCE_SUBJECT_RE = re.compile(r"(undeliverable|falha de entrega|delivery has failed)", re.I)
_POSTMASTER_RE     = re.compile(r"postmaster|mailer-daemon", re.I)
PREFIXES           = tuple(p.upper() for p in IGNORE_SUBJECT_PREFIXES)


def _is_bounce(m: Email) -> bool:
    return bool(
        _BOUNCE_SUBJECT_RE.search(m.subject or "")
        or _POSTMASTER_RE.search(m.from_address or "")
    )


def _is_prefixed(subject: str | None) -> bool:
    return (subject or "").lstrip().upper().startswith(PREFIXES)


def email_label(is_replied: bool, is_bounced: bool) -> str:
    if is_bounced:
        return "frio"
    if is_replied:
        return "quente"
    return "morno"

def _label(rate: float) -> str:
    """Converte taxa de resposta limpa em rótulo de temperatura."""
    if rate >= 0.50:
        return "quente"
    if rate >= 0.20:
        return "morno"
    return "frio"


# ------------------  serviço principal  ------------------------------ #
class EmailMetricsService:
    """
    Calcula métricas diárias em dois universos:

    • **raw**  – todos os e-mails enviados (inclui RES/ENC/FW, duplicados)
    • **clean** – apenas a 1ª mensagem de cada conversa, sem prefixos

    Também classifica a “temperatura” do cliente a partir da taxa de reply.
    """

    def __init__(self, graph_client: GraphClientPort) -> None:
        self.graph = graph_client

    # ------------------------------------------------------------------ #
    def calculate_daily_metrics(self, sent_emails: List[Email], account: str) -> EmailMetrics:
        log = logger.new(total_raw=len(sent_emails))
        log.info("metrics.calc.start")

        # ---- agrupa e-mails por conversa ----------------------------- #
        conv_map: dict[str, List[Email]] = defaultdict(list)
        for mail in sent_emails:
            conv_map[mail.conversation_id].append(mail)

        raw_bounced = raw_replied = bounced = replied = 0

        for idx, (conv_id, mails) in enumerate(conv_map.items(), start=1):
            log.debug("metrics.thread.fetch", n=idx, conversation_id=conv_id)
            try:
                head = self.graph.fetch_conversation_head(account, conv_id)
            except Exception:
                log.exception("metrics.thread.error", conversation_id=conv_id)
                continue

            bounce_thread = any(_is_bounce(m) for m in head)
            reply_thread  = any(m.from_address.lower() != account.lower() for m in head)

            first_mail = mails[0]
            first_mail.is_bounced = bounce_thread
            first_mail.is_replied = reply_thread
            
            first_mail.temperature_label = email_label(
                is_replied=reply_thread,
                is_bounced=bounce_thread,
            )

            # ------ contadores cleansed (por conversa) ---------------- #
            if bounce_thread:
                bounced += 1
            elif reply_thread:
                replied += 1

            # ------ contadores raw (todos mails da conversa) ---------- #
            if bounce_thread:
                raw_bounced += len(mails)
            elif reply_thread:
                raw_replied += len(mails)

        # ------------------ totais ------------------------------------ #
        raw_total_sent       = len(sent_emails)
        raw_total_delivered  = raw_total_sent - raw_bounced

        clean_conv_ids       = {e.conversation_id for e in sent_emails if not _is_prefixed(e.subject)}
        total_sent           = len(clean_conv_ids)
        total_delivered      = total_sent - bounced

        # --------- taxas + temperatura -------------------------------- #
        reply_rate_clean = replied / max(total_delivered, 1)
        temperature_lbl  = _label(reply_rate_clean)

        # ------------------ constrói dataclass ------------------------ #
        metrics = EmailMetrics(
            id=uuid.uuid4(),
            run_at=datetime.now(timezone.utc),
            date=(sent_emails[0].sent_datetime.date() if sent_emails else date.today()),
            # clean
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_bounced=bounced,
            total_replied=replied,
            total_no_reply=total_delivered - replied,
            # raw
            raw_total_sent=raw_total_sent,
            raw_total_delivered=raw_total_delivered,
            raw_total_bounced=raw_bounced,
            raw_total_replied=raw_replied,
            raw_total_no_reply=raw_total_delivered - raw_replied,
            # temperatura
            temperature_label=temperature_lbl,
        )

        log.info("metrics.calc.success", **metrics.to_dict())
        return metrics
