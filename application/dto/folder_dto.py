from dataclasses import dataclass

@dataclass
class FolderDTO:
    id: str
    display_name: str
    unread_count: int
    total_count: int
