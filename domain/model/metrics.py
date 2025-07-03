from dataclasses import dataclass
from datetime import date

from dataclasses import asdict


@dataclass(slots=True)
class EmailMetrics:
    date: date
    total_sent: int
    total_delivered: int        # enviados – bounced
    total_bounced: int          # falha de entrega
    total_replied: int          # entregues com retorno
    total_no_reply: int         # entregues sem retorno

    # ---- taxas derivadas --------------------------------------------- #
    @property
    def delivery_rate(self) -> float:          # 0–1
        return self.total_delivered / max(self.total_sent, 1)

    @property
    def reply_rate(self) -> float:             # 0–1 (entre entregues)
        return self.total_replied / max(self.total_delivered, 1)

    def to_dict(self) -> dict:
        """Dict pronto para ser passado ao structlog."""
        return asdict(self)