import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import List

import structlog

from application.dto.email_dto import EmailDTO
from config.settings import IGNORE_SUBJECT_PREFIXES
from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from ports.graph_client import GraphClientPort

logger = structlog.get_logger(__name__).bind(service="email_metrics")

_BOUNCE_INDICATORS_RE = re.compile(
    r"undeliverable|falha na entrega|delivery has failed|não foi possível entregar|user doesn't exist|recipient address rejected",
    re.I
)
_POSTMASTER_RE = re.compile(
    r"postmaster|mailer-daemon|system administrator|microsoftexchange",
    re.I
)
PREFIXES = tuple(p.upper() for p in IGNORE_SUBJECT_PREFIXES)

def calculate_engagement_score(
    is_replied: bool, 
    is_bounced: bool, 
    reply_latency_sec: float | None
) -> int:
    """Calcula o score de engajamento, com bônus por velocidade de resposta."""
    if is_bounced:
        return -100
    
    if not is_replied:
        return 0

    score = 50
    
    if reply_latency_sec is not None:
        if reply_latency_sec < 14400:  # Menos de 4 horas
            score += 20
        elif reply_latency_sec < 43200: # Menos de 12 horas
            score += 10
        elif reply_latency_sec < 172800: # Menos de 48 horas
            score += 5
            
    return score

def score_to_label(score: int) -> str:
    if score > 0: 
        return "quente"
    if score < 0: 
        return "frio"
    return "morno"

def _is_bounce(m: Email) -> bool:
    """Verifica se um e-mail é um bounce checando assunto, remetente E corpo."""
    if _POSTMASTER_RE.search(m.from_address or ""):
        return True
    
    text_to_check = (m.subject or "") + " " + (m.body_preview or "")
    if _BOUNCE_INDICATORS_RE.search(text_to_check):
        return True
        
    return False

def _is_prefixed(subject: str | None) -> bool:
    return (subject or "").lstrip().upper().startswith(PREFIXES)

def _label(rate: float) -> str:
    return "quente" if rate >= 0.50 else ("morno" if rate >= 0.20 else "frio")

class EmailMetricsService:
    def __init__(self, graph_client: GraphClientPort) -> None:
        self.graph = graph_client

    @staticmethod
    def _to_domain(dto: EmailDTO) -> Email:
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
            from_address=dto.from_address,
            body_preview=dto.body_preview
        )

    def calculate_daily_metrics(self, sent_emails: List[Email], account: str) -> EmailMetrics:
        log = logger.new(total_raw=len(sent_emails), account=account)
        log.info("metrics.calc.start")

        if not sent_emails:
            log.warn("metrics.calc.skip_empty_list")
            return EmailMetrics(
                id=uuid.uuid4(), run_at=datetime.now(timezone.utc), date=date.today(),
                total_sent=0, total_delivered=0, total_bounced=0, total_replied=0, total_no_reply=0,
                raw_total_sent=0, raw_total_delivered=0, raw_total_bounced=0, raw_total_replied=0, raw_total_no_reply=0,
                temperature_label='frio'
            )

        conv_map: dict[str, List[Email]] = defaultdict(list)
        for mail in sent_emails:
            conv_map[mail.conversation_id].append(mail)

        bounced_convs, replied_convs = 0, 0
        raw_bounced, raw_replied = 0, 0
        reply_latencies: List[float] = []

        for conv_id, mails_in_conv in conv_map.items():
            try:
                head_dtos = self.graph.fetch_conversation_head(account, conv_id)
                head_mails = sorted([self._to_domain(dto) for dto in head_dtos], key=lambda m: m.sent_datetime)
            except Exception:
                log.exception("metrics.thread.error", conv_id=conv_id)
                continue

            first_original_mail = sorted(mails_in_conv, key=lambda m: m.sent_datetime)[0]
            
            is_bounce_thread = any(_is_bounce(m) for m in head_mails)
            first_reply_mail = None
            is_reply_thread = False

            if not is_bounce_thread:
                first_reply_mail = next((m for m in head_mails if m.from_address and m.from_address.lower() != account.lower() and not _is_prefixed(m.subject)), None)
                is_reply_thread = first_reply_mail is not None

            first_original_mail.is_bounced = is_bounce_thread
            first_original_mail.is_replied = is_reply_thread
            
            if is_bounce_thread:
                bounced_convs += 1
                raw_bounced += len(mails_in_conv)
            elif is_reply_thread:
                replied_convs += 1
                raw_replied += len(mails_in_conv)
                if first_original_mail.sent_datetime and first_reply_mail.sent_datetime:
                    latency = first_reply_mail.sent_datetime - first_original_mail.sent_datetime
                    latency_sec = latency.total_seconds()
                    if latency_sec > 0:
                        first_original_mail.reply_latency_sec = latency_sec
                        reply_latencies.append(latency_sec)

            score = calculate_engagement_score(
                is_reply_thread,
                is_bounce_thread,
                first_original_mail.reply_latency_sec 
            )
            first_original_mail.engagement_score = score
            first_original_mail.temperature_label = score_to_label(score)

            if is_bounce_thread:
                bounced_convs += 1
                raw_bounced += len(mails_in_conv)
            elif is_reply_thread:
                replied_convs += 1
                raw_replied += len(mails_in_conv)
                if first_original_mail.sent_datetime and first_reply_mail.sent_datetime:
                    latency = first_reply_mail.sent_datetime - first_original_mail.sent_datetime
                    latency_sec = latency.total_seconds()
                    if latency_sec > 0:
                        first_original_mail.reply_latency_sec = latency_sec
                        reply_latencies.append(latency_sec)

        raw_total_sent = len(sent_emails)
        raw_total_delivered = raw_total_sent - raw_bounced
        
        clean_conv_ids = {e.conversation_id for e in sent_emails if not _is_prefixed(e.subject)}
        total_sent = len(clean_conv_ids)
        total_delivered = total_sent - bounced_convs

        avg_reply_latency = sum(reply_latencies) / len(reply_latencies) if reply_latencies else None
        reply_rate_clean = replied_convs / max(total_delivered, 1)
        temperature_lbl = _label(reply_rate_clean)

        metrics = EmailMetrics(
            id=uuid.uuid4(),
            run_at=datetime.now(timezone.utc),
            date=sent_emails[0].sent_datetime.date(),
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_bounced=bounced_convs,
            total_replied=replied_convs,
            total_no_reply=total_delivered - replied_convs,
            raw_total_sent=raw_total_sent,
            raw_total_delivered=raw_total_delivered,
            raw_total_bounced=raw_bounced,
            raw_total_replied=raw_replied,
            raw_total_no_reply=raw_total_delivered - raw_replied,
            temperature_label=temperature_lbl,
            avg_reply_latency_sec=avg_reply_latency,
        )

        log.info("metrics.calc.success", **metrics.to_dict())
        return metrics