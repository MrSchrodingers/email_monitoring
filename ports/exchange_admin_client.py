from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from application.dto.trace_dto import MessageTraceDTO

class ExchangeAdminPort(ABC):
    """
    Porta de interface para interagir com APIs administrativas do Exchange,
    como o rastreamento de mensagens.
    """

    @abstractmethod
    def trace_message_by_id(
        self,
        message_id: str,
        sender_address: str,
        sent_datetime: datetime
    ) -> Optional[MessageTraceDTO]:
        """
        Rastreia uma única mensagem usando seu Message-ID de internet,
        que é a forma mais precisa de encontrá-la.

        Args:
            message_id: O Message-ID do cabeçalho do e-mail.
            sender_address: O endereço do remetente.
            sent_datetime: A data/hora de envio para otimizar a busca.

        Returns:
            Um MessageTraceDTO com os detalhes de entrega ou None se não for encontrado.
        """
        pass