from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class EmailDTO:
    id: str
    subject: str
    sent_datetime: datetime
    is_read: bool
    conversation_id: str
    has_attachments: bool
    from_address: str
    to_addresses: List[str]
