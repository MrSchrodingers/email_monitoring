# domain/model/metrics.py
from dataclasses import dataclass, asdict
from datetime import datetime, date
from uuid import UUID

@dataclass(slots=True)
class EmailMetrics:
    id: UUID
    run_at: datetime
    date: date
    # ---- métricas deduplicadas / sem RES|ENC ----------
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_replied: int
    total_no_reply: int
    # ---- métricas brutas ------------------------------
    raw_total_sent: int
    raw_total_delivered: int
    raw_total_bounced: int
    raw_total_replied: int
    raw_total_no_reply: int
    temperature_label: str      # 'quente' | 'morno' | 'frio'
    
    # ---- taxas derivadas ------------------------------ #
    @property
    def delivery_rate(self) -> float:
        return self.total_delivered / max(self.total_sent, 1)

    @property
    def reply_rate(self) -> float:
        return self.total_replied / max(self.total_delivered, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(
            delivery_rate=self.delivery_rate,
            reply_rate=self.reply_rate,
        )
        return d
