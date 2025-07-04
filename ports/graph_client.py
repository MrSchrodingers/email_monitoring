from typing import List
from application.dto.email_dto import EmailDTO
from application.dto.folder_dto import FolderDTO

class GraphClientPort:
    def fetch_mail_folders(self, account: str) -> List[FolderDTO]:
        """Lista todas as mailFolders do usuário."""
        raise NotImplementedError

    def fetch_conversation_head(self, account: str, conversation_id: str, top: int = 10) -> List[EmailDTO]: 
        raise NotImplementedError

    def fetch_messages_in_folder(
        self,
        account: str,
        folder_id: str,
        page_size: int = 50
    ) -> List[EmailDTO]:
        """Retorna todas as mensagens de uma pasta, paginando."""
        raise NotImplementedError
