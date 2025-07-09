from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import uuid

@dataclass
class Email:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    message_id: str = ""
    conversation_id: str = ""
    subject: str | None = None
    sent_datetime: datetime | None = None

    # --- participantes ---
    to_addresses: List[str] = field(default_factory=list)
    from_address: str | None = None

    # --- flags originais ---
    is_read: bool = False
    has_attachments: bool = False
    importance: str | None = None
    is_read_receipt_requested: bool = False

    # --- enriquecimento ---
    internet_message_id: str | None = None
    body_preview: str | None = None
    
    # --- flags e métricas derivadas ---
    is_bounced: bool = False
    is_replied: bool = False
    reply_latency_sec: float | None = None
    engagement_score: int = 0
    temperature_label: str = "frio" # 'quente' | 'morno' | 'frio'