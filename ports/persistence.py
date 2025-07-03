from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from typing import List

class EmailRepositoryPort:
    def save_all(self, emails: List[Email]) -> None:
        """Persistir lista de e-mails."""
        raise NotImplementedError

class MetricsRepositoryPort:
    def save(self, metrics: EmailMetrics) -> None:
        """Persistir métricas diárias."""
        raise NotImplementedError
