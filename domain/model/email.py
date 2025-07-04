from datetime import datetime
from uuid import UUID, uuid4

class Email:
    def __init__(
        self,
        message_id: str,
        subject: str,
        sent_datetime: datetime,
        is_read: bool,
        conversation_id: str,
        has_attachments: bool,
        to_addresses: list[str],
        *,
        from_address: str | None = None,
        is_bounced: bool = False,
        is_replied: bool = False,
    ):
        self.id: UUID = uuid4()
        self.to_addresses = to_addresses 
        self.message_id = message_id
        self.subject = subject
        self.sent_datetime = sent_datetime
        self.is_read = is_read
        self.conversation_id = conversation_id
        self.has_attachments = has_attachments
        self.from_address = from_address
        self.temperature_label: str | None = None     # 'quente' | 'morno' | 'frio'
        self.is_bounced = is_bounced
        self.is_replied = is_replied