from ports.graph_client import GraphClientPort
from domain.model.metrics import EmailMetrics
from datetime import date

class ListFolderMetrics:
    def __init__(self, graph_client: GraphClientPort):
        self.graph = graph_client

    def execute(self):
        folders = self.graph.fetch_mail_folders()
        result = []
        for f in folders:
            result.append(EmailMetrics(
                date=date.today(),
                total_sent=f.total_count if f.display_name.lower().startswith("itens enviados") else 0,
                total_read=f.total_count - f.unread_count,
                total_replied=0  # se quiser filtrar por assunto “RES:” em fetch_messages...
            ))
        return result
