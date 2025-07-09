
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

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
    internet_message_id: Optional[str] = None
    importance: Optional[str] = None
    is_read_receipt_requested: bool = False
    from_ip: Optional[str] = None
    to_ip: Optional[str] = None
    body_preview: Optional[str] = None