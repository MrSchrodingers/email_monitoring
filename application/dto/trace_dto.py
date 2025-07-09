
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MessageTraceDTO:
    message_id: str
    sender_address: str
    recipient_address: str
    received_datetime: datetime
    from_ip: Optional[str] 